# Blend

> 源文件: src/gpu/Blend.h, src/gpu/Blend.cpp

## 概述

`Blend` 模块是 Skia GPU 后端的核心混合(blending)系统实现,负责处理图形渲染中的颜色混合操作。该模块定义了 GPU 硬件级别的混合方程、混合系数以及混合配置信息,为不同的 Porter-Duff 混合模式和高级混合模式提供底层支持。它将高层的 `SkBlendMode` 转换为 GPU 可以直接执行的混合参数,是连接 Skia 混合语义和 GPU 硬件混合能力的关键桥梁。

该模块提供了从基本的 Porter-Duff 混合到 SVG/PDF 高级混合模式的完整支持,并通过优化的查找表和辅助函数简化了着色器代码的生成。

## 架构位置

在 Skia 的架构中,`Blend` 模块位于 GPU 抽象层 (`src/gpu`) 中,处于以下位置:

- **上游依赖**: 接收来自 `SkBlendMode` (Skia 公共 API) 的混合模式请求
- **同级模块**: 与 `BlendFormula` 协作进行混合配置的优化和计算
- **下游使用**: 为 Ganesh 和 Graphite 等 GPU 后端提供混合配置
- **硬件抽象**: 作为 Skia 混合语义到 GPU 硬件混合功能的转换层

该模块是跨平台的,不依赖特定的 GPU API (如 OpenGL、Vulkan、Metal),提供通用的混合抽象。

## 主要类与结构体

### BlendEquation (枚举)
GPU 混合方程的类型定义。

| 成员 | 说明 |
|------|------|
| `kAdd` | 基本加法混合: Cs*S + Cd*D |
| `kSubtract` | 减法混合: Cs*S - Cd*D |
| `kReverseSubtract` | 反向减法混合: Cd*D - Cs*S |
| `kScreen` ~ `kHSLLuminosity` | SVG/PDF 高级混合方程 (15种) |
| `kIllegal` | 非法值标记 |

**设计说明**: 包含基本混合方程和高级混合方程,其中高级混合对应 SVG 规范中的混合模式。

### BlendCoeff (枚举)
混合系数类型定义,用于控制源色和目标色的权重。

| 成员 | 说明 |
|------|------|
| `kZero` / `kOne` | 常量 0 和 1 |
| `kSC` / `kISC` | 源颜色 / 源颜色的反色 |
| `kDC` / `kIDC` | 目标颜色 / 目标颜色的反色 |
| `kSA` / `kISA` | 源 alpha / 源 alpha 的反色 |
| `kDA` / `kIDA` | 目标 alpha / 目标 alpha 的反色 |
| `kConstC` / `kIConstC` | 常量颜色 / 常量颜色的反色 |
| `kS2C` / `kIS2C` | 第二源颜色 / 反色 (双源混合) |
| `kS2A` / `kIS2A` | 第二源 alpha / 反色 |

**设计说明**: 支持双源混合(dual-source blending),可实现更复杂的混合效果。

### BlendInfo (结构体)
完整的混合配置信息。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fEquation` | `BlendEquation` | 混合方程类型 |
| `fSrcBlend` | `BlendCoeff` | 源混合系数 |
| `fDstBlend` | `BlendCoeff` | 目标混合系数 |
| `fBlendConstant` | `SkPMColor4f` | 混合常量颜色 |
| `fWritesColor` | `bool` | 是否写入颜色缓冲区 |

**继承关系**: 无继承,纯数据结构。

### ReducedBlendModeInfo (结构体)
优化后的混合模式信息,用于减少着色器函数的数量。

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fFunction` | `const char*` | SkSL 内置混合函数名 |
| `fUniformData` | `SkSpan<const float>` | 函数参数的统一数据 |

**设计说明**: 通过参数化的混合函数减少着色器变体数量,例如所有 Porter-Duff 模式共用 `blend_porter_duff` 函数。

## 公共 API 函数

### BlendFuncName
```cpp
const char* BlendFuncName(SkBlendMode mode)
```
**功能**: 返回给定 `SkBlendMode` 对应的 SkSL 内置混合函数名称。

**参数**:
- `mode`: Skia 混合模式枚举

**返回值**: SkSL 函数名字符串,如 "blend_src_over", "blend_multiply" 等。

### GetPorterDuffBlendConstants
```cpp
SkSpan<const float> GetPorterDuffBlendConstants(SkBlendMode mode)
```
**功能**: 获取 Porter-Duff 混合模式的常量参数(4个浮点数)。

**参数**:
- `mode`: Skia 混合模式

**返回值**:
- 如果是 Porter-Duff 模式,返回包含4个浮点数的 span
- 否则返回空 span

**用途**: 用于 `blend_porter_duff` 函数的参数,实现12种 Porter-Duff 模式的统一化处理。

### GetReducedBlendModeInfo
```cpp
ReducedBlendModeInfo GetReducedBlendModeInfo(SkBlendMode mode)
```
**功能**: 获取优化后的混合模式信息,包括函数名和参数数据。

**特性**:
- 将多个相似的混合模式归约到同一函数
- 例如 `kHue`/`kSaturation`/`kColor`/`kLuminosity` 共用 `blend_hslc` 函数
- `kOverlay` 和 `kHardLight` 共用 `blend_overlay` 函数

### 辅助函数 (constexpr)

| 函数名 | 功能 |
|--------|------|
| `BlendCoeffRefsSrc()` | 判断系数是否引用源颜色 |
| `BlendCoeffRefsDst()` | 判断系数是否引用目标颜色 |
| `BlendCoeffRefsSrc2()` | 判断系数是否引用第二源 (双源混合) |
| `BlendCoeffsUseSrcColor()` | 判断混合是否使用源颜色 |
| `BlendCoeffsUseDstColor()` | 判断混合是否使用目标颜色 |
| `BlendEquationIsAdvanced()` | 判断是否为高级混合方程 |
| `BlendModifiesDst()` | 判断混合是否修改目标 |
| `BlendCoeffRefsConstant()` | 判断系数是否引用常量 |
| `BlendShouldDisable()` | 判断是否应禁用混合 (优化为直接写入) |
| `BlendAllowsCoverageAsAlpha()` | 判断是否允许将覆盖率作为 alpha 处理 |

这些 `constexpr` 函数在编译时求值,用于优化混合配置的计算。

## 内部实现细节

### 混合函数名映射
`BlendFuncName()` 使用 switch-case 实现从 `SkBlendMode` 到 SkSL 函数名的直接映射,所有29种混合模式都有对应的 SkSL 内置函数。

### Porter-Duff 常量设计
Porter-Duff 混合的常量是4个浮点数 `[a, b, c, d]`,用于以下公式:
```
result = a * src + b * dst + c * src.a * dst + d * dst.a * src
```
这种参数化设计使得12种 Porter-Duff 模式可以用单个着色器函数实现。

### 归约混合模式
`GetReducedBlendModeInfo()` 实现了以下归约策略:
- **Porter-Duff 组**: 9种模式 → `blend_porter_duff` + 参数
- **HSLC 组**: 4种色调混合 → `blend_hslc` + 参数
- **Overlay 组**: 2种 → `blend_overlay` + 参数
- **Darken 组**: 2种 → `blend_darken` + 参数

### 调试支持
在 `SK_DEBUG` 模式下,提供了 `BlendInfo::dump()` 函数用于调试输出混合配置的详细信息。

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkBlendMode.h` | `SkBlendMode` 枚举 | 混合模式定义 |
| `include/core/SkSpan.h` | `SkSpan<T>` | 数据视图 |
| `src/core/SkColorData.h` | `SkPMColor4f` | 预乘颜色类型 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| `BlendFormula` | `BlendEquation`, `BlendCoeff` | 构建混合公式 |
| Ganesh 后端 | `BlendInfo`, 辅助函数 | 配置硬件混合状态 |
| Graphite 后端 | 混合函数名、常量 | 生成渲染管线 |
| GLSL 代码生成器 | `GetReducedBlendModeInfo()` | 着色器代码生成 |

## 设计模式与设计决策

### 1. 枚举抽象模式
使用枚举类型 (`BlendEquation`, `BlendCoeff`) 而非直接使用 GPU API 的常量,实现跨平台抽象。这使得代码可以在 OpenGL、Vulkan、Metal 等不同后端之间共享。

### 2. 常量表达式优化
大量使用 `constexpr` 函数和 `static constexpr` 数据,使得混合配置的计算可以在编译时完成,减少运行时开销。

### 3. 归约设计模式
通过参数化函数减少着色器变体:
- 29种混合模式 → 约15个实际函数
- 减少编译时间和内存占用
- 简化着色器缓存管理

### 4. 数据驱动设计
Porter-Duff 常量使用静态数组存储,查询操作为 O(1) 时间复杂度。

### 5. 防御性编程
- 使用 `SkUNREACHABLE` 标记不应到达的代码路径
- 在调试模式下提供详细的诊断信息

## 性能考量

### 1. 编译时计算
- 所有辅助判断函数都是 `constexpr`,在编译时求值
- Porter-Duff 常量是 `static constexpr`,无运行时初始化开销

### 2. 内存效率
- `BlendInfo` 结构体设计紧凑,仅包含必要字段
- 使用 `SkSpan` 避免数据拷贝

### 3. 查找优化
- `BlendFuncName()` 使用 switch-case,编译器会优化为跳转表
- `GetPorterDuffBlendConstants()` 对非 Porter-Duff 模式快速返回空

### 4. 缓存友好
- 枚举和常量数据紧密排列
- 避免虚函数调用和动态分配

### 5. 混合优化
`BlendShouldDisable()` 识别可以禁用硬件混合的情况 (如源混合模式),直接写入颜色缓冲区以提升性能。

### 6. 覆盖率优化
`BlendAllowsCoverageAsAlpha()` 识别可以将覆盖率融入 alpha 通道的混合模式,避免双源混合,在不支持该特性的 GPU 上提升性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/BlendFormula.h/cpp` | 协作 | 基于 `Blend` 构建完整混合公式 |
| `src/gpu/Blend.h` | 定义 | 混合抽象的头文件 |
| `src/gpu/Blend.cpp` | 实现 | 混合函数的实现 |
| `include/core/SkBlendMode.h` | 依赖 | 上层混合模式定义 |
| `src/ganesh/glsl/GrGLSLBlend.cpp` | 使用者 | Ganesh GLSL 混合实现 |
| `src/core/SkBlurEngine.h` | 间接使用 | 模糊效果中的混合应用 |

**备注**: 该模块是 GPU 渲染管线中混合阶段的核心抽象,所有需要混合操作的渲染路径都会间接使用此模块。
