# SkBmpRustDecoder

> 源文件：experimental/rust_bmp/decoder/SkBmpRustDecoder.h, experimental/rust_bmp/decoder/SkBmpRustDecoder.cpp

## 概述

`SkBmpRustDecoder` 是 Skia 中基于 Rust 实现的 BMP 图像解码器模块。该模块提供了 BMP 格式的识别和解码功能，通过 FFI（Foreign Function Interface）机制调用 Rust 编写的底层解码器实现，为 Skia 的编解码器系统提供了 BMP 格式的支持。这是一个实验性功能，展示了 Skia 如何通过 Rust 与 C++ 的互操作来实现高性能的图像解码。

## 架构位置

该模块位于 Skia 的实验性功能目录中，属于编解码器子系统的一部分：

- 位于 `experimental/rust_bmp/decoder/` 目录
- 依赖于 Rust FFI 接口层 (`experimental/rust_bmp/ffi/FFI.rs.h`)
- 使用实现类 `SkBmpRustCodec` 完成实际解码工作
- 继承自 Skia 核心编解码器框架 (`SkCodec`)
- 与 Skia 的流处理系统 (`SkStream`) 和数据容器 (`SkData`) 集成

该模块作为 Skia 编解码器注册系统的一个插件，可以被动态注册到编解码器工厂中。

## 主要类与结构体

### SkBmpRustDecoder 命名空间

整个功能封装在 `SkBmpRustDecoder` 命名空间中，提供三个核心函数：

**IsBmp()**
```cpp
bool IsBmp(const void* buff, size_t bytesRead)
```
用于快速识别给定的字节序列是否为有效的 BMP 图像格式。通过调用 Rust 实现的 `rust_bmp::is_bmp_data()` 函数进行检测。

**Decode() - Stream 版本**
```cpp
std::unique_ptr<SkCodec> Decode(std::unique_ptr<SkStream> stream,
                                SkCodec::Result* result,
                                SkCodecs::DecodeContext = nullptr)
```
从 `SkStream` 对象解码 BMP 图像，返回 `SkCodec` 对象用于后续解码操作。

**Decode() - Data 版本**
```cpp
std::unique_ptr<SkCodec> Decode(sk_sp<const SkData> data,
                                SkCodec::Result* result,
                                SkCodecs::DecodeContext = nullptr)
```
从 `SkData` 对象解码 BMP 图像，内部通过创建 `SkMemoryStream` 转换为流处理。

**Decoder() 工厂函数**
```cpp
inline constexpr SkCodecs::Decoder Decoder()
```
返回编解码器描述符结构体，包含编解码器名称 "rust_bmp"、识别函数和解码函数。

## 公共 API 函数

### IsBmp
**功能**：检测数据是否为 BMP 格式
- **参数**：
  - `buff`: 字节缓冲区指针
  - `bytesRead`: 已读取的字节数
- **返回值**：`true` 表示是 BMP 格式，否则返回 `false`
- **使用场景**：在解码前快速识别格式，避免不必要的解码尝试

### Decode (Stream)
**功能**：从流对象解码 BMP 图像
- **参数**：
  - `stream`: 输入流的智能指针
  - `result`: 输出参数，返回解码结果状态
  - `context`: 解码上下文（可选，默认 nullptr）
- **返回值**：`SkCodec` 智能指针，失败时返回 nullptr
- **使用场景**：从文件流或网络流解码 BMP 图像

### Decode (Data)
**功能**：从数据对象解码 BMP 图像
- **参数**：
  - `data`: 包含完整图像数据的 `SkData` 对象
  - `result`: 输出参数，返回解码结果状态
  - `context`: 解码上下文（可选，默认 nullptr）
- **返回值**：`SkCodec` 智能指针，失败时返回 nullptr
- **使用场景**：从内存中的完整数据解码 BMP 图像

### Decoder
**功能**：获取编解码器描述符
- **返回值**：`SkCodecs::Decoder` 结构体，包含编解码器元信息
- **使用场景**：注册编解码器到 Skia 的编解码器工厂系统

## 内部实现细节

### BMP 格式识别实现

`IsBmp()` 函数的实现展示了 C++ 与 Rust 的互操作模式：

```cpp
bool IsBmp(const void* buff, size_t bytesRead) {
    const rust::Slice<const uint8_t> data_slice{
        static_cast<const uint8_t*>(buff),
        bytesRead
    };
    return rust_bmp::is_bmp_data(data_slice);
}
```

- 将 C++ 原始指针转换为 Rust 的 `Slice` 类型
- 调用 Rust FFI 函数 `rust_bmp::is_bmp_data()` 进行检测
- 使用 `cxx` crate 提供的类型安全互操作机制

### 解码器创建流程

两个 `Decode()` 函数重载实现了不同输入源的统一处理：

1. **Stream 版本**：直接委托给 `SkBmpRustCodec::MakeFromStream()`，由实现类处理流数据
2. **Data 版本**：将 `SkData` 包装为 `SkMemoryStream`，然后调用 Stream 版本的 Decode 函数

这种设计模式实现了代码复用，避免了重复的解码逻辑。

### 错误处理机制

- 通过 `SkCodec::Result*` 输出参数返回详细的错误状态
- 解码失败时返回 `nullptr`，调用者需检查返回值
- Rust 侧的错误会通过 FFI 边界传递到 C++ 侧

## 依赖关系

**头文件依赖**：
- `include/codec/SkCodec.h` - Skia 编解码器基类
- `include/core/SkRefCnt.h` - 引用计数智能指针
- `include/core/SkData.h` - 数据容器类
- `include/core/SkStream.h` - 流抽象接口
- `include/private/base/SkAPI.h` - API 导出宏定义

**实现依赖**：
- `experimental/rust_bmp/ffi/FFI.rs.h` - Rust FFI 接口头文件
- `experimental/rust_bmp/decoder/impl/SkBmpRustCodec.h` - 实际解码器实现
- `src/core/SkStreamPriv.h` - 流的私有辅助函数

**Rust 依赖**：
- `rust_bmp` crate - Rust 实现的 BMP 解码库
- `cxx` crate - C++ 与 Rust 互操作框架

## 设计模式与设计决策

### 外观模式（Facade Pattern）
该模块作为 Rust BMP 解码器的外观，隐藏了 FFI 调用的复杂性，向 Skia 提供统一的 C++ 接口。

### 适配器模式（Adapter Pattern）
将 Rust 实现的解码器适配到 Skia 的 `SkCodec` 接口体系，实现了不同语言生态系统的集成。

### 工厂模式（Factory Pattern）
`Decoder()` 函数返回编解码器描述符，支持动态注册和创建解码器实例。

### 重要设计决策

1. **使用 Rust 实现核心解码逻辑**：利用 Rust 的内存安全特性，避免 C++ 中常见的内存安全问题
2. **通过 FFI 边界隔离**：C++ 和 Rust 代码通过明确的 FFI 接口分离，降低耦合度
3. **保持 Skia API 兼容性**：对外暴露的接口完全符合 Skia 的编解码器规范
4. **实验性标记**：放置在 `experimental/` 目录，表明该功能尚未稳定

## 性能考量

### FFI 调用开销
- C++ 与 Rust 之间的 FFI 调用存在一定开销，但对于图像解码这种计算密集型任务，开销可忽略不计
- 使用 `rust::Slice` 避免了数据复制，仅传递指针和长度

### 内存管理效率
- `std::unique_ptr` 和 `sk_sp` 确保资源自动释放
- `SkMemoryStream::Make()` 直接引用已有数据，避免内存复制

### 解码性能
- Rust 实现的解码器可利用 LLVM 的优化能力
- BMP 格式相对简单，解码性能主要受 IO 和像素格式转换影响

### 优化建议
- 对于频繁使用的场景，可缓存 `IsBmp()` 的结果
- 考虑使用内存映射（memory-mapped IO）处理大型 BMP 文件
- 可以考虑在 Rust 侧实现并行解码（针对多帧或大图像）

## 相关文件

**实现文件**：
- `experimental/rust_bmp/decoder/impl/SkBmpRustCodec.h` - 完整的解码器实现类
- `experimental/rust_bmp/decoder/impl/SkBmpRustCodec.cpp` - 解码器实现细节

**FFI 接口**：
- `experimental/rust_bmp/ffi/FFI.rs.h` - C++ 侧的 Rust FFI 接口声明
- `experimental/rust_bmp/ffi/*.rs` - Rust 侧的 FFI 实现（推测）

**测试文件**：
- `tests/` 目录下可能存在相关的单元测试和集成测试

**构建配置**：
- `BUILD.gn` 或 `CMakeLists.txt` - 配置 Rust 与 C++ 的联合编译
- `Cargo.toml` - Rust crate 的依赖配置

**参考实现**：
- `src/codec/SkBmpCodec.h` - Skia 原生的 BMP 解码器实现
- `include/codec/SkCodec.h` - 编解码器接口定义
