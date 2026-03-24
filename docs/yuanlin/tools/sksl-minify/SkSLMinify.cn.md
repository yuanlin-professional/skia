# SkSLMinify.cpp

> 源文件: tools/sksl-minify/SkSLMinify.cpp

## 概述

`SkSLMinify.cpp` 是 Skia 的 SkSL（Skia Shading Language）代码压缩工具的主程序。该工具用于将 SkSL 源代码文件压缩和优化，移除注释、多余空格和换行符，生成紧凑的代码输出。它可以选择性地将输出字符串化（stringify）为 C++ 字符串常量，方便嵌入到编译后的二进制文件中。

该工具的主要功能包括：
- 编译和优化 SkSL 模块
- 移除注释和不必要的空白字符
- 压缩浮点字面量（如 3.0 → 3.，0.5 → .5）
- 智能插入必要的空格以保持语法正确性
- 支持多种程序类型（fragment、vertex、runtime shader 等）
- 支持模块依赖链的递归编译和优化
- 可选的代码字符串化功能，用于嵌入式部署

## 架构位置

在 Skia 的构建和工具链中的位置：

```
tools/
  ├── skslc/                      # SkSL 编译器主程序
  │   ├── Main.cpp               # skslc 编译器入口
  │   └── ProcessWorklist.h      # 批处理工作列表
  ├── sksl-minify/
  │   └── SkSLMinify.cpp        # SkSL 压缩工具（本文件）
  └── ...

src/sksl/                         # SkSL 编译器核心
  ├── SkSLCompiler.h             # 编译器接口
  ├── SkSLLexer.h                # 词法分析器
  ├── SkSLModule.h               # 模块系统
  └── ...
```

典型使用场景：
```
SkSL 源文件 → sksl-minify → 压缩后的 SkSL → 嵌入到 Skia 库中
```

## 主要类与结构体

本文件没有定义类，主要由全局函数和模块化的辅助函数组成。

### 全局变量

```cpp
static bool gUnoptimized = false;
static bool gStringify = false;
static SkSL::ProgramKind gProgramKind = SkSL::ProgramKind::kFragment;
```

**说明**：
- `gUnoptimized`：是否禁用优化（保留原始符号名称）
- `gStringify`：是否将输出包装为 C++ 字符串常量
- `gProgramKind`：当前编译的程序类型（默认为 fragment shader）

## 公共 API 函数

### main

```cpp
int main(int argc, const char** argv)
```

**功能**：程序入口点，处理命令行参数并启动压缩流程。

**执行流程**：
1. 检查参数数量，如果是工作列表则使用 `ProcessWorklist`
2. 否则调用 `process_command` 处理单个文件

### process_command

```cpp
static ResultCode process_command(SkSpan<std::string> args)
```

**功能**：处理单个压缩命令，是工具的核心逻辑。

**参数**：
- `args`：命令行参数数组

**返回值**：
- `ResultCode::kSuccess`：成功
- `ResultCode::kInputError`：输入错误
- `ResultCode::kOutputError`：输出错误

**处理流程**：
1. 解析命令行标志（--unoptimized、--stringify、程序类型等）
2. 验证至少有输出路径和一个输入路径
3. 调用 `compile_module_list` 编译所有输入模块
4. 生成程序文本并调用 `generate_minified_text` 压缩
5. 写入输出文件

### compile_module_list

```cpp
static std::forward_list<std::unique_ptr<const SkSL::Module>> compile_module_list(
        SkSpan<const std::string> paths, SkSL::ProgramKind kind)
```

**功能**：编译一系列 SkSL 模块，构建依赖链。

**参数**：
- `paths`：输入文件路径列表
- `kind`：程序类型

**返回值**：编译后的模块链表（从右到左的依赖顺序）

**特殊处理**：
- 对于 Runtime Effect 类型，自动包含 sksl_shared 和 sksl_public 模块
- 从右到左编译模块，每个模块继承前一个模块的符号表
- 对每个模块执行优化和符号重命名

### generate_minified_text

```cpp
static bool generate_minified_text(std::string_view inputPath,
                                   std::string_view text,
                                   SkSL::FileOutputStream& out)
```

**功能**：使用词法分析器压缩 SkSL 代码。

**参数**：
- `inputPath`：输入文件路径（用于错误报告）
- `text`：要压缩的代码文本
- `out`：输出流

**返回值**：成功返回 true，失败返回 false

**压缩策略**：
1. **移除注释和空白**：跳过 TK_LINE_COMMENT、TK_BLOCK_COMMENT、TK_WHITESPACE
2. **浮点字面量优化**：
   - `3.0` → `3.`
   - `0.5` → `.5`
3. **智能空格插入**：
   - 相邻标识符之间插入空格（避免 `intx` 这样的错误）
   - 相邻的 +/- 符号之间插入空格（区分 `x++` 和 `x + +y`）
4. **行宽控制**：在 stringify 模式下，超过 75 字符时换行

## 内部实现细节

### 命令行参数处理

```cpp
gUnoptimized = find_boolean_flag(&args, "--unoptimized");
gStringify = find_boolean_flag(&args, "--stringify");
bool isFrag = find_boolean_flag(&args, "--frag");
// ... 更多标志
```

使用 `find_boolean_flag` 从参数列表中提取布尔标志，同时从列表中移除已处理的参数。

### 程序类型映射

```cpp
if (isFrag) {
    gProgramKind = SkSL::ProgramKind::kFragment;
} else if (isVert) {
    gProgramKind = SkSL::ProgramKind::kVertex;
} else if (isColorFilter) {
    gProgramKind = SkSL::ProgramKind::kRuntimeColorFilter;
}
// ... 更多类型
```

支持的程序类型：
- Fragment、Vertex、Compute（传统着色器）
- RuntimeShader、RuntimeColorFilter、RuntimeBlender（运行时效果）
- MeshFragment、MeshVertex（网格着色器）

### 词法分析循环

```cpp
SkSL::Lexer lexer;
lexer.start(text);

SkSL::Token token;
std::string_view lastTokenText = " ";
int lineWidth = 1;
for (;;) {
    token = lexer.next();
    if (token.fKind == TokenKind::TK_END_OF_FILE) {
        break;
    }
    // 跳过注释和空白
    // 压缩浮点字面量
    // 智能插入空格
    // 写入输出
}
```

### 浮点字面量压缩

```cpp
if (token.fKind == TokenKind::TK_FLOAT_LITERAL) {
    if (skstd::contains(thisTokenText, '.')) {
        while (thisTokenText.back() == '0' && thisTokenText.size() >= 3) {
            thisTokenText.remove_suffix(1);  // 移除尾部 0
        }
    }
    if (skstd::starts_with(thisTokenText, "0.") && thisTokenText.size() >= 3) {
        thisTokenText.remove_prefix(1);  // 移除前导 0
    }
}
```

### 空格插入逻辑

```cpp
bool adjacentIdentifiers =
        maybe_identifier(lastTokenText.back()) && maybe_identifier(thisTokenText.front());

bool adjacentPlusOrMinus =
        is_plus_or_minus(lastTokenText.back()) && is_plus_or_minus(thisTokenText.front());

if (adjacentIdentifiers || adjacentPlusOrMinus) {
    out.writeText(" ");
    lineWidth++;
}
```

### 字符串化输出

```cpp
if (gStringify) {
    out.printf("static constexpr char SKSL_MINIFIED_%s[] =\n\"", baseName.c_str());
}

// ... 压缩代码 ...

if (gStringify) {
    out.writeText("\";");
}
```

### Mesh 着色器特殊处理

```cpp
if ((isMeshFrag || isMeshVert) && element->is<SkSL::StructDefinition>()) {
    std::string_view name = element->as<SkSL::StructDefinition>().type().name();
    if (name == "Attributes" || name == "Varyings") {
        continue;  // 跳过这些结构体，由 SkMeshSpecification 合成
    }
}
```

## 依赖关系

**SkSL 编译器核心**：
- `src/sksl/SkSLCompiler.h`：编译器接口
- `src/sksl/SkSLLexer.h`：词法分析器
- `src/sksl/SkSLModule.h`、`SkSLModuleLoader.h`：模块系统
- `src/sksl/SkSLProgramKind.h`、`SkSLProgramSettings.h`：程序配置
- `src/sksl/ir/SkSLStructDefinition.h`、`SkSLSymbolTable.h`：IR 表示
- `src/sksl/transform/SkSLTransform.h`：代码转换

**工具基础设施**：
- `tools/skslc/ProcessWorklist.h`：批处理工作列表
- `src/sksl/SkSLFileOutputStream.h`：文件输出流
- `src/utils/SkGetExecutablePath.h`、`SkOSPath.h`：路径工具

**标准库**：
- `<cctype>`：字符分类
- `<forward_list>`：单向链表
- `<fstream>`：文件流
- `<stdio.h>`、`<stdarg.h>`：C 标准 I/O

## 设计模式与设计决策

### 两阶段处理

1. **编译阶段**：使用完整的 SkSL 编译器编译和优化代码
2. **压缩阶段**：使用词法分析器移除多余字符

**理由**：确保语义正确性，同时最大化压缩效果

### 模块链式依赖

```cpp
std::forward_list<std::unique_ptr<const SkSL::Module>> modules;
```

使用单向链表存储模块依赖链：
- 支持递归的模块继承
- 从右到左编译（依赖在前，使用者在后）
- 自动管理内存

### 智能空格保留

不是简单删除所有空格，而是：
- 分析相邻 token 的语法性质
- 仅在必要时插入空格
- 避免产生语法错误

### 可配置的输出模式

- **普通模式**：输出压缩的 SkSL 源码
- **Stringify 模式**：输出 C++ 字符串常量
- **Unoptimized 模式**：保留原始符号名称（用于调试）

### 批处理支持

通过 `ProcessWorklist` 支持处理多个文件：
```cpp
if (argc == 2) {
    return (int)ProcessWorklist(argv[1], process_command);
}
```

## 性能考量

### 词法分析效率

使用单遍词法分析而非完整解析：
- 时间复杂度：O(n)，n 为字符数
- 避免构建完整的 AST（编译阶段已完成）

### 浮点字面量压缩

```cpp
while (thisTokenText.back() == '0' && thisTokenText.size() >= 3) {
    thisTokenText.remove_suffix(1);
}
```

简单的字符串操作，时间复杂度 O(k)，k 为尾部 0 的数量（通常很小）

### 行宽控制开销

```cpp
if (gStringify && lineWidth > 75) {
    out.writeText("\"\n\"");
    lineWidth = 1;
}
```

仅在 stringify 模式下启用，增加少量开销但改善可读性

### 模块优化

```cpp
compiler.optimizeModuleBeforeMinifying(kind, *m, /*shrinkSymbols=*/!gUnoptimized);
```

对每个模块执行优化，包括：
- 死代码消除
- 符号重命名（缩短名称）
- 常量折叠

这些优化比词法压缩更有效，但时间复杂度更高（编译时可接受）

## 相关文件

**工具程序**：
- `tools/skslc/Main.cpp`：完整的 SkSL 编译器
- `tools/skslc/ProcessWorklist.h`：批处理框架

**核心库**：
- `src/sksl/SkSLCompiler.cpp`：编译器实现
- `src/sksl/SkSLLexer.cpp`：词法分析器实现
- `src/sksl/SkSLModule.cpp`：模块系统实现

**构建系统**：
- `BUILD.gn`：GN 构建配置，定义 sksl-minify 可执行文件

**使用示例**：
```bash
# 压缩 fragment shader
sksl-minify output.sksl input.sksl --frag

# 压缩为 C++ 字符串
sksl-minify output.cpp input.sksl --shader --stringify

# 压缩 runtime shader（自动包含依赖）
sksl-minify output.sksl my_shader.sksl --shader

# 批处理模式
sksl-minify worklist.txt
```

该工具是 Skia 构建流程的重要组成部分，用于减小着色器代码的体积，优化运行时加载性能。
