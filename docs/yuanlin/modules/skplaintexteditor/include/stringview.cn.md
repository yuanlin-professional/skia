# StringView - 轻量只读字符串视图

> 源文件: `modules/skplaintexteditor/include/stringview.h`

## 概述

`stringview.h` 定义了 `SkPlainTextEditor` 命名空间中的 `Span<T>` 模板结构体及其类型别名 `StringView`。这是一个极简的非拥有型数据视图，仅包含一个指针和一个大小值，用于在不进行内存复制的情况下引用字符串数据。该文件仅 19 行，是 `skplaintexteditor` 模块中最小的头文件。

`StringView` 的设计早于 C++17 中 `std::string_view` 的广泛采用（文件版权标记为 2019 年），它提供了一个更简洁的替代方案，刻意省略了 NUL 终止相关的 API，与模块中 `StringSlice` 的非 NUL 终止设计保持一致。

## 架构位置

`StringView` 位于 `skplaintexteditor` 模块的最底层工具层，是所有文本数据只读传递的基础类型。在模块的数据流中：

```
StringSlice (拥有型存储)
    |
    v  .view()
StringView (非拥有型视图)
    |
    v  解引用
Editor::Text::Iterator -> 外部代码
```

它被 `StringSlice::view()` 方法返回，被 `Editor::Text::Iterator` 的解引用操作符生成，是模块向外部代码暴露只读文本引用的标准方式。在编辑器应用中，遍历文本行时使用 `StringView` 避免了不必要的字符串复制。

## 主要类与结构体

### `Span<T>` 模板结构体
```cpp
template <typename T>
struct Span {
    T* data;
    std::size_t size;
};
```

一个泛型的非拥有型数据视图，设计特点：
- **POD 类型**: 无构造函数、无析构函数、无虚方法
- **泛型设计**: 模板参数 `T` 允许用于任意元素类型
- **聚合初始化**: 支持 `Span<const char>{ptr, len}` 形式的初始化
- **公有成员**: 直接访问 `data` 和 `size`，无封装开销

### `StringView` 类型别名
```cpp
using StringView = Span<const char>;
```

`Span<const char>` 的特化别名，表示不可变字符数据的视图。`const` 修饰确保通过此视图不能修改底层数据。

## 公共 API 函数

`StringView` 是一个纯数据结构体（POD-like），没有方法定义。所有访问通过直接访问成员完成：

| 成员 | 类型 | 说明 |
|------|------|------|
| `data` | `const char*` | 字符数据起始指针（可能为 `nullptr`） |
| `size` | `std::size_t` | 数据长度（字节数，不含 NUL 终止符） |

### 使用示例（来自 editor.h）
```cpp
// 遍历编辑器的所有文本行
for (SkPlainTextEditor::StringView str : editor.text()) {
    std::cout.write(str.data, str.size) << '\n';
}
```

### 空视图表示
空或无效的视图表示为 `{nullptr, 0}`，如 `Editor::line()` 在索引越界时返回此值。

## 内部实现细节

- **无任何方法实现**: 完全依赖结构体的聚合语义
- **不以 NUL 结尾**: 与 `StringSlice` 的设计一致，使用 `data` + `size` 定义范围
- **不进行任何内存管理**: 使用方需确保 `data` 指向的内存在 `StringView` 使用期间有效
- **不检查空指针**: 不进行防御性空指针检查，遵循"调用方负责"原则
- **`Span<T>` 模板设计**: 虽然当前仅用作 `StringView`，但模板设计允许将来复用于其他类型（如 `Span<const uint8_t>` 表示二进制数据视图）
- **头文件保护**: 使用 `#ifndef stringview_DEFINED` 传统头文件保护宏

## 依赖关系

- **直接依赖**: `<cstddef>` — 提供 `std::size_t` 类型定义
- **被依赖**:
  - `modules/skplaintexteditor/include/stringslice.h` — `StringSlice::view()` 返回 `StringView`
  - `modules/skplaintexteditor/include/editor.h` — `Editor::Text::Iterator` 生成 `StringView`，`Editor::line()` 返回 `StringView`
  - `modules/skplaintexteditor/app/editor_application.cpp` — 通过 `StringView` 访问文本行进行输出和保存

## 设计模式与设计决策

- **零开销抽象**: 纯 POD 结构体，无虚函数表、无构造/析构开销。与裸指针+大小的手动管理在机器级别完全等价，但提供了类型安全性和语义清晰性
- **泛型 Span 模式**: 使用模板 `Span<T>` 而非直接定义 `StringView` 结构体，遵循 DRY 原则，并为将来的泛型使用留出扩展空间
- **非拥有语义**: 明确不管理内存生命周期，遵循 C++ 中"视图不拥有数据"的惯例（如 `std::string_view`、`SkSpan`）
- **与 `std::string_view` 的对比**:
  - `std::string_view` 提供丰富的方法（`find`、`substr` 等），而 `StringView` 是纯数据
  - `std::string_view` 在 C++17 中标准化，而此文件编写于 2019 年早期
  - `StringView` 的 POD 设计使其可以安全地用于 C ABI 边界
- **最小 API 表面**: 刻意不提供 `begin()`/`end()` 等迭代器方法，保持接口极简

## 性能考量

- **完全零开销**: POD 结构体在所有主流编译器上会被优化为两个寄存器传递（指针 + 大小），无论是按值传递还是按引用传递，性能等价
- **无内存分配**: 不涉及任何堆分配或引用计数
- **无复制**: 创建 `StringView` 仅复制指针和大小值（16 字节在 64 位平台），不复制实际字符数据
- **可安全地按值传递**: 大小仅为两个机器字，按值传递的开销与按引用传递相当
- **缓存友好**: 数据成员紧凑排列，访问时不会造成缓存行浪费

## 相关文件

- `modules/skplaintexteditor/include/stringslice.h` — 拥有型字符串类，通过 `view()` 方法产生 `StringView`
- `modules/skplaintexteditor/include/editor.h` — 使用 `StringView` 作为文本行只读访问类型
- `modules/skplaintexteditor/app/editor_application.cpp` — 通过 `StringView` 遍历、打印和保存文本
- `include/core/SkSpan.h` — Skia 核心的 `SkSpan<T>` 类型，类似的非拥有型视图设计
