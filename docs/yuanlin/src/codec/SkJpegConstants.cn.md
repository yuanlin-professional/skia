# SkJpegConstants - JPEG 格式常量定义

> 源文件: `src/codec/SkJpegConstants.h`

## 概述

`SkJpegConstants.h` 定义了 JPEG 图像格式处理中使用的各类常量，包括 JPEG 标记代码、段参数、ICC 配置文件签名、XMP 元数据签名、EXIF 签名、MPF（Multi-Picture Format）签名、ISO 21496-1 增益图签名以及 JUMBF（JPEG Universal Metadata Box Format）签名。这些常量被 Skia 的 JPEG 编解码器和元数据解析器广泛使用。

## 架构位置

该文件位于 `src/codec/` 目录下，是 JPEG 相关编解码和元数据处理的基础常量库。它被 JPEG 解码器、EXIF 解析器、XMP 解析器、增益图解析器等多个组件引用，提供了统一的 JPEG 格式常量定义。

## 主要类与结构体

该文件不定义类或结构体，仅包含 `static constexpr` 常量。

## 公共 API 函数

无函数定义。

## 内部实现细节

### JPEG 基础标记
- `kJpegMarkerStartOfImage`(0xD8): JPEG 文件起始标记
- `kJpegMarkerEndOfImage`(0xD9): JPEG 文件结束标记
- `kJpegMarkerStartOfScan`(0xDA): 扫描开始标记（头部与图像数据的分界）
- `kJpegMarkerAPP0`(0xE0): APP0 标记（APP1-APP15 通过偏移计算）

### JPEG 格式参数
- `kJpegMarkerCodeSize = 2`: 标记代码占 2 字节（0xFF + 标记值）
- `kJpegSegmentParameterLengthSize = 2`: 段参数长度字段占 2 字节（包含自身）
- `kJpegSig[] = {0xFF, 0xD8, 0xFF}`: JPEG 文件签名（SOI + 下一标记的首字节）

### ICC 配置文件常量
- `kICCMarker = APP0 + 2 = 0xE2`: ICC 存储在 APP2 段
- `kICCMarkerHeaderSize = 14`: ICC 段头大小
- `kICCMarkerIndexSize = 1`: ICC 分块索引占 1 字节
- `kICCSig[] = "ICC_PROFILE\0"`: ICC 签名（12 字节 + 空终止符）

### XMP 元数据常量
- `kXMPMarker = APP0 + 1 = 0xE1`: XMP 存储在 APP1 段
- `kXMPStandardSig[]`: 标准 XMP 签名 `"http://ns.adobe.com/xap/1.0/\0"`
- `kXMPExtendedSig[]`: 扩展 XMP 签名 `"http://ns.adobe.com/xmp/extension/\0"`

### EXIF 常量
- `kExifMarker = APP0 + 1 = 0xE1`: EXIF 同样存储在 APP1 段（与 XMP 共用）
- `kExifSig[] = "Exif\0"`: EXIF 签名

### MPF（Multi-Picture Format）常量
- `kMpfMarker = APP0 + 2 = 0xE2`: MPF 存储在 APP2 段
- `kMpfSig[] = "MPF\0"`: MPF 签名

### ISO 21496-1 增益图常量
- `kISOGainmapMarker = APP0 + 2 = 0xE2`: ISO 增益图存储在 APP2 段
- `kISOGainmapSig[]`: 签名 `"urn:iso:std:iso:ts:21496:-1\0"`

### JUMBF 常量
- `kJumbfMarker = APP0 + 11 = 0xEB`: JUMBF 存储在 APP11 段
- `kJumbfSig[] = "JP"`: JUMBF 签名

## 依赖关系

- `<cstddef>`: `size_t` 类型
- `<cstdint>`: `uint8_t`, `uint32_t` 类型

## 设计模式与设计决策

1. **编译时常量**: 所有值均为 `static constexpr`，在编译时确定，无运行时开销。

2. **字节数组签名**: 签名使用字符数组而非字符串字面量，确保精确匹配（包含空终止符位置）。

3. **APP 段偏移计算**: 通过 `kJpegMarkerAPP0 + N` 计算 APP 段标记，避免硬编码每个 APP 标记值。

4. **非 static 的 EXIF 签名**: `kExifSig` 缺少 `static` 关键字（可能是有意为之，允许在多个编译单元中使用）。

## 性能考量

- **零运行时开销**: 所有常量在编译时求值
- **内联友好**: `constexpr` 常量可被编译器内联到使用点
- **签名匹配优化**: 固定大小的字节数组可使用 `memcmp` 进行高效比较

## 相关文件

- JPEG 编解码器文件（使用这些常量进行标记解析）
- `src/codec/SkExif.cpp`: EXIF 解析（使用 `kExifMarker` 和 `kExifSig`）
- `src/codec/SkXmp.cpp`: XMP 解析（使用 `kXMPMarker` 和 XMP 签名）
- `src/codec/SkGainmapInfo.cpp`: 增益图解析（使用 ISO 增益图常量）
