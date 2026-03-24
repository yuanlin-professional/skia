# SkSL Codegen - 着色器语言代码生成后端

## 概述

`src/sksl/codegen` 目录是 Skia 图形库中 SkSL (Skia Shading Language) 编译器的代码生成模块。该模块负责将 SkSL 编译器前端生成的中间表示 (IR) 程序转换为各种目标平台的原生着色器代码。这是 SkSL 编译器管道的最后阶段，直接决定了着色器程序在不同 GPU 后端上的执行方式。

代码生成后端支持多种目标语言和格式，包括 GLSL（用于 OpenGL/OpenGL ES）、Metal Shading Language（用于 Apple 平台）、SPIR-V（用于 Vulkan）、WGSL（用于 WebGPU/Dawn）、HLSL（用于 Direct3D）以及 Raster Pipeline（用于 CPU 软件渲染）。每种后端都实现了从 SkSL IR 到目标代码的完整转换逻辑，处理类型映射、内置函数翻译、流程控制结构转换等复杂任务。

该模块的设计遵循策略模式，通过 `CodeGenerator` 基类定义统一的代码生成接口，各后端实现类负责具体的代码输出。此外，`PipelineStageCodeGenerator` 提供了一种特殊的代码生成路径，用于将 SkSL 程序转换为可以嵌入到 Skia 渲染管线中的片段处理器代码。`RasterPipelineCodeGenerator` 则将 SkSL 编译为 Skia 的光栅化管道操作序列，使着色器可以在 CPU 上高效执行。

代码生成后端还包含验证器组件（`SkSLSPIRVValidator` 和 `SkSLWGSLValidator`），用于在开发和调试阶段验证生成代码的正确性。HLSL 后端的实现采用了独特的两阶段方案：先生成 SPIR-V，再通过 SPIRV-Cross 库转换为 HLSL，复用了成熟的跨编译基础设施。

## 架构图

```
                          SkSL IR (Program)
                               |
                    +----------+----------+
                    |                     |
              CodeGenerator           独立函数接口
              (基类,已弃用)          (ToGLSL/ToMetal/...)
                    |                     |
    +-------+-------+-------+-------+-----+-------+--------+
    |       |       |       |       |     |       |        |
  GLSL   Metal   SPIRV    WGSL   HLSL  Pipeline  Raster   验证器
  Code   Code    Code     Code   Code   Stage    Pipeline
  Gen    Gen     Gen      Gen    Gen    CodeGen  CodeGen
    |       |       |       |       |     |       |        |
    v       v       v       v       |     v       v        v
  .glsl   .metal  SPIR-V  .wgsl    |   回调接口  RP::     SPIRV/
  文本     文本    二进制   文本     |   (Callbacks) Program  WGSL
                    |               |             |        验证
                    +----> SPIRVtoHLSL            |
                           |                      v
                           v              SkRasterPipeline
                         .hlsl                 Stages
                          文本

  NativeShader 统一输出结构:
  +---------------------------+
  | fText: std::string        |  <- GLSL/Metal/WGSL/HLSL
  | fBinary: vector<uint32_t> |  <- SPIR-V
  +---------------------------+
```

## 目录结构

```
src/sksl/codegen/
|-- BUILD.bazel                           # Bazel 构建配置，定义各后端库目标
|-- SkSLCodeGenerator.h                   # 代码生成器基类定义
|-- SkSLCodeGenTypes.h                    # 代码生成相关类型定义（PrettyPrint, SPIRV ReservedId）
|-- SkSLNativeShader.h                    # 原生着色器输出统一结构体
|
|-- SkSLGLSLCodeGenerator.h              # GLSL 代码生成器公共接口
|-- SkSLGLSLCodeGenerator.cpp            # GLSL 代码生成器实现 (~77KB)
|
|-- SkSLMetalCodeGenerator.h             # Metal 代码生成器公共接口
|-- SkSLMetalCodeGenerator.cpp           # Metal 代码生成器实现 (~148KB)
|
|-- SkSLSPIRVCodeGenerator.h             # SPIR-V 代码生成器公共接口
|-- SkSLSPIRVCodeGenerator.cpp           # SPIR-V 代码生成器实现 (~261KB，最大文件)
|
|-- SkSLWGSLCodeGenerator.h              # WGSL 代码生成器公共接口
|-- SkSLWGSLCodeGenerator.cpp            # WGSL 代码生成器实现 (~206KB)
|
|-- SkSLHLSLCodeGenerator.h              # HLSL 代码生成器公共接口
|-- SkSLHLSLCodeGenerator.cpp            # HLSL 代码生成器实现（通过 SPIR-V 中转）
|-- SkSLSPIRVtoHLSL.h                    # SPIR-V 到 HLSL 的转换接口
|-- SkSLSPIRVtoHLSL.cpp                  # 使用 SPIRV-Cross 实现 SPIR-V 到 HLSL 的转换
|
|-- SkSLPipelineStageCodeGenerator.h     # 管线阶段代码生成器接口
|-- SkSLPipelineStageCodeGenerator.cpp   # 管线阶段代码生成器实现
|
|-- SkSLRasterPipelineCodeGenerator.h    # 光栅管道代码生成器接口
|-- SkSLRasterPipelineCodeGenerator.cpp  # 光栅管道代码生成器实现 (~161KB)
|-- SkSLRasterPipelineBuilder.h          # 光栅管道指令构建器头文件
|-- SkSLRasterPipelineBuilder.cpp        # 光栅管道指令构建器实现 (~164KB)
|
|-- SkSLSPIRVValidator.h                 # SPIR-V 验证器接口
|-- SkSLSPIRVValidator.cpp               # SPIR-V 验证器实现（依赖 spirv-tools）
|-- SkSLWGSLValidator.h                  # WGSL 验证器接口
|-- SkSLWGSLValidator.cpp                # WGSL 验证器实现（依赖 Dawn/Tint）
```

## 关键类与函数

### CodeGenerator 基类 (`SkSLCodeGenerator.h`)

```cpp
class CodeGenerator {
public:
    CodeGenerator(const Context* context,
                  const ShaderCaps* caps,
                  const Program* program,
                  OutputStream* stream);
    virtual ~CodeGenerator() = default;
    virtual bool generateCode() = 0;  // 纯虚函数，子类必须实现

protected:
    static constexpr float kSharpenTexturesBias = -.475f;  // 纹理锐化偏移量
    const Program& fProgram;    // 要编译的 SkSL 程序
    Context fContext;            // 编译上下文
    const ShaderCaps& fCaps;    // GPU 能力描述
    OutputStream* fOut;          // 输出流
};
```

`CodeGenerator` 是所有文本输出后端的抽象基类。它持有对 SkSL `Program` 的引用、`ShaderCaps` 能力描述以及一个 `OutputStream` 输出流。`AutoOutputStream` 辅助类提供了 RAII 风格的输出流切换机制，支持临时重定向输出并自动恢复缩进级别。

### NativeShader 输出结构 (`SkSLNativeShader.h`)

```cpp
struct NativeShader {
    std::string fText;              // 文本形式输出（GLSL/Metal/WGSL/HLSL）
    std::vector<uint32_t> fBinary;  // 二进制形式输出（SPIR-V）
    bool isBinary() const;          // 判断是否为二进制输出
};
```

`NativeShader` 是统一的代码生成输出容器。大多数后端输出文本（存储在 `fText`），只有 SPIR-V 后端输出二进制数据（存储在 `fBinary`）。

### GLSL 代码生成器 (`SkSLGLSLCodeGenerator.h`)

```cpp
bool ToGLSL(Program& program, const ShaderCaps* caps, OutputStream& out, PrettyPrint);
bool ToGLSL(Program& program, const ShaderCaps* caps, OutputStream& out);
bool ToGLSL(Program& program, const ShaderCaps* caps, NativeShader* out);
```

GLSL 代码生成器将 SkSL 程序转换为 OpenGL 着色语言代码。其实现文件约 77KB，处理了 GLSL 各版本的差异、扩展声明、类型映射（如 SkSL 的 `half` 到 GLSL 的 `float`）、内置函数名称转换等。

### Metal 代码生成器 (`SkSLMetalCodeGenerator.h`)

```cpp
bool ToMetal(Program& program, const ShaderCaps* caps, OutputStream& out, PrettyPrint);
bool ToMetal(Program& program, const ShaderCaps* caps, NativeShader* out);
```

Metal 代码生成器是最大的文本后端之一（~148KB），负责将 SkSL 转换为 Apple Metal Shading Language。Metal 的内存模型和着色器接口与 GLSL 有显著差异，需要大量的结构重组工作。

### SPIR-V 代码生成器 (`SkSLSPIRVCodeGenerator.h`)

```cpp
using ValidateSPIRVProc = bool (*)(ErrorReporter&, SkSpan<const uint32_t>);
bool ToSPIRV(Program& program, const ShaderCaps* caps, OutputStream& out, ValidateSPIRVProc = nullptr);
bool ToSPIRV(Program& program, const ShaderCaps* caps, std::vector<uint32_t>* out, ValidateSPIRVProc = nullptr);
```

SPIR-V 代码生成器是本目录中最大的单个文件（~261KB），直接输出 SPIR-V 二进制字节码。SPIR-V 是 Vulkan 的原生着色器格式，也是 HLSL 后端的中间格式。`ValidateSPIRVProc` 回调函数可选地在生成后验证 SPIR-V 的正确性。`SkSLCodeGenTypes.h` 中定义了 SPIR-V 的保留 ID 枚举（`spirv::ReservedId`），用于标识固定的类型和变量 ID。

### WGSL 代码生成器 (`SkSLWGSLCodeGenerator.h`)

```cpp
enum class IncludeSyntheticCode : bool { kNo = false, kYes = true };
using ValidateWGSLProc = bool (*)(ErrorReporter&, std::string_view wgsl, std::string* warnings);
bool ToWGSL(Program& program, const ShaderCaps* caps, OutputStream& out,
            PrettyPrint, IncludeSyntheticCode, ValidateWGSLProc);
```

WGSL 代码生成器（~206KB）是为 WebGPU 标准设计的后端。`IncludeSyntheticCode` 控制是否包含合成的辅助代码。WGSL 验证器使用 Dawn/Tint 库进行语法和语义验证。

### HLSL 代码生成器 (`SkSLHLSLCodeGenerator.h`)

```cpp
bool ToHLSL(Program& program, const ShaderCaps* caps, OutputStream& out, ValidateSPIRVProc = nullptr);
bool ToHLSL(Program& program, const ShaderCaps* caps, std::string* out, ValidateSPIRVProc);
```

HLSL 后端采用两阶段转换策略：先调用 `ToSPIRV()` 生成 SPIR-V 二进制，再通过 `SPIRVtoHLSL()` 函数（基于 SPIRV-Cross 库）将 SPIR-V 转译为 HLSL。这种复用策略避免了从零编写 HLSL 代码生成器的巨大工作量。

### PipelineStage 代码生成器 (`SkSLPipelineStageCodeGenerator.h`)

```cpp
namespace PipelineStage {
    class Callbacks {
    public:
        virtual std::string declareUniform(const VarDeclaration*) = 0;
        virtual std::string sampleShader(int index, std::string coords) = 0;
        virtual std::string sampleColorFilter(int index, std::string color) = 0;
        virtual std::string sampleBlender(int index, std::string src, std::string dst) = 0;
        virtual void defineFunction(const char* decl, const char* body, bool isMain) = 0;
        // ... 更多回调方法
    };
    void ConvertProgram(const Program& program, const char* sampleCoords,
                        const char* inputColor, const char* destColor, Callbacks* callbacks);
}
```

`PipelineStageCodeGenerator` 不直接输出目标代码，而是通过 `Callbacks` 接口将程序元素传递给调用者。这用于将 SkSL 着色器嵌入到 Skia 的 `GrFragmentProcessor` 体系中，支持 uniform 变量重命名（名称修饰以避免冲突）和子效果采样。

### Raster Pipeline 代码生成器

```cpp
// SkSLRasterPipelineCodeGenerator.h
std::unique_ptr<RP::Program> MakeRasterPipelineProgram(
    const Program& program,
    const FunctionDefinition& function,
    DebugTracePriv* debugTrace = nullptr,
    bool writeTraceOps = false);

// SkSLRasterPipelineBuilder.h - 关键类型
using Slot = int;
struct SlotRange { Slot index; int count; };
struct Instruction { BuilderOp fOp; Slot fSlotA, fSlotB; int fImmA, fImmB, fImmC, fImmD; int fStackID; };

class Program {
    bool appendStages(SkRasterPipeline* pipeline, SkArenaAlloc* alloc,
                      Callbacks* callbacks, SkSpan<const float> uniforms) const;
};

class Builder {
    std::unique_ptr<Program> finish(int numValueSlots, int numUniformSlots,
                                     int numImmutableSlots, DebugTracePriv* debugTrace = nullptr);
    void push_constant_i(int32_t val, int count = 1);
    void label(int labelID);
    void jump(int labelID);
    void branch_if_all_lanes_active(int labelID);
    // ... 大量栈操作和数学运算指令
};
```

Raster Pipeline 后端是 SkSL 最独特的后端，它将着色器编译为 Skia 的 CPU 光栅化管道操作序列。`Builder` 类提供了丰富的指令集，包括栈操作（`push_slots`、`pop`）、条件分支（`branch_if_*`）、数学运算以及子效果调用。`BuilderOp` 枚举是 `ProgramOp` 的超集，包含仅在构建阶段使用的操作（如 `push_clone`、`push_constant`），这些操作在 `Program::makeStages` 阶段被重写为原生 `SkRasterPipelineOp`。

## 依赖关系

```
codegen 模块依赖:
+-------------------------------------------+
| 上游依赖 (codegen 使用的模块)              |
|   - src/sksl/ir/*          SkSL IR 节点   |
|   - src/sksl/SkSLContext   编译上下文      |
|   - src/sksl/SkSLCompiler  编译器核心      |
|   - src/sksl/SkSLAnalysis  程序分析工具    |
|   - src/sksl/SkSLOutputStream  输出流      |
|   - include/gpu/ShaderCaps GPU 能力描述    |
+-------------------------------------------+

+-------------------------------------------+
| 外部库依赖                                 |
|   - spirv-tools      SPIR-V 验证          |
|   - spirv-cross       SPIR-V -> HLSL      |
|   - dawn/tint         WGSL 验证           |
+-------------------------------------------+

+-------------------------------------------+
| 下游使用者 (使用 codegen 的模块)           |
|   - src/gpu/ganesh/gl  Ganesh OpenGL 后端  |
|   - src/gpu/ganesh/mtl Ganesh Metal 后端   |
|   - src/gpu/vk         Vulkan 后端         |
|   - src/gpu/graphite   Graphite 渲染引擎   |
|   - tools/skslc        SkSL 命令行编译器   |
|   - src/core           Raster Pipeline     |
+-------------------------------------------+
```

## 设计模式分析

### 1. 策略模式 (Strategy Pattern)

`CodeGenerator` 基类与各具体后端形成经典的策略模式。不过，新的公共 API 采用了自由函数（`ToGLSL`、`ToMetal` 等）而非虚函数调用，内部实现类对外部用户不可见。这是一种封装更好的策略实现。

### 2. 回调模式 (Callback Pattern)

`PipelineStage::Callbacks` 使用回调接口将代码生成的具体细节委托给调用方。每种程序元素（uniform、函数定义、子效果采样）都有专门的回调方法，允许 `GrFragmentProcessor` 等系统自定义代码的嵌入方式。

### 3. 构建者模式 (Builder Pattern)

`RP::Builder` 是典型的构建者模式实现。它通过一系列方法调用（`push_constant_i`、`label`、`branch_if_*` 等）逐步构建指令序列，最终通过 `finish()` 方法产出不可变的 `RP::Program` 对象。

### 4. RAII 模式

`AutoOutputStream` 类使用 RAII 模式管理输出流的切换和缩进恢复，确保在代码生成过程中不会因异常或提前返回而导致输出流状态不一致。

### 5. 两阶段编译 (Two-Phase Compilation)

HLSL 后端通过 SPIR-V 中转实现代码生成，体现了两阶段编译思想。这种方法利用了已有的 SPIR-V 后端和成熟的 SPIRV-Cross 转译工具，大幅减少了开发和维护成本。

## 数据流

```
输入: SkSL Program (IR 树)
   |
   +---> ShaderCaps 查询 GPU 能力
   |
   +---> 遍历 Program 中的 ProgramElement
   |        |
   |        +---> StructDefinition   -> 输出结构体定义
   |        +---> GlobalVarDecl      -> 输出全局变量/uniform
   |        +---> InterfaceBlock     -> 输出 interface block
   |        +---> FunctionDefinition -> 输出函数定义
   |        +---> Extension          -> 输出扩展声明 (GLSL)
   |
   +---> 遍历 Statement 和 Expression 节点
   |        |
   |        +---> 类型映射: half -> float (GLSL), half -> half (Metal)
   |        +---> 内置函数转换: sample() -> texture() (GLSL 3.3+)
   |        +---> 运算符适配: 矩阵乘法语法差异
   |        +---> 流程控制: for/while/if/switch 语法差异
   |
   +---> 输出目标代码
            |
            +---> 文本后端: 写入 OutputStream -> std::string / NativeShader::fText
            +---> 二进制后端: 写入 vector<uint32_t> -> NativeShader::fBinary
            +---> Raster Pipeline: 构建 RP::Instruction[] -> RP::Program -> SkRasterPipeline
```

### Raster Pipeline 特殊数据流

```
SkSL Program
   |
   v
MakeRasterPipelineProgram()
   |
   v
RP::Builder (逐语句生成指令)
   |
   +---> 变量分配 Slot (值槽位)
   +---> 表达式求值 -> push 到栈
   +---> 控制流 -> 执行掩码管理
   +---> 函数调用 -> Enter/Exit 对
   |
   v
RP::Builder::finish()
   |
   v
RP::Program (指令数组 + 元数据)
   |
   v
RP::Program::appendStages()
   |
   +---> makeStages(): BuilderOp -> ProgramOp -> SkRasterPipelineOp
   +---> 分配 SlotData (值/栈/不可变数据)
   +---> 子效果通过 Callbacks 接口注入
   |
   v
SkRasterPipeline Stages (可直接执行)
```

## 相关文档与参考

- **SkSL 语言规范**: SkSL 是基于 GLSL ES 的着色语言方言，增加了 `half`、`short` 等精度类型以及 `$pure`、`$es3` 等内部注解。
- **Raster Pipeline 设计文档**: [go/sksl-rp](https://docs.google.com/document/d/1GCQeAGVGHubOCbmULVdXUkNiXdw9J4umai_M5X3JGS4) 描述了 SkSL 在光栅管道中的设计。
- **SPIR-V 规范**: [Khronos SPIR-V](https://www.khronos.org/spir/) - SPIR-V 二进制格式的官方规范。
- **WGSL 规范**: [W3C WGSL](https://www.w3.org/TR/WGSL/) - WebGPU 着色语言规范。
- **SPIRV-Cross**: 用于 SPIR-V 到 HLSL 的转译，是 Khronos 维护的开源工具。
- **Dawn/Tint**: Google 的 WebGPU 实现，其中 Tint 编译器用于验证 WGSL 代码。
- **相关目录**:
  - `src/sksl/ir/` - SkSL 中间表示定义
  - `src/sksl/lex/` - SkSL 词法分析器
  - `src/sksl/tracing/` - SkSL 调试追踪
  - `src/sksl/generated/` - 生成的 SkSL 内置模块
  - `include/sksl/` - SkSL 公共 API 头文件
  - `src/gpu/ganesh/` - Ganesh 渲染引擎 GPU 后端
  - `src/gpu/graphite/` - Graphite 新一代渲染引擎
