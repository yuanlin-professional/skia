# SkStreamAdapter

> 源文件: rust/common/SkStreamAdapter.h, rust/common/SkStreamAdapter.cpp

## 概述

`SkStreamAdapter` 是 Skia 中用于将 C++ 的 `SkStream` 适配为 Rust 标准 I/O trait 的适配器类。该类实现了 Rust-C++ 互操作层,使得 Rust 编写的编解码器可以通过标准的 `Read` 和 `Seek` trait 访问 Skia 的流抽象,从而实现跨语言的流式数据访问。

该适配器的核心设计目标是提供零成本抽象,通过薄包装层将 Skia 的流操作直接映射到 Rust 的 I/O 接口,避免不必要的缓冲和内存拷贝。它被设计为所有 Rust 编解码器(如 PNG、ICC 等)的通用组件。

## 架构位置

```
skia/
├── include/core/
│   └── SkStream.h          # Skia 流抽象基类
├── rust/
│   ├── common/
│   │   ├── SkStreamAdapter.h    # C++ 适配器头文件
│   │   ├── SkStreamAdapter.cpp  # C++ 适配器实现
│   │   ├── io_traits_ffi.rs     # Rust trait 实现
│   │   └── SpanUtils.h          # Slice/Span 转换工具
│   ├── png/                     # PNG 编解码器使用示例
│   └── icc/                     # ICC 解析器使用示例
└── src/codec/
    └── SkPngRustCodec.cpp       # 使用 SkStreamAdapter 的 PNG 编解码器
```

该模块位于 `rust/common/` 目录,作为 Rust 互操作层的通用基础设施,被多个 Rust 编解码器共享使用。

## 主要类与结构体

### C++ 侧

**`rust::stream::SkStreamAdapter`**
- **用途**: 将 `SkStream*` 包装为可从 Rust 调用的适配器
- **生命周期**: 不拥有流对象,调用者必须确保底层 `SkStream` 在 `SkStreamAdapter` 生命周期内保持有效
- **限制**: 不可拷贝、不可移动,确保 `this` 指针稳定

**关键成员**:
- `SkStream* fStream`: 底层流指针(未拥有)

**接口方法**:
- `size_t read(rust::Slice<uint8_t> buffer)`: 读取数据到缓冲区
- `bool seek_from_start(uint64_t requestedPos, uint64_t& finalPos)`: 从起始位置寻址
- `bool seek_from_end(int64_t requestedOffset, uint64_t& finalPos)`: 从末尾偏移寻址
- `bool seek_relative(int64_t requestedOffset, uint64_t& finalPos)`: 相对当前位置寻址

### Rust 侧

**`SkStreamAdapter` (透明类型)**
- 通过 `#[cxx::bridge]` 声明的外部 C++ 类型
- 暴露为 `Pin<&mut SkStreamAdapter>` 以保证内存稳定性

**Trait 实现**:
- `impl Read for Pin<&mut SkStreamAdapter>`: 实现标准读取接口
- `impl Seek for Pin<&mut SkStreamAdapter>`: 实现标准寻址接口

## 公共 API 函数

### C++ API

**`explicit SkStreamAdapter(SkStream* stream)`**
- 构造适配器,包装指定的流对象
- 断言流指针非空
- **生命周期约束**: 调用者保证 `stream` 在适配器生命周期内有效

**`size_t read(rust::Slice<uint8_t> buffer)`**
- 从流中读取最多 `buffer.size()` 字节到缓冲区
- 返回实际读取的字节数(可能少于请求的字节数)
- 使用 `ToSkSpan()` 转换 Rust slice 为 Skia span

**`bool seek_from_start(uint64_t requestedPos, uint64_t& finalPos)`**
- 寻址到流的绝对位置
- 成功时设置 `finalPos` 为实际位置并返回 `true`
- 处理 64 位到 `size_t` 的安全转换

**`bool seek_from_end(int64_t requestedOffset, uint64_t& finalPos)`**
- 从流末尾偏移寻址(负偏移向前,正偏移不支持)
- 要求流支持 `hasLength()` 和 `getLength()`
- 内部转换为 `seek_from_start()` 调用

**`bool seek_relative(int64_t requestedOffset, uint64_t& finalPos)`**
- 相对当前位置偏移寻址
- 要求流支持 `hasPosition()` 和 `getPosition()`
- 零偏移被优化为无操作

### Rust API

**`impl Read for Pin<&mut SkStreamAdapter>`**
```rust
fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize>
```
- 实现标准 `std::io::Read` trait
- 调用底层 C++ `read()` 方法
- 始终返回 `Ok(bytes_read)`,不报告错误

**`impl Seek for Pin<&mut SkStreamAdapter>`**
```rust
fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64>
```
- 实现标准 `std::io::Seek` trait
- 将 `SeekFrom::Start/End/Current` 映射到对应的 C++ 方法
- 失败时返回 `Err(ErrorKind::Other)`

## 内部实现细节

### 类型转换和内存安全

**Slice 到 Span 转换**:
```cpp
size_t SkStreamAdapter::read(rust::Slice<uint8_t> buffer) {
    SkSpan<uint8_t> span = ToSkSpan(buffer);
    return fStream->read(span.data(), span.size());
}
```
`ToSkSpan()` 工具函数处理空 slice 的边界情况,避免解引用空指针的未定义行为。

**安全数值转换**:
使用 `SkSafeMath` 检测整数溢出和截断:
```cpp
SkSafeMath safe;
size_t pos = safe.castTo<size_t>(requestedPos);
if (!safe.ok()) {
    return false;
}
```

### Seek 操作实现

**从起始寻址 (`seek_from_start`)**:
1. 使用 `SkSafeMath` 安全转换 `uint64_t` 到 `size_t`
2. 调用 `fStream->seek(pos)`
3. 验证流位置与请求位置匹配(如果流支持 `hasPosition()`)

**从末尾寻址 (`seek_from_end`)**:
1. 检查流是否支持长度查询 (`hasLength()`)
2. 验证偏移量有效性:
   - 不支持正偏移(超出流末尾)
   - 不支持 `INT64_MIN`(取反会溢出)
3. 计算绝对位置: `endPos - abs(offset)`
4. 转发到 `seek_from_start()`

**相对寻址 (`seek_relative`)**:
1. 检查流是否支持位置查询 (`hasPosition()`)
2. 安全转换 `int64_t` 到 `long`(SkStream::move 的参数类型)
3. 优化零偏移为无操作
4. 调用 `fStream->move(offset)` 并返回新位置

### 边界情况处理

1. **空 slice**: `ToSkSpan()` 返回空 span 而不解引用空指针
2. **整数溢出**: `SkSafeMath` 检测所有转换,失败时提前返回 `false`
3. **不支持的操作**: 检查流能力(hasLength/hasPosition)后再调用对应方法
4. **零偏移**: `seek_relative` 优化为无操作,避免不必要的流移动

### Pin 语义

Rust 侧使用 `Pin<&mut SkStreamAdapter>` 确保:
- 适配器对象在内存中不被移动
- C++ 的 `this` 指针保持稳定
- 安全地持有可变引用跨越 FFI 边界

## 依赖关系

### 外部依赖
- **SkStream.h**: Skia 流抽象基类
- **cxx**: Rust-C++ 互操作框架
- **SkSafeMath**: Skia 安全算术工具

### 内部依赖
- **SpanUtils.h**: `ToSkSpan()` 工具函数
- **io_traits_ffi.rs**: Rust trait 实现

### 依赖图
```
Rust 编解码器 (png, icc)
    ↓
io_traits_ffi.rs (Read/Seek trait)
    ↓
SkStreamAdapter.cpp
    ↓
SkStream (SkMemoryStream, SkFILEStream 等)
```

## 设计模式与设计决策

### 1. 适配器模式
经典的适配器模式,将 Skia 特有的 `SkStream` 接口适配为 Rust 标准库的 `Read` + `Seek` trait。

### 2. 零成本抽象
- 无虚函数调用开销(直接转发到 SkStream 方法)
- 无额外缓冲(直接操作 Rust slice)
- 编译期内联潜力高

### 3. 借用语义
适配器不拥有流对象,遵循 Rust 的借用检查哲学,调用者负责生命周期管理。

### 4. 防御性编程
大量使用断言和边界检查:
- `SkASSERT_RELEASE` 验证关键假设
- `SkSafeMath` 防止整数溢出
- 空指针检查和能力查询

### 5. 统一命名空间
C++ 和 Rust 都使用 `rust::stream` 命名空间,通过 CXX bridge 的 `namespace` 属性实现类型统一。

### 6. 未来扩展性
代码注释建议未来可将 `fStream` 字段替换为虚方法 `virtual SkStream& stream() = 0`,支持在子类中定制流来源。

### 7. 错误处理策略
- C++ 侧: 返回布尔值表示成功/失败
- Rust 侧: 映射到 `std::io::Result`,失败时使用 `ErrorKind::Other`

## 性能考量

### 1. 直接转发调用
所有方法都是薄包装,直接调用底层 SkStream 方法,无额外逻辑开销。

### 2. 零拷贝读取
`read()` 方法直接将数据读取到 Rust 提供的缓冲区,避免中间缓冲区。

### 3. 内联优化
简短的方法体(如 `seek_from_start`)适合编译器内联,减少函数调用开销。

### 4. 静态断言
使用 `static_assert(sizeof(uint64_t) >= sizeof(size_t))` 等编译期检查,运行时无开销。

### 5. 条件优化
零偏移 seek 被优化为无操作:
```cpp
if (offset != 0 && !fStream->move(offset)) { ... }
```

### 6. 潜在瓶颈
- FFI 调用开销: 每次 `read()` 或 `seek()` 都跨越 FFI 边界
- 建议: 使用较大的缓冲区批量读取,减少 FFI 调用次数

### 7. 内存对齐
Rust slice 和 Skia span 都是 `{ptr, len}` 表示,内存布局兼容,转换无拷贝。

## 相关文件

### 核心实现
- `rust/common/SkStreamAdapter.h`: C++ 适配器声明
- `rust/common/SkStreamAdapter.cpp`: C++ 适配器实现
- `rust/common/io_traits_ffi.rs`: Rust trait 实现
- `rust/common/SpanUtils.h`: Slice/Span 转换工具

### 依赖接口
- `include/core/SkStream.h`: Skia 流基类
- `src/base/SkSafeMath.h`: 安全算术工具
- `third_party/rust/cxx/v1/cxx.h`: CXX bridge 头文件

### 使用示例
- `rust/png/FFI.rs`: PNG 解码器中的 `SkStreamAdapter` 使用
- `rust/icc/FFI.rs`: ICC 解析器中的流式读取
- `src/codec/SkPngRustCodec.cpp`: C++ 侧创建和使用适配器

### 测试文件
- `tests/StreamTest.cpp`: SkStream 基础测试
- `tests/RustPngCodecTest.cpp`: 通过 Rust PNG 解码器间接测试适配器

### 构建配置
- `rust/common/BUILD.bazel` 或 `BUILD.gn`: 构建规则
- `Cargo.toml`: Rust 依赖声明(cxx crate)
