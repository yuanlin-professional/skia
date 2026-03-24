# HashAndEncode - 图像哈希与标准化编码

> 源文件:
> - [tools/HashAndEncode.h](../../tools/HashAndEncode.h)
> - [tools/HashAndEncode.cpp](../../tools/HashAndEncode.cpp)

## 概述

HashAndEncode 将任意 SkBitmap 转换为标准格式（16 位未预乘 RGBA，Rec. 2020 色彩空间），用于跨后端、跨配置的图像内容比较。它提供两个核心功能：`feedHash()` 用于基于内容的 MD5 哈希计算，`encodePNG()` 用于生成可视化比较的 PNG 文件。该组件是 DM（Skia 测试运行器）结果上传到 Gold 系统的关键环节。

## 架构位置

位于 `tools/` 目录下，是 DM 测试基础设施的核心组件。它连接了渲染结果与 Gold 图像比较系统，确保不同后端和配置生成的图像能够被一致地哈希和比较。

## 主要类与结构体

### `HashAndEncode`
核心类，持有标准化后的像素数据。
- `fSize` - 图像尺寸
- `fPixels` - 转换后的 16 位大端 RGBA 像素数组（`uint64_t[]`）

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `HashAndEncode(const SkBitmap&)` | 构造函数，将位图转换为标准格式 |
| `feedHash(SkWStream*)` | 将像素数据写入流以供哈希计算 |
| `encodePNG(SkWStream*, md5, key, properties)` | 编码为 PNG 并嵌入元数据 |

## 内部实现细节

- **色彩空间转换**：使用 `skcms` 库将各种源格式转换为目标格式（`skcms_PixelFormat_RGBA_16161616BE`、`skcms_AlphaFormat_Unpremul`、Rec. 2020 色彩空间）。
- **源格式映射**：支持大量 SkColorType 到 skcms 格式的映射，部分格式（如 R8G8_unorm、R16_unorm 等）不支持会提前返回。
- **R8 色彩类型特殊处理**：由于 skcms 没有 R_8 格式，假装为 G_8 但修改源色彩空间矩阵将 green/blue 通道清零。
- **分块转换**：大图像分块处理，每块不超过 `1<<27` 像素以满足 skcms 要求。
- **直接使用 libpng**：`encodePNG` 绕过 SkPngEncoder，直接调用 libpng API，确保产出稳定、可移植的结果。
- **哈希盐值**：feedHash 中包含 `salt` 值，修改盐值会使所有图像哈希失效。
- **PNG 元数据**：嵌入 Author、Description、iCCP 配置文件信息。

## 依赖关系

- **Skia 核心**：SkBitmap、SkColorSpace、SkColorType、SkString、SkStream
- **色彩管理**：skcms 库、SkICC（ICC 配置文件写入）
- **外部库**：libpng（直接调用）
- **工具**：CommandLineFlags（命令行参数）

## 设计模式与设计决策

- **不可变值对象**：构造时完成所有转换，之后只读。
- **绕过 Skia 编码器**：直接使用 libpng 而非 SkPngEncoder，确保编码结果不受 Skia 编码器变更影响。
- **统一标准格式**：选择 16 位 Rec. 2020 作为统一格式，能够无损表示 Skia 支持的所有颜色类型。

## 性能考量

- PNG 编码使用 `PNG_FILTER_NONE` 和压缩级别 1，在文件大小和编解码速度间取平衡。
- 大图像的 skcms 转换分块执行，避免单次操作溢出。
- 构造时即完成完整转换，适合单次哈希 + 编码的使用场景。

## 相关文件

- `dm/DMJsonWriter.h` - DM 结果 JSON 写入
- `tools/flags/CommandLineFlags.h` - 命令行参数定义
- `modules/skcms/skcms.h` - 色彩管理库
- `include/encode/SkICC.h` - ICC 配置文件
