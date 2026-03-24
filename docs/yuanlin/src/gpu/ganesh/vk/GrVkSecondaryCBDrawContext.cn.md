# GrVkSecondaryCBDrawContext — Vulkan 辅助命令缓冲区绘制上下文

> 源文件: `src/gpu/ganesh/vk/GrVkSecondaryCBDrawContext.cpp`

## 概述

`GrVkSecondaryCBDrawContext` 允许 Skia 将绘制命令录制到 Vulkan 辅助命令缓冲区 (Secondary Command Buffer) 中。这是 Chromium 等嵌入器使用的私有 API，使得 Skia 可以在外部管理的 Vulkan 渲染通道 (Render Pass) 内执行绘制操作，而无需拥有主命令缓冲区或渲染通道的控制权。该类还支持延迟显示列表 (DDL) 的录制和回放。

## 架构位置

```
外部 Vulkan 渲染通道（如 Chromium 的 viz compositor）
    └── GrVkSecondaryCBDrawContext (本文件)
        ├── SkCanvas (绘图接口)
        ├── skgpu::ganesh::Device (设备实现)
        ├── GrSurfaceCharacterization (DDL 兼容性)
        └── GrDeferredDisplayList (DDL 回放)
            └── GrRenderTargetProxy (包装的辅助 CB)
```

## 主要类与结构体

### GrVkSecondaryCBDrawContext

| 成员 | 类型 | 描述 |
|------|------|------|
| `fDevice` | `sk_sp<skgpu::ganesh::Device>` | Ganesh 设备，持有渲染目标代理 |
| `fCachedCanvas` | `unique_ptr<SkCanvas>` | 懒创建的 Canvas，用于绘图操作 |
| `fProps` | `SkSurfaceProps` | 表面属性 |

## 公共 API 函数

### Make() — 静态工厂

```cpp
static sk_sp<GrVkSecondaryCBDrawContext> Make(GrRecordingContext* rContext,
                                               const SkImageInfo& imageInfo,
                                               const GrVkDrawableInfo& vkInfo,
                                               const SkSurfaceProps* props);
```

创建流程：
1. 验证上下文为 Vulkan 后端
2. 通过 `resourceProvider->wrapVulkanSecondaryCBAsRenderTarget()` 将辅助 CB 包装为渲染目标
3. 验证渲染目标不可纹理化且未预算
4. 检查颜色格式可渲染性
5. 创建 `GrRenderTargetProxy`（标记为 `WrapsVkSecondaryCB::kYes`，`UseAllocator::kNo`）
6. 创建 Ganesh 设备和上下文

### getCanvas()

```cpp
SkCanvas* getCanvas();
```

返回用于绘图的 Canvas。首次调用时懒创建。

### flush()

```cpp
void flush();
```

刷新待处理的绘制操作到辅助命令缓冲区，并提交到 GPU。调用 `flushSurface()` + `submit()`。

### wait()

```cpp
bool wait(int numSemaphores, const GrBackendSemaphore waitSemaphores[],
           bool deleteSemaphoresAfterWait);
```

在绘制前等待 GPU 信号量，用于外部同步。

### releaseResources()

```cpp
void releaseResources();
```

释放 Canvas 和 Device。析构函数验证此方法已被调用。

### characterize()

```cpp
bool characterize(GrSurfaceCharacterization* characterization) const;
```

描述此上下文的特征，用于 DDL 录制。设置 `VulkanSecondaryCBCompatible(true)`、`Textureable(false)`、`Mipmapped(kNo)` 等关键标志。

### isCompatible()

```cpp
bool isCompatible(const GrSurfaceCharacterization& characterization) const;
```

检查 DDL 特征是否与此上下文兼容。验证项包括：
- Vulkan 辅助 CB 兼容标志
- 不可纹理化
- 非 GL FBO0
- 上下文匹配、格式、尺寸、采样数、色彩空间、保护状态等

### draw()

```cpp
bool draw(sk_sp<const GrDeferredDisplayList> ddl);
// 或
bool draw(const GrDeferredDisplayList* ddl);
```

回放 DDL 到此上下文。先验证兼容性，然后通过 `createDDLTask()` 将 DDL 操作附加到渲染目标代理。

## 内部实现细节

1. **不可纹理化**: 辅助命令缓冲区包装的渲染目标不能用作纹理采样源，通过断言和 characterization 强制此约束。

2. **未预算资源**: 包装的外部资源不参与 Skia 的资源缓存预算，因为其生命周期由外部管理。

3. **代理不使用分配器**: `UseAllocator::kNo` 表示代理已即时实例化（`isInstantiated()`），不需要延迟分配。

4. **析构验证**: 析构函数通过 `SkASSERT(!fDevice && !fCachedCanvas)` 验证 `releaseResources()` 已被调用，防止资源泄漏。

5. **DDL 兼容性**: `SK_DDL_IS_UNIQUE_POINTER` 宏控制 DDL 参数是智能指针还是裸指针，用于过渡期的 API 兼容。

6. **Chromium 私有 API**: 头文件位于 `include/private/chromium/`，表明这是为 Chromium 设计的非公开接口。

## 依赖关系

**Vulkan 后端**:
- `include/gpu/ganesh/vk/GrVkBackendSurface.h` — Vulkan 后端表面
- `include/gpu/ganesh/vk/GrVkTypes.h` — `GrVkDrawableInfo`

**DDL 支持**:
- `include/private/chromium/GrDeferredDisplayList.h` — 延迟显示列表
- `include/private/chromium/GrSurfaceCharacterization.h` — 表面特征描述
- `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` — 线程安全代理

**资源管理**:
- `src/gpu/ganesh/GrProxyProvider.h` — 代理提供者
- `src/gpu/ganesh/GrResourceProvider.h` — 资源提供者
- `src/gpu/ganesh/GrRenderTarget.h`, `GrRenderTargetProxy.h` — 渲染目标

## 设计模式与设计决策

1. **命令缓冲区借用**: Skia 不创建或提交命令缓冲区，只是将绘制命令录制到外部提供的辅助命令缓冲区中。这允许嵌入器控制渲染通道的生命周期和提交时机。

2. **DDL 集成**: 通过 `characterize()` / `isCompatible()` / `draw()` 三步流程，支持在一个线程上录制 DDL，在另一个线程上回放到辅助命令缓冲区。

3. **显式资源释放**: `releaseResources()` 必须在析构前调用，比隐式 RAII 更明确地控制 GPU 资源释放时机。

4. **Canvas 懒创建**: `getCanvas()` 延迟 Canvas 创建到首次使用，因为某些使用场景可能只需要 DDL 回放而不直接绘图。

## 性能考量

- 辅助命令缓冲区允许在单个渲染通道内使用多个命令缓冲区，支持多线程命令录制。
- `flush()` 调用 `submit()` 触发实际的 GPU 提交，这是一个同步点。
- DDL 回放通过 `createDDLTask()` 将操作附加到代理，避免重新创建绘制操作。
- 不可纹理化约束避免了额外的渲染目标到纹理的解析拷贝。

## 相关文件

- `include/private/chromium/GrVkSecondaryCBDrawContext.h` — 公共声明
- `include/gpu/ganesh/vk/GrVkTypes.h` — `GrVkDrawableInfo` 定义
- `include/private/chromium/GrDeferredDisplayList.h` — DDL 定义
- `include/private/chromium/GrSurfaceCharacterization.h` — 表面特征
- `src/gpu/ganesh/GrResourceProvider.h` — `wrapVulkanSecondaryCBAsRenderTarget()`
- `src/gpu/ganesh/vk/GrVkRenderTarget.h` — Vulkan 渲染目标
