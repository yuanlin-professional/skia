# BlendFormula

> 源文件: src/gpu/BlendFormula.h, src/gpu/BlendFormula.cpp

## 概述

`BlendFormula` 是 Skia GPU 渲染中负责处理 Porter-Duff 混合模式的核心模块,它将着色器输出和硬件混合状态进行优化组合,以实现带覆盖率(coverage)的混合效果。该模块的主要目标是在支持有限混合能力的 GPU 硬件上,通过巧妙的着色器输出和硬件混合状态的组合,正确实现各种 Porter-Duff 混合模式,同时考虑部分覆盖(antialiasing)和 LCD 文本渲染的特殊需求。

核心设计思想是:当源像素具有覆盖率 `f` 时,混合公式从标准的 `D' = S*srcCoeff + D*dstCoeff` 变为 `D' = f*(S*srcCoeff + D*dstCoeff) + (1-f)*D`,需要通过调整着色器输出和混合系数来实现这个数学等式。

## 架构位置

在 Skia 架构中,`BlendFormula` 位于以下位置:

- **上游依赖**: 依赖 `Blend.h` 提供的混合方程和系数定义
- **同级协作**: 与 GPU 管线状态管理器协作配置硬件
- **下游使用**: 被 Ganesh 和 Graphite 的渲染管线使用
- **特化场景**: 为抗锯齿渲染和 LCD 文本渲染提供专门的混合策略

该模块是 GPU 渲染管线中混合阶段的策略制定者,负责将高层的混合语义转化为具体的硬件配置。

## 主要类与结构体

### BlendFormula 类

Porter-Duff 混合公式的封装类,包含着色器输出类型和硬件混合状态。

**继承关系**: 无继承,独立类。

**关键成员变量**:

| 成员变量 | 类型 | 位宽 | 说明 |
|----------|------|------|------|
| `fPrimaryOutputType` | `OutputType` | 4 bits | 主输出类型 |
| `fSecondaryOutputType` | `OutputType` | 4 bits | 辅助输出类型(双源混合) |
| `fBlendEquation` | `uint32_t` | 6 bits | 混合方程 |
| `fSrcCoeff` | `uint32_t` | 6 bits | 源混合系数 |
| `fDstCoeff` | `uint32_t` | 6 bits | 目标混合系数 |
| `fProps` | `Properties` | 6 bits | 预计算的属性标志 |

**设计说明**: 使用位域压缩,整个结构体仅占4字节,优化内存和缓存效率。

### OutputType 枚举

着色器输出类型定义,所有输出都经过覆盖率调制。

| 枚举值 | 说明 |
|--------|------|
| `kNone_OutputType` | 无输出 (0) |
| `kCoverage_OutputType` | 输出覆盖率 `f` |
| `kModulate_OutputType` | 输出 `inputColor * f` |
| `kSAModulate_OutputType` | 输出 `inputColor.a * f` |
| `kISAModulate_OutputType` | 输出 `(1 - inputColor.a) * f` |
| `kISCModulate_OutputType` | 输出 `(1 - inputColor) * f` |

### Properties 枚举

BlendFormula 的预计算属性标志。

| 属性 | 说明 |
|------|------|
| `kModifiesDst_Property` | 是否修改目标缓冲区 |
| `kUnaffectedByDst_Property` | 是否不受目标值影响 |
| `kUnaffectedByDstIfOpaque_Property` | 当源不透明时是否不受目标影响 |
| `kUsesInputColor_Property` | 是否使用输入颜色 |
| `kCanTweakAlphaForCoverage_Property` | 是否可以调整 alpha 来处理覆盖率 |

## 公共 API 函数

### 构造函数
```cpp
constexpr BlendFormula(OutputType primaryOut,
                       OutputType secondaryOut,
                       skgpu::BlendEquation equation,
                       skgpu::BlendCoeff srcCoeff,
                       skgpu::BlendCoeff dstCoeff)
```
**功能**: 构造混合公式,并在编译时计算属性标志。
**特性**: `constexpr` 构造函数,支持编译时常量表的构建。

### 查询函数

#### hasSecondaryOutput
```cpp
bool hasSecondaryOutput() const
```
**返回**: 是否需要双源混合输出。

#### modifiesDst
```cpp
bool modifiesDst() const
```
**返回**: 混合操作是否会修改目标缓冲区。

#### unaffectedByDst
```cpp
bool unaffectedByDst() const
```
**返回**: 结果是否不受目标值影响(如 `kSrc` 模式)。

#### unaffectedByDstIfOpaque
```cpp
bool unaffectedByDstIfOpaque() const
```
**返回**: 当源不透明时是否不受目标影响。

#### usesInputColor
```cpp
bool usesInputColor() const
```
**返回**: 是否需要输入颜色(优化:可跳过颜色计算)。

#### canTweakAlphaForCoverage
```cpp
bool canTweakAlphaForCoverage() const
```
**返回**: 是否可以通过调整 alpha 值来处理覆盖率(避免修改着色器)。

### 访问器函数

| 函数 | 返回类型 | 说明 |
|------|----------|------|
| `equation()` | `BlendEquation` | 获取混合方程 |
| `srcCoeff()` | `BlendCoeff` | 获取源系数 |
| `dstCoeff()` | `BlendCoeff` | 获取目标系数 |
| `primaryOutput()` | `OutputType` | 获取主输出类型 |
| `secondaryOutput()` | `OutputType` | 获取辅助输出类型 |

### 全局查找函数

#### GetBlendFormula
```cpp
BlendFormula GetBlendFormula(bool isOpaque, bool hasCoverage, SkBlendMode xfermode)
```
**功能**: 根据源不透明性、覆盖率和混合模式获取最优的混合公式。
**参数**:
- `isOpaque`: 源颜色是否不透明
- `hasCoverage`: 是否有覆盖率(抗锯齿)
- `xfermode`: 混合模式
**返回**: 优化后的 `BlendFormula`。

#### GetLCDBlendFormula
```cpp
BlendFormula GetLCDBlendFormula(SkBlendMode xfermode)
```
**功能**: 获取 LCD 文本渲染专用的混合公式。
**参数**: `xfermode` - 混合模式。
**返回**: LCD 优化的 `BlendFormula`。

## 内部实现细节

### 混合表设计
使用4维编译时常量数组 `gBlendTable[opaque][coverage][mode]`:
- 维度1: 源是否不透明 (2种)
- 维度2: 是否有覆盖率 (2种)
- 维度3: 混合模式 (15种 Porter-Duff 模式)

总共 2×2×15 = 60 个预计算的公式,所有计算在编译时完成。

### 辅助构造函数

#### MakeCoeffFormula
```cpp
constexpr BlendFormula MakeCoeffFormula(BlendCoeff srcCoeff, BlendCoeff dstCoeff)
```
**用途**: 标准 Porter-Duff 公式,用于无覆盖率或可调整 alpha 的情况。
**优化**: 当系数为 `(Zero, Zero)` 或 `(Zero, One)` 时,设置主输出为 `kNone`。

#### MakeCoverageFormula
```cpp
constexpr BlendFormula MakeCoverageFormula(OutputType oneMinusDstCoeffModulateOutput,
                                           BlendCoeff srcCoeff)
```
**用途**: 处理带覆盖率的混合,通过辅助输出 `f*(1-dstCoeff)` 实现。
**数学**: `D' = f*S*srcCoeff + D*(1 - f*(1-dstCoeff))`。
**实现**: 目标系数使用 `kIS2C`,从辅助输出读取。

#### MakeCoverageSrcCoeffZeroFormula
```cpp
constexpr BlendFormula MakeCoverageSrcCoeffZeroFormula(OutputType oneMinusDstCoeffModulateOutput)
```
**用途**: 当源系数为零时的特殊优化。
**数学**: `D' = D - D*[f*(1-dstCoeff)]`。
**实现**: 使用反向减法方程 `kReverseSubtract` 和系数 `(DC, One)`。

#### MakeCoverageDstCoeffZeroFormula
```cpp
constexpr BlendFormula MakeCoverageDstCoeffZeroFormula(BlendCoeff srcCoeff)
```
**用途**: 当目标系数为零时的优化。
**数学**: `D' = f*S*srcCoeff + (1-f)*D`。
**实现**: 辅助输出为 `f`,目标系数使用 `kIS2A`。

#### MakeSAModulateFormula
```cpp
constexpr BlendFormula MakeSAModulateFormula(BlendCoeff srcCoeff, BlendCoeff dstCoeff)
```
**用途**: LCD 文本渲染中的特殊公式,主输出为 `f*Sa`。

### LCD 混合表
`gLCDBlendTable[mode]` 为 LCD 文本渲染提供专门优化的公式,处理子像素覆盖率的特殊需求。

### 属性推导逻辑
`GetProperties()` 是编译时函数,根据输出类型和混合系数推导属性:
- **kModifiesDst**: 调用 `BlendModifiesDst()`
- **kUnaffectedByDst**: 检查 `!BlendCoeffsUseDstColor(..., false)`
- **kUnaffectedByDstIfOpaque**: 检查 `!BlendCoeffsUseDstColor(..., true)`
- **kUsesInputColor**: 检查主/辅助输出是否 >= `kModulate`
- **kCanTweakAlpha**: 检查是否可将覆盖率融入 alpha

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `src/gpu/Blend.h` | `BlendEquation`, `BlendCoeff` | 混合基础类型 |
| `src/gpu/Blend.h` | 辅助函数 | 混合逻辑判断 |
| `include/core/SkBlendMode.h` | `SkBlendMode` | 混合模式枚举 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 管线状态 | `BlendFormula` | 配置 GPU 混合状态 |
| Graphite 渲染管线 | `GetBlendFormula()` | 管线描述符构建 |
| 抗锯齿渲染路径 | 覆盖率混合公式 | AA 渲染 |
| LCD 文本渲染器 | `GetLCDBlendFormula()` | 子像素渲染 |

## 设计模式与设计决策

### 1. 编译时计算模式
所有混合公式在编译时预计算并存储在常量表中,运行时查询为 O(1) 且无分配开销。这是典型的"计算一次,使用多次"策略。

### 2. 位域优化模式
将4字节的结构体分解为位域,在不牺牲功能的前提下最小化内存占用,提升缓存效率。

### 3. 数学等价变换
通过代数变换将覆盖率处理从运行时计算转移到硬件混合:
- 原式: `f*(S*srcCoeff + D*dstCoeff) + (1-f)*D`
- 变换: `f*S*srcCoeff + D*(1 - f*(1-dstCoeff))`
- 实现: 辅助输出 `f*(1-dstCoeff)`,硬件执行 `S*srcCoeff + D*(1-Sec)`

### 4. 双源混合利用
在支持双源混合的硬件上,使用辅助颜色输出避免额外的渲染通道,提升性能。

### 5. 特例优化模式
为常见情况提供专门的构造函数:
- 源系数为零时使用反向减法
- 目标系数为零时使用辅助输出 + ISA 系数
- 标准情况使用普通加法

### 6. 属性标志模式
预计算属性标志避免运行时重复判断,例如 `unaffectedByDst()` 可快速决定是否需要读取帧缓冲。

## 性能考量

### 1. 零运行时开销
- 所有公式查询为数组索引,O(1) 时间复杂度
- 无动态内存分配
- 编译时常量表优化为只读数据段

### 2. 缓存友好
- 整个混合表约占 240 字节(60个公式×4字节)
- 单次访问触发的缓存行可包含多个公式
- 位域压缩使数据更紧凑

### 3. 分支减少
属性标志避免了运行时条件判断:
```cpp
// 优化前
if (BlendModifiesDst(eq, src, dst)) { ... }

// 优化后
if (formula.modifiesDst()) { ... }
```

### 4. 硬件混合利用
尽可能使用硬件混合而非多通道渲染:
- 单通道渲染 vs 多通道合成
- 减少帧缓冲读写
- 降低带宽消耗

### 5. 双源混合权衡
仅在必要时使用双源混合,因为:
- 并非所有 GPU 都支持
- 可能限制 MRT (多渲染目标) 数量
- 增加着色器复杂度

### 6. LCD 文本优化
专门的 LCD 混合表避免通用路径的额外检查,提升文本渲染性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/BlendFormula.h` | 定义 | 混合公式接口 |
| `src/gpu/BlendFormula.cpp` | 实现 | 混合公式表和查询函数 |
| `src/gpu/Blend.h` | 依赖 | 混合基础类型定义 |
| `src/ganesh/GrPipeline.h` | 使用者 | Ganesh 管线状态 |
| `src/graphite/RenderPassTask.cpp` | 使用者 | Graphite 渲染通道 |
| `src/ganesh/GrProcessorAnalysis.h` | 协作 | 处理器分析 |
| `src/gpu/ganesh/GrXferProcessor.h` | 使用者 | 传输处理器 |

**备注**: 该模块是 GPU 渲染管线混合阶段的核心策略提供者,所有需要精确混合控制的渲染路径都依赖它提供的公式。设计精妙地平衡了数学正确性、硬件限制和性能优化。
