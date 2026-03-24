# AHardwareBufferUtils

> 源文件: `include/android/AHardwareBufferUtils.h`

## 概述

AHardwareBufferUtils 是 Skia 中用于处理 Android 硬件缓冲区(AHardwareBuffer)的工具模块。该模块提供了从 Android 硬件缓冲区格式到 Skia 颜色类型的转换功能,是 Skia 与 Android 图形栈集成的关键接口,支持零拷贝图像共享和高效的 GPU 渲染。

## 架构位置

该模块位于 Skia 的 Android 平台适配层,是连接 Android NDK API(AHardwareBuffer)和 Skia 核心类型系统(SkColorType)的桥梁。它为上层的 Surface、Image 等模块提供硬件缓冲区格式识别能力,是 Android 平台高性能图像处理的基础设施。

## 平台依赖

该模块仅在 Android API Level 26(Android 8.0)及以上版本可用:

```cpp
#if __ANDROID_API__ >= 26
// AHardwareBufferUtils 功能可用
#endif
```

**历史背景**: AHardwareBuffer API 在 Android 8.0(Oreo)中引入,用于跨进程和跨 API(Vulkan/OpenGL/Camera 等)共享图形缓冲区。

## 核心常量

### `kExternalFormatColorType`

定义外部格式图像的默认颜色类型。

```cpp
static const SkColorType kExternalFormatColorType = SkColorType::kRGBA_8888_SkColorType;
```

**功能**: 指定从外部图像源(如相机、视频解码器)导入的 AHardwareBuffer 的颜色类型。

**设计原因**:
- 外部格式的实际布局可能未知(如 YUV、专有压缩格式)
- 统一映射到 RGBA_8888,上层代码无需关心底层细节
- GPU 通过 EGL External Image 或 VkExternalFormatAndroid 处理实际转换

**典型场景**:
- 相机预览帧(通常是 YUV 或 NV21 格式)
- 视频解码输出(MediaCodec 的硬件缓冲区)
- 受保护内容(DRM 保护的视频帧)

## 核心函数

### `GetSkColorTypeFromBufferFormat`

将 AHardwareBuffer 的格式转换为 SkColorType。

```cpp
SkColorType GetSkColorTypeFromBufferFormat(uint32_t bufferFormat)
```

**参数**:
- `bufferFormat`: AHardwareBuffer 的格式标识符(来自 `AHardwareBuffer_Format` 枚举)

**返回值**:
- 对应的 SkColorType,如果格式不支持则返回 `kUnknown_SkColorType`

**支持的格式映射**:

| AHardwareBuffer 格式 | SkColorType | 说明 |
|----------------------|-------------|------|
| AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM | kRGBA_8888_SkColorType | 标准 RGBA 8-bit |
| AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM | kRGB_888x_SkColorType | RGB 8-bit,Alpha 忽略 |
| AHARDWAREBUFFER_FORMAT_R8G8B8_UNORM | kRGB_888x_SkColorType | RGB 8-bit(无 Alpha) |
| AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM | kRGB_565_SkColorType | RGB 5-6-5 |
| AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT | kRGBA_F16_SkColorType | HDR 半精度浮点 |
| AHARDWAREBUFFER_FORMAT_R10G10B10A2_UNORM | kRGBA_1010102_SkColorType | HDR 10-bit |

**不支持的格式**:
- YUV 格式(AHARDWAREBUFFER_FORMAT_Y8Cb8Cr8_420 等)
- 深度/模板格式
- 专有压缩格式

**错误处理**:
```cpp
SkColorType colorType = GetSkColorTypeFromBufferFormat(format);
if (colorType == kUnknown_SkColorType) {
    // 格式不支持,需要使用外部图像机制
    colorType = kExternalFormatColorType;
}
```

## 内部实现细节

### 格式检测逻辑
函数内部使用 switch 语句匹配格式:
```cpp
switch (bufferFormat) {
    case AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM:
        return kRGBA_8888_SkColorType;
    case AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM:
        return kRGB_565_SkColorType;
    // ... 其他格式
    default:
        return kUnknown_SkColorType;
}
```

### AHardwareBuffer 格式枚举
Android NDK 定义的格式常量(部分):
- `AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM = 1`
- `AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM = 4`
- `AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT = 22`
- `AHARDWAREBUFFER_FORMAT_BLOB = 0x21` (不透明数据,非图像)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/core/SkColorType.h | 定义 SkColorType 枚举 |
| include/core/SkTypes.h | 基础类型定义 |
| android/hardware_buffer.h (NDK) | AHardwareBuffer API |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkImageAndroid | 从 AHardwareBuffer 创建 SkImage |
| SkSurfaceAndroid | 从 AHardwareBuffer 创建 SkSurface |
| GrAHardwareBufferUtils | GPU 后端使用格式信息创建纹理 |

## 设计模式与设计决策

### 纯工具函数设计
该模块仅包含静态工具函数,无类封装:
- 避免不必要的对象开销
- 函数可内联,性能最优
- 清晰表达"工具集"的性质

### 格式映射的保守策略
仅映射确定支持的格式,未知格式返回 `kUnknown_SkColorType`:
- 避免错误的类型转换导致渲染错误
- 明确区分"已知格式"和"外部格式"
- 上层可根据返回值选择处理路径

### 外部格式的统一抽象
将所有不可直接映射的格式归为"外部格式":
- GPU 通过扩展机制处理(EGL_ANDROID_image_native_buffer)
- 上层无需知道实际的 YUV 布局或压缩细节
- 简化 API 复杂度

## 性能考量

### 零开销抽象
- 函数极简,通常内联为数条汇编指令
- 无动态内存分配
- 无系统调用或锁操作

### 格式转换
- 该函数本身不执行像素转换,仅返回类型信息
- 实际转换由 GPU 在采样时完成(硬件加速)

## 典型使用场景

### 场景 1: 相机预览集成
```cpp
// 从相机获取 AHardwareBuffer
AHardwareBuffer* buffer = getCameraPreviewBuffer();
AHardwareBuffer_Desc desc;
AHardwareBuffer_describe(buffer, &desc);

// 确定颜色类型
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);
if (colorType == kUnknown_SkColorType) {
    // 使用外部格式(如 YUV)
    colorType = AHardwareBufferUtils::kExternalFormatColorType;
}

// 创建 Skia 图像
sk_sp<SkImage> image = SkImages::DeferredFromAHardwareBuffer(buffer, ...);
```

### 场景 2: 视频解码输出
```cpp
// MediaCodec 输出到 AHardwareBuffer
AHardwareBuffer* videoFrame = getDecodedFrame();
AHardwareBuffer_Desc desc;
AHardwareBuffer_describe(videoFrame, &desc);

// 视频帧通常是 YUV 格式,返回 kUnknown
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);
// colorType == kUnknown_SkColorType

// 使用外部格式机制
sk_sp<SkImage> frame = SkImages::DeferredFromAHardwareBuffer(
    videoFrame,
    kPremul_SkAlphaType,
    nullptr,
    kTopLeft_GrSurfaceOrigin
);
```

### 场景 3: GPU 渲染目标
```cpp
// 创建 RGBA8888 格式的 AHardwareBuffer 作为渲染目标
AHardwareBuffer_Desc desc = {
    .width = 1920,
    .height = 1080,
    .format = AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM,
    .usage = AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT |
             AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE,
};
AHardwareBuffer* buffer = allocateBuffer(&desc);

// 获取 Skia 颜色类型
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);
// colorType == kRGBA_8888_SkColorType

// 创建 SkSurface
sk_sp<SkSurface> surface = SkSurfaces::WrapAndroidHardwareBuffer(...);
```

## 平台相关说明

### Android 版本要求
- **最低**: Android 8.0(API 26)
- **推荐**: Android 10+(API 29),支持更多格式和优化
- **最新**: Android 12+(API 31),增加 AHARDWAREBUFFER_FORMAT_R8_UNORM 等

### 设备兼容性
- 所有 Android 8.0+ 设备必须支持 AHardwareBuffer
- 某些格式(如 R16G16B16A16_FLOAT)仅在高端设备上可用
- YUV 格式支持取决于设备 SoC 和驱动

### GPU 后端支持
- **Vulkan**: 通过 VK_ANDROID_external_memory_android_hardware_buffer 扩展
- **OpenGL ES**: 通过 EGL_ANDROID_image_native_buffer 扩展
- **Ganesh**: Skia 的 GPU 后端自动选择合适的扩展

## 限制与注意事项

### 格式限制
- 仅支持 RGB/RGBA 格式的直接映射
- YUV 格式需要通过外部图像机制处理
- 深度/模板格式不用于颜色渲染,不映射到 SkColorType

### Alpha 通道处理
```cpp
// R8G8B8X8_UNORM 的 Alpha 通道被忽略
SkColorType colorType = GetSkColorTypeFromBufferFormat(AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM);
// colorType == kRGB_888x_SkColorType (Alpha 始终为 1.0)
```

### HDR 格式支持
- 10-bit 和 16-bit 浮点格式需要设备硬件支持
- 需要配合宽色域色彩空间(Display P3、BT.2020)
- 显示器需要支持 HDR10+ 或 Dolby Vision

## 相关文件

| 文件 | 关系 |
|------|------|
| include/android/SkImageAndroid.h | 使用格式信息创建 SkImage |
| include/android/SkSurfaceAndroid.h | 使用格式信息创建 SkSurface |
| include/android/GrAHardwareBufferUtils.h | GPU 后端的 AHardwareBuffer 工具 |
| include/core/SkColorType.h | 颜色类型定义 |
| src/gpu/ganesh/android | Ganesh GPU 后端的 Android 适配实现 |

## 扩展阅读

### Android 官方文档
- AHardwareBuffer Reference
- Android Graphics Architecture
- EGL Extensions for Android

### Vulkan 扩展
- VK_ANDROID_external_memory_android_hardware_buffer
- VK_KHR_external_memory

### OpenGL ES 扩展
- EGL_ANDROID_image_native_buffer
- OES_EGL_image_external

## 最佳实践

### 格式选择建议
- **UI 渲染**: AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM(标准)
- **相机预览**: 使用设备原生格式,通过外部图像处理
- **HDR 内容**: AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT 或 R10G10B10A2_UNORM
- **性能优先**: AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM(较小内存占用)

### 错误处理
```cpp
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(format);
if (colorType == kUnknown_SkColorType) {
    // 方案 1: 使用外部图像
    colorType = AHardwareBufferUtils::kExternalFormatColorType;
    // GPU 将通过扩展处理

    // 方案 2: 转换格式
    // 创建新的 RGBA8888 buffer 并转换像素
}
```

### 性能优化
```cpp
// 避免不必要的格式查询
static const SkColorType kDefaultColorType =
    AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(
        AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM
    );
// 缓存常用格式的映射结果
```

### 线程安全
- `GetSkColorTypeFromBufferFormat` 是纯函数,线程安全
- 无全局状态,可在任意线程调用
- AHardwareBuffer 本身是线程安全的引用计数对象

## 未来展望

### 新格式支持
Android 未来版本可能添加:
- AHARDWAREBUFFER_FORMAT_R8_UNORM(单通道灰度)
- 更多 HDR 格式(如 PQ 编码的 10-bit)
- 压缩纹理格式(ASTC、ETC2)

### API 演进
- 可能增加格式能力查询函数
- 支持更复杂的格式协商机制
- 与 Android 13+ 的 AIDL HardwareBuffer API 集成
