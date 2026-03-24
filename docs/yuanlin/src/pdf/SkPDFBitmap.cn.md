# SkPDFBitmap - PDF 图像序列化

> 源文件：
> - `src/pdf/SkPDFBitmap.h`
> - `src/pdf/SkPDFBitmap.cpp`

## 概述

`SkPDFBitmap` 是 Skia PDF 后端中负责将 `SkImage` 序列化为 PDF Image XObject 的模块。它支持三种图像编码格式：JPEG 直通（DCT）、Flate 压缩和无压缩。模块能智能选择最佳编码路径：优先尝试复用图像原始的 JPEG 编码数据，其次尝试用 JPEG 编码器重新编码，最后使用 Deflate 压缩原始像素数据。对于包含透明度的图像，模块会将颜色通道和 Alpha 通道分离为独立的 Image XObject 和 SMask（软蒙版）。此外，模块还处理 ICC 颜色配置文件的嵌入和去重。

## 架构位置

该模块是 PDF 图像处理管线的核心，被 `SkPDFDevice` 在绘制图像时调用。

```
SkPDFDevice (drawImage/drawBitmap)
  └── SkPDFSerializeImage
        ├── serialize_image
        │     ├── do_jpeg (JPEG 直通/重编码)
        │     └── do_deflated_image (Deflate 压缩像素)
        │           └── do_deflated_alpha (Alpha 通道分离)
        └── emit_image_stream → PDF Image XObject
```

## 主要类与结构体

### `SkPDFIccProfileKey`

```cpp
struct SkPDFIccProfileKey {
    sk_sp<const SkData> fData;   // ICC 配置文件数据
    int fChannels;                // 通道数
};
```

用于 ICC 配置文件去重的缓存键。通过 `fData` 内容和通道数联合判断相等性。`Hash` 函子通过 `SkGoodHash` 和 `SkChecksum::Hash32` 组合计算哈希值。

### `SkPDFStreamFormat` 枚举（内部）

```cpp
enum class SkPDFStreamFormat { DCT, Flate, Uncompressed };
```

图像流的编码格式：DCT（JPEG）、Flate（zlib 压缩）或不压缩。

## 公共 API 函数

### `SkPDFSerializeImage`

```cpp
SkPDFIndirectReference SkPDFSerializeImage(const SkImage* img,
                                           SkPDFDocument* doc,
                                           int encodingQuality);
```

将 `SkImage` 序列化为 PDF Image XObject。`encodingQuality` > 100 表示无损编码。支持异步执行：如果文档配置了 `SkExecutor`，序列化任务将被提交到线程池异步处理。返回预留的间接引用。

### `SkPDFSerializeImageSize`

```cpp
size_t SkPDFSerializeImageSize(const SkImage* img, SkPDFDocument* doc, int encodingQuality);
```

计算图像序列化后的字节大小，但不实际写入 PDF。通过传入无效的 `SkPDFIndirectReference()` 来触发仅计算路径。

## 内部实现细节

### 编码路径选择

`serialize_image()` 按以下优先级选择编码路径：

1. **JPEG 直通**：如果图像携带原始编码数据（`refEncodedData`），尝试通过 `do_jpeg()` 直接使用。要求 JPEG 颜色类型为 YUV 或 Gray，且 EXIF 方向为 TopLeft。
2. **JPEG 重编码**：如果图像不透明且 `encodingQuality <= 100` 且配置了 JPEG 编码器回调，尝试将像素重新编码为 JPEG。
3. **Deflate 压缩**：作为最终回退，使用 `do_deflated_image()` 将原始像素数据进行 Flate 压缩。

### 透明像素颜色修正

`get_neighbor_avg_color()` 处理透明像素的颜色通道。PDF 渲染器可能独立重采样颜色和 Alpha 通道，导致本应透明的区域显示为灰色（因为透明像素的颜色通道可能是黑色）。该函数用相邻非透明像素的平均颜色替代透明像素的颜色分量。

### Alpha 通道分离

`do_deflated_alpha()` 从 BGRA 像素中提取 Alpha 通道，生成一个独立的 DeviceGray Image XObject 作为 SMask。对于 `kAlpha_8_SkColorType` 直接使用原始数据。

### 颜色空间处理

- **灰度图像**：使用 `DeviceGray` 颜色空间
- **彩色图像**：默认使用 `DeviceRGB`，如果有 ICC 配置文件则使用 `ICCBased` 颜色空间
- **ICC 去重**：通过 `doc->fICCProfileMap`（线程安全，使用 `SkMutex`）缓存已嵌入的 ICC 配置文件
- **通道数校验**：`icc_channel_mismatch()` 确保 ICC 配置文件的通道数与图像格式匹配

### 像素格式转换

`to_pixels()` 将 `SkImage` 转为位图，根据颜色类型选择目标格式：
- `kAlpha_8_SkColorType` → 保持 A8
- `kGray_8_SkColorType` → 保持 Gray8（不透明）
- 其他 → BGRA_8888（Unpremul）

### 异步执行

`SkPDFSerializeImage()` 支持通过 `SkExecutor` 线程池异步序列化。通过 `doc->incrementJobCount()` 和 `doc->signalJobComplete()` 管理异步任务的生命周期，确保文档关闭前所有任务完成。

### 流输出

`emit_image_stream()` 模板函数统一处理所有格式的 Image XObject 字典构建和流写入。字典包含 `/Type XObject`、`/Subtype Image`、`/Width`、`/Height`、`/ColorSpace`、`/BitsPerComponent`、`/Filter` 和可选的 `/SMask` 等键。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | PDF 基本类型 |
| `SkPDFDocumentPriv.h` | 文档私有接口（reserveRef、emit）|
| `SkPDFUnion.h` | PDF 联合类型（Name、Object）|
| `SkDeflate.h` | Flate/zlib 压缩 |
| `SkCodec.h` | JPEG 解码器（格式验证）|
| `SkEncodedInfo.h` | 编码信息（颜色类型、ICC）|
| `SkImage.h` | 图像基类 |
| `SkBitmap.h` / `SkPixmap.h` | 像素数据访问 |
| `SkICC.h` | ICC 配置文件写入 |
| `skcms.h` | 颜色管理系统 |
| `SkExecutor.h` | 线程池异步执行 |
| `SkMutex.h` | ICC 缓存线程安全 |
| `SkTHash.h` | 哈希映射（ICC 缓存）|

## 设计模式与设计决策

1. **编码路径优先级**：JPEG 直通 > JPEG 重编码 > Deflate 压缩。JPEG 直通零开销，JPEG 重编码在质量可控时压缩率最优，Deflate 作为通用回退保证正确性。

2. **Alpha 通道分离**：遵循 PDF 规范，使用独立的 SMask Image XObject 表示透明度。颜色通道的透明像素使用邻域平均色修正，解决独立重采样导致的灰边问题。

3. **ICC 配置文件去重**：通过文档级缓存避免相同 ICC 配置文件被多次嵌入。缓存使用互斥锁保证线程安全，因为图像序列化可能在异步线程中执行。

4. **异步序列化**：利用 `SkExecutor` 支持图像序列化的并行化。预留引用（`reserveRef`）使得异步写入不影响对象编号的确定性。

5. **大小预计算**：`SkPDFSerializeImageSize` 允许在不实际写入的情况下估算输出大小，用于文档大小预估或分页决策。

6. **颜色空间保真**：尽可能保留原始 ICC 配置文件（从编码数据、解码器或图像对象依次尝试），确保颜色在 PDF 中的准确再现。

## 性能考量

- **JPEG 直通零拷贝**：已编码的 JPEG 数据直接写入 PDF 流，避免解码-重编码的开销。
- **异步执行**：图像序列化可以在后台线程并行执行，充分利用多核 CPU。
- **缓冲写入**：Alpha 提取和颜色数据写入都使用固定大小缓冲区（4092/3072 字节），平衡内存使用和写入频率。
- **Deflate 压缩**：使用文档配置的压缩级别，允许用户在压缩率和速度之间权衡。
- **fill_stream 优化**：`fill_stream()` 使用 4096 字节缓冲区批量写入重复值，避免逐字节写入。
- **ICC 缓存**：相同 ICC 配置文件仅序列化一次，减少输出大小和处理时间。

## 相关文件

- `src/pdf/SkPDFDevice.h` / `src/pdf/SkPDFDevice.cpp` — 主要调用方，在 drawImage 时调用
- `src/pdf/SkPDFDocumentPriv.h` — 文档私有接口
- `src/pdf/SkPDFTypes.h` — PDF 基本类型
- `src/pdf/SkPDFUnion.h` — PDF 联合值类型
- `src/pdf/SkDeflate.h` — Flate 压缩实现
- `include/docs/SkPDFDocument.h` — 公共 API（Metadata 中的编码器回调）
- `include/encode/SkICC.h` — ICC 配置文件写入
