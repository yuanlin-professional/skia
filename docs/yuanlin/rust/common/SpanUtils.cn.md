# SpanUtils

> 源文件: rust/common/SpanUtils.h

## 概述

`SpanUtils.h` 是 Skia 中用于在 Rust 的 `rust::Slice` 和 C++ 的 `SkSpan` 之间进行类型转换的轻量级工具头文件。该文件提供了单一的模板函数 `ToSkSpan()`,用于将 CXX bridge 生成的 Rust slice 类型安全地转换为 Skia 的 span 类型,同时处理空 slice 的边界情况以避免未定义行为。

该工具是 Rust-C++ 互操作层的基础设施,被所有需要在 FFI 边界传递数组数据的 Skia Rust 组件使用,如流适配器、编解码器和图像处理模块。

## 架构位置

```
skia/
├── include/core/
│   └── SkSpan.h                    # Skia span 类型定义
├── rust/common/
│   ├── SpanUtils.h                 # 本文件
│   ├── SkStreamAdapter.h           # 使用 ToSkSpan
│   └── io_traits_ffi.rs            # Rust 侧 slice 来源
├── rust/
│   ├── png/FFI.cpp                 # 使用 ToSkSpan 的 PNG 模块
│   └── icc/FFI.cpp                 # 使用 ToSkSpan 的 ICC 模块
└── third_party/rust/cxx/           # CXX bridge (提供 rust::Slice)
```

该文件位于 `rust/common/` 目录,作为所有 Rust FFI 组件的共享基础工具。

## 主要类与结构体

### 模板函数

**`template <typename T> SkSpan<T> ToSkSpan(rust::Slice<T> slice)`**
- **输入**: `rust::Slice<T>` - CXX bridge 生成的 Rust slice 包装类型
- **输出**: `SkSpan<T>` - Skia 的 span 类型(非拥有的数组视图)
- **类型参数**: `T` - 元素类型(通常为 `uint8_t`, `const uint8_t`, `uint16_t` 等)

### 外部类型声明

**`namespace rust::cxxbridge1::Slice<T>`**
- CXX bridge 自动生成的类型
- 表示 Rust 的 `&[T]` 或 `&mut [T]` slice
- 方法: `.data()` 返回指针, `.size()` 返回长度, `.empty()` 检查是否为空

## 公共 API 函数

### `ToSkSpan<T>(rust::Slice<T> slice)`

**功能**: 将 Rust slice 转换为 Skia span

**实现**:
```cpp
template <typename T> SkSpan<T> ToSkSpan(rust::Slice<T> slice) {
    if (slice.empty()) {
        return SkSpan<T>();
    }
    return SkSpan<T>(slice.data(), slice.size());
}
```

**边界情况处理**:
- **空 slice**: 返回默认构造的空 `SkSpan<T>()`,避免调用 `.data()` 可能触发的未定义行为
- **非空 slice**: 直接使用 `.data()` 和 `.size()` 构造 span

**使用示例**:
```cpp
size_t read(rust::Slice<uint8_t> buffer) {
    SkSpan<uint8_t> span = ToSkSpan(buffer);
    return fStream->read(span.data(), span.size());
}
```

## 内部实现细节

### 空 Slice 的未定义行为问题

根据注释中引用的文章 [Empty Slices](https://davidben.net/2024/01/15/empty-slices.html),在某些平台和编译器配置下,对空 slice 调用 `.data()` 可能导致未定义行为,因为:

1. Rust 的空 slice 可能使用 `NonNull::dangling()` 指针
2. C++ 标准对空容器的 `.data()` 行为未明确定义
3. 某些优化可能假设指针非空并进行错误的优化

通过先检查 `.empty()`,代码避免了这些潜在问题。

### 类型推导和模板实例化

`ToSkSpan` 是泛型模板,编译器根据调用点的类型参数自动实例化:
- `ToSkSpan(rust::Slice<uint8_t>)` → `SkSpan<uint8_t>`
- `ToSkSpan(rust::Slice<const uint8_t>)` → `SkSpan<const uint8_t>`
- `ToSkSpan(rust::Slice<uint16_t>)` → `SkSpan<uint16_t>`

每个实例化版本都是零成本的内联函数。

### SkSpan 构造

`SkSpan<T>` 支持多种构造方式:
- **默认构造**: `SkSpan()` - 创建空 span (指针为 nullptr, 长度为 0)
- **指针+长度构造**: `SkSpan(T* ptr, size_t len)` - 从原始指针和长度创建

`ToSkSpan` 根据 slice 是否为空选择合适的构造方式。

### 内存布局兼容性

`rust::Slice<T>` 和 `SkSpan<T>` 在内存布局上高度相似:
- 都是 `{pointer, length}` 的薄包装
- 都不拥有数据,只是视图
- 转换是零拷贝的

但由于 C++ 和 Rust 的 ABI 差异,不能直接 `reinterpret_cast`,需要通过构造函数转换。

## 依赖关系

### 外部依赖
- **SkSpan.h**: 定义 `SkSpan<T>` 类型
- **CXX bridge**: 提供 `rust::Slice<T>` 类型(通过注释中的前向声明避免直接包含)

### 内部依赖
无,这是最底层的工具函数。

### 依赖方向
```
上层 Rust FFI 模块 (SkStreamAdapter, PNG FFI, ICC FFI)
    ↓
SpanUtils.h (ToSkSpan 函数)
    ↓
SkSpan.h (Skia) + rust::Slice<T> (CXX bridge)
```

## 设计模式与设计决策

### 1. 单一职责原则
整个文件只负责一个任务:类型转换。没有其他逻辑混入,保持高内聚。

### 2. 泛型编程
使用模板支持任意类型的 slice/span 转换,避免为每种类型编写重复代码。

### 3. 防御性编程
显式处理空 slice 边界情况,避免依赖未定义行为。

### 4. 最小化依赖
通过前向声明 `rust::Slice<T>` 避免包含 CXX 头文件,减少编译依赖。

### 5. 内联友好
简短的函数体适合编译器内联,转换在优化后可能完全消失。

### 6. 类型安全
模板参数确保 slice 和 span 的元素类型匹配,编译期捕获类型错误。

### 7. 文档化的 UB 规避
通过注释链接外部文章,明确说明为何需要特殊处理空 slice,便于未来维护者理解。

## 性能考量

### 1. 零成本抽象
转换操作在优化后通常被完全内联,编译为零指令开销:
```cpp
// 源代码
SkSpan<uint8_t> span = ToSkSpan(buffer);

// 优化后(伪代码)
T* ptr = buffer.empty() ? nullptr : buffer.data();
size_t len = buffer.empty() ? 0 : buffer.size();
// span 就是 {ptr, len},可能直接作为寄存器传递
```

### 2. 分支预测
空 slice 检查是高度可预测的分支(大多数情况下 slice 非空),现代 CPU 的分支预测器能有效处理。

### 3. 编译期优化
如果编译器能证明 slice 非空(如通过常量传播),条件检查会被优化掉。

### 4. 无额外内存分配
转换是纯栈操作,不涉及堆分配。

### 5. 缓存友好
Slice 和 Span 的大小通常只有 16 字节(64 位系统),可以在寄存器中传递。

## 相关文件

### 核心依赖
- `include/core/SkSpan.h`: SkSpan 类型定义和实现
- `third_party/rust/cxx/v1/cxx.h`: rust::Slice 类型定义(CXX bridge 生成)

### 使用者
- `rust/common/SkStreamAdapter.cpp`: 在 `read()` 方法中使用
- `rust/png/FFI.cpp`: PNG 解码器的缓冲区转换
- `rust/icc/FFI.cpp`: ICC 解析器的数据传递
- 所有其他 Rust FFI 模块

### 相关工具
- `rust/common/io_traits_ffi.rs`: Rust 侧提供 slice 的源头
- `include/private/base/SkSpan_impl.h`: SkSpan 的详细实现

### 参考文档
- [Empty Slices and Undefined Behavior](https://davidben.net/2024/01/15/empty-slices.html): 解释空 slice 的 UB 风险

### 测试文件
- `tests/SkSpanTest.cpp`: SkSpan 的单元测试
- `tests/RustPngCodecTest.cpp`: 间接测试 ToSkSpan(通过 PNG 解码器)

### 构建文件
- `rust/common/BUILD.bazel` 或 `BUILD.gn`: 包含此头文件的构建规则
