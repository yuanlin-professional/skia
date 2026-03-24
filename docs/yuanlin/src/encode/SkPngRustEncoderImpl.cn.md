# SkPngRustEncoderImpl — 基于 Rust png crate 的 PNG 编码器

> 源文件：[src/encode/SkPngRustEncoderImpl.h](../../src/encode/SkPngRustEncoderImpl.h)、[src/encode/SkPngRustEncoderImpl.cpp](../../src/encode/SkPngRustEncoderImpl.cpp)

## 概述

`SkPngRustEncoderImpl` 是 Skia 图像编码 API（`SkEncoder`）的 PNG 编码实现，底层使用 Rust 编写的 `png` crate 进行 PNG 压缩和编码。它继承自 `SkPngEncoderBase`，通过 C++/Rust FFI（CXX）桥接与 Rust 代码交互。

核心特性：
- 基于 Rust `png` crate 的 PNG 压缩（替代传统的 libpng）
- 支持多种压缩级别（Low/Medium/High）
- 处理 Rust png 不支持的像素格式转换（RGBA→RGB、LE→BE）
- 支持 ICC 颜色配置文件嵌入
- 支持 tEXt 文本块（注释）

## 架构位置

```
SkEncoder (基类)
    └── SkPngEncoderBase (PNG 共享逻辑：像素格式协商、行转换)
            └── SkPngRustEncoderImpl (Rust png crate 后端)
                    │
                    └── rust_png::StreamWriter (Rust FFI)
```

## 主要类与结构体

### `SkPngRustEncoderImpl`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStreamWriter` | `rust::Box<rust_png::StreamWriter>` | Rust PNG 流写入器 |
| `fExtraRowTransform` | `ExtraRowTransform` | 额外的行级像素转换类型 |
| `fExtraRowBuffer` | `std::vector<uint8_t>` | 额外转换的行缓冲区 |

### `ExtraRowTransform`（枚举）

| 值 | 说明 |
|----|------|
| `kNone` | 无额外转换 |
| `kRgba8ToRgb8` | 8位 RGBA→RGB（去 alpha 通道） |
| `kRgba16leToRgba16be` | 16位 RGBA 小端→大端 |
| `kRgba16leToRgb16be` | 16位 RGBA 小端→RGB 大端（去 alpha + 换端序） |

### `WriteTraitAdapterForSkWStream`

将 `SkWStream` 适配为 Rust FFI 要求的 `WriteTrait` 接口。

## 公共 API 函数

### `Make(SkWStream*, const SkPixmap&, const Options&) -> unique_ptr<SkEncoder>`

静态工厂方法：验证像素图有效性、确定目标信息和额外转换类型、创建 ICC 配置文件、初始化 Rust writer、编码注释文本块、转换为 StreamWriter。

### `onEncodeRow(SkSpan<const uint8_t> row) -> bool`

编码单行像素。需要额外转换时使用 `skcms_Transform` 进行格式转换，然后传给 Rust StreamWriter。

### `onFinishEncoding() -> bool`

调用 `rust_png::finish_encoding` 完成 PNG 编码（写入 IEND 块等）。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `rust_png` (FFI) | Rust png crate 的 C++ 绑定 |
| CXX (`third_party/rust/cxx`) | C++/Rust FFI 框架 |
| `SkPngEncoderBase` | PNG 编码基类（像素格式协商） |
| `skcms` | 像素格式转换 |

## 设计模式与设计决策

1. **C++/Rust 混合架构**：使用 CXX 桥接实现 C++ 和 Rust 之间的安全互操作。SkWStream 通过 `WriteTraitAdapterForSkWStream` 适配为 Rust trait 对象。

2. **额外行转换**：Rust png 不支持 libpng 的 `png_set_filler`（忽略 alpha 通道）和 `png_set_swap`（字节序转换），因此在 C++ 侧使用 skcms 进行这些转换。

3. **三级压缩**：Low（Level1 + Up 滤波）、Medium（Balanced 或 fdeflate Fast）、High（完整压缩）。

## 性能考量

- Rust png crate 的压缩性能通常与 libpng 相当或更优。
- 额外行转换引入少量开销，但通过 skcms 的 SIMD 优化降低了影响。
- 32KB 写入缓冲区继承自 SkPngEncoderBase，减少系统调用。

## 相关文件

- `src/encode/SkPngEncoderBase.h` / `.cpp` — PNG 编码基类
- `include/encode/SkPngRustEncoder.h` — 公共 API
- `rust/png/FFI.rs.h` — Rust FFI 定义
