# SkJpegGainmapEncoder

> 源文件: `include/private/SkJpegGainmapEncoder.h`

## 概述

SkJpegGainmapEncoder 是用于编码 UltraHDR 和多图片格式(MPF)JPEG 图像的编码器类。它支持将基础图像和 Gainmap 图像组合成符合 HDR 标准的 JPEG 文件,以及创建包含多张图片的 MPF 格式文件。该类是 Skia 支持 HDR 图像编码的核心组件。

## 架构位置

SkJpegGainmapEncoder 位于 Skia 图像编码层的高级接口部分,专门处理 HDR 和多图片格式的 JPEG 编码。它建立在 SkJpegEncoder 基础之上,为 HDR 图像提供了更高层次的抽象。该类定义在 `include/private` 目录,主要供 Skia 内部和高级用户使用。

## 主要类与结构体

### SkJpegGainmapEncoder

这是一个纯静态方法类,提供 HDR JPEG 和 MPF 格式的编码功能。

**设计特点**:
- 所有方法都是静态的,无需创建实例
- 使用工具类(utility class)模式
- 依赖 SkJpegEncoder 进行实际的 JPEG 编码

## 公共 API 函数

### `static bool EncodeHDRGM(...)`

编码 UltraHDR 格式的 JPEG 图像,包含基础图像和 Gainmap。

**完整签名**:
```cpp
static bool EncodeHDRGM(
    SkWStream* dst,
    const SkPixmap& base,
    const SkJpegEncoder::Options& baseOptions,
    const SkPixmap& gainmap,
    const SkJpegEncoder::Options& gainmapOptions,
    const SkGainmapInfo& gainmapInfo
);
```

**参数说明**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| dst | SkWStream* | 输出流,编码结果写入此流 |
| base | const SkPixmap& | 基础图像的像素数据 |
| baseOptions | const SkJpegEncoder::Options& | 基础图像的编码选项(质量、采样等) |
| gainmap | const SkPixmap& | Gainmap 图像的像素数据 |
| gainmapOptions | const SkJpegEncoder::Options& | Gainmap 图像的编码选项 |
| gainmapInfo | const SkGainmapInfo& | Gainmap 渲染参数 |

**返回值**:
- true: 编码成功
- false: 编码失败(通常是参数无效或不支持)

**特殊说明**:
- 如果 baseOptions 或 gainmapOptions 指定了 XMP 元数据,该元数据会被覆盖
- 函数会自动生成符合 UltraHDR 标准的 XMP 元数据
- Gainmap 信息会被序列化为 ISO 21496-1 格式并嵌入 JPEG

### `static bool MakeMPF(...)`

创建多图片格式(MPF)JPEG 文件,包含多张独立的 JPEG 图像。

**完整签名**:
```cpp
static bool MakeMPF(
    SkWStream* dst,
    const SkData** images,
    size_t imageCount
);
```

**参数说明**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| dst | SkWStream* | 输出流,MPF 文件写入此流 |
| images | const SkData** | 指向 JPEG 图像数据的指针数组 |
| imageCount | size_t | 图像数量 |

**返回值**:
- true: 创建成功
- false: 创建失败

**说明**:
- 每个 images[i] 都应该是完整的 JPEG 编码数据
- 生成的 MPF 文件符合 CIPA DC-007 标准

## 内部实现细节

### UltraHDR 编码流程

EncodeHDRGM 函数的处理步骤:

1. **验证输入**: 检查基础图像和 Gainmap 的尺寸、格式是否有效
2. **编码基础图像**: 使用 baseOptions 将基础图像编码为 JPEG
3. **编码 Gainmap**: 使用 gainmapOptions 将 Gainmap 编码为 JPEG
4. **生成 XMP 元数据**: 根据 gainmapInfo 生成符合 Adobe Gainmap 规范的 XMP
5. **生成 ISO 21496-1 元数据**: 序列化 gainmapInfo 为二进制格式
6. **嵌入元数据**: 将 XMP 和 ISO 元数据嵌入基础 JPEG 的 APP 段
7. **构建 MPF 结构**: 使用 MakeMPF 将基础图像和 Gainmap 组合
8. **写入输出流**: 将最终的 JPEG 数据写入 dst

### MPF 格式结构

Multi-Picture Format 的数据结构:

```
[Primary JPEG]
  - SOI (0xFFD8)
  - APP2 (MPF 标记段)
    - MP Index IFD (包含所有图像的偏移和大小)
  - [JPEG 数据]
  - EOI (0xFFD9)
[Secondary JPEG 1]
  - JPEG 完整数据
[Secondary JPEG 2]
  - ...
```

MakeMPF 函数:
1. 写入第一张 JPEG(主图像)
2. 在主图像中插入 MPF APP2 段
3. 记录所有次要图像的偏移量
4. 依次追加次要图像的数据

### XMP 元数据生成

UltraHDR XMP 包含以下关键信息:
- **Gainmap 版本**: Adobe Gainmap 1.0
- **基础图像类型**: SDR 或 HDR
- **Gainmap 参数**:
  - GainmapMin/Max(RGB 三通道)
  - Gamma 值
  - Offset 值(epsilon)
  - HDR/SDR 显示比例

XMP 格式示例:
```xml
<rdf:Description
    xmlns:hdrgm="http://ns.adobe.com/hdr-gain-map/1.0/">
    <hdrgm:Version>1.0</hdrgm:Version>
    <hdrgm:GainMapMin>0.0</hdrgm:GainMapMin>
    <hdrgm:GainMapMax>1.0</hdrgm:GainMapMax>
    ...
</rdf:Description>
```

### ISO 21496-1 元数据

ISO 标准的 Gainmap 元数据是二进制格式:
- 包含版本号、参数类型、值数据
- 序列化为 TLV(Type-Length-Value)结构
- 嵌入 JPEG 的 APP11 段

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/encode/SkJpegEncoder.h` | 基础 JPEG 编码功能 |
| `include/core/SkPixmap.h` | 像素图数据表示 |
| `include/core/SkData.h` | 二进制数据容器 |
| `include/private/SkGainmapInfo.h` | Gainmap 参数定义 |

### 被依赖的模块

- **SkImage**: 图像编码接口可能使用此类保存 HDR 图像
- **高级编码工具**: 需要生成 HDR JPEG 的应用
- **测试代码**: UltraHDR 相关的单元测试和集成测试

## 设计模式与设计决策

### 静态工具类模式

使用静态方法而非实例方法的原因:
- **无状态操作**: 编码是一次性操作,不需要维护状态
- **简化 API**: 避免不必要的对象创建和销毁
- **命名空间式设计**: 将相关功能组织在一起

### 参数分离设计

将基础图像和 Gainmap 的编码选项分开:
- **灵活性**: 可以对两张图使用不同的质量设置
- **优化空间**: Gainmap 通常可以使用更低的质量,节省空间
- **独立控制**: 某些场景可能需要特殊的 Gainmap 编码参数

### 元数据覆盖策略

自动覆盖用户提供的 XMP 元数据:
- **一致性保证**: 确保 XMP 与实际的 Gainmap 参数一致
- **避免冲突**: 防止用户手动设置的元数据与自动生成的冲突
- **简化使用**: 用户不需要手动构造复杂的 XMP 结构

## 性能考量

### 编码效率

EncodeHDRGM 的性能特点:
- **双重编码**: 需要分别编码基础图像和 Gainmap,时间约为单张的 2 倍
- **元数据开销**: XMP 和 ISO 元数据生成通常很快(微秒级)
- **I/O 瓶颈**: 写入大文件时,I/O 可能成为瓶颈

### 内存使用

- **临时缓冲**: 需要为两张 JPEG 图像分配临时内存
- **流式写入**: 使用 SkWStream 可以实现流式输出,避免一次性分配大块内存
- **元数据大小**: XMP 通常在 1-5 KB,ISO 元数据约 100-500 字节

### 优化建议

1. **Gainmap 质量**: Gainmap 可以使用较低质量(60-70),几乎不影响视觉效果
2. **Gainmap 分辨率**: Gainmap 可以是基础图像的 1/2 或 1/4 分辨率
3. **并行编码**: 基础图像和 Gainmap 可以并行编码(需要多线程支持)

## 平台相关说明

### 兼容性

- **UltraHDR**: 主要由 Adobe 和 Google 推广,Android 12+ 原生支持
- **MPF**: CIPA 标准,大多数相机和图像查看器支持
- **向后兼容**: 不支持 UltraHDR 的查看器会显示基础图像(SDR)

### 应用场景

- **移动摄影**: 手机相机拍摄 HDR 照片
- **图像处理**: 保留 HDR 图像的编辑结果
- **全景图**: MPF 可用于存储多角度照片

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/encode/SkJpegEncoder.h` | 基础 JPEG 编码器 |
| `src/encode/SkJpegGainmapEncoder.cpp` | 实现文件 |
| `include/private/SkGainmapInfo.h` | Gainmap 参数定义 |
| `include/private/SkJpegMetadataDecoder.h` | 对应的解码器 |
| `src/codec/SkJpegXmp.cpp` | XMP 元数据处理 |
| `tests/JpegGainmapTest.cpp` | 单元测试 |
