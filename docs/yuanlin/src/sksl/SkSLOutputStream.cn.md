# SkSL::OutputStream - SkSL 输出流

> 源文件: `src/sksl/SkSLOutputStream.h`, `src/sksl/SkSLOutputStream.cpp`

## 概述

`SkSL::OutputStream` 是 SkSL 编译器中用于代码生成的抽象输出流基类。它提供了写入原始字节、文本和格式化字符串的接口，被 SkSL 的各种代码生成后端（GLSL、Metal、SPIR-V 等）用于输出生成的着色器代码。

## 架构位置

```
SkSL::OutputStream (抽象基类)
  ├── SkSL::StringStream (写入 std::string)
  ├── SkSL::FileOutputStream (写入文件)
  └── 其他具体实现
```

该类是 SkSL 代码生成管线的基础 I/O 抽象层。

## 主要类与结构体

### `OutputStream`
- 纯虚基类
- 提供字节级、文本级和格式化输出能力
- 使用 1024 字节的内部缓冲区处理 printf 格式化

## 公共 API 函数

### 字节级写入
- `virtual void write8(uint8_t b) = 0`: 写入单个字节（纯虚）
- `void write16(uint16_t i)`: 小端序写入 16 位整数
- `void write32(uint32_t i)`: 小端序写入 32 位整数
- `virtual void write(const void* s, size_t size) = 0`: 写入任意字节块（纯虚）

### 文本写入
- `virtual void writeText(const char* s) = 0`: 写入 C 字符串（纯虚）
- `void writeString(const std::string& s)`: 写入 std::string

### 格式化输出
- `void printf(const char format[], ...)`: printf 风格的格式化输出
- `void appendVAList(const char format[], va_list args)`: va_list 版本的格式化输出

### 状态
- `virtual bool isValid() const`: 检查流是否有效（默认返回 true）

## 内部实现细节

### 格式化实现
`appendVAList` 使用两阶段策略：
1. 首先尝试使用 1024 字节的栈缓冲区格式化
2. 如果长度超过缓冲区，动态分配 `char[]` 并重新格式化

```cpp
void OutputStream::appendVAList(const char format[], va_list args) {
    char buffer[kBufferSize];
    va_list copy;
    va_copy(copy, args);
    int length = vsnprintf(buffer, kBufferSize, format, args);
    if (length > (int) kBufferSize) {
        std::unique_ptr<char[]> bigBuffer(new char[length + 1]);
        vsnprintf(bigBuffer.get(), length + 1, format, copy);
        this->write(bigBuffer.get(), length);
    } else {
        this->write(buffer, length);
    }
    va_end(copy);
}
```

### 小端序写入
`write16` 和 `write32` 按小端字节序逐字节写入，用于 SPIR-V 等二进制格式。

## 依赖关系

- `SkTypes.h`: `SK_PRINTF_LIKE` 宏（编译时格式字符串检查）
- 标准库: `<cstdarg>`, `<cstdio>`, `<string>`

## 设计模式与设计决策

### 抽象工厂
作为抽象基类，允许不同的后端选择合适的输出目标（字符串、文件等）。

### 栈缓冲区优先
格式化输出优先使用栈缓冲区（1024 字节），仅在必要时进行堆分配，优化了常见的短格式化字符串场景。

### 小端序二进制输出
`write16`/`write32` 的小端序设计匹配 SPIR-V 的字节序要求。

## 性能考量

- 1024 字节的栈缓冲区覆盖绝大多数格式化输出场景
- `va_copy` 确保 `va_list` 可以安全地使用两次
- `writeString` 直接调用 `write`，避免额外的遍历

## 相关文件

- `src/sksl/SkSLStringStream.h`: 基于 std::string 的具体实现
- `src/sksl/codegen/SkSLGLSLCodeGenerator.h`: GLSL 代码生成器（使用 OutputStream）
- `src/sksl/codegen/SkSLMetalCodeGenerator.h`: Metal 代码生成器
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.h`: SPIR-V 代码生成器
