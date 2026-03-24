# SkJpegMetadataDecoderImpl - JPEG 元数据解码器实现

> 源文件: `src/codec/SkJpegMetadataDecoderImpl.h`, `src/codec/SkJpegMetadataDecoderImpl.cpp`

## 概述

`SkJpegMetadataDecoderImpl` 是 `SkJpegMetadataDecoder` 接口的具体实现，负责从 JPEG 图像中提取各种元数据，包括 EXIF 信息、ICC 颜色配置文件、XMP 数据、ISO 21496-1 增益图（Gainmap）元数据以及 JUMBF 元数据。该类还实现了从多图片格式（MPF）的 JPEG 文件中查找和提取增益图图像的功能，支持 ISO、Adobe 和 Apple 三种增益图格式。

## 架构位置

该类位于 Skia 的 JPEG 编解码模块中，是 JPEG 元数据处理子系统的核心。它与 `SkJpegSourceMgr`（数据源管理）、`SkJpegMultiPicture`（多图片参数解析）和 `SkJpegSegmentScan`（段扫描）协同工作。

```
SkJpegMetadataDecoder (公共接口)
  └── SkJpegMetadataDecoderImpl (具体实现)
        ├── SkJpegSourceMgr (数据访问)
        ├── SkJpegMultiPictureParameters (MPF 解析)
        ├── SkJpegSegmentScanner (段扫描)
        └── SkXmp (XMP 元数据解析)
```

## 主要类与结构体

### `SkJpegMetadataDecoderImpl`
- 继承自 `SkJpegMetadataDecoder`
- 维护一个 JPEG 标记列表 (`fMarkerList`)
- 提供两种构造方式：从标记列表构造或从原始数据构造

### 类型别名
- `SkJpegMarker`: 等同于 `SkJpegMetadataDecoder::Segment`
- `SkJpegMarkerList`: `std::vector<SkJpegMarker>`

## 公共 API 函数

### 构造函数
- `SkJpegMetadataDecoderImpl(SkJpegMarkerList markerList)`: 从预解析的标记列表构造
- `SkJpegMetadataDecoderImpl(sk_sp<const SkData> data)`: 从原始 JPEG 数据构造，内部通过段扫描器提取 APP1 和 APP2 段

### 元数据提取
- `getExifMetadata(bool copyData)`: 提取 EXIF 元数据
- `getICCProfileData(bool copyData)`: 提取 ICC 颜色配置文件（支持多段拼接）
- `getISOGainmapMetadata(bool copyData)`: 提取 ISO 21496-1 增益图元数据
- `getJUMBFMetadata(bool copyData)`: 提取 JUMBF 元数据

### 增益图功能
- `mightHaveGainmapImage()`: 快速检查是否可能包含增益图（通过检测 MPF 参数）
- `findGainmapImage(SkJpegSourceMgr*)`: 从源管理器中查找增益图图像
- `findGainmapImage(sk_sp<const SkData>)`: 从数据中查找增益图图像
- `getXmpMetadata()`: 提取 XMP 元数据（条件编译，需 `SK_CODEC_DECODES_JPEG_GAINMAPS`）

## 内部实现细节

### `read_metadata` 函数
核心的元数据读取函数，支持以下特性：
- 基于标记类型和签名的段匹配
- 大端序多字节索引解析，用于多段元数据（如 ICC Profile）
- 自动拼接多段数据，验证段计数一致性和完整性
- 可选零拷贝模式（`alwaysCopyData=false` 时直接引用解码器数据）

### 增益图查找流程
`findGainmapImage(SkJpegSourceMgr*)` 实现了复杂的增益图搜索逻辑：
1. 解析基础图像的 EXIF 和 XMP 元数据
2. 检测 ISO 21496-1、Adobe HDR 和 Apple 增益图格式标识
3. 通过容器 XMP 定位增益图偏移量
4. 查找 MPF 参数和对应的段信息
5. 遍历 MPF 图像，提取并验证增益图
6. 回退到容器 XMP 指定的位置

### `extract_gainmap` 函数
从指定偏移和大小提取增益图的内部函数：
1. 从源管理器提取子集数据
2. 创建嵌套的 `SkJpegMetadataDecoderImpl` 解析增益图元数据
3. 按优先级检查 ISO 21496-1、Adobe 和 Apple 格式
4. 处理 ISO 格式中增益图颜色空间的特殊要求

### 条件编译
增益图相关功能由 `SK_CODEC_DECODES_JPEG_GAINMAPS` 宏控制。未启用时，增益图函数返回空结果。

## 依赖关系

- `SkJpegMetadataDecoder`: 基类接口
- `SkJpegSourceMgr`: JPEG 数据源管理
- `SkJpegMultiPictureParameters`: MPF 参数解析
- `SkJpegSegmentScanner`: JPEG 段扫描
- `SkXmp`: XMP 元数据解析
- `SkExif`: EXIF 元数据解析
- `SkGainmapInfo`: 增益图信息结构
- `SkJpegConstants`: JPEG 常量定义（标记类型、签名等）
- `SkData`: 数据管理
- `skcms`: 颜色管理（ICC 配置文件解析）

## 设计模式与设计决策

### 延迟解析
从原始数据构造时，仅扫描到 StartOfScan 标记即停止，避免完整解码图像。

### 零拷贝优化
当 `copyData=false` 且元数据仅包含单个段时，返回直接引用解码器内存的 `SkData`，避免内存拷贝。

### 多格式兼容
增益图检测同时支持三种业界格式（ISO、Adobe、Apple），按优先级依次尝试。

### 防御性编程
- `marker_has_signature` 严格验证标记类型和签名
- 多段元数据验证段计数一致性和无重复
- 增益图提取验证 MPF 偏移量与容器 XMP 的一致性

## 性能考量

- 元数据提取是按需进行的，不会预加载所有元数据
- `mightHaveGainmapImage()` 提供快速预检，避免不必要的完整扫描
- 多段元数据拼接使用预分配的向量和累计大小计算，减少内存重分配
- 增益图搜索在找到第一个有效结果后立即返回
- 从内存映射流构造时避免数据拷贝

## 相关文件

- `include/private/SkJpegMetadataDecoder.h`: 公共接口定义
- `src/codec/SkJpegMultiPicture.h` / `.cpp`: MPF 参数解析
- `src/codec/SkJpegSourceMgr.h` / `.cpp`: JPEG 数据源管理
- `src/codec/SkJpegSegmentScan.h`: JPEG 段扫描器
- `src/codec/SkJpegConstants.h`: JPEG 常量定义
- `src/codec/SkJpegXmp.h`: JPEG XMP 处理
- `include/private/SkGainmapInfo.h`: 增益图信息
- `include/private/SkXmp.h`: XMP 元数据接口
