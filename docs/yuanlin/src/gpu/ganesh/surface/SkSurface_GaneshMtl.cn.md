# SkSurface_GaneshMtl — Metal 平台 Surface 工厂

> 源文件: `src/gpu/ganesh/surface/SkSurface_GaneshMtl.mm`

## 概述

本文件实现了 `SkSurfaces` 命名空间中用于 Apple Metal 平台的两个 Surface 创建工厂函数：`WrapCAMetalLayer` 和 `WrapMTKView`。它们将 Metal 原生显示对象（`CAMetalLayer` 和 `MTKView`）包装为 Skia `SkSurface`，使得 Skia 可以直接渲染到 Apple 平台的屏幕表面。这是 macOS 和 iOS 应用将 Skia 集成到 Metal 渲染管线的主要入口。

## 架构位置

```
应用层 (CAMetalLayer / MTKView)
    └── SkSurfaces::WrapCAMetalLayer / WrapMTKView (本文件)
        └── GrProxyProvider::createLazyRenderTargetProxy()
            └── 延迟回调 → nextDrawable / currentDrawable
                ├── GrMtlRenderTarget (framebufferOnly)
                └── GrMtlTextureRenderTarget (可采样)
                    └── SkSurface_Ganesh (Skia Surface)
```

## 主要类与结构体

本文件不定义新类，实现 `SkSurfaces` 命名空间中的工厂函数。涉及的关键 Metal 类型：

| 类型 | 描述 |
|------|------|
| `CAMetalLayer` | Core Animation Metal 图层，用于屏幕渲染 |
| `MTKView` | MetalKit 视图，UIKit/AppKit 的 Metal 视图封装 |
| `id<CAMetalDrawable>` | Metal 可绘制对象，代表一帧的渲染目标 |
| `GrMTLHandle` | Skia 中 Metal 对象的不透明句柄 (`void*`) |

## 公共 API 函数

### WrapCAMetalLayer()

```cpp
sk_sp<SkSurface> WrapCAMetalLayer(GrRecordingContext* rContext, GrMTLHandle layer,
                                   GrSurfaceOrigin origin, int sampleCnt,
                                   SkColorType colorType, sk_sp<SkColorSpace> colorSpace,
                                   const SkSurfaceProps* surfaceProps, GrMTLHandle* drawable);
```

将 `CAMetalLayer` 包装为 `SkSurface`。特点：
- 通过 `drawable` 输出参数返回当前可绘制对象的句柄（通过 `__bridge_retained` 转移所有权）
- 使用延迟代理，在实际需要时才获取 drawable
- 调用者需在提交绘制后释放 drawable

### WrapMTKView()

```cpp
sk_sp<SkSurface> WrapMTKView(GrRecordingContext* rContext, GrMTLHandle view,
                               GrSurfaceOrigin origin, int sampleCnt,
                               SkColorType colorType, sk_sp<SkColorSpace> colorSpace,
                               const SkSurfaceProps* surfaceProps);
```

将 `MTKView` 包装为 `SkSurface`。与 `WrapCAMetalLayer` 类似，但使用 `mtkView.currentDrawable` 获取 drawable，不通过输出参数返回。

## 内部实现细节

### 延迟代理创建

两个函数都使用 `createLazyRenderTargetProxy()` 创建延迟代理，回调在首次需要渲染目标时执行：

1. **获取 Drawable**:
   - CAMetalLayer: `[metalLayer nextDrawable]` — 从图层获取下一个可用 drawable
   - MTKView: `[mtkView currentDrawable]` — 获取当前帧的 drawable

2. **FramebufferOnly 检测**:
   - 若 `framebufferOnly = true`：创建 `GrMtlRenderTarget`（仅可渲染，不可采样）
   - 若 `framebufferOnly = false`：创建 `GrMtlTextureRenderTarget`（可渲染也可采样）
   - `framebufferOnly` 纹理不传 `texInfo` 参数

3. **MSAA 处理**: 当 `sampleCnt > 1` 时：
   - 设置 `kRequiresManualMSAAResolve` 标志
   - Surface 需要手动 MSAA 解析

### Objective-C 桥接

- `(__bridge CAMetalLayer*)`: 无所有权转移的类型转换
- `(__bridge_retained GrMTLHandle)`: 增加引用计数并转移所有权给 C++ 侧（仅 `WrapCAMetalLayer`）
- 使用 `GrMTLHandle` (`void*`) 跨越 C++/Objective-C 边界传递 Metal 对象

### 像素格式映射

- CAMetalLayer: `metalLayer.pixelFormat` → `GrBackendFormats::MakeMtl()`
- MTKView: `mtkView.colorPixelFormat` → `GrBackendFormats::MakeMtl()`

### 设备创建

通过 `rContext->priv().createDevice()` 创建 Ganesh 设备，参数包括颜色类型、代理、色彩空间、表面原点和属性。内容初始化为 `kUninit`（不清空）。

## 依赖关系

**Skia 核心**:
- `include/core/SkSurface.h`, `include/core/SkColorSpace.h`
- `src/gpu/ganesh/surface/SkSurface_Ganesh.h` — Surface 实现类

**Ganesh GPU**:
- `src/gpu/ganesh/GrProxyProvider.h` — 延迟代理创建
- `src/gpu/ganesh/GrResourceProvider.h` — 资源管理
- `src/gpu/ganesh/SurfaceDrawContext.h` — 绘制上下文

**Metal 后端**:
- `src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.h`
- `include/gpu/ganesh/mtl/GrMtlBackendSurface.h`
- `include/gpu/ganesh/mtl/GrMtlTypes.h`

**Apple 框架**:
- `<Metal/Metal.h>`, `<MetalKit/MetalKit.h>`, `<QuartzCore/CAMetalLayer.h>`

## 设计模式与设计决策

1. **延迟实例化 (Lazy Instantiation)**: 使用延迟代理推迟 drawable 获取到实际需要时。这很关键，因为 Metal drawable 的可用性取决于呈现时机——过早获取可能导致 drawable 耗尽。

2. **句柄隐藏**: 使用 `GrMTLHandle` (`void*`) 作为跨语言边界的不透明句柄，避免 C++ 头文件包含 Objective-C 类型。

3. **FramebufferOnly 优化**: 当图层声明仅用于帧缓冲时，创建纯渲染目标而非纹理渲染目标，减少 GPU 内存使用。

4. **所有权管理差异**: `WrapCAMetalLayer` 通过 `__bridge_retained` 将 drawable 所有权转移给调用者，而 `WrapMTKView` 不暴露 drawable（由 MTKView 管理生命周期）。

## 性能考量

- 延迟代理避免过早获取 Metal drawable，这是 Apple 文档中推荐的最佳实践——drawable 应尽可能晚获取。
- `framebufferOnly` 纹理在 iOS 上通常更快，因为不需要支持纹理采样的额外内存布局。
- `GrWrapCacheable::kNo` 确保 drawable 包装的资源不进入 Skia 缓存，因为每帧的 drawable 都不同。
- `Budgeted::kYes` 确保代理参与内存预算管理。
- MSAA 手动解析允许延迟解析到必要时刻，避免不必要的中间拷贝。

## 相关文件

- `include/gpu/ganesh/mtl/SkSurfaceMetal.h` — 公共 API 声明
- `src/gpu/ganesh/surface/SkSurface_Ganesh.h` — Ganesh Surface 基类实现
- `src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.h` — Metal 纹理渲染目标
- `src/gpu/ganesh/mtl/GrMtlRenderTarget.h` — Metal 纯渲染目标
- `src/gpu/ganesh/GrProxyProvider.h` — 代理提供者
- `src/gpu/ganesh/surface/SkSurface_AndroidFactories.cpp` — Android 平台类似实现
