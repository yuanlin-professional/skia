# SkJpegEncoder

> 源文件: `include/encode/SkJpegEncoder.h`

## 概述

`SkJpegEncoder` 是 Skia 图形库中用于将像素数据编码为 JPEG 格式图像的命名空间。它提供了一套完整的 JPEG 编码 API，支持从 `SkPixmap`（光栅像素数据）、`SkYUVAPixmaps`（YUV 格式像素数据）以及 `SkImage`（包括 GPU 纹理支持的图像）进行编码。

JPEG 是一种广泛使用的有损图像压缩格式，特别适合于照片和自然场景图像的存储。`SkJpegEncoder` 封装了底层 libjpeg-turbo 编码库的功能，为 Skia 用户提供了简洁易用的高层 API。

### 核心功能

- 支持可配置的图像质量（0-100）
- 支持色度下采样策略选择（4:2:0、4:2:2、4:4:4）
- 支持 Alpha 通道处理策略（忽略或混合到黑色背景上）
- 支持 XMP 元数据嵌入
- 支持 EXIF 方向信息（`SkEncodedOrigin`）
- 支持从 YUV 格式像素直接编码（避免不必要的颜色空间转换）
- 支持增量编码（逐行编码）
- 支持 GPU 纹理图像的读回与编码

## 架构位置

`SkJpegEncoder` 位于 Skia 编码器子系统中，是三大核心图像编码器之一（JPEG、PNG、WebP）。

```
Skia 编码子系统架构
====================

  应用层 (Application)
        |
        v
  SkJpegEncoder / SkPngEncoder / SkWebpEncoder   <-- 公共 API 命名空间
        |
        v
  SkEncoder (基类)                                 <-- 增量编码接口
        |
        v
  SkJpegEncoderImpl (内部实现)                     <-- 具体编码逻辑
        |
        v
  libjpeg-turbo                                    <-- 第三方底层库
```

在 Skia 的分层架构中，`SkJpegEncoder` 属于 `include/encode/` 层的公共头文件，提供对外稳定的 API 接口。其具体实现在 `src/encode/SkJpegEncoderImpl.cpp` 中，依赖 libjpeg-turbo 第三方库完成实际的 JPEG 压缩操作。

## 主要类与结构体

### `SkJpegEncoder::AlphaOption` 枚举

控制编码器如何处理包含 Alpha 通道的输入图像。由于 JPEG 格式不支持透明度，必须对 Alpha 通道做出处理决策。

| 枚举值 | 说明 |
|--------|------|
| `kIgnore` | 忽略 Alpha 通道，将图像视为完全不透明（默认） |
| `kBlendOnBlack` | 将像素与黑色背景混合后再编码，支持线性和传统混合模式 |

### `SkJpegEncoder::Downsample` 枚举

控制 U、V 色度分量的下采样策略。JPEG 编码中的色度下采样是一种利用人类视觉系统对亮度比对颜色更敏感的特性来减小文件体积的技术。

| 枚举值 | 说明 | 水平缩减 | 垂直缩减 | 适用场景 |
|--------|------|----------|----------|----------|
| `k420` | 4:2:0 下采样（默认） | 2x | 2x | 照片、一般图像，文件最小 |
| `k422` | 4:2:2 下采样 | 2x | 无 | 需要更好水平色彩分辨率 |
| `k444` | 无下采样 | 无 | 无 | 最高质量，文件最大 |

> 注意：当输入源为 `SkYUVAPixmaps` 时，将使用源数据自身的子采样设置，忽略此选项。当源图像为灰度（kGray）时，此选项无意义，因为灰度图不会以 YUV 格式编码。

### `SkJpegEncoder::Options` 结构体

```cpp
struct Options {
    int fQuality = 100;                              // 编码质量 [0, 100]
    Downsample fDownsample = Downsample::k420;       // 色度下采样策略
    AlphaOption fAlphaOption = AlphaOption::kIgnore;  // Alpha 通道处理方式
    const SkData* xmpMetadata = nullptr;              // 可选 XMP 元数据
    std::optional<SkEncodedOrigin> fOrigin;           // 可选 EXIF 方向信息
};
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fQuality` | `int` | `100` | 编码质量，范围 [0, 100]，0 为最低质量 |
| `fDownsample` | `Downsample` | `k420` | 色度下采样方式，默认与 libjpeg-turbo 一致 |
| `fAlphaOption` | `AlphaOption` | `kIgnore` | Alpha 通道处理策略 |
| `xmpMetadata` | `const SkData*` | `nullptr` | 可选的 XMP 元数据指针 |
| `fOrigin` | `std::optional<SkEncodedOrigin>` | 空 | 可选的图像方向信息 |

## 公共 API 函数

### 一次性编码到流

```cpp
SK_API bool Encode(SkWStream* dst, const SkPixmap& src, const Options& options);
```

将 `SkPixmap` 像素数据编码为 JPEG 并写入输出流。这是最常用的编码方式。

- **参数**: `dst` - 目标输出流；`src` - 源像素数据；`options` - 编码选项
- **返回值**: 成功返回 `true`，输入无效或不支持时返回 `false`

```cpp
SK_API bool Encode(SkWStream* dst,
                   const SkYUVAPixmaps& src,
                   const SkColorSpace* srcColorSpace,
                   const Options& options);
```

从 YUV 格式像素数据直接编码为 JPEG。此重载可以避免 RGB 到 YUV 的颜色空间转换开销。

- **参数**: `dst` - 目标输出流；`src` - YUVA 像素数据；`srcColorSpace` - 源色彩空间；`options` - 编码选项
- **返回值**: 成功返回 `true`，输入无效或不支持时返回 `false`

### 一次性编码到内存

```cpp
SK_API sk_sp<SkData> Encode(const SkPixmap& src, const Options& options);
```

将像素数据编码为 JPEG 并返回编码后的字节数据。

- **返回值**: 成功返回包含 JPEG 数据的 `sk_sp<SkData>`，失败返回 `nullptr`

### GPU 图像编码

```cpp
SK_API sk_sp<SkData> Encode(GrDirectContext* ctx, const SkImage* img, const Options& options);
```

编码一个 `SkImage` 对象（支持 GPU 纹理支持的图像）。对于在 GPU 上下文中创建的纹理图像，必须提供对应的 `GrDirectContext` 以便读回像素；对于光栅图像，`ctx` 可以传 `nullptr`。

- **返回值**: 成功返回 `sk_sp<SkData>`，像素无法读取或编码失败返回 `nullptr`

### 增量编码器工厂

```cpp
SK_API std::unique_ptr<SkEncoder> Make(SkWStream* dst, const SkPixmap& src, const Options& options);
SK_API std::unique_ptr<SkEncoder> Make(SkWStream* dst,
                                       const SkYUVAPixmaps& src,
                                       const SkColorSpace* srcColorSpace,
                                       const Options& options);
```

创建一个增量 JPEG 编码器实例，允许调用者通过 `SkEncoder::encodeRows()` 逐步编码图像行。

- **注意**: `dst` 流的所有权不会被转移，但在编码器生存期间必须保持有效
- **返回值**: 成功返回编码器实例，输入无效或不支持时返回 `nullptr`

## 内部实现细节

### 编码流程

1. **像素验证**: 验证输入的 `SkPixmap` 是否具有有效的颜色类型和 Alpha 类型
2. **颜色空间转换**: 如果需要，将源颜色空间转换为 sRGB 或其他目标空间
3. **Alpha 处理**: 根据 `AlphaOption` 设置进行 Alpha 预乘或混合
4. **色度下采样**: 应用选定的下采样策略（对 YUV 输入可跳过此步骤）
5. **JPEG 压缩**: 调用 libjpeg-turbo 执行实际的 DCT 变换和熵编码
6. **元数据写入**: 写入 XMP 元数据和 EXIF 方向信息（如果提供）

### 禁用构建支持

当 JPEG 编码功能未在构建中启用时，`SkJpegEncoder_none.cpp` 提供了所有 API 的空实现（桩函数），确保链接不会失败但所有编码操作将返回失败。

### YUV 直通路径

通过 `SkYUVAPixmaps` 重载，编码器可以直接接受 YUV 格式的像素数据，跳过昂贵的 RGB-to-YUV 转换步骤。这在处理已经是 YUV 格式的视频帧或相机输出时非常有用。

## 依赖关系

### 头文件依赖

| 依赖 | 说明 |
|------|------|
| `include/codec/SkEncodedOrigin.h` | EXIF 方向枚举定义 |
| `include/core/SkRefCnt.h` | 引用计数智能指针 `sk_sp` |
| `include/private/base/SkAPI.h` | `SK_API` 导出宏定义 |

### 前向声明依赖

| 类型 | 说明 |
|------|------|
| `SkColorSpace` | 色彩空间描述 |
| `SkData` | 不可变二进制数据容器 |
| `SkEncoder` | 增量编码器基类 |
| `SkPixmap` | 光栅像素数据视图 |
| `SkWStream` | 可写流抽象接口 |
| `SkImage` | 图像对象（可能是 GPU 支持的） |
| `GrDirectContext` | GPU 上下文（Ganesh 后端） |
| `SkYUVAPixmaps` | YUVA 格式像素数据集合 |
| `skcms_ICCProfile` | ICC 色彩配置文件 |

### 第三方库依赖

- **libjpeg-turbo**: 底层 JPEG 编码实现，使用 SIMD 优化

## 设计模式与设计决策

### 命名空间 API 模式

`SkJpegEncoder` 使用命名空间而非类来组织 API。这是 Skia 编码器的统一设计风格，与传统面向对象的设计不同：

- **自由函数 `Encode()`**: 提供简洁的一步编码功能，适合大多数使用场景
- **工厂函数 `Make()`**: 返回 `SkEncoder` 基类指针，用于增量编码的高级场景

这种设计使调用者无需了解具体的编码器实现类（`SkJpegEncoderImpl`），实现了接口与实现的清晰分离。

### 编译时功能开关

通过提供 `_none.cpp` 桩实现文件，Skia 允许在构建配置中灵活地启用或禁用 JPEG 编码支持，而无需在 API 层面做条件编译。这保持了头文件的简洁性和 API 的稳定性。

### 多输入源支持

API 为不同的输入源（`SkPixmap`、`SkYUVAPixmaps`、`SkImage`）提供了专门的重载，而非使用单一的通用接口，这减少了不必要的类型转换和抽象层次，也使得每种路径的错误处理和优化更加清晰。

### 合理的默认值

`Options` 结构体的所有字段都有合理的默认值（质量 100、4:2:0 下采样、忽略 Alpha），使得最简单的用法只需传入默认构造的 `Options{}`。

## 性能考量

### 质量与文件大小的权衡

- `fQuality = 100` 提供最高质量但文件较大
- 通常 `fQuality` 在 75-85 范围内可以在视觉质量和文件大小之间取得良好平衡
- `fQuality` 低于 50 时，压缩伪影将变得明显

### 色度下采样的影响

| 策略 | 相对文件大小 | 编码速度 | 图像质量 |
|------|-------------|----------|----------|
| k420 | 最小 (~60%) | 最快 | 一般（对色彩边缘有影响） |
| k422 | 中等 (~75%) | 中等 | 较好 |
| k444 | 最大 (100%) | 最慢 | 最佳 |

### YUV 直通优势

当输入数据已经是 YUV 格式时，使用 `SkYUVAPixmaps` 重载可以避免 RGB-to-YUV 颜色空间转换，显著减少编码延迟和 CPU 使用率。

### GPU 图像读回

从 GPU 纹理编码 JPEG 时，需要先将像素从 GPU 内存读回 CPU 内存。这是一个同步操作，可能会导致 GPU 管线停顿。建议在不影响渲染帧率的时机执行此操作。

### 增量编码

使用 `Make()` 创建增量编码器可以分批处理图像行，这在处理非常大的图像时可以控制峰值内存使用量，避免一次性分配整个图像的编码缓冲区。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/encode/SkJpegEncoder.h` | 公共 API 头文件（本文件） |
| `include/encode/SkEncoder.h` | 编码器基类定义 |
| `src/encode/SkJpegEncoderImpl.h` | JPEG 编码器内部实现头文件 |
| `src/encode/SkJpegEncoderImpl.cpp` | JPEG 编码器内部实现 |
| `src/encode/SkJpegEncoder_none.cpp` | JPEG 编码功能禁用时的桩实现 |
| `src/encode/SkJpegGainmapEncoder.cpp` | JPEG 增益图编码实现 |
| `include/encode/SkPngEncoder.h` | PNG 编码器公共 API |
| `include/encode/SkWebpEncoder.h` | WebP 编码器公共 API |
| `include/core/SkPixmap.h` | 像素数据视图 |
| `include/codec/SkEncodedOrigin.h` | EXIF 方向枚举 |
