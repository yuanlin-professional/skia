# src/sksl - SkSL 着色器语言编译器

## 概述

SkSL（"Skia Shading Language"，Skia 着色语言）是 Skia 图形库的内部着色器语言编译器模块。SkSL 本质上是 GLSL（OpenGL 着色语言）的一个标准化变体，旨在消除 GLSL 在不同厂商驱动、不同版本之间存在的各种差异和方言问题，为 Skia 渲染引擎提供统一的着色器编程接口。该编译器自 2016 年由 Google 开发至今，是 Skia 项目中最为复杂和核心的模块之一。

SkSL 编译器的核心职责是将用户编写的 SkSL 源代码转换为各种目标后端所需的着色器格式，包括 GLSL、GLSL ES、SPIR-V（Vulkan）、MSL（Metal）、HLSL（Direct3D）以及 WGSL（WebGPU）。这种多后端架构使得 Skia 能够在几乎所有主流图形平台上运行，而开发者只需编写一份着色器代码。

在语言层面，SkSL 对 GLSL 进行了若干改进。例如，精度修饰符被简化（使用 `half`/`short`/`ushort` 表示中等精度），向量和矩阵类型采用更直观的命名方式（如 `float2` 代替 `vec2`，`float3x3` 代替 `mat3`），并且支持通过 `sk_Caps` 在编译期查询硬件能力，配合常量折叠和分支消除实现条件编译效果。SkSL 还引入了面向 GPU 计算的原子操作和同步原语，支持 `atomicUint` 类型以及 `workgroupBarrier()` / `storageBarrier()` 等屏障函数。

从架构角度看，SkSL 编译器采用了经典的多阶段编译器设计：词法分析 (Lexer) -> 语法分析 (Parser) -> 中间表示 (IR) -> 分析与优化 (Analysis/Transform) -> 代码生成 (CodeGenerator)。整个编译流程高度模块化，各阶段通过清晰定义的接口进行协作，使得新增后端或优化 pass 变得相对简单。

SkSL 编译器不仅服务于传统的顶点/片段着色器编译，还支持运行时效果 (Runtime Effects)，允许应用在运行时动态创建自定义的 SkShader、SkColorFilter 和 SkBlender。此外，它还支持 Skia 新一代渲染后端 Graphite 的特有着色器格式，以及自定义 Mesh 着色器。

## 架构图

```
                            +-------------------+
                            |   SkSL 源代码      |
                            | (.sksl 文本输入)    |
                            +--------+----------+
                                     |
                                     v
                            +--------+----------+
                            |   Lexer (词法分析)  |
                            |  SkSLLexer.h/.cpp  |
                            +--------+----------+
                                     |
                                     | Token 流
                                     v
                            +--------+----------+
                            |  Parser (语法分析)  |
                            |  SkSLParser.h/.cpp |
                            +--------+----------+
                                     |
                                     | IR 节点树
                                     v
                   +-----------------+------------------+
                   |          IR (中间表示层)             |
                   |  ir/SkSLExpression, Statement,     |
                   |  ProgramElement, Type, Symbol...   |
                   +-----------------+------------------+
                                     |
                        +------------+------------+
                        |                         |
                        v                         v
              +---------+---------+    +----------+----------+
              | Analysis (分析)    |    | Transform (变换)     |
              | - 程序使用量分析    |    | - 死代码消除          |
              | - 循环展开信息     |    | - 常量替换            |
              | - 副作用检测       |    | - 不可达代码消除       |
              | - 返回值分析       |    | - 函数内联            |
              +-------------------+    | - 符号重命名          |
                                       +----------+----------+
                                                   |
                                     +-------------+
                                     |
                        +------------+-------------+
                        |      Compiler (编译器)    |
                        |   SkSLCompiler.h/.cpp    |
                        |  (协调整个编译流水线)      |
                        +------------+-------------+
                                     |
              +----------+-----------+-----------+----------+----------+
              |          |           |           |          |          |
              v          v           v           v          v          v
         +--------+ +--------+ +--------+ +--------+ +--------+ +--------+
         | GLSL   | | SPIRV  | | Metal  | | HLSL   | | WGSL   | | RP     |
         | Code   | | Code   | | Code   | | Code   | | Code   | | Code   |
         | Gen    | | Gen    | | Gen    | | Gen    | | Gen    | | Gen    |
         +--------+ +--------+ +--------+ +--------+ +--------+ +--------+
              |          |           |           |          |          |
              v          v           v           v          v          v
          OpenGL     Vulkan      Apple       Direct3D   WebGPU    Raster
          驱动        驱动       Metal        驱动       浏览器    Pipeline
```

## 目录结构

### 子目录

| 子目录 | 用途 |
|--------|------|
| `ir/` | 中间表示（Intermediate Representation）节点定义，包含所有表达式、语句、程序元素、类型和符号表的 IR 类 |
| `codegen/` | 代码生成器，包含 GLSL、SPIR-V、Metal、HLSL、WGSL 和 Raster Pipeline 等多个后端 |
| `analysis/` | 程序静态分析工具，如程序使用量分析、循环展开检测、副作用检测、常量表达式判断等 |
| `transform/` | IR 变换 pass，如死代码消除、常量替换、符号重命名、不可达代码删除等 |
| `tracing/` | 调试跟踪支持，用于着色器的逐步调试和变量检查 |
| `lex/` | 词法分析器生成工具 `sksllex` 的源代码和词法规则文件 |
| `generated/` | 预生成的优化和压缩后的模块文件（.minified.sksl 和 .unoptimized.sksl） |

### 顶层关键文件

| 文件 | 说明 |
|------|------|
| `SkSLCompiler.h/.cpp` | 编译器主入口类，协调整个编译流水线 |
| `SkSLParser.h/.cpp` | 语法分析器，将 Token 流转换为 IR 树 |
| `SkSLLexer.h/.cpp` | 词法分析器（由 sksllex 自动生成），将源文本切分为 Token |
| `SkSLContext.h/.cpp` | 编译上下文，持有内置类型引用、错误报告器、符号表等编译器全局状态 |
| `SkSLAnalysis.h/.cpp` | 静态分析的聚合入口，声明 `Analysis` 命名空间下的所有分析函数 |
| `SkSLConstantFolder.h/.cpp` | 常量折叠器，在编译期化简常量表达式（如 `2 + 2` -> `4`） |
| `SkSLInliner.h/.cpp` | 函数内联器，将符合条件的函数调用展开为内联代码 |
| `SkSLBuiltinTypes.h/.cpp` | 内置类型定义，包含 float/half/int/bool/matrix/sampler 等所有基础类型 |
| `SkSLModule.h/.cpp` | 模块系统定义，SkSL 通过模块层次来组织内置声明 |
| `SkSLModuleLoader.h/.cpp` | 模块加载器，单例模式管理所有 SkSL 模块的加载和缓存 |
| `SkSLOperator.h/.cpp` | 运算符定义和类型推断逻辑 |
| `SkSLPool.h/.cpp` | 内存池，为 IR 节点分配提供高性能内存管理 |
| `SkSLPosition.h/.cpp` | 源码位置信息，用于错误报告和调试 |
| `SkSLErrorReporter.h/.cpp` | 错误报告器接口 |
| `SkSLProgramKind.h` | 程序类型枚举（Fragment、Vertex、Compute、Runtime Effect 等） |
| `SkSLProgramSettings.h` | 编译设置，包含优化开关、精度控制、内联阈值等选项 |
| `SkSLMemoryLayout.h` | 内存布局计算器，支持 std140/std430/Metal/WGSL 等多种内存布局标准 |
| `SkSLMangler.h/.cpp` | 名称修饰器，为内联过程中的变量生成唯一名称 |
| `SkSLUtil.h/.cpp` | 工具类，包含 `ShaderCaps` 硬件能力描述结构体 |
| `SkSLString.h/.cpp` | 字符串工具函数 |
| `SkSLOutputStream.h/.cpp` | 输出流抽象基类 |
| `SkSLDefines.h` | 全局类型定义和常量（如 `SKSL_INT`、`SKSL_FLOAT`、内联阈值等） |
| `SkSLGLSL.h` | GLSL 版本枚举定义 |
| `spirv.h` | SPIR-V 规范常量定义 |
| `GLSL.std.450.h` | GLSL 扩展指令集定义（SPIR-V 用） |
| `sksl_shared.sksl` | 共享内置函数模块，所有程序类型共用 |
| `sksl_gpu.sksl` | GPU 着色器专用内置函数模块 |
| `sksl_frag.sksl` | 片段着色器内置声明模块 |
| `sksl_vert.sksl` | 顶点着色器内置声明模块 |
| `sksl_compute.sksl` | 计算着色器内置声明模块 |
| `sksl_public.sksl` | 公共 Runtime Effect 模块 |
| `sksl_rt_shader.sksl` | 私有 Runtime Shader 模块 |
| `sksl_graphite_frag.sksl` | Graphite 后端片段着色器模块 |
| `sksl_graphite_vert.sksl` | Graphite 后端顶点着色器模块 |

## 关键类与函数

### Compiler（编译器主类）
- **文件**: `SkSLCompiler.h` / `SkSLCompiler.cpp`
- **职责**: 编译器的主入口，协调词法分析、语法分析、优化和最终化的完整编译流程。管理编译上下文、符号表和内存池的生命周期。
- **关键方法**:
  - `convertProgram(ProgramKind, std::string, ProgramSettings)` - 核心编译方法，将 SkSL 源码转换为 `Program` IR 树
  - `compileModule(ProgramKind, ModuleType, std::string, Module*, bool)` - 编译 SkSL 模块
  - `moduleForProgramKind(ProgramKind)` - 根据程序类型获取对应的基础模块
  - `runInliner(Program&)` - 对已编译程序执行函数内联优化
  - `optimize(Program&)` - 执行完整的优化流水线（私有）
  - `finalize(Program&)` - 最终检查，确认程序的正确性（私有）
  - `GetRTAdjustVector(SkISize, bool)` - 计算渲染目标坐标调整向量
  - `GetRTFlipVector(int, bool)` - 计算渲染目标翻转向量

### Parser（语法分析器）
- **文件**: `SkSLParser.h` / `SkSLParser.cpp`
- **职责**: 消耗 SkSL 文本输入，通过递归下降解析将其转换为 IR 树。直接产出 `Program` 或 `Module` 对象。
- **关键方法**:
  - `programInheritingFrom(const Module*)` - 解析源码生成继承指定模块的 Program
  - `moduleInheritingFrom(const Module*)` - 解析源码生成继承指定模块的 Module
  - `declaration()` - 解析顶层声明（函数、变量、结构体等）
  - `statement()` - 解析语句（if/for/while/switch/return 等）
  - `expression()` - 解析表达式，内部按优先级拆分为多个层次（assignmentExpression -> ternaryExpression -> logicalOrExpression -> ... -> term）
  - `type(Modifiers*)` - 解析类型声明
  - `layout()` - 解析 layout 限定符

### Lexer（词法分析器）
- **文件**: `SkSLLexer.h` / `SkSLLexer.cpp`（由 `lex/` 下的 sksllex 工具自动生成）
- **职责**: 将 SkSL 源文本切分为 Token 序列。使用 DFA（确定性有限自动机）实现高效的词法扫描。
- **关键方法**:
  - `start(std::string_view)` - 初始化词法分析器
  - `next()` - 返回下一个 Token
  - `getCheckpoint()` / `rewindToCheckpoint(Checkpoint)` - 支持回溯的检查点机制
- **Token 类型**: 包括数值字面量（`TK_FLOAT_LITERAL`、`TK_INT_LITERAL`）、关键字（`TK_IF`、`TK_FOR`、`TK_RETURN` 等）、运算符、标识符以及空白/注释等约 80 种 Token 类型。

### Context（编译上下文）
- **文件**: `SkSLContext.h` / `SkSLContext.cpp`
- **职责**: 持有编译器范围的全局对象和状态，包括内置类型引用、当前程序配置、错误报告器和当前符号表。
- **关键成员**:
  - `fTypes` - 对 `BuiltinTypes` 的引用，包含所有内置类型
  - `fConfig` - 当前程序的配置信息指针
  - `fErrors` - 错误报告器指针
  - `fModule` - 当前加载的内置模块指针
  - `fSymbolTable` - 当前正在处理的代码的符号表指针

### BuiltinTypes（内置类型集合）
- **文件**: `SkSLBuiltinTypes.h` / `SkSLBuiltinTypes.cpp`
- **职责**: 定义 SkSL 的所有内置类型，包括标量类型（float/half/int/uint/short/ushort/bool）、向量类型（float2-4 等）、矩阵类型（float2x2-4x4 等）、纹理和采样器类型、泛型类型（GenType 等）以及特殊类型（Shader/ColorFilter/Blender/AtomicUInt）。
- **特殊类型**: 包括 GLSL 兼容别名（vec2/mat4 等）、SkSL 特有类型（SkCaps、Shader、ColorFilter、Blender）和原子类型（atomicUint）。

### ConstantFolder（常量折叠器）
- **文件**: `SkSLConstantFolder.h` / `SkSLConstantFolder.cpp`
- **职责**: 在编译期对常量表达式进行化简。例如将 `2 + 2` 直接替换为 `4`，将 `true && x` 替换为 `x`。
- **关键方法**:
  - `Simplify(Context, Position, Expression, Operator, Expression, Type)` - 尝试化简二元表达式
  - `GetConstantInt(Expression, SKSL_INT*)` - 提取整数常量值
  - `GetConstantValue(Expression, double*)` - 提取标量常量值
  - `GetConstantValueForVariable(Expression)` - 对 const 变量取其编译期值
  - `IsConstantSplat(Expression, double)` - 检查表达式是否为全分量相同的常量

### Inliner（函数内联器）
- **文件**: `SkSLInliner.h` / `SkSLInliner.cpp`
- **职责**: 将函数调用替换为函数体的内联副本，以减少调用开销并为后续优化创造更多机会。受 `SK_ENABLE_OPTIMIZE_SIZE` 宏控制，可在优化体积模式下被完全禁用。
- **关键方法**:
  - `analyze(elements, symbols, usage)` - 扫描程序元素并内联所有合格的函数调用
  - `inlineCall(FunctionCall, SymbolTable, ProgramUsage, FunctionDeclaration)` - 执行单次函数内联（私有）
  - `isSafeToInline(FunctionDefinition, ProgramUsage)` - 判断函数是否可以安全内联（私有）
- **内联限制**: 函数大小超过阈值（默认 50 个 IR 节点 x 调用次数）、递归函数、包含复杂返回逻辑的函数将不会被内联。

### ModuleLoader（模块加载器）
- **文件**: `SkSLModuleLoader.h` / `SkSLModuleLoader.cpp`
- **职责**: 以单例模式管理所有 SkSL 内置模块的加载和生命周期。模块按需加载，一旦加载则在进程生命周期内保持。
- **关键方法**:
  - `Get()` - 获取互斥锁保护的单例引用
  - `builtinTypes()` / `rootModule()` - 获取全局共享的内置类型和根模块
  - `loadSharedModule()` / `loadGPUModule()` / `loadVertexModule()` 等 - 按需加载各类型模块
  - `addPublicTypeAliases(Module*)` - 为 Runtime Effect 添加 GLSL 类型别名（如 `vec4`）

### CodeGenerator（代码生成器基类）
- **文件**: `codegen/SkSLCodeGenerator.h`
- **职责**: 所有代码生成器的抽象基类，定义了从 `Program` 到目标代码的生成接口。
- **关键方法**:
  - `generateCode()` - 纯虚方法，由各后端实现具体的代码生成逻辑
- **具体实现**:
  - `GLSLCodeGenerator` - 生成 GLSL / GLSL ES 代码
  - `SPIRVCodeGenerator` - 生成 SPIR-V 二进制字节码
  - `MetalCodeGenerator` - 生成 Apple Metal Shading Language 代码
  - `HLSLCodeGenerator` - 生成 HLSL 代码（通过 SPIR-V 中间转换）
  - `WGSLCodeGenerator` - 生成 WebGPU Shading Language 代码
  - `RasterPipelineCodeGenerator` - 生成 Skia Raster Pipeline 操作序列
  - `PipelineStageCodeGenerator` - 为 Ganesh pipeline stage 生成代码

### MemoryLayout（内存布局计算器）
- **文件**: `SkSLMemoryLayout.h`
- **职责**: 根据不同的内存布局标准（std140/std430/Metal/WGSL）计算类型的对齐、大小和步长。
- **支持标准**: `k140`（OpenGL std140）、`k430`（OpenGL std430）、`kMetal`（Apple Metal）、`kWGSLUniform_Base/EnableF16`（WebGPU uniform 地址空间）、`kWGSLStorage_Base/EnableF16`（WebGPU storage 地址空间）。
- **关键方法**:
  - `alignment(Type)` - 计算类型的对齐要求
  - `size(Type)` - 计算类型占用的字节数
  - `stride(Type)` - 计算数组/矩阵的步长
  - `isSupported(Type)` - 检查类型是否与当前布局标准兼容

### Pool（内存池）
- **文件**: `SkSLPool.h` / `SkSLPool.cpp`
- **职责**: 为 SkSL IR 节点提供高性能内存分配。通过线程本地的内存池减少频繁的堆分配开销。继承自 `Poolable` 的类将自动使用内存池。
- **关键方法**:
  - `Create()` - 创建新的内存池
  - `attachToThread()` / `detachFromThread()` - 将内存池绑定/解绑到当前线程
  - `AllocMemory(size)` / `FreeMemory(ptr)` - 静态内存分配/释放方法

## 依赖关系

### 上游依赖（本模块依赖的模块）

| 依赖模块 | 说明 |
|----------|------|
| `include/core/` | Skia 核心类型定义，如 `SkTypes.h`、`SkSize.h`、`SkPoint.h` |
| `include/private/base/` | 内部基础工具，如 `SkTArray.h`（动态数组）、`SkAssert.h`（断言宏） |
| `include/sksl/` | SkSL 的公共 API 头文件，如 `SkSLVersion.h`、`SkSLDebugTrace.h` |
| `include/private/SkSLSampleUsage.h` | 采样使用信息的公共定义 |
| `src/core/SkTHash.h` | Skia 内部哈希表实现，用于 Inliner 的缓存 |
| `src/core/SkTraceEvent.h` | Skia 性能跟踪事件 |

### 下游被依赖（依赖本模块的模块）

| 依赖方 | 说明 |
|--------|------|
| `src/gpu/ganesh/` | Ganesh (OpenGL/Vulkan/D3D) GPU 后端，使用 SkSL 编译器编译着色器程序 |
| `src/gpu/graphite/` | Graphite (新一代 Metal/Vulkan/Dawn) GPU 后端 |
| `src/gpu/SkSLToBackend.cpp` | GPU 层的 SkSL 到后端着色器转换工具 |
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.cpp` | Ganesh GLSL 程序构建器 |
| `src/gpu/ganesh/gl/` | Ganesh OpenGL 后端（GrGLProgram、GrGLUniformHandler） |
| `src/gpu/ganesh/mtl/` | Ganesh Metal 后端 |
| `src/gpu/ganesh/vk/` | Ganesh Vulkan 后端 |
| `src/gpu/ganesh/d3d/` | Ganesh Direct3D 后端 |
| `src/gpu/graphite/mtl/` | Graphite Metal 后端 |
| `src/gpu/graphite/vk/` | Graphite Vulkan 后端 |
| `src/gpu/graphite/dawn/` | Graphite Dawn (WebGPU) 后端 |
| `tools/skslc/` | SkSL 命令行编译器工具 |
| `tools/sksl-minify/` | SkSL 模块压缩工具 |
| `tools/viewer/` | Skia Viewer 调试工具，支持实时着色器编辑 |
| `tests/` | SkSL 单元测试套件 |

### 外部依赖（第三方库）

| 依赖 | 说明 |
|------|------|
| SPIR-V 头文件 (`spirv.h`) | SPIR-V 规范的常量定义，直接包含在源码中 |
| GLSL.std.450 (`GLSL.std.450.h`) | SPIR-V 的 GLSL 扩展指令集头文件 |
| SPIRV-Tools（可选） | 用于 SPIR-V 验证 (`SkSLSPIRVValidator.cpp`) |
| spirv-cross（可选） | 用于 SPIR-V 到 HLSL 的转换 (`SkSLSPIRVtoHLSL.cpp`) |

## 设计模式分析

### 访问者模式（Visitor Pattern）
SkSL 编译器大量使用访问者模式遍历 IR 树。`analysis/SkSLProgramVisitor.h` 定义了模板化的 `TProgramVisitor<T>` 基类，提供 `visitExpression()`、`visitStatement()` 和 `visitProgramElement()` 三个虚方法。具体的分析 pass（如副作用检测 `HasSideEffects`、常量表达式判断 `IsConstantExpression`、程序使用量分析 `ProgramUsage`）均通过继承此访问者基类实现。该模式还区分了只读的 `ProgramVisitor` 和可修改的 `ProgramWriter`，通过类型系统在编译期保证 const 正确性。

### 工厂模式（Factory Pattern）
IR 节点的创建广泛采用静态工厂方法（如 `IfStatement::Convert()`、`ForStatement::Convert()`、`BinaryExpression::Convert()` 等）。这些工厂方法不仅负责构造对象，还在创建时执行类型检查、常量折叠和简化优化，确保 IR 树在构建时即保持良好的语义一致性。

### 单例模式（Singleton Pattern）
`ModuleLoader` 采用线程安全的单例模式，通过 `ModuleLoader::Get()` 获取互斥锁保护的全局实例。内置类型和根模块在首次初始化后全进程共享，而各种功能模块（如 GPU 模块、Fragment 模块等）则按需加载并缓存。

### 策略模式（Strategy Pattern）
代码生成采用策略模式。抽象基类 `CodeGenerator` 定义了 `generateCode()` 纯虚接口，各后端（GLSL、SPIR-V、Metal、HLSL、WGSL、RasterPipeline）提供各自的具体实现。`Compiler` 类不直接参与代码生成，而是由调用方根据目标平台选择合适的 `CodeGenerator` 实现。

### RAII 模式（Resource Acquisition Is Initialization）
模块中大量使用 RAII 惯用法管理资源和状态。例如：
- `AutoProgramConfig` - 自动保存和恢复编译上下文的程序配置
- `AutoAttachPoolToThread` - 自动将内存池绑定到线程并在作用域结束时解绑
- `AutoOutputStream` - 自动切换和恢复代码生成器的输出流
- `Parser::AutoDepth` - 自动跟踪解析深度并防止栈溢出
- `Parser::AutoSymbolTable` - 自动管理符号表的作用域进出

### 模块模式（Module Pattern）
SkSL 的模块系统通过分层继承实现。模块之间形成一个层次化的继承链：`rootModule` -> `sksl_shared` -> `sksl_gpu` -> `sksl_frag/sksl_vert/sksl_compute`。每个模块包含符号表 (`fSymbols`)、程序元素列表 (`fElements`) 和父模块指针 (`fParent`)，通过这种链式结构实现声明的逐层可见性。

## 数据流

### 编译流水线

SkSL 的编译过程可以划分为以下几个阶段，数据在各阶段之间顺序流动：

1. **源码输入**: 用户提供 SkSL 源文本字符串和 `ProgramSettings` 编译设置。

2. **环境准备**: `Compiler::convertProgram()` 根据 `ProgramKind` 加载对应的基础模块（通过 `ModuleLoader`），创建内存池 (`Pool`) 并绑定到当前线程，初始化 `Context` 的程序配置和符号表。

3. **词法分析**: `Lexer` 将源文本切分为 `Token` 序列。每个 Token 包含类型 (`Kind`)、在源文本中的偏移 (`fOffset`) 和长度 (`fLength`)。词法分析器基于 DFA 实现，由 `lex/` 目录下的 `sksllex` 工具从 `sksl.lex` 规则文件自动生成。

4. **语法分析**: `Parser` 通过递归下降法消费 Token 流，直接构建 IR 树。解析过程中会进行基本的语义检查（类型匹配、变量声明合法性等），并在构造 IR 节点时触发常量折叠。Parser 产出的结果是一个 `Program` 对象，包含顶层程序元素列表和符号表。

5. **优化阶段**（如果启用 `fOptimize`）:
   - **函数内联** (`Inliner`): 扫描所有函数调用，将满足条件的调用替换为函数体副本
   - **死函数消除** (`EliminateDeadFunctions`): 移除未被调用的函数
   - **死变量消除** (`EliminateDeadLocalVariables` / `EliminateDeadGlobalVariables`): 移除未使用的变量
   - **不可达代码消除** (`EliminateUnreachableCode`): 移除无法到达的代码路径

6. **最终化检查** (`finalize`): 验证程序结构完整性，检查递归调用深度，确保所有函数都有返回值等。

7. **代码生成**: 调用方将 `Program` 传递给具体的 `CodeGenerator` 实现，生成目标平台的着色器代码。

### 模块数据流

```
sksl_shared.sksl (基础内置函数)
        |
        v
sksl_gpu.sksl (GPU 专用内置函数)
       / \
      /   \
     v     v
sksl_frag  sksl_vert    sksl_compute     sksl_public (Runtime Effect)
   |          |              |                  |
   v          v              v                  v
sksl_graphite_frag   sksl_graphite_vert    sksl_rt_shader (私有 RT)
```

每个模块在被加载时，会继承其父模块的所有符号声明，从而形成一个完整的类型和函数声明环境。用户编写的程序代码在编译时将继承对应程序类型的叶子模块。

### IR 节点层次

```
IRNode (所有 IR 节点的基类)
  |
  +-- ProgramElement (顶层程序元素)
  |     +-- FunctionDefinition (函数定义)
  |     +-- FunctionPrototype (函数前向声明)
  |     +-- GlobalVarDeclaration (全局变量声明)
  |     +-- InterfaceBlock (接口块)
  |     +-- StructDefinition (结构体定义)
  |     +-- ModifiersDeclaration (修饰符声明)
  |     +-- Extension (扩展声明)
  |
  +-- Statement (语句)
  |     +-- Block (代码块)
  |     +-- VarDeclaration (变量声明)
  |     +-- ExpressionStatement (表达式语句)
  |     +-- ReturnStatement, BreakStatement, ContinueStatement, DiscardStatement
  |     +-- IfStatement, ForStatement, DoStatement, WhileStatement (尚不存在, 由ForStatement处理)
  |     +-- SwitchStatement / SwitchCase
  |     +-- Nop (空操作)
  |
  +-- Expression (表达式)
  |     +-- Literal (字面量)
  |     +-- VariableReference (变量引用)
  |     +-- BinaryExpression (二元表达式)
  |     +-- PrefixExpression / PostfixExpression (前缀/后缀表达式)
  |     +-- TernaryExpression (三元表达式)
  |     +-- FunctionCall / ChildCall (函数调用)
  |     +-- FieldAccess (字段访问)
  |     +-- IndexExpression (下标访问)
  |     +-- Swizzle (向量分量重排)
  |     +-- Constructor* (各种构造器: Array, Compound, Splat, ScalarCast 等)
  |     +-- Setting (sk_Caps 查询)
  |     +-- TypeReference / FunctionReference / MethodReference
  |
  +-- Symbol (符号)
        +-- Variable (变量)
        +-- FunctionDeclaration (函数声明)
        +-- Type (类型)
        +-- FieldSymbol (字段符号)
```

## 平台特定说明

### GLSL / OpenGL
- `GLSLCodeGenerator` 支持从 GLSL 1.10 到 GLSL 4.50 的多个版本
- 通过 `ShaderCaps` 结构体查询具体 GPU 驱动的能力和限制
- 支持 framebuffer-fetch 扩展（`fFragColorIsInOut`）
- ES2 严格模式下限制循环必须可展开，不支持位运算

### SPIR-V / Vulkan
- `SPIRVCodeGenerator` 直接产出 SPIR-V 二进制字节码
- 支持 Vulkan push constant 语法（`fUseVulkanPushConstantsForGaneshRTAdjust`）
- 可选的 SPIR-V 验证（`SkSLSPIRVValidator`）
- 原子操作使用 relaxed 内存语义，memory scope 根据变量位置（buffer block 或 workgroup）分别为 Device 或 Workgroup

### Metal / Apple
- `MetalCodeGenerator` 将 SkSL 转换为 MSL (Metal Shading Language)
- Metal 中 `half` 类型是真正的 16 位浮点数（而非 GLSL 中的别名）
- 三分量向量在 Metal 布局中占用 4 个分量的空间
- workgroupBarrier 映射为 `threadgroup_barrier(mem_flags::mem_threadgroup)`

### HLSL / Direct3D
- `HLSLCodeGenerator` 通过 SPIR-V 作为中间格式，再使用 spirv-cross 转换为 HLSL
- `SkSLSPIRVtoHLSL.cpp` 封装了 SPIR-V -> HLSL 的转换流程

### WGSL / WebGPU
- `WGSLCodeGenerator` 生成 WebGPU Shading Language 代码
- 支持专门的 WGSL 内存布局计算（uniform 和 storage 地址空间的不同对齐规则）
- WGSL 不支持 bool 类型作为 host-shareable 数据
- 可选的 WGSL 验证（`SkSLWGSLValidator`）

### Raster Pipeline
- `RasterPipelineCodeGenerator` 将 SkSL 编译为 Skia 的 Raster Pipeline 操作序列
- `RasterPipelineBuilder` 构建具体的光栅化管线操作
- 用于 CPU 端的软件渲染，不依赖 GPU 硬件

### Graphite 后端
- `sksl_graphite_frag.sksl` 和 `sksl_graphite_vert.sksl` 提供了 Graphite 特有的内置声明
- Graphite 模块较为庞大（分别约 85KB 和 60KB），包含大量预定义的着色器片段
- 通过 `SkSLGraphiteModules.h/.cpp` 管理 Graphite 特有模块的加载

## 相关文档与参考

### 内部文档
- [src/sksl/README.md](../../../../src/sksl/README.md) - SkSL 语言规范和与 GLSL 的差异说明
- [模块系统设计文档](https://docs.google.com/document/d/1P8LkkimNr-nPlxMimUsz3K_7qMM7-tZOxDCWZejPcWg) - SkSL 模块架构的详细设计
- `lex/sksl.lex` - SkSL 词法规则文件

### 外部参考
- [OpenGL Shading Language 规范](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.50.pdf) - GLSL 4.50 规范
- [SPIR-V 规范](https://registry.khronos.org/SPIR-V/specs/unified1/SPIRV.html) - SPIR-V 中间语言规范
- [Metal Shading Language 规范](https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf) - Apple MSL 规范
- [WGSL 规范](https://www.w3.org/TR/WGSL/) - WebGPU Shading Language 规范
- [Skia 官方文档](https://skia.org/) - Skia 图形库官方网站
- [GL_KHR_memory_scope_semantics](https://github.com/KhronosGroup/GLSL/blob/master/extensions/khr/GL_KHR_memory_scope_semantics.txt) - GLSL 内存作用域语义扩展
