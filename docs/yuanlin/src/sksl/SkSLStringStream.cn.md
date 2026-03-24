# SkSLStringStream — 基于字符串的输出流

> 源文件：[`src/sksl/SkSLStringStream.h`](../../src/sksl/SkSLStringStream.h)

## 概述

SkSLStringStream.h 定义了 `StringStream` 类，它是 SkSL 编译器输出流系统中基于内存字符串的实现。该类将 SkSL 编译器的输出收集到内存中的字符串缓冲区，底层使用 Skia 的 `SkDynamicMemoryWStream`。这是 SkSL 代码生成中最常用的输出流实现，用于将生成的着色器代码收集为字符串。

该文件 58 行，是一个完全内联实现的头文件。

## 架构位置

```
SkSL 输出流体系
  └── OutputStream (基类, src/sksl/SkSLOutputStream.h)
        ├── FileOutputStream (文件输出)
        └── StringStream (字符串输出, 本文件)
              └── SkDynamicMemoryWStream (底层内存流)
```

`StringStream` 是 SkSL 代码生成器的主要输出目标。几乎所有后端（GLSL、SPIR-V、Metal、WGSL）都使用 `StringStream` 收集生成的代码。

## 主要类与结构体

### `StringStream`

```cpp
class StringStream : public OutputStream {
public:
    void write8(uint8_t b) override;
    void writeText(const char* s) override;
    void write(const void* s, size_t size) override;
    size_t bytesWritten() const;
    const std::string& str() const;
    void reset();
private:
    mutable SkDynamicMemoryWStream fStream;
    mutable std::string fString;
};
```

## 公共 API 函数

```cpp
void write8(uint8_t b) override;
void writeText(const char* s) override;
void write(const void* s, size_t size) override;
```
- 写入方法，委托给底层 `SkDynamicMemoryWStream`
- 每个方法都有 `SkASSERT(fString.empty())` 断言，确保在调用 `str()` 后不再写入

```cpp
size_t bytesWritten() const;
```
- 返回已写入的总字节数

```cpp
const std::string& str() const;
```
- 返回累积的全部输出内容作为 `std::string` 引用
- 惰性转换：首次调用时从 `SkDynamicMemoryWStream` 提取数据并缓存到 `fString`
- 后续调用直接返回缓存的字符串

```cpp
void reset();
```
- 重置流状态，清空所有已写入的数据和缓存的字符串

## 内部实现细节

### 双缓冲机制

`StringStream` 使用两个 `mutable` 成员维护双缓冲：

1. `fStream`（`SkDynamicMemoryWStream`）：写入阶段使用的高效内存流
2. `fString`（`std::string`）：读取阶段缓存的字符串

写入操作直接进入 `fStream`。当调用 `str()` 时，数据从 `fStream` 通过 `detachAsData()` 转移到 `fString`。这两个阶段是互斥的：一旦调用 `str()` 就不应再写入（通过断言保护）。

### `mutable` 关键字

两个成员都声明为 `mutable`，使得 `str()` 可以是 `const` 方法。这是因为 `str()` 在语义上是只读操作（获取输出内容），即使它在实现上需要修改内部状态（惰性转换）。

### 惰性字符串转换

```cpp
const std::string& str() const {
    if (!fString.size()) {
        sk_sp<SkData> data = fStream.detachAsData();
        fString = std::string((const char*) data->data(), data->size());
    }
    return fString;
}
```

仅在首次调用 `str()` 时执行转换。注意 `detachAsData()` 会消耗 `fStream` 的内容。

## 依赖关系

- `include/core/SkData.h` — `sk_sp<SkData>` 用于数据中转
- `include/core/SkStream.h` — `SkDynamicMemoryWStream` 底层内存流
- `src/sksl/SkSLOutputStream.h` — 输出流基类

## 设计模式与设计决策

- **适配器模式**：将 Skia 的 `SkDynamicMemoryWStream` 适配为 SkSL 的 `OutputStream` 接口。
- **惰性求值**：字符串转换延迟到首次访问时，避免在不需要字符串结果时的多余拷贝。
- **两阶段使用模型**：先写入、后读取的使用模式通过断言强制执行，简化了实现。

## 性能考量

1. **SkDynamicMemoryWStream 的高效写入**：底层使用链表式内存块，避免频繁重新分配。
2. **零拷贝中转**：`detachAsData()` 通常可以避免数据拷贝（取决于 `SkDynamicMemoryWStream` 的实现）。
3. **字符串缓存**：`str()` 的结果被缓存，多次调用不会重复转换。
4. **完全内联**：所有方法在头文件中实现，编译器可以内联优化。

## 相关文件

- `src/sksl/SkSLOutputStream.h` — 输出流基类定义
- `src/sksl/SkSLFileOutputStream.h` — 文件输出流（另一个 OutputStream 实现）
- `include/core/SkStream.h` — Skia 流类体系
- `src/sksl/codegen/` — 各代码生成器（使用 StringStream 收集输出）
