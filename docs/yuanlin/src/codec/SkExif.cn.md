# SkExif - EXIF 元数据解析与序列化

> 源文件: `src/codec/SkExif.cpp`

## 概述

`SkExif.cpp` 实现了 EXIF（Exchangeable Image File Format）元数据的解析和序列化功能。EXIF 是数码相机和智能手机拍摄的 JPEG/TIFF 图像中嵌入的元数据标准，包含方向、分辨率、像素尺寸等信息。该文件还实现了 Apple iOS HDR 增益图的 MakerNote 解析，用于从 Apple 设备拍摄的照片中提取 HDR 头部余量（headroom）信息。文件同时包含了将 EXIF 元数据序列化为二进制 IFD（Image File Directory）格式的写入功能。

## 架构位置

该文件位于 `src/codec/` 目录下，属于 Skia 图像解码子系统的元数据处理层。它被 JPEG 解码器在解析 APP1 段时调用，用于提取图像的方向、HDR 信息等。解析后的 `SkExif::Metadata` 结构会影响图像的显示方向和 HDR 渲染。

## 主要类与结构体

该文件在 `SkExif` 命名空间中操作 `Metadata` 结构体（定义在头文件中），主要字段包括：
- `fOrigin`: 图像方向（`SkEncodedOrigin`）
- `fHdrHeadroom`: HDR 头部余量（Apple MakerNote）
- `fXResolution`, `fYResolution`: X/Y 方向分辨率
- `fResolutionUnit`: 分辨率单位
- `fPixelXDimension`, `fPixelYDimension`: 像素尺寸（来自 ExifIFD）

## 公共 API 函数

### `SkExif::Parse(Metadata&, const SkData*)`
解析 EXIF 二进制数据，填充 `Metadata` 结构。
- 首先通过 `SkTiff::ImageFileDirectory::ParseHeader` 解析 TIFF 头（确定字节序和首 IFD 偏移）
- 然后递归解析 IFD 条目，包括子 IFD（ExifIFD）

### `SkExif::WriteExif(Metadata&)`
将 `Metadata` 序列化为 EXIF 二进制数据（`sk_sp<SkData>`）。
- 生成大端 TIFF 格式的 IFD 结构
- 支持 IFD0 和 SubIFD（ExifIFD）的层级写入
- 不支持写入 MakerNote（HDR headroom 信息在编码时丢失）

## 内部实现细节

### Apple MakerNote HDR 解析
`get_maker_note_hdr_headroom()` 从 Apple iOS 设备的 MakerNote 数据中提取 HDR 头部余量：
1. 验证 "Apple iOS" 签名（`'A','p','p','l','e',' ','i','O','S',0,0,1,'M','M'`）
2. 解析 MakerNote 中的 tag 33（maker33）和 tag 48（maker48）
3. 通过分段线性公式计算 HDR stops：
   - maker33 < 1.0: stops = -20.0*maker48 + 1.8（或 -0.101*maker48 + 1.601）
   - maker33 >= 1.0: stops = -70.0*maker48 + 3.0（或 -0.303*maker48 + 2.303）
4. 返回 `pow(2, max(stops, 0))` 作为线性头部余量

### IFD 递归解析
`parse_ifd()` 遍历 IFD 条目，处理以下标签：
- `kOriginTag`: 图像方向（1-8）
- `kMarkerNoteTag`(0x927c): Apple MakerNote
- `kSubIFDOffsetTag`(0x8769): 子 IFD 偏移（ExifIFD）
- `kXResolutionTag`, `kYResolutionTag`: 分辨率（无符号有理数）
- `kResolutionUnitTag`: 分辨率单位（无符号短整数）
- `kPixelXDimensionTag`, `kPixelYDimensionTag`: 像素尺寸（支持 uint16 和 uint32 两种类型）

### EXIF 写入逻辑
`WriteExif()` 的写入流程：
1. 写入大端 TIFF 头（"MM" + IFD0 偏移）
2. 统计有效标签数量（包括 SubIFD 指针）
3. 计算所有数据的偏移量（IFD 条目 + 大值缓冲区）
4. 按标签顺序写入 IFD 条目
5. 如有 SubIFD，紧随 IFD0 后写入
6. 附加超过 4 字节的值数据（如有理数）

`write_entry()` 辅助函数处理不同标签类型的写入格式差异。

## 依赖关系

- `include/private/SkExif.h`: 公共接口和 Metadata 定义
- `include/core/SkData.h`, `SkStream.h`: 数据和流接口
- `src/codec/SkTiffUtility.h`: TIFF IFD 解析工具
- `src/codec/SkCodecPriv.h`: 编解码器私有工具（`SkCodecPrintf`）
- `src/core/SkStreamPriv.h`: 流的大端读写辅助函数

## 设计模式与设计决策

1. **首次赋值语义**: 使用 `has_value()` 检查确保每个字段只被第一次出现的值填充，符合 EXIF 规范的优先级规则。

2. **递归 IFD 解析**: 通过 `isRoot` 标志限制只在根 IFD 中跟随 SubIFD 偏移，防止循环引用。

3. **容错性**: 使用 `allowTruncated=true` 允许解析被截断的 EXIF 数据。

4. **MakerNote 不可逆性**: 写入时明确拒绝将 HDR headroom 转回 MakerNote 格式，因为原始 maker33/maker48 值不可恢复。

## 性能考量

- **单遍解析**: 所有 IFD 条目在单次遍历中处理
- **零拷贝数据引用**: 使用 `SkData::MakeWithoutCopy` 避免复制原始 EXIF 数据
- **按需解析**: 只解析已知标签，跳过未识别的条目
- **流式写入**: 写入使用 `SkDynamicMemoryWStream`，避免预分配固定缓冲区

## 相关文件

- `include/private/SkExif.h`: EXIF 元数据公共接口
- `src/codec/SkTiffUtility.h`: TIFF/IFD 解析工具
- `src/codec/SkJpegConstants.h`: JPEG 常量定义（包含 EXIF 标记签名）
- `src/core/SkStreamPriv.h`: 大端流读写工具
