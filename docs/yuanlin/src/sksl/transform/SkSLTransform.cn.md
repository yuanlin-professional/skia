# SkSL Transform (IR 变换工具)

> 源文件:
> - `src/sksl/transform/SkSLTransform.h`
> - `src/sksl/transform/SkSLTransform.cpp`

## 概述

`SkSL::Transform` 命名空间提供了一组 IR 变换函数，用于在 SkSL 编译的不同阶段对程序或模块进行优化和规范化。这些变换包括死代码消除、常量替换、符号重命名、不可达代码消除、空语句清理、以及 switch 语句的变量声明提升等。该头文件是这些分散实现的变换函数的统一声明点。

注意：`SkSLTransform.cpp` 文件实际上是空的（仅为 IWYU 处理存在），各个变换的实际实现分布在 `src/sksl/transform/` 目录下的独立文件中。

## 架构位置

Transform 函数位于 SkSL 编译器的优化和后处理阶段，在 IR 构建完成后、代码生成之前执行。

```
Parser -> IR 构建 -> Transform (优化/规范化) -> CodeGen
                       |
                       |-- EliminateDeadFunctions
                       |-- EliminateDeadLocalVariables
                       |-- EliminateDeadGlobalVariables
                       |-- EliminateUnreachableCode
                       |-- ReplaceConstVarsWithLiterals
                       |-- RenamePrivateSymbols
                       |-- ...
```

## 主要类与结构体

本模块不定义任何类，所有功能通过 `Transform` 命名空间中的自由函数提供。

## 公共 API 函数

### 修饰符增强

- **`AddConstToVarModifiers(var, initialValue, usage)`** -- 检查变量是否可以安全添加 `const` 修饰符。如果变量从未被写入（初始赋值除外），则返回添加了 `const` 的修饰符。这允许内联器折叠更多值。

### 表达式重写

- **`RewriteIndexedSwizzle(context, swizzle)`** -- 将 `myVec.zyx[i]` 形式的索引 swizzle 重写为 `myVec[vec3(2,1,0)[i]]`。这与 glslang 的处理方式一致。

### 内建元素声明

- **`FindAndDeclareBuiltinFunctions(program)`** -- 根据 `ProgramUsage` 将模块中使用的内建函数复制到程序中。
- **`FindAndDeclareBuiltinStructs(program)`** -- 复制使用到的内建结构体定义。
- **`FindAndDeclareBuiltinVariables(program)`** -- 扫描并声明 `sk_FragColor` 等内建变量。

### 死代码消除

- **`EliminateUnreachableCode(module/program, usage)`** -- 消除不可达语句（如 `return` 后的代码）。
- **`EliminateEmptyStatements(module)`** -- 消除空语句（Nop 和仅含 Nop 的块），仅用于模块。
- **`EliminateUnnecessaryBraces(context, module)`** -- 消除不必要的花括号（单语句块），仅用于模块。
- **`EliminateDeadFunctions(context, module/program, usage)`** -- 消除未被调用的函数。返回是否有变更。
- **`EliminateDeadLocalVariables(context, module/program, usage)`** -- 消除未使用的局部变量，保留初始化器的副作用。
- **`EliminateDeadGlobalVariables(context, module/program, usage, onlyPrivateGlobals)`** -- 消除未使用的全局变量。

### 代码压缩

- **`RenamePrivateSymbols(context, module, usage, kind)`** -- 将私有函数和局部变量重命名为短名称，减小生成代码体积。
- **`ReplaceConstVarsWithLiterals(module, usage)`** -- 将常量变量替换为其字面值。
- **`ReplaceSplatCastsWithSwizzles(context, module)`** -- 将 `float4(myFloat)` 替换为 `myFloat.xxxx`，更紧凑的文本表示。

### Switch 语句处理

- **`HoistSwitchVarDeclarationsAtTopLevel(context, cases, symbolTable, pos)`** -- 将 switch-case 顶层的变量声明提升到外部作用域。解决了 fallthrough 时变量作用域的正确性问题和不支持原生 switch 的后端的代码生成困难。返回包含提升声明的 Block，如果无需提升则返回 nullptr。

## 内部实现细节

### Module vs Program

大部分变换函数提供了 `Module` 和 `Program` 两个重载版本：
- **Module 版本** -- 用于模块的长期优化，更积极（如消除空语句和不必要花括号）
- **Program 版本** -- 用于用户程序的优化，较保守

### Switch 变量提升

`HoistSwitchVarDeclarationsAtTopLevel` 的详细行为：
1. 扫描 case 语句的顶层（非嵌套块）查找变量声明
2. 将声明移到返回的 Block 中
3. 有初始值的声明被替换为赋值语句
4. 无初始值的声明被替换为 Nop
5. 嵌套块中的声明不受影响

## 依赖关系

**内部依赖：**
- `SkSLDefines` -- 基础定义
- `SkSLModifierFlags` -- 修饰符标志
- `SkSLContext` -- 编译器上下文
- `SkSLExpression` / `SkSLBlock` -- IR 节点
- `SkSLProgramUsage` -- 程序使用分析
- `SkSLSymbolTable` -- 符号表
- `SkSLVariable` -- 变量
- `SkSLIndexExpression` -- 索引表达式

**外部依赖：**
- `<memory>`, `<cstdint>` -- 标准库

## 设计模式与设计决策

1. **函数级变换**：每个变换是独立的函数，可以按需组合。不同编译路径（模块编译 vs 程序编译）使用不同的变换组合。

2. **头文件声明/分散实现**：所有变换在同一头文件中声明，但实现分布在不同的 `.cpp` 文件中。这允许增量编译，修改一个变换不会重编其他变换。

3. **Module 优先优化**：空语句消除和花括号简化只对 Module 实施，因为它们对用户程序无害但会增加模块的长期内存占用。

4. **返回值指示变更**：死代码消除函数返回 `bool` 指示是否做了修改，允许调用者决定是否需要重新分析。

## 性能考量

- **ProgramUsage 驱动**：变换依赖预计算的 `ProgramUsage` 信息来确定哪些函数/变量是活跃的，避免重复遍历。
- **增量消除**：死代码消除可能需要多轮运行（消除一个函数可能使另一个函数变为无用），调用者通过返回值循环运行。
- **符号重命名压缩**：`RenamePrivateSymbols` 使用短名称替换长名称，对 GLSL/WGSL 等文本格式的着色器有显著的大小压缩效果。

## 相关文件

- `src/sksl/transform/SkSLProgramWriter.h` -- 程序遍历器（变换的实现工具）
- `src/sksl/analysis/SkSLProgramUsage.h` -- 程序使用分析
- `src/sksl/SkSLCompiler.h` -- 编译器（变换的调用者）
- `src/sksl/ir/SkSLBlock.h` -- Block 节点（变量提升的输出）
- `src/sksl/ir/SkSLSwitchStatement.h` -- switch 语句（使用 HoistSwitchVarDeclarations）
