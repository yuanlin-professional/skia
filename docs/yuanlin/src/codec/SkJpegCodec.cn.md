# SkJpegCodec — JPEG 图像解码器

> 源文件：[src/codec/SkJpegCodec.h](../../src/codec/SkJpegCodec.h)、[src/codec/SkJpegCodec.cpp](../../src/codec/SkJpegCodec.cpp)

## 概述

`SkJpegCodec` 是 Skia 图像编解码框架中的 JPEG 解码器实现。它继承自 `SkCodec`，封装了 libjpeg-turbo 库来实现 JPEG 图像的解码，支持以下功能：

- JPEG 格式检测（magic number 验证）
- 基线（Baseline）和渐进式（Progressive）JPEG 解码
- 多种输出色彩格式（RGBA_8888、BGRA_8888、RGB_565、Gray_8 等）
- CMYK/YCCK 色彩空间转换
- libjpeg-turbo 原生缩放（1/8 到 1/1，步长 1/8）
- YUV（YCbCr）原始数据解码，支持 444/422/420/440/411/410 子采样
- 扫描线（scanline）逐行解码模式
- 子集解码（通过 libjpeg-turbo 的 `jpeg_crop_scanline`）
- ICC 颜色配置文件和 EXIF 方向信息的提取
- Gainmap（增益图）解码支持

## 架构位置

```
SkCodec (抽象基类)
    │
    └── SkJpegCodec
            │
            ├── JpegDecoderMgr (libjpeg-turbo 封装管理器)
            │   ├── jpeg_decompress_struct (libjpeg-turbo 核心结构)
            │   ├── skjpeg_error_mgr (错误处理)
            │   └── skjpeg_source_mgr (数据源管理)
            │
            ├── SkSwizzler (像素格式转换)
            ├── SkJpegMetadataDecoderImpl (元数据解析)
            └── SkCodecs::ColorProfile (颜色配置)
```

## 主要类与结构体

### `SkJpegCodec`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDecoderMgr` | `unique_ptr<JpegDecoderMgr>` | libjpeg-turbo 解压管理器 |
| `fReadyState` | `const int` | 读取头信息后的 decompressor 全局状态快照 |
| `fStorage` | `AutoTMalloc<uint8_t>` | Swizzle 和颜色转换的临时缓冲区 |
| `fSwizzleSrcRow` | `uint8_t*` | Swizzle 源行指针 |
| `fColorXformSrcRow` | `uint32_t*` | 颜色转换源行指针 |
| `fSwizzlerSubset` | `SkIRect` | Swizzler 的子集裁剪区域 |
| `fSwizzler` | `unique_ptr<SkSwizzler>` | 像素格式转换器 |

## 公共 API 函数

### 静态方法

- **`IsJpeg(const void*, size_t) -> bool`**：通过检查 JPEG 签名字节判断数据是否为 JPEG 格式。
- **`MakeFromStream(unique_ptr<SkStream>, Result*) -> unique_ptr<SkCodec>`**：从数据流创建 JPEG 解码器。读取头信息、提取 EXIF 方向和 ICC 配置文件、验证颜色空间匹配。

### 虚函数实现

- **`onGetScaledDimensions(float desiredScale) -> SkISize`**：根据请求的缩放比例返回 libjpeg-turbo 支持的最接近缩放后尺寸。支持的比例为 1/8、1/4、3/8、1/2、5/8、3/4、7/8、1/1。
- **`onGetPixels(...) -> Result`**：执行完整图像解码。处理基线和渐进式 JPEG，管理内存预算，执行行读取和像素转换。
- **`onQueryYUVAInfo(...) -> bool`**：查询是否支持 YUV 解码及其参数（子采样格式、平面布局）。
- **`onGetYUVAPlanes(const SkYUVAPixmaps&) -> Result`**：执行 YUV 原始数据解码，直接输出 Y、U、V 三个平面。
- **`onRewind() -> bool`**：回绕流以重新开始解码。重置所有内部状态。
- **`onDimensionsSupported(const SkISize&) -> bool`**：检查指定尺寸是否可通过 libjpeg-turbo 的缩放实现。
- **`conversionSupported(...) -> bool`**：检查目标颜色格式是否被支持，并配置 libjpeg-turbo 输出颜色空间。
- **`onGetGainmapCodec(...) / onGetGainmapInfo(...)`**：提取和解码 JPEG 增益图元数据。

### 扫描线解码

- **`onStartScanlineDecode(...) -> Result`**：初始化扫描线解码模式，处理子集裁剪。
- **`onGetScanlines(...) -> int`**：逐行读取解码数据。
- **`onSkipScanlines(int count) -> bool`**：跳过指定行数。

## 内部实现细节

### 解码流程

1. **头部读取**：`read_header()` 创建 `JpegDecoderMgr`，初始化 libjpeg-turbo，保存 EXIF/ICC/MPF 标记。
2. **颜色空间协商**：`conversionSupported()` 根据目标格式设置 libjpeg-turbo 的 `out_color_space`。CMYK 图像特殊处理，始终输出 JCS_CMYK 再由 Swizzler 转 RGB。
3. **解压启动**：对渐进式 JPEG 设置 `buffered_image=TRUE`，先消耗所有输入扫描，然后输出最后一个完整扫描。
4. **行读取管道**：`readRows()` 实现三级管道：
   - libjpeg-turbo → `fSwizzleSrcRow`（如需 Swizzle）
   - Swizzle → `fColorXformSrcRow`（如需颜色转换）
   - 颜色转换 → 最终目标缓冲区

### CMYK 处理

当 JPEG 编码为 CMYK 或 YCCK 时：
- libjpeg-turbo 不直接支持 CMYK 到 RGBA 的转换
- 如果有 CMYK ICC 配置文件且启用了颜色转换，由颜色转换器处理
- 否则使用 `SkSwizzler` 执行 InvertedCMYK 到 RGB 的转换

### YUV 解码

使用 `jpeg_read_raw_data()` 以 DCTSIZE（8）行为单位读取原始 YCbCr 数据：
- Y 平面按 `v_samp_factor * DCTSIZE` 行读取
- U、V 平面按 DCTSIZE 行读取
- 最后不足一个块的行使用额外缓冲区填充

### 内存预算管理

解码时估算 libjpeg-turbo 的内部内存需求：
- 渐进式 JPEG：`6 * width * height` 字节
- 基线 JPEG：`34 * width` 字节
通过 `allocateFromBudget()` 检查预算是否允许。

### 缩放实现

`onGetScaledDimensions()` 使用临时的 `jpeg_decompress_struct` 调用 `jpeg_calc_output_dimensions()` 来获取精确的缩放后尺寸，避免修改实际解码使用的结构体。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| libjpeg-turbo (`jpeglib.h`) | 底层 JPEG 解码库 |
| `JpegDecoderMgr` | libjpeg-turbo 封装（错误管理、源管理） |
| `SkSwizzler` | 像素格式转换（CMYK→RGB、子集裁剪） |
| `SkJpegMetadataDecoderImpl` | JPEG 元数据（EXIF、ICC、MPF）解析 |
| `SkCodec` | 编解码器基类 |
| `SkCodecs::ColorProfile` | ICC 颜色配置文件 |
| `skcms` | 颜色管理系统 |
| `SkYUVAInfo` / `SkYUVAPixmaps` | YUV 平面布局和数据 |
| `SkParseEncodedOrigin` | EXIF 方向解析 |

## 设计模式与设计决策

1. **setjmp/longjmp 错误处理**：libjpeg-turbo 使用 longjmp 作为错误恢复机制。每个可能触发 libjpeg 错误的方法开头都设置 `setjmp` 跳转点，错误发生时 longjmp 回跳，返回错误码而非崩溃。

2. **三级像素管道**：解码 → Swizzle → 颜色转换的分离设计允许灵活组合不同的处理步骤。当不需要某个步骤时直接跳过，避免不必要的内存分配和拷贝。

3. **友元类 SkRawCodec**：`SkRawCodec` 作为友元类可以使用带默认颜色配置文件参数的私有 `MakeFromStream` 重载，用于从 EXIF 数据传递颜色配置。

4. **fReadyState 快照**：在头部读取后保存 decompressor 的全局状态，允许创建临时的 decompressor 结构体来计算缩放尺寸，而不影响实际解码状态。

5. **渐进式 JPEG 优化**：对渐进式 JPEG 先消耗所有输入数据确定最后完成的扫描编号，再从该扫描输出，确保输出质量最佳且处理不完整数据。

## 性能考量

- **libjpeg-turbo 原生缩放**：利用 DCT 系数跳过实现 1/8 到 1/1 的缩放，比解码全分辨率再缩放快数倍。
- **YUV 直出**：`onGetYUVAPlanes()` 输出原始 YCbCr 数据，避免色彩空间转换开销，适合 GPU 纹理上传。
- **内存预算控制**：通过 `allocateFromBudget()` 防止大图解码消耗过多内存。
- **子集裁剪**：利用 `jpeg_crop_scanline()` 在 libjpeg-turbo 层面减少处理的列数，配合 Swizzler 进一步精确子集。
- **零拷贝路径**：当不需要 Swizzle 和颜色转换时，libjpeg-turbo 直接解码到目标缓冲区，避免中间拷贝。

## 相关文件

- `src/codec/SkJpegDecoderMgr.h` — libjpeg-turbo 解压管理器
- `src/codec/SkJpegPriv.h` — JPEG 内部常量和工具
- `src/codec/SkJpegConstants.h` — JPEG 标记常量
- `src/codec/SkJpegMetadataDecoderImpl.h` — JPEG 元数据解码
- `src/codec/SkSwizzler.h` — 像素格式转换器
- `src/codec/SkParseEncodedOrigin.h` — 图像方向解析
- `include/codec/SkJpegDecoder.h` — JPEG 解码器公共命名空间
