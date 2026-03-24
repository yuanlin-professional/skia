# SkShaderUtils - 着色器工具函数

> 源文件:
> - `src/utils/SkShaderUtils.h`
> - `src/utils/SkShaderUtils.cpp`

## 概述

SkShaderUtils 是 Skia 中用于 GPU 着色器代码处理的工具命名空间。它提供了一组实用函数，主要用于着色器源代码的格式化美化 (Pretty Print)、逐行访问与打印、SPIR-V 二进制转十六进制字符串、着色器编译错误消息构建以及着色器横幅打印。这些工具在调试和错误报告场景中尤为重要。

## 架构位置

```
Skia GPU 后端
├── SkSL 编译器
│   └── 着色器代码生成
│       └── SkShaderUtils (本模块 - 着色器调试与格式化工具)
│           ├── GLSL 代码美化
│           ├── SPIR-V 二进制转储
│           └── 错误消息生成
├── Ganesh / Graphite (GPU 渲染后端)
└── 调试输出 (SkDebugf)
```

## 主要类与结构体

### `GLSLPrettyPrint` (内部类)
- 位于 `.cpp` 文件中的私有类，实现 GLSL 着色器代码的美化格式化。
- **核心算法**: 基于字符扫描的状态机，处理括号 `{}`、圆括号 `()`、分号 `;`、注释 `//` 和 `/* */`、预处理指令 `#` 等语法元素。
- **格式化规则**:
  - `{` 和 `}` 总是独占一行，并调整缩进层级。
  - `;` 触发换行（但在 `for` 语句的圆括号内不换行）。
  - 注释和预处理指令保持在同一行内，直到遇到换行符。
  - 忽略原始输入中的 `\t` 和 `\n`，使用自身的缩进和换行策略。
- **成员变量**: `fTabs` (缩进层级)、`fFreshline` (新行标记)、`fIndex/fLength` (扫描位置)、`fInput` (输入字符串)、`fPretty` (输出字符串)。

## 公共 API 函数

### `PrettyPrint`
```cpp
std::string PrettyPrint(const std::string& string);
```
- **功能**: 美化格式化 GLSL 着色器代码。
- **参数**: 原始着色器代码字符串。
- **返回值**: 格式化后的着色器代码。
- **实现**: 创建 `GLSLPrettyPrint` 对象并调用 `prettify()`。

### `VisitLineByLine`
```cpp
void VisitLineByLine(const std::string& text,
                     const std::function<void(int lineNumber, const char* lineText)>&);
```
- **功能**: 将文本按行拆分，并对每一行调用回调函数，行号从 1 开始。
- **实现**: 使用 `SkStrSplit` 按 `\n` 拆分，以严格模式保留空行。

### `PrintLineByLine`
```cpp
inline void PrintLineByLine(const std::string& text);
```
- **功能**: 逐行打印着色器代码（包含行号）。
- **用途**: 在 adb 日志中避免长字符串被截断。
- **实现**: 调用 `VisitLineByLine` 配合 `SkDebugf` 输出。

### `SpirvAsHexStream`
```cpp
std::string SpirvAsHexStream(SkSpan<const uint32_t> spirv);
```
- **功能**: 将 SPIR-V 二进制数据转换为十六进制字符串流。
- **输出格式**: 每行 10 个 32 位值，格式为 `0xXXXXXXXX,`。
- **用途**: 输出可粘贴到 SPIR-V 可视化工具或传递给 `spirv-dis` 的文本。

### `BuildShaderErrorMessage`
```cpp
std::string BuildShaderErrorMessage(const char* shader, const char* errors);
```
- **功能**: 将原始着色器代码和编译错误信息组合成可读的错误消息。
- **输出格式**: 包含"Shader compilation error"标题、带行号的着色器代码和"Errors:"部分。

### `PrintShaderBanner`
```cpp
void PrintShaderBanner(SkSL::ProgramKind programKind);
```
- **功能**: 根据着色器类型打印调试横幅 (例如 "---- Vertex shader ----")。
- **支持类型**: Vertex、Fragment，其他类型显示为 "Unknown"。

## 内部实现细节

### GLSL 美化算法
美化器使用单遍扫描的状态机实现：
1. 维护两个解析状态：`fInParseUntilNewline`（解析到行尾）和 `fInParseUntil`（解析到指定 token）。
2. 优先检查解析状态恢复，然后检查 `#`、`//`、`/*` 等标记。
3. 使用 `parensDepth` 计数器跟踪圆括号嵌套深度，避免在 `for` 循环内部错误换行。
4. `undoNewlineAfter()` 方法处理 `}` 后紧跟 `;` 或 `,` 的情况，确保它们出现在同一行。

### SPIR-V 转换
使用 `std::ostringstream` 和 `std::setw`/`std::setfill`/`std::hex` 进行格式化，每行限制 10 个 32 位字以保持可读性。

## 依赖关系

- `include/core/SkSpan.h`: SPIR-V 数据的 span 视图。
- `include/core/SkString.h`: Skia 字符串类。
- `src/core/SkStringUtils.h`: 字符串拆分函数 (`SkStrSplit`)。
- `src/sksl/SkSLProgramSettings.h`: SkSL 程序类型定义 (`ProgramKind`, `ProgramConfig`)。
- `src/sksl/SkSLString.h`: SkSL 字符串格式化函数 (`String::appendf`)。
- `include/private/base/SkDebug.h`: 调试输出 (`SkDebugf`)。
- `include/private/base/SkTArray.h`: 用于行拆分的动态数组。

## 设计模式与设计决策

1. **命名空间封装**: 所有函数封装在 `SkShaderUtils` 命名空间中，避免全局命名污染。

2. **回调模式**: `VisitLineByLine` 使用 `std::function` 回调，提供灵活的逐行处理接口，`PrintLineByLine` 是其便捷封装。

3. **内部类隐藏**: `GLSLPrettyPrint` 类完全隐藏在 `.cpp` 文件中，只通过 `PrettyPrint()` 函数暴露功能。

4. **adb 日志适配**: `PrintLineByLine` 的设计动机是避免 Android 的 adb 日志对长字符串的截断，通过逐行输出规避此限制。

## 性能考量

1. **单遍扫描**: GLSL 美化器在单次扫描中完成所有格式化操作，时间复杂度为 O(n)。

2. **字符串拼接**: 美化器使用 `std::string` 的 `+=` 操作符逐字符/逐 token 追加，在大型着色器上可能产生频繁的内存重分配。对于调试场景，这一开销是可接受的。

3. **仅限调试使用**: 这些工具函数主要用于调试和错误报告，不在性能关键路径上。

## 相关文件

- `src/sksl/SkSLProgramSettings.h`: SkSL 着色器类型定义。
- `src/sksl/SkSLString.h`: SkSL 字符串工具。
- `src/gpu/ganesh/GrGLGpu.cpp`: Ganesh GL 后端中使用这些工具函数的一个典型消费者。
- `src/core/SkStringUtils.h`: 字符串拆分工具。
