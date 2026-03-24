# io_traits_ffi

> 源文件: rust/common/io_traits_ffi.rs

## 概述

`io_traits_ffi.rs` 是 Skia Rust 互操作层中为 `SkStreamAdapter` 实现标准 Rust I/O trait 的模块。该模块通过 CXX bridge 声明 C++ 的 `SkStreamAdapter` 类型,并为其实现 `std::io::Read` 和 `std::io::Seek` trait,使得 Rust 编写的编解码器可以使用标准库的 I/O 接口访问 Skia 的流抽象。

该模块是所有 Rust 编解码器的基础依赖,提供统一的流式数据访问接口,消除了每个编解码器单独实现 FFI 绑定的重复工作。

## 架构位置

```
skia/
├── include/core/
│   └── SkStream.h                      # Skia 流基类
├── rust/common/
│   ├── SkStreamAdapter.h               # C++ 适配器声明
│   ├── SkStreamAdapter.cpp             # C++ 适配器实现
│   └── io_traits_ffi.rs                # 本文件(Rust trait 实现)
├── rust/
│   ├── png/
│   │   └── FFI.rs                      # 使用 SkStreamAdapter 的 PNG 模块
│   └── icc/
│       └── FFI.rs                      # 使用 SkStreamAdapter 的 ICC 模块
└── src/codec/
    └── SkPngRustCodec.cpp              # C++ 侧创建 SkStreamAdapter
```

该模块位于 `rust/common/` 目录,作为 Rust 编解码器的通用基础设施。

## 主要类与结构体

### FFI 模块 (`ffi`)

**命名空间**: `rust::stream`

**`type SkStreamAdapter`**
- 通过 `unsafe extern "C++"` 声明的不透明 C++ 类型
- 对应 C++ 中的 `rust::stream::SkStreamAdapter` 类
- 在 Rust 中只能通过指针或引用访问,不能直接实例化

**外部方法**:
```rust
fn read(self: Pin<&mut SkStreamAdapter>, buffer: &mut [u8]) -> usize;

fn seek_from_start(
    self: Pin<&mut SkStreamAdapter>,
    requested_pos: u64,
    final_pos: &mut u64,
) -> bool;

fn seek_from_end(
    self: Pin<&mut SkStreamAdapter>,
    requested_offset: i64,
    final_pos: &mut u64,
) -> bool;

fn seek_relative(
    self: Pin<&mut SkStreamAdapter>,
    requested_offset: i64,
    final_pos: &mut u64,
) -> bool;
```

**`impl UniquePtr<SkStreamAdapter>`**
- 显式声明 `UniquePtr` 支持,使 CXX bridge 生成智能指针包装
- 允许 Rust 侧安全持有 C++ 对象的所有权

## 公共 API 函数

### Trait 实现

**`impl<'a> Read for Pin<&'a mut SkStreamAdapter>`**

实现 Rust 标准库的 `std::io::Read` trait,提供统一的读取接口。

**方法**:
```rust
fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize>
```

**行为**:
- 调用底层 C++ 的 `read()` 方法
- 返回实际读取的字节数(可能少于 `buf.len()`)
- 始终返回 `Ok(bytes_read)`,不报告错误(遵循 SkStream 的语义)

**用法示例**:
```rust
use std::io::Read;
let mut buffer = vec![0u8; 1024];
let bytes_read = stream.read(&mut buffer)?;
```

**`impl<'a> Seek for Pin<&'a mut SkStreamAdapter>`**

实现 Rust 标准库的 `std::io::Seek` trait,提供统一的寻址接口。

**方法**:
```rust
fn seek(&mut self, pos: SeekFrom) -> std::io::Result<u64>
```

**行为**:
- 根据 `SeekFrom` 枚举值调用相应的 C++ 方法:
  - `SeekFrom::Start(pos)` → `seek_from_start(pos, &mut final_pos)`
  - `SeekFrom::End(offset)` → `seek_from_end(offset, &mut final_pos)`
  - `SeekFrom::Current(offset)` → `seek_relative(offset, &mut final_pos)`
- 成功时返回 `Ok(final_pos)`(最终位置)
- 失败时返回 `Err(ErrorKind::Other.into())`

**用法示例**:
```rust
use std::io::{Seek, SeekFrom};
let new_pos = stream.seek(SeekFrom::Start(100))?;
let end_pos = stream.seek(SeekFrom::End(-10))?;
```

### 重导出

**`pub use ffi::SkStreamAdapter;`**
- 将 `SkStreamAdapter` 类型从 `ffi` 模块重导出到 `io_traits_ffi` 模块
- 允许其他 Rust 模块通过 `use crate::io_traits_ffi::SkStreamAdapter` 访问

## 内部实现细节

### Pin 语义

使用 `Pin<&mut SkStreamAdapter>` 确保适配器对象在内存中的稳定性:

**原因**:
1. C++ 的 `SkStreamAdapter` 是不可移动的(删除了移动构造函数)
2. C++ 方法接收 `this` 指针,要求对象地址不变
3. `Pin` 防止 Rust 代码移动对象(如通过 `std::mem::swap`)

**实现**:
- FFI 方法签名使用 `self: Pin<&mut SkStreamAdapter>`
- Trait 实现接收 `Pin<&'a mut SkStreamAdapter>`
- 使用 `self.as_mut()` 重新借用 Pin 包装的引用

### 错误处理映射

**C++ 侧**:
- 返回 `bool` 表示成功/失败
- 通过引用参数 `&mut final_pos` 返回结果值

**Rust 侧**:
- 将 `bool` 映射到 `Result<u64, std::io::Error>`
- 成功: `Ok(final_pos)`
- 失败: `Err(ErrorKind::Other.into())`

**设计权衡**:
- 丢失了详细的错误信息(SkStream 也不提供详细错误)
- 符合 Rust I/O trait 的惯例
- 简化了跨 FFI 的错误传递

### 生命周期管理

**`impl<'a> Read for Pin<&'a mut SkStreamAdapter>`**:
- 生命周期 `'a` 绑定到底层 `SkStream` 的生命周期
- 编译器确保 `SkStreamAdapter` 不能超出 `SkStream` 的生命周期
- 防止悬垂指针和使用后释放

### CXX Bridge 类型统一

**命名空间一致性**:
- C++ 侧: `namespace rust::stream { class SkStreamAdapter; }`
- Rust 侧: `#[cxx::bridge(namespace = "rust::stream")]`
- CXX bridge 确保两侧引用同一个 C++ 类型

**UniquePtr 支持**:
```rust
impl UniquePtr<SkStreamAdapter> {}
```
- 触发 CXX bridge 生成 `cxx::UniquePtr<SkStreamAdapter>` 绑定
- 允许 Rust 侧拥有 C++ 对象(如果需要)

## 依赖关系

### 外部依赖
- **std::io**: Rust 标准库的 I/O trait (`Read`, `Seek`, `SeekFrom`, `ErrorKind`)
- **std::pin**: Pin 类型用于不可移动对象
- **cxx**: CXX bridge 宏和类型

### C++ 依赖
- **SkStreamAdapter.h**: C++ 适配器声明

### 依赖图
```
Rust 编解码器 (png::FFI, icc::FFI)
    ↓
io_traits_ffi::SkStreamAdapter (Read + Seek trait)
    ↓ (FFI)
SkStreamAdapter.cpp (C++ 实现)
    ↓
SkStream (Skia 流基类)
```

## 设计模式与设计决策

### 1. Trait 实现模式
通过为外部 C++ 类型实现 Rust 标准 trait,实现"鸭子类型"式的接口统一。

### 2. 桥接模式
`SkStreamAdapter` 作为 Skia 和 Rust 标准库之间的桥接,隐藏 FFI 复杂性。

### 3. 零成本抽象
Trait 方法是薄包装,优化后可能被内联为直接的 FFI 调用。

### 4. 类型安全
CXX bridge 生成类型安全的绑定,避免手动编写 `extern "C"` 函数。

### 5. 重用标准接口
实现 `Read` 和 `Seek` trait 使得 Rust 编解码器可以使用大量基于这些 trait 的第三方库(如 `png` crate, `image` crate)。

### 6. 命名空间隔离
使用 `rust::stream` 命名空间避免与其他 Skia 类型冲突。

### 7. 文档化的生命周期约束
虽然无法在类型系统中强制,但注释明确说明调用者需保证 `SkStream` 的生命周期。

## 性能考量

### 1. FFI 调用开销
每次 `read()` 或 `seek()` 都跨越 FFI 边界,有一定开销:
- 函数调用约定切换(Rust ABI → C++ ABI)
- 寄存器保存/恢复
- 约 10-20 纳秒/调用(现代 CPU)

**缓解策略**: 使用较大的缓冲区批量读取,减少调用次数。

### 2. 无虚函数开销
尽管实现了 trait,但编译器可以静态分发(单态化),无虚函数调用开销。

### 3. 内联潜力
简短的 Rust trait 方法可能被内联,减少 Rust 侧的调用栈深度。

### 4. 零拷贝
`read()` 直接将数据读取到 Rust 提供的缓冲区,无中间拷贝。

### 5. Pin 开销
`Pin<&mut T>` 本质上是 `&mut T`,无额外运行时开销,只是编译期约束。

### 6. 错误处理开销
将 `bool` 转换为 `Result` 涉及构造 `Err` 对象(包含堆分配的错误消息),但只在失败路径发生。

## 相关文件

### 核心实现
- `rust/common/io_traits_ffi.rs`: 本文件(Rust trait 实现)
- `rust/common/SkStreamAdapter.h`: C++ 适配器声明
- `rust/common/SkStreamAdapter.cpp`: C++ 适配器实现
- `rust/common/SpanUtils.h`: Slice/Span 转换工具

### 标准库依赖
- `std::io::Read`: Rust 标准读取 trait
- `std::io::Seek`: Rust 标准寻址 trait
- `std::pin::Pin`: 不可移动对象包装

### 使用示例
- `rust/png/FFI.rs`: PNG 解码器使用 `SkStreamAdapter` 作为 `Read + Seek`
- `rust/icc/FFI.rs`: ICC 解析器(如果使用流式解析)

### CXX Bridge
- `third_party/rust/cxx/`: CXX bridge 库
- `rust/common/SkStreamAdapter.h.rs`: CXX 自动生成的 Rust 绑定(编译时)

### 测试文件
- `tests/RustPngCodecTest.cpp`: 间接测试 trait 实现(通过 PNG 解码)
- 未来可能的 `tests/rust/io_traits_test.rs`: 直接测试 trait 实现

### 构建文件
- `rust/common/BUILD.bazel` 或 `BUILD.gn`: 构建此 Rust 模块
- `Cargo.toml`: 声明 `cxx` 依赖
