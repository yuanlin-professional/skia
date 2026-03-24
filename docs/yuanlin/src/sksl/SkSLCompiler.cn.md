# SkSL Compiler（编译器主类）

> 源文件：[src/sksl/SkSLCompiler.h](../../src/sksl/SkSLCompiler.h)、[src/sksl/SkSLCompiler.cpp](../../src/sksl/SkSLCompiler.cpp)

## 概述

`Compiler` 是 SkSL 着色语言编译器的核心入口类。它负责将 SkSL 源代码文本解析为中间表示（IR）树，在解析过程中执行常量折叠和死代码消除等基础优化，随后将生成的 `Program` 对象传递给代码生成器以产生最终输出。`Compiler` 还管理编译上下文、符号表、内存池、错误报告等核心基础设施，并提供模块编译和优化的完整管道。

## 架构位置

`Compiler` 位于 SkSL 编译管道的顶层，统领整个编译流程：

```
用户代码 -> Compiler::convertProgram()
               |
               v
        ModuleLoader（加载预编译模块）
               |
               v
        Parser（解析源代码为 IR）
               |
               v
        Compiler::finalize()（最终验证）
               |
               v
        Compiler::optimize()（优化：内联、死代码消除等）
               |
               v
        CodeGenerator（GLSL / Metal / SPIR-V 等）
```

## 主要类与结构体

### `class Compiler`

编译器主类（`SK_API` 导出），核心成员：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fErrorReporter` | `CompilerErrorReporter` | 内部错误报告器 |
| `fContext` | `std::shared_ptr<Context>` | 编译上下文（共享所有权） |
| `fGlobalSymbols` | `std::unique_ptr<SymbolTable>` | 全局符号表 |
| `fConfig` | `std::unique_ptr<ProgramConfig>` | 程序配置 |
| `fPool` | `std::unique_ptr<Pool>` | 内存池 |
| `fErrorText` | `std::string` | 累积的错误文本 |

### `enum class OverrideFlag`

允许调试工具（如 Viewer、Nanobench）覆盖编译设置：

| 值 | 说明 |
|----|------|
| `kDefault` | 使用程序设置中的默认值 |
| `kOff` | 强制关闭 |
| `kOn` | 强制开启 |

### 内置变量常量

头文件定义了大量 builtin 变量 ID 常量：

| 常量 | 值 | 说明 |
|------|----|------|
| `SK_FRAGCOLOR_BUILTIN` | 10001 | `sk_FragColor` |
| `SK_FRAGCOORD_BUILTIN` | 15 | `sk_FragCoord` |
| `SK_POSITION_BUILTIN` | 0 | `sk_Position` |
| `SK_VERTEXID_BUILTIN` | 42 | `sk_VertexID` |
| `SK_GLOBALINVOCATIONID_BUILTIN` | 28 | `sk_GlobalInvocationID` |

## 公共 API 函数

### 编译入口

- **`convertProgram(kind, programSource, settings)`** —— 将 SkSL 源代码编译为 `Program`。自动加载对应 `ProgramKind` 的模块，通过 Parser 解析源代码，完成优化和验证。
- **`compileModule(kind, moduleType, moduleSource, parentModule, shouldInline)`** —— 编译一个 SkSL 模块，用于构建模块层级结构。

### 静态工具函数

- **`GetRTAdjustVector(rtDims, flipY)`** —— 计算 `sk_RTAdjust` 向量，将 Skia 设备坐标转换为归一化设备坐标。
- **`GetRTFlipVector(rtHeight, flipY)`** —— 计算用于实现 `dFdy`、`sk_Clockwise` 和 `sk_FragCoord` 的翻转向量。

### 优化控制

- **`EnableOptimizer(flag)` / `EnableInliner(flag)`** —— 静态方法，允许全局覆盖优化器/内联器的启用状态。
- **`runInliner(program)`** —— 对已编译的程序运行内联优化。
- **`optimizeModuleBeforeMinifying(kind, module, shrinkSymbols)`** —— 在模块最小化之前执行优化。

### 错误处理

- **`handleError(msg, pos)`** —— 处理编译错误，格式化错误位置和上下文代码。
- **`errorText(showCount)`** —— 获取格式化的错误文本。
- **`errorCount()` / `resetErrors()`** —— 查询/重置错误计数。

### 上下文访问

- **`context()`** —— 获取编译上下文引用。
- **`globalSymbols()` / `symbolTable()`** —— 获取全局或当前符号表。

## 内部实现细节

### 编译管道

`convertProgram` 的完整流程：
1. 将源代码包装在 `unique_ptr<string>` 中，保证稳定性
2. 通过 `moduleForProgramKind` 加载对应的预编译模块
3. `initializeContext` 初始化编译环境（内存池、符号表、配置）
4. 创建 `Parser` 解析源代码为 IR
5. `cleanupContext` 清理编译环境
6. 在 `releaseProgram` 中执行 `finalize`（验证）和 `optimize`（优化）

### AutoProgramConfig

内部 RAII 类，用于临时切换 `Context` 中的 `ProgramConfig`。在模块优化等场景中使用，确保上下文配置在函数返回时正确恢复。

### 优化阶段

`optimize` 方法按以下顺序执行优化：
1. **内联**（`Inliner::analyze`）—— 仅执行一次，开销较大
2. **不可达代码消除**（`EliminateUnreachableCode`）
3. **死函数消除**（`EliminateDeadFunctions`）—— 迭代直到无变化
4. **死局部变量消除**（`EliminateDeadLocalVariables`）—— 迭代直到无变化
5. **死全局变量消除**（`EliminateDeadGlobalVariables`）—— 迭代直到无变化

### 模块优化的两个阶段

- **`optimizeModuleBeforeMinifying`**：离线构建时执行，包含符号重命名、常量替换、空语句消除、大括号消除、splat 转 swizzle 等
- **`optimizeModuleAfterLoading`**：运行时加载后执行，仅包含内联优化

### 错误格式化

`handleError` 生成详细的错误报告，包括行号、源代码上下文和插入符号标记，类似于现代 C++ 编译器的错误输出。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLContext.h` | 编译上下文 |
| `SkSLParser.h` | 源代码解析器 |
| `SkSLInliner.h` | 函数内联器 |
| `SkSLModuleLoader.h` | 模块加载 |
| `SkSLAnalysis.h` | 静态分析工具 |
| `SkSLTransform.h` | 代码变换工具 |
| `SkSLPool.h` | 内存池管理 |
| `SkTraceEvent.h` | 性能追踪 |

## 设计模式与设计决策

1. **单例模块加载器**：通过 `ModuleLoader::Get()` 访问线程安全的全局单例，模块在进程生命周期内缓存。
2. **RAII 上下文管理**：`initializeContext` / `cleanupContext` 配对使用，`AutoProgramConfig` 保证配置恢复。
3. **不可复制**：`Compiler` 删除了拷贝构造函数和赋值运算符，防止意外复制。
4. **全局覆盖机制**：通过静态 `OverrideFlag` 允许调试工具全局控制优化行为。
5. **友元类**：`Parser` 和 `ThreadContext` 被声明为友元，可访问私有成员。
6. **迭代优化**：死代码消除等优化在循环中迭代执行，因为移除一个死元素可能使其他元素变为死代码。

## 性能考量

- 内联仅执行一次以限制编译时间（多次传递的收益递减）
- 使用 `TRACE_EVENT0` 标记 `convertProgram` 便于性能分析
- `SK_ENABLE_OPTIMIZE_SIZE` 编译选项可完全禁用内联以减小二进制大小
- 内存池（`Pool`）减少频繁的小对象分配
- 模块在进程级别缓存，避免重复编译
- `FinalizeSettings` 在优化关闭时连带禁用依赖优化的设置，避免无效工作

## 相关文件

- `src/sksl/SkSLParser.h` / `.cpp` —— 语法解析器
- `src/sksl/SkSLInliner.h` / `.cpp` —— 函数内联器
- `src/sksl/SkSLModuleLoader.h` / `.cpp` —— 模块加载器
- `src/sksl/SkSLContext.h` —— 编译上下文
- `src/sksl/SkSLAnalysis.h` —— 静态分析
- `src/sksl/transform/SkSLTransform.h` —— IR 变换
- `src/sksl/ir/SkSLProgram.h` —— 编译输出的 Program 结构
- `src/sksl/SkSLProgramSettings.h` —— 程序设置
- `src/sksl/SkSLPool.h` —— 内存池
