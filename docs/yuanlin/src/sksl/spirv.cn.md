# spirv.h — SPIR-V 规范常量定义

> 源文件：[`src/sksl/spirv.h`](../../src/sksl/spirv.h)

## 概述

spirv.h 是由 Khronos Group 自动生成的 SPIR-V 规范头文件，定义了 SPIR-V 二进制格式中使用的所有枚举常量和类型。SPIR-V 是 Vulkan 和 OpenCL 使用的中间着色语言表示形式。SkSL 编译器使用此头文件中的常量来生成 SPIR-V 二进制代码。

该文件约 870 行，包含大量枚举定义，涵盖了 SPIR-V 1.0 规范（修订版 4）的完整指令集和类型系统。

## 架构位置

```
SkSL 编译器
  └── SPIR-V 代码生成后端
        ├── spirv.h        — SPIR-V 枚举常量（本文件）
        ├── GLSL.std.450.h — GLSL 扩展指令集
        └── SkSLSPIRVCodeGenerator.cpp — 代码生成器实现
```

此文件是 Khronos Group 官方 SPIR-V 规范的 C 头文件副本，未经 Skia 修改。

## 主要类与结构体

### 基础类型与常量

```cpp
typedef unsigned int SpvId;  // SPIR-V ID 类型

static const unsigned int SpvMagicNumber = 0x07230203;   // SPIR-V 魔数
static const unsigned int SpvVersion = 0x00010000;       // SPIR-V 版本 1.0
static const unsigned int SpvRevision = 4;               // 修订版 4
static const unsigned int SpvOpCodeMask = 0xffff;        // 操作码掩码
static const unsigned int SpvWordCountShift = 16;        // 字数偏移量
```

### 主要枚举类型

| 枚举名 | 说明 |
|--------|------|
| `SpvSourceLanguage` | 源语言标识（Unknown, ESSL, GLSL, OpenCL_C, OpenCL_CPP） |
| `SpvExecutionModel` | 执行模型（Vertex, Fragment, GLCompute, Kernel 等） |
| `SpvAddressingModel` | 寻址模型（Logical, Physical32, Physical64） |
| `SpvMemoryModel` | 内存模型（Simple, GLSL450, OpenCL） |
| `SpvExecutionMode` | 执行模式（各种着色器阶段的配置参数） |
| `SpvStorageClass` | 存储类（UniformConstant, Input, Output, Uniform, Function 等） |
| `SpvDim` | 图像维度（1D, 2D, 3D, Cube, Buffer, SubpassData） |
| `SpvImageFormat` | 图像格式（40 种纹理存储格式） |
| `SpvDecoration` | 装饰（Location, Binding, DescriptorSet, Offset, Block 等） |
| `SpvBuiltIn` | 内建变量（Position, FragCoord, WorkgroupId 等） |
| `SpvCapability` | 能力声明（Shader, Float16, Int64, ImageQuery 等） |
| `SpvOp` | 操作码（约 300 个 SPIR-V 指令） |

### 位掩码枚举

文件中多个枚举成对出现，以 `Shift` 和 `Mask` 后缀区分：
- `SpvImageOperandsShift` / `SpvImageOperandsMask` — 图像操作参数
- `SpvFPFastMathModeShift` / `SpvFPFastMathModeMask` — 浮点快速数学模式
- `SpvSelectionControlShift` / `SpvSelectionControlMask` — 选择控制
- `SpvLoopControlShift` / `SpvLoopControlMask` — 循环控制
- `SpvFunctionControlShift` / `SpvFunctionControlMask` — 函数控制
- `SpvMemorySemanticsShift` / `SpvMemorySemanticsMask` — 内存语义
- `SpvMemoryAccessShift` / `SpvMemoryAccessMask` — 内存访问

## 公共 API 函数

本文件不包含函数定义，仅定义类型和常量。

## 内部实现细节

### SpvOp 操作码枚举

`SpvOp` 是最大的枚举，包含约 300 个操作码，可按功能分类如下：

**类型声明指令**：
- `SpvOpTypeVoid`（19）, `SpvOpTypeBool`（20）, `SpvOpTypeInt`（21）, `SpvOpTypeFloat`（22）
- `SpvOpTypeVector`（23）, `SpvOpTypeMatrix`（24）
- `SpvOpTypeImage`（25）, `SpvOpTypeSampler`（26）, `SpvOpTypeSampledImage`（27）
- `SpvOpTypeArray`（28）, `SpvOpTypeRuntimeArray`（29）, `SpvOpTypeStruct`（30）
- `SpvOpTypePointer`（32）, `SpvOpTypeFunction`（33）

**常量定义指令**：
- `SpvOpConstantTrue`（41）, `SpvOpConstantFalse`（42）, `SpvOpConstant`（43）
- `SpvOpConstantComposite`（44）, `SpvOpConstantNull`（46）
- `SpvOpSpecConstant`（50）, `SpvOpSpecConstantComposite`（51）

**函数操作指令**：
- `SpvOpFunction`（54）— 函数入口
- `SpvOpFunctionParameter`（55）— 函数参数
- `SpvOpFunctionEnd`（56）— 函数结束标记
- `SpvOpFunctionCall`（57）— 函数调用

**内存操作指令**：
- `SpvOpVariable`（59）— 变量声明
- `SpvOpLoad`（61）, `SpvOpStore`（62）— 加载和存储
- `SpvOpAccessChain`（65）— 结构体/数组成员访问
- `SpvOpCopyMemory`（63）, `SpvOpCopyMemorySized`（64）

**算术运算指令**：
- 整数：`SpvOpIAdd`（128）, `SpvOpISub`（130）, `SpvOpIMul`（132）, `SpvOpSDiv`（135）, `SpvOpUDiv`（134）
- 浮点：`SpvOpFAdd`（129）, `SpvOpFSub`（131）, `SpvOpFMul`（133）, `SpvOpFDiv`（136）
- 取模：`SpvOpUMod`（137）, `SpvOpSRem`（138）, `SpvOpFRem`（140）, `SpvOpFMod`（141）
- 向量/矩阵：`SpvOpVectorTimesScalar`（142）, `SpvOpMatrixTimesVector`（145）, `SpvOpMatrixTimesMatrix`（146）, `SpvOpDot`（148）

**逻辑与比较指令**：
- 逻辑：`SpvOpLogicalEqual`（164）, `SpvOpLogicalNotEqual`（165）, `SpvOpLogicalOr`（166）, `SpvOpLogicalAnd`（167）, `SpvOpLogicalNot`（168）
- 整数比较：`SpvOpIEqual`（170）, `SpvOpINotEqual`（171）, `SpvOpSLessThan`（177）, `SpvOpULessThan`（176）
- 浮点比较：`SpvOpFOrdEqual`（180）, `SpvOpFOrdLessThan`（184）, `SpvOpFUnordLessThan`（185）
- 选择：`SpvOpSelect`（169）

**位运算指令**：
- `SpvOpBitwiseOr`（197）, `SpvOpBitwiseXor`（198）, `SpvOpBitwiseAnd`（199）, `SpvOpNot`（200）
- `SpvOpShiftRightLogical`（194）, `SpvOpShiftRightArithmetic`（195）, `SpvOpShiftLeftLogical`（196）
- `SpvOpBitFieldInsert`（201）, `SpvOpBitFieldSExtract`（202）, `SpvOpBitFieldUExtract`（203）

**控制流指令**：
- `SpvOpBranch`（249）— 无条件跳转
- `SpvOpBranchConditional`（250）— 条件跳转
- `SpvOpSwitch`（251）— 多路分支
- `SpvOpReturn`（253）, `SpvOpReturnValue`（254）— 函数返回
- `SpvOpPhi`（245）— SSA phi 节点
- `SpvOpLoopMerge`（246）, `SpvOpSelectionMerge`（247）— 结构化控制流标记
- `SpvOpLabel`（248）— 基本块标签
- `SpvOpKill`（252）— 片段着色器终止

**图像操作指令**：
- 采样：`SpvOpImageSampleImplicitLod`（87）, `SpvOpImageSampleExplicitLod`（88）
- 深度采样：`SpvOpImageSampleDrefImplicitLod`（89）, `SpvOpImageSampleDrefExplicitLod`（90）
- 投影采样：`SpvOpImageSampleProjImplicitLod`（91）
- 聚集：`SpvOpImageGather`（96）, `SpvOpImageDrefGather`（97）
- 读写：`SpvOpImageFetch`（95）, `SpvOpImageRead`（98）, `SpvOpImageWrite`（99）
- 查询：`SpvOpImageQuerySizeLod`（103）, `SpvOpImageQuerySize`（104）, `SpvOpImageQueryLevels`（106）

**原子操作指令**：
- `SpvOpAtomicLoad`（227）, `SpvOpAtomicStore`（228）
- `SpvOpAtomicExchange`（229）, `SpvOpAtomicCompareExchange`（230）
- `SpvOpAtomicIAdd`（234）, `SpvOpAtomicISub`（235）
- `SpvOpAtomicSMin`（236）, `SpvOpAtomicUMin`（237）, `SpvOpAtomicSMax`（238）, `SpvOpAtomicUMax`（239）

**导数指令**：
- 标准导数：`SpvOpDPdx`（207）, `SpvOpDPdy`（208）, `SpvOpFwidth`（209）
- 精细导数：`SpvOpDPdxFine`（210）, `SpvOpDPdyFine`（211）
- 粗略导数：`SpvOpDPdxCoarse`（213）, `SpvOpDPdyCoarse`（214）

### SPIR-V 二进制格式

SPIR-V 指令使用固定格式：每个指令的第一个字（32 位）的高 16 位是字数，低 16 位是操作码。这由 `SpvWordCountShift`（16）和 `SpvOpCodeMask`（0xffff）常量支持。

SPIR-V 模块的二进制布局以魔数 `0x07230203`（`SpvMagicNumber`）开头，后续依次是版本号、生成器信息、ID 上界、保留字、以及指令流。

### 存储类详解

`SpvStorageClass` 枚举定义了 SPIR-V 变量的存储位置：

| 存储类 | 值 | 说明 |
|-------|---|------|
| `UniformConstant` | 0 | 只读的 uniform 数据（纹理、采样器） |
| `Input` | 1 | 着色器阶段输入变量 |
| `Uniform` | 2 | Uniform 缓冲区中的数据 |
| `Output` | 3 | 着色器阶段输出变量 |
| `Workgroup` | 4 | 工作组共享内存（compute shader） |
| `Private` | 6 | 调用私有存储 |
| `Function` | 7 | 函数局部变量 |
| `PushConstant` | 9 | Vulkan push constants |

### 装饰详解

`SpvDecoration` 枚举中 SkSL 最常使用的装饰包括：

- `SpvDecorationLocation`（30）— 输入/输出变量的位置
- `SpvDecorationBinding`（33）— 描述符绑定编号
- `SpvDecorationDescriptorSet`（34）— 描述符集编号
- `SpvDecorationOffset`（35）— 结构体成员偏移
- `SpvDecorationBlock`（2）— 标记 uniform 块
- `SpvDecorationBufferBlock`（3）— 标记 storage 块
- `SpvDecorationRelaxedPrecision`（0）— 放松精度修饰
- `SpvDecorationFlat`（14）— 平坦插值
- `SpvDecorationBuiltIn`（11）— 标记内建变量

## 依赖关系

本文件无外部依赖，是自包含的纯 C 头文件。

## 设计模式与设计决策

- **自动生成**：此文件由 Khronos 工具链自动生成，确保与 SPIR-V 规范完全一致。Skia 不应修改此文件。
- **C 风格枚举**：使用 `typedef enum` 而非 C++ `enum class`，保持与 C 语言的兼容性。这允许在 C 和 C++ 项目中共享相同的头文件。
- **`Spv` 前缀**：所有常量使用 `Spv` 前缀避免命名冲突。由于使用了 C 风格枚举（非 `enum class`），前缀是必要的命名空间替代方案。
- **Shift/Mask 分离**：位掩码枚举提供移位值和掩码值两个版本，便于组合使用。例如可以通过 `1 << SpvImageOperandsBiasShift` 或直接使用 `SpvImageOperandsBiasMask` 来设置位标志。
- **有符号/无符号分离**：算术指令区分有符号和无符号操作（如 `SpvOpSDiv` vs `SpvOpUDiv`），因为 SPIR-V 在类型系统层面不区分有符号和无符号整数。
- **有序/无序浮点比较**：浮点比较指令区分有序（`FOrd*`）和无序（`FUnord*`）版本，对应 IEEE 754 中 NaN 的不同处理方式。

## 性能考量

作为纯常量定义头文件，不涉及运行时性能问题。所有常量在编译时解析，用于 SPIR-V 代码生成阶段。

SPIR-V 版本为 1.0（`SPV_VERSION 0x10000`），这是 Vulkan 1.0 所要求的最低版本，确保了最广泛的兼容性。更高版本的 SPIR-V 功能（如子组操作）如果需要，应通过 SPIR-V 扩展机制引入。

此文件通过 `#include` 被 SkSL 的 SPIR-V 代码生成器包含。由于文件中只有枚举和 `static const` 常量，不会增加目标文件的数据段大小（编译器会在使用点内联这些常量值）。

## 相关文件

- `src/sksl/GLSL.std.450.h` — GLSL 标准扩展指令集枚举
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.h` — SPIR-V 代码生成器头文件
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp` — SPIR-V 代码生成器实现
- `src/gpu/ganesh/vk/GrVkCaps.cpp` — Vulkan 能力查询（影响 SPIR-V 功能选择）
