# StringSlice - 轻量可变字符串类

> 源文件: `modules/skplaintexteditor/include/stringslice.h`

## 概述

`stringslice.h` 定义了 `SkPlainTextEditor::StringSlice` 类，这是一个为纯文本编辑器设计的轻量级可变字符串类。与 `std::string` 不同，`StringSlice` 不以 NUL 字符结尾，专为高效的文本插入和删除操作设计。它使用 C 风格的 `malloc`/`realloc`/`free` 进行内存管理，支持容量预分配和收缩，是编辑器中每行文本的底层存储。

## 架构位置

`StringSlice` 位于 `skplaintexteditor` 模块的基础工具层，是文本存储的核心组件。`Editor::TextLine` 中的每一行文本都以 `StringSlice` 形式存储。它向上为 `Editor` 提供文本操作接口，向下通过 `StringView` 提供只读访问视图。

## 主要类与结构体

### `StringSlice`
```cpp
class StringSlice {
    struct FreeWrapper { void operator()(void*); };
    std::unique_ptr<char[], FreeWrapper> fPtr;  // 数据指针（使用 free 释放）
    std::size_t fLength = 0;    // 当前长度
    std::size_t fCapacity = 0;  // 分配容量
};
```

- **不以 NUL 结尾**: 显式声明不提供 `c_str()` 方法
- **自定义释放**: 使用 `FreeWrapper` 包装 `std::free`，与 `std::unique_ptr` 配合使用
- **分离长度和容量**: 支持预分配空间减少重分配次数

## 公共 API 函数

### 构造与赋值

| 方法 | 说明 |
|------|------|
| `StringSlice()` | 默认构造空字符串 |
| `StringSlice(const char* s, std::size_t l)` | 从字符指针和长度构造 |
| `StringSlice(StringSlice&&)` | 移动构造 |
| `StringSlice(const StringSlice&)` | 拷贝构造 |
| `operator=(StringSlice&&)` | 移动赋值 |
| `operator=(const StringSlice&)` | 拷贝赋值 |

### 访问

| 方法 | 说明 |
|------|------|
| `const char* begin() const` | 返回数据起始指针 |
| `const char* end() const` | 返回数据结束指针 |
| `std::size_t size() const` | 返回字符串长度 |
| `StringView view() const` | 返回只读视图 |

### 修改

| 方法 | 说明 |
|------|------|
| `void insert(std::size_t offset, const char* text, std::size_t length)` | 在指定偏移处插入文本 |
| `void remove(std::size_t offset, std::size_t length)` | 从指定偏移处删除文本 |

### 容量管理

| 方法 | 说明 |
|------|------|
| `void reserve(std::size_t size)` | 预分配至少指定容量 |
| `void shrink()` | 收缩容量至当前长度 |

## 内部实现细节

### 内存管理策略
- 使用 `std::unique_ptr<char[], FreeWrapper>` 管理内存，`FreeWrapper` 调用 `std::free`
- 容量按 16 字节对齐（`kBits = 4`），减少频繁的小量重分配
- `realloc` 方法执行实际的内存重分配

### 构造函数实现
带参构造函数委托给 `insert`：
```cpp
StringSlice(const char* s, std::size_t l) { this->insert(0, s, l); }
```

### 移动语义
拷贝构造委托给带参构造函数，移动构造直接转移内部指针和大小。

## 依赖关系

- **直接依赖**: `stringview.h`（提供 `StringView` 类型）
- **标准库**: `<memory>`（`std::unique_ptr`）、`<cstddef>`（`std::size_t`）
- **被使用**: `editor.h` 中的 `TextLine::fText`
- **实现文件**: `stringslice.cpp`

## 设计模式与设计决策

- **非 NUL 终止**: 专为文本编辑优化，避免每次修改都需要维护 NUL 终止符
- **C 风格内存管理**: 使用 `malloc`/`realloc`/`free` 而非 `new`/`delete`，利用 `realloc` 的原地扩展能力，这在文本编辑场景中频繁的小量增长时效率更高
- **容量对齐**: 16 字节对齐分配减少了小型增长的重分配次数
- **视图分离**: 通过 `view()` 方法提供只读 `StringView`，遵循读写分离原则
- **值语义**: 支持完整的拷贝和移动语义，可以直接作为值类型在容器中使用

## 性能考量

- **`realloc` 原地扩展**: 使用 `realloc` 而非 `new`+`memcpy`，可能在原地扩展缓冲区，减少数据拷贝
- **16 字节对齐**: 容量按 16 字节对齐，减少小量增长时的重分配频率
- **`memmove` 操作**: `insert` 和 `remove` 使用 `memmove` 移动数据，对于大文本行可能较慢，但对于典型的文本编辑行长度（<200 字节）是高效的
- **预分配支持**: `reserve()` 允许提前分配空间，减少多次插入时的重分配

## 相关文件

- `modules/skplaintexteditor/src/stringslice.cpp` — 完整实现
- `modules/skplaintexteditor/include/stringview.h` — 只读视图定义
- `modules/skplaintexteditor/include/editor.h` — 使用 StringSlice 的编辑器
