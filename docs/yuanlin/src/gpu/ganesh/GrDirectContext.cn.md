# GrDirectContext

> 源文件: `include/gpu/ganesh/GrDirectContext.h` (1028 行), `src/gpu/ganesh/GrDirectContext.cpp` (1205 行)
> 辅助参考: `src/gpu/ganesh/GrDirectContextPriv.h` (友元类)

## 1. 概述

`GrDirectContext` 是 Ganesh GPU 后端的根上下文，代表与 GPU 设备的直接连接。它提供完整的 GPU 资源管理、命令提交、同步和后端纹理创建功能，是 Skia GPU 渲染的主入口点。每个 `GrDirectContext` 对应一个底层 GPU 上下文（如 OpenGL context、VkDevice、MTLDevice），负责将 Skia 绘制命令转换为底层 GPU API 调用。

**继承关系**：`GrDirectContext` → `GrRecordingContext` → `GrImageContext` → `GrContext_Base` → `SkRefCnt`

**架构位置**：
```
客户端 → GrDirectContext ──→ GrGpu (后端抽象)
              │                  ↓
              │          GL / Vulkan / Metal / Dawn / Mock
              │
              ├──→ GrResourceCache (资源缓存)
              ├──→ GrResourceProvider (资源创建)
              ├──→ GrDrawingManager (绘制调度)
              ├──→ GrAtlasManager (字形图集)
              └──→ GrClientMappedBufferManager (异步缓冲区)
```

**后端工厂创建路径**：各后端（MakeGL / MakeVulkan / MakeMetal 等）通过以下统一路径创建上下文：
1. `GrDirectContextPriv::Make(backend, options, proxy)` — 调用 `new GrDirectContext(...)`
2. `GrDirectContextPriv::SetGpu(ctx, gpu)` — 注入后端特定的 GrGpu 实现
3. `GrDirectContextPriv::Init(ctx)` — 调用 `ctx->init()` 完成初始化

**关键成员变量**（14 个 private 成员）：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDeleteCallbackHelper` | `std::unique_ptr<DeleteCallbackHelper>` | 析构回调辅助器，**第一个 private 成员**，保证最后被销毁 |
| `fDirectContextID` | `const DirectContextID` | 上下文唯一标识，构造时由 `DirectContextID::Next()` 生成 |
| `fTaskGroup` | `std::unique_ptr<SkTaskGroup>` | 多线程任务组，必须在 fGpu 之前声明以确保后销毁 |
| `fStrikeCache` | `std::unique_ptr<sktext::gpu::StrikeCache>` | 字形缓存 |
| `fGpu` | `std::unique_ptr<GrGpu>` | GPU 后端抽象层 |
| `fResourceCache` | `std::unique_ptr<GrResourceCache>` | GPU 资源缓存 |
| `fResourceProvider` | `std::unique_ptr<GrResourceProvider>` | GPU 资源工厂 |
| `fInsideReleaseProcCnt` | `int` | ReleaseProc 嵌套计数，>0 时禁止 abandon |
| `fDidTestPMConversions` | `bool` | 是否已测试 PM/UPM 转换 |
| `fPMUPMConversionsRoundTrip` | `bool` | PM/UPM 转换是否可逆 |
| `fPersistentCache` | `GrContextOptions::PersistentCache*` | 持久化着色器缓存（裸指针，不拥有） |
| `fMappedBufferManager` | `std::unique_ptr<GrClientMappedBufferManager>` | 客户端映射缓冲区管理器 |
| `fAtlasManager` | `std::unique_ptr<GrAtlasManager>` | 字形图集管理器 |
| `fSmallPathAtlasMgr` | `std::unique_ptr<skgpu::ganesh::SmallPathAtlasMgr>` | 小路径图集管理器（条件编译，`!SK_ENABLE_OPTIMIZE_SIZE`） |

---

## 2. 内部类

### 2.1 DirectContextID

上下文唯一标识符类型，用于区分不同的 `GrDirectContext` 实例。

#### Next()

```cpp
static GrDirectContext::DirectContextID Next();
```

**流程**：
1. 访问 `static std::atomic<uint32_t> nextID{1}`（从 1 开始）
2. `id = nextID.fetch_add(1, std::memory_order_relaxed)`
3. 如果 `id == SK_InvalidUniqueID`（即 0）→ 重新 fetch_add 跳过（do-while 循环）
4. 返回 `DirectContextID(id)`（调用 private constexpr 构造函数）

#### 其他方法

| 方法 | 实现 |
|------|------|
| `DirectContextID()` | 默认构造，`fID = SK_InvalidUniqueID`（无效） |
| `isValid()` | `fID != SK_InvalidUniqueID` |
| `makeInvalid()` | `fID = SK_InvalidUniqueID` |
| `operator==` | `fID == that.fID` |
| `operator!=` | `!(*this == that)` |

### 2.2 DeleteCallbackHelper

封装客户端注册的上下文销毁回调。

```cpp
class DeleteCallbackHelper {
    GrDirectContextDestroyedContext fContext;
    GrDirectContextDestroyedProc fProc;
public:
    DeleteCallbackHelper(context, proc);
    ~DeleteCallbackHelper() { if (fProc) fProc(fContext); }
};
```

**关键设计**：作为**第一个 private 成员**声明。C++ 按声明的逆序析构成员，因此它**最后被销毁**，保证客户端的 destroy 回调在所有其他成员（fGpu、fResourceCache 等）清理完毕后才触发。

---

## 3. 构造函数 / 析构函数 / 初始化

### 3.1 GrDirectContext(backend, options, proxy)

```cpp
GrDirectContext(GrBackendApi backend,
                const GrContextOptions& options,
                sk_sp<GrContextThreadSafeProxy> proxy);
```

**流程**：
1. 调用基类 `GrRecordingContext(std::move(proxy), false)`（`false` 表示非 DDL 录制上下文）
2. 创建 `fDeleteCallbackHelper`：从 `options.fContextDeleteContext` 和 `options.fContextDeleteProc` 构造
3. `fDirectContextID = DirectContextID::Next()`

> **注意**：`fGpu` 不在构造函数中设置。由外部通过 `GrDirectContextPriv::SetGpu()` 注入，`init()` 中使用。

### 3.2 init() override

```cpp
bool init() override;
```

**流程**（17 步）：
1. `ASSERT_SINGLE_OWNER`
2. `fGpu` 为空 → return false
3. `fThreadSafeProxy->priv().init(fGpu->refCaps(), fGpu->refPipelineBuilder())`
4. `GrRecordingContext::init()`（创建 GrDrawingManager、TextBlobRedrawCoordinator、ThreadSafeCache 等）→ 失败返回 false
5. 断言 `getTextBlobRedrawCoordinator()` 和 `threadSafeCache()` 已创建
6. 创建 `fStrikeCache = make_unique<StrikeCache>()`
7. 创建 `fResourceCache = make_unique<GrResourceCache>(singleOwner, directContextID, contextID)`
8. `fResourceCache->setProxyProvider(this->proxyProvider())`
9. `fResourceCache->setThreadSafeCache(this->threadSafeCache())`
10. （`GPU_TEST_UTILS`）如果 `options.fResourceCacheLimitOverride != -1` → 应用 `setResourceCacheLimit(override)`
11. 创建 `fResourceProvider = make_unique<GrResourceProvider>(fGpu, fResourceCache, singleOwner)`
12. 创建 `fMappedBufferManager = make_unique<GrClientMappedBufferManager>(directContextID)`
13. `fDidTestPMConversions = false`
14. 如果 `options.fExecutor` 非空 → 创建 `fTaskGroup = make_unique<SkTaskGroup>(*fExecutor)`
15. `fPersistentCache = options.fPersistentCache`
16. 确定 `allowMultitexturing`：如果 `options.fAllowMultipleGlyphCacheTextures == kNo` 或 shaderCaps 不支持（非 float32 且无 integer support）→ `kNo`；否则 → `kYes`
17. 创建 `fAtlasManager = make_unique<GrAtlasManager>(proxyProvider, glyphCacheMaxBytes, allowMultitexturing, supportBilerpFromGlyphAtlas)`
18. `addOnFlushCallbackObject(fAtlasManager.get())`
19. return true

### 3.3 ~GrDirectContext()

```cpp
~GrDirectContext() override;
```

**流程**：
1. `ASSERT_SINGLE_OWNER`
2. 如果 `fGpu` 存在 → `this->flushAndSubmit()`（保护未完全构造的 context 场景）
3. `syncAllOutstandingGpuWork(shouldExecuteWhileAbandoned=false)`（等待 GPU 完成所有工作）
4. `destroyDrawingManager()`
5. 如果 `fResourceCache` 存在 → `fResourceCache->releaseAll()`
6. `fMappedBufferManager.reset()`（**必须**在 `releaseAll` 之后，防止其他线程持有的异步缓冲区跨线程销毁）

### 3.4 MakeMock(mockOptions, options)

```cpp
static sk_sp<GrDirectContext> MakeMock(const GrMockOptions*, const GrContextOptions&);
static sk_sp<GrDirectContext> MakeMock(const GrMockOptions*); // 使用默认 options
```

**流程**（两参数版本）：
1. `new GrDirectContext(GrBackendApi::kMock, options, GrContextThreadSafeProxyPriv::Make(kMock, options))`
2. `direct->fGpu = GrMockGpu::Make(mockOptions, options, direct.get())`
3. `direct->init()` → 失败返回 `nullptr`
4. 返回 `direct`

单参数版本创建默认 `GrContextOptions` 后委托到两参数版本。

---

## 4. 公共方法

### 4.1 状态管理

#### abandonContext()

```cpp
void abandonContext() override;
```

放弃上下文，假定底层 GPU API 不再可用。不调用后端 API 释放资源。

**流程**：
1. 如果 `GrRecordingContext::abandoned()` → 早返回（已经放弃过）
2. 如果 `fInsideReleaseProcCnt > 0` → `SkDEBUGFAIL` + 返回（禁止在 ReleaseProc 内调用）
3. `GrRecordingContext::abandonContext()`（设置 abandoned 标志 + `destroyDrawingManager()`）
4. `syncAllOutstandingGpuWork(this->caps()->mustSyncGpuDuringAbandon())`
5. `fStrikeCache->freeAll()`
6. `fMappedBufferManager->abandon()`
7. `fResourceProvider->abandon()`
8. `fResourceCache->abandonAll()`（标记所有资源为 abandoned，**不调用**后端 API 释放）
9. `fGpu->disconnect(GrGpu::DisconnectType::kAbandon)`
10. （`!SK_ENABLE_OPTIMIZE_SIZE`）如果 `fSmallPathAtlasMgr` 存在 → `fSmallPathAtlasMgr->reset()`
11. `fAtlasManager->freeAll()`

#### releaseResourcesAndAbandonContext()

```cpp
void releaseResourcesAndAbandonContext();
```

正确释放所有 GPU 资源后放弃上下文。适用于 GPU 仍然可用但即将销毁的场景。

**流程**：
1. 如果 `GrRecordingContext::abandoned()` → 早返回
2. `GrRecordingContext::abandonContext()`（设置 abandoned 标志）
3. `syncAllOutstandingGpuWork(shouldExecuteWhileAbandoned=true)`（**总是同步**，因为 GPU 还活着）
4. `fResourceProvider->abandon()`
5. `fResourceCache->releaseAll()`（正确调用后端 API **释放** GPU 资源）
6. `fMappedBufferManager.reset()`（**必须**在 `releaseAll` 之后）
7. `fGpu->disconnect(GrGpu::DisconnectType::kCleanup)`（正确清理断开）
8. （`!SK_ENABLE_OPTIMIZE_SIZE`）如果 `fSmallPathAtlasMgr` 存在 → `fSmallPathAtlasMgr->reset()`
9. `fAtlasManager->freeAll()`

**与 abandonContext() 的关键区别**：

| 维度 | abandonContext() | releaseResourcesAndAbandonContext() |
|------|-----------------|-------------------------------------|
| 资源缓存 | `abandonAll()`（不调 API） | `releaseAll()`（正确释放） |
| GPU 断开 | `kAbandon` | `kCleanup` |
| 同步策略 | 取决于 `mustSyncGpuDuringAbandon()` | 总是同步 |
| 适用场景 | GPU 已丢失/不可用 | GPU 仍可用，即将销毁 |

#### abandoned()

```cpp
bool abandoned() override;
```

**流程**：
1. `GrRecordingContext::abandoned()` → true 则返回 true（之前已手动 abandon）
2. `fGpu` 存在且 `fGpu->isDeviceLost()` → 调用 `this->abandonContext()` 然后返回 true
3. 返回 false

#### isDeviceLost()

```cpp
bool isDeviceLost();
```

**流程**：
1. `fGpu` 存在且 `fGpu->isDeviceLost()`：
   - 如果 `!GrRecordingContext::abandoned()` → `this->abandonContext()`
   - 返回 true
2. 返回 false

**与 `abandoned()` 的区别**：`isDeviceLost()` **仅**在 GPU 设备实际丢失时返回 true；`abandoned()` 在手动 abandon 后也返回 true。

#### resetContext(state) / resetGLTextureBindings()

```cpp
void resetContext(uint32_t state = kAll_GrBackendState);
void resetGLTextureBindings();
```

| 方法 | 流程 |
|------|------|
| `resetContext(state)` | `ASSERT_SINGLE_OWNER` → `fGpu->markContextDirty(state)` |
| `resetGLTextureBindings()` | 如果 `abandoned()` 或 `backend() != kOpenGL` → 返回；否则 `fGpu->resetTextureBindings()` |

---

### 4.2 命令提交

#### flush / submit / flushAndSubmit 委托链表格

| 重载签名 | 类型 | 核心逻辑 / 委托到 |
|----------|------|-------------------|
| `flush(GrFlushInfo)` | **核心** | abandoned 时执行 `finishedProc` / `submittedProc` 后返回 `kNo`；否则 `drawingManager()->flushSurfaces({}, kNoAccess, info, nullptr)` |
| `flush()` | 包装器 | `flush(GrFlushInfo{})` |
| `flush(image, GrFlushInfo)` | **核心** | 检查 image 非空且 `isGaneshBacked()` → `static_cast<SkImage_GaneshBase*>` → `igb->flush(this, info)` |
| `flush(image)` | 包装器 | `flush(image, {})` |
| `flushAndSubmit(image)` | 包装器 | `flush(image, {})` + `submit()` |
| `flush(surface, access, info)` | **核心** | 检查 surface 非空且 `isGaneshBacked()` → cast 为 `SkSurface_Ganesh` → 获取 `rtp = gs->getDevice()->targetProxy()` → `priv().flushSurface(rtp, access, info, nullptr)` |
| `flush(surface, info, newState)` | **核心**（带状态转换） | 同上但传 `kNoAccess` + `newState`：`priv().flushSurface(rtp, kNoAccess, info, newState)` |
| `flush(surface)` | 包装器 | `flush(surface, GrFlushInfo{}, nullptr)` |
| `flushAndSubmit(sync)` | 内联包装器 | `flush(GrFlushInfo{})` + `submit(sync)` |
| `flushAndSubmit(surface, sync)` | 包装器 | `flush(surface, kNoAccess, GrFlushInfo{})` + `submit(sync)` |

#### submit(const GrSubmitInfo&)

```cpp
bool submit(const GrSubmitInfo& info);
```

**流程**：
1. `ASSERT_SINGLE_OWNER`
2. `this->abandoned()` → return false
3. `!fGpu` → return false
4. `fGpu->submitToGpu(info)`

#### submit(GrSyncCpu) (内联)

```cpp
bool submit(GrSyncCpu sync = GrSyncCpu::kNo) {
    GrSubmitInfo info;
    info.fSync = sync;
    return this->submit(info);
}
```

---

### 4.3 资源缓存管理

#### 查询与设置方法

| 方法 | 实现 |
|------|------|
| `getResourceCacheLimit()` | `ASSERT_SINGLE_OWNER` → `fResourceCache->getMaxResourceBytes()` |
| `setResourceCacheLimit(bytes)` | `ASSERT_SINGLE_OWNER` → `fResourceCache->setLimit(bytes)` |
| `getResourceCacheLimits(maxRes, maxBytes)` | DEPRECATED：`*maxResources = -1`，`*maxResourceBytes = getResourceCacheLimit()` |
| `setResourceCacheLimits(unused, bytes)` | DEPRECATED：委托 `setResourceCacheLimit(bytes)` |
| `getResourceCacheUsage(count, bytes)` | `*resourceCount = fResourceCache->getBudgetedResourceCount()`，`*resourceBytes = fResourceCache->getBudgetedResourceBytes()` |
| `getResourceCachePurgeableBytes()` | `fResourceCache->getPurgeableBytes()` |

#### freeGpuResources()

```cpp
void freeGpuResources();
```

**流程**：
1. `ASSERT_SINGLE_OWNER`，`abandoned()` → 返回
2. `flushAndSubmit()`
3. （`!SK_ENABLE_OPTIMIZE_SIZE`）如果 `fSmallPathAtlasMgr` 存在 → `fSmallPathAtlasMgr->reset()`
4. `fAtlasManager->freeAll()`
5. `fStrikeCache->freeAll()`
6. `drawingManager()->freeGpuResources()`
7. `fResourceCache->purgeUnlockedResources(GrPurgeResourceOptions::kAllResources)`

#### performDeferredCleanup(msNotUsed, opts)

```cpp
void performDeferredCleanup(std::chrono::milliseconds msNotUsed,
                            GrPurgeResourceOptions opts = GrPurgeResourceOptions::kAllResources);
```

**流程**：
1. `TRACE_EVENT0("skia.gpu", TRACE_FUNC)` + `ASSERT_SINGLE_OWNER`
2. `abandoned()` → 返回
3. `checkAsyncWorkCompletion()`
4. `fMappedBufferManager->process()`
5. `purgeTime = skgpu::StdSteadyClock::now() - msNotUsed`
6. `fResourceCache->purgeAsNeeded()`
7. `fResourceCache->purgeResourcesNotUsedSince(purgeTime, opts)`
8. `getTextBlobRedrawCoordinator()->purgeStaleBlobs()`

#### purgeUnlockedResources(GrPurgeResourceOptions)

```cpp
void purgeUnlockedResources(GrPurgeResourceOptions opts);
```

**流程**：
1. `ASSERT_SINGLE_OWNER`，`abandoned()` → 返回
2. `fResourceCache->purgeUnlockedResources(opts)`
3. `fResourceCache->purgeAsNeeded()`
4. `getTextBlobRedrawCoordinator()->purgeStaleBlobs()`
5. `fGpu->releaseUnlockedBackendObjects()`

#### purgeUnlockedResources(size_t, bool)

```cpp
void purgeUnlockedResources(size_t bytesToPurge, bool preferScratchResources);
```

**流程**：
1. `ASSERT_SINGLE_OWNER`，`abandoned()` → 返回
2. `fResourceCache->purgeUnlockedResources(bytesToPurge, preferScratchResources)`

---

### 4.4 信号量同步 wait()

```cpp
bool wait(int numSemaphores, const GrBackendSemaphore waitSemaphores[],
          bool deleteSemaphoresAfterWait = true);
```

**流程**：
1. `!fGpu` 或 `!fGpu->caps()->backendSemaphoreSupport()` → return false
2. `ownership = deleteSemaphoresAfterWait ? kAdopt_GrWrapOwnership : kBorrow_GrWrapOwnership`
3. 遍历 `[0, numSemaphores)`：
   - `sema = fResourceProvider->wrapBackendSemaphore(waitSemaphores[i], kWillWait, ownership)`
   - 如果 `sema` 有效 → `fGpu->waitSemaphore(sema.get())`
   - 无效则跳过（客户端给了无效信号量，可以安全忽略）
4. return true

---

### 4.5 后端纹理创建 (createBackendTexture)

#### 委托链表格

| 重载 | 类型 | 委托到 |
|------|------|--------|
| `(w, h, GrBackendFormat, mipmapped, renderable, protected, label)` | **核心（未初始化）** | `fGpu->createBackendTexture()` |
| `(w, h, SkColorType, mipmapped, renderable, protected, label)` | 包装器：解析 format | 上面的 GrBackendFormat 版本 |
| `(w, h, GrBackendFormat, color, mipmapped, renderable, ...)` | **核心（颜色初始化）** | `create_and_clear_backend_texture()` |
| `(w, h, SkColorType, color, mipmapped, renderable, ...)` | 包装器：解析 format + 应用 writeSwizzle | `create_and_clear_backend_texture()` |
| `(srcData[], numLevels, origin, renderable, protected, ...)` | **核心（像素初始化）** | `createBackendTexture(未初始化)` + `update_texture_with_pixmaps()` |
| `(srcData, origin, renderable, protected, ...)` | 包装器：单 SkPixmap | `(srcData[], 1, origin, ...)` |
| `(srcData[], numLevels, renderable, protected, ...)` | 包装器：默认 kTopLeft | `(srcData[], numLevels, kTopLeft_GrSurfaceOrigin, ...)` |
| `(srcData, renderable, protected, ...)` | 包装器 | `(srcData[], 1, renderable, ...)` |

#### 核心（未初始化）流程

```cpp
GrBackendTexture createBackendTexture(int width, int height,
                                      const GrBackendFormat& backendFormat,
                                      skgpu::Mipmapped mipmapped,
                                      GrRenderable renderable,
                                      GrProtected isProtected,
                                      std::string_view label);
```

**流程**：
1. `TRACE_EVENT0("skia.gpu", TRACE_FUNC)`
2. `this->abandoned()` → 返回无效 `GrBackendTexture()`
3. `fGpu->createBackendTexture({width, height}, backendFormat, renderable, mipmapped, isProtected, label)`

#### 核心（SkColorType + color）流程

```cpp
GrBackendTexture createBackendTexture(int width, int height,
                                      SkColorType skColorType,
                                      const SkColor4f& color, ...);
```

**流程**：
1. 创建 `finishedCallback = skgpu::RefCntedCallback::Make(finishedProc, finishedContext)`
2. `this->abandoned()` → 返回 `{}`
3. `format = this->defaultBackendFormat(skColorType, renderable)` → `!format.isValid()` 则返回 `{}`
4. `grColorType = SkColorTypeToGrColorType(skColorType)`
5. `swizzledColor = this->caps()->getWriteSwizzle(format, grColorType).applyTo(color)`（应用写入 swizzle）
6. 委托 `create_and_clear_backend_texture(this, {w,h}, format, mipmapped, renderable, isProtected, finishedCallback, swizzledColor.array(), label)`

#### 核心（像素初始化）流程

```cpp
GrBackendTexture createBackendTexture(const SkPixmap srcData[],
                                      int numProvidedLevels,
                                      GrSurfaceOrigin textureOrigin, ...);
```

**流程**：
1. `TRACE_EVENT0("skia.gpu", TRACE_FUNC)`
2. 创建 `finishedCallback`
3. `this->abandoned()` → 返回 `{}`
4. `!srcData || numProvidedLevels <= 0` → 返回 `{}`
5. `colorType = srcData[0].colorType()`
6. `mipmapped = numProvidedLevels > 1 ? kYes : kNo`
7. `backendFormat = this->defaultBackendFormat(colorType, renderable)`
8. 创建未初始化纹理：`beTex = createBackendTexture(srcData[0].width(), srcData[0].height(), backendFormat, mipmapped, renderable, isProtected, label)`
9. `!beTex.isValid()` → 返回 `{}`
10. `update_texture_with_pixmaps(this, srcData, numLevels, beTex, textureOrigin, finishedCallback)` → 失败则 `deleteBackendTexture(beTex)` + 返回 `{}`
11. 返回 `beTex`

---

### 4.6 后端纹理更新 (updateBackendTexture)

#### 委托链表格

| 重载 | 类型 | 委托到 |
|------|------|--------|
| `(texture, color, finishedProc, ctx)` | **核心（颜色）** | `fGpu->clearBackendTexture()` |
| `(texture, SkColorType, color, finishedProc, ctx)` | 扩展：验证兼容性 + writeSwizzle | `fGpu->clearBackendTexture()` |
| `(texture, srcData[], numLevels, origin, ...)` | **核心（像素）** | `update_texture_with_pixmaps()` |
| `(texture, srcData, origin, ...)` | 内联包装器（单 SkPixmap） | `(&srcData, 1, origin, ...)` |
| `(texture, srcData[], numLevels, finishedProc, ctx)` | 包装器：默认 kTopLeft | `(texture, srcData, numLevels, kTopLeft, ...)` |

#### 核心（颜色更新 — GrBackendFormat 版本）

```cpp
bool updateBackendTexture(const GrBackendTexture& backendTexture,
                          const SkColor4f& color,
                          GrGpuFinishedProc finishedProc,
                          GrGpuFinishedContext finishedContext);
```

**流程**：
1. 创建 `finishedCallback`
2. `this->abandoned()` → return false
3. `fGpu->clearBackendTexture(backendTexture, std::move(finishedCallback), color.array())`

#### 扩展（SkColorType 版本）

```cpp
bool updateBackendTexture(const GrBackendTexture& backendTexture,
                          SkColorType skColorType,
                          const SkColor4f& color, ...);
```

**流程**：
1. 创建 `finishedCallback`
2. `this->abandoned()` → return false
3. `format = backendTexture.getBackendFormat()`
4. `grColorType = SkColorTypeToGrColorType(skColorType)`
5. `!caps()->areColorTypeAndFormatCompatible(grColorType, format)` → return false
6. `swizzle = caps()->getWriteSwizzle(format, grColorType)`
7. `swizzledColor = swizzle.applyTo(color)`
8. `fGpu->clearBackendTexture(backendTexture, finishedCallback, swizzledColor.array())`

#### 核心（像素更新）

```cpp
bool updateBackendTexture(const GrBackendTexture& backendTexture,
                          const SkPixmap srcData[],
                          int numLevels,
                          GrSurfaceOrigin textureOrigin, ...);
```

**流程**：
1. 创建 `finishedCallback`
2. `this->abandoned()` → return false
3. `!srcData || numLevels <= 0` → return false
4. MIP 级别验证：
   - `numExpectedLevels = 1`
   - 如果 `backendTexture.hasMipmaps()` → `numExpectedLevels = SkMipmap::ComputeLevelCount(w, h) + 1`
   - `numLevels != numExpectedLevels` → return false（必须提供完整 MIP 链）
5. `update_texture_with_pixmaps(this, srcData, numLevels, backendTexture, textureOrigin, finishedCallback)`

---

### 4.7 压缩纹理创建与更新

#### createCompressedBackendTexture 委托链

| 重载 | 类型 | 委托到 |
|------|------|--------|
| `(w, h, GrBackendFormat, color, mipmapped, ...)` | **核心（颜色）** | 生成压缩数据 → `create_and_update_compressed_backend_texture()` |
| `(w, h, CompressionType, color, mipmapped, ...)` | 包装器：解析 format | GrBackendFormat 版本 |
| `(w, h, GrBackendFormat, data, dataSize, mipmapped, ...)` | **核心（原始数据）** | `create_and_update_compressed_backend_texture()` |
| `(w, h, CompressionType, data, dataSize, mipmapped, ...)` | 包装器：解析 format | GrBackendFormat 版本 |

#### 核心（颜色初始化）流程

```cpp
GrBackendTexture createCompressedBackendTexture(int width, int height,
                                                const GrBackendFormat& backendFormat,
                                                const SkColor4f& color,
                                                skgpu::Mipmapped mipmapped, ...);
```

**流程**：
1. `TRACE_EVENT0("skia.gpu", TRACE_FUNC)`
2. 创建 `finishedCallback`
3. `this->abandoned()` → 返回 `{}`
4. `compression = GrBackendFormatToCompressionType(backendFormat)` → `kNone` 则返回 `{}`
5. `size = SkCompressedDataSize(compression, {w, h}, nullptr, mipmapped == kYes)`
6. 分配 `storage = make_unique<char[]>(size)`
7. `skgpu::FillInCompressedData(compression, {w, h}, mipmapped, storage.get(), color)`
8. 委托 `create_and_update_compressed_backend_texture(this, {w,h}, backendFormat, mipmapped, isProtected, finishedCallback, storage.get(), size)`

#### updateCompressedBackendTexture（颜色版本）

```cpp
bool updateCompressedBackendTexture(const GrBackendTexture& backendTexture,
                                    const SkColor4f& color, ...);
```

**流程**：
1. 创建 `finishedCallback`
2. `this->abandoned()` → return false
3. `compression = GrBackendFormatToCompressionType(backendTexture.getBackendFormat())` → `kNone` 则返回 false
4. `size = SkCompressedDataSize(compression, backendTexture.dimensions(), nullptr, backendTexture.hasMipmaps())`
5. `SkAutoMalloc storage(size)`
6. `skgpu::FillInCompressedData(compression, backendTexture.dimensions(), backendTexture.mipmapped(), storage, color)`
7. `fGpu->updateCompressedBackendTexture(backendTexture, finishedCallback, storage.get(), size)`

#### updateCompressedBackendTexture（原始数据版本）

```cpp
bool updateCompressedBackendTexture(const GrBackendTexture& backendTexture,
                                    const void* compressedData, size_t dataSize, ...);
```

**流程**：
1. 创建 `finishedCallback`
2. `this->abandoned()` → return false
3. `!compressedData` → return false
4. `fGpu->updateCompressedBackendTexture(backendTexture, finishedCallback, compressedData, dataSize)`

---

### 4.8 纹理/渲染目标状态管理

#### setBackendTextureState / setBackendRenderTargetState

```cpp
bool setBackendTextureState(const GrBackendTexture&, const skgpu::MutableTextureState&,
                            skgpu::MutableTextureState* previousState, ...);
bool setBackendRenderTargetState(const GrBackendRenderTarget&, const skgpu::MutableTextureState&,
                                 skgpu::MutableTextureState* previousState, ...);
```

两者流程相同：
1. `callback = skgpu::RefCntedCallback::Make(finishedProc, finishedContext)`
2. `this->abandoned()` → return false
3. `fGpu->setBackendTextureState(texture, state, previousState, callback)` / `fGpu->setBackendRenderTargetState(...)`

#### deleteBackendTexture

```cpp
void deleteBackendTexture(const GrBackendTexture& backendTex);
```

**流程**：
1. `TRACE_EVENT0("skia.gpu", TRACE_FUNC)`
2. 如果 `(this->abandoned() && this->backend() != GrBackendApi::kVulkan) || !backendTex.isValid()` → 返回
3. `fGpu->deleteBackendTexture(backendTex)`

**Vulkan 特例**：Vulkan 资源必须显式销毁，即使 context 已 abandon。其他后端（如 OpenGL）在 context 销毁时由驱动自动清理资源。

---

### 4.9 其他公共方法

| 方法 | 实现 |
|------|------|
| `oomed()` | `fGpu ? fGpu->checkAndResetOOMed() : false` |
| `checkAsyncWorkCompletion()` | `fGpu` 存在则 `fGpu->checkFinishedCallbacks()` |
| `precompileShader(key, data)` | `fGpu->precompileShader(key, data)` |
| `supportsDistanceFieldText()` | `caps()->shaderCaps()->supportsDistanceFieldText()` |
| `supportedGpuStats()` | `caps()->supportedGpuStats()` |
| `threadSafeProxy()` | `GrRecordingContext::threadSafeProxy()` |
| `directContextID()` | 返回 `fDirectContextID`（内联） |

#### dumpMemoryStatistics(traceMemoryDump)

```cpp
void dumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump) const;
```

**流程**：
1. `ASSERT_SINGLE_OWNER`
2. `fResourceCache->dumpMemoryStatistics(traceMemoryDump)`
3. `traceMemoryDump->dumpNumericValue("skia/gr_text_blob_cache", "size", "bytes", getTextBlobRedrawCoordinator()->usedBytes())`

#### dump() (SK_ENABLE_DUMP_GPU)

```cpp
#ifdef SK_ENABLE_DUMP_GPU
SkString dump() const;
#endif
```

**流程**：
1. 创建 `SkDynamicMemoryWStream` + `SkJSONWriter(Mode::kPretty)`
2. `writer.beginObject()`
3. `writer.appendCString("backend", GrBackendApiToStr(this->backend()))`
4. `writer.appendName("caps")` → `this->caps()->dumpJSON(&writer)`
5. `writer.appendName("gpu")` → `this->fGpu->dumpJSON(&writer)`
6. `writer.appendName("context")` → `this->dumpJSON(&writer)`（基类方法）
7. `writer.endObject()` → `writer.flush()`
8. `stream.write8(0)` — null 终止
9. 分配 `SkString result(stream.bytesWritten())`，`stream.copyToAndReset(result.data())`
10. 返回 `result`

#### Vulkan 管线缓存方法

| 方法 | 实现 |
|------|------|
| `canDetectNewVkPipelineCacheData()` | `!fGpu` → false；否则 `fGpu->canDetectNewVkPipelineCacheData()` |
| `hasNewVkPipelineCacheData()` | `!fGpu` → false；否则 `fGpu->hasNewVkPipelineCacheData()` |
| `storeVkPipelineCacheData()` | 委托 `storeVkPipelineCacheData(SIZE_MAX)` |
| `storeVkPipelineCacheData(maxSize)` | `fGpu` 存在则 `fGpu->storeVkPipelineCacheData(maxSize)` |

---

## 5. 保护方法

#### onGetAtlasManager()

```cpp
GrAtlasManager* onGetAtlasManager() { return fAtlasManager.get(); }
```

内联，直接返回字形图集管理器。

#### onGetSmallPathAtlasMgr()（条件编译：`!SK_ENABLE_OPTIMIZE_SIZE`）

```cpp
skgpu::ganesh::SmallPathAtlasMgr* onGetSmallPathAtlasMgr();
```

**流程**：
1. 如果 `fSmallPathAtlasMgr` 为 null：
   - 创建 `fSmallPathAtlasMgr = make_unique<skgpu::ganesh::SmallPathAtlasMgr>()`
   - `this->priv().addOnFlushCallbackObject(fSmallPathAtlasMgr.get())`
2. `fSmallPathAtlasMgr->initAtlas(this->proxyProvider(), this->caps())` → 失败返回 `nullptr`
3. 返回 `fSmallPathAtlasMgr.get()`

**惰性创建**：与 `fAtlasManager`（`init()` 中创建）不同，`fSmallPathAtlasMgr` 首次访问时才创建。因为小路径渲染可能永远不被使用，且受 `SK_ENABLE_OPTIMIZE_SIZE` 条件编译控制。

#### asDirectContext() override

```cpp
GrDirectContext* asDirectContext() override { return this; }
```

内联，实现从 `GrRecordingContext*` 的安全向下转型。

---

## 6. 私有方法

#### syncAllOutstandingGpuWork(shouldExecuteWhileAbandoned)

```cpp
void syncAllOutstandingGpuWork(bool shouldExecuteWhileAbandoned);
```

**流程**：
1. 如果 `fGpu` 存在且（`!this->abandoned()` 或 `shouldExecuteWhileAbandoned`）：
   - `fGpu->finishOutstandingGpuWork()`（GPU fence 等待所有提交的工作完成）
   - `this->checkAsyncWorkCompletion()`（触发完成回调）

> **设计说明**：在 `abandonContext()` 中调用时，context 已被标记为 abandoned。`shouldExecuteWhileAbandoned` 参数允许绕过 abandoned 检查以正确完成同步。

---

## 7. 静态辅助函数

### create_and_clear_backend_texture()

```cpp
static GrBackendTexture create_and_clear_backend_texture(
    GrDirectContext* dContext, SkISize dimensions,
    const GrBackendFormat& backendFormat, skgpu::Mipmapped mipmapped,
    GrRenderable renderable, GrProtected isProtected,
    sk_sp<skgpu::RefCntedCallback> finishedCallback,
    std::array<float, 4> color, std::string_view label);
```

**流程**：
1. `gpu = dContext->priv().getGpu()`
2. `beTex = gpu->createBackendTexture(dimensions, format, renderable, mipmapped, isProtected, label)`
3. `!beTex.isValid()` → 返回 `{}`
4. `gpu->clearBackendTexture(beTex, std::move(finishedCallback), color)` → 失败则 `dContext->deleteBackendTexture(beTex)` + 返回 `{}`
5. 返回 `beTex`

### update_texture_with_pixmaps()

```cpp
static bool update_texture_with_pixmaps(
    GrDirectContext* context, const SkPixmap src[], int numLevels,
    const GrBackendTexture& backendTexture, GrSurfaceOrigin textureOrigin,
    sk_sp<skgpu::RefCntedCallback> finishedCallback);
```

**流程**：
1. `ct = SkColorTypeToGrColorType(src[0].colorType())`
2. `format = backendTexture.getBackendFormat()`
3. `!caps()->areColorTypeAndFormatCompatible(ct, format)` → return false
4. `proxy = proxyProvider->wrapBackendTexture(backendTexture, kBorrow, kNo(cacheable), kRW, finishedCallback)` → 失败返回 false
5. `readSwizzle = caps()->getReadSwizzle(format, ct)`
6. 创建 `GrSurfaceProxyView(std::move(proxy), textureOrigin, swizzle)`
7. 创建 `skgpu::ganesh::SurfaceContext(context, std::move(view), src[0].info().colorInfo())`
8. 转换 `SkPixmap[]` → `GrCPixmap[]`（`AutoSTArray<15, GrCPixmap>`）
9. `surfaceContext.writePixels(context, tmpSrc.get(), numLevels)` → 失败返回 false
10. `p = surfaceContext.asSurfaceProxy()`
11. `drawingManager->flushSurfaces({&p, 1}, kNoAccess, {}, nullptr)`（确保上传命令就绪）
12. return true

**关键设计**：通过 wrap 后端纹理为 proxy → 创建 SurfaceContext → 复用标准 `writePixels` 路径，避免重复实现像素格式转换逻辑。

### create_and_update_compressed_backend_texture()

```cpp
static GrBackendTexture create_and_update_compressed_backend_texture(
    GrDirectContext* dContext, SkISize dimensions,
    const GrBackendFormat& backendFormat, skgpu::Mipmapped mipmapped,
    GrProtected isProtected, sk_sp<skgpu::RefCntedCallback> finishedCallback,
    const void* data, size_t size);
```

**流程**：
1. `gpu = dContext->priv().getGpu()`
2. `beTex = gpu->createCompressedBackendTexture(dimensions, backendFormat, mipmapped, isProtected)`
3. `!beTex.isValid()` → 返回 `{}`
4. `gpu->updateCompressedBackendTexture(beTex, std::move(finishedCallback), data, size)` → 失败则 `dContext->deleteBackendTexture(beTex)` + 返回 `{}`
5. 返回 `beTex`

---

## 8. 关键设计决策

- **DeleteCallbackHelper 声明顺序**：作为第一个 private 成员声明，C++ 按声明的逆序析构，因此它最后被销毁，保证客户端的 destroy 回调在所有其他成员清理完毕后才触发。

- **flush 与 submit 分离**：`flush()` 将绘制命令记录到后端命令缓冲区但不发送到 GPU；`submit()` 才实际发送。允许多次 flush 后单次 submit，优化吞吐量。

- **两条 abandon 路径**：`abandonContext()`（GPU 丢失，不调 API 释放）使用 `abandonAll` + `kAbandon`；`releaseResourcesAndAbandonContext()`（GPU 还活着，正确清理）使用 `releaseAll` + `kCleanup`。

- **Vulkan deleteBackendTexture 特例**：Vulkan 资源必须显式销毁，即使 context 已 abandon。其他后端（如 OpenGL）在 context 销毁时自动清理资源。

- **写入 swizzle**：`SkColorType` + `SkColor4f` 版本的 `createBackendTexture` / `updateBackendTexture` 会通过 `caps()->getWriteSwizzle()` 将颜色值转换为后端格式（如 BGRA vs RGBA）。`GrBackendFormat` 版本不做此转换，由调用者负责。

- **像素上传复用 SurfaceContext**：`update_texture_with_pixmaps()` 将后端纹理 wrap 为 proxy → 创建 SurfaceContext → 使用 `writePixels` 标准路径。这复用了完整的像素格式转换和上传机制。

- **SmallPathAtlasMgr 惰性创建**：与 `fAtlasManager`（`init()` 中创建）不同，`fSmallPathAtlasMgr` 首次访问时才创建。因为小路径渲染可能永远不被使用，且受 `SK_ENABLE_OPTIMIZE_SIZE` 条件编译控制。

- **RefCntedCallback 模式**：所有异步 GPU 操作将 `finishedProc` 包装为 `RefCntedCallback`。即使在错误路径提前返回时，`RefCntedCallback` 的析构函数也会调用回调，保证回调恰好执行一次。

- **fInsideReleaseProcCnt 守卫**：防止在 `ReleaseProc` 回调内调用 `abandonContext()`，避免递归销毁。通过 `GrDirectContextPriv::setInsideReleaseProc()` 递增/递减计数器。
