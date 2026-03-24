# SkJpegMetadataDecoder

> 源文件: `include/private/SkJpegMetadataDecoder.h`

## 概述

SkJpegMetadataDecoder 是一个用于从 JPEG 编码文件中提取元数据的接口类。它提供了访问 EXIF 数据、ICC 配置文件、ISO 21496-1 Gainmap 元数据和 JUMBF 超级盒等多种元数据格式的统一接口。该类是 Skia JPEG 解码管线中处理元数据的核心抽象层。

## 架构位置

SkJpegMetadataDecoder 位于 Skia 图像编解码层的元数据处理子系统。它作为 JPEG 元数据的高层抽象接口,隔离了底层 JPEG 格式解析的复杂性,为上层图像加载和处理代码提供清晰的元数据访问 API。该类定义在 `include/private` 目录中。

## 主要类与结构体

### SkJpegMetadataDecoder

这是一个抽象接口类,定义了 JPEG 元数据访问的标准方法。具体实现由内部类提供。

**继承关系**: `SkJpegMetadataDecoder` (抽象基类)

**设计特点**:
- 禁用拷贝构造和赋值操作
- 所有元数据访问方法都是纯虚函数
- 使用工厂方法创建实例

### Segment 结构体

表示 JPEG 文件中的一个段(marker segment),这是 JPEG 文件格式的基本组成单元。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fMarker | uint8_t | 段的标记字节,标识段的类型(如 0xE0 表示 APP0) |
| fData | sk_sp<const SkData> | 段的参数数据(不包括标记和长度字段) |

**构造函数**:
```cpp
Segment(uint8_t marker, sk_sp<const SkData> data)
```

## 公共 API 函数

### 工厂方法

#### `static std::unique_ptr<SkJpegMetadataDecoder> Make(std::vector<Segment> headerSegments)`
- **功能**: 从 JPEG 文件头部的段列表创建元数据解码器
- **参数**: `headerSegments` - JPEG 头部段的向量(StartOfScan 之前的所有段)
- **返回值**: 元数据解码器的唯一指针,失败时返回 nullptr
- **说明**: 头部段通常包含 APP0-APP15 等应用标记段

#### `static std::unique_ptr<SkJpegMetadataDecoder> Make(sk_sp<const SkData> data)`
- **功能**: 从完整的 JPEG 编码数据创建元数据解码器
- **参数**: `data` - 包含完整 JPEG 文件的数据
- **返回值**: 元数据解码器的唯一指针,失败时返回 nullptr
- **说明**: 此方法会自动解析 JPEG 结构并提取头部段

### 元数据访问方法

#### `virtual sk_sp<const SkData> getExifMetadata(bool copyData) const`
- **功能**: 获取图像附带的 EXIF 元数据
- **参数**: `copyData` - 为 false 时可能返回直接引用原始数据的 SkData
- **返回值**: 包含 EXIF 数据的智能指针,无数据时返回 nullptr
- **说明**: EXIF 数据通常在 APP1 段中

#### `virtual sk_sp<const SkData> getICCProfileData(bool copyData) const`
- **功能**: 获取图像的 ICC 颜色配置文件
- **参数**: `copyData` - 为 false 时可能返回直接引用原始数据的 SkData
- **返回值**: 包含 ICC 配置文件的智能指针,无数据时返回 nullptr
- **说明**: ICC 配置文件通常在 APP2 段中

#### `virtual sk_sp<const SkData> getISOGainmapMetadata(bool copyData) const`
- **功能**: 获取 ISO 21496-1 标准的 Gainmap 元数据
- **参数**: `copyData` - 为 false 时可能返回直接引用原始数据的 SkData
- **返回值**: 包含 Gainmap 元数据的智能指针,无数据时返回 nullptr
- **说明**: Gainmap 用于 HDR 图像的多曝光渲染

#### `virtual sk_sp<const SkData> getJUMBFMetadata(bool copyData) const`
- **功能**: 获取第一个 JUMBF 超级盒
- **参数**: `copyData` - 为 false 时可能返回直接引用原始数据的 SkData
- **返回值**: 包含 JUMBF 数据的智能指针,无数据时返回 nullptr
- **说明**: JUMBF (JPEG Universal Metadata Box Format) 是新的元数据封装格式

### Gainmap 图像提取

#### `virtual bool mightHaveGainmapImage() const`
- **功能**: 检查图像是否可能包含 Gainmap 图像
- **参数**: 无
- **返回值**: true 表示可能包含,false 表示肯定不包含
- **说明**: 这是一个快速检查方法,用于避免不必要的完整解析

#### `virtual std::pair<sk_sp<const SkData>, SkGainmapInfo> findGainmapImage(sk_sp<const SkData>) const`
- **功能**: 从基础图像中提取 Gainmap 图像及其渲染参数
- **参数**: 基础 JPEG 图像数据
- **返回值**: pair 对象,包含 Gainmap 图像数据和渲染参数信息
- **说明**: 返回的 Gainmap 图像也是 JPEG 编码的

#### `virtual bool findGainmapImage(sk_sp<const SkData> baseImageData, sk_sp<SkData>& outGainmapImagedata, SkGainmapInfo& outGainmapInfo)` (已弃用)
- **功能**: 旧版本的 Gainmap 图像提取方法
- **参数**:
  - `baseImageData`: 基础图像数据
  - `outGainmapImagedata`: 输出参数,Gainmap 图像数据
  - `outGainmapInfo`: 输出参数,Gainmap 渲染参数
- **返回值**: true 表示成功提取,false 表示失败
- **说明**: 此方法已标记为 deprecated,建议使用返回 pair 的新版本

## 内部实现细节

### JPEG 段解析

JPEG 文件由一系列段组成,每个段的结构为:
```
[Marker(0xFF + ID)] [Length(2 bytes)] [Data(Length-2 bytes)]
```

SkJpegMetadataDecoder 的实现需要:
1. **识别段类型**: 通过 marker 字节识别 APP0-APP15 等应用段
2. **提取元数据**: 从特定段中提取元数据内容
3. **多段拼接**: 某些大型元数据(如 ICC)可能跨越多个段

### Gainmap 图像定位

Gainmap 图像的提取流程:
1. **检查 MPF 标记**: Multi-Picture Format 段指示是否有额外图像
2. **定位 Gainmap 数据**: 通过偏移量找到 Gainmap 的 JPEG 数据
3. **解析元数据**: 提取 ISO 21496-1 或其他格式的 Gainmap 参数
4. **构造返回值**: 打包 Gainmap 图像和渲染参数

### 零拷贝优化

`copyData` 参数提供了性能优化选项:
- **false**: 返回的 SkData 可能直接引用原始输入数据的内存区域,避免内存拷贝
- **true**: 返回的 SkData 包含独立的内存拷贝,可以在原始数据释放后继续使用

使用者需要根据数据的生命周期需求选择合适的模式。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkData.h` | 提供二进制数据容器 |
| `include/core/SkRefCnt.h` | 提供引用计数智能指针 |
| `include/core/SkTypes.h` | 提供 SK_API 等基础定义 |
| `include/private/SkGainmapInfo.h` | 提供 Gainmap 参数结构 |
| `<memory>` | 提供 unique_ptr |
| `<vector>` | 提供 vector 容器 |

### 被依赖的模块

- **SkJpegCodec**: JPEG 解码器使用此接口获取元数据
- **SkAndroidCodec**: Android 平台的图像解码器
- **图像加载器**: 应用层使用此接口读取图像元信息
- **HDR 图像处理**: Gainmap 相关功能的使用者

## 设计模式与设计决策

### 接口隔离原则

SkJpegMetadataDecoder 作为纯接口类,遵循接口隔离原则:
- 只定义元数据访问的抽象方法
- 不暴露内部解析细节
- 允许多种实现策略

### 工厂方法模式

使用静态工厂方法 `Make()` 创建实例:
- **封装创建逻辑**: 隐藏具体实现类的类型
- **失败处理**: 可以返回 nullptr 表示创建失败
- **灵活性**: 可以根据输入数据选择不同的实现类

### 不可拷贝设计

禁用拷贝构造和赋值操作的原因:
- 元数据解码器通常持有大量内部状态
- 拷贝成本高,且很少有拷贝需求
- 使用智能指针管理生命周期更合适

### 向后兼容性

保留了旧版本的 `findGainmapImage()` 方法:
- 标记为 deprecated,提示用户迁移到新 API
- 确保现有代码不会突然失效
- 给予用户足够的过渡时间

## 性能考量

### 懒加载策略

元数据解码器通常使用懒加载:
- 只在调用 getter 方法时才解析对应的元数据
- 避免解析不需要的元数据
- 减少初始化时间

### 缓存机制

实现类通常会缓存已解析的元数据:
- 第一次调用时解析并缓存结果
- 后续调用直接返回缓存的数据
- 避免重复解析开销

### 内存管理

通过 `copyData` 参数平衡性能和安全性:
- 快速路径(copyData=false): 零拷贝,但数据生命周期受限
- 安全路径(copyData=true): 独立拷贝,但消耗更多内存

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/codec/SkJpegMetadataDecoderImpl.h` | 实现类,提供具体的解析逻辑 |
| `include/private/SkExif.h` | 用于解析 EXIF 格式数据 |
| `include/private/SkGainmapInfo.h` | 定义 Gainmap 渲染参数 |
| `src/codec/SkJpegCodec.cpp` | JPEG 解码器,使用此接口 |
| `include/codec/SkCodec.h` | 通用解码器接口,上层抽象 |
| `src/codec/SkJpegSegmentScan.cpp` | JPEG 段扫描器,提取段数据 |
