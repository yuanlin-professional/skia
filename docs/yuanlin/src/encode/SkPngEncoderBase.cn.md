# SkPngEncoderBase — PNG 编码器基类

> 源文件：[src/encode/SkPngEncoderBase.h](../../src/encode/SkPngEncoderBase.h)、[src/encode/SkPngEncoderBase.cpp](../../src/encode/SkPngEncoderBase.cpp)

## 概述

`SkPngEncoderBase` 是 PNG 编码器的抽象基类，实现了 `SkPngEncoderImpl`（libpng 后端）和 `SkPngRustEncoderImpl`（Rust 后端）之间的共享功能。主要职责包括：

- 根据源 `SkImageInfo` 协商 PNG 目标格式
- 源像素到 PNG 兼容格式的逐行转换
- 编码行循环和完成检测
- 特殊处理 `kAlpha_8` 色彩类型（编码为 GrayAlpha）

## 架构位置

```
SkEncoder (抽象基类)
    └── SkPngEncoderBase (PNG 通用逻辑) ← 本模块
            ├── SkPngEncoderImpl (libpng)
            └── SkPngRustEncoderImpl (Rust)
```

## 主要类与结构体

### `SkPngEncoderBase::TargetInfo`

| 字段 | 类型 | 说明 |
|------|------|------|
| `fSrcRowInfo` | `optional<SkImageInfo>` | 源行的图像信息（宽度=1行） |
| `fDstRowInfo` | `optional<SkImageInfo>` | 目标行的图像信息 |
| `fDstInfo` | `SkEncodedInfo` | PNG 编码目标信息 |
| `fDstRowSize` | `size_t` | 目标行字节数 |

## 公共 API 函数

### `getTargetInfo(const SkImageInfo& srcInfo) -> optional<TargetInfo>`

静态方法。根据源色彩类型确定 PNG 编码参数：
- 1 通道灰度 → Gray8
- `kAlpha_8` → GrayAlpha8（特殊路径）
- 3 通道 ≤8bit → RGBA8 via RGB_888x
- 3 通道 >8bit → RGBA16 via R16G16B16A16_unorm
- 4 通道：类似，根据 alpha 类型选择是否保留 alpha

### `onEncodeRows(int numRows) -> bool`

模板方法：遍历指定行数，对每行执行格式转换（通过 `SkConvertPixels`），然后调用子类的 `onEncodeRow()`。所有行编码完成后调用 `onFinishEncoding()`。

## 内部实现细节

### kAlpha_8 特殊路径

`kAlpha_8` 源通过 `transform_scanline_A8_to_GrayAlpha` 转换为 GrayAlpha 格式（每像素 2 字节：灰度+alpha），不经过 `SkConvertPixels`。

### 格式协商逻辑

优先选择与源位深匹配的最小 PNG 格式。不透明图像的 alpha 通道会被编码为 RGB（通过中间格式 `kRGB_888x` 或 `kR16G16B16A16_unorm`），子类实现负责最终去除 alpha。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkEncoder` | 编码器基类 |
| `SkConvertPixels` | 像素格式转换 |
| `SkEncodedInfo` | 编码目标信息 |
| `SkImageEncoderFns` | alpha 转换函数 |
| `SkSafeMath` | 安全数学运算 |

## 设计模式与设计决策

1. **模板方法模式**：`onEncodeRows()` 是 final 方法，定义了行编码的算法骨架。子类通过 `onEncodeRow()` 和 `onFinishEncoding()` 提供具体实现。

2. **格式协商与转换分离**：`getTargetInfo()` 在编码器创建时确定转换策略，`onEncodeRows()` 在运行时执行转换。

3. **可选的行信息**：`fSrcRowInfo` 和 `fDstRowInfo` 为 `optional`，对于 `kAlpha_8` 等特殊路径可以为空。

## 性能考量

- 行级转换使用 `SkConvertPixels`，支持 SIMD 优化。
- 每次仅转换一行，内存使用恒定（一行缓冲区）。
- 完成检测避免多余的 `onFinishEncoding()` 调用。

## 相关文件

- `src/encode/SkPngEncoderImpl.h` — libpng 后端
- `src/encode/SkPngRustEncoderImpl.h` — Rust png 后端
- `include/encode/SkEncoder.h` — 编码器基类
- `src/core/SkConvertPixels.h` — 像素格式转换
