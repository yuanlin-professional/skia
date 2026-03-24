# GrFragmentProcessor

> 源文件
> - src/gpu/ganesh/GrFragmentProcessor.h
> - src/gpu/ganesh/GrFragmentProcessor.cpp

## 概述

`GrFragmentProcessor` (FP) 是 Ganesh GPU 渲染管线中的片段处理器基类，负责提供自定义的片段着色器代码。FP 接收输入位置和颜色，经过处理后产生输出颜色。它们可以包含 uniform 变量，可以有子 FP 形成树状结构，并支持对子 FP 进行采样。

FP 是 Skia GPU 渲染的核心抽象，几乎所有的颜色效果（着色器、颜色过滤器、混合器等）都通过 FP 树来实现。

主要功能：
- 生成片段着色器代码
- 管理 uniform 数据和子处理器
- 支持颜色变换、纹理采样、形状剪裁等效果
- 提供优化标志以支持渲染管线优化
- 实现常量输入常量输出的分析

## 架构位置

`GrFragmentProcessor` 在渲染管线中的位置：

```
GrPaint
    └── GrFragmentProcessor 树
            ├── 着色器 FP (Shader)
            ├── 颜色过滤器 FP (ColorFilter)
            └── 混合器 FP (Blender)
                    ↓
            GrPipeline
                    ↓
            GPU 片段着色器
```

在绘制流程中：
1. **记录时**：`GrPaint` 构建 FP 树
2. **编译时**：FP 树生成片段着色器代码
3. **运行时**：`ProgramImpl` 更新 uniform 数据
4. **执行时**：GPU 执行片段着色器

## 继承关系

```
GrProcessor (基类)
    └── GrFragmentProcessor
            ├── ProgramImpl (内部类，着色器实现)
            └── 各种具体 FP 子类
                    ├── GrTextureEffect
                    ├── GrBlendFragmentProcessor
                    ├── GrSkSLFP
                    └── 其他效果 FP
```

## 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fChildProcessors` | `STArray<1, std::unique_ptr<GrFragmentProcessor>, true>` | 子处理器数组 |
| `fParent` | `const GrFragmentProcessor*` | 父处理器指针（根节点为 nullptr）|
| `fFlags` | `uint32_t` | 优化标志 + 私有标志的位域组合 |
| `fUsage` | `SkSL::SampleUsage` | 描述父 FP 如何采样本 FP 的方式 |

### ProgramImpl 关键成员

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFunctionName` | `SkString` | 着色器函数名（经过名称修饰）|
| `fChildProcessors` | `TArray<std::unique_ptr<ProgramImpl>, true>` | 子处理器实现数组 |

## 枚举和标志

### OptimizationFlags 枚举（protected）

| 标志 | 值 | 说明 |
|------|---|------|
| `kNone_OptimizationFlags` | 0 | 无优化 |
| `kCompatibleWithCoverageAsAlpha_OptimizationFlag` | 0x1 | 兼容覆盖率即 alpha 优化 |
| `kPreservesOpaqueInput_OptimizationFlag` | 0x2 | 不透明输入产生不透明输出 |
| `kConstantOutputForConstantInput_OptimizationFlag` | 0x4 | 常量输入产生常量输出 |
| `kAll_OptimizationFlags` | 0x7 | 以上三个的组合 |

### PrivateFlags 枚举（private）

| 标志 | 说明 | 传播方式 |
|------|------|---------|
| `kUsesSampleCoordsIndirectly_Flag` | 间接使用采样坐标 | 向上传播到根或第一个显式采样 |
| `kUsesSampleCoordsDirectly_Flag` | 直接使用采样坐标 | 不传播 |
| `kIsBlendFunction_Flag` | 是混合函数（需要 src + dst 两个颜色输入）| 不传播 |
| `kWillReadDstColor_Flag` | 将读取目标颜色 | 向上传播到根 |

### EmitArgs 结构（ProgramImpl 内部）

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFragBuilder` | `GrGLSLFPFragmentBuilder*` | 片段着色器构建器 |
| `fUniformHandler` | `GrGLSLUniformHandler*` | Uniform 处理器 |
| `fShaderCaps` | `const GrShaderCaps*` | 着色器能力 |
| `fFp` | `const GrFragmentProcessor&` | 当前 FP 实例 |
| `fInputColor` | `const char*` | 输入颜色变量名（nullptr 转为 `"half4(1.0)"`）|
| `fDestColor` | `const char*` | 目标颜色变量名（混合函数使用）|
| `fSampleCoord` | `const char*` | 采样坐标变量名 |

### GrFPResult 类型别名

```cpp
// .h:50
using GrFPResult = std::tuple<bool /*success*/, std::unique_ptr<GrFragmentProcessor>>;
```

某些工厂方法有前置条件，不一定能满足。这些方法返回 `GrFPResult`：若成功则 `success=true` 且包含新 FP；若前置条件不满足则 `success=false` 且原输入 FP 原样返回。

---

## 函数详解

---

### A. 静态工厂方法

#### A1. `MakeColor`

```cpp
// .h:67, .cpp:204-215
static std::unique_ptr<GrFragmentProcessor> MakeColor(SkPMColor4f color);
```

**作用**：创建一个始终输出固定颜色的 FP，忽略输入颜色。

**实现原理**：
1. 使用 `SkRuntimeEffect::MakeForColorFilter` 创建运行时效果，SkSL 代码为 `return color;`
2. 通过 `GrSkSLFP::Make` 创建 FP，将颜色作为 uniform 传入
3. 如果颜色不透明（`color.isOpaque()`），设置 `kPreservesOpaqueInput` 优化标志
4. 运行时效果声明为 ColorFilter 签名，可获得 `kConstantOutputForConstantInput` 优化

**调用场景**：
- `Compose` 优化时用常量颜色替换可折叠的子 FP
- `ModulateRGBA` 中创建颜色 FP 再与子 FP 混合

---

#### A2. `MulInputByChildAlpha`

```cpp
// .h:74-75, .cpp:217-223
static std::unique_ptr<GrFragmentProcessor> MulInputByChildAlpha(
    std::unique_ptr<GrFragmentProcessor> child);
```

**作用**：输出 = 输入颜色 × 子 FP 的 alpha 值。即 `output = input * child.a`。

**实现原理**：
1. 若 child 为空，直接返回 nullptr
2. 使用 `GrBlendFragmentProcessor::Make<SkBlendMode::kSrcIn>` 创建混合 FP
3. src 为 nullptr（使用管线输入颜色），dst 为传入的 child FP
4. kSrcIn 混合模式本质即 `src * dst.a`

**调用场景**：Shader 树中需要用 alpha 遮罩调制颜色的场景。

---

#### A3. `ApplyPaintAlpha`

```cpp
// .h:81-82, .cpp:225-238
static std::unique_ptr<GrFragmentProcessor> ApplyPaintAlpha(
    std::unique_ptr<GrFragmentProcessor> child);
```

**作用**：用不透明版本的输入颜色调用子 FP，然后将输入 alpha 应用到结果上。用于在 SkShader 树的 FP 评估中引入 paint alpha。

**实现原理**：
1. SkSL 代码：`return fp.eval(inColor.rgb1) * inColor.a;`
   - 先将输入颜色的 alpha 设为 1（构造 `inColor.rgb1`），传给子 FP
   - 再将子 FP 的输出乘以原始输入的 alpha
2. 设置 `kPreservesOpaqueInput | kCompatibleWithCoverageAsAlpha` 优化标志
3. 子 FP 声明为 `uniform colorFilter fp`

**调用场景**：将 paint alpha 融入 shader 评估链，确保 alpha 正确传播。

---

#### A4. `ModulateRGBA`

```cpp
// .h:89-90, .cpp:240-245
static std::unique_ptr<GrFragmentProcessor> ModulateRGBA(
    std::unique_ptr<GrFragmentProcessor> child, const SkPMColor4f& color);
```

**作用**：创建输出固定颜色与子 FP RGBA 调制结果的 FP。子 FP 的输入颜色将是父级的 `fInputColor`。若 child 为 null，则使用 `fInputColor`。

**实现原理**：
1. 先调用 `MakeColor(color)` 创建颜色 FP
2. 再用 `GrBlendFragmentProcessor::Make<SkBlendMode::kModulate>` 将颜色 FP 和 child FP 混合
3. kModulate 模式 = `src * dst`，实现逐分量乘法

**调用场景**：需要将固定颜色与动态纹理/着色器输出逐分量相乘的场景。

---

#### A5. `OverrideInput`

```cpp
// .h:97-98, .cpp:330-347
static std::unique_ptr<GrFragmentProcessor> OverrideInput(
    std::unique_ptr<GrFragmentProcessor>, const SkPMColor4f&);
```

**作用**：创建一个包装 FP，忽略自身输入颜色，改用指定的固定颜色作为子 FP 的输入。

**实现原理**：
1. 若输入 FP 为空，返回 nullptr
2. SkSL 代码：`return fp.eval(color);`
   - 子 FP 声明为 `uniform colorFilter fp`
   - 固定颜色声明为 `uniform half4 color`
3. 如果颜色不透明，设置 `kPreservesOpaqueInput` 标志
4. inputFP 设为 nullptr（不接收管线输入），直接用 uniform color 喂给子 FP

**调用场景**：需要用固定颜色替换 FP 树某节点输入的场景，如常量颜色优化。

---

#### A6. `DisableCoverageAsAlpha`

```cpp
// .h:105-106, .cpp:351-362
static std::unique_ptr<GrFragmentProcessor> DisableCoverageAsAlpha(
    std::unique_ptr<GrFragmentProcessor>);
```

**作用**：创建一个包装 FP，返回子 FP 的颜色结果，但禁用 `coverageAsAlpha` 优化。

**实现原理**：
1. 若输入 FP 为空或已不兼容 coverageAsAlpha，直接返回原 FP（无需包装）
2. SkSL 代码：`return inColor;`（恒等变换）
3. 只设置 `kPreservesOpaqueInput` 标志，**不**设置 `kCompatibleWithCoverageAsAlpha`
4. 这样包装层自身不带 coverageAsAlpha 标志，阻止了该优化向上传播

**调用场景**：某些 FP 数学上兼容 coverageAsAlpha 但在特定组合中该优化不正确时使用。

---

#### A7. `DestColor`

```cpp
// .h:112, .cpp:366-373
static std::unique_ptr<GrFragmentProcessor> DestColor();
```

**作用**：创建一个返回目标颜色（`args.fDestColor`）的 FP。仅在 blender 等使用 src/dst 双色输入的上下文中有意义。

**实现原理**：
1. 使用 `SkRuntimeEffect::MakeForBlender` 创建运行时效果
2. SkSL 代码：`half4 main(half4 src, half4 dst) { return dst; }`
3. 无优化标志（`kNone`），因为输出取决于目标像素，不可预测

**调用场景**：blender FP 树中需要引用目标颜色的场景。

---

#### A8. `SwizzleOutput`

```cpp
// .h:118-119, .cpp:260-326
static std::unique_ptr<GrFragmentProcessor> SwizzleOutput(
    std::unique_ptr<GrFragmentProcessor>, const skgpu::Swizzle&);
```

**作用**：对子 FP 的输出进行通道重排（swizzle）。

**实现原理**：
1. 若输入 FP 为空，返回 nullptr
2. 若 swizzle 为 RGBA（恒等），直接返回原 FP
3. 否则创建内部类 `SwizzleFragmentProcessor`：
   - 继承 `GrFragmentProcessor`，持有 `skgpu::Swizzle fSwizzle` 成员
   - `emitCode`: 调用 `invokeChild(0, args)` 获取子颜色，然后 `return childColor.swizzle`
   - `onAddToKey`: 将 `fSwizzle.asKey()` 写入 key
   - `onIsEqual`: 比较 fSwizzle
   - `constantOutputForConstantInput`: 对子 FP 的常量输出应用 swizzle
   - 优化标志继承自子 FP（`ProcessorOptimizationFlags(fp.get())`）

**调用场景**：纹理格式需要通道重排时（如 BGR→RGB）。

---

#### A9. `ClampOutput`

```cpp
// .h:125, .cpp:247-258
static std::unique_ptr<GrFragmentProcessor> ClampOutput(
    std::unique_ptr<GrFragmentProcessor>);
```

**作用**：将子 FP 的输出钳位到 [0, 1]。

**实现原理**：
1. SkSL 代码：`return saturate(inColor);`（`saturate` = clamp(x, 0, 1)）
2. 设置 `kPreservesOpaqueInput` 标志（不透明输入钳位后仍不透明）
3. 运行时效果支持 `ConstantOutputForConstantInput`

**调用场景**：颜色运算可能超出 [0,1] 范围时，需要钳位保证结果合法。

---

#### A10. `Compose`

```cpp
// .h:132-133, .cpp:377-463
static std::unique_ptr<GrFragmentProcessor> Compose(
    std::unique_ptr<GrFragmentProcessor> f,
    std::unique_ptr<GrFragmentProcessor> g);
```

**作用**：组合两个 FP 为 `f(g(x))`，即先执行 g 再用其输出作为 f 的输入。这不是混合模式组合，没有 blending 步骤。

**实现原理**：
1. 空值处理：若 f 为 null 返回 g，若 g 为 null 返回 f
2. **优化分析**：
   - 用 `GrColorFragmentProcessorAnalysis` 对 `[g, f]` 做常量传播分析
   - `initialProcessorsToEliminate(&knownColor)` 返回可消除的前导 FP 数量：
     - 0：正常组合，创建 `ComposeProcessor`
     - 1：g 可折叠为常量颜色，用 `MakeColor(knownColor)` 替换 g
     - 2：整个组合可折叠为常量，直接返回 `MakeColor(knownColor)`
3. **ComposeProcessor** 内部类：
   - 注册 f 为 child[0]，g 为 child[1]
   - 优化标志 = `f.optimizationFlags() & g.optimizationFlags()`（取交集）
   - `emitCode`: 先 `invokeChild(1, args)` 得 g(x)，再 `invokeChild(0, result, args)` 得 f(g(x))
   - `constantOutputForConstantInput`: 依次传播 child[1] → child[0]

**调用场景**：ColorFilter 链、Shader + ColorFilter 组合等多级效果串联。

---

#### A11. `ColorMatrix`

```cpp
// .h:139-144, .cpp:467-508
static std::unique_ptr<GrFragmentProcessor> ColorMatrix(
    std::unique_ptr<GrFragmentProcessor> child,
    const float matrix[20],
    bool unpremulInput, bool clampRGBOutput, bool premulOutput);
```

**作用**：对子 FP 的输出应用 4×5 颜色矩阵变换。

**实现原理**：
1. SkSL 逻辑：
   - 若 `unpremulInput`：先反预乘输入颜色
   - `color = m * color + v`（4×4 矩阵乘法 + 偏移向量）
   - 若 `clampRGBOutput`：`saturate(color)` 钳位全通道；否则只钳位 alpha
   - 若 `premulOutput`：`color.rgb *= color.a` 重新预乘
2. 从 20 元素 float 数组构建 `SkM44`（4×4 矩阵）和 `SkV4`（偏移向量）：
   - 矩阵取 [0-3, 5-8, 10-13, 15-18]，偏移取 [4, 9, 14, 19]
3. 三个 bool 参数使用 `GrSkSLFP::Specialize` 特化为编译时常量，编译器可优化掉未使用的分支
4. 无优化标志（`kNone`），因为矩阵变换通常不保留不透明性

**调用场景**：`SkColorMatrix`、颜色滤镜等需要线性颜色变换的效果。

---

#### A12. `SurfaceColor`

```cpp
// .h:150, .cpp:512-548
static std::unique_ptr<GrFragmentProcessor> SurfaceColor();
```

**作用**：读取并返回当前正在被绘制的表面像素颜色（即 framebuffer 回读）。

**实现原理**：
1. 内部类 `SurfaceColorProcessor`：
   - 构造函数中调用 `setWillReadDstColor()`，标记需要回读目标颜色
   - 优化标志为 `kNone`（输出不可预测）
   - `emitCode`: `return args.fFragBuilder->dstColor();`
   - 无 key 数据，所有实例等价

**调用场景**：自定义混合效果需要访问当前像素颜色时。

---

#### A13. `DeviceSpace`

```cpp
// .h:156, .cpp:552-600
static std::unique_ptr<GrFragmentProcessor> DeviceSpace(
    std::unique_ptr<GrFragmentProcessor>);
```

**作用**：使子 FP 在设备空间（而非局部空间）中求值。

**实现原理**：
1. 若输入 FP 为空，返回 nullptr
2. 内部类 `DeviceSpace` 继承 `GrFragmentProcessor`：
   - 关键：使用 `SkSL::SampleUsage::FragCoord()` 注册子 FP
   - 这告诉系统子 FP 使用片段坐标（设备坐标）而非局部坐标
   - `emitCode`: `invokeChild(0, args.fInputColor, args, "sk_FragCoord.xy")`
   - 优化标志继承自子 FP
   - `constantOutputForConstantInput` 委托给子 FP

**调用场景**：需要让着色器在屏幕空间而非对象空间中求值（如设备空间渐变）。

---

#### A14. `Rect`

```cpp
// .h:163-165, .cpp:615-656
static std::unique_ptr<GrFragmentProcessor> Rect(
    std::unique_ptr<GrFragmentProcessor>, GrClipEdgeType, SkRect);
```

**作用**：矩形形状 FP，计算矩形内的覆盖率，并与输入 FP 的结果调制。用于剪裁。

**实现原理**：
1. SkSL 根据 `edgeType` 计算覆盖率：
   - **非 AA（BW）**：使用 `greaterThan` 比较片段坐标与矩形边界，覆盖率为 0 或 1
   - **AA**：计算到四条边的距离，`dists4 = saturate(...)` 后组合为平滑覆盖率
   - **反向填充**：`coverage = 1.0 - coverage`
2. AA 模式下矩形外扩 0.5 像素以实现半像素平滑
3. `edgeType` 使用 `GrSkSLFP::Specialize` 特化，编译器优化分支
4. 最终用 `GrBlendFragmentProcessor::Make<kModulate>` 将覆盖率 FP 与输入 FP 相乘

**调用场景**：矩形剪裁、矩形区域遮罩。

---

#### A15. `Circle`

```cpp
// .h:167-170, .cpp:658-707
static GrFPResult Circle(std::unique_ptr<GrFragmentProcessor>,
                         GrClipEdgeType, SkPoint center, float radius);
```

**作用**：圆形形状 FP，计算圆内的覆盖率。返回 `GrFPResult` 因为半径过小时可能失败。

**实现原理**：
1. **前置条件检查**：半径 < 0.5 且为反向填充时返回 `GrFPFailure`
2. 计算 `effectiveRadius`：正向填充 +0.5，反向填充 -0.5（用于半像素偏移）
3. SkSL 逻辑：
   - 计算归一化距离 `d = (1.0 - length(offset * invRadius)) * radius`（正向）
   - 或 `d = (length(offset * invRadius) - 1.0) * radius`（反向）
   - AA 模式：`saturate(d)`；BW 模式：`d > 0.5 ? 1 : 0`
4. uniform `circle` = `{center.x, center.y, effectiveRadius, 1/effectiveRadius}`
5. 最终与输入 FP 用 kModulate 混合

**调用场景**：圆形剪裁、圆形区域遮罩。

---

#### A16. `Ellipse`

```cpp
// .h:172-176, .cpp:709-806
static GrFPResult Ellipse(std::unique_ptr<GrFragmentProcessor>,
                          GrClipEdgeType, SkPoint center, SkPoint radii,
                          const GrShaderCaps&);
```

**作用**：椭圆形状 FP，计算椭圆内的覆盖率。返回 `GrFPResult` 因为多种精度条件可能导致失败。

**实现原理**：
1. **前置条件检查**（中等精度设备额外限制）：
   - 半径 < 0.5 → 失败
   - 长短轴比 > 255 → 失败（极窄椭圆）
   - 半径 > 16384 → 失败（极大椭圆）
2. 中等精度设备上使用缩放因子：以较大半径归一化，避免浮点溢出
3. SkSL 逻辑：
   - 计算隐式方程 `(x/rx)² + (y/ry)² - 1` 的值
   - 使用梯度长度归一化得到近似距离：`approx_dist = implicit * inversesqrt(grad_dot)`
   - 按 edgeType 输出覆盖率
4. `medPrecision` 和 `edgeType` 均使用 `Specialize` 特化

**调用场景**：椭圆剪裁、圆角矩形等需要椭圆形状的场景。

---

#### A17. `HighPrecision`

```cpp
// .h:182, .cpp:810-856
static std::unique_ptr<GrFragmentProcessor> HighPrecision(
    std::unique_ptr<GrFragmentProcessor>);
```

**作用**：包装子 FP，强制整个程序使用高精度类型编译。

**实现原理**：
1. 内部类 `HighPrecisionFragmentProcessor`：
   - 优化标志继承自子 FP
   - `emitCode`: 调用 `invokeChild(0, args)` 后调用 `args.fFragBuilder->forceHighPrecision()`
   - `constantOutputForConstantInput` 委托给子 FP

**调用场景**：在精度敏感的计算（如大坐标范围的纹理采样）中确保不丢精度。

---

### B. 核心实例方法

#### B1. `clone`

```cpp
// .h:188
virtual std::unique_ptr<GrFragmentProcessor> clone() const = 0;
```

**作用**：创建一个绘制效果等价的 FP 副本。如果有子处理器也会一并克隆。

**实现原理**：纯虚函数，每个具体 FP 子类必须实现。通常流程为：
1. 分配新的子类对象
2. 调用 `cloneAndRegisterAllChildProcessors(*this)` 克隆并注册所有子 FP
3. 复制子类特有的成员变量

**调用场景**：需要复制 FP 树时（如 `Compose` 优化失败后恢复原 FP、管线需要多份 FP 引用）。

---

#### B2. `makeProgramImpl`

```cpp
// .h:193, .cpp:130-138
std::unique_ptr<ProgramImpl> makeProgramImpl() const;
```

**作用**：创建与此 FP 匹配的 `ProgramImpl` 对象树，用于着色器代码生成和 uniform 数据设置。

**实现原理**：
1. 调用虚函数 `this->onMakeProgramImpl()` 创建当前 FP 的 ProgramImpl
2. 为 impl 的 `fChildProcessors` 预分配与 `fChildProcessors` 相同数量的槽位
3. 递归：对每个非空子 FP 调用 `fChildProcessors[i]->makeProgramImpl()`，空子 FP 对应 nullptr
4. 返回完成的 ProgramImpl 树

**调用场景**：着色器程序编译时，`GrGLSLProgramBuilder` 为每个 FP 创建 ProgramImpl。

---

#### B3. `addToKey`

```cpp
// .h:195-202（inline）
void addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const;
```

**作用**：递归地将 FP 树的特征写入 key，用于着色器缓存查找。相同 key 的 FP 树可以复用已编译的着色器。

**实现原理**：
1. 调用 `this->onAddToKey(caps, b)` 写入自身的 key 数据
2. 遍历所有子处理器，对非空子 FP 递归调用 `child->addToKey(caps, b)`

**注意**：`isEqual()` 返回 true 不等于 key 相同——key 用于着色器代码缓存，`isEqual` 用于相等性判断。

**调用场景**：着色器程序编译前的缓存查找。

---

#### B4. `isEqual`

```cpp
// .h:299, .cpp:36-60
bool isEqual(const GrFragmentProcessor& that) const;
```

**作用**：保守地判断两个 FP 是否绘制效果完全等价。

**实现原理**：
1. 比较 `classID`：不同子类一定不等
2. 比较 `sampleUsage`：采样方式不同则不等
3. 调用 `this->onIsEqual(that)`：子类特定数据比较
4. 比较子处理器数量
5. 递归比较每个子 FP（处理 null 情况）

**调用场景**：管线状态去重、判断是否需要重新编译。

---

#### B5. `visitProxies`

```cpp
// .h:301, .cpp:62-66
void visitProxies(const GrVisitProxyFunc& func) const;
```

**作用**：遍历 FP 树中所有纹理代理（GrSurfaceProxy），对每个代理调用回调。

**实现原理**：
委托给 `visitTextureEffects`，对每个 `GrTextureEffect` 提取其 `view().proxy()` 和 `samplerState().mipmapped()` 传给回调。

**调用场景**：资源追踪、纹理实例化验证。

---

#### B6. `visitTextureEffects`

```cpp
// .h:303, .cpp:68-78
void visitTextureEffects(
    const std::function<void(const GrTextureEffect&)>& func) const;
```

**作用**：递归遍历 FP 树中所有 `GrTextureEffect` 节点。

**实现原理**：
1. 检查自身是否为 `GrTextureEffect`（通过 `asTextureEffect()`），若是则调用 func
2. 递归遍历所有非空子 FP

**调用场景**：`visitProxies` 的底层实现、纹理效果统计。

---

#### B7. `visitWithImpls`

```cpp
// .h:305-306, .cpp:80-90
void visitWithImpls(
    const std::function<void(const GrFragmentProcessor&, ProgramImpl&)>& f,
    ProgramImpl& impl) const;
```

**作用**：同时遍历 FP 树和对应的 ProgramImpl 树，对每一对 (FP, ProgramImpl) 调用回调。

**实现原理**：
1. 对当前 (this, impl) 调用回调 f
2. 断言 `impl.numChildProcessors() == this->numChildProcessors()`
3. 递归：对每个非空子 FP 调用 `child->visitWithImpls(f, *impl.childProcessor(i))`

**调用场景**：`setData` 阶段批量更新 uniform 数据、着色器程序验证。

---

#### B8. `asTextureEffect`

```cpp
// .h:308-309, .cpp:92-104
GrTextureEffect* asTextureEffect();
const GrTextureEffect* asTextureEffect() const;
```

**作用**：若此 FP 是 `GrTextureEffect`，返回其指针；否则返回 nullptr。

**实现原理**：
检查 `this->classID() == kGrTextureEffect_ClassID`，是则 `static_cast` 转换，否则返回 nullptr。

**调用场景**：`visitTextureEffects` 中识别纹理节点、纹理代理访问。

---

#### B9. `dumpTreeInfo`（调试）

```cpp
// .h:314, .cpp:106-128（仅在 GPU_TEST_UTILS 宏启用时）
SkString dumpTreeInfo() const;
```

**作用**：生成整个 FP 树的调试信息字符串。

**实现原理**：
1. 调用 `this->dumpInfo()` 获取当前节点信息
2. 通过辅助函数 `recursive_dump_tree_info` 递归处理子节点
3. 每层缩进一个 tab，格式为 `(#index) -> childDumpInfo`，空子节点显示 "null"

**调用场景**：调试和测试环境下检查 FP 树结构。

---

#### B10. `isInstantiated`（调试）

```cpp
// .h:212, .cpp:146-155（仅在 SK_DEBUG 宏启用时）
bool isInstantiated() const;
```

**作用**：检查 FP 树中所有纹理效果是否都已实例化（纹理资源已就绪）。

**实现原理**：
通过 `visitTextureEffects` 遍历所有 `GrTextureEffect`，检查每个的 `texture()` 是否非空。任何一个为空则返回 false。

**调用场景**：调试断言，确保绘制前所有纹理已就绪。

---

### C. 子处理器管理

#### C1. `numChildProcessors`

```cpp
// .h:204（inline）
int numChildProcessors() const { return fChildProcessors.size(); }
```

**作用**：返回子处理器总数（包括 null 槽位）。

---

#### C2. `numNonNullChildProcessors`

```cpp
// .h:205, .cpp:140-143
int numNonNullChildProcessors() const;
```

**作用**：返回非空子处理器的数量。

**实现原理**：使用 `std::count_if` 统计 `fChildProcessors` 中非 nullptr 的元素。

---

#### C3. `childProcessor`

```cpp
// .h:207-210（inline）
GrFragmentProcessor* childProcessor(int index);
const GrFragmentProcessor* childProcessor(int index) const;
```

**作用**：按索引访问子处理器。可能返回 nullptr（若该槽位注册了空子 FP）。

---

#### C4. `parent`

```cpp
// .h:191（inline）
const GrFragmentProcessor* parent() const { return fParent; }
```

**作用**：返回父处理器指针。根节点返回 nullptr。

**实现原理**：直接返回 `fParent` 成员。`fParent` 在 `registerChild` 中设置。

---

#### C5. `registerChild`

```cpp
// .h:402-403, .cpp:157-192
void registerChild(std::unique_ptr<GrFragmentProcessor> child,
                   SkSL::SampleUsage sampleUsage = SkSL::SampleUsage::PassThrough());
```

**作用**：在构造函数中注册一个子 FP，建立父子关系并传播标志。

**实现原理**：
1. 断言 `sampleUsage.isSampled()` 为 true
2. 若 child 为 null，push_back nullptr 后直接返回
3. 断言子 FP 尚未被附加到其他 FP（`!child->fParent && !child->sampleUsage().isSampled()`）
4. 设置子 FP 的采样方式：`child->fUsage = sampleUsage`
5. **标志传播**：
   - 若子 FP `willReadDstColor()`，向上传播 → `this->setWillReadDstColor()`
   - 若采样方式为 passthrough 或 uniformMatrix，且子 FP `usesSampleCoords()`，则标记自身 `kUsesSampleCoordsIndirectly_Flag`
6. 设置父子关系：`child->fParent = this`
7. 将 child 移入 `fChildProcessors`

**调用场景**：所有 FP 子类的构造函数中注册子 FP。

---

#### C6. `cloneAndRegisterAllChildProcessors`

```cpp
// .h:409, .cpp:194-202
void cloneAndRegisterAllChildProcessors(const GrFragmentProcessor& src);
```

**作用**：克隆源 FP 的所有子处理器并注册为当前 FP 的子处理器。

**实现原理**：
遍历 src 的每个子 FP：
- 非空：调用 `fp->clone()` 克隆，然后 `this->registerChild(clone, fp->sampleUsage())` 保留原采样方式
- 空：调用 `this->registerChild(nullptr)`

**调用场景**：FP 拷贝构造函数中自动调用（见 `.h:362-365` 的拷贝构造函数），以及 `clone()` 实现中。

---

### D. 标志查询与设置

#### D1. `willReadDstColor`

```cpp
// .h:215-217（inline）
bool willReadDstColor() const;
```

**作用**：FP 树中是否有任何节点会回读目标表面颜色。

**实现原理**：检查 `fFlags & kWillReadDstColor_Flag`。该标志在 `registerChild` 中从子 FP 向上传播到根。

---

#### D2. `isBlendFunction`

```cpp
// .h:220-222（inline）
bool isBlendFunction() const;
```

**作用**：此 FP 的 SkSL 是否接受两个颜色输入（src + dst）。

**实现原理**：检查 `fFlags & kIsBlendFunction_Flag`。该标志不传播，仅标记自身。

---

#### D3. `usesSampleCoordsDirectly`

```cpp
// .h:229-231（inline）
bool usesSampleCoordsDirectly() const;
```

**作用**：此 FP 是否直接引用采样坐标参数。

**实现原理**：检查 `fFlags & kUsesSampleCoordsDirectly_Flag`。不传播。在构造时由 `setUsesSampleCoordsDirectly()` 设置。

---

#### D4. `usesSampleCoords`

```cpp
// .h:238-241（inline）
bool usesSampleCoords() const;
```

**作用**：此 FP 是否使用输入坐标（直接或间接通过 passthrough/matrix 子 FP 链）。

**实现原理**：检查 `fFlags & (kUsesSampleCoordsDirectly_Flag | kUsesSampleCoordsIndirectly_Flag)`。间接标志在 `registerChild` 中传播。

---

#### D5. `sampleUsage`

```cpp
// .h:245-247（inline）
const SkSL::SampleUsage& sampleUsage() const;
```

**作用**：返回描述父 FP 如何采样此 FP 的 `SampleUsage` 对象。

**实现原理**：直接返回 `fUsage` 引用。该值在 `registerChild` 中由父 FP 设置。

---

#### D6. `compatibleWithCoverageAsAlpha`

```cpp
// .h:261-263（inline）
bool compatibleWithCoverageAsAlpha() const;
```

**作用**：此 FP 是否兼容"覆盖率即 alpha"优化。

**解释**：当 FP 的输出是输入颜色/alpha 与某个 [0,1] 范围内的计算值的调制时，可以将抗锯齿覆盖率预乘到 GeometryProcessor 的颜色输出中，避免单独的覆盖率通道。

**实现原理**：检查 `fFlags & kCompatibleWithCoverageAsAlpha_OptimizationFlag`。

---

#### D7. `preservesOpaqueInput`

```cpp
// .h:268-270（inline）
bool preservesOpaqueInput() const;
```

**作用**：不透明输入是否一定产生不透明输出。

**实现原理**：检查 `fFlags & kPreservesOpaqueInput_OptimizationFlag`。

---

#### D8. `hasConstantOutputForConstantInput`（两个重载）

```cpp
// .h:277-283
bool hasConstantOutputForConstantInput(SkPMColor4f inputColor,
                                       SkPMColor4f* outputColor) const;
// .h:284-286
bool hasConstantOutputForConstantInput() const;
```

**作用**：
- 带参数版本：检查是否常量输出，若是则计算输出颜色写入 `outputColor`
- 无参数版本：仅查询标志

**实现原理**：
带参数版本检查 `kConstantOutputForConstantInput_OptimizationFlag`，若设置则调用虚函数 `this->constantOutputForConstantInput(inputColor)` 获取实际输出颜色。

**调用场景**：`Compose` 等优化分析中的常量折叠。

---

#### D9. `clearConstantOutputForConstantInputFlag`

```cpp
// .h:288-290（inline）
void clearConstantOutputForConstantInputFlag();
```

**作用**：清除常量输出标志。

**实现原理**：`fFlags &= ~kConstantOutputForConstantInput_OptimizationFlag`。

**调用场景**：子类在某些条件下确定自己不再能保证常量输出时调用。

---

#### D10. `setUsesSampleCoordsDirectly`

```cpp
// .h:413-415（inline, protected）
void setUsesSampleCoordsDirectly();
```

**作用**：标记此 FP 的 ProgramImpl 会直接使用 `EmitArgs::fSampleCoord`。

**实现原理**：`fFlags |= kUsesSampleCoordsDirectly_Flag`。

**调用场景**：FP 子类构造函数中，当 emitCode 会引用采样坐标时调用。

---

#### D11. `setWillReadDstColor`

```cpp
// .h:419-421（inline, protected）
void setWillReadDstColor();
```

**作用**：标记此 FP 的 ProgramImpl 会调用 `dstColor()` 回读 framebuffer。

**实现原理**：`fFlags |= kWillReadDstColor_Flag`。该标志在 `registerChild` 中向上传播。

**调用场景**：`SurfaceColor()` 等需要回读目标颜色的 FP。

---

#### D12. `setIsBlendFunction`

```cpp
// .h:425-427（inline, protected）
void setIsBlendFunction();
```

**作用**：标记此 FP 的 emitCode 会生成接受两个颜色输入的混合函数。

**实现原理**：`fFlags |= kIsBlendFunction_Flag`。

**调用场景**：blender FP（如 `GrBlendFragmentProcessor`）的构造函数中。

---

#### D13. `mergeOptimizationFlags`

```cpp
// .h:429-432（inline, protected）
void mergeOptimizationFlags(OptimizationFlags flags);
```

**作用**：与传入的标志做交集，仅保留双方都有的优化标志。

**实现原理**：
```cpp
fFlags &= (flags | ~kAll_OptimizationFlags);
```
- `~kAll_OptimizationFlags` 保护非优化位不被清除
- `flags | ~kAll_OptimizationFlags` 的结果中，优化位仅保留 flags 中为 1 的
- 与 `fFlags` 做 AND，实现优化标志取交集

**调用场景**：复合 FP 在构造时合并子 FP 的优化标志（如 `Compose` 取 f 和 g 的交集）。

---

#### D14. `optimizationFlags`

```cpp
// .h:367-369（inline, protected）
OptimizationFlags optimizationFlags() const;
```

**作用**：返回当前 FP 的优化标志（仅低 3 位）。

**实现原理**：`static_cast<OptimizationFlags>(kAll_OptimizationFlags & fFlags)`，掩掉私有标志位。

---

#### D15. `ModulateForSamplerOptFlags`（静态, protected）

```cpp
// .h:339-345（inline）
static OptimizationFlags ModulateForSamplerOptFlags(
    SkAlphaType alphaType, bool samplingDecal);
```

**作用**：辅助函数，帮助纹理采样 FP 子类决定应设置哪些优化标志。假设输出颜色是输入颜色与纹理采样值的调制。

**实现原理**：
- 若 `samplingDecal` 为 true（decal 采样可能产生透明区域）：仅返回 `kCompatibleWithCoverageAsAlpha`
- 否则委托给 `ModulateForClampedSamplerOptFlags`

---

#### D16. `ModulateForClampedSamplerOptFlags`（静态, protected）

```cpp
// .h:348-355（inline）
static OptimizationFlags ModulateForClampedSamplerOptFlags(SkAlphaType alphaType);
```

**作用**：同上，但假设采样器使用 clamp 模式（不会因 decal 产生透明）。

**实现原理**：
- 若 `alphaType == kOpaque_SkAlphaType`：返回 `kCompatibleWithCoverageAsAlpha | kPreservesOpaqueInput`
- 否则：仅返回 `kCompatibleWithCoverageAsAlpha`

---

#### D17. `ProcessorOptimizationFlags`（静态, protected）

```cpp
// .h:372-374（inline）
static OptimizationFlags ProcessorOptimizationFlags(const GrFragmentProcessor* fp);
```

**作用**：安全地获取 FP 的优化标志。若 fp 为 null 则返回 `kAll_OptimizationFlags`（null FP 等价于恒等变换，拥有所有优化）。

**实现原理**：`fp ? fp->optimizationFlags() : kAll_OptimizationFlags`。

**调用场景**：`SwizzleOutput`、`HighPrecision` 等包装 FP 在构造时获取子 FP 的优化标志。

---

#### D18. `ConstantOutputForConstantInput`（静态, protected）

```cpp
// .h:381-389（inline）
static SkPMColor4f ConstantOutputForConstantInput(
    const GrFragmentProcessor* fp, const SkPMColor4f& input);
```

**作用**：允许一个子类访问另一个 FP 的 `constantOutputForConstantInput` 实现。

**实现原理**：
- 若 fp 非空：断言 `fp->hasConstantOutputForConstantInput()` 成立，调用 `fp->constantOutputForConstantInput(input)`
- 若 fp 为 null：返回 input 本身（null FP 是恒等变换）

**调用场景**：复合 FP 的 `constantOutputForConstantInput` 实现中，递归计算子 FP 的常量输出（如 `Compose`、`SwizzleOutput`、`DeviceSpace`、`HighPrecision`）。

---

### E. 构造函数与私有虚函数

#### E1. 主构造函数

```cpp
// .h:357-360（inline, protected）
GrFragmentProcessor(ClassID classID, OptimizationFlags optimizationFlags);
```

**作用**：初始化 FP 基类，设置类 ID 和优化标志。

**实现原理**：
1. 调用基类 `GrProcessor(classID)` 构造函数
2. 将 `optimizationFlags` 存入 `fFlags`
3. 断言优化标志不包含非法位

**调用场景**：所有 FP 子类的构造函数中。

---

#### E2. 拷贝构造函数

```cpp
// .h:362-365（inline, protected）
explicit GrFragmentProcessor(const GrFragmentProcessor& src);
```

**作用**：从现有 FP 拷贝构造，复制 classID 和 flags，并克隆所有子处理器。

**实现原理**：
1. 用 `src.classID()` 初始化基类
2. 复制 `src.fFlags`
3. 调用 `this->cloneAndRegisterAllChildProcessors(src)` 克隆所有子 FP

**注意**：不复制 `fParent` 和 `fUsage`，因为这些将由新的父 FP 在 `registerChild` 中设置。

**调用场景**：FP 子类的拷贝构造函数中（如 `ComposeProcessor(const ComposeProcessor& that)`）。

---

#### E3. `onMakeProgramImpl`（纯虚, private）

```cpp
// .h:444
virtual std::unique_ptr<ProgramImpl> onMakeProgramImpl() const = 0;
```

**作用**：创建适当的 ProgramImpl 子类实例。

**实现原理**：由 `makeProgramImpl()` 调用。每个 FP 子类实现此函数返回自己的 ProgramImpl。通常返回 `std::make_unique<Impl>()`，其中 Impl 是子类内部定义的 ProgramImpl 派生类。

---

#### E4. `onAddToKey`（纯虚, private）

```cpp
// .h:446
virtual void onAddToKey(const GrShaderCaps&, skgpu::KeyBuilder*) const = 0;
```

**作用**：将子类特有的数据写入着色器 key。

**实现原理**：由 `addToKey()` 调用。子类将影响着色器代码生成的参数写入 KeyBuilder（如 swizzle 值、edgeType 等）。没有需要区分的参数时可实现为空函数。

---

#### E5. `onIsEqual`（纯虚, private）

```cpp
// .h:452
virtual bool onIsEqual(const GrFragmentProcessor&) const = 0;
```

**作用**：比较同一子类的两个实例是否具有相同的效果参数。

**实现原理**：由 `isEqual()` 调用。调用前已保证两者有相同的 `classID`。子类只需比较自身的成员变量。没有额外成员时可返回 true。

---

#### E6. `constantOutputForConstantInput`（虚, private）

```cpp
// .h:435-437
virtual SkPMColor4f constantOutputForConstantInput(
    const SkPMColor4f& /* inputColor */) const;
```

**作用**：给定常量输入颜色，计算常量输出颜色。

**实现原理**：默认实现调用 `SK_ABORT`（崩溃），因此只有标记了 `kConstantOutputForConstantInput_OptimizationFlag` 的子类才应覆盖此函数。

**调用场景**：`hasConstantOutputForConstantInput(inputColor, outputColor)` 和 `ConstantOutputForConstantInput()` 中调用。

---

### F. ProgramImpl 方法

#### F1. `emitCode`（纯虚）

```cpp
// .h:536
virtual void emitCode(EmitArgs&) = 0;
```

**作用**：生成此 FP 的 SkSL 片段着色器代码。每个 FP 的代码在自己的作用域 `{}` 中，局部变量名不会跨 FP 冲突。

**实现原理**：
子类通过 `args.fFragBuilder` 写入着色器代码。典型流程：
1. 通过 `args.fUniformHandler` 声明 uniform 变量
2. 通过 `invokeChild` 调用子 FP 获取中间颜色
3. 写入计算代码并 `return` 结果颜色

---

#### F2. `setData`

```cpp
// .h:540, .cpp:862-865
void setData(const GrGLSLProgramDataManager& pdman,
             const GrFragmentProcessor& processor);
```

**作用**：在每次绘制时从 FP 实例中提取数据并上传到 GPU uniform 变量。

**实现原理**：
直接调用 `this->onSetData(pdman, processor)`。

**注意**：此函数不递归处理子处理器，递归遍历整棵树是调用者的责任（通常通过 `visitWithImpls`）。

---

#### F3. `onSetData`（虚, private）

```cpp
// .h:654
virtual void onSetData(const GrGLSLProgramDataManager&,
                       const GrFragmentProcessor&) {}
```

**作用**：子类覆盖此函数以上传 uniform 数据。

**实现原理**：默认为空（无 uniform 数据需要更新）。子类实现中通过 `pdman.set1f()`、`pdman.setMatrix3f()` 等方法上传数据。

**保证**：传入的 `GrFragmentProcessor` 与创建此 ProgramImpl 时的 FP 类型相同、key 相同。

---

#### F4. `invokeChild`（三个重载）

**重载 1**：默认输入颜色和目标颜色
```cpp
// .h:557-565（inline）
SkString invokeChild(int childIndex, EmitArgs& parentArgs,
                     std::string_view skslCoords = {});
```
委托给完整版本，`inputColor=nullptr`，`destColor=nullptr`。

**重载 2**：指定输入颜色，默认目标颜色
```cpp
// .h:575-584（inline）
SkString invokeChild(int childIndex, const char* inputColor,
                     EmitArgs& parentArgs, std::string_view skslCoords = {});
```
委托给完整版本，`destColor=nullptr`。

**重载 3**：完整版本
```cpp
// .h:606-610, .cpp:867-910
SkString invokeChild(int childIndex, const char* inputColor,
                     const char* destColor, EmitArgs& parentArgs,
                     std::string_view skslCoords = {});
```

**作用**：在着色器代码中生成对子 FP 函数的调用表达式。

**实现原理**：
1. 若 `inputColor` 为 null，使用 `args.fInputColor`
2. 若子 FP 为 null，直接返回 inputColor 字符串（空对象模式）
3. 构造函数调用：`childFunctionName(inputColor`
4. 若子 FP 是混合函数：追加 `, destColor`（null 时使用父级的 destColor 或 `"half4(1)"`）
5. 断言子 FP 不使用 uniform 矩阵采样（那应用 `invokeChildWithMatrix`）
6. 若子 FP 需要坐标参数：
   - 有自定义 `skslCoords`：追加自定义坐标
   - 否则：追加父级的 `args.fSampleCoord`
7. 闭合括号，返回完整的调用表达式

---

#### F5. `invokeChildWithMatrix`（三个重载）

**重载 1**：默认输入颜色和目标颜色
```cpp
// .h:567-572（inline）
SkString invokeChildWithMatrix(int childIndex, EmitArgs& parentArgs);
```

**重载 2**：指定输入颜色，默认目标颜色
```cpp
// .h:586-593（inline）
SkString invokeChildWithMatrix(int childIndex, const char* inputColor,
                               EmitArgs& parentArgs);
```

**重载 3**：完整版本
```cpp
// .h:617-620, .cpp:912-968
SkString invokeChildWithMatrix(int childIndex, const char* inputColor,
                               const char* destColor, EmitArgs& parentArgs);
```

**作用**：生成对子 FP 函数的调用，并根据子 FP 的 `SampleUsage` 中的矩阵变换坐标。

**实现原理**：
1. 与 `invokeChild` 类似的 null 处理和输入颜色默认值
2. 断言子 FP 使用 uniform 矩阵采样
3. 通过 `args.fUniformHandler->getUniformMapping` 获取矩阵 uniform 的修饰名
4. 构造函数调用，处理混合函数参数
5. **坐标变换**（仅当子 FP 需要坐标参数时）：
   - **有透视**：`proj((matrix) * coord.xy1)` — 需要透视除法
   - **支持非方阵**：`float3x2(matrix) * coord.xy1` — 用 3×2 矩阵优化
   - **不支持非方阵**：`((matrix) * coord.xy1).xy` — 3×3 乘法后取 xy
6. 若子 FP 的坐标计算可以提升到顶点着色器（所有祖先矩阵均为 uniform），则子 FP 不需要坐标参数，矩阵乘法在顶点着色器中完成，结果存储在 varying 中

---

#### F6. `ProgramImpl::numChildProcessors`

```cpp
// .h:542（inline）
int numChildProcessors() const { return fChildProcessors.size(); }
```

**作用**：返回 ProgramImpl 的子处理器实现数量。与对应 FP 的 `numChildProcessors()` 一致。

---

#### F7. `ProgramImpl::childProcessor`

```cpp
// .h:544（inline）
ProgramImpl* childProcessor(int index) const { return fChildProcessors[index].get(); }
```

**作用**：按索引访问子 ProgramImpl。

---

#### F8. `setFunctionName`

```cpp
// .h:546-549（inline）
void setFunctionName(SkString name);
```

**作用**：设置此 FP 在着色器中的入口函数名（已经过名称修饰）。只能设置一次。

**实现原理**：断言 `fFunctionName` 为空，然后 move 赋值。

**调用场景**：`GrGLSLProgramBuilder` 在为 FP 生成着色器函数时设置。

---

#### F9. `functionName`

```cpp
// .h:551-554（inline）
const char* functionName() const;
```

**作用**：返回此 FP 在着色器中的入口函数名。

**实现原理**：断言 `fFunctionName` 不为空，返回 `fFunctionName.c_str()`。

**调用场景**：`invokeChild` 和 `invokeChildWithMatrix` 中用于构造函数调用表达式。

---

#### F10. `ProgramImpl::Iter` 迭代器

```cpp
// .h:628-644
class Iter {
public:
    Iter(std::unique_ptr<ProgramImpl> fps[], int cnt);
    Iter(ProgramImpl& fp);
    ProgramImpl& operator*() const;
    ProgramImpl* operator->() const;
    Iter& operator++();
    explicit operator bool() const;
};
```

**作用**：对 ProgramImpl 树进行前序遍历。可从单个 ProgramImpl 或 ProgramImpl 数组开始。

**实现原理**：
- 内部维护一个 `STArray<4, ProgramImpl*, true> fFPStack` 作为遍历栈
- 构造时将根节点压栈
- `operator++`：弹出栈顶，将其子节点压栈
- `operator bool`：栈非空则可继续遍历
- 禁止拷贝（每个迭代器持有栈）

**调用场景**：需要线性遍历所有 ProgramImpl 节点时（如批量 setData）。遍历顺序与 `GrFragmentProcessor::Iter` 对同一 pipeline key 的遍历一致。

---

### G. 自由函数

#### G1. `GrFPFailure`

```cpp
// .h:668-670（inline）
static inline GrFPResult GrFPFailure(std::unique_ptr<GrFragmentProcessor> fp);
```

**作用**：构造一个表示失败的 `GrFPResult`，`success=false`，并将原 FP 原样返回。

**实现原理**：`return {false, std::move(fp)};`

**调用场景**：`Circle`、`Ellipse` 等工厂方法在前置条件不满足时返回。

---

#### G2. `GrFPSuccess`

```cpp
// .h:671-674（inline）
static inline GrFPResult GrFPSuccess(std::unique_ptr<GrFragmentProcessor> fp);
```

**作用**：构造一个表示成功的 `GrFPResult`，`success=true`。断言 FP 非空。

**实现原理**：`SkASSERT(fp); return {true, std::move(fp)};`

**调用场景**：工厂方法成功创建 FP 时返回。

---

#### G3. `GrFPNullableSuccess`

```cpp
// .h:676-678（inline）
static inline GrFPResult GrFPNullableSuccess(std::unique_ptr<GrFragmentProcessor> fp);
```

**作用**：与 `GrFPSuccess` 相同但允许 FP 为 null。

**实现原理**：`return {true, std::move(fp)};`（无断言）。

**调用场景**：成功但结果可以为 null 的场景。

---

## 设计模式与设计决策

### 1. 组合模式

FP 形成树状结构，每个 FP 可以有多个子 FP。复杂效果通过简单效果组合实现，支持递归遍历和灵活嵌套。

### 2. 访问者模式

`visitProxies`、`visitTextureEffects`、`visitWithImpls` 允许外部代码遍历 FP 树执行特定操作（如收集纹理代理、批量更新 uniform 数据）。

### 3. 策略模式

`ProgramImpl` 封装着色器代码生成逻辑，每个 FP 子类提供自己的 ProgramImpl 实现。FP 和 ProgramImpl 的解耦使得同一 ProgramImpl 可以复用于 key 相同的不同 FP 实例。

### 4. 工厂方法模式

所有静态工厂方法（`MakeColor`、`Compose`、`Rect` 等）封装了内部类的创建细节，调用者无需了解具体子类。

### 5. 空对象模式

子处理器可以为 nullptr。`invokeChild` 遇到空子 FP 时返回输入颜色（恒等变换）。`ProcessorOptimizationFlags(nullptr)` 返回 `kAll`。这避免了到处检查空指针的复杂性。

### 6. 关键设计决策

- **优化标志系统**：三个标志在 FP 树中自动传播（通过 `mergeOptimizationFlags` 取交集），支持管线级优化决策
- **采样使用追踪**：`SkSL::SampleUsage` 精确描述采样方式（passthrough、uniform matrix、explicit coords、frag coord），允许几何处理器将坐标计算提升到顶点着色器
- **常量折叠**：`hasConstantOutputForConstantInput` + `Compose` 的分析优化，可在编译时消除产生常量输出的 FP 子树
- **混合函数支持**：`kIsBlendFunction_Flag` 标记双色输入 FP，`invokeChild` 自动处理 destColor 参数传递
- **运行时效果特化**：大量工厂方法使用 `GrSkSLFP::Specialize` 将 uniform 值特化为编译时常量，编译器可优化掉未使用的分支

## 性能考量

### 1. Compose 常量折叠

`Compose` 在创建时运行 `GrColorFragmentProcessorAnalysis`，如果子 FP 产生常量输出则直接替换为 `MakeColor`，消除不必要的着色器指令。

### 2. 着色器缓存

`addToKey` 生成的 key 用于着色器缓存查找，相同 key 的 FP 树复用已编译的着色器，避免重复编译。

### 3. 运行时效果特化

`GrSkSLFP::Specialize` 将枚举/bool 类型的 uniform 嵌入为字面值常量，编译器可消除死分支，生成更紧凑高效的着色器代码。

### 4. 优化标志传播

`mergeOptimizationFlags` 通过位运算取交集，O(1) 代价完成标志合并。标志的传播在 `registerChild` 中自动完成，FP 子类无需手动管理。

### 5. 提前失败

形状剪裁 FP（`Circle`、`Ellipse`）检测不支持的配置（过小半径、低精度设备限制），通过 `GrFPFailure` 避免无效 FP 进入管线。

### 6. 坐标提升到顶点着色器

当所有祖先矩阵均为 uniform 时，`invokeChildWithMatrix` 的矩阵乘法可以完全在顶点着色器中完成，结果通过 varying 传递到片段着色器，减少逐像素计算。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrProcessor` | 基类 |
| `GrPipeline` | 渲染管线组装 |
| `GrShaderCaps` | 着色器能力查询 |
| `GrGLSLFragmentShaderBuilder` | 片段着色器构建 |
| `GrGLSLUniformHandler` | Uniform 管理 |
| `GrGLSLProgramDataManager` | Uniform 数据更新 |
| `GrGLSLProgramBuilder` | 着色器程序构建 |
| `GrProcessorAnalysis` | FP 分析优化 |
| `GrSurfaceProxyView` | 纹理视图 |
| `skgpu::KeyBuilder` | 着色器 key 构建 |
| `skgpu::Swizzle` | 纹理通道重排 |
| `SkRuntimeEffect` | 运行时效果系统 |
| `SkSL::SampleUsage` | 采样使用信息 |
| `SkBlendMode` | 混合模式 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 具体 FP 子类 | 继承并实现特定效果 |
| `GrPaint` | 构建 FP 树 |
| `GrPipeline` | 使用 FP 树 |
| `GrFragmentProcessors` | 创建各种 FP 实例 |
| `GrGLSLProgramBuilder` | 从 FP 树生成着色器 |
| `GrOpsRenderPass` | 执行使用 FP 的绘制命令 |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrProcessor.h` | 处理器基类 |
| `src/gpu/ganesh/GrFragmentProcessors.h` | FP 工厂函数 |
| `src/gpu/ganesh/GrPaint.h` | 绘制状态，包含 FP 树 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线 |
| `src/gpu/ganesh/GrProcessorAnalysis.h` | FP 分析优化 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 片段着色器构建 |
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h` | 着色器程序构建 |
| `src/gpu/ganesh/glsl/GrGLSLUniformHandler.h` | Uniform 管理 |
| `src/gpu/ganesh/glsl/GrGLSLProgramDataManager.h` | Uniform 数据更新 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 纹理效果 FP |
| `src/gpu/ganesh/effects/GrBlendFragmentProcessor.h` | 混合效果 FP |
| `src/gpu/ganesh/effects/GrSkSLFP.h` | 运行时效果 FP |
| `src/gpu/ganesh/effects/GrMatrixEffect.h` | 矩阵变换效果 |
| `src/gpu/ganesh/effects/GrColorSpaceXformEffect.h` | 颜色空间转换 |
| `include/private/SkSLSampleUsage.h` | 采样使用信息 |
| `src/gpu/KeyBuilder.h` | 着色器 key 构建 |
| `src/gpu/Swizzle.h` | 纹理通道重排 |
