# SkSL GLSL 代码生成器 (SkSLGLSLCodeGenerator)

> 源文件:
> - `src/sksl/codegen/SkSLGLSLCodeGenerator.h`
> - `src/sksl/codegen/SkSLGLSLCodeGenerator.cpp`

## 概述

GLSL 代码生成器负责将 SkSL 编译器的中间表示（IR）程序转换为 GLSL（OpenGL Shading Language）代码。这是 Skia 在 OpenGL 后端上运行的核心组件。该模块处理 SkSL 到 GLSL 的类型映射、精度限定符、驱动程序 Bug 的变通方案（workaround）、内建函数重写等功能。源文件超过 2100 行，包含了针对各种 GPU 驱动问题的大量补丁逻辑。

## 架构位置

GLSL 代码生成器位于 SkSL 编译器的代码生成层，继承自 `CodeGenerator` 基类。

```
SkSL Program (IR)
  |
  |-- ToGLSL() [入口函数]
  |     |-- GLSLCodeGenerator::generateCode()
  |           |-- writeHeader() (版本声明和扩展)
  |           |-- writeProgramElement() (逐元素生成)
  |           |-- 输出 extensions + globals + main body
```

## 主要类与结构体

### `GLSLCodeGenerator`

`final` 类，继承自 `CodeGenerator`，在 `.cpp` 文件中定义。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fExtensions` | `StringStream` | GLSL 扩展声明缓冲区 |
| `fGlobals` | `StringStream` | 全局声明缓冲区 |
| `fExtraFunctions` | `StringStream` | 额外辅助函数缓冲区 |
| `fFunctionHeader` | `string` | 当前函数的局部变量声明头 |
| `fIndentation` | `int` | 当前缩进级别 |
| `fPrettyPrint` | `PrettyPrint` | 是否格式化输出 |
| `fCurrentFunction` | `FunctionDeclaration*` | 当前正在生成的函数 |
| `fFoundDerivatives` | `bool` | 是否使用了 dFdx/dFdy |
| 各种 `fWritten*` 标志 | `bool` | 已生成的 polyfill 函数追踪 |

## 公共 API 函数

### 入口函数（头文件导出）

- **`ToGLSL(program, caps, out, prettyPrint)`** -- 完整版 GLSL 生成。
- **`ToGLSL(program, caps, out)`** -- 简化版。
- **`ToGLSL(program, caps, nativeShader)`** -- 输出到 NativeShader 结构。

## 内部实现细节

### 代码生成流程

`generateCode()` 按以下顺序执行：
1. `writeHeader()` -- 输出 GLSL 版本声明（如 `#version 310 es`）和默认精度
2. 遍历所有 ProgramElement 并输出到主体
3. 将 extensions + globals + extraFunctions + body 合并输出

### 输出缓冲区组织

生成器使用四个独立的缓冲区：
- `fExtensions` -- `#extension` 声明（如 `#extension GL_OES_standard_derivatives : enable`）
- `fGlobals` -- 全局变量声明
- `fExtraFunctions` -- 辅助多态填充函数
- 主输出流 -- 函数定义和其他元素

这种分离确保了 GLSL 规范要求的声明顺序。

### 类型名称映射

`getTypeName()` 将 SkSL 类型映射到 GLSL 类型名：
- `half` -> `float`（GLSL 无 half）
- `short` -> `int`, `ushort` -> `uint`
- 向量：根据组件类型选择 `vec`/`ivec`/`uvec`/`bvec` + 列数
- 矩阵：`mat` + 列数 + (`x` + 行数) 当非方阵时
- 数组：`type[size]` 格式

### 标识符安全处理

`writeIdentifier()` 处理 GLSL 标识符限制：
- GLSL 禁止连续两个下划线（`__`）
- 包含 `__` 或 `_X` 的标识符中每个 `_` 被替换为 `_X`
- GLSL 保留字前添加 `_skReserved_` 前缀

### 驱动 Bug 变通方案

GLSL 代码生成器包含大量针对特定 GPU 驱动的变通方案：

1. **`writeMinAbsHack`** -- Tegra3 编译器无法正确处理 `min(abs(x), y)`，将其重写为条件表达式。
2. **`writeDeterminantHack`** -- 当 GPU 不支持 `determinant()` 时生成手动实现。
3. **`writeInverseHack`** -- 当 GPU 不支持 `inverse()` 时生成手动实现（2x2, 3x3, 4x4）。
4. **`writeTransposeHack`** -- 当 GPU 不支持 `transpose()` 时生成手动实现。
5. **`writeInverseSqrtHack`** -- inversesqrt 的变通。
6. **`writeMatrixComparisonWorkaround`** -- 矩阵比较运算变通。
7. **`writeShortCircuitWorkaroundExpression`** -- 短路求值变通。
8. **`writeFragCoord`** -- FragCoord Y 轴翻转处理。

### 精度限定符

`usesPrecisionModifiers()` 检查 `ShaderCaps` 中的 `fUsesPrecisionModifiers` 标志。当目标为 GLES 时，需要输出 `highp`/`mediump`/`lowp` 限定符。

### 表达式输出分发

`writeExpression()` 通过 `Expression::Kind` 枚举进行分发，处理所有表达式类型：二元表达式、构造器、函数调用、字面量、swizzle、索引等。

### 多缓冲区输出

生成器使用多个 `StringStream` 缓冲区分别收集扩展声明、全局声明和额外函数，最终在 `generateCode()` 中按正确顺序合并输出。

### void 函数返回值重写

`shouldRewriteVoidTypedFunctions()` 检查函数是否需要将 void 返回类型重写。某些 GPU 驱动程序对特定的 void 函数调用模式存在问题，需要将其转换为返回虚拟值的形式。

### 构造器输出

构造器表达式的输出根据类型分流：
- `ConstructorCompound` -- 复合构造，可能需要展开为逐分量构造
- `ConstructorDiagonalMatrix` -- 对角矩阵构造，需要特殊处理
- `ConstructorArrayCast` -- 数组转换构造，GLSL 中跳过（类型已匹配）
- 其他构造器 -- 通过 `writeAnyConstructor` 统一处理
- 类型转换构造器 -- 通过 `writeCastConstructor` 处理

## 依赖关系

**内部依赖：**
- `SkSLCodeGenerator` -- 代码生成器基类
- SkSL IR 体系 -- 几乎所有 IR 节点类型
- `SkSLAnalysis` -- 程序分析
- `SkSLGLSL` -- GLSL 版本信息
- `SkSLIntrinsicList` -- 内建函数列表
- `SkSLShaderCaps` / `SkSLUtil` -- GPU 能力查询
- `SkSLOutputStream` / `SkSLStringStream` -- 输出流

**外部依赖：**
- `SkTHash` -- 哈希容器（保留字查找）
- `SkNoDestructor` -- 静态对象生命周期管理
- `SkTraceEvent` -- 性能追踪

## 设计模式与设计决策

1. **流式输出模式**：与 WGSL 生成器的字符串返回模式不同，GLSL 生成器直接将内容写入输出流。这是更传统的代码生成方式。

2. **ShaderCaps 驱动的变通**：所有驱动 Bug 变通都通过 `ShaderCaps` 标志控制，允许在运行时根据实际硬件选择最佳代码路径。

3. **Polyfill 按需生成**：`determinant`、`inverse`、`transpose` 等函数的手动实现只在实际使用时生成，通过 `fWritten*` 标志防止重复。

4. **函数头部延迟写入**：`fFunctionHeader` 收集函数内的临时变量声明，在函数体生成完毕后再插入到函数开头。这允许按需在函数体中引入辅助变量。

5. **多缓冲区有序合并**：扩展、全局和函数体分别生成，最终按 GLSL 规范要求的顺序（版本 -> 扩展 -> 全局 -> 函数）合并。

## 性能考量

- **代码压缩**：Pretty-print 关闭时省略缩进，减小着色器字符串大小。
- **冗余检查避免**：标识符安全处理先检查是否包含问题字符，只在必要时执行替换。
- **Polyfill 函数复用**：同一程序中多次使用 `inverse()` 只生成一份 polyfill 实现。
- **驱动适配**：通过 ShaderCaps 在编译时选择最优路径，避免运行时的降级处理。
- **半精度降级**：在不支持 mediump 的平台上，`half` 类型透明降级为 `float`，无额外运行时开销。
- **函数头部延迟写入**：临时变量声明收集在 `fFunctionHeader` 中，函数体生成完毕后一次性插入，避免多次扫描。
- **条件启用扩展**：仅在实际使用了需要扩展的功能时才输出对应的 `#extension` 声明，避免不必要的扩展依赖。

## 相关文件

- `src/sksl/codegen/SkSLCodeGenerator.h` -- 代码生成器基类
- `src/sksl/codegen/SkSLWGSLCodeGenerator.h` -- WGSL 代码生成器
- `src/sksl/codegen/SkSLCodeGenTypes.h` -- 代码生成类型
- `src/sksl/codegen/SkSLNativeShader.h` -- NativeShader 结构
- `src/sksl/SkSLGLSL.h` -- GLSL 版本定义
- `src/sksl/SkSLUtil.h` -- ShaderCaps
- `src/sksl/SkSLIntrinsicList.h` -- 内建函数列表
- `src/sksl/spirv.h` -- SPIR-V 内建常量
- `src/sksl/ir/SkSLProgram.h` -- 程序 IR
- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义
- `src/sksl/ir/SkSLExtension.h` -- 扩展声明
