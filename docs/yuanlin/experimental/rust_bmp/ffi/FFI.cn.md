# FFI.rs - Rust BMP 解码器 C++/Rust FFI 桥接层

> 源文件:
> - `experimental/rust_bmp/ffi/FFI.rs`

## 概述

FFI.rs 是 Skia 实验性 Rust BMP 解码器的 C++/Rust 互操作桥接层，使用 `cxx` crate 定义了 C++ 与 Rust 之间的类型安全 FFI 接口。该模块实现了一个基于 `image-rs` crate 的 BMP 图像解码器，支持流式/可恢复的解码模式，允许在数据不完整时暂停并在后续恢复解码。这是 Skia 探索将 Rust 图像解码能力集成到 C++ 代码库中的实验性项目。

## 架构位置

```
Skia C++ 编解码器层
    ↓ (通过 cxx FFI 调用)
rust_bmp::ffi (FFI 桥接定义)  <── 本模块
    ↓
Reader (Rust BMP 解码器)
    ↓
image::codecs::bmp::BmpDecoder (image-rs crate)
    ↓
SkStreamAdapter (C++ 流适配器, 通过 FFI 回传)
```

该模块桥接了 C++ 端的 Skia 流系统和 Rust 端的 image-rs 解码器，形成双向 FFI 调用链。

## 主要类与结构体

### FFI 层枚举

| 枚举 | 描述 |
|------|------|
| `DecodingResult` | 解码结果状态：Success, FormatError, ParameterError, UnsupportedFeature, IncompleteInput, MemoryError, OtherError |
| `BmpColor` | BMP 颜色类型（匹配 `SkEncodedInfo::Color`）：RGB=5, RGBA=6, BGR=7, BGRA=9 |
| `BmpAlpha` | BMP Alpha 类型（匹配 `SkEncodedInfo::Alpha`）：Opaque=0, Unpremul=1 |

### FFI 层结构体

| 结构体 | 描述 |
|--------|------|
| `DecodedRowsInfo` | 解码行信息：`dst_row_start`（目标起始行）、`row_count`（有效行数）|

### Rust 端类型

| 类型 | 描述 |
|------|------|
| `Reader` | BMP 解码器主体，封装 `BmpDecoder` 和解码状态 |
| `ResultOfReader` | Reader 创建结果的包装，用于跨 FFI 传递 `Result` |
| `BmpError` | 内部错误类型，映射 `image::ImageError` 和 `std::io::Error` |

### Reader 结构体字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `decoder` | `Option<BmpDecoder<BufReader<UniquePtr<SkStreamAdapter>>>>` | 底层 BMP 解码器 |
| `metadata_loaded` | `bool` | 元数据是否已加载 |
| `width`, `height` | `u32` | 图像尺寸 |
| `color`, `alpha` | `BmpColor`, `BmpAlpha` | 颜色和 Alpha 类型 |
| `bytes_per_pixel` | `u32` | 每像素字节数 |
| `image_data` | `Vec<u8>` | 解码后的像素数据缓冲区 |
| `image_data_loaded` | `bool` | 像素数据是否完全加载 |
| `last_consumed_row_count` | `u32` | 上次消费的行数（用于增量获取）|

## 公共 API 函数

### FFI 导出到 C++ 的函数

| 函数 | 描述 |
|------|------|
| `is_bmp_data(data)` | 检查数据是否以 "BM" 签名开头 |
| `new_reader(input)` | 创建新的 BMP 读取器 |
| `Reader::width()` / `height()` | 获取图像尺寸 |
| `Reader::color()` / `alpha()` | 获取颜色/Alpha 类型 |
| `Reader::metadata_loaded()` | 检查元数据是否已加载 |
| `Reader::read_metadata()` | 读取并解析 BMP 头部元数据 |
| `Reader::read_image_data()` | 读取所有像素数据 |
| `Reader::image_data_loaded()` | 检查像素数据是否完全加载 |
| `Reader::get_next_rows(buffer)` | 获取自上次调用以来的新行 |
| `Reader::row_bytes()` | 获取每行字节数 |
| `Reader::reset_decode_state()` | 重置解码状态以重新解码 |
| `Reader::icc_profile()` | 获取 ICC 颜色配置文件 |

## 内部实现细节

### 流式解码模型

解码分为两个阶段，每个阶段都支持暂停和恢复：

1. **`read_metadata()`**: 读取 BMP 文件头，解析图像尺寸和颜色格式。支持 `Rgb8` 和 `Rgba8` 两种颜色类型
2. **`read_image_data()`**: 读取全部像素数据到内部缓冲区。数据不足时返回 `IncompleteInput`，保留已解码的部分数据

### 增量行获取（get_next_rows）

```rust
pub fn get_next_rows<'a>(&'a mut self, buffer: &mut &'a [u8]) -> DecodedRowsInfo
```

该方法跟踪 `last_consumed_row_count`，仅返回自上次调用以来新解码的行。支持两种 BMP 行顺序：
- **自顶向下 (top-down)**: 新行追加在已消费行之后
- **自底向上 (bottom-up)**: 新行位于缓冲区末尾，目标起始行从底部计算

### 错误映射

`BmpError` 将 `image-rs` 的错误类型映射为 Skia 兼容的 `DecodingResult`：
- `image::ImageError::Decoding` -> `FormatError`
- `image::ImageError::Limits` / `Unsupported` -> `UnsupportedFeature`
- `io::ErrorKind::UnexpectedEof` -> `IncompleteInput`（关键：区分数据不足和真正的 IO 错误）
- `image::ImageError::Parameter` -> `panic!`（表示 Skia 调用 image-rs 的方式有内部 bug）

### BufReader 优化

```rust
const BUFFER_SIZE: usize = 64 * 1024;
let buffered = BufReader::with_capacity(BUFFER_SIZE, input);
```

使用 64KB 的 BufReader 代替默认的 8KB，减少通过 FFI 回调读取 `SkStreamAdapter` 的系统调用次数。

### ResultOfReader 包装

由于 `cxx` 不直接支持 Rust `Result` 类型跨 FFI 传递，使用 `ResultOfReader` 结构体包装：
- `err()`: 查询错误状态
- `unwrap()`: 通过 `std::mem::replace` 提取内部 Reader（消耗性操作）

## 依赖关系

- **Rust 依赖**:
  - `cxx` crate - C++/Rust FFI 桥接
  - `image` crate - BMP 图像解码（`image::codecs::bmp::BmpDecoder`）
- **C++ 依赖**:
  - `SkStreamAdapter` - Skia C++ 流到 Rust `Read` trait 的适配器
  - `skia_rust_common` - Rust 通用绑定
- **编译时验证**: C++ 端的静态断言验证 `BmpColor` 和 `BmpAlpha` 的值与 `SkEncodedInfo` 匹配

## 设计模式与设计决策

- **cxx 桥接**: 使用 `#[cxx::bridge]` 宏生成类型安全的 FFI 代码，避免手动 `extern "C"` 的不安全性
- **可恢复解码**: 使用 `new_resumable()` 创建解码器，支持数据不完整时暂停并保留状态
- **增量消费**: `get_next_rows` 的设计允许 C++ 端按需获取新解码的行，适用于渐进式渲染
- **所有权模型**: `SkStreamAdapter` 通过 `cxx::UniquePtr` 跨 FFI 传递所有权
- **零初始化缓冲区**: 像素缓冲区使用 `vec![0u8; total_bytes]`，确保部分解码时未写入区域为有效零值
- **编译时枚举值验证**: `BmpColor` 和 `BmpAlpha` 使用 `#[repr(i32)]` 并通过 C++ 静态断言确保与 Skia 枚举值一致

## 性能考量

- 64KB BufReader 减少了跨 FFI 边界的调用次数，显著降低流式读取的开销
- `image_data` 缓冲区仅在第一次 `read_image_data()` 调用时分配，后续重试复用
- `reset_decode_state()` 通过清空 Vec 回收内存，而非保持分配
- `get_next_rows` 返回对内部缓冲区的切片引用（`&'a [u8]`），避免数据复制
- 自底向上 BMP 的行重排在 `get_next_rows` 中通过偏移量计算实现，无需额外的内存拷贝

## 相关文件

- `rust/common/SkStreamAdapter.h` - C++ 流适配器头文件
- `experimental/rust_bmp/` - Rust BMP 解码器项目根目录
- `include/codec/SkEncodedImageFormat.h` - Skia 编码格式定义
- `src/codec/SkBmpCodec.h` - Skia 原生 C++ BMP 解码器（对比参考）
