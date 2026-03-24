# SkJpegMultiPicture - JPEG 多图片格式解析

> 源文件: `src/codec/SkJpegMultiPicture.h`, `src/codec/SkJpegMultiPicture.cpp`

## 概述

`SkJpegMultiPictureParameters` 实现了 CIPA DC-x007-2009 标准定义的 JPEG 多图片格式（Multi-Picture Format, MPF）的解析和序列化。MPF 允许在单个 JPEG 文件中嵌入多个图像，常用于 HDR 增益图（gainmap）、立体图像和缩略图。该类负责从 APP2 段中解析 MPF 参数，以及将 MPF 参数序列化回 APP2 段格式。

## 架构位置

该类位于 Skia JPEG 编解码模块的元数据处理层，被 `SkJpegMetadataDecoderImpl` 调用以定位嵌入的增益图图像。

```
SkJpegMetadataDecoderImpl
  └── SkJpegMultiPictureParameters (MPF 参数解析)
        └── SkTiff::ImageFileDirectory (IFD 解析)
```

## 主要类与结构体

### `SkJpegMultiPictureParameters`
- 包含嵌入图像列表 (`images`)
- 每个 `Image` 记录 `size`（字节大小）和 `dataOffset`（相对偏移）

### `SkJpegMultiPictureParameters::Image`
- `uint32_t size`: 图像的字节大小
- `uint32_t dataOffset`: 相对于 MP Endian 字段地址的偏移量（第一个图像为 0）

## 公共 API 函数

### 解析
- `static Make(const sk_sp<const SkData>&)`: 从 APP2 段参数解析 MPF 结构。验证 MPF 签名、版本号、IFD 标签顺序，返回解析后的参数或 nullptr。

### 序列化
- `serialize(uint32_t individualImageNumber)`: 将 MPF 参数序列化为 APP2 段数据。第一个图像写入完整的 MP Index IFD，其他图像写入简化的 MP Attribute IFD。

### 偏移计算
- `static GetImageAbsoluteOffset(uint32_t dataOffset, size_t mpSegmentOffset)`: 将 MPF 中的相对偏移转换为文件中的绝对偏移。
- `static GetImageDataOffset(size_t imageAbsoluteOffset, size_t mpSegmentOffset)`: 将文件绝对偏移转换回 MPF 格式的数据偏移。

## 内部实现细节

### 解析流程 (`Make`)
1. 验证 MPF 签名 (`{'M','P','F',0}`)
2. 通过 `SkTiff::ImageFileDirectory::ParseHeader` 确定字节序
3. 创建 Index IFD 并验证标签顺序
4. 解析以下标签：
   - `B000` (Version): 必须为 "0100"
   - `B001` (Number of Images): 图像数量
   - `B002` (MP Entry): 图像条目数据
   - `B003` (Individual Image Unique ID): 可选验证
   - `B004` (Total Number Captured Frames): 可选
5. 逐条解析 MP Entry，验证：
   - 格式为 JPEG
   - 第一个图像为 Primary 类型
   - 第一个图像的偏移为 0
   - Primary 标志与索引一致

### 序列化流程 (`serialize`)
- 始终使用大端字节序
- 对于第一个图像（`individualImageNumber == 0`）：写入 3 个标签（版本、图像数、MP 条目）和完整条目数据
- 对于其他图像：仅写入 1 个标签（版本）

### 偏移计算
MPF 的偏移是相对于 MP Header（即 MP Endian 字段）的位置。绝对偏移计算：
```
absoluteOffset = mpSegmentOffset + markerCodeSize + paramLengthSize + signatureSize + dataOffset
```

### IFD 标签常量
```cpp
kVersionTag = 0xB000
kNumberOfImagesTag = 0xB001
kMPEntryTag = 0xB002
kIndividualImageUniqueIDTag = 0xB003
kTotalNumberCapturedFramesTag = 0xB004
```

## 依赖关系

- `SkTiff::ImageFileDirectory`: TIFF IFD 解析（MPF 使用 TIFF 格式存储元数据）
- `SkData`: 数据管理
- `SkStream` / `SkDynamicMemoryWStream`: 序列化输出
- `SkStreamPriv`: 大端写入工具 (`WriteU16BE`, `WriteU32BE`)
- `SkSafeMath`: 安全数学运算
- `SkJpegConstants`: JPEG 常量（`kMpfSig`）
- `SkJpegSegmentScan`: 段扫描
- `SkEndian`: 字节序处理
- `SkCodecPriv`: `GetEndianInt` 工具

## 设计模式与设计决策

### 严格验证
解析过程对每个标签进行严格验证（版本号、标签顺序、图像格式、大小一致性），遇到不合规数据立即返回 nullptr。

### 读写对称
`Make` 和 `serialize` 互为逆操作，支持完整的 MPF 往返（round-trip）。

### 简化属性 IFD
非第一个图像的序列化仅包含版本标签，因为增益图支持暂未在 CIPA DC-007 中正式定义其他必需标签。

## 性能考量

- 解析使用 `SkData::shareSubset` 共享底层数据，避免拷贝
- 序列化使用 `SkDynamicMemoryWStream` 一次性构建输出
- 偏移计算是简单的算术运算，开销极低

## 相关文件

- `src/codec/SkJpegMetadataDecoderImpl.h` / `.cpp`: 使用 MPF 参数的元数据解码器
- `src/codec/SkTiffUtility.h`: TIFF IFD 解析工具
- `src/codec/SkJpegConstants.h`: JPEG 格式常量
- `src/codec/SkJpegSegmentScan.h`: JPEG 段扫描
- `src/core/SkStreamPriv.h`: 流写入工具
