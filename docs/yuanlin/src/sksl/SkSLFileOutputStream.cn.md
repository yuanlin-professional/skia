# SkSLFileOutputStream — 基于文件的输出流

> 源文件：[`src/sksl/SkSLFileOutputStream.h`](../../src/sksl/SkSLFileOutputStream.h)

## 概述

SkSLFileOutputStream.h 定义了 `FileOutputStream` 类，它是 SkSL 编译器输出流系统中基于文件的实现。该类将 SkSL 编译器的输出（如生成的着色器代码）写入文件系统中的文件。它继承自 `OutputStream` 基类，使用标准 C 文件 I/O（`FILE*`）进行底层操作。

该文件 78 行，是一个完全内联实现的头文件。

## 架构位置

```
SkSL 输出流体系
  └── OutputStream (基类, src/sksl/SkSLOutputStream.h)
        ├── FileOutputStream (文件输出, 本文件)
        └── StringStream (字符串输出, src/sksl/SkSLStringStream.h)
```

`FileOutputStream` 在 SkSL 工具链中主要用于将编译后的着色器代码输出到文件，常用于离线编译工具和调试场景。

## 主要类与结构体

### `FileOutputStream`

```cpp
class FileOutputStream : public OutputStream {
public:
    FileOutputStream(const char* name);
    ~FileOutputStream() override;
    bool isValid() const override;
    void write8(uint8_t b) override;
    void writeText(const char* s) override;
    void write(const void* s, size_t size) override;
    bool close();
private:
    bool fOpen = true;
    FILE* fFile;
};
```

成员变量：
- `fOpen`：标记文件是否处于打开状态，初始为 `true`
- `fFile`：标准 C 文件指针

## 公共 API 函数

```cpp
FileOutputStream(const char* name);
```
- 构造函数，以二进制写模式（`"wb"`）打开指定路径的文件
- 如果打开失败，`fFile` 为 `nullptr`

```cpp
~FileOutputStream();
```
- 析构函数，如果文件仍处于打开状态则自动关闭

```cpp
bool isValid() const override;
```
- 返回文件是否有效（`fFile` 非空）
- 写入错误后会将 `fFile` 设为 `nullptr`，后续调用 `isValid()` 返回 `false`

```cpp
void write8(uint8_t b) override;
```
- 写入单个字节，使用 `fputc`

```cpp
void writeText(const char* s) override;
```
- 写入以 null 结尾的字符串，使用 `fputs`

```cpp
void write(const void* s, size_t size) override;
```
- 写入指定大小的二进制数据，使用 `fwrite`

```cpp
bool close();
```
- 关闭文件，设置 `fOpen` 为 `false`
- 返回是否成功关闭

## 内部实现细节

### 错误处理策略

所有写入方法采用"标记无效"的错误处理策略：当写入操作失败时（`fputc`/`fputs` 返回 EOF，或 `fwrite` 返回的字节数不等于请求大小），将 `fFile` 设置为 `nullptr`。这导致：

1. `isValid()` 返回 `false`
2. 后续的写入操作被静默跳过（每个方法都先检查 `isValid()`）
3. 调用者可以在最终检查 `isValid()` 来确认是否所有写入都成功

这种设计避免了在每次写入时检查返回值的繁琐模式。

### RAII 式生命周期管理

析构函数检查 `fOpen` 标志，如果文件未被显式关闭则自动关闭，确保不会泄漏文件描述符。`close()` 方法设置 `fOpen = false` 以防止析构函数重复关闭。

### 断言保护

`write8` 和 `writeText` 方法包含 `SkASSERT(fOpen)` 断言，在 Debug 构建中检测对已关闭流的写入操作。

## 依赖关系

- `src/sksl/SkSLOutputStream.h` — 输出流基类
- `src/sksl/SkSLUtil.h` — SkSL 工具函数（提供 `SkASSERT`）
- `<stdio.h>` — 标准 C 文件 I/O

## 设计模式与设计决策

- **模板方法模式**：通过继承 `OutputStream` 基类并重写虚方法，实现文件特定的输出行为。
- **二进制模式**：使用 `"wb"` 模式打开文件，确保跨平台一致的行为（避免 Windows 上的行尾转换）。
- **延迟错误报告**：不在每次写入时抛出或返回错误，而是通过 `isValid()` 标志实现延迟检查。

## 性能考量

1. **每次写入一次系统调用**：每次 `write8`、`writeText`、`write` 调用都直接调用 C 标准库函数。对于大量小写入，标准库的缓冲机制（`FILE*` 自带缓冲）减少了实际的系统调用次数。
2. **完全内联实现**：所有方法都在头文件中实现，编译器可以内联优化。

## 相关文件

- `src/sksl/SkSLOutputStream.h` — 输出流基类定义
- `src/sksl/SkSLStringStream.h` — 字符串输出流（另一个 OutputStream 实现）
- `src/sksl/codegen/` — 代码生成器目录（使用 OutputStream 输出代码）
