# SkAvifDecoder

> 源文件: `include/codec/SkAvifDecoder.h`

## 概述

SkAvifDecoder 提供 AVIF(AV1 Image File Format)图像格式的解码能力。AVIF 是基于 AV1 视频编解码器的次世代图像格式,相比 JPEG 可节省约 50% 文件大小,同时支持 HDR、动画和无损压缩。该模块为 Skia 提供了最先进的图像格式支持,是面向未来的图像处理能力的重要组成部分。

## 架构位置

SkAvifDecoder 位于 Skia Codec 子系统,实现 SkCodec 抽象接口。它提供两种后端实现:LibAvif(官方参考库)和 CrabbyAvif(Rust 实现),为上层提供统一的 AVIF 访问接口。该模块代表了 Skia 对新兴图像格式的支持策略。

## 命名空间结构

SkAvifDecoder 采用三层命名空间结构:

```
SkAvifDecoder
├── LibAvif (官方 C 实现)
│   ├── IsAvif()
│   ├── Decode()
│   └── Decoder()
├── CrabbyAvif (Rust 实现)
│   ├── IsAvif()
│   ├── Decode()
│   └── Decoder()
└── Decoder() (默认路由到 LibAvif)
```

## LibAvif 命名空间

### `LibAvif::IsAvif`

检测数据是否为 AVIF 格式(使用 libavif 实现)。

```cpp
SK_API bool IsAvif(const void* data, size_t length)
```

**功能**: 通过检查 AVIF/HEIF 容器头识别格式。

**参数**:
- `data`: 待检测数据的指针
- `length`: 数据长度(字节)

**返回值**:
- `true`: 数据符合 AVIF 文件结构
- `false`: 非 AVIF 格式

**检测逻辑**:
- AVIF 基于 ISO BMFF(Base Media File Format)容器
- 文件头包含 "ftyp" box,brand 为 "avif"、"avis"(序列)等
- 最少需要 12 字节进行检测

### `LibAvif::Decode` (SkStream 版本)

使用 libavif 从输入流解码 AVIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    std::unique_ptr<SkStream> stream,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `stream`: 输入数据流,解码器获取所有权
- `result`: 输出参数,返回解码结果状态
- `context`: 解码上下文(当前版本忽略)

**返回值**:
- 成功: 返回 SkCodec 智能指针
- 失败: 返回 `nullptr`,`result` 设为错误码

**支持的 AVIF 特性**:
- 单帧和多帧(动画)AVIF
- 10-bit 和 12-bit 色深
- HDR(高动态范围)图像
- 宽色域(BT.2020、Display P3 等)
- 有损和无损压缩
- Alpha 通道

### `LibAvif::Decode` (SkData 版本)

使用 libavif 从内存数据块解码 AVIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    sk_sp<const SkData> data,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**参数**:
- `data`: 包含完整 AVIF 数据的智能指针
- `result`: 输出参数,返回解码状态
- `context`: 解码上下文(当前忽略)

### `LibAvif::Decoder`

返回 libavif 解码器描述符。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**返回值**: 包含 "avif", IsAvif, Decode 的结构体。

## CrabbyAvif 命名空间

### `CrabbyAvif::IsAvif`

检测数据是否为 AVIF 格式(使用 CrabbyAvif 实现)。

```cpp
SK_API bool IsAvif(const void* data, size_t length)
```

**功能**: 与 LibAvif::IsAvif 相同,但使用 Rust 实现的后端。

### `CrabbyAvif::Decode` (SkStream 版本)

使用 CrabbyAvif 从输入流解码 AVIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    std::unique_ptr<SkStream> stream,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

### `CrabbyAvif::Decode` (SkData 版本)

使用 CrabbyAvif 从内存数据块解码 AVIF 图像。

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    sk_sp<const SkData> data,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

### `CrabbyAvif::Decoder`

返回 CrabbyAvif 解码器描述符。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

## 根命名空间

### `SkAvifDecoder::Decoder`

默认解码器工厂方法,路由到 LibAvif 实现。

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**功能**: 为向后兼容性提供默认实现,内部调用 `LibAvif::Decoder()`。

**设计原因**: 允许用户无需关心后端选择,使用统一接口。

## 内部实现细节

### AVIF 文件结构
```
ftyp box (File Type)
    major_brand: "avif"
    compatible_brands: ["avif", "mif1", ...]

meta box (Metadata)
    hdlr: "pict" (图片处理器)
    pitm: 主图像项 ID
    iinf: 图像项信息
    iprp: 图像属性(尺寸、变换等)
    idat/iloc: 图像数据位置

mdat box (Media Data)
    AV1 编码的图像数据
```

### AV1 解码
AVIF 使用 AV1 视频编解码器的帧内编码(Intra-frame):
- **无损模式**: 类似 PNG,但压缩率更高
- **有损模式**: 类似 JPEG,但相同质量下文件小 50%
- **编码工具**: 支持 4x4 到 128x128 的块分割,10+ 种预测模式

### 色彩空间处理
AVIF 原生支持广色域:
- **SDR**: sRGB、Display P3
- **HDR**: BT.2020、PQ(Perceptual Quantizer)、HLG(Hybrid Log-Gamma)
- **位深**: 8-bit、10-bit、12-bit

### 后端选择策略
Skia 支持两种 AVIF 后端:
- **LibAvif**: 官方 C 实现,兼容性最好,依赖 dav1d(解码器)和 librav1e/libaom(编码器)
- **CrabbyAvif**: Rust 实现,内存安全性更强,性能与 LibAvif 相当

编译时通过宏控制:
```cpp
#ifdef SK_CODEC_DECODES_AVIF_LIBAVIF
    // 使用 LibAvif
#elif defined(SK_CODEC_DECODES_AVIF_CRABBY)
    // 使用 CrabbyAvif
#endif
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| include/codec/SkCodec.h | SkCodec 基类定义 |
| include/core/SkRefCnt.h | 智能指针支持 |
| include/private/base/SkAPI.h | 导出宏 SK_API |
| libavif | 官方 AVIF 解码库 |
| dav1d | 高性能 AV1 解码器 |
| rav1e / libaom | AV1 编码器(可选) |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkCodec | 通过工厂方法创建 AVIF 解码器 |
| SkImage | 从 AVIF 数据创建图像 |
| Web 应用 | 显示 AVIF 格式的网络图片 |
| 现代应用 | 利用 AVIF 减少存储和带宽 |

## 设计模式与设计决策

### 多后端策略模式
提供两个独立后端,用户可根据需求选择:
- **LibAvif**: 稳定性优先,生态成熟
- **CrabbyAvif**: 安全性优先,避免内存漏洞

### 命名空间隔离
不同后端使用独立命名空间,避免符号冲突:
- 可在同一程序中链接两个后端(虽然不常见)
- 清晰表达 API 的后端归属

### 默认路由设计
根命名空间的 `Decoder()` 提供默认实现:
- 新用户无需了解后端细节
- 老代码无需修改即可使用 AVIF

## 性能考量

### 解码速度
AVIF 解码比 JPEG 慢,因为 AV1 编码复杂:
- **JPEG 解码**(1920x1080): ~15ms
- **AVIF 解码**(同尺寸): ~100-300ms
- **硬件加速**: 新一代芯片(Apple M2、Snapdragon 8 Gen 2 等)开始支持 AV1 硬解

### 内存占用
- 解码器对象: ~1 KB
- AV1 解码器状态: ~10-50 MB(取决于图像尺寸)
- 帧缓冲区: width * height * 8 字节(10-bit 图像)

### 文件大小对比
以 1920x1080 照片为例:
- **JPEG**(质量 80): ~300 KB
- **AVIF**(相同感知质量): ~150 KB(节省 50%)
- **PNG**(无损): ~2 MB
- **AVIF 无损**: ~800 KB(节省 60%)

## 典型使用场景

### 场景 1: 解码 AVIF 图片
```cpp
sk_sp<SkData> data = loadFromNetwork("image.avif");
SkCodec::Result result;

// 使用默认后端
auto codec = SkAvifDecoder::Decode(data, &result);

// 或显式指定 LibAvif
auto codec = SkAvifDecoder::LibAvif::Decode(data, &result);

if (codec) {
    SkImageInfo info = codec->getInfo();
    SkBitmap bitmap;
    bitmap.allocPixels(info);
    codec->getPixels(info, bitmap.getPixels(), bitmap.rowBytes());
}
```

### 场景 2: 处理 HDR AVIF
```cpp
auto codec = SkAvifDecoder::Decode(stream, &result);
SkImageInfo info = codec->getInfo();

// 检查是否为 HDR 图像
if (info.colorType() == kRGBA_F16_SkColorType) {
    // 10-bit 或 12-bit HDR 图像
    // 需要 HDR 显示器和色彩管理
}

// 获取色彩空间
sk_sp<SkColorSpace> colorSpace = info.refColorSpace();
if (colorSpace->gammaIsLinear()) {
    // 线性色彩空间(HDR)
}
```

### 场景 3: 动画 AVIF
```cpp
auto codec = SkAvifDecoder::Decode(data, &result);
int frameCount = codec->getFrameCount();

if (frameCount > 1) {
    // 动画 AVIF(较少见,但规范支持)
    for (int i = 0; i < frameCount; ++i) {
        SkCodec::Options options;
        options.fFrameIndex = i;
        codec->getPixels(info, pixels, rowBytes, &options);
    }
}
```

## 边界情况处理

### 不支持的 AV1 配置
某些高级 AV1 特性可能不支持:
- 返回 `kUnimplemented` 错误
- 例如:Film Grain Synthesis 等实验性特性

### 超高分辨率
AVIF 规范支持 8K 甚至更高分辨率:
- 解码可能需要数秒
- 内存占用可能超过 1 GB
- 建议在移动设备上限制最大尺寸

### 损坏的文件
- AV1 数据损坏: 返回 `kIncompleteInput` 或 `kInvalidInput`
- 容器损坏: 返回 `kInvalidInput`

## 平台相关说明

### Android
- **Android 12+**: 系统原生支持 AVIF(通过 ImageDecoder API)
- **硬件加速**: Snapdragon 8 Gen 2+ 支持 AV1 硬解
- **兼容性**: 旧版本需要软件解码

### iOS/macOS
- **iOS 16+ / macOS Ventura+**: 系统原生支持 AVIF
- **硬件加速**: M2 及更新的芯片支持 AV1 硬解
- **Safari**: 支持 AVIF 图片显示

### Web 浏览器
- **Chrome 85+**: 完全支持 AVIF
- **Firefox 93+**: 默认启用 AVIF
- **Safari 16+**: 支持 AVIF
- **Edge 92+**: 基于 Chromium,支持 AVIF

## 限制与注意事项

### 编码器依赖
虽然本头文件仅声明解码器,但实际应用中:
- 编码 AVIF 需要 rav1e 或 libaom
- 编码速度极慢(可能数分钟,取决于质量设置)
- 建议使用预编码工具链

### 专利问题
AV1 由 Alliance for Open Media 开发,承诺免专利费:
- 无需支付许可费用
- 但某些国家可能有专利诉讼风险

### 浏览器支持
虽然主流浏览器已支持,但需考虑兼容性:
- 提供 JPEG 或 WebP 回退
- 使用 `<picture>` 标签多源策略

## 性能优化建议

### 解码优化
```cpp
// 对于缩略图,使用缩放解码
SkImageInfo scaledInfo = info.makeWH(width / 4, height / 4);
codec->getPixels(scaledInfo, pixels, rowBytes);
// 比全尺寸解码后再缩放快得多
```

### 异步解码
```cpp
// AVIF 解码慢,应在后台线程执行
std::async(std::launch::async, [data]() {
    SkCodec::Result result;
    auto codec = SkAvifDecoder::Decode(data, &result);
    // 解码完成后通知主线程
});
```

### 缓存策略
- 缓存已解码的 SkBitmap,避免重复解码
- 对于动画 AVIF,缓存关键帧

## 相关文件

| 文件 | 关系 |
|------|------|
| src/codec/SkAvifCodec.cpp | AVIF 解码器实现 |
| third_party/libavif | libavif 库源码 |
| third_party/dav1d | dav1d AV1 解码器 |
| include/codec/SkCodec.h | 解码器基类接口 |
| include/encode/SkAvifEncoder.h | AVIF 编码器(如果存在) |

## 扩展阅读

### AVIF 规范
- AVIF Specification v1.0.0
- ISO/IEC 23000-22:2019 (MIAF)
- AV1 Bitstream & Decoding Process Specification

### 工具链
- **libavif**: 官方编解码库
- **avifenc/avifdec**: 命令行工具
- **Squoosh**: Google 的在线图像压缩工具

### 性能测试
- Netflix AVIF 性能测试报告
- AV1 vs HEVC vs VP9 压缩对比

## 最佳实践

### 格式选择
- **网络图片**: 优先使用 AVIF,提供 WebP/JPEG 回退
- **存档**: AVIF 无损模式比 PNG 小
- **HDR 内容**: AVIF 是目前最好的 HDR 图像格式

### 质量设置
- **高质量**: CRF 23-28(类似 JPEG 90-95)
- **平衡**: CRF 28-32(类似 JPEG 80-90)
- **小文件**: CRF 32-40(类似 JPEG 60-80)

### 兼容性策略
```html
<!-- Web 中使用 -->
<picture>
  <source srcset="image.avif" type="image/avif">
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="fallback">
</picture>
```

### 线程安全
- `IsAvif` 函数线程安全
- 单个解码器实例不可跨线程使用
- 可在不同线程创建多个解码器实例
