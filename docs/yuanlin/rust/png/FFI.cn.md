# FFI.rs / FFI.h - Rust PNG 编解码器的 C++/Rust FFI 桥接层

> 源文件: `rust/png/FFI.rs`, `rust/png/FFI.h`

## 概述

本文件组（FFI.rs 和 FFI.h）实现了 Skia 中 Rust `png` crate 与 C++ 代码之间的跨语言互操作层（FFI - Foreign Function Interface）。FFI.rs 是核心实现文件，通过 `cxx` 库定义了 Rust PNG 解码器和编码器的 C++ 绑定接口；FFI.h 是配套的 C++ 头文件，定义了 `WriteTrait` 抽象类，为 Rust 端提供对 C++ I/O 流的写入能力。这套桥接层使得 Skia 能够利用 Rust 生态中高质量的 `png` crate 来替代传统的 `libpng` C 库进行 PNG 图像的编解码。

## 架构位置

该模块位于 Skia 的 `rust/png/` 目录下，是 Skia 的 Rust 集成层的核心组件之一。在整体架构中：

- **上层调用者**: C++ 端的 `SkPngRustCodec`（解码）和 `SkPngRustEncoderImpl`（编码）
- **本层**: FFI 桥接层，将 Rust API 包装为 C++ 可调用的接口
- **下层依赖**: Rust `png` crate（实际的 PNG 编解码实现）
- **同层**: `rust/common/SkStreamAdapter` 提供 Skia 流到 Rust `Read` trait 的适配

## 主要类与结构体

### FFI 枚举类型（Rust 侧，跨 FFI 边界）

- **`ColorType`**: PNG 颜色类型的 FFI 友好等价物（Grayscale、Rgb、Indexed、GrayscaleAlpha、Rgba）
- **`DecodingResult`**: 解码结果的简化表示（Success、FormatError、ParameterError、LimitsExceededError、IncompleteInput、OtherIoError、EndOfFrame）
- **`DisposeOp`**: APNG 帧处置操作（None、Background、Previous）
- **`BlendOp`**: APNG 帧混合操作（Source、Over）
- **`Compression`**: 编码压缩级别（Level1WithUpFilter、Fastest、Fast、Balanced、High）
- **`EncodingResult`**: 编码结果（Success、IoError、FormatError、ParameterError、LimitsExceededError）

### FFI 结构体

- **`ColorSpacePrimaries`**: 色彩空间原色坐标，对应 C++ 的 `SkColorSpacePrimaries`
- **`MasteringDisplayColorVolume`**: HDR 主显示色量元数据
- **`ContentLightLevelInfo`**: HDR 内容光照级别信息

### Rust 内部类型

- **`Reader`**: 对 `png::Reader<BufReader<UniquePtr<SkStreamAdapter>>>` 的 FFI 友好封装，提供逐行解码、元数据查询等功能
- **`ResultOfReader`**: 对 `Result<Reader, DecodingError>` 的 FFI 友好封装
- **`Writer`**: 对 `png::Writer<UniquePtr<WriteTrait>>` 的 FFI 友好封装
- **`ResultOfWriter`**: 对 `Result<Writer, EncodingError>` 的 FFI 友好封装
- **`StreamWriter`**: 对 `png::StreamWriter` 的 FFI 友好封装，支持流式写入
- **`ResultOfStreamWriter`**: 对 `Result<StreamWriter, EncodingError>` 的 FFI 友好封装

### C++ 端类（FFI.h）

- **`WriteTrait`**: 纯虚抽象类，等价于 Rust 的 `dyn std::io::Write`。C++ 实现者需重写 `write()` 和 `flush()` 方法。不可复制、不可移动。

## 公共 API 函数

### 解码 API

- **`new_reader(input)`**: 创建 PNG 解码器，接受 `SkStreamAdapter` 输入流，返回 `ResultOfReader`
- **`Reader::width()` / `Reader::height()`**: 获取图像尺寸
- **`Reader::interlaced()`**: 查询是否为隔行扫描图像
- **`Reader::is_srgb()`**: 查询是否包含 sRGB 块
- **`Reader::try_get_chrm()` / `try_get_gama()` / `try_get_cicp_chunk()` / `try_get_mdcv_chunk()` / `try_get_clli_chunk()`**: 查询色彩空间和 HDR 元数据
- **`Reader::has_*_chunk()` / `get_*_chunk()`**: 查询和获取各种 PNG 辅助块（eXIf、iCCP、tRNS、PLTE、acTL、fcTL、sBIT）
- **`Reader::output_color_type()` / `output_bits_per_component()`**: 获取解码后的输出格式
- **`Reader::next_frame_info()`**: 读取下一帧信息（APNG）
- **`Reader::next_interlaced_row()`**: 解码下一行（隔行扫描模式）
- **`Reader::expand_last_interlaced_row()`**: 展开隔行扫描行数据
- **`Reader::read_row()`**: 直接将解码数据写入调用者提供的缓冲区

### 编码 API

- **`new_writer(output, width, height, color, bits_per_component, compression, icc_profile)`**: 创建 PNG 编码器
- **`Writer::write_text_chunk(keyword, text)`**: 写入 tEXt 文本块（Latin-1 编码）
- **`convert_writer_into_stream_writer(writer)`**: 将 Writer 转换为 StreamWriter 以支持流式写入
- **`StreamWriter::write(data)`**: 流式写入像素数据
- **`finish_encoding(stream_writer)`**: 完成编码并刷新所有缓冲区

## 内部实现细节

### CXX 桥接机制

使用 `#[cxx::bridge(namespace = "rust_png")]` 宏定义 FFI 边界。由于 `cxx` 不支持泛型，所有 `Result<T, E>` 类型都手动单态化为具体的 `ResultOfReader`、`ResultOfWriter`、`ResultOfStreamWriter` 包装类型。

### 类型转换

通过 `From` 和 `Into` trait 实现 Rust 原生 `png` crate 类型与 FFI 类型之间的双向转换：
- `png::ColorType` <-> `ffi::ColorType`
- `png::DisposeOp` -> `ffi::DisposeOp`
- `png::BlendOp` -> `ffi::BlendOp`
- `Option<&png::DecodingError>` -> `ffi::DecodingResult`
- `Option<&png::EncodingError>` -> `ffi::EncodingResult`

### 解码变换（Transformations）

`compute_transformations()` 函数根据图像的颜色类型和位深度决定解码时需要的变换：
- 对低位深度（<8bit）的非索引图像应用 `EXPAND` 变换
- 对 RGB 和 Grayscale 图像应用 `EXPAND` 以处理 tRNS 块的透明度注入
- 对索引图像避免使用 `EXPAND` 以获得更好的性能
- 在非新行为模式下，对 16 位灰度图像应用 `STRIP_16` 变换

### 缓冲区策略

Reader 内部使用 32KB 的 `BufReader` 包装输入流，该值基于 `png` crate 0.17.x 版本的历史 `CHUNK_BUFFER_SIZE` 常量。

### 模糊测试支持

在 `FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION` 模式下，跳过校验和验证以提高模糊测试效率。

### 浮点精度兼容

`png_u32_into_f32()` 使用 `0.00001_f32 * (v.into_scaled() as f32)` 而非直接 `v.into_value()`，以保持与 Blink 渲染引擎中遗留 `ReadColorProfile` 实现的兼容性。

### APNG 帧时长计算

`get_fctl_info()` 中处理了 `delay_den == 0` 的特殊情况，按 PNG 规范将其视为 1/100 秒。

### Writer 的 Latin-1 文本验证

`write_text_chunk()` 严格按照 PNG 规范（W3C PNG-3）验证关键字和文本的 Latin-1 编码合法性。

## 依赖关系

### Rust 依赖
- **`png` crate**: 核心 PNG 编解码库
- **`cxx` crate**: C++/Rust 互操作框架
- **`std::io`**: 标准 I/O traits（BufReader、Write）
- **`skia_rust_common`**: Skia 的 Rust 公共适配层（SkStreamAdapter）

### C++ 依赖（FFI.h）
- **`<stddef.h>` / `<stdint.h>`**: 基本类型定义
- **`rust::cxxbridge1::Slice`**: CXX 桥接的切片类型

## 设计模式与设计决策

- **手动单态化**: 由于 CXX 不支持泛型，使用 `ResultOfReader`/`ResultOfWriter`/`ResultOfStreamWriter` 手动实现 `Result<T,E>` 的单态化，每个类型都提供 `err()` 和 `unwrap()` 方法
- **移动语义模拟**: `unwrap()` 方法通过 `std::mem::swap` 将内部值交换出来，留下一个 C++ 友好的"已移走"状态
- **桥接层隔离**: FFI 层不暴露 Rust `png` crate 的原始类型，而是定义独立的枚举和结构体，确保 ABI 稳定性
- **抽象写入接口**: FFI.h 中的 `WriteTrait` 使用纯虚函数模拟 Rust 的 `dyn Write` trait，允许 C++ 端提供任意写入实现
- **不可复制/不可移动设计**: `WriteTrait` 禁止拷贝和移动，确保生命周期安全
- **压缩级别固定化**: `Level1WithUpFilter` 被显式导出为独立级别，以保持与 M136 版本字段试验结果的一致性

## 性能考量

- 索引色图像避免使用 `EXPAND` 变换，基于 Chromium bug 356882657 的性能测试结果
- 32KB 缓冲区大小经过历史验证，在减少系统调用次数和内存使用之间取得平衡
- 流式写入（StreamWriter）模式避免在内存中缓存整个图像
- 压缩级别提供从 `Fastest`（fdeflate 后端）到 `High` 的多档选择，允许调用者根据场景权衡速度与文件大小
- `write_text_chunk` 的 Latin-1 验证使用逐字节检查，对于短文本元数据开销可忽略

### WriteTrait 的 C++ 端实现要求

FFI.h 中的 `WriteTrait` 抽象类对实现者有以下约束：
- `write()` 方法必须写入整个缓冲区或返回失败，不支持部分写入
- `flush()` 方法是不可失败的（与 Rust 的 `Write::flush` 不同），这模仿了 `SkWStream::flush` 的语义
- 析构函数通过 `virtual ~WriteTrait() = default` 暴露，使得 `std::unique_ptr<WriteTrait>` 能够跨 FFI 边界传递
- 禁止拷贝和移动构造/赋值，确保生命周期由 `unique_ptr` 独占管理

### Reader 的隔行扫描支持

Reader 通过 `next_interlaced_row()` 和 `expand_last_interlaced_row()` 两个方法支持 Adam7 隔行扫描 PNG 图像的解码。解码流程为：
1. 调用 `next_interlaced_row()` 获取当前隔行扫描行的数据和 `InterlaceInfo`
2. 内部将 `InterlaceInfo` 缓存在 `last_interlace_info` 字段中
3. 调用 `expand_last_interlaced_row()` 将隔行数据展开到完整的图像缓冲区中
4. 重复直到所有行解码完成

对于非隔行扫描图像，可以直接使用 `read_row()` 方法逐行解码到调用者提供的缓冲区。

### 编码器的 ICC 配置文件处理

`new_writer()` 中 `icc_profile` 参数为空切片时视为 `None`。非空时通过 `Cow::Owned` 拷贝一份传递给 `png::Info`，确保编码器拥有数据的所有权。

### 条件编译

通过 `cfg(feature = "skia_png_new_gray16_behavior_for_crbug359245096")` 特性标志控制灰度 16 位图像的处理行为。启用新行为时不再剥离最低有效 8 位，保留完整的 16 位精度。

### 错误处理策略

所有跨 FFI 边界的错误都通过枚举值返回（`DecodingResult`/`EncodingResult`），不使用异常或 panic。Rust 侧的 `Result` 类型在通过 `ResultOfXxx` 包装器传递时，调用者必须先检查 `err()` 再调用 `unwrap()`。

## 相关文件

- `rust/png/BUILD.bazel` - 构建配置
- `rust/common/SkStreamAdapter.h` / `rust/common/SkStreamAdapter.rs` - Skia 流到 Rust Read 适配器
- `src/codec/SkPngRustCodec.cpp` - C++ 端使用此 FFI 的 PNG 解码实现
- `src/encode/SkPngRustEncoderImpl.cpp` - C++ 端使用此 FFI 的 PNG 编码实现
- `src/codec/SkPngCodec.cpp` - 传统的基于 libpng 的 PNG 解码器（对照实现）
- `rust/png/FFI.rs.h` - CXX 自动生成的 C++ 头文件（构建产物）
- `include/codec/SkPngDecoder.h` - PNG 解码器的公共注册接口
- `include/encode/SkPngEncoder.h` - PNG 编码器的公共接口
- `third_party/libpng/` - 传统 libpng 依赖（Rust png crate 的替代目标）

### 从 libpng 到 Rust png 的迁移背景

此 FFI 层是 Skia 将 PNG 编解码从 C 库（libpng）迁移到 Rust 库（png crate）的核心组件。迁移的主要动机包括：
- 内存安全：Rust 的所有权系统消除了 libpng 中常见的内存安全问题
- 减少安全漏洞：libpng 历史上有多个 CVE，Rust 实现从根本上减少了此类风险
- 现代 PNG 特性支持：Rust png crate 对 APNG、HDR 元数据等新特性有更好的支持
- 性能竞争力：经过优化的 Rust 实现在性能上与 libpng 具有竞争力

### CXX 桥接的局限性

使用 CXX 进行 Rust/C++ 互操作存在以下限制，影响了本模块的设计：
- 不支持泛型类型跨 FFI 边界传递，因此需要手动单态化 `Result<T, E>`
- 不支持 trait 对象直接传递，因此需要 `WriteTrait` 抽象类作为替代
- `UniquePtr<T>` 必须是完整类型，不能跨 FFI 传递前向声明的类型
- 枚举值必须在 `#[cxx::bridge]` 块中显式列出，不能自动从 Rust 枚举派生
