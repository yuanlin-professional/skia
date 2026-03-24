# SkMetalViewBridge

> 源文件：tools/skottie_ios_app/SkMetalViewBridge.h, tools/skottie_ios_app/SkMetalViewBridge.mm

## 概述

SkMetalViewBridge 提供了 iOS MetalKit 视图与 Skia GPU 表面之间的桥接功能。该模块封装了将 MTKView 转换为 SkSurface 的逻辑，以及从 Metal 设备创建 Ganesh 上下文的工具函数。这使得 Skottie 动画能够通过 Metal 后端在 iOS 设备上高效渲染。

主要功能：
- 将 MTKView 包装为 SkSurface 以进行 Skia 绘制
- 从 Metal 设备和命令队列创建 GrDirectContext
- 配置 MTKView 的像素格式和深度/模板缓冲区以适配 Skia

该模块使用 Objective-C++ 实现，充分利用 Metal 和 Skia 的 C++ API。

## 架构位置

- **上层**：SkottieViewController（使用这些工具函数进行渲染）
- **下层**：Metal 框架、Skia Ganesh Metal 后端
- **桥接**：MetalKit（MTKView）与 Skia（SkSurface）

## 公共 API 函数

### SkMtkViewToSurface

```cpp
sk_sp<SkSurface> SkMtkViewToSurface(MTKView* mtkView, GrRecordingContext* rContext);
```

将 MTKView 包装为 SkSurface。

**参数**：
- `mtkView` - MetalKit 视图
- `rContext` - Ganesh 录制上下文

**返回**：SkSurface 智能指针，失败时返回 nullptr

**验证**：
- 上下文有效性
- 深度/模板格式必须是 `MTLPixelFormatDepth32Float_Stencil8`
- 颜色格式必须是 `MTLPixelFormatBGRA8Unorm`

**实现**：
```cpp
const SkColorType colorType = kBGRA_8888_SkColorType;
const GrSurfaceOrigin origin = kTopLeft_GrSurfaceOrigin;
int sampleCount = (int)[mtkView sampleCount];

return SkSurfaces::WrapMTKView(rContext,
                               (__bridge GrMTLHandle)mtkView,
                               origin,
                               sampleCount,
                               colorType,
                               colorSpace,
                               &surfaceProps);
```

### SkMetalDeviceToGrContext

```cpp
GrContextHolder SkMetalDeviceToGrContext(id<MTLDevice> device,
                                         id<MTLCommandQueue> queue);
```

从 Metal 设备和命令队列创建 Ganesh 上下文。

**参数**：
- `device` - Metal 设备对象
- `queue` - Metal 命令队列

**返回**：GrContextHolder（unique_ptr 包装器）

**实现**：
```cpp
GrMtlBackendContext backendContext = {};
backendContext.fDevice.reset((__bridge void*)device);
backendContext.fQueue.reset((__bridge void*)queue);
GrContextOptions grContextOptions;
return GrContextHolder(GrDirectContexts::MakeMetal(backendContext, grContextOptions).release());
```

### SkMtkViewConfigForSkia

```cpp
void SkMtkViewConfigForSkia(MTKView* mtkView);
```

配置 MTKView 以适配 Skia 的要求。

**配置项**：
- 深度/模板格式：`MTLPixelFormatDepth32Float_Stencil8`
- 颜色格式：`MTLPixelFormatBGRA8Unorm`
- 采样数：1（无 MSAA）

**实现**：
```cpp
[mtkView setDepthStencilPixelFormat:MTLPixelFormatDepth32Float_Stencil8];
[mtkView setColorPixelFormat:MTLPixelFormatBGRA8Unorm];
[mtkView setSampleCount:1];
```

## 内部实现细节

### 颜色格式选择

使用 `BGRA8Unorm` 而非 `RGBA8Unorm` 是因为：
- iOS/macOS 原生格式为 BGRA
- 避免运行时格式转换开销
- 与 Core Graphics 兼容

### 深度模板格式

`Depth32Float_Stencil8` 提供：
- 32 位浮点深度（高精度）
- 8 位模板缓冲区（用于遮罩和剪裁）
- 广泛的硬件支持

### 采样数

默认使用 1（无 MSAA）简化配置。如需抗锯齿可以增加。

### Objective-C 桥接

使用 `__bridge` 转换在 Objective-C 对象和 C++ 指针之间：
```cpp
(__bridge GrMTLHandle)mtkView
```

这是非拥有转换，不影响引用计数。

## 依赖关系

### Metal 框架
- `<Metal/Metal.h>` - Metal 核心 API
- `<MetalKit/MetalKit.h>` - MTKView 和辅助工具

### Skia 组件
- `include/gpu/ganesh/mtl/GrMtlDirectContext.h` - Metal 直接上下文
- `include/gpu/ganesh/mtl/SkSurfaceMetal.h` - Metal 表面包装
- `include/gpu/ganesh/mtl/GrMtlBackendContext.h` - Metal 后端上下文
- `tools/skottie_ios_app/GrContextHolder.h` - 上下文持有者

## 设计模式与设计决策

### 桥接模式
函数作为 MetalKit 和 Skia 之间的桥梁。

### 工厂函数设计
`SkMetalDeviceToGrContext` 封装复杂的上下文创建逻辑。

### 配置函数分离
`SkMtkViewConfigForSkia` 独立于表面创建，允许预先配置视图。

### 智能指针管理
返回 `sk_sp<SkSurface>` 和 `GrContextHolder` 确保自动内存管理。

## 性能考量

- 使用原生 BGRA 格式避免转换
- 单采样减少内存和带宽
- Metal 的低开销特性
- 直接包装 MTKView 避免中间缓冲

## 相关文件

- `tools/skottie_ios_app/SkottieViewController.h/.mm` - 使用这些函数的视图控制器
- `tools/skottie_ios_app/GrContextHolder.h/.mm` - Ganesh 上下文管理
- `include/gpu/ganesh/mtl/GrMtlDirectContext.h` - Metal 直接上下文
- `include/gpu/ganesh/mtl/SkSurfaceMetal.h` - Metal 表面API
