# SkPngEncoderImpl — 基于 libpng 的 PNG 编码器

> 源文件：[src/encode/SkPngEncoderImpl.h](../../src/encode/SkPngEncoderImpl.h)、[src/encode/SkPngEncoderImpl.cpp](../../src/encode/SkPngEncoderImpl.cpp)

## 概述

`SkPngEncoderImpl` 是 Skia 基于 libpng 的 PNG 图像编码器实现，继承自 `SkPngEncoderBase`。它是传统 libpng 后端的实现，与 Rust png crate 后端（`SkPngRustEncoderImpl`）共享基类中的像素格式协商和行转换逻辑。

## 架构位置

```
SkEncoder (基类)
    └── SkPngEncoderBase (PNG 共享逻辑)
            ├── SkPngEncoderImpl (libpng 后端) ← 本模块
            └── SkPngRustEncoderImpl (Rust 后端)
```

## 主要类与结构体

### `SkPngEncoderImpl`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fEncoderMgr` | `unique_ptr<SkPngEncoderMgr>` | libpng 管理器（png_struct 和 png_info 封装） |

## 公共 API 函数

- **构造函数**：接收 `TargetInfo`、`SkPngEncoderMgr` 和源 `SkPixmap`。
- **`onEncodeRow(SkSpan<const uint8_t> row) -> bool`**：将单行像素数据传递给 libpng 进行压缩。
- **`onFinishEncoding() -> bool`**：完成 PNG 编码（写入 IEND 块）。

## 内部实现细节

libpng 提供了 `png_set_filler`（忽略 alpha 通道）和 `png_set_swap`（字节序转换）等功能，因此 `SkPngEncoderImpl` 不需要像 Rust 版本那样进行额外的行级转换。像素格式协商和行级格式转换（如 premul→unpremul、float→16bit）由基类 `SkPngEncoderBase` 处理。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| libpng | PNG 压缩引擎 |
| `SkPngEncoderBase` | PNG 编码基类 |
| `SkPngEncoderMgr` | libpng 封装管理器 |

## 设计模式与设计决策

1. **模板方法模式**：`SkPngEncoderBase::onEncodeRows()` 实现行遍历和格式转换，子类只需实现 `onEncodeRow()` 和 `onFinishEncoding()` 两个方法。
2. **后端可替换**：通过共享基类，libpng 后端和 Rust 后端可以在构建时选择。

## 性能考量

- libpng 是成熟的 C 库，有良好的压缩率和速度。
- libpng 的内置转换（filler/swap）避免了额外的内存拷贝。

## 相关文件

- `src/encode/SkPngEncoderBase.h` / `.cpp` — PNG 编码基类
- `include/encode/SkPngEncoder.h` — 公共 API
