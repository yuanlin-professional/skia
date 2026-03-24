# AHardwareBufferUtils

> 源文件: src/gpu/android/AHardwareBufferUtils.cpp

## 概述

`AHardwareBufferUtils` 是 Skia 为 Android 平台提供的硬件缓冲区工具模块，专门处理 Android `AHardwareBuffer` 格式与 Skia `SkColorType` 之间的映射转换。`AHardwareBuffer` 是 Android 提供的跨进程共享图像数据的原生 API，广泛用于摄像头、视频解码、传感器数据等场景的零拷贝传递。

该模块仅包含一个命名空间函数 `GetSkColorTypeFromBufferFormat`，负责将 `AHardwareBuffer` 的 32 位格式标识符转换为 Skia 的 `SkColorType` 枚举。这个转换是 Skia 与 Android 图形栈互操作的关键步骤，使得 Skia 能够正确解释和渲染来自 Android 系统的硬件缓冲区内容。

## 架构位置

```
skia/
├── include/android/
│   └── AHardwareBufferUtils.h    # 公共 API 头文件
├── src/gpu/android/
│   └── AHardwareBufferUtils.cpp  # 本模块实现
└── include/core/
    └── SkColorType.h             # Skia 颜色类型定义
```

该文件位于 `src/gpu/android/` 目录，是 Android 平台特定代码的一部分。它依赖 Android NDK 的 `<android/hardware_buffer.h>` 头文件，仅在 Android API 26（Android 8.0 Oreo）及以上版本编译。

## 主要类与结构体

### AHardwareBufferUtils 命名空间

**关键函数**:

| 函数签名 | 说明 |
|---------|------|
| `SkColorType GetSkColorTypeFromBufferFormat(uint32_t)` | 将硬件缓冲区格式转换为 Skia 颜色类型 |

### 支持的格式映射

该函数支持以下 `AHardwareBuffer` 格式到 `SkColorType` 的映射：

| AHardwareBuffer 格式 | SkColorType | API 要求 | 说明 |
|---------------------|-------------|---------|------|
| `AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM` | `kRGBA_8888_SkColorType` | API 26+ | 标准 RGBA 8 位/通道 |
| `AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM` | `kRGB_888x_SkColorType` | API 26+ | RGB 8 位/通道（忽略 Alpha） |
| `AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT` | `kRGBA_F16_SkColorType` | API 26+ | HDR 半精度浮点 RGBA |
| `AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM` | `kRGB_565_SkColorType` | API 26+ | 低精度 RGB（5-6-5 位） |
| `AHARDWAREBUFFER_FORMAT_R8G8B8_UNORM` | `kRGB_888x_SkColorType` | API 26+ | RGB 8 位/通道（映射到 888x） |
| `AHARDWAREBUFFER_FORMAT_R10G10B10A2_UNORM` | `kRGBA_1010102_SkColorType` | API 26+ | 高精度 RGB + 2 位 Alpha |
| `AHARDWAREBUFFER_FORMAT_R8_UNORM` | `kAlpha_8_SkColorType` | API 33+ | 单通道 8 位（Alpha 或灰度） |
| `AHARDWAREBUFFER_FORMAT_R10G10B10A10_UNORM` | `kRGBA_10x6_SkColorType` | API 34+ | 10 位/通道 RGBA（打包到 16 位） |
| 其他格式 | `kExternalFormatColorType` | - | 未知或外部格式 |

## 公共 API 函数

### GetSkColorTypeFromBufferFormat

```cpp
SkColorType GetSkColorTypeFromBufferFormat(uint32_t bufferFormat)
```

**功能**: 将 `AHardwareBuffer` 格式枚举转换为 `SkColorType`
**参数**: `bufferFormat` - 来自 `AHardwareBuffer_Desc::format` 的 32 位格式标识符
**返回**: 对应的 `SkColorType` 枚举值

**实现逻辑**:
```cpp
switch (bufferFormat) {
    case AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM:
        return kRGBA_8888_SkColorType;
    // ... 其他格式映射
    default:
        return kExternalFormatColorType;
}
```

**特殊处理**:
- **RGB 格式映射**: `R8G8B8_UNORM` 映射到 `RGB_888x`，因为 Skia 内部按 4 字节对齐处理
- **未知格式**: 返回 `kExternalFormatColorType`，表示格式不透明，Skia 将其视为外部纹理

## 内部实现细节

### 条件编译

整个实现被包裹在条件编译指令中：
```cpp
#if __ANDROID_API__ >= 26
// ... 实现代码
#endif
```

**原因**:
- `AHardwareBuffer` API 是 Android 8.0 (API 26) 引入的
- 旧版本 Android 不支持该 API，编译会失败
- 条件编译确保向后兼容性

### API 级别差异

不同格式支持的 API 级别：
- **API 26-32**: 支持基本格式（RGBA8, RGB565, F16 等）
- **API 33**: 新增 `R8_UNORM`（单通道）
- **API 34**: 新增 `R10G10B10A10_UNORM`（10 位/通道）

**实现策略**:
```cpp
#if __ANDROID_API__ >= 34
case AHARDWAREBUFFER_FORMAT_R10G10B10A10_UNORM:
    return kRGBA_10x6_SkColorType;
#endif
```

### 外部格式处理

对于 `default` 分支（未知格式），代码注释说明：
> "Given that we only use this texture as a source, colorType will not impact how Skia uses the texture."

**含义**:
- 外部格式通常绑定为 OES 纹理（OpenGL ES 扩展纹理）
- Skia 不直接解释像素内容，而是通过 GPU 采样
- `kExternalFormatColorType` 作为占位符，实际采样由 GPU 驱动处理

**潜在问题**:
- SKP（Skia Picture）回放时可能无法正确捕获纹理内容
- 如果尝试读取像素（`readPixels`），可能返回无效数据

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/android/AHardwareBufferUtils.h` | 公共 API 声明 |
| `<android/hardware_buffer.h>` | Android NDK 硬件缓冲区 API |
| `include/core/SkColorType.h` | Skia 颜色类型定义 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkImage::MakeFromAHardwareBuffer` | 从硬件缓冲区创建 Skia 图像 |
| `GrBackendTexture` | 包装硬件缓冲区为 GPU 纹理 |
| 摄像头预览渲染 | 将摄像头帧转换为 Skia 可渲染的图像 |
| 视频播放器 | 零拷贝视频帧渲染 |

## 设计模式与设计决策

### 设计模式

1. **适配器模式 (Adapter Pattern)**: 适配 Android 格式到 Skia 格式
2. **单一职责模式**: 仅负责格式转换，不涉及缓冲区管理
3. **命名空间封装**: 使用命名空间避免全局符号污染

### 设计决策

**为什么不支持所有 AHardwareBuffer 格式？**
- **硬件限制**: 某些格式（如 YUV）需要特殊采样器，Skia 不直接支持
- **优先级**: 映射表覆盖最常见的 sRGB 和 HDR 格式
- **扩展性**: 通过 `kExternalFormatColorType` 兜底，未来可扩展

**为什么 R8G8B8 映射到 RGB_888x？**
- **内存对齐**: Skia 内部使用 32 位对齐的像素格式
- **性能**: 3 字节/像素的格式在 GPU 上访问效率低
- **兼容性**: RGB_888x 与大多数 GPU 纹理格式匹配

**为什么返回 kExternalFormatColorType 而非错误？**
- **容错性**: 允许使用未知格式的缓冲区作为纹理
- **灵活性**: GPU 驱动可能支持 Skia 未列举的格式
- **调试友好**: 与返回错误相比，提供了降级处理路径

**为什么不支持 YUV 格式？**
- **采样复杂性**: YUV 需要多平面采样和颜色空间转换
- **性能**: YUV 到 RGB 转换通常在 GPU shader 中完成
- **替代方案**: Android 提供 `AImageReader` 和 `MediaCodec` 处理 YUV

### Android 特定考虑

**与 Vulkan 集成**:
- `AHardwareBuffer` 可通过 `VK_ANDROID_external_memory_android_hardware_buffer` 扩展导入 Vulkan
- Skia 的 Vulkan 后端使用此映射来创建 `VkImage`

**与 OpenGL 集成**:
- 通过 `EGL_ANDROID_image_native_buffer` 扩展绑定为 `EGLImage`
- 再转换为 OpenGL 纹理（`GL_TEXTURE_EXTERNAL_OES`）

**跨进程共享**:
- `AHardwareBuffer` 支持通过 Binder IPC 传递文件描述符
- 多个进程可零拷贝访问同一缓冲区
- 此工具函数在接收端使用，解释共享的缓冲区格式

## 性能考量

### 零拷贝优势

使用 `AHardwareBuffer` 的性能收益：
- **避免内存拷贝**: 摄像头直接写入 GPU 可见内存
- **减少带宽**: 无需 CPU-GPU 数据传输
- **降低延迟**: 去除中间缓冲区，端到端延迟降低 10-30ms

### 格式转换开销

| 场景 | 开销 | 说明 |
|------|------|------|
| 直接匹配格式 | 无 | GPU 直接采样 |
| RGB → RGBA 转换 | 低 | GPU 可高效处理，约 0.1ms/帧 |
| YUV → RGB 转换 | 中 | 需要 shader 转换，约 1-2ms/帧 |
| 未知格式 | 不确定 | 依赖驱动实现 |

### 内存对齐

`RGB_888x` 的对齐收益：
- **SIMD 友好**: 4 字节对齐允许使用向量指令
- **GPU 缓存**: 与纹理缓存行对齐，减少缓存缺失
- **浪费**: 每像素额外 1 字节（25% 内存浪费）

**权衡**:
- 对于 1080p 图像：1920×1080×1 = 2MB 额外内存
- 换来的性能提升通常值得（特别是实时渲染场景）

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/android/AHardwareBufferUtils.h` | 依赖 | 公共 API 头文件 |
| `include/core/SkColorType.h` | 依赖 | Skia 颜色类型定义 |
| `src/gpu/android/AndroidVulkanMemoryAllocator.cpp` | 同目录 | Vulkan 内存分配器（协同工作） |
| `src/image/SkImage_Android.cpp` | 使用 | 创建 `SkImage` 时调用此工具 |
| `src/gpu/ganesh/GrAHardwareBufferUtils.*` | 使用 | Ganesh 后端的硬件缓冲区集成 |

## 使用示例

### 示例 1: 从摄像头缓冲区创建 SkImage

```cpp
#include "include/android/AHardwareBufferUtils.h"
#include "include/core/SkImage.h"

// 假设从摄像头获取了 AHardwareBuffer
AHardwareBuffer* buffer = /* 从 ImageReader 获取 */;

// 查询缓冲区格式
AHardwareBuffer_Desc desc;
AHardwareBuffer_describe(buffer, &desc);

// 转换为 SkColorType
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);

// 创建 SkImage（伪代码，实际需要更多参数）
sk_sp<SkImage> image = SkImage::MakeFromAHardwareBuffer(
    buffer,
    kPremul_SkAlphaType,
    /* colorSpace */ nullptr,
    colorType
);

if (image) {
    // 使用图像进行渲染
    canvas->drawImage(image, 0, 0);
}
```

### 示例 2: 格式检查

```cpp
bool isSupportedFormat(uint32_t format) {
    SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(format);

    // kExternalFormatColorType 表示未知格式
    if (colorType == kExternalFormatColorType) {
        ALOGW("Unsupported AHardwareBuffer format: 0x%x", format);
        return false;
    }

    return true;
}
```

### 示例 3: HDR 内容检测

```cpp
bool isHDRBuffer(AHardwareBuffer* buffer) {
    AHardwareBuffer_Desc desc;
    AHardwareBuffer_describe(buffer, &desc);

    SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);

    // F16 或 1010102 格式通常用于 HDR 内容
    return (colorType == kRGBA_F16_SkColorType ||
            colorType == kRGBA_1010102_SkColorType);
}
```

### 示例 4: 跨进程缓冲区共享

```cpp
// 发送端（进程 A）
AHardwareBuffer* buffer = /* 创建缓冲区 */;
int fd = /* 从 buffer 获取文件描述符 */;
// 通过 Binder 将 fd 发送到进程 B

// 接收端（进程 B）
int fd = /* 从 Binder 接收 */;
AHardwareBuffer* buffer = /* 从 fd 重建 buffer */;

// 使用工具函数确定格式
AHardwareBuffer_Desc desc;
AHardwareBuffer_describe(buffer, &desc);
SkColorType colorType = AHardwareBufferUtils::GetSkColorTypeFromBufferFormat(desc.format);

// 现在可以在进程 B 中渲染来自进程 A 的内容
```

## 平台特性

### Android API 演进

| Android 版本 | API 级别 | 新增格式支持 |
|-------------|---------|-------------|
| 8.0 (Oreo) | 26 | AHardwareBuffer 基础 API |
| 13 (Tiramisu) | 33 | R8_UNORM（单通道） |
| 14 (Upside Down Cake) | 34 | R10G10B10A10_UNORM（10 位） |

### 硬件兼容性

不同 GPU 厂商对格式的支持：
- **Qualcomm (Adreno)**: 全面支持，包括 10 位格式
- **ARM (Mali)**: 支持大多数格式，部分旧款不支持 10 位
- **Imagination (PowerVR)**: 基础格式支持良好
- **Samsung (Exynos)**: 因使用 Mali 或自研 GPU，支持度不一

### 使用建议

**推荐格式**:
1. **标准内容**: `R8G8B8A8_UNORM`（最广泛支持）
2. **HDR 内容**: `R16G16B16A16_FLOAT`（半精度浮点）
3. **高效率**: `R5G6B5_UNORM`（低内存，适合 UI）

**避免格式**:
- 专有或未文档化的格式
- YUV 格式（Skia 不直接支持）

## 总结

`AHardwareBufferUtils.cpp` 是 Skia 与 Android 图形栈互操作的关键桥梁：
- **仅 49 行代码**，却支撑着 Skia 在 Android 上的零拷贝图像渲染
- **覆盖主流格式**，满足从标准 sRGB 到 HDR 的各种场景
- **向后兼容**，通过条件编译支持不同 Android 版本
- **容错设计**，对未知格式提供降级处理

对于 Android 平台的 Skia 开发者，理解此模块有助于：
- 正确配置摄像头和视频解码输出格式
- 优化跨进程图像共享性能
- 调试格式不匹配导致的渲染问题
