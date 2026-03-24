# StringSlice 实现 - 轻量可变字符串操作

> 源文件: `modules/skplaintexteditor/src/stringslice.cpp`

## 概述

`stringslice.cpp` 提供了 `SkPlainTextEditor::StringSlice` 类的完整实现，包括移动语义、赋值操作、文本插入/删除以及内存重分配。该实现使用 C 标准库的 `malloc`/`realloc`/`free` 进行内存管理，容量按 16 字节边界对齐分配，为文本编辑场景中频繁的小量修改提供高效支持。

## 架构位置

该文件是 `StringSlice` 头文件的实现文件，位于 `skplaintexteditor` 模块的基础实现层。所有非内联的成员函数都在此文件中定义。它是编辑器文本存储的底层引擎，每次文本编辑操作（输入、删除）最终都会通过此文件的 `insert`/`remove` 方法执行。

## 主要类与结构体

### `StringSlice::FreeWrapper`
```cpp
void StringSlice::FreeWrapper::operator()(void* t) { std::free(t); }
```
自定义删除器，使 `std::unique_ptr` 能与 `malloc` 分配的内存配合使用。

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `StringSlice(StringSlice&&)` | 移动构造，转移所有权 |
| `StringSlice& operator=(StringSlice&&)` | 移动赋值，使用 placement new |
| `StringSlice& operator=(const StringSlice&)` | 拷贝赋值，重用已有缓冲区 |
| `void insert(std::size_t, const char*, std::size_t)` | 在指定偏移处插入文本 |
| `void remove(std::size_t, std::size_t)` | 从指定偏移处删除文本 |

## 内部实现细节

### 移动构造函数
```cpp
StringSlice::StringSlice(StringSlice&& that)
    : fPtr(std::move(that.fPtr))
    , fLength(that.fLength)
    , fCapacity(that.fCapacity) {
    that.fLength = 0;
    that.fCapacity = 0;
}
```
转移指针所有权后，将源对象的长度和容量清零。

### 移动赋值
```cpp
StringSlice& StringSlice::operator=(StringSlice&& that) {
    if (this != &that) {
        this->~StringSlice();
        new (this)StringSlice(std::move(that));  // placement new
    }
    return *this;
}
```
使用析构+placement new 模式实现移动赋值，确保正确释放旧数据。

### 拷贝赋值
```cpp
StringSlice& StringSlice::operator=(const StringSlice& that) {
    if (this != &that) {
        fLength = 0;  // 清空但保留缓冲区
        if (that.size() > 0) {
            this->insert(0, that.begin(), that.size());
        }
    }
    return *this;
}
```
重置长度为 0 但保留已分配的缓冲区，然后通过 `insert` 复制数据。这避免了在容量足够时的重新分配。

### 插入操作
```cpp
void StringSlice::insert(std::size_t offset, const char* text, std::size_t length) {
    if (length) {
        offset = std::min(fLength, offset);    // 防止越界
        this->reserve(fLength + length);       // 确保容量
        char* s = fPtr.get();
        if (offset != fLength) {
            std::memmove(s + offset + length, s + offset, fLength - offset);  // 移位
        }
        if (text) {
            std::memcpy(s + offset, text, length);  // 复制新数据
        } else {
            std::memset(s + offset, 0, length);     // text 为 null 时填零
        }
        fLength += length;
    }
}
```

关键点：
- `offset` 被钳制到 `[0, fLength]`，防止越界
- 使用 `memmove`（非 `memcpy`）处理重叠区域
- `text` 为 `nullptr` 时填充零字节（用于预分配空间）

### 删除操作
```cpp
void StringSlice::remove(std::size_t offset, std::size_t length) {
    if (length && offset < fLength) {
        length = std::min(length, fLength - offset);  // 防止越界
        if (length + offset < fLength) {
            std::memmove(s + offset, s + offset + length, fLength - (length + offset));
        }
        fLength -= length;
    }
}
```
通过 `memmove` 将后续数据前移覆盖被删除区域，仅修改 `fLength` 而不缩减容量。

### 内存重分配
```cpp
void StringSlice::realloc(std::size_t size) {
    static constexpr unsigned kBits = 4;
    fCapacity = size ? (((size - 1) >> kBits) + 1) << kBits : 0;
    fPtr.reset((char*)std::realloc(fPtr.release(), fCapacity));
}
```
容量计算公式：`capacity = ceil(size / 16) * 16`，确保 16 字节对齐。使用 `fPtr.release()` 暂时释放 `unique_ptr` 所有权传给 `realloc`，再通过 `reset` 重新接管。

## 依赖关系

- **直接依赖**: `stringslice.h`（类声明）
- **标准库**: `<cstdlib>`（`malloc`/`realloc`/`free`）、`<cstring>`（`memmove`/`memcpy`/`memset`）、`<algorithm>`（`std::min`）、`<cassert>`

## 设计模式与设计决策

- **C 内存管理**: 选择 `malloc`/`realloc`/`free` 而非 `new`/`delete`，核心原因是利用 `realloc` 的原地扩展能力
- **Placement New 移动赋值**: 使用析构+placement new 而非逐字段赋值，这是一种简洁但需注意自赋值的实现方式
- **惰性收缩**: `remove` 不自动收缩缓冲区，需要显式调用 `shrink()` 来释放多余内存
- **防御性编程**: `insert` 和 `remove` 都对偏移量和长度进行边界钳制，防止越界
- **16 字节对齐**: 选择 16 字节作为对齐粒度是在分配开销和空间浪费之间的平衡

## 性能考量

- **`realloc` 优势**: 当堆管理器有足够的连续空间时，`realloc` 可以原地扩展而不需要数据拷贝，这对于频繁的小量增长（如逐字符输入）非常有利
- **16 字节对齐分配**: 减少了小量增长时的重分配频率。例如，插入 1 个字节到 15 字节的字符串不会触发重分配
- **删除不收缩**: `remove` 后保留已分配空间，避免了 "删除后立即插入" 场景下的反复分配
- **`memmove` 使用**: 保证了重叠内存区域操作的正确性，虽然比 `memcpy` 略慢，但在文本编辑的典型行长度（<200 字节）下差异可忽略
- **断言验证**: 使用 `assert` 进行不变量检查，在 release 构建中零开销

## 相关文件

- `modules/skplaintexteditor/include/stringslice.h` — 类声明
- `modules/skplaintexteditor/include/stringview.h` — 只读视图
- `modules/skplaintexteditor/src/editor.cpp` — 使用 `StringSlice` 的编辑器实现
