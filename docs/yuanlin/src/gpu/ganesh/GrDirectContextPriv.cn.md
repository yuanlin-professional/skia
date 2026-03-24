# GrDirectContextPriv

> 源文件
> - src/gpu/ganesh/GrDirectContextPriv.h
> - src/gpu/ganesh/GrDirectContextPriv.cpp

## 概述

`GrDirectContextPriv` 是 `GrDirectContext` 的特权访问类，为 Skia 内部代码提供对 `GrDirectContext` 私有成员和功能的访问接口。该类遵循"友元访问器"（Privileged Window）设计模式，不包含任何自有数据成员或虚函数，仅作为访问 `GrDirectContext` 内部实现的桥梁。

这个类的主要职责包括：管理表面刷新、编译着色器程序、访问GPU资源、进行预乘与非预乘颜色转换、以及提供调试和统计功能。它继承自 `GrRecordingContextPriv`，扩展了更多与直接GPU操作相关的特权方法。

## 架构位置

`GrDirectContextPriv` 位于 Skia GPU 上下文架构的核心层：

```
Skia GPU Context Hierarchy
├── GrContext (废弃基类)
├── GrRecordingContext (录制上下文基类)
│   └── GrRecordingContextPriv (录制上下文特权访问)
│       └── GrDirectContextPriv ← 当前模块
└── GrDirectContext (直接渲染上下文)
    ├── GrGpu (GPU硬件抽象层)
    ├── GrResourceCache (资源缓存)
    ├── GrResourceProvider (资源提供者)
    ├── GrDrawingManager (绘制管理器)
    └── GrAtlasManager (图集管理器)
```

该模块在架构中的作用：
- 为内部模块提供受控的上下文访问
- 隔离公共API与内部实现细节
- 支持DDL（延迟显示列表）的创建和回放
- 提供调试、测试和性能分析接口

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDirectContextPriv` | `GrRecordingContextPriv` | 直接上下文特权访问类 |

### 关键成员访问

`GrDirectContextPriv` 不包含自有成员变量，通过指针访问 `GrDirectContext` 的私有成员：

| 访问的成员 | 类型 | 说明 |
|-----------|------|------|
| `fContext` | `GrRecordingContext*` | 继承的上下文指针 |
| `fGpu` | `std::unique_ptr<GrGpu>` | GPU硬件接口 |
| `fResourceCache` | `std::unique_ptr<GrResourceCache>` | 资源缓存 |
| `fResourceProvider` | `std::unique_ptr<GrResourceProvider>` | 资源提供者 |
| `fStrikeCache` | `std::unique_ptr<sktext::gpu::StrikeCache>` | 字形缓存 |
| `fTaskGroup` | `std::unique_ptr<SkTaskGroup>` | 任务组 |
| `fMappedBufferManager` | `std::unique_ptr<GrClientMappedBufferManager>` | 映射缓冲区管理器 |
| `fPersistentCache` | `GrContextOptions::PersistentCache*` | 持久缓存 |
| `fPMUPMConversionsRoundTrip` | `bool` | PM↔UPM转换是否保持一致 |
| `fDidTestPMConversions` | `bool` | 是否已测试PM转换 |

## 公共 API 函数

### 工厂方法

#### Make
```cpp
static sk_sp<GrDirectContext> Make(
    GrBackendApi backend,
    const GrContextOptions& options,
    sk_sp<GrContextThreadSafeProxy> proxy);
```
创建 `GrDirectContext` 实例的内部工厂方法。

#### Init
```cpp
static bool Init(const sk_sp<GrDirectContext>& ctx);
```
初始化已创建的上下文对象。

#### SetGpu
```cpp
static void SetGpu(const sk_sp<GrDirectContext>& ctx, std::unique_ptr<GrGpu> gpu);
```
设置上下文的GPU实现。

### 表面刷新

#### flushSurfaces
```cpp
GrSemaphoresSubmitted flushSurfaces(
    SkSpan<GrSurfaceProxy*> proxies,
    SkSurfaces::BackendSurfaceAccess access = SkSurfaces::BackendSurfaceAccess::kNoAccess,
    const GrFlushInfo& info = {},
    const skgpu::MutableTextureState* newState = nullptr);
```
刷新指定的表面代理，完成所有待处理的绘制和写入操作，如有需要执行MSAA解析。

**参数说明：**
- `proxies`: 要刷新的表面代理数组（提示性，可能刷新更多）
- `access`: 后端表面访问模式
- `info`: 刷新信息，包含回调函数
- `newState`: 新的纹理状态

**返回值：** 是否提交了信号量

#### flushSurface
```cpp
GrSemaphoresSubmitted flushSurface(
    GrSurfaceProxy* proxy,
    SkSurfaces::BackendSurfaceAccess access = SkSurfaces::BackendSurfaceAccess::kNoAccess,
    const GrFlushInfo& info = {},
    const skgpu::MutableTextureState* newState = nullptr);
```
刷新单个表面代理的便捷方法，允许传入 `nullptr`。

### 资源访问

#### resourceProvider
```cpp
GrResourceProvider* resourceProvider();
const GrResourceProvider* resourceProvider() const;
```
获取资源提供者，用于创建和管理GPU资源。

#### getResourceCache
```cpp
GrResourceCache* getResourceCache();
```
获取资源缓存，管理GPU资源的生命周期。

#### getGpu
```cpp
GrGpu* getGpu();
const GrGpu* getGpu() const;
```
获取GPU硬件抽象层接口。

#### getAtlasManager
```cpp
GrAtlasManager* getAtlasManager();
```
获取图集管理器，仅应由 `GrOpFlushState` 调用。

#### getSmallPathAtlasMgr
```cpp
skgpu::ganesh::SmallPathAtlasMgr* getSmallPathAtlasMgr();
```
获取小路径图集管理器（仅在未启用大小优化时可用）。

#### getStrikeCache
```cpp
sktext::gpu::StrikeCache* getStrikeCache();
```
获取字形缓存。

#### getTaskGroup
```cpp
SkTaskGroup* getTaskGroup();
```
获取任务组，用于异步任务调度。

### DDL（延迟显示列表）支持

#### createDDLTask
```cpp
void createDDLTask(sk_sp<const GrDeferredDisplayList> ddl,
                   sk_sp<GrRenderTargetProxy> newDest);
```
创建DDL任务，将延迟显示列表中的渲染任务添加到绘制管理器。

### 着色器编译

#### compile
```cpp
bool compile(const GrProgramDesc& desc, const GrProgramInfo& info);
```
编译指定的着色器程序。

### 颜色转换

#### validPMUPMConversionExists
```cpp
bool validPMUPMConversionExists();
```
检测是否存在保持往返一致性的预乘↔非预乘转换效果。

#### createPMToUPMEffect
```cpp
std::unique_ptr<GrFragmentProcessor> createPMToUPMEffect(
    std::unique_ptr<GrFragmentProcessor> fp);
```
创建预乘到非预乘的片段处理器效果。

#### createUPMToPMEffect
```cpp
std::unique_ptr<GrFragmentProcessor> createUPMToPMEffect(
    std::unique_ptr<GrFragmentProcessor> fp);
```
创建非预乘到预乘的片段处理器效果。

### 调试和统计（GPU_TEST_UTILS）

#### 缓存统计
```cpp
void dumpCacheStats(SkString* out) const;
void printCacheStats() const;
```

#### GPU统计
```cpp
void resetGpuStats() const;
void dumpGpuStats(SkString* out) const;
void printGpuStats() const;
```

#### 上下文统计
```cpp
void resetContextStats();
void dumpContextStats(SkString* out) const;
void printContextStats() const;
```

#### 字体图集测试
```cpp
sk_sp<SkImage> testingOnly_getFontAtlasImage(
    skgpu::MaskFormat format,
    unsigned int index = 0);
```
获取字体图集纹理的快照图像，仅用于测试。

#### 回调测试
```cpp
void testingOnly_flushAndRemoveOnFlushCallbackObject(
    GrOnFlushCallbackObject* cb);
```

### 其他

#### getPersistentCache
```cpp
GrContextOptions::PersistentCache* getPersistentCache();
```
获取持久缓存，用于着色器二进制缓存。

#### clientMappedBufferManager
```cpp
GrClientMappedBufferManager* clientMappedBufferManager();
```
获取客户端映射缓冲区管理器。

#### setInsideReleaseProc
```cpp
void setInsideReleaseProc(bool inside);
```
标记是否在释放回调中，防止嵌套释放问题。

## 内部实现细节

### 预乘/非预乘转换测试

`test_for_preserving_PM_conversions` 函数执行复杂的往返测试：

1. **生成测试数据**：创建256×256的纹理，包含所有可能的预乘RGBA组合
2. **第一次转换**：PM → UPM（预乘到非预乘）
3. **第二次转换**：UPM → PM → UPM（完整往返）
4. **结果比较**：验证两次读取的非预乘值是否一致

测试代码使用 `SkRuntimeEffect` 创建自定义着色器：

```cpp
// 预乘效果
"half4 main(half4 halfColor) {"
    "float4 color = float4(halfColor);"
    "color = floor(color * 255 + 0.5) / 255;"
    "color.rgb = floor(color.rgb * color.a * 255 + 0.5) / 255;"
    "return color;"
"}"
```

这种激进的量化策略（舍入到最近的N/255）可以在某些GPU上找到保持往返一致性的转换对。

### 表面刷新实现

```cpp
GrSemaphoresSubmitted GrDirectContextPriv::flushSurfaces(...) {
    ASSERT_SINGLE_OWNER
    GR_CREATE_TRACE_MARKER_CONTEXT("GrDirectContextPriv", "flushSurfaces", ...);

    if (this->context()->abandoned()) {
        // 调用回调并返回
        if (info.fSubmittedProc) info.fSubmittedProc(..., false);
        if (info.fFinishedProc) info.fFinishedProc(...);
        return GrSemaphoresSubmitted::kNo;
    }

    // 委托给绘制管理器
    return this->context()->drawingManager()->flushSurfaces(proxies, access, info, newState);
}
```

### 单例所有权断言

使用宏确保线程安全：
```cpp
#define ASSERT_SINGLE_OWNER SKGPU_ASSERT_SINGLE_OWNER(this->context()->singleOwner())
#define ASSERT_OWNED_PROXY(P) \
    SkASSERT(!(P) || !((P)->peekTexture()) || (P)->peekTexture()->getContext() == this->context())
```

### 懒加载PM/UPM转换测试

```cpp
bool GrDirectContextPriv::validPMUPMConversionExists() {
    if (!dContext->fDidTestPMConversions) {
        dContext->fPMUPMConversionsRoundTrip = test_for_preserving_PM_conversions(dContext);
        dContext->fDidTestPMConversions = true;
    }
    return dContext->fPMUPMConversionsRoundTrip;
}
```

测试仅执行一次，结果缓存在上下文中。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrDirectContext` | 被访问的上下文对象 |
| `GrRecordingContextPriv` | 基类 |
| `GrGpu` | GPU硬件抽象 |
| `GrResourceCache` | 资源缓存管理 |
| `GrResourceProvider` | 资源创建 |
| `GrDrawingManager` | 绘制任务管理 |
| `GrAtlasManager` | 图集管理 |
| `GrFragmentProcessor` | 片段处理器 |
| `GrDeferredDisplayList` | DDL支持 |
| `SkRuntimeEffect` | 运行时着色器效果 |
| `GrSurfaceProxy` | 表面代理 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| Skia内部渲染代码 | 通过 `context->priv()` 访问特权功能 |
| `GrOpFlushState` | 访问atlas管理器 |
| DDL录制和回放系统 | 创建DDL任务 |
| 测试代码 | 访问调试和统计接口 |
| 颜色管理模块 | 使用PM/UPM转换效果 |

## 设计模式与设计决策

### 特权访问器模式（Privileged Window）

这是该类的核心设计模式：
```cpp
class GrDirectContextPriv : public GrRecordingContextPriv {
private:
    explicit GrDirectContextPriv(GrDirectContext* dContext);
    GrDirectContextPriv& operator=(const GrDirectContextPriv&) = delete;
    const GrDirectContextPriv* operator&() const;  // 禁止取地址
    GrDirectContextPriv* operator&();
    friend class GrDirectContext;
};

// 在 GrDirectContext 中
GrDirectContextPriv priv() { return GrDirectContextPriv(this); }
```

**优点：**
- 清晰分离公共API和内部接口
- 避免友元类污染
- 零运行时开销（编译器优化后）
- 类型安全

### 单例所有权（Single Owner）

使用 `SingleOwner` 调试工具确保线程安全：
```cpp
ASSERT_SINGLE_OWNER
```

在调试构建中检测多线程错误使用。

### 延迟初始化

PM/UPM转换测试采用延迟初始化，仅在首次需要时执行，避免不必要的开销。

### 委托模式

大部分功能委托给专门的管理器对象：
- 刷新操作 → `GrDrawingManager`
- 资源管理 → `GrResourceCache`、`GrResourceProvider`
- DDL任务 → `GrDrawingManager`

### 条件编译

调试和测试功能使用条件编译：
```cpp
#if defined(GPU_TEST_UTILS)
    void dumpCacheStats(SkString*) const;
    ...
#endif
```

减小发布版本的二进制大小。

### 设计决策

1. **不包含数据成员**：确保特权访问器没有额外的内存开销
2. **禁止取地址**：防止误用和生命周期问题
3. **返回值拷贝**：`priv()` 返回值对象而非引用，利用RVO优化
4. **const正确性**：提供const和非const版本的访问方法

## 性能考量

### 零开销抽象

`GrDirectContextPriv` 设计为零开销抽象：
- 无虚函数
- 无数据成员
- 内联访问方法
- 编译器可完全优化掉包装

### PM/UPM转换缓存

转换测试结果缓存避免重复执行昂贵的GPU操作：
```cpp
if (!dContext->fDidTestPMConversions) {
    dContext->fPMUPMConversionsRoundTrip = test_for_preserving_PM_conversions(dContext);
    dContext->fDidTestPMConversions = true;
}
```

### 批量刷新优化

`flushSurfaces` 接受代理数组，允许批量处理：
- 减少GPU命令提交次数
- 改善资源分配
- 更好的依赖管理

### 调试代码隔离

统计和调试功能使用条件编译，不影响发布版本性能。

### 单次所有权检查

使用 `ASSERT_SINGLE_OWNER` 宏，仅在调试构建中执行，发布版本无开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/GrDirectContext.h` | 被访问 | 直接渲染上下文公共接口 |
| `src/gpu/ganesh/GrRecordingContextPriv.h` | 基类 | 录制上下文特权访问基类 |
| `src/gpu/ganesh/GrGpu.h` | 访问 | GPU硬件抽象层 |
| `src/gpu/ganesh/GrResourceCache.h` | 访问 | 资源缓存 |
| `src/gpu/ganesh/GrResourceProvider.h` | 访问 | 资源提供者 |
| `src/gpu/ganesh/GrDrawingManager.h` | 访问 | 绘制管理器 |
| `src/gpu/ganesh/text/GrAtlasManager.h` | 访问 | 图集管理器 |
| `include/private/chromium/GrDeferredDisplayList.h` | 使用 | DDL支持 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 使用 | 片段处理器 |
| `include/effects/SkRuntimeEffect.h` | 使用 | 运行时着色器效果 |
| `src/gpu/ganesh/SurfaceFillContext.h` | 使用 | 表面填充上下文 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 使用 | 纹理效果 |
