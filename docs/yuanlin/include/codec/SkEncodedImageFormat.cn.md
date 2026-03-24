# SkEncodedImageFormat

> 源文件: `include/codec/SkEncodedImageFormat.h`

## 概述

SkEncodedImageFormat 是 Skia 中用于标识编码图像格式的核心枚举类型。它为图像解码、编码和格式检测提供了统一的类型标识符,支持从常见的 JPEG、PNG 到现代的 AVIF、JPEG XL 等十余种格式,是 Skia 多格式图像处理能力的基础。

## 架构位置

该模块位于 Skia Codec 子系统的最顶层,为整个图像编解码框架提供格式类型定义。它被 SkCodec、SkEncoder 以及格式检测模块广泛使用,是连接上层 API 和底层编解码实现的关键枚举。

## 枚举定义

### SkEncodedImageFormat

描述编码图像数据的格式类型。

**支持的格式**:

| 枚举值 | 格式名称 | 说明 |
|--------|----------|------|
| kBMP | Windows Bitmap | Windows 标准位图格式,支持多种压缩方式 |
| kGIF | Graphics Interchange Format | 支持动画的索引色图像格式,最多 256 色 |
| kICO | Windows Icon | Windows 图标格式,可包含多尺寸图像 |
| kJPEG | JPEG/JPG | 有损压缩格式,广泛用于照片存储 |
| kPNG | Portable Network Graphics | 无损压缩格式,支持透明度,Web 常用 |
| kWBMP | Wireless Bitmap | WAP 协议中使用的单色位图格式 |
| kWEBP | WebP | Google 开发的现代图像格式,支持有损/无损及动画 |
| kPKM | ETC1 Compressed | OpenGL ES 纹理压缩格式 ETC1 |
| kKTX | Khronos Texture | Khronos 组织定义的 GPU 纹理容器格式 |
| kASTC | Adaptive Scalable Texture Compression | ARM 开发的高效纹理压缩格式 |
| kDNG | Digital Negative | Adobe 定义的 RAW 图像格式 |
| kHEIF | High Efficiency Image Format | 基于 HEVC 的高效图像格式,Apple 设备常用 |
| kAVIF | AV1 Image File Format | 基于 AV1 视频编解码器的次世代图像格式 |
| kJPEGXL | JPEG XL | 新一代通用图像格式,旨在替代 JPEG |

## 设计模式与设计决策

### 简洁枚举设计
该枚举采用最简形式,仅包含格式标识符,不携带额外元数据。这种设计:
- **解耦性强**: 格式属性(如是否支持动画、是否有损)由对应的 Codec 实现提供
- **扩展灵活**: 添加新格式仅需增加枚举值,不影响现有代码
- **性能优异**: 枚举比较为常数时间操作,适合高频调用场景

### 无版本化设计
枚举值不区分格式版本(如 JPEG 不区分 baseline/progressive),版本细节由解码器内部处理。这简化了上层 API,用户无需关心格式子类型。

### 命名约定
- 使用常见缩写(JPEG、PNG)而非完整名称,提升代码可读性
- 纹理格式(PKM、KTX、ASTC)保留原始大写,与 GPU 规范一致
- 新格式(AVIF、JPEGXL)采用社区通用名称

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| stdint.h | 提供固定宽度整数类型(虽然此枚举未直接使用,但为保持一致性包含) |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 在创建解码器时返回对应格式类型 |
| SkEncoder | 编码时指定输出格式 |
| SkAndroidCodec | Android 扩展解码器使用格式信息 |
| SkData | 从数据流检测格式类型 |
| SkImageGenerator | 根据格式选择生成器实现 |

## 典型使用场景

### 格式检测
```cpp
// 检测图像数据格式
SkEncodedImageFormat format = SkCodec::GetEncodedFormat(data);
if (format == SkEncodedImageFormat::kJPEG) {
    // 针对 JPEG 进行特殊处理
}
```

### 解码器选择
```cpp
// 根据格式创建对应解码器
std::unique_ptr<SkCodec> codec = SkCodec::MakeFromData(data);
if (codec->getEncodedFormat() == SkEncodedImageFormat::kGIF) {
    // 处理 GIF 动画
    int frameCount = codec->getFrameCount();
}
```

### 编码格式指定
```cpp
// 编码为 PNG 格式
SkFILEWStream stream("output.png");
SkPngEncoder::Encode(&stream, pixmap, options);
// 对应枚举值为 SkEncodedImageFormat::kPNG
```

## 格式支持状态

### 完全支持(解码+编码)
- **kJPEG**: 标准 JPEG,包括渐进式和优化 Huffman
- **kPNG**: 支持所有 PNG 标准特性
- **kWEBP**: 有损/无损/动画三种模式

### 仅解码支持
- **kBMP**: 支持多种压缩类型(RLE4/RLE8/Bitfields)
- **kGIF**: 包括 GIF89a 动画和透明度
- **kICO**: 可包含 BMP 或 PNG 子图像
- **kWBMP**: 简单的单色格式
- **kDNG**: 通过 libraw 支持
- **kHEIF**: 需要系统编解码器支持
- **kAVIF**: 通过 libavif 或 dav1d 支持
- **kJPEGXL**: 通过 libjxl 支持

### 纹理格式(通常不解码,直接上传 GPU)
- **kPKM**: ETC1 压缩纹理
- **kKTX**: 可包含多种 GPU 压缩格式
- **kASTC**: 高质量纹理压缩

## 性能考量

### 格式检测开销
格式检测通常通过读取文件头魔数(前 8-16 字节)实现:
- **快速检测**: JPEG(`0xFF 0xD8`)、PNG(`89 50 4E 47`)等前缀明确
- **复杂检测**: ICO 和 BMP 头部相似,需要更多字节判断
- **流式优化**: 检测逻辑避免读取整个文件,适合网络流场景

### 解码性能差异
不同格式的解码性能差异显著:
- **硬件加速**: JPEG/HEIF 在移动设备上通常有硬件支持
- **纯软件**: GIF/BMP 解码简单但不支持硬件加速
- **计算密集**: AVIF/JPEGXL 压缩率高但解码复杂度大

## 平台相关说明

### Android 特殊支持
- **HEIF**: Android 9+ 原生支持,通过 MediaCodec API
- **AVIF**: Android 12+ 官方支持
- **硬件解码**: JPEG/WebP 可能使用硬件加速器

### iOS/macOS 特殊支持
- **HEIF**: 系统级支持,性能优异
- **AVIF**: macOS 11+/iOS 16+ 开始支持
- **DNG**: 通过 CoreImage 支持

### Web 平台
- **WASM 构建**: 纹理格式(PKM/KTX/ASTC)通常在 Web 构建中禁用
- **WebP**: 现代浏览器原生支持,可直接使用浏览器解码器

## 扩展性

### 添加新格式流程
1. 在枚举中添加新值(如 `kJXL`)
2. 实现对应的 `SkXXXCodec` 类
3. 在 `SkCodec::MakeFromStream` 中添加格式检测逻辑
4. 更新格式检测表(`gDecoderProcs`)

### 插件化支持
部分格式(如 AVIF)通过编译时开关控制:
```cpp
#ifdef SK_CODEC_DECODES_AVIF
    case SkEncodedImageFormat::kAVIF:
        return "AVIF";
#endif
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/codec/SkCodec.h | 使用该枚举作为 `getEncodedFormat()` 返回值 |
| include/encode/SkEncoder.h | 编码器基类,指定输出格式 |
| include/encode/SkPngEncoder.h | PNG 编码器,对应 kPNG |
| include/encode/SkJpegEncoder.h | JPEG 编码器,对应 kJPEG |
| include/encode/SkWebpEncoder.h | WebP 编码器,对应 kWEBP |
| src/codec/SkCodec.cpp | 实现格式检测和解码器工厂方法 |
| include/codec/SkJpegDecoder.h | JPEG 解码器接口 |
| include/codec/SkGifDecoder.h | GIF 解码器接口 |

## 最佳实践

### 格式选择建议
- **照片**: 使用 JPEG(有损)或 PNG(无损)
- **UI 图标**: PNG 或 WebP
- **动画**: GIF(简单场景)或 WebP(高质量)
- **次世代**: AVIF(高压缩率)或 JPEGXL(全能型)
- **游戏纹理**: ASTC(移动端)或 KTX(桌面端)

### 兼容性处理
```cpp
// 检查格式是否支持
bool isSupported = SkCodec::IsFormatSupported(format);
if (!isSupported) {
    // 回退到通用格式
    encodeAsPng(image);
}
```
