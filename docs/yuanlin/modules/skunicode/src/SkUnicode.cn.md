# SkUnicode.cpp

> 源文件: `modules/skunicode/src/SkUnicode.cpp`

## 概述

`SkUnicode.cpp` 是 SkUnicode 模块的基类实现文件，提供了 `SkUnicode` 接口中与具体后端无关的通用工具方法。主要包含 UTF-8 与 UTF-16 之间的编码转换函数，以及用于查询 Unicode 代码单元属性标志（如制表符、换行、字位簇起始等）的静态辅助函数。这些方法被所有 SkUnicode 后端实现共享使用。

## 架构位置

该文件位于 `modules/skunicode/src/` 目录下，是 SkUnicode 模块的核心实现之一。在架构层次上，它实现了 `SkUnicode` 基类中的非虚函数，这些函数与具体的 Unicode 后端（ICU、Bidi 等）无关，为上层的文本处理流程（如 Skottie 文本排版、SkParagraph 段落布局）提供基础的编码转换和字符属性查询能力。

## 主要类与结构体

该文件不定义新的类或结构体，而是实现 `SkUnicode` 基类中已声明的成员函数。

## 公共 API 函数

### UTF 编码转换函数

#### `SkUnicode::convertUtf16ToUtf8(const char16_t*, int)`
```cpp
SkString SkUnicode::convertUtf16ToUtf8(const char16_t* utf16Char, int utf16Units);
```
- **功能**: 将 UTF-16 编码的字符串转换为 UTF-8 编码的 `SkString`。
- **实现**: 首先调用 `SkUTF::UTF16ToUTF8` 计算输出所需字节数，然后分配缓冲区并执行转换。若输入无效则输出调试消息并返回空字符串。

#### `SkUnicode::convertUtf16ToUtf8(const std::u16string&)`
```cpp
SkString SkUnicode::convertUtf16ToUtf8(const std::u16string& utf16);
```
- **功能**: 重载版本，接受 `std::u16string` 参数，内部委托给指针版本。

#### `SkUnicode::convertUtf8ToUtf16(const char*, int)`
```cpp
std::u16string SkUnicode::convertUtf8ToUtf16(const char* utf8, int utf8Units);
```
- **功能**: 将 UTF-8 编码的字符串转换为 UTF-16 编码的 `std::u16string`。
- **实现**: 两阶段转换策略，先计算长度再执行转换。

#### `SkUnicode::convertUtf8ToUtf16(const SkString&)`
```cpp
std::u16string SkUnicode::convertUtf8ToUtf16(const SkString& utf8);
```
- **功能**: 重载版本，接受 `SkString` 参数。

### 代码单元标志查询函数

#### `hasTabulationFlag(CodeUnitFlags)`
- 检查标志是否包含制表符（kTabulation）标记。

#### `hasHardLineBreakFlag(CodeUnitFlags)`
- 检查标志是否包含硬换行（kHardLineBreakBefore）标记。

#### `hasSoftLineBreakFlag(CodeUnitFlags)`
- 检查标志是否包含软换行（kSoftLineBreakBefore）标记。

#### `hasGraphemeStartFlag(CodeUnitFlags)`
- 检查标志是否包含字位簇起始（kGraphemeStart）标记。

#### `hasControlFlag(CodeUnitFlags)`
- 检查标志是否包含控制字符（kControl）标记。

#### `hasPartOfWhiteSpaceBreakFlag(CodeUnitFlags)`
- 检查标志是否包含空白断行（kPartOfWhiteSpaceBreak）标记。

## 内部实现细节

- **两阶段编码转换**: 所有编码转换函数均采用两阶段策略：第一阶段以 `nullptr` 输出缓冲区调用 `SkUTF` 工具函数，仅计算所需输出长度；第二阶段分配精确大小的缓冲区并执行实际转换。这种方式避免了预估缓冲区大小的复杂性。
- **位掩码标志查询**: 标志查询函数使用位与运算（`&`）配合全值比较来检测特定标志位，这依赖于 `SkBitmaskEnum.h` 提供的枚举位掩码支持。
- **调试断言**: 在 DEBUG 模式下，使用 `SkASSERT` 验证转换后的实际长度与预计算长度一致，确保编码转换的正确性。

## 依赖关系

- **`include/private/base/SkDebug.h`**: 提供 `SkDEBUGF` 调试输出宏。
- **`modules/skunicode/include/SkUnicode.h`**: 基类接口声明。
- **`src/base/SkBitmaskEnum.h`**: 枚举位掩码运算支持，使 `CodeUnitFlags` 可以使用位运算。
- **`src/base/SkUTF.h`**（隐式依赖）: 提供 `SkUTF::UTF16ToUTF8` 和 `SkUTF::UTF8ToUTF16` 底层转换函数。

## 设计模式与设计决策

- **模板方法模式的辅助**: 该文件中的方法为所有 SkUnicode 后端提供公共实现，体现了"基类实现通用逻辑，子类实现差异逻辑"的设计思想。
- **防御性编程**: 编码转换函数在输入无效时优雅地返回空结果而非崩溃，并在调试模式下输出诊断信息。
- **静态工具函数风格**: 标志查询函数虽然是成员函数，但仅依赖输入参数不依赖对象状态，本质上是静态工具函数。

## 性能考量

- **两阶段转换的权衡**: 两阶段策略虽然需要遍历输入两次，但避免了缓冲区浪费和重新分配，在大多数场景下性能表现良好。
- **内联友好**: 标志查询函数体非常短小（单行位运算），编译器很可能将其内联优化。
- **UTF 转换频率**: 在文本排版流程中，UTF 编码转换通常在文本输入阶段一次性完成，不会成为热路径。

## 相关文件

- `modules/skunicode/include/SkUnicode.h` -- 基类接口声明
- `modules/skunicode/include/SkUnicode_icu.h` -- ICU 后端工厂
- `modules/skunicode/src/SkUnicode_bidi.cpp` -- Bidi 后端实现
- `src/base/SkUTF.h` -- UTF 编码转换底层工具
- `src/base/SkBitmaskEnum.h` -- 枚举位掩码运算支持
