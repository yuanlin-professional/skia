# GLSL.std.450.h — GLSL 标准扩展指令集

> 源文件：[`src/sksl/GLSL.std.450.h`](../../src/sksl/GLSL.std.450.h)

## 概述

GLSL.std.450.h 是由 Khronos Group 自动生成的头文件，定义了 SPIR-V 中 GLSL 标准 450 扩展指令集的所有操作码。这些扩展指令对应 GLSL 中的内建数学函数和向量/矩阵操作函数，在 SPIR-V 中通过 `OpExtInst` 指令引用。

该文件 131 行，包含一个枚举定义和版本信息常量。

## 架构位置

```
SPIR-V 指令集
  ├── 核心指令 (spirv.h) — SpvOp 枚举
  └── 扩展指令集
        └── GLSL.std.450 (本文件) — 数学内建函数
```

在 SPIR-V 代码生成中，当 SkSL 程序调用内建数学函数（如 `sin`、`sqrt`、`clamp` 等）时，SkSL 的 SPIR-V 代码生成器会使用此文件中的常量生成对应的 `OpExtInst` 指令。

## 主要类与结构体

### 版本常量

```cpp
static const int GLSLstd450Version = 100;
static const int GLSLstd450Revision = 3;
```

### `GLSLstd450` 枚举

包含 82 个扩展指令操作码，按功能分组：

**取整与绝对值函数（1-10）**：
- `Round`, `RoundEven`, `Trunc`, `FAbs`, `SAbs`, `FSign`, `SSign`, `Floor`, `Ceil`, `Fract`

**三角函数（11-25）**：
- `Radians`, `Degrees`, `Sin`, `Cos`, `Tan`, `Asin`, `Acos`, `Atan`
- `Sinh`, `Cosh`, `Tanh`, `Asinh`, `Acosh`, `Atanh`, `Atan2`

**指数与对数函数（26-32）**：
- `Pow`, `Exp`, `Log`, `Exp2`, `Log2`, `Sqrt`, `InverseSqrt`

**矩阵函数（33-34）**：
- `Determinant`, `MatrixInverse`

**通用数学函数（35-53）**：
- `Modf`, `ModfStruct`, `FMin`, `UMin`, `SMin`, `FMax`, `UMax`, `SMax`
- `FClamp`, `UClamp`, `SClamp`, `FMix`, `Step`, `SmoothStep`
- `Fma`, `Frexp`, `FrexpStruct`, `Ldexp`

**打包/解包函数（54-65）**：
- `PackSnorm4x8`, `PackUnorm4x8`, `PackSnorm2x16`, `PackUnorm2x16`, `PackHalf2x16`, `PackDouble2x32`
- 对应的 `Unpack*` 系列

**几何函数（66-72）**：
- `Length`, `Distance`, `Cross`, `Normalize`, `FaceForward`, `Reflect`, `Refract`

**位操作函数（73-75）**：
- `FindILsb`, `FindSMsb`, `FindUMsb`

**插值函数（76-78）**：
- `InterpolateAtCentroid`, `InterpolateAtSample`, `InterpolateAtOffset`

**NaN 安全函数（79-81）**：
- `NMin`, `NMax`, `NClamp`

## 公共 API 函数

本文件不包含函数定义，仅定义枚举常量。

## 内部实现细节

### 有符号/无符号/浮点变体

多个函数提供了按类型区分的变体：
- `FAbs` / `SAbs` — 浮点/有符号整数绝对值
- `FMin` / `UMin` / `SMin` — 浮点/无符号/有符号最小值
- `FMax` / `UMax` / `SMax` — 浮点/无符号/有符号最大值
- `FClamp` / `UClamp` / `SClamp` — 浮点/无符号/有符号钳位

### Modf/Frexp 的双版本

- `Modf` / `Frexp` — 第二个操作数需要 `OpVariable` 来写入输出
- `ModfStruct` / `FrexpStruct` — 不需要 `OpVariable`，通过结构体返回

### 保留操作码

`GLSLstd450IMix = 47` 标记为 Reserved（保留），SkSL 不应使用此操作码。

### 哨兵值

- `GLSLstd450Bad = 0` — 标记为 "Don't use"，用于表示无效操作码
- `GLSLstd450Count` — 枚举结束标记，用于获取操作码数量

## 依赖关系

本文件无外部依赖，是自包含的纯 C 头文件。

## 设计模式与设计决策

- **自动生成**：与 `spirv.h` 一样，由 Khronos 工具链自动生成，Skia 不应修改。
- **枚举值映射**：枚举值直接对应 SPIR-V 二进制中 `OpExtInst` 指令的立即数操作数。
- **分组设计**：相关函数使用连续的枚举值，便于范围检查和批量处理。

## 性能考量

作为纯常量定义，不涉及运行时性能。这些常量在 SkSL 编译时用于生成 SPIR-V `OpExtInst` 指令，选择正确的扩展指令操作码。

## 相关文件

- `src/sksl/spirv.h` — SPIR-V 核心指令和类型定义
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp` — SPIR-V 代码生成器（使用这些常量生成 `OpExtInst`）
