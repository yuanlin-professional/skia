# tools/sksl-minify - SkSL 着色器最小化工具

## 概述

`tools/sksl-minify` 目录包含了 SkSL（Skia Shading Language）着色器源代码最小化（minify）工具。该工具负责将 SkSL 模块源代码压缩为最小化版本，去除不必要的空白、注释和冗余字符，以减小最终二进制文件中嵌入的着色器代码体积。

`sksl-minify` 在 Skia 的构建流程中扮演着重要角色。Skia 内置了多个 SkSL 模块文件（如 `sksl_shared.sksl`、`sksl_public.sksl` 等），这些模块在编译时被嵌入到 Skia 库中。通过最小化处理，可以显著减少这些内嵌着色器的存储开销。

该工具的工作流程分为两个阶段。首先，它使用 SkSL 编译器将输入文件编译为模块（Module），并执行优化（包括私有函数的符号重命名）。然后，它使用 SkSL 词法分析器（Lexer）对优化后的代码进行最小化处理：去除所有注释和多余空白，仅在语法需要时（如相邻标识符或歧义运算符之间）保留空格。浮点字面量也会被简化（如 `3.0` 变为 `3.`，`0.5` 变为 `.5`）。

`sksl-minify` 支持多种程序类型（通过命令行标志指定）：片段着色器（`--frag`）、顶点着色器（`--vert`）、计算着色器（`--compute`）、运行时着色器（`--shader`）、颜色过滤器（`--colorfilter`）、混合器（`--blender`）以及网格着色器（`--meshfrag`/`--meshvert`）。默认类型为运行时着色器。

该工具还支持 `--stringify` 选项，将输出格式化为 C++ 字符串字面量（`static constexpr char SKSL_MINIFIED_xxx[] = "...";`），便于直接嵌入到 C++ 源代码中。

## 目录结构

```
tools/sksl-minify/
├── BUILD.bazel          # Bazel 构建配置
└── SkSLMinify.cpp       # 最小化工具主程序
```

## 关键类与函数

### main 函数
- 解析命令行参数，确定输入/输出路径和程序类型
- 两种调用模式：
  - 单文件: `sksl-minify <output> <input> [flags] [dependencies...]`
  - 工作列表: `sksl-minify <worklist>`

### process_command 函数
- 解析命令行标志（`--frag`、`--vert`、`--compute` 等）
- 编译输入模块链（从右到左继承父模块符号）
- 执行优化和符号重命名
- 调用 `generate_minified_text()` 生成最小化输出

### compile_module_list 函数
- **功能**: 编译模块依赖链
- **处理流程**:
  1. 对于运行时效果，自动包含 `sksl_public.sksl` 和 `sksl_shared.sksl`
  2. 从右到左加载模块，每个模块继承父模块的符号表
  3. 对每个模块执行优化和符号缩短
- **符号重命名**: 全局作用域的私有函数被重命名为短符号（`$a`、`$b` 等），确保嵌套模块间无名称冲突

### generate_minified_text 函数
- **功能**: 将优化后的 SkSL 代码转换为最小化文本
- **处理规则**:
  - 去除所有注释（行注释和块注释）和空白
  - 相邻字母数字字符之间插入最小空格
  - 相邻 `+`/`-` 运算符之间插入空格（避免歧义）
  - 简化浮点字面量（`3.0` -> `3.`，`0.5` -> `.5`）
  - `--stringify` 模式下在第 75 列左右换行

### 命令行标志
- `--frag` / `--vert` / `--compute` - 指定着色器程序类型
- `--shader` / `--privshader` - 运行时着色器
- `--colorfilter` / `--blender` - 运行时效果类型
- `--meshfrag` / `--meshvert` - 网格着色器
- `--stringify` - 输出为 C++ 字符串字面量格式
- `--unoptimized` - 跳过符号重命名优化

## 依赖关系

- **编译器核心**: `src/sksl/SkSLCompiler.h`（SkSL 编译器）
- **词法分析**: `src/sksl/SkSLLexer.h`（SkSL 词法分析器）
- **模块系统**: `src/sksl/SkSLModule.h`、`src/sksl/SkSLModuleLoader.h`
- **变换层**: `src/sksl/transform/SkSLTransform.h`（优化和符号重命名）
- **共享工具**: `tools/skslc/ProcessWorklist.h`（工作列表处理）
- **路径工具**: `src/utils/SkOSPath.h`、`src/utils/SkGetExecutablePath.h`
- **构建集成**: 在 Skia 构建过程中自动调用以最小化内置 SkSL 模块

## 使用示例

```bash
# 最小化一个运行时着色器
sksl-minify output.minified input.sksl --shader

# 最小化并生成 C++ 字符串字面量
sksl-minify output.h input.sksl --shader --stringify

# 最小化片段着色器（带依赖模块）
sksl-minify output.minified input.sksl --frag dep1.sksl dep2.sksl

# 使用工作列表批量处理
sksl-minify worklist.txt
```

## 最小化效果示例

原始代码：
```glsl
// This is a simple shader
uniform float scale;  // scale factor

float helper(float x) {
    return x * scale;
}

half4 main(float2 coords) {
    return half4(helper(coords.x), 0.0, 0.0, 1.0);
}
```

最小化后：
```
uniform float scale;float $a(float x){return x*scale;}half4 main(float2 coords){return half4($a(coords.x),0.,0.,1.);}
```

关键变化：
- 注释被完全移除
- 多余空白被消除
- 私有函数 `helper` 被重命名为 `$a`
- 浮点字面量 `0.0` 被简化为 `0.`
- 浮点字面量 `1.0` 被简化为 `1.`

## 模块依赖链处理

`sksl-minify` 的一个重要特性是正确处理模块依赖链。SkSL 模块系统允许模块继承父模块的符号，这意味着最小化过程中的符号重命名必须考虑跨模块的名称冲突。

工具从右到左编译模块链，每个模块继承前一个模块的符号表。符号重命名（`$a`、`$b`、`$c`...）在全局作用域中进行，确保嵌套模块间不会产生重复的短符号名。

## 相关文档与参考

- `tools/skslc/` - SkSL 编译器工具（共享 ProcessWorklist）
- `src/sksl/SkSLCompiler.h` - SkSL 编译器核心
- `src/sksl/SkSLLexer.h` - SkSL 词法分析器
- `src/sksl/SkSLModule.h` - SkSL 模块系统
- `src/sksl/` 目录下的 `.sksl` 文件 - 内置 SkSL 模块源代码
- `tools/sksltrace/` - SkSL 调试追踪工具
