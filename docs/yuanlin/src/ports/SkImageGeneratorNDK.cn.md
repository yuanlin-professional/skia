# SkImageGeneratorNDK

> 源文件: include/ports/SkImageGeneratorNDK.h, src/ports/SkImageGeneratorNDK.cpp

## 概述

SkImageGeneratorNDK 是 Skia 图形库为 Android 平台提供的图像解码器实现，基于 Android NDK 的 AImageDecoder API（API Level 30+）。它将 Android 原生图像解码能力集成到 Skia 的 SkImageGenerator 框架中，支持 JPEG 和 WebP 格式的硬件加速解码、缩放采样和色彩空间转换。该模块提供了比传统编解码器更高效的平台原生解码路径。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 Android NDK 提供图像生成功能：

```
skia/
├── include/ports/
│   └── SkImageGeneratorNDK.h       # 公共接口
└── src/ports/
    ├── SkImageGeneratorNDK.cpp     # 实现
    └── SkNDKConversions.h          # NDK 类型转换工具
```

该模块仅在定义 `SK_ENABLE_NDK_IMAGES` 宏且 Android API Level >= 30 时可用。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `ImageGeneratorNDK` | `SkImageGenerator` | 封装 AImageDecoder 的图像生成器 |

### 关键成员变量

**ImageGeneratorNDK:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `sk_sp<const SkData>` | 编码图像的原始数据 |
| `fDecoder` | `AImageDecoder*` | Android 原生解码器实例 |
| `fPreviouslySetADataSpace` | `bool` | 标记是否曾设置色彩空间（用于重置逻辑） |

## 公共 API 函数

### 工厂函数

```cpp
namespace SkImageGeneratorNDK {
    SK_API std::unique_ptr<SkImageGenerator> MakeFromEncodedNDK(sk_sp<const SkData>);
}
```

从编码的图像数据创建 NDK 图像生成器。支持平台原生支持的所有图像格式，但返回的生成器主要优化了 JPEG 和 WebP。

**缩放支持说明**:
- **WebP**: 支持任意小于原始尺寸的缩放
- **JPEG**: 支持 1/2、1/4、1/8 采样比例
- 调用 `getPixels()` 时可请求不同尺寸，生成器将自动处理缩放

### SkImageGenerator 接口实现

```cpp
protected:
    sk_sp<const SkData> onRefEncodedData() override;
    bool onGetPixels(const SkImageInfo& info, void* pixels,
                     size_t rowBytes, const Options& opts) override;
```

## 内部实现细节

### 解码器初始化

`MakeFromEncodedNDK` 执行以下初始化流程：

1. **创建解码器**:
   ```cpp
   AImageDecoder_createFromBuffer(data->data(), data->size(), &rawDecoder);
   ```

2. **查询图像属性**:
   ```cpp
   const AImageDecoderHeaderInfo* headerInfo = AImageDecoder_getHeaderInfo(rawDecoder);
   int32_t width  = AImageDecoderHeaderInfo_getWidth(headerInfo);
   int32_t height = AImageDecoderHeaderInfo_getHeight(headerInfo);
   ```

3. **确定颜色类型**: 尝试设置 `kGray_8_SkColorType`，若失败则使用默认格式
4. **确定透明度类型**: 根据 `ANDROID_BITMAP_FLAGS_ALPHA_OPAQUE` 标志选择 `kOpaque` 或 `kPremul`
5. **提取色彩空间**: 从 `ADataSpace` 转换为 `SkColorSpace`

### 色彩空间转换

色彩空间处理逻辑分三种情况：

1. **指定色彩空间**: 调用 `AImageDecoder_setDataSpace` 应用转换
2. **nullptr 色彩空间（原始颜色）**: 需要重置到默认 ADataSpace
3. **ADATASPACE_UNKNOWN**: 由于 API 限制，需要重新创建解码器

关键代码：
```cpp
if (defaultDataSpace == ADATASPACE_UNKNOWN) {
    // R 版本无法重置到 UNKNOWN，需要重建解码器
    AImageDecoder_createFromBuffer(fData->data(), fData->size(), &decoder);
    AImageDecoder_delete(fDecoder);
    fDecoder = decoder;
}
```

### 缩放支持

`set_target_size` 函数实现智能缩放验证：

```cpp
static bool set_target_size(AImageDecoder* decoder, const SkISize& size, const SkISize targetSize) {
    if (size != targetSize) {
        const char* mimeType = AImageDecoderHeaderInfo_getMimeType(headerInfo);
        if (0 == strcmp(mimeType, "image/jpeg")) {
            // JPEG 仅支持 2、4、8 倍采样
            for (int sampleSize : { 2, 4, 8 }) {
                // 验证计算出的采样尺寸是否匹配目标
            }
        } else if (0 == strcmp(mimeType, "image/webp")) {
            // WebP 支持任意缩小比例
            if (targetSize.width() > size.width() || targetSize.height() > size.height()) {
                return false;
            }
        }
    }
    return ok(AImageDecoder_setTargetSize(decoder, targetSize.width(), targetSize.height()));
}
```

### 像素格式处理

`set_android_bitmap_format` 转换 Skia 色彩类型到 Android 格式：

- `kGray_8_SkColorType` → 灰度格式（如果图像支持）
- `kN32_SkColorType` → 默认 RGBA 格式

透明度处理：
- `kUnpremul_SkAlphaType`: 调用 `AImageDecoder_setUnpremultipliedRequired(true)`
- `kPremul_SkAlphaType`: 使用 AImageDecoder 默认预乘行为
- `kOpaque_SkAlphaType`: 验证图像本身无透明度

### 解码执行

`onGetPixels` 方法执行实际解码：

```cpp
bool ImageGeneratorNDK::onGetPixels(const SkImageInfo& info, void* pixels,
                                    size_t rowBytes, const Options& opts) {
    // 1. 设置色彩空间
    // 2. 设置位图格式
    // 3. 设置透明度类型
    // 4. 设置目标尺寸（如果需要缩放）
    // 5. 执行解码
    switch (AImageDecoder_decodeImage(fDecoder, pixels, rowBytes, byteSize)) {
        case ANDROID_IMAGE_DECODER_INCOMPLETE:  // 部分解码
        case ANDROID_IMAGE_DECODER_ERROR:       // 错误但有部分数据
        case ANDROID_IMAGE_DECODER_SUCCESS:
            return true;
        default:
            return false;
    }
}
```

对于部分解码和错误情况，仍然返回 true，允许客户端使用不完整的图像数据。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| Android NDK `<android/imagedecoder.h>` | 原生图像解码 API |
| Android NDK `<android/bitmap.h>` | 位图格式定义 |
| Android NDK `<android/data_space.h>` | 色彩空间定义 |
| `SkNDKConversions` | Skia 与 NDK 类型转换 |
| `SkImageInfo` | 图像元数据描述 |

### 被依赖的模块

该模块通过 SkCodec 框架被 SkImage、SkBitmap 等高层 API 使用，作为 Android 平台优先的图像解码路径。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeFromEncodedNDK` 静态工厂方法创建生成器
2. **适配器模式**: 将 AImageDecoder API 适配到 SkImageGenerator 接口
3. **策略模式**: 根据 MIME 类型选择不同的缩放验证策略

### 设计决策

1. **平台优先**: 优先使用 Android 硬件加速解码器，性能优于软件解码
2. **懒解码**: SkImageGenerator 框架支持延迟解码，节省内存
3. **色彩空间感知**: 支持 Android 色彩管理，可应用或跳过色彩转换
4. **格式限制**: 仅支持 NDK 提供的格式，但涵盖常用的 JPEG、PNG、WebP、GIF 等
5. **错误容忍**: 部分解码失败时仍返回可用数据，提高鲁棒性
6. **解码器重用**: 保持 AImageDecoder 实例，支持多次调用 `getPixels`

### API Level 考虑

- **最低版本**: Android 11 (API 30)
- **特性依赖**: AImageDecoder 在 API 30 引入，早期版本回退到其他编解码器
- **版本适配**: 通过编译时宏 `SK_ENABLE_NDK_IMAGES` 控制功能可用性

## 性能考量

### 性能优势

1. **硬件加速**: AImageDecoder 可利用 Android 设备的硬件解码器（如 MediaCodec）
2. **零拷贝路径**: 某些格式可直接解码到目标缓冲区，避免中间拷贝
3. **平台优化**: Android 系统针对移动设备优化的解码实现
4. **采样解码**: JPEG 采样解码在解码时直接缩小，比解码后缩放更快

### 缩放性能

- **JPEG 1/8 采样**: 比完整解码后缩小快约 64 倍（理论值）
- **WebP 任意缩放**: 解码时缩放比事后缩放节省内存和计算

### 内存优化

1. **按需解码**: 只有调用 `getPixels` 时才执行解码
2. **直接输出**: 解码直接写入调用者提供的缓冲区
3. **数据共享**: `fData` 使用引用计数共享原始数据

### 潜在瓶颈

- **首次解码开销**: 创建 AImageDecoder 和查询头信息有一定成本
- **色彩空间转换**: 某些色彩空间转换可能在 GPU 上更快
- **解码器重建**: 切换到 ADATASPACE_UNKNOWN 时需要重建解码器

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkImageGeneratorNDK.h` | 公共接口定义 |
| `src/ports/SkImageGeneratorNDK.cpp` | 实现文件 |
| `src/ports/SkNDKConversions.h` | NDK 类型转换工具 |
| `include/core/SkImageGenerator.h` | 图像生成器抽象基类 |
| `include/core/SkImageInfo.h` | 图像信息描述 |
| `include/core/SkData.h` | 数据容器 |
| Android NDK `imagedecoder.h` | 原生解码 API |
