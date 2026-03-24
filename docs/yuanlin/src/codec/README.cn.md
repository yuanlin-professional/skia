# src/codec - Skia 图像编解码模块

## 概述

`src/codec` 是 Skia 图形库的核心图像解码模块，负责将各种编码格式的图像数据（如 PNG、JPEG、WebP、GIF、BMP、AVIF、JPEG XL 等）解码为 Skia 内部可直接使用的像素数据。该模块是 Skia 图像处理管线的入口之一，为上层的 `SkImage`、`SkBitmap` 等核心对象提供原始像素数据来源。

该模块最早于 2015 年由 Google 引入（取代早期的 `SkImageDecoder`），采用了更加现代化的 C++ 设计模式，以统一的抽象接口 `SkCodec` 对外暴露解码能力。相比旧的 `SkImageDecoder`，新的 `SkCodec` 架构提供了更精细的错误处理、增量解码（incremental decoding）、扫描线解码（scanline decoding）和动画帧支持等高级功能。

自创建以来，该模块持续扩展对新图像格式的支持。2018 年引入了基于 Wuffs 安全解析库的 GIF 解码器；2021 年新增了 JPEG XL 支持；2022 年新增了 AVIF 支持（包括基于 libavif 和 CrabbyAvif 两种实现）；2024 年还引入了基于 Rust 的 PNG 解码器 (`SkPngRustCodec`) 作为传统 libpng 的替代方案，以及 Rust ICC 颜色配置文件解析支持。

该模块还包含 HDR（高动态范围）相关的支持，如 Gainmap 信息解析、自适应全局色调映射（Adaptive Global Tone Mapping, AGTM）以及 HDR 元数据处理，为现代 HDR 图像的正确显示提供了基础设施。

模块采用解码器注册表（decoder registry）机制，通过 `SkCodecs::Decoder` 结构体和 `SkCodecs::Register()` 函数实现解码器的动态注册与查找，使得构建时可以灵活地选择需要包含的图像格式支持，实现按需裁剪。

## 架构图

```
                        +---------------------------+
                        |     客户端代码 (Client)      |
                        +---------------------------+
                                    |
                         MakeFromStream / MakeFromData
                                    |
                                    v
+-----------------------------------------------------------------------+
|                          SkCodec (基类)                                 |
|  - getPixels()        - startScanlineDecode()                         |
|  - getFrameCount()    - startIncrementalDecode()                      |
|  - queryYUVAInfo()    - getEncodedFormat()                            |
+-----------------------------------------------------------------------+
         |                    |                    |              |
         v                    v                    v              v
+----------------+  +----------------+  +-----------------+ +----------+
| SkScalingCodec |  |   SkBmpCodec   |  |  SkJpegCodec    | | SkIcoCodec|
| (缩放辅助基类)  |  |  (BMP 基类)     |  |  (JPEG 解码)    | | (ICO 容器)|
+----------------+  +----------------+  +-----------------+ +----------+
    |    |    |         |       |    |
    v    v    v         v       v    v
+------+------+------+  +-------+-------+--------+
|WebP  |AVIF  |JXL   |  |Std    |RLE    |Mask    |
|Codec |Codec |Codec |  |BMP    |BMP    |BMP     |
+------+------+------+  +-------+-------+--------+

+----------------+  +----------------+  +------------------+
| SkPngCodecBase |  | SkWuffsCodec   |  |   SkRawCodec     |
|  (PNG 基类)     |  | (GIF via Wuffs)|  |  (RAW/DNG 解码)  |
+----------------+  +----------------+  +------------------+
    |         |
    v         v
+--------+ +-------------+
|SkPng   | |SkPngRust    |
|Codec   | |Codec        |
|(libpng)| |(Rust实现)    |
+--------+ +-------------+

辅助组件:
+-------------+ +-------------+ +--------------+ +----------------+
| SkSwizzler  | |SkMaskSwizzl | | SkSampler    | | SkFrameHolder  |
| (像素格式    | |er (位掩码    | | (采样控制)    | | (动画帧管理)    |
|  转换)       | | 转换)       | |              | |                |
+-------------+ +-------------+ +--------------+ +----------------+

元数据与HDR:
+-------------+ +-------------+ +--------------+ +----------------+
| SkExif      | | SkTiff      | | SkGainmap    | | SkHdrAgtm      |
| (EXIF解析)   | | Utility     | | Info (增益图) | | (自适应色调    |
|             | | (TIFF IFD)  | |              | |  映射)         |
+-------------+ +-------------+ +--------------+ +----------------+
```

## 目录结构

`src/codec/` 目录不包含子目录，所有文件平铺在同一层级。按功能分类如下：

### 核心框架文件

| 文件 | 说明 |
|------|------|
| `SkCodec.cpp` | `SkCodec` 基类的核心实现，包含解码器注册表、`MakeFromStream` 工厂方法、颜色变换管线等 |
| `SkCodecPriv.h` | 编解码模块内部共享的私有工具函数和 `SkCodecs::ColorProfile` 颜色配置文件类 |
| `SkCodecImageGenerator.h/cpp` | 将 `SkCodec` 适配为 `SkImageGenerator` 接口，供 `SkImage` 延迟解码使用 |
| `SkEncodedInfo.cpp` | `SkEncodedInfo` 的实现，描述编码图像的颜色类型、Alpha 类型、位深度和颜色配置文件 |
| `SkCodecColorProfile.cpp` | `SkCodecs::ColorProfile` 的 skcms 实现，用于解析和表示 ICC 颜色配置文件 |
| `SkCodecColorProfileRust.cpp/h` | `ColorProfile` 的 Rust 实现，作为 skcms 的替代方案 |
| `SkImageGenerator_FromEncoded.cpp` | 从编码数据创建 `SkImageGenerator` 的工厂函数 |

### 像素转换与采样文件

| 文件 | 说明 |
|------|------|
| `SkSwizzler.h/cpp` | 核心像素格式转换器（Swizzler），负责源格式到目标格式的逐行像素转换，支持采样和子集 |
| `SkMaskSwizzler.h/cpp` | 基于位掩码的像素转换器，专用于 BMP 位掩码编码格式 |
| `SkSampler.h/cpp` | 采样器基类，控制 X/Y 方向的像素采样（降采样解码），`SkSwizzler` 继承自此类 |
| `SkColorPalette.h/cpp` | 调色板类，存储 8 位索引图像使用的最多 256 色预乘颜色表 |
| `SkPixmapUtils.cpp` / `SkPixmapUtilsPriv.h` | Pixmap 工具函数，处理 EXIF 方向变换等 |

### 动画帧支持

| 文件 | 说明 |
|------|------|
| `SkFrameHolder.h` | `SkFrame` 和 `SkFrameHolder` 基类，为动画图像（GIF、WebP、AVIF 等）提供帧管理抽象 |
| `SkScalingCodec.h` | 支持任意缩放的编解码器辅助基类，提供 `onGetScaledDimensions` 和 `onDimensionsSupported` 的默认实现 |

### 各格式解码器

| 文件 | 说明 |
|------|------|
| `SkPngCodecBase.h/cpp` | PNG 解码器的共享基类，同时被 `SkPngCodec` (libpng) 和 `SkPngRustCodec` (Rust) 继承 |
| `SkPngCodec.h/cpp` | 基于 libpng 库的 PNG 解码器实现 |
| `SkPngRustCodec.h/cpp` | 基于 Rust png crate 的 PNG 解码器实现（实验性替代方案） |
| `SkPngRustDecoder.cpp` | Rust PNG 解码器的公开注册入口 |
| `SkPngCompositeChunkReader.h/cpp` | PNG Chunk 读取器组合类，将多个 chunk reader 组合为一个 |
| `SkPngPriv.h` | PNG 解码的内部私有定义 |
| `SkJpegCodec.h/cpp` | 基于 libjpeg-turbo 的 JPEG 解码器，支持 YUVA 解码和 Gainmap 提取 |
| `SkJpegDecoderMgr.h/cpp` | JPEG 解码管理器，封装 libjpeg-turbo 的 decompress 结构体 |
| `SkJpegSourceMgr.h/cpp` | JPEG 数据源管理器，将 `SkStream` 适配为 libjpeg-turbo 的数据源接口 |
| `SkJpegUtility.h/cpp` | JPEG 解码辅助工具 |
| `SkJpegConstants.h` | JPEG 格式相关常量定义（如标记字节） |
| `SkJpegPriv.h` | JPEG 解码的内部私有定义 |
| `SkJpegSegmentScan.h/cpp` | JPEG 段扫描器，解析 JPEG 文件的段结构 |
| `SkJpegMultiPicture.h/cpp` | JPEG 多图片格式（MPF）解析，支持多图嵌入的 JPEG 文件 |
| `SkJpegMetadataDecoderImpl.h/cpp` | JPEG 元数据解码器实现，解析 EXIF、XMP、ICC 等元数据 |
| `SkJpegXmp.h/cpp` | JPEG XMP 元数据解析 |
| `SkWebpCodec.h/cpp` | 基于 libwebp 的 WebP 解码器，支持动画和有损/无损格式 |
| `SkWuffsCodec.cpp` | 基于 Wuffs 安全解析库的 GIF 解码器（无独立头文件，全部实现在单一 .cpp 文件中） |
| `SkBmpCodec.h/cpp` | BMP 解码器基类，处理 BMP 文件头解析 |
| `SkBmpBaseCodec.h/cpp` | BMP 解码器的进一步基类抽象 |
| `SkBmpStandardCodec.h/cpp` | 标准（未压缩或调色板）BMP 解码器 |
| `SkBmpRLECodec.h/cpp` | RLE 压缩 BMP 解码器 |
| `SkBmpMaskCodec.h/cpp` | 位掩码编码 BMP 解码器 |
| `SkIcoCodec.h/cpp` | ICO/CUR 容器格式解码器，内部包含多个嵌入的 BMP 或 PNG 编码图像 |
| `SkWbmpCodec.h/cpp` | WBMP（无线位图）解码器，处理单色位图 |
| `SkAvifCodec.h/cpp` | 基于 libavif 的 AVIF 解码器 |
| `SkCrabbyAvifCodec.h/cpp` | 基于 CrabbyAvif（Rust 实现的 AVIF 解码器）的 AVIF 解码器 |
| `SkJpegxlCodec.h/cpp` | 基于 libjxl 的 JPEG XL 解码器 |
| `SkRawCodec.h/cpp` | 基于 DNG SDK 的 RAW/DNG 图像解码器 |

### Android 特定支持

| 文件 | 说明 |
|------|------|
| `SkAndroidCodec.cpp` | `SkAndroidCodec` 的实现，为 Android 平台提供缩放和采样解码的统一接口 |
| `SkAndroidCodecAdapter.h/cpp` | 将支持原生缩放的 `SkCodec` 适配为 `SkAndroidCodec` 接口 |
| `SkSampledCodec.h/cpp` | 为不支持原生缩放的 `SkCodec` 通过采样实现降分辨率解码 |

### 元数据与 HDR 支持

| 文件 | 说明 |
|------|------|
| `SkExif.cpp` | EXIF 元数据解析，提取方向、分辨率、拍摄参数等信息 |
| `SkTiffUtility.h/cpp` | TIFF IFD（Image File Directory）解析工具，被 EXIF、MPF 等元数据解析使用 |
| `SkParseEncodedOrigin.h/cpp` | 从编码数据中解析图像方向 |
| `SkGainmapInfo.cpp` | Gainmap（增益图）信息的解析与处理 |
| `SkHdrAgtm.cpp` | 自适应全局色调映射（AGTM）的核心实现 |
| `SkHdrAgtmParse.cpp` | AGTM 参数的解析 |
| `SkHdrAgtmPriv.h` | AGTM 的内部定义和辅助函数 |
| `SkHdrMetadata.cpp` | HDR 元数据处理 |
| `SkXmp.cpp` | XMP 元数据解析（通用实现） |

### 构建配置

| 文件 | 说明 |
|------|------|
| `BUILD.bazel` | Bazel 构建规则，定义了各解码器的编译目标和依赖关系 |

## 关键类与函数

### SkCodec

- **文件**: `include/codec/SkCodec.h` / `src/codec/SkCodec.cpp`
- **职责**: 所有图像解码器的抽象基类，定义了统一的解码接口和生命周期管理
- **关键方法**:
  - `MakeFromStream(stream, result)` - 核心工厂方法，通过检测流中的魔数（magic bytes）自动识别图像格式，遍历注册的解码器列表调用 `isFormat()` 进行匹配，然后调用对应的 `makeFromStream()` 创建解码器实例
  - `MakeFromData(data)` - 从内存数据创建解码器
  - `getPixels(dstInfo, dst, rowBytes, options)` - 执行完整图像解码，将像素写入指定内存
  - `startScanlineDecode()` / `getScanlines()` / `skipScanlines()` - 扫描线解码接口，支持逐行解码
  - `startIncrementalDecode()` / `incrementalDecode()` - 增量解码接口，允许在数据不完整时分批解码
  - `getFrameCount()` / `getFrameInfo()` / `getRepetitionCount()` - 动画帧信息查询
  - `queryYUVAInfo()` / `getYUVAPlanes()` - YUVA 平面解码（主要用于 JPEG 硬件加速）
  - `getEncodedFormat()` - 返回编码图像的格式
  - `getGainmapInfo()` / `getGainmapCodec()` - HDR Gainmap 信息提取

### SkCodecs::Decoder

- **文件**: `include/codec/SkCodec.h`
- **职责**: 解码器注册表条目，包含格式识别和解码器创建的回调函数
- **关键字段**:
  - `id` - 解码器的字符串标识符（如 "png"、"jpeg"、"webp"）
  - `isFormat(data, size)` - 判断数据是否为该格式
  - `makeFromStream(stream, result, context)` - 从流创建解码器实例

### SkCodecs::ColorProfile

- **文件**: `src/codec/SkCodecPriv.h` / `src/codec/SkCodecColorProfile.cpp`
- **职责**: 封装图像的完整颜色配置文件信息，包括 ICC 配置文件和 CICP 色域标识
- **关键方法**:
  - `MakeICCProfile(data)` - 从 ICC 数据创建颜色配置文件
  - `MakeCICP(cp, tc, mc, fr)` - 从 CICP 值创建颜色配置文件
  - `getExactColorSpace()` - 获取精确的 `SkColorSpace` 表示
  - `getAndroidOutputColorSpace()` - 获取 Android 兼容的输出色彩空间
  - `dataSpace()` - 返回配置文件的数据空间类型（RGB、CMYK、Gray 等）

### SkSwizzler

- **文件**: `src/codec/SkSwizzler.h` / `src/codec/SkSwizzler.cpp`
- **职责**: 核心像素格式转换引擎，将编码格式的行数据转换为目标像素格式，同时支持采样和子集操作
- **关键方法**:
  - `Make(encodedInfo, ctable, dstInfo, options, frame)` - 创建完整功能的 Swizzler
  - `MakeSimple(srcBPP, dstInfo, options, frame)` - 创建仅做采样/子集操作的简化 Swizzler
  - `swizzle(dst, src)` - 转换一行像素数据
  - `sampleX()` - 获取当前 X 方向采样间隔
  - `swizzleWidth()` - 获取实际写入的像素宽度

### SkSampler

- **文件**: `src/codec/SkSampler.h` / `src/codec/SkSampler.cpp`
- **职责**: 采样器抽象基类，控制解码过程中的行列采样策略
- **关键方法**:
  - `setSampleX(sampleX)` - 设置每隔 sampleX 个像素取一个
  - `setSampleY(sampleY)` - 设置每隔 sampleY 行取一行
  - `rowNeeded(row)` - 判断当前行是否需要被解码
  - `Fill(info, dst, rowBytes, zeroInit)` - 用零值填充剩余未解码区域

### SkFrame / SkFrameHolder

- **文件**: `src/codec/SkFrameHolder.h`
- **职责**: `SkFrame` 表示动画图像的单帧，`SkFrameHolder` 管理帧序列
- **关键方法**:
  - `SkFrame::frameId()` - 获取帧的 0 基索引
  - `SkFrame::getRequiredFrame()` - 获取依赖的前置帧
  - `SkFrame::getDuration()` - 获取帧显示时长（毫秒）
  - `SkFrame::getDisposalMethod()` - 获取帧的处置方式（保留/恢复背景/恢复前帧）
  - `SkFrame::getBlend()` - 获取混合模式（SrcOver/Src）
  - `SkFrameHolder::setAlphaAndRequiredFrame(frame)` - 根据帧的混合和处置方式计算透明度和依赖帧

### SkPngCodecBase

- **文件**: `src/codec/SkPngCodecBase.h` / `src/codec/SkPngCodecBase.cpp`
- **职责**: PNG 解码器的公共基类，封装 libpng 和 Rust 实现共享的逻辑
- **关键方法**:
  - `initializeXforms(dstInfo, options, frameWidth)` - 初始化颜色变换管线
  - `applyXformRow(dstRow, srcRow)` - 对解码行应用颜色变换（swizzle + 色彩空间转换）
  - `isCompatibleColorProfileAndType(profile, color)` - 校验颜色配置文件与编码类型是否兼容

### SkJpegCodec

- **文件**: `src/codec/SkJpegCodec.h` / `src/codec/SkJpegCodec.cpp`
- **职责**: JPEG 图像解码，支持硬件加速的 YUVA 解码和 Gainmap 提取
- **关键方法**:
  - `onGetScaledDimensions(desiredScale)` - 利用 libjpeg-turbo 的原生 1/2、1/4、1/8 缩放
  - `onGetPixels()` - 完整 RGB/RGBA 解码
  - `onQueryYUVAInfo()` / `onGetYUVAPlanes()` - YUVA 平面解码
  - `onGetGainmapCodec()` / `onGetGainmapInfo()` - HDR Gainmap 提取

### SkWebpCodec

- **文件**: `src/codec/SkWebpCodec.h` / `src/codec/SkWebpCodec.cpp`
- **职责**: WebP 图像解码，支持有损/无损、动画和 Alpha 通道
- **关键方法**:
  - `onGetPixels()` - 解码当前帧
  - `onGetFrameCount()` / `onGetFrameInfo()` - 动画帧信息
  - `onGetValidSubset()` - 子区域解码支持

### SkTiff::ImageFileDirectory

- **文件**: `src/codec/SkTiffUtility.h` / `src/codec/SkTiffUtility.cpp`
- **职责**: TIFF IFD 结构解析工具，被 EXIF、MPF 等多种元数据格式使用
- **关键方法**:
  - `ParseHeader(data, outLittleEndian, outIfdOffset)` - 解析 TIFF 头部字节序和 IFD 偏移
  - `MakeFromOffset(data, littleEndian, ifdOffset)` - 从数据偏移创建 IFD 解析对象
  - `getEntryTag(index)` - 获取指定条目的标签号
  - `getEntryUnsignedShort/Long/Rational()` - 读取各种类型的条目值

## 依赖关系

### 上游依赖（本模块依赖的模块）

| 模块 | 说明 |
|------|------|
| `include/core` | 核心类型定义：`SkImageInfo`、`SkColorSpace`、`SkStream`、`SkData`、`SkBitmap` 等 |
| `include/codec` | 公开头文件，定义 `SkCodec`、`SkAndroidCodec` 等公开 API |
| `include/private` | `SkEncodedInfo`、`SkHdrMetadata` 等模块内部共享但不对外暴露的类型 |
| `src/core` | 核心私有实现：`SkColorPriv`、`SkColorData`、`SkStreamPriv` 等 |
| `src/base` | 基础设施：`SkNoDestructor`（避免静态初始化器）等 |
| `modules/skcms` | 颜色管理系统，用于 ICC 配置文件解析和色彩空间转换 |

### 下游被依赖（依赖本模块的模块）

| 模块 | 说明 |
|------|------|
| `src/core` | 通过 `SkCodecImageGenerator` 实现图像延迟解码 |
| `src/encode` | 编码模块依赖 `any_decoder` 以获取像素格式转换工具 |
| `src/pdf` | PDF 生成依赖解码器处理嵌入图像 |
| `src/ports` | 平台端口层使用编解码模块处理系统图像 |
| `include/android` | Android 平台通过 `SkAndroidCodec` 接口使用 |
| 客户端应用 | 通过 `SkCodec::MakeFromStream/Data` 或 `SkImage::MakeFromEncoded` 间接使用 |

### 外部依赖（第三方库）

| 库 | 用途 | 控制宏 |
|---|------|--------|
| **libpng** | PNG 解码（传统实现） | `SK_CODEC_DECODES_PNG_WITH_LIBPNG` |
| **Rust png crate** | PNG 解码（Rust 实现） | `SK_CODEC_DECODES_PNG_WITH_RUST` |
| **libjpeg-turbo** | JPEG 解码，包括 SIMD 加速 | `SK_CODEC_DECODES_JPEG` |
| **libwebp** | WebP 解码（有损/无损/动画） | `SK_CODEC_DECODES_WEBP` |
| **Wuffs** | GIF 解码，内存安全的解析库 | `SK_CODEC_DECODES_GIF` / `SK_HAS_WUFFS_LIBRARY` |
| **libavif** | AVIF 解码（C 实现） | `SK_CODEC_DECODES_AVIF` |
| **CrabbyAvif** | AVIF 解码（Rust 实现，Android 默认） | `SK_CODEC_DECODES_AVIF` + `SK_BUILD_FOR_ANDROID_FRAMEWORK` |
| **libjxl** | JPEG XL 解码 | `SK_CODEC_DECODES_JPEGXL` |
| **piex / DNG SDK** | RAW/DNG 图像解码 | `SK_CODEC_DECODES_RAW` |
| **skcms** | ICC 颜色配置文件解析与色彩空间转换 | 始终包含 |

## 设计模式分析

### 工厂方法模式（Factory Method）

`SkCodec::MakeFromStream()` 是典型的工厂方法实现。它通过读取流的前 32 字节（`MinBufferedBytesNeeded()`），遍历注册的 `SkCodecs::Decoder` 列表，调用每个解码器的 `isFormat()` 方法进行格式检测，匹配成功后调用对应的 `makeFromStream()` 创建具体的解码器实例。这种设计使客户端无需了解具体格式的细节，只需提供数据流即可获得正确的解码器。

```cpp
// SkCodec.cpp 中的核心逻辑
for (const SkCodecs::Decoder& proc : decoders) {
    if (proc.isFormat(buffer, bytesRead)) {
        return proc.makeFromStream(std::move(stream), outResult, nullptr);
    }
}
```

### 注册表模式（Registry）

模块使用静态的 `std::vector<SkCodecs::Decoder>` 作为解码器注册表，通过编译时宏（如 `SK_CODEC_DECODES_PNG_WITH_LIBPNG`）和运行时的 `SkCodecs::Register()` 函数管理可用的解码器。这允许应用程序精确控制链接哪些解码器，有效减少二进制体积。

### 模板方法模式（Template Method）

`SkCodec` 基类定义了解码的整体流程框架（如 `getPixels()` 中的参数验证、颜色变换设置），子类通过覆写 `onGetPixels()`、`onStartScanlineDecode()` 等虚方法提供具体实现。基类的 `getPixels()` 方法在调用 `onGetPixels()` 前后执行通用的验证和后处理，确保一致的行为。

### 策略模式（Strategy）

`SkSwizzler` 使用函数指针（`RowProc`）作为策略，根据源格式和目标格式在构造时选择最优的逐行转换函数。它维护一个 `fFastProc`（优化路径）和 `fSlowProc`（通用路径），运行时根据是否需要采样动态选择实际使用的处理过程 `fActualProc`。

### 适配器模式（Adapter）

- `SkAndroidCodecAdapter` 将已支持缩放的 `SkCodec` 适配为 `SkAndroidCodec` 接口
- `SkSampledCodec` 为不支持原生缩放的 `SkCodec` 通过采样策略实现 `SkAndroidCodec` 的缩放接口
- `SkCodecImageGenerator` 将 `SkCodec` 适配为 `SkImageGenerator` 接口

### 组合模式（Composite）

`SkIcoCodec` 是组合模式的体现：一个 ICO 文件内部包含多个嵌入的图像（BMP 或 PNG），`SkIcoCodec` 持有一个 `std::unique_ptr<SkCodec>` 数组（`fEmbeddedCodecs`），解码时根据请求的尺寸选择最优的内嵌图像进行解码。

## 数据流

### 完整解码流程

```
1. 客户端调用 SkCodec::MakeFromStream(stream)
   |
2. 读取前 32 字节进行格式识别
   |
3. 遍历注册表匹配 isFormat()
   |
4. 调用匹配的 makeFromStream() 创建具体 Codec
   |   (解析头部信息、提取 SkEncodedInfo)
   |
5. 客户端调用 codec->getPixels(dstInfo, dst, rowBytes, options)
   |
6. SkCodec::getPixels() 执行通用逻辑:
   |   a. 验证参数合法性
   |   b. 设置颜色变换管线 (initializeColorXform)
   |   c. 调用子类 onGetPixels()
   |
7. 子类 onGetPixels() 执行格式特定解码:
   |   a. 从 stream 读取编码数据
   |   b. 调用第三方库解码 (如 libjpeg-turbo)
   |   c. 通过 SkSwizzler 转换像素格式
   |   d. 通过 skcms 应用颜色变换
   |   e. 将结果写入 dst 缓冲区
   |
8. 返回 Result 给客户端
```

### 增量解码流程

```
1. codec->startIncrementalDecode(dstInfo, dst, rowBytes, options)
   |
2. 初始化解码状态，设置目标缓冲区
   |
3. codec->incrementalDecode(&rowsDecoded)  [可能被多次调用]
   |
4. 每次调用尝试解码更多行:
   |   a. 从 stream 读取可用数据
   |   b. 解码尽可能多的行
   |   c. 返回 kIncompleteInput 或 kSuccess
   |
5. 重复步骤 3 直到完成或放弃
```

### 颜色变换管线

```
源像素数据 (编码格式)
    |
    v
SkSwizzler (格式转换 + 采样)
    |  源格式 -> 中间格式 (如 RGBA_8888)
    v
skcms_Transform (颜色空间转换)
    |  源色彩空间 -> 目标色彩空间
    v
目标像素数据 (请求的 SkColorType)
```

## 平台特定说明

### Android 平台

Android 框架对图像解码有特殊需求，主要通过以下机制体现：

1. **SkAndroidCodec**: 为 Android BitmapFactory 提供了 `getAndroidPixels()` 接口，支持 `sampleSize` 参数实现高效的降分辨率解码。内部通过 `SkAndroidCodecAdapter`（用于支持原生缩放的编解码器，如 JPEG、WebP）和 `SkSampledCodec`（用于不支持原生缩放的编解码器，如 PNG、BMP）两种适配器实现。

2. **CrabbyAvif 优先**: 在 Android Framework 构建中（`SK_BUILD_FOR_ANDROID_FRAMEWORK`），AVIF 解码默认使用基于 Rust 的 `SkCrabbyAvifCodec` 而非 C 实现的 `SkAvifCodec`，以获得更好的内存安全性。

3. **Android 颜色空间**: `SkCodecs::ColorProfile::getAndroidOutputColorSpace()` 提供了 Android 平台特定的颜色空间映射逻辑。

### Rust 集成

模块正在逐步引入 Rust 实现来替代传统的 C/C++ 库：

1. **SkPngRustCodec**: 通过 `SK_CODEC_DECODES_PNG_WITH_RUST` 宏启用，使用 Rust 的 `png` crate 替代 libpng
2. **SkCodecColorProfileRust**: 通过 `SK_CODEC_COLOR_PROFILE_PARSE_WITH_RUST` 宏启用，使用 Rust 解析 ICC 配置文件
3. **CrabbyAvif**: 基于 Rust 的 AVIF 解码器实现

### 字节序处理

`SkCodecPriv.h` 中提供了 `IsValidEndianMarker()`、`GetEndianShort()`、`GetEndianInt()` 等函数来处理不同平台和格式的字节序问题。通过 `SK_CPU_BENDIAN` 宏区分大端和小端平台，`UnsafeGetShort/Int()` 等函数根据平台字节序进行适当的字节交换。

### 编译期格式选择

每种图像格式的支持都可以通过预处理器宏单独控制，核心的格式选择宏包括：

- `SK_CODEC_DECODES_PNG_WITH_LIBPNG` / `SK_CODEC_DECODES_PNG_WITH_RUST`
- `SK_CODEC_DECODES_JPEG`
- `SK_CODEC_DECODES_WEBP`
- `SK_CODEC_DECODES_GIF` / `SK_HAS_WUFFS_LIBRARY`
- `SK_CODEC_DECODES_BMP` / `SK_CODEC_DECODES_BMP_WITH_RUST`
- `SK_CODEC_DECODES_ICO`
- `SK_CODEC_DECODES_WBMP`
- `SK_CODEC_DECODES_AVIF`
- `SK_CODEC_DECODES_JPEGXL`
- `SK_CODEC_DECODES_RAW`

通过 `SK_DISABLE_LEGACY_INIT_DECODERS` 可禁用编译时自动注册，改为应用程序手动调用 `SkCodecs::Register()` 注册所需的解码器。

## 相关文档与参考

### Skia 内部相关目录

- `include/codec/` - 编解码模块的公开头文件，定义了 `SkCodec`、`SkAndroidCodec` 以及各格式解码器的公开注册入口
- `include/private/SkEncodedInfo.h` - 编码图像信息的完整定义
- `include/private/SkHdrMetadata.h` - HDR 元数据和 AGTM 结构体定义
- `src/encode/` - 图像编码模块（与解码模块对称）
- `src/core/SkImageGenerator.h` - `SkImageGenerator` 基类定义
- `modules/skcms/` - 颜色管理系统模块

### 外部参考资源

- [Skia 官方文档](https://skia.org/) - Skia 图形库官方站点
- [libpng 官方文档](http://www.libpng.org/pub/png/libpng.html) - PNG 参考实现
- [libjpeg-turbo](https://libjpeg-turbo.org/) - SIMD 加速的 JPEG 编解码库
- [libwebp](https://developers.google.com/speed/webp) - WebP 格式参考实现
- [Wuffs](https://github.com/google/wuffs) - 内存安全的文件格式解析库
- [libavif](https://github.com/AOMediaCodec/libavif) - AVIF 格式参考实现
- [libjxl](https://github.com/libjxl/libjxl) - JPEG XL 参考实现
- [CrabbyAvif](https://github.com/nicholascw/crabbyavif) - Rust 实现的 AVIF 解码器
- [Wuffs 图像解码器文档](https://github.com/google/wuffs/blob/master/doc/std/image-decoders.md) - Wuffs 图像解码 API 说明
