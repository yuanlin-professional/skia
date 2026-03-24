# SkSL WGSL 代码生成器 (SkSLWGSLCodeGenerator)

> 源文件:
> - `src/sksl/codegen/SkSLWGSLCodeGenerator.h`
> - `src/sksl/codegen/SkSLWGSLCodeGenerator.cpp`

## 概述

WGSL 代码生成器负责将 SkSL 编译器的中间表示（IR）程序转换为 WebGPU 着色语言（WGSL）代码。这是 Skia 在 WebGPU/Dawn 后端上运行的关键组件。该模块处理了 SkSL 与 WGSL 之间的大量语法和语义差异，包括类型映射、运算符转换、管线 I/O 结构体合成、uniform 布局多态填充（polyfill）、矩阵运算补丁、以及内建函数映射等。由于 WGSL 规范较为严格（不支持隐式类型转换、不支持 fallthrough 的 switch 等），该生成器包含了大量的适配和变通逻辑。源文件超过 5000 行，是 SkSL 后端中最复杂的代码生成器之一。

## 架构位置

WGSL 代码生成器位于 SkSL 编译器的代码生成（codegen）层，继承自 `CodeGenerator` 基类。

```
SkSL Program (IR)
  |
  |-- ToWGSL() [入口函数]
  |     |-- WGSLCodeGenerator::generateCode()
  |           |-- preprocessProgram() (分析依赖)
  |           |-- writeEnables() (扩展启用)
  |           |-- writeStageInputStruct() / writeStageOutputStruct()
  |           |-- writeUniformsAndBuffers()
  |           |-- writeProgramElement() (逐元素生成)
  |           |-- writeEntryPoint() (入口点)
  |
  |-- ToGLSL() [其他后端]
  |-- MakeRasterPipelineProgram() [其他后端]
```

## 主要类与结构体

### `WGSLCodeGenerator`

继承自 `CodeGenerator`，是 WGSL 代码生成的核心类。在 `.cpp` 文件中定义（非公开头文件导出）。

**关键内嵌类型：**
- `Builtin` 枚举 -- WGSL 内建变量（如 `@builtin(position)`, `@builtin(vertex_index)` 等）
- `Delimiter` 枚举 -- 声明分隔符类型（逗号、分号、无）
- `ProgramRequirements` -- 程序级需求，包含函数依赖映射和扩展标志
- `LValue` / `PointerLValue` / `SwizzleLValue` / `VectorComponentLValue` -- 左值抽象层次

**关键成员变量：**
- `fHeader` -- 头部代码流（在主体之前输出）
- `fRequirements` -- 函数管线依赖信息
- `fPipelineInputs` / `fPipelineOutputs` -- 管线输入/输出变量
- `fFieldPolyfillMap` -- uniform 布局多态填充映射
- `fF32Polyfills` / `fF16Polyfills` -- 数学函数多态填充状态

### `WGSLFunctionDependency`

位掩码枚举，标识函数对管线输入/输出参数的依赖：
- `kPipelineInputs` -- 函数需要管线输入参数
- `kPipelineOutputs` -- 函数需要管线输出参数

## 公共 API 函数

### 入口函数（头文件导出）

- **`ToWGSL(program, caps, out, prettyPrint, includeSyntheticCode, validateProc)`** -- 完整版 WGSL 生成，支持格式化输出、合成代码控制和验证回调。
- **`ToWGSL(program, caps, out)`** -- 简化版。
- **`ToWGSL(program, caps, nativeShader)`** -- 输出到 `NativeShader` 结构。

### 类型与枚举

- **`IncludeSyntheticCode`** -- 控制是否包含编译器合成的代码。
- **`ValidateWGSLProc`** -- WGSL 验证回调函数类型。

## 内部实现细节

### 代码生成流程

`generateCode()` 按以下顺序执行：
1. `preprocessProgram()` -- 分析所有函数的管线 I/O 依赖
2. 收集管线输入/输出变量
3. 写入 `enable` 指令（如 `enable f16;`）
4. 写入管线阶段 I/O 结构体
5. 写入 uniform 和 buffer 声明
6. 遍历所有 ProgramElement 并输出（结构体定义、全局变量、函数）
7. 写入着色器入口点函数（包含 uniform polyfill 解包）
8. 将头部和主体合并输出

### 类型映射

SkSL 类型到 WGSL 类型的映射通过 `to_wgsl_type()` 函数实现：
- `float`/`half` -> `f32`/`f16`（取决于 f16 扩展是否可用）
- `int` -> `i32`, `uint` -> `u32`, `bool` -> `bool`
- `float2` -> `vec2<f32>`, `mat3x4` -> `mat3x4<f32>` 等
- `atomicUint` -> `atomic<u32>`
- 数组 -> `array<elementType, size>`
- 纹理 -> `texture_2d<f32>`, `texture_storage_2d<format, write>` 等

### 内建变量映射

WGSL 的内建变量通过 `builtin_from_sksl_name()` 从 SkSL 内建常量映射：
- `SK_POSITION_BUILTIN` / `SK_FRAGCOORD_BUILTIN` -> `@builtin(position)`
- `SK_VERTEXID_BUILTIN` -> `@builtin(vertex_index)`（需要 u32 到 i32 类型转换）
- `SK_INSTANCEID_BUILTIN` -> `@builtin(instance_index)`
- `SK_CLOCKWISE_BUILTIN` -> `@builtin(front_facing)`
- `SK_SAMPLEMASKIN_BUILTIN` -> `@builtin(sample_mask)`

### 指针和地址空间

WGSL 使用显式的地址空间（address space）系统：
- `function` -- 函数局部变量
- `private` -- 模块级私有变量
- `storage` -- 存储缓冲区

函数参数在需要时被转换为指针类型 `ptr<address_space, type>`。

### 内建函数适配

SkSL 内建函数到 WGSL 的映射通过 `assembleIntrinsicCall()` 处理：
- 简单重命名：`dFdx` -> `dpdx`，`dFdy` -> `dpdy`
- 运算符替换：`mod(a,b)` -> `a % b`
- 多态填充：`inverse()`、`outerProduct()` 需要手动实现
- 纹理采样：`sample()`、`sampleLod()` 需要分离采样器和纹理

### 管线 I/O 结构体合成

WGSL 要求管线输入/输出通过结构体传递。生成器自动创建 `VSIn`/`VSOut`/`FSIn`/`FSOut`/`CSIn` 等结构体，将 SkSL 的全局管线变量包装其中，并为每个字段添加适当的 `@location` 或 `@builtin` 属性。

### Uniform 布局多态填充

WGSL 的 uniform 布局与 std140 存在差异（特别是矩阵和数组对齐）。生成器通过 `FieldPolyfillMap` 跟踪需要多态填充的字段，在着色器入口点生成解包代码，将 `@align(16)` 的包装结构解包为原生类型。

### 保留字处理

WGSL 有大量保留字（包括关键字、预声明类型、预声明枚举、以及未来保留字）。`is_reserved_word()` 使用哈希集合检查标识符，冲突时通过重命名（添加前缀）解决。

### 表达式汇编模式

`assembleExpression()` 方法有三种模式：
- `kAuto` -- 自动决定内联或创建 `let` 变量
- `kUsedMultipleTimes` -- 对平凡表达式内联，复杂表达式创建 `let`
- `kForceLet` -- 强制创建 `let` 变量

### Switch 语句的 Fallthrough 模拟

WGSL 不支持 switch fallthrough。生成器分析 case 结构，在需要 fallthrough 时通过条件变量模拟。

### 矩阵分量操作补丁

WGSL 不支持矩阵的分量级二元运算（如矩阵加法）。生成器检测此类操作并生成按列的逐分量计算代码。

## 依赖关系

**内部依赖：**
- `SkSLCodeGenerator` -- 代码生成器基类
- SkSL IR 体系 -- 几乎所有 IR 节点类型
- `SkSLAnalysis` -- 程序分析（函数依赖）
- `SkSLMemoryLayout` -- 内存布局计算
- `SkSLConstantFolder` -- 常量折叠
- `SkSLTransform` -- IR 变换
- `SkSLOutputStream` / `SkSLStringStream` -- 输出流

**外部依赖：**
- `SkTHash` -- 哈希容器
- `SkTraceEvent` -- 性能追踪

## 设计模式与设计决策

1. **字符串返回的表达式汇编**：表达式生成方法返回 `std::string` 而非直接写入流，允许灵活的表达式组合和 `let` 变量引入。

2. **预处理+生成两阶段**：`preprocessProgram()` 先分析函数依赖关系，然后 `generateCode()` 根据分析结果生成正确的参数传递。

3. **多态填充策略**：对于 WGSL 不支持的 SkSL 特性（如 `inverse()`、`outerProduct()`、矩阵分量运算），采用生成辅助函数的方式解决，并缓存已生成的补丁以避免重复。

4. **LValue 抽象**：将赋值目标抽象为 `LValue` 层次，统一处理指针、swizzle 和向量分量等不同的赋值场景。

## 性能考量

- **生成代码质量**：Pretty-print 模式可关闭以减少输出大小。
- **let 变量引入**：对多次使用的表达式自动引入 `let` 变量，避免在 WGSL 中重复求值。
- **多态填充按需生成**：`inverse` 等数学函数的 polyfill 只在实际使用时才生成。
- **F16 支持**：在硬件支持时使用 `f16` 类型，减少带宽和提升性能。
- **const 求值变通**：通过 `AutoConstEvalWorkaround` 类处理 WGSL/Tint 的 const 表达式求值问题，在需要时将 `const` 降级为 `let`。
- **scratch 变量管理**：通过 `fScratchCount` 计数器生成唯一的临时变量名（`_skTemp0`, `_skTemp1` 等），避免名称冲突。
- **条件作用域追踪**：`fConditionalScopeDepth` 追踪条件代码块的嵌套深度，用于决定是否可以使用 `const` 而非 `let`。

## 相关文件

- `src/sksl/codegen/SkSLCodeGenerator.h` -- 代码生成器基类
- `src/sksl/codegen/SkSLWGSLValidator.h` -- WGSL 验证器
- `src/sksl/codegen/SkSLGLSLCodeGenerator.h` -- GLSL 代码生成器（类似功能）
- `src/sksl/codegen/SkSLCodeGenTypes.h` -- 代码生成类型定义
- `src/sksl/codegen/SkSLNativeShader.h` -- NativeShader 输出结构
- `src/sksl/SkSLMemoryLayout.h` -- 内存布局工具
- `src/sksl/SkSLUtil.h` -- ShaderCaps 定义
- `src/sksl/SkSLCompiler.h` -- 编译器（调用 ToWGSL 的入口）
- `src/sksl/analysis/SkSLProgramUsage.h` -- 程序使用分析
- `src/sksl/analysis/SkSLProgramVisitor.h` -- 程序访问者（依赖分析）
- `src/sksl/ir/SkSLInterfaceBlock.h` -- 接口块（uniform buffer）
- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义
- `src/sksl/ir/SkSLVariable.h` -- 变量（管线 I/O）
- `src/sksl/spirv.h` -- SPIR-V 内建常量（内建变量映射）
