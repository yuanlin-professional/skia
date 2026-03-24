# src/encode - 图像编码模块

## 概述

`src/encode` 目录是 Skia 图形库的图像编码子系统，负责将内存中的像素数据序列化为标准的图像文件格式。该模块支持三种主流的有损/无损图像格式：JPEG、PNG 和 WebP，每种格式都有独立的编码器实现。此外，该模块还包含了 ICC 颜色配置文件的生成功能以及 JPEG 增益图（Gainmap/HDR）编码的高级特性。

从设计层面看，该模块采用了分层架构。最上层是 `SkEncoder` 基类，定义了逐行编码（`encodeRows`）的通用接口；中间层是针对每种格式的具体编码器实现（`SkJpegEncoderImpl`、`SkPngEncoderImpl`/`SkPngRustEncoderImpl`、`SkWebpEncoderImpl`）；底层则依赖第三方压缩库（libjpeg-turbo、libpng/Rust png crate、libwebp）执行实际的数据压缩。特别值得注意的是，PNG 编码器提供了两套实现路径：基于 C 语言的 libpng 和基于 Rust 的 png crate，两者共享 `SkPngEncoderBase` 基类的公共逻辑。

编码模块还提供了灵活的构建时配置能力。通过 `*_none.cpp` 桩文件（stub），可以在不链接实际编码库的情况下编译 Skia，此时调用编码 API 会在调试模式下触发断言失败。这种设计使得 Skia 可以根据目标平台的需求选择性地包含编码支持，有效减小二进制体积。

ICC 配置文件生成（`SkICC.cpp`）是编码模块中一个相对独立但非常重要的组件。它支持生成符合 ICC v4.3/v4.4 标准的颜色配置文件，涵盖 sRGB、Display P3、Rec.2020 等常见色域，并能处理 PQ（感知量化）和 HLG（混合对数伽马）等 HDR 传输函数，包含完整的色调映射（Tone Mapping）算法和 CICP 标签支持。

## 架构图

```
                    +-------------------+
                    |  SkEncoder (基类)  |
                    | include/encode/   |
                    +--------+----------+
                             |
        +--------------------+--------------------+
        |                    |                    |
+-------+-------+   +-------+--------+   +-------+--------+
| SkJpegEncoder |   | SkPngEncoder   |   | SkWebpEncoder  |
| Impl          |   | Base           |   | Impl           |
+-------+-------+   +-------+--------+   +----------------+
        |                    |
        |           +--------+--------+
        |           |                 |
        |   +-------+--------+ +-----+----------+
        |   | SkPngEncoder   | | SkPngRust      |
        |   | Impl (libpng)  | | EncoderImpl    |
        |   +----------------+ | (Rust png)     |
        |                      +----------------+
        |
+-------+---------------+
| SkJpegGainmapEncoder  |
| (HDR增益图编码)        |
+------------------------+

辅助模块:
+--------------------+  +---------------------+  +--------------------+
| SkICC.cpp          |  | SkImageEncoderFns.h |  | SkICCPriv.h        |
| (ICC配置文件生成)   |  | (格式转换辅助函数)   |  | (ICC内部常量)       |
+--------------------+  +---------------------+  +--------------------+
+--------------------+  +---------------------+
| SkJPEGWriteUtility |  | SkImageEncoderPriv.h |
| (JPEG写入工具)      |  | (编码器验证辅助)     |
+--------------------+  +---------------------+

第三方库:
+------------------+  +------------------+  +------------------+
| libjpeg-turbo    |  | libpng           |  | libwebp          |
| (JPEG压缩)       |  | (PNG压缩)        |  | (WebP压缩)       |
+------------------+  +------------------+  +------------------+
                      +------------------+
                      | Rust png crate   |
                      | (PNG替代实现)     |
                      +------------------+
```

## 目录结构

```
src/encode/
├── BUILD.bazel                    # Bazel 构建规则，含条件编译逻辑
├── SkEncoder.cpp                  # SkEncoder 基类实现（encodeRows 逐行编码控制）
├── SkImageEncoderPriv.h           # 编码器私有工具（SkPixmapIsValid 验证函数）
├── SkImageEncoderFns.h            # 编码器公共辅助函数（ICC提取、Exif生成、扫描线变换）
│
├── SkJpegEncoderImpl.h            # JPEG 编码器头文件（含 SkJpegMetadataEncoder 元数据接口）
├── SkJpegEncoderImpl.cpp          # JPEG 编码器实现（RGB/YUV编码、元数据写入）
├── SkJpegEncoder_none.cpp         # JPEG 编码器桩文件（未链接 libjpeg 时使用）
├── SkJPEGWriteUtility.h           # JPEG 写入目标管理器头文件
├── SkJPEGWriteUtility.cpp         # JPEG 写入目标管理器实现（SkWStream 适配）
├── SkJpegGainmapEncoder.cpp       # JPEG HDR 增益图编码（HDRGM/UltraHDR 格式）
│
├── SkPngEncoderBase.h             # PNG 编码器基类头文件（共享于 libpng 和 Rust 实现）
├── SkPngEncoderBase.cpp           # PNG 编码器基类实现（像素格式转换、逐行编码逻辑）
├── SkPngEncoderImpl.h             # PNG 编码器 libpng 实现头文件
├── SkPngEncoderImpl.cpp           # PNG 编码器 libpng 实现
├── SkPngRustEncoder.cpp           # PNG Rust 编码器入口
├── SkPngRustEncoderImpl.h         # PNG Rust 编码器头文件
├── SkPngRustEncoderImpl.cpp       # PNG Rust 编码器实现（通过 CXX 桥接 Rust png crate）
├── SkPngEncoder_none.cpp          # PNG 编码器桩文件
│
├── SkWebpEncoderImpl.cpp          # WebP 编码器实现（静态图和动画编码、ICC嵌入）
├── SkWebpEncoder_none.cpp         # WebP 编码器桩文件
│
├── SkICC.cpp                      # ICC 颜色配置文件生成（支持 HDR/SDR、CICP、A2B/B2A）
├── SkICCPriv.h                    # ICC 内部常量定义（标签类型、色彩空间签名等）
```

## 关键类与函数

### SkEncoder（编码器基类）

定义在 `include/encode/SkEncoder.h` 中，提供逐行编码的控制框架。

```cpp
class SkEncoder {
public:
    bool encodeRows(int numRows);   // 编码指定行数（调用子类的 onEncodeRows）
protected:
    virtual bool onEncodeRows(int numRows) = 0;  // 纯虚：子类实现实际编码
    const SkPixmap& fSrc;  // 源像素数据
    int fCurrRow = 0;       // 当前已编码行号
};
```

### SkJpegEncoderImpl（JPEG 编码器）

支持 RGB 和 YUV 两种输入模式，通过 `SkJpegEncoderMgr` 管理 libjpeg-turbo 的压缩状态。

```cpp
class SkJpegEncoderImpl : public SkEncoder {
public:
    // 从 RGB 像素创建 JPEG 编码器
    static std::unique_ptr<SkEncoder> MakeRGB(SkWStream* dst,
                                              const SkPixmap& src,
                                              const SkJpegEncoder::Options& options,
                                              const SkJpegMetadataEncoder::SegmentList& metadata);
    // 从 YUV 像素创建 JPEG 编码器
    static std::unique_ptr<SkEncoder> MakeYUV(SkWStream* dst,
                                              const SkYUVAPixmaps& srcYUVA, ...);
protected:
    bool onEncodeRows(int numRows) override;  // 逐行压缩并写入
};
```

### SkJpegMetadataEncoder（JPEG 元数据编码器）

管理 JPEG 文件中的 APP 标记段，包括 ICC 配置文件、XMP 元数据和 Exif 方向信息。

```cpp
namespace SkJpegMetadataEncoder {
    struct Segment {
        uint8_t fMarker;           // JPEG 标记类型
        sk_sp<SkData> fParameters; // 段参数数据
    };
    using SegmentList = std::vector<Segment>;

    void AppendICC(SegmentList&, const SkJpegEncoder::Options&, const SkColorSpace*);
    void AppendXMPStandard(SegmentList&, const SkData* xmpMetadata);
    void AppendOrigin(SegmentList&, SkEncodedOrigin origin);
}
```

### SkPngEncoderBase（PNG 编码器基类）

为 libpng 和 Rust png 两种实现提供共享的像素格式转换逻辑。

```cpp
class SkPngEncoderBase : public SkEncoder {
public:
    struct TargetInfo {
        std::optional<SkImageInfo> fSrcRowInfo;   // 源行信息
        std::optional<SkImageInfo> fDstRowInfo;   // 目标行信息
        SkEncodedInfo fDstInfo;                    // 编码信息
        size_t fDstRowSize;                        // 目标行字节大小
    };

    // 计算从源格式到 PNG 支持格式的转换信息
    static std::optional<TargetInfo> getTargetInfo(const SkImageInfo& srcInfo);

protected:
    bool onEncodeRows(int numRows) final;              // 执行格式转换后调用子类
    virtual bool onEncodeRow(SkSpan<const uint8_t> row) = 0;  // 子类实现实际压缩
    virtual bool onFinishEncoding() = 0;                       // 写入 IEND 结束块
};
```

### SkPngRustEncoderImpl（Rust PNG 编码器）

通过 CXX（C++/Rust 互操作桥接）调用 Rust 的 `png` crate 进行 PNG 压缩。

```cpp
class SkPngRustEncoderImpl final : public SkPngEncoderBase {
    enum ExtraRowTransform {
        kNone_ExtraRowTransform,              // 无需额外转换
        kRgba8ToRgb8_ExtraRowTransform,       // RGBA->RGB (Rust png 不支持忽略 alpha)
        kRgba16leToRgba16be_ExtraRowTransform, // 小端->大端
        kRgba16leToRgb16be_ExtraRowTransform,  // 小端 RGBA->大端 RGB
    };
    rust::Box<rust_png::StreamWriter> fStreamWriter;  // Rust 侧的流写入器
};
```

### WebP 编码器

WebP 编码支持有损和无损两种压缩模式，以及动画 WebP 编码。

```cpp
namespace SkWebpEncoder {
    bool Encode(SkWStream* stream, const SkPixmap& pixmap, const Options& opts);
    bool EncodeAnimated(SkWStream* stream, SkSpan<const SkEncoder::Frame> frames, const Options& opts);
    sk_sp<SkData> Encode(GrDirectContext* ctx, const SkImage* img, const Options& options);
}
```

### SkWriteICCProfile（ICC 配置文件生成）

生成符合 ICC v4.3/v4.4 标准的颜色配置文件数据。

```cpp
// 从传输函数和色彩矩阵生成 ICC 配置文件
sk_sp<SkData> SkWriteICCProfile(const skcms_TransferFunction& fn,
                                const skcms_Matrix3x3& toXYZD50);

// 从完整的 skcms_ICCProfile 结构生成
sk_sp<SkData> SkWriteICCProfile(const skcms_ICCProfile* profile, const char* desc);
```

### SkJpegGainmapEncoder（增益图编码器）

生成包含 HDR 增益图的多图片 JPEG 文件（HDRGM/UltraHDR 格式）。

```cpp
class SkJpegGainmapEncoder {
    static bool EncodeHDRGM(SkWStream* dst,
                            const SkPixmap& base,           // SDR 基础图像
                            const SkJpegEncoder::Options& baseOptions,
                            const SkPixmap& gainmap,         // 增益图
                            const SkJpegEncoder::Options& gainmapOptions,
                            const SkGainmapInfo& gainmapInfo);
    static bool MakeMPF(SkWStream* dst, const SkData** images, size_t imageCount);
};
```

## 依赖关系

### 上游依赖（本模块依赖的组件）

| 依赖模块 | 文件/类 | 用途 |
|---------|---------|------|
| `include/encode/` | `SkEncoder.h`, `SkJpegEncoder.h`, `SkPngEncoder.h`, `SkWebpEncoder.h` | 公共 API 定义 |
| `include/encode/` | `SkICC.h` | ICC 配置文件生成公共接口 |
| `include/core/` | `SkPixmap`, `SkData`, `SkStream`, `SkColorSpace` | 像素数据、内存管理、流IO |
| `include/core/` | `SkYUVAPixmaps` | YUV 像素数据（JPEG YUV 编码） |
| `src/core/` | `SkConvertPixels` | 像素格式转换（颜色类型/Alpha 转换） |
| `src/core/` | `SkImageInfoPriv` | 图像信息验证工具 |
| `src/image/` | `SkImage_Base` | `getROPixels()` 用于从 SkImage 获取可编码的像素 |
| `src/codec/` | `SkJpegConstants`, `SkJpegPriv`, `SkJpegMultiPicture` | JPEG 格式常量、MPF 多图片参数 |
| `src/codec/` | `SkJpegSegmentScan` | JPEG 段扫描（增益图编码中定位插入点） |
| `src/codec/` | `SkTiffUtility` | TIFF/Exif 工具（增益图编码中的 Exif 生成） |
| `modules/skcms/` | `skcms.h` | 颜色管理系统（传输函数、ICC 配置文件解析） |
| 第三方 | `libjpeg-turbo` | JPEG 压缩引擎 |
| 第三方 | `libpng` | PNG 压缩引擎 |
| 第三方 | `libwebp` | WebP 压缩引擎 |
| 第三方 | `rust/png` crate | Rust PNG 压缩引擎（可选替代） |

### 下游被依赖（使用本模块的组件）

| 依赖方 | 用途 |
|--------|------|
| 应用层代码 | 通过 `SkJpegEncoder::Encode()` 等 API 编码图像 |
| `tools/` | 测试和工具中的图像保存 |
| `modules/skottie/` | Lottie 动画导出中的图像编码 |

## 设计模式分析

### 1. 策略模式（Strategy）

编码模块的核心架构基于策略模式。`SkEncoder` 基类定义了通用的编码接口，而 JPEG、PNG、WebP 各自的实现类提供了不同的编码策略。用户通过各编码器命名空间中的 `Make()` 工厂函数选择具体策略。

### 2. 模板方法模式（Template Method）

`SkPngEncoderBase` 是该模式的典型应用。`onEncodeRows()` 在基类中完成像素格式转换（如 RGBA_F32 到 RGBA_16），然后调用子类的 `onEncodeRow()` 执行实际压缩。子类只需关注压缩逻辑，无需关心格式转换。

```
SkPngEncoderBase::onEncodeRows()
    |
    +--> SkConvertPixels()      // 基类：格式转换
    +--> onEncodeRow(row)       // 子类：压缩
    +--> onFinishEncoding()     // 子类：写入结束标记
```

### 3. 桥接模式（Bridge）

PNG 编码器的设计是桥接模式的体现。`SkPngEncoderBase` 定义了抽象接口，而 `SkPngEncoderImpl`（libpng）和 `SkPngRustEncoderImpl`（Rust png crate）提供了两个不同的底层实现。这使得编码逻辑与压缩库解耦，便于替换或添加新的压缩后端。

### 4. 空对象模式（Null Object）

`*_none.cpp` 桩文件实现了空对象模式。当某个编码器的第三方库未被链接时，桩文件中的函数返回失败或 nullptr，避免了链接错误同时提供了优雅降级。

### 5. 建造者模式（Builder）

JPEG 元数据编码采用建造者风格。`SkJpegMetadataEncoder::SegmentList` 通过 `AppendICC()`、`AppendXMPStandard()`、`AppendOrigin()` 逐步构建元数据段列表，最终一次性传入编码器。

## 数据流

### JPEG 编码流程

```
用户调用 SkJpegEncoder::Encode(stream, pixmap, options)
    |
    v
SkJpegEncoder::Make(stream, pixmap, options)
    |
    +--> 构建 SkJpegMetadataEncoder::SegmentList
    |    +--> AppendXMPStandard()   添加 XMP 元数据
    |    +--> AppendICC()           添加 ICC 配置文件
    |    +--> AppendOrigin()        添加 Exif 方向
    |
    +--> SkJpegEncoderImpl::MakeRGB(stream, pixmap, options, metadata)
         |
         +--> SkJpegEncoderMgr::Make(stream)
         |    +--> jpeg_create_compress()
         |    +--> fCInfo.dest = &fDstMgr (适配 SkWStream)
         |
         +--> SkJpegEncoderMgr::initializeRGB()
         |    +--> 根据 colorType 选择 J_COLOR_SPACE
         |    +--> 设置色度子采样 (420/422/444)
         |    +--> jpeg_set_defaults() + jpeg_set_quality()
         |    +--> jpeg_start_compress()
         |    +--> 写入元数据标记段 (jpeg_write_marker)
         |
         +--> 创建 SkJpegEncoderImpl 实例
    |
    v
encoder->encodeRows(pixmap.height())
    |
    v
SkJpegEncoderImpl::onEncodeRows(numRows)
    |
    +--> 逐行处理:
    |    +--> [若需要颜色转换] colorTransformProc() (SkConvertPixels)
    |    +--> jpeg_write_scanlines() 写入压缩数据
    |
    +--> [最后一行] jpeg_finish_compress()
```

### PNG 编码流程（以 Rust 实现为例）

```
用户调用 SkPngRustEncoder::Encode(stream, pixmap, options)
    |
    v
SkPngRustEncoderImpl::Make(stream, pixmap, options)
    |
    +--> SkPngEncoderBase::getTargetInfo(srcInfo)
    |    +--> 根据 colorType 和通道数确定目标格式
    |    +--> 例: kRGBA_F32 -> SkEncodedInfo::kRGBA_Color, 16bit
    |
    +--> 创建 Rust StreamWriter (通过 CXX 桥接)
    +--> 确定 ExtraRowTransform 类型
    |
    v
encoder->encodeRows(pixmap.height())
    |
    v
SkPngEncoderBase::onEncodeRows(numRows)  [模板方法]
    |
    +--> 逐行处理:
    |    +--> [kAlpha_8] transform_scanline_A8_to_GrayAlpha()
    |    +--> [其他] SkConvertPixels(dstRowInfo, storage, srcRowInfo, srcRow)
    |    +--> SkPngRustEncoderImpl::onEncodeRow(row)
    |         +--> [若需要] ExtraRowTransform (RGBA->RGB 或 LE->BE)
    |         +--> fStreamWriter->write_row(row) [调用 Rust]
    |
    +--> [所有行完成] SkPngRustEncoderImpl::onFinishEncoding()
         +--> fStreamWriter->finish() [调用 Rust]
```

### ICC 配置文件生成流程

```
SkWriteICCProfile(transferFunction, toXYZD50)
    |
    +--> 检测传输函数类型 (sRGBish / PQish / HLGish)
    |
    +--> 填充 skcms_ICCProfile 结构:
    |    +--> toXYZD50 矩阵 (基色点)
    |    +--> TRC 曲线 (传输函数)
    |    +--> [HDR] A2B 表 (含色调映射 3D LUT)
    |    +--> [HDR] B2A 表 (逆映射)
    |    +--> [HDR] CICP 标签
    |
    +--> SkWriteICCProfile(profile, desc)
         |
         +--> 构建标签列表:
         |    +--> rXYZ, gXYZ, bXYZ (基色点)
         |    +--> rTRC, gTRC, bTRC (传输曲线)
         |    +--> wtpt (白点 D50)
         |    +--> desc (描述)
         |    +--> cprt (版权)
         |    +--> [可选] cicp, A2B0, B2A0
         |
         +--> 写入 ICC 头部 (128字节)
         +--> 写入标签表 (每项12字节)
         +--> 写入标签数据
         +--> 返回 sk_sp<SkData>
```

## 相关文档与参考

| 资源 | 说明 |
|------|------|
| `include/encode/SkEncoder.h` | 编码器基类公共 API |
| `include/encode/SkJpegEncoder.h` | JPEG 编码器公共 API（Options 结构含 quality, downsample 等） |
| `include/encode/SkPngEncoder.h` | PNG 编码器公共 API（Options 结构含 filterFlags, zlibLevel 等） |
| `include/encode/SkWebpEncoder.h` | WebP 编码器公共 API（Options 结构含 quality, compression 等） |
| `include/encode/SkICC.h` | ICC 配置文件生成公共接口 |
| `include/private/SkJpegGainmapEncoder.h` | JPEG 增益图编码器接口 |
| `include/private/SkGainmapInfo.h` | 增益图元信息结构定义 |
| `include/core/SkStream.h` | 流接口（SkWStream 写入流） |
| `modules/skcms/skcms.h` | 颜色管理系统 API |
| ICC 规范 | https://www.color.org/specification/ICC.1-2022-05.pdf |
| JPEG 规范 (ITU-T T.81) | https://www.w3.org/Graphics/JPEG/itu-t81.pdf |
| PNG 规范 (W3C) | https://www.w3.org/TR/png-3/ |
| WebP 格式说明 | https://developers.google.com/speed/webp |
| Adobe HDRGM 规范 | HDR 增益图元数据命名空间 |
| ISO 21496-1 | 增益图国际标准 |
