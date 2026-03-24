# SkExif

> 源文件: `include/private/SkExif.h`

## 概述

SkExif 命名空间提供了 EXIF(Exchangeable Image File Format)元数据的解析和写入功能。EXIF 是数码相机和图像处理软件常用的元数据格式,用于存储图像方向、分辨率、HDR 属性等信息。该模块是 Skia 图像编解码系统的重要组成部分。

## 架构位置

SkExif 位于 Skia 的图像编解码层,作为元数据处理的工具命名空间。它主要服务于 JPEG 编解码器,为图像的元数据提取和嵌入提供标准化接口。该模块定义在 `include/private` 目录,属于 Skia 内部 API。

## 主要类与结构体

### Metadata 结构体

Metadata 结构体包含了从 EXIF 数据中解析出的各种元数据字段,所有字段都使用 `std::optional` 包装,表示该字段可能不存在。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fOrigin | std::optional<SkEncodedOrigin> | 图像方向,用于正确旋转显示图像 |
| fHdrHeadroom | std::optional<float> | HDR 动态范围余量,Apple HDR 效果的关键参数 |
| fResolutionUnit | std::optional<uint16_t> | 分辨率单位(英寸或厘米) |
| fXResolution | std::optional<float> | X 方向分辨率(DPI/DPCM) |
| fYResolution | std::optional<float> | Y 方向分辨率(DPI/DPCM) |
| fPixelXDimension | std::optional<uint32_t> | 图像有效像素宽度 |
| fPixelYDimension | std::optional<uint32_t> | 图像有效像素高度 |

## EXIF 标签常量

SkExif 命名空间定义了常用的 EXIF 标签值:

| 常量名 | 值 | EXIF 标签名称 | 说明 |
|--------|-----|---------------|------|
| kOriginTag | 0x112 | Orientation | 图像方向标签 |
| kResolutionUnitTag | 0x0128 | ResolutionUnit | 分辨率单位标签 |
| kXResolutionTag | 0x011a | XResolution | X 分辨率标签 |
| kYResolutionTag | 0x011b | YResolution | Y 分辨率标签 |
| kPixelXDimensionTag | 0xa002 | PixelXDimension | 像素宽度标签(EXIF 子 IFD) |
| kPixelYDimensionTag | 0xa003 | PixelYDimension | 像素高度标签(EXIF 子 IFD) |

## 公共 API 函数

### `void SK_API Parse(Metadata& metadata, const SkData* data)`
- **功能**: 解析 EXIF 数据并填充到 Metadata 结构体中
- **参数**:
  - `metadata`: 输出参数,解析结果将写入此结构体
  - `data`: 包含 EXIF 数据的 SkData 对象
- **返回值**: 无(通过引用参数返回结果)
- **说明**: 该函数容错性强,即使遇到截断的输入也会继续解析,只在不可恢复的错误时停止

### `sk_sp<SkData> WriteExif(Metadata& metadata)`
- **功能**: 将 Metadata 结构体序列化为完整的 EXIF 数据块
- **参数**: `metadata` - 要写入的元数据
- **返回值**: 包含 EXIF 数据的 SkData 智能指针,失败时返回 nullptr
- **说明**:
  - 如果 metadata.fHdrHeadroom 有值,函数会返回 nullptr,因为无法写入该字段(缺少 maker33 和 maker48 信息)
  - 属于子 IFD 的元数据会被写入独立的子 IFD 并放置在根 IFD 之后
  - 超出单个条目大小的数据会被附加到数据末尾

## 内部实现细节

### EXIF 数据结构

EXIF 数据遵循 TIFF 格式规范,主要包含:

1. **TIFF 头部**: 包含字节序标记和 IFD 偏移量
2. **IFD (Image File Directory)**: 包含标签条目的目录
3. **标签条目**: 每个条目包含标签 ID、类型、计数和值/偏移量
4. **值数据区**: 存储超过 4 字节的值数据

### 解析流程

Parse 函数的处理流程:

1. **验证数据有效性**: 检查最小长度和 TIFF 头部
2. **确定字节序**: 根据 TIFF 头部的标记确定大小端
3. **遍历 IFD**: 读取每个标签条目
4. **提取已知标签**: 将识别的标签值填充到 Metadata 结构体
5. **处理子 IFD**: 如果存在 EXIF 子 IFD,递归解析

### 写入流程

WriteExif 函数的处理流程:

1. **计算所需空间**: 统计标签数量和数据大小
2. **写入 TIFF 头部**: 使用大端字节序(标准 EXIF 格式)
3. **写入根 IFD**: 包含基本图像属性标签
4. **写入子 IFD**: 如果有 EXIF 特定标签,创建子 IFD
5. **写入值数据**: 将超大值数据附加到末尾

### HDR Headroom 处理

fHdrHeadroom 字段对应 Apple 的 HDR 效果元数据,存储在特定的 maker note 中。由于在解码过程中会丢失 maker33 和 maker48 的原始信息,WriteExif 无法重新构造这些数据,因此当该字段存在时会返回失败。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/codec/SkEncodedOrigin.h` | 提供图像方向枚举 |
| `include/core/SkRefCnt.h` | 提供引用计数基类 |
| `include/core/SkData.h` | 提供二进制数据容器 |
| `include/private/base/SkAPI.h` | 提供 API 导出宏 |
| `<cstdint>` | 提供标准整数类型 |
| `<optional>` | 提供可选值包装器 |

### 被依赖的模块

SkExif 命名空间被以下模块使用:

- **SkJpegCodec**: JPEG 编解码器使用 SkExif 解析和写入元数据
- **SkJpegMetadataDecoder**: JPEG 元数据解码器内部使用 SkExif 处理 EXIF 段
- **SkJpegEncoder**: JPEG 编码器使用 WriteExif 嵌入元数据
- **图像工具**: 各种图像处理工具使用该接口读取图像属性

## 设计模式与设计决策

### 命名空间设计

使用命名空间而非类封装的原因:
- EXIF 解析是无状态操作,不需要维护对象状态
- 简化 API,避免不必要的对象创建和销毁
- 所有功能都是静态的工具函数

### Optional 模式

所有 Metadata 字段都使用 `std::optional` 包装,这样设计的优势:
- **表达存在性**: 清晰表示某个元数据是否在原始数据中存在
- **类型安全**: 避免使用魔法值(如 -1 或 0)表示"不存在"
- **现代 C++ 风格**: 符合 C++17 的最佳实践

### 容错性设计

Parse 函数被设计为高度容错:
- 允许截断的输入数据
- 只在完全无法解析时才停止
- 部分成功的解析结果仍然有效

这种设计考虑了实际应用中可能遇到的损坏或不完整的图像文件。

## 性能考量

### 解析性能

EXIF 解析是线性时间操作 O(n),其中 n 是 EXIF 数据大小:
- 通常 EXIF 数据很小(几 KB),解析速度很快
- 避免了动态内存分配(使用栈上的 Metadata 结构)
- 标签查找使用直接比较,无需哈希表

### 写入性能

WriteExif 需要两次遍历:
1. 第一次计算所需空间
2. 第二次实际写入数据

这种方式避免了多次内存重新分配,提高了整体性能。

### 内存使用

Metadata 结构体非常紧凑:
- 7 个 optional 字段,每个约 8-16 字节
- 总计约 100 字节左右
- 无动态内存分配

## 平台相关说明

### 字节序处理

EXIF 标准允许大端或小端字节序,但实际中:
- JPEG 文件通常使用大端(Motorola 格式)
- Parse 函数自动检测字节序
- WriteExif 固定使用大端以确保兼容性

### Apple HDR 扩展

fHdrHeadroom 字段是 Apple 特有的扩展:
- 用于 Apple 设备的 HDR 照片效果
- 存储在 maker note 中,格式不公开
- 其他平台可能不支持此特性

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/codec/SkJpegCodec.cpp` | 使用 SkExif::Parse 解析 JPEG 元数据 |
| `src/encode/SkJpegEncoder.cpp` | 使用 SkExif::WriteExif 写入元数据 |
| `include/private/SkJpegMetadataDecoder.h` | 提供更高层的元数据解码接口 |
| `include/codec/SkEncodedOrigin.h` | 定义图像方向枚举 |
| `src/codec/SkExifPriv.cpp` | SkExif 的内部实现 |
