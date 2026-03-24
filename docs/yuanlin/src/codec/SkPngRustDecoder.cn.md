# SkPngRustDecoder

> 源文件
> - include/codec/SkPngRustDecoder.h
> - src/codec/SkPngRustDecoder.cpp

## 概述

`SkPngRustDecoder` 是 Skia 中基于 Rust 实现的 PNG 图像解码器命名空间。它提供了 PNG 格式检测和解码功能，是 Skia 编解码器架构的一部分。该模块作为轻量级的工厂接口，将 PNG 解码工作委托给底层的 `SkPngRustCodec` 实现。

此解码器遵循 Skia 的统一编解码器接口设计，可以通过 `SkCodecs::Decoder` 结构轻松集成到编解码器注册系统中。

## 架构位置

`SkPngRustDecoder` 位于 Skia 的编解码器层次结构中：

```
应用层 (SkImage, SkBitmap)
    ↓
编解码器工厂 (SkCodec::MakeFromStream)
    ↓
格式解码器 (SkPngRustDecoder, SkJpegDecoder, ...)
    ↓
具体实现 (SkPngRustCodec)
    ↓
数据流 (SkStream)
```

该命名空间是 Skia 编解码器插件系统的标准组件，与其他格式解码器（JPEG、WebP 等）并列。

## 主要类与结构体

### SkPngRustDecoder 命名空间

这不是一个类，而是包含静态函数和工厂方法的命名空间。

**主要组件**：

| 组件 | 类型 | 说明 |
|------|------|------|
| `IsPng()` | 函数 | PNG 格式检测 |
| `Decode()` | 函数 | PNG 解码器创建 |
| `Decoder()` | 内联函数 | 返回解码器描述符 |

### 内部数据结构

**PNG 签名（Magic Number）**：
```cpp
{0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A}
```
这是 PNG 文件格式的标准文件头，用于格式识别。

## 公共 API 函数

### IsPng

```cpp
SK_API bool IsPng(const void* buff, size_t bytesRead)
```

**功能**：检测数据是否为 PNG 格式

**参数**：
- `buff`：数据缓冲区指针
- `bytesRead`：已读取的字节数

**返回值**：
- `true`：数据为 PNG 格式
- `false`：数据不是 PNG 或数据不足

**实现逻辑**：
1. 检查数据长度是否至少 8 字节
2. 比较前 8 字节是否与 PNG 签名匹配

### Decode

```cpp
SK_API std::unique_ptr<SkCodec> Decode(
    std::unique_ptr<SkStream> stream,
    SkCodec::Result* result,
    SkCodecs::DecodeContext context = nullptr
)
```

**功能**：从数据流创建 PNG 解码器

**参数**：
- `stream`：输入数据流（转移所有权）
- `result`：输出解码结果状态
- `context`：解码上下文（可选，当前未使用）

**返回值**：
- 成功：返回 `SkCodec` 智能指针
- 失败：返回 `nullptr`，并通过 `result` 输出错误码

**实现逻辑**：
1. 如果 `result` 为空，使用局部变量存储结果
2. 调用 `SkPngRustCodec::MakeFromStream()` 创建解码器
3. 返回解码器实例

### Decoder

```cpp
inline constexpr SkCodecs::Decoder Decoder()
```

**功能**：返回解码器描述符结构

**返回值**：`SkCodecs::Decoder` 结构，包含：
- `id`：格式标识符 `"png"`
- `isFormat`：指向 `IsPng` 函数
- `makeCodec`：指向 `Decode` 函数

**用途**：用于注册到 Skia 的编解码器系统

## 内部实现细节

### PNG 格式检测

PNG 文件以固定的 8 字节签名开头：
- `0x89`：非 ASCII 字符，防止文本误识别
- `0x50 0x4E 0x47`：ASCII 字符 "PNG"
- `0x0D 0x0A`：DOS 风格换行符
- `0x1A`：DOS 文件结束符
- `0x0A`：Unix 换行符

该签名设计可以检测多种传输错误（换行符转换、7 位传输等）。

### 解码器创建流程

```
Decode() 调用
    ↓
检查 result 指针
    ↓
调用 SkPngRustCodec::MakeFromStream()
    ↓
返回 SkCodec 实例
```

实际的解码逻辑由 `SkPngRustCodec` 类实现，该类继承自 `SkCodec` 并实现了完整的 PNG 解码功能。

### 解码上下文

当前实现中 `DecodeContext` 参数未被使用，为未来扩展预留：
- 可能用于传递解码配置
- 可能用于多线程上下文
- 保持与其他解码器接口一致

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkCodec` | 编解码器基类和接口 |
| `SkStream` | 数据流抽象 |
| `SkPngRustCodec` | 底层 PNG 解码实现 |
| `SkCodecs` | 编解码器注册系统 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| 编解码器注册系统 | 将 PNG 解码器注册为可用格式 |
| `SkCodec::MakeFromStream()` | 自动选择合适的解码器 |
| `SkImage::MakeFromEncoded()` | 通过编解码器加载图像 |

## 设计模式与设计决策

### 工厂方法模式

`Decode()` 函数作为工厂方法：
- 封装具体解码器的创建细节
- 统一返回基类 `SkCodec` 指针
- 便于替换底层实现

### 策略模式

通过 `SkCodecs::Decoder` 结构实现策略模式：
- 封装格式检测策略（`IsPng`）
- 封装解码创建策略（`Decode`）
- 运行时可插拔不同的解码器

### 命名空间设计

使用命名空间而非类的原因：
- 无需实例化，所有功能都是静态的
- 避免不必要的对象开销
- 清晰的代码组织

### Rust 集成

模块名称包含 "Rust" 表明：
- 底层实现使用 Rust 语言
- 可能利用 Rust 的内存安全特性
- 通过 FFI（外部函数接口）与 C++ 交互

## 性能考量

### 格式检测优化

1. **最小读取**：只需读取 8 字节即可判断格式
2. **快速失败**：长度检查在内存比较前完成
3. **单次比较**：`memcmp()` 高效实现批量比较

### 智能指针管理

使用 `std::unique_ptr` 的优势：
- 自动内存管理，防止泄漏
- 明确所有权转移语义
- 零运行时开销（相比原始指针）

### 数据流处理

`SkStream` 的使用：
- 支持按需读取，避免加载整个文件
- 支持多种数据源（文件、内存、网络）
- 统一的接口便于优化

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/codec/SkPngRustDecoder.h` | 公共接口声明 |
| `src/codec/SkPngRustDecoder.cpp` | 实现代码 |
| `src/codec/SkPngRustCodec.h` | 底层 PNG 解码器（推断） |
| `src/codec/SkPngRustCodec.cpp` | 底层解码实现（推断） |
| `include/codec/SkCodec.h` | 编解码器基类 |
| `include/core/SkStream.h` | 数据流接口 |
| `include/codec/SkCodecs.h` | 编解码器注册系统（推断） |
