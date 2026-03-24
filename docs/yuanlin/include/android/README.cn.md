# include/android - Android 平台专用 API

## 概述

`include/android` 目录包含 Skia 为 Android 平台提供的专用 API 头文件。这些接口主要供 Android Framework（系统框架层）使用，提供了 Android 硬件缓冲区（AHardwareBuffer）集成、动画图像渲染、Surface/Image 的 Android 特化创建以及 Canvas 底层访问等功能。大部分接口被标记为 Android Framework 私有，不建议普通应用开发者直接使用。

Android 硬件缓冲区（AHardwareBuffer）是该目录的核心功能之一。AHardwareBuffer 是 Android 系统中跨进程、跨 API 的共享内存机制，可在 CPU、GPU（OpenGL ES/Vulkan）、Camera、Video Decoder 等多个硬件组件之间零拷贝共享图像数据。Skia 的 Android API 允许从 AHardwareBuffer 创建 SkImage 和 SkSurface，从而将 Android 系统的图形管线与 Skia 的渲染能力无缝连接。

该目录还提供了 `SkAnimatedImage` 类用于播放 GIF 等动画格式，`SkAndroidFrameworkUtils` 提供了模板剪裁、画布操作等 Framework 专用工具，以及 Bitmap 到 GPU 纹理的固定（Pin）机制。这些功能是 Android 系统 UI 渲染流水线的重要组成部分。

此外，该目录包含 `graphite/` 和 `vk/` 两个子目录，分别提供 Graphite 渲染引擎和 Vulkan 后端的 Android 特化接口。

## 目录结构

```
include/android/
├── graphite/                        # Graphite 引擎的 Android 接口
│   └── SurfaceAndroid.h             # Graphite AHardwareBuffer Surface 创建
├── vk/                              # Android Vulkan 特化接口
│   └── AndroidVulkanMemoryAllocator.h  # Android Vulkan 内存分配器
├── AHardwareBufferUtils.h           # AHardwareBuffer 工具函数
├── GrAHardwareBufferUtils.h         # Ganesh AHardwareBuffer GPU 纹理工具
├── SkAndroidFrameworkUtils.h        # Android Framework 专用工具集
├── SkAnimatedImage.h                # 动画图像播放（GIF 等）
├── SkCanvasAndroid.h                # Canvas 底层访问（TopLayer 信息）
├── SkImageAndroid.h                 # Android 专用 SkImage 创建函数
├── SkSurfaceAndroid.h               # Android 专用 SkSurface 创建函数
└── BUILD.bazel                      # Bazel 构建配置
```

## 关键类与函数

### AHardwareBuffer 集成
- **`SkImages::DeferredFromAHardwareBuffer()`** (`SkImageAndroid.h`): 从 AHardwareBuffer 创建延迟解码的 SkImage，支持指定 Alpha 类型、色彩空间和表面原点。需要 Android API Level 26+。
- **`SkImages::TextureFromAHardwareBufferWithData()`** (`SkImageAndroid.h`): 将 SkPixmap 数据上传到 AHardwareBuffer 支持的 GPU 纹理并返回 SkImage。
- **`SkSurfaces::WrapAndroidHardwareBuffer()`** (`SkSurfaceAndroid.h`): 从 AHardwareBuffer 创建可渲染的 SkSurface。缓冲区必须同时支持 `AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT` 和 `AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE`。
- **`AHardwareBufferUtils::GetSkColorTypeFromBufferFormat()`** (`AHardwareBufferUtils.h`): 将 AHardwareBuffer 格式转换为对应的 SkColorType。

### Ganesh GPU 纹理工具
- **`GrAHardwareBufferUtils::GetBackendFormat()`** (`GrAHardwareBufferUtils.h`): 获取 AHardwareBuffer 对应的 `GrBackendFormat`（已弃用，请使用 API 特定版本）。
- **`GrAHardwareBufferUtils::GetGLBackendFormat()`**: OpenGL 后端的 AHardwareBuffer 格式查询。
- **`GrAHardwareBufferUtils::GetVulkanBackendFormat()`**: Vulkan 后端的 AHardwareBuffer 格式查询。
- **`GrAHardwareBufferUtils::MakeBackendTexture()`**: 从 AHardwareBuffer 创建 `GrBackendTexture`，通过回调管理纹理生命周期（`DeleteImageProc`、`UpdateImageProc`）。

### Bitmap 纹理固定
- **`SkImages::PinnableRasterFromBitmap()`** (`SkImageAndroid.h`): 创建可通过 `skgpu::ganesh::PinAsTexture()` 固定为 GPU 纹理的光栅图像，Skia 不会复制 Bitmap 数据。
- **`skgpu::ganesh::PinAsTexture()`** (`SkImageAndroid.h`): 将图像内容上传并锁定为 GPU 纹理，后续绘制直接使用纹理而非原始像素。
- **`skgpu::ganesh::UnpinTexture()`**: 解除纹理固定，释放 GPU 资源。

### 动画图像
- **`SkAnimatedImage`** (`SkAnimatedImage.h`): 动画图像播放器，继承自 `SkDrawable`。
  - `Make()`: 从 `SkAndroidCodec` 创建，支持自定义尺寸和裁剪。
  - `decodeNextFrame()`: 解码下一帧，返回帧持续时间（毫秒）或 `kFinished`。
  - `getCurrentFrame()`: 获取当前帧的 SkImage。
  - `reset()`: 重置动画到开头。

### Framework 工具
- **`SkAndroidFrameworkUtils`** (`SkAndroidFrameworkUtils.h`):
  - `clipWithStencil()`: 将当前剪裁写入模板缓冲区（仅 GPU 画布）。用于 Android 视图系统的硬件加速剪裁。
  - `getSurfaceFromCanvas()`: 从 Canvas 获取底层 Surface。用于 Framework 需要直接访问渲染目标的场景。
  - `SaveBehind()`: 保存画布背景区域。用于实现 Android 的模糊背景等视觉效果。
  - `ResetClip()`: 重置剪裁几何为完全打开状态（受设备级剪裁限制除外）。
  - `getBaseWrappedCanvas()`: 展开嵌套的 SkPaintFilterCanvas 链，获取最底层的原始画布。
  - `SafetyNetLog()`: 安全网日志记录，用于 Android 系统安全审计。
  - `ShaderAsALinearGradient()`: 从着色器中提取线性渐变信息。
- **`skgpu::ganesh::TopLayerBounds()`** (`SkCanvasAndroid.h`): 获取 Canvas 顶层图层的 `SkIRect` 边界。
- **`skgpu::ganesh::TopLayerBackendRenderTarget()`** (`SkCanvasAndroid.h`): 获取 Canvas 顶层的 `GrBackendRenderTarget`，用于与外部渲染系统协调。

### API 级别要求
本目录中涉及 AHardwareBuffer 的 API 均需要 Android API Level 26（Android 8.0 Oreo）或更高版本。编译时通过 `__ANDROID_API__ >= 26` 条件编译控制。在不满足此条件的平台上，相关函数和类不可用。

## 依赖关系

- **上游依赖**: `include/core/`（SkImage、SkSurface、SkCanvas、SkDrawable 等）、`include/gpu/ganesh/`（GrBackendSurface、GrTypes）、`include/codec/`（SkAndroidCodec、SkCodecAnimation）
- **平台依赖**: Android NDK（`<android/hardware_buffer.h>`），需要 `__ANDROID_API__ >= 26`
- **下游消费者**: Android Framework 的 `hwui`（硬件加速 UI 渲染）和 `libhwui`（Canvas 2D 渲染库）
- **子目录**: `graphite/`（Graphite AHardwareBuffer 支持）、`vk/`（Android Vulkan 内存分配）

## 相关文档与参考

- [Android AHardwareBuffer](https://developer.android.com/ndk/reference/group/a-hardware-buffer) - Android NDK 硬件缓冲区 API
- [Android Skia 集成](https://source.android.com/docs/core/graphics/) - Android 图形系统架构
- [SkAnimatedImage 参考](https://api.skia.org/classSkAnimatedImage.html) - 动画图像 API 文档
- `include/gpu/ganesh/` - Ganesh GPU 后端公共 API
- `include/android/graphite/` - Graphite Android 接口文档
- `include/android/vk/` - Android Vulkan 接口文档
- `include/codec/` - 编解码器公共 API

## 使用注意事项

### Framework 专用标记
本目录中多数接口的注释中包含 "Private; only to be used by Android Framework" 标记。这意味着这些 API：
- 不保证在 Skia 版本更新时保持兼容
- 不建议 Android 应用开发者直接使用
- Skia 团队与 Android Framework 团队协调接口变更

### AHardwareBuffer 使用限制
- 缓冲区必须同时支持 GPU 颜色输出和 GPU 采样用途
- 在 Vulkan 后端上，`fromWindow` 参数会影响内存分配策略
- 从 AHardwareBuffer 创建的 Surface/Image 的生命周期受缓冲区生命周期约束
- 确保在调用 `DeferredFromAHardwareBuffer()` 后缓冲区不被过早释放

### 纹理固定注意事项
使用 `PinAsTexture()`/`UnpinTexture()` 时：
- 所有固定/解除固定操作必须在同一线程上执行
- 成功的每次 `PinAsTexture()` 调用都必须有对应的 `UnpinTexture()` 调用
- 固定后的图像具有与原生 GPU 图像相同的线程限制
