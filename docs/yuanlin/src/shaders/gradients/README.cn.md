# src/shaders/gradients - Skia 渐变着色器实现

## 概述

`src/shaders/gradients` 目录包含了 Skia 图形库中所有渐变着色器(Gradient Shader)的核心实现。渐变着色器是 2D 图形编程中最常用的效果之一,它在指定的几何形状上根据颜色停靠点(color stops)生成平滑的颜色过渡。Skia 支持四种标准渐变类型:线性渐变(Linear)、径向渐变(Radial)、扫描渐变(Sweep)和锥形渐变(Conical/TwoPointConical)。

该目录采用经典的模板方法设计模式。`SkGradientBaseShader` 作为所有渐变着色器的公共基类,封装了颜色停靠点管理、颜色空间转换、TileMode 处理、以及光栅化管线构建的通用逻辑。四个具体渐变类型各自仅需实现 `appendGradientStages()` 钩子方法,提供从笛卡尔坐标(x, y)到一维渐变参数 t(范围 [0, 1])的映射逻辑。这种分离使得通用的颜色插值和管线构建代码只需编写一次,而特定的坐标映射算法则由各子类独立实现。

颜色插值机制是渐变系统的核心技术挑战。Skia 通过将颜色停靠点预计算为分段线性函数(color = factor * t + bias)的形式,避免了运行时的逐像素查找开销。对于均匀分布的停靠点和非均匀分布的停靠点,分别采用不同的优化策略。特别地,两个停靠点的常见情况使用专用的 `evenly_spaced_2_stop_gradient` 快速路径。此外,渐变系统还完整支持 CSS Color Level 4 中定义的各种插值色彩空间(sRGB、Lab、OKLab、HCL 等)和色相插值方法(shorter、longer、increasing、decreasing)。

锥形渐变(SkConicalGradient)是四种类型中算法最为复杂的。它描述了两个圆之间的颜色过渡,根据两圆的几何关系可分解为三种子类型:径向(Radial,同心圆)、条带(Strip,等半径)和焦点(Focal,一般情况)。焦点类型又根据焦点是否在终止圆上、是否为原始焦点等条件,在光栅化管线中选择不同的计算分支,以在数值稳定性和性能之间取得平衡。

渐变着色器系统在 GPU 后端(Ganesh 和 Graphite)中也有对应的实现,通过 `ShaderType::kGradientBase` 类型标识和 `asGradient()` 接口,GPU 后端可以提取渐变参数并生成等效的着色器程序。当颜色停靠点数量超过 GPU uniform 的限制时,系统会将颜色数据存储在位图中(`fColorsAndOffsetsBitmap`),通过纹理采样的方式传递给 GPU。

## 架构图

```
                     +---------------------------+
                     |    SkShaderBase           |
                     |  (src/shaders/)           |
                     +------------+--------------+
                                  |
                     +------------+--------------+
                     | SkGradientBaseShader      |
                     |  (渐变着色器基类)           |
                     |                           |
                     | - fColors[]               |  颜色停靠点数组
                     | - fPositions[]            |  位置数组 (可选)
                     | - fColorSpace             |  停靠点色彩空间
                     | - fInterpolation          |  插值参数
                     | - fTileMode               |  平铺模式
                     | - fPtsToUnit              |  坐标到单位空间矩阵
                     | - fColorsAndOffsetsBitmap |  GPU 大颜色表缓存
                     |                           |
                     | + appendStages()          |  [模板方法] 通用管线构建
                     | + appendGradientStages()  |  [钩子] 子类坐标映射
                     | + AppendGradientFillStages| 颜色填充阶段
                     | + AppendInterpolatedTo... | 色彩空间转换阶段
                     +------+--------+-----------+
                            |        |
            +---------------+        +----------------+
            |               |                          |
   +--------+------+ +------+--------+   +------------+--------+
   |SkLinearGradient| |SkRadialGradient|   |SkSweepGradient      |
   |                | |                |   |                      |
   | fStart, fEnd   | | fCenter        |   | fCenter              |
   |                | | fRadius        |   | fTBias, fTScale      |
   | t = x          | | t = sqrt(x^2  |   | t = atan2(y,x)/2pi  |
   | (无额外阶段)    | |      + y^2)   |   |   * scale + bias     |
   +----------------+ +----------------+   +----------------------+

                     +------+--------+
                     |SkConicalGradient|
                     |                 |
                     | fCenter1/2      |
                     | fRadius1/2      |
                     | fType:          |
                     |  kRadial        |  同心圆 -> xy_to_radius
                     |  kStrip         |  等半径 -> xy_to_2pt_conical_strip
                     |  kFocal         |  一般情况 -> 多种焦点分支
                     | fFocalData      |
                     +-----------------+

  辅助类:
  +--------------------+    +----------------------+
  | SkGradientScope    |    | SkColor4fXformer     |
  | (反序列化临时存储)   |    | (颜色空间变换)        |
  +--------------------+    +----------------------+
```

## 目录结构

```
src/shaders/gradients/
|-- BUILD.bazel                         # Bazel 构建定义
|-- SkGradientBaseShader.h              # 渐变基类头文件 (154 行)
|-- SkGradientBaseShader.cpp            # 渐变基类实现 (约 700 行)
|                                       #   - 构造函数(停靠点处理/去重)
|                                       #   - flatten/unflatten 序列化
|                                       #   - appendStages 模板方法
|                                       #   - AppendGradientFillStages 颜色填充
|                                       #   - AppendInterpolatedToDstStages 色彩转换
|-- SkLinearGradient.h                  # 线性渐变头文件
|-- SkLinearGradient.cpp                # 线性渐变实现 (112 行)
|-- SkRadialGradient.h                  # 径向渐变头文件
|-- SkRadialGradient.cpp                # 径向渐变实现 (102 行)
|-- SkSweepGradient.h                   # 扫描渐变头文件
|-- SkSweepGradient.cpp                 # 扫描渐变实现 (147 行)
|-- SkConicalGradient.h                 # 锥形渐变头文件
|-- SkConicalGradient.cpp               # 锥形渐变实现 (316 行)
```

## 关键类与函数

### SkGradientBaseShader (渐变基类)

`SkGradientBaseShader` 继承自 `SkShaderBase`,是所有渐变着色器共享的基类。它管理渐变的核心数据:

**核心数据成员:**
- **`fColors`** (`SkColor4f*`): 颜色停靠点数组,存储在 `fStorage` 内联缓冲区中。
- **`fPositions`** (`SkScalar*`): 位置数组(0.0~1.0),若停靠点均匀分布则为 `nullptr` 以节省内存。
- **`fColorCount`** (`size_t`): 颜色数量,可能比用户输入多 0~2 个(隐式首尾停靠点)。
- **`fColorSpace`** (`sk_sp<SkColorSpace>`): 停靠点颜色的色彩空间,默认为 sRGB。
- **`fInterpolation`** (`SkGradient::Interpolation`): 插值配置,包含预乘模式、插值色彩空间、色相方法。
- **`fPtsToUnit`** (`SkMatrix`): 从世界坐标到单位渐变空间的变换矩阵。
- **`fTileMode`** (`SkTileMode`): 平铺模式(Clamp、Repeat、Mirror、Decal)。
- **`kInlineStopCount = 4`**: 内联存储优化,4 个停靠点以内不需要堆分配。

**构造函数停靠点处理逻辑:**
1. 检测是否需要在 t=0 和 t=1 处插入隐式停靠点(`fFirstStopIsImplicit`, `fLastStopIsImplicit`)。
2. 分配 `fStorage` 缓冲区用于存储颜色和位置。
3. 如果位置均匀分布,将 `fPositions` 设为 `nullptr`。
4. 去除重复停靠点(保留最左和最右颜色),非 Clamp 模式下忽略端点重复。

**关键方法:**

```cpp
// 模板方法: 通用渐变管线构建
bool appendStages(const SkStageRec&, const SkShaders::MatrixRec&) const override;

// 钩子方法: 子类实现特定的坐标映射
virtual void appendGradientStages(SkArenaAlloc* alloc,
                                  SkRasterPipeline* tPipeline,
                                  SkRasterPipeline* postPipeline) const = 0;

// 静态方法: 颜色填充阶段 (分段线性插值)
static void AppendGradientFillStages(SkRasterPipeline* p, SkArenaAlloc* alloc,
                                     const SkPMColor4f* colors,
                                     const SkScalar* positions, int count);

// 静态方法: 插值色彩空间到目标色彩空间的转换
static void AppendInterpolatedToDstStages(SkRasterPipeline* p, SkArenaAlloc* alloc,
                                          bool colorsAreOpaque,
                                          const Interpolation& interpolation,
                                          const SkColorSpace* intermediateColorSpace,
                                          const SkColorSpace* dstColorSpace);

// 退化渐变处理
static sk_sp<SkShader> MakeDegenerateGradient(const SkGradient::Colors&);

// 渐变有效性验证
static bool ValidGradient(SkSpan<const SkColor4f>, SkTileMode, const Interpolation&);
```

### SkColor4fXformer (颜色空间变换器)

辅助结构体,负责在 `appendStages` 中将渐变颜色从存储色彩空间转换为插值色彩空间:

```cpp
struct SkColor4fXformer {
    SkColor4fXformer(const SkGradientBaseShader* shader, SkColorSpace* dst,
                     bool forceExplicitPositions = false);
    ColorStorage fColors;                     // 转换后的预乘颜色
    PositionStorage fPositionStorage;         // 位置(可能被强制显式化)
    const float* fPositions;                  // 指向位置数组
    sk_sp<SkColorSpace> fIntermediateColorSpace; // 中间插值色彩空间
};
```

### SkGradientScope (反序列化作用域)

管理反序列化过程中的临时存储,避免堆分配:

```cpp
class SkGradientScope {
    std::optional<SkGradient> unflatten(SkReadBuffer&, SkMatrix* legacyLocalMatrix);
private:
    skia_private::STArray<16, SkColor4f> fColorStorage;
    skia_private::STArray<16, SkScalar> fPositionStorage;
};
```

### SkLinearGradient (线性渐变)

线性渐变是最简单的渐变类型,沿两点之间的直线方向进行颜色过渡。

- **构造参数**: 起点 `fStart`、终点 `fEnd`。
- **坐标映射**: 通过 `pts_to_unit_matrix()` 将两点映射到单位空间,使得 t 值直接等于变换后的 x 坐标。
- **`appendGradientStages()`**: 空实现。线性渐变不需要额外的管线阶段,因为 `ptsToUnit` 矩阵已经将世界坐标映射到了 t 值。
- **工厂方法**: `SkShaders::LinearGradient(pts, grad, lm)`,处理退化情况(两点重合)。

### SkRadialGradient (径向渐变)

径向渐变从中心点向外按圆形扩散进行颜色过渡。

- **构造参数**: 中心点 `fCenter`、半径 `fRadius`。
- **坐标映射**: `rad_to_unit_matrix()` 将圆映射到单位圆,然后 `appendGradientStages` 添加 `xy_to_radius` 操作计算 `t = sqrt(x^2 + y^2)`。
- **工厂方法**: `SkShaders::RadialGradient(center, radius, grad, lm)`，处理退化情况(半径为零)。

### SkSweepGradient (扫描渐变)

扫描渐变围绕中心点按角度进行颜色过渡,类似圆锥截面的展开。

- **构造参数**: 中心点 `fCenter`、起始参数 `t0`(对应起始角度)、终止参数 `t1`(对应终止角度)。内部存储为 `fTBias = -t0`、`fTScale = 1/(t1-t0)`。
- **坐标映射**: `appendGradientStages` 添加 `xy_to_unit_angle` 操作计算角度参数,然后通过缩放和偏移矩阵将 [t0, t1] 映射到 [0, 1]。
- **工厂方法**: `SkShaders::SweepGradient(center, startAngle, endAngle, grad, lm)`。当 t 范围覆盖 [0, 1] 时自动优化为 Clamp 模式。
- **角度单位**: 公共 API 使用角度(0~360),内部转换为 t 参数(0~1)。

### SkConicalGradient (锥形渐变)

锥形渐变(又称两点锥形渐变)描述两个不同圆之间的颜色过渡,是最复杂的渐变类型。

- **构造参数**: 起始圆心 `fCenter1`、起始半径 `fRadius1`、终止圆心 `fCenter2`、终止半径 `fRadius2`。
- **三种子类型** (`SkConicalGradient::Type`):
  - **`kRadial`**: 两圆同心(`c0 == c1`)。简化为径向渐变,通过缩放和偏移调整 t 范围。
  - **`kStrip`**: 两圆半径相等(`r0 == r1`)。使用 `xy_to_2pt_conical_strip` 操作。
  - **`kFocal`**: 一般情况。使用 `FocalData` 结构体存储焦点参数。

- **FocalData 结构体**:
  - `fR1`: 映射后的 r1 值。
  - `fFocalX`: 焦点 x 坐标(f 值)。
  - `fIsSwapped`: 是否交换了 r0/r1。
  - `isFocalOnCircle()`: 焦点是否在终止圆上(线性退化)。
  - `isWellBehaved()`: 焦点不在圆上且 r1 > 1(最简单的焦点情况)。
  - `isNativelyFocal()`: 焦点是否在原点。

- **管线阶段选择逻辑**:
  ```
  Focal 子类型:
    isFocalOnCircle    -> xy_to_2pt_conical_focal_on_circle
    isWellBehaved      -> xy_to_2pt_conical_well_behaved
    isSwapped/负       -> xy_to_2pt_conical_smaller
    其他               -> xy_to_2pt_conical_greater

  后处理:
    !isWellBehaved     -> mask_2pt_conical_degenerates
    负方向             -> negate_x
    !isNativelyFocal   -> alter_2pt_conical_compensate_focal
    isSwapped          -> alter_2pt_conical_unswap
  ```

- **`MapToUnitX()`**: 将两圆心映射到 {(0,0), (1,0)} 的变换矩阵。
- **工厂方法**: `SkShaders::TwoPointConicalGradient(start, startRadius, end, endRadius, grad, lm)`。处理多种退化情况(同心圆、半径为零、完全退化等)。

### 序列化格式 (GradientSerializationFlags)

渐变的序列化使用紧凑的位标志格式:

```
Bit 31:    kHasPosition_GSF          - 是否有显式位置
Bit 30:    kHasLegacyLocalMatrix_GSF - 是否有旧版本本地矩阵
Bit 29:    kHasColorSpace_GSF        - 是否有自定义色彩空间
Bit 12~28: (未使用)
Bit 8~11:  fTileMode                 - 平铺模式 (4 bit)
Bit 4~7:   Interpolation::ColorSpace - 插值色彩空间 (4 bit)
Bit 1~3:   Interpolation::HueMethod  - 色相插值方法 (3 bit)
Bit 0:     Interpolation::InPremul   - 是否在预乘空间插值
```

### 宏定义

```cpp
// 从 SkGradient 参数创建颜色和位置的 SkSpan
MAKE_COLORS_POS_SPANS(colorPtr, posPtr, count)

// 渐变工厂函数的通用早期退出检查
// 验证参数、处理单色退化、检查矩阵可逆性
GRADIENT_FACTORY_EARLY_EXIT(grad, lm)
```

## 依赖关系

### 向上依赖(被本目录使用)

| 依赖模块 | 说明 |
|----------|------|
| `src/shaders/SkShaderBase.h` | 着色器基类定义 |
| `include/effects/SkGradient.h` | 渐变描述结构体 `SkGradient`(公共 API) |
| `include/core/SkColorSpace.h` | 色彩空间管理 |
| `include/core/SkTileMode.h` | 平铺模式枚举 |
| `src/core/SkRasterPipeline.h` | 光栅化管线 |
| `src/core/SkRasterPipelineOpList.h` | 管线操作码列表 |
| `src/core/SkRasterPipelineOpContexts.h` | 管线操作上下文(GradientCtx 等) |
| `src/core/SkColorSpaceXformSteps.h` | 色彩空间转换步骤 |
| `src/core/SkReadBuffer` / `SkWriteBuffer` | 序列化/反序列化缓冲区 |
| `src/base/SkArenaAlloc` | 竞技场分配器 |
| `src/base/SkVx.h` | SIMD 向量操作 |
| `modules/skcms/skcms.h` | 色彩管理模块 |

### 向下依赖(依赖本目录的模块)

| 依赖模块 | 说明 |
|----------|------|
| `src/gpu/ganesh/gradients/` | Ganesh GPU 后端的渐变 Fragment Processor |
| `src/gpu/graphite/` | Graphite GPU 后端的渐变着色器转换 |
| `src/shaders/SkShaderBase.h` | 通过 `SK_ALL_GRADIENTS(M)` 宏引用四种渐变类型 |
| `src/shaders/SkLocalMatrixShader.h` | 渐变工厂方法通过 `makeWithLocalMatrix` 包装输出 |

## 设计模式分析

### 1. 模板方法模式 (Template Method)

这是本目录最核心的设计模式。`SkGradientBaseShader::appendStages()` 定义了渐变光栅化的标准流程:

```
appendStages() 流程:
  1. matrixRec.apply() -- 应用坐标变换(CTM + 本地矩阵)
  2. matrixRec 进一步 concat(fPtsToUnit) -- 应用点到单位空间矩阵
  3. SkColor4fXformer 执行颜色空间转换
  4. appendGradientStages()  <-- [钩子方法: 子类重写]
  5. 添加 TileMode 阶段 (clamp/repeat/mirror/decal)
  6. AppendGradientFillStages() -- 颜色填充(分段线性插值)
  7. AppendInterpolatedToDstStages() -- 插值空间到目标色彩空间转换
  8. 添加 premul 阶段(如果需要)
```

子类只需实现第 4 步的坐标映射:
- **SkLinearGradient**: 空实现(t = x,已由 ptsToUnit 完成)
- **SkRadialGradient**: `xy_to_radius`(t = sqrt(x^2+y^2))
- **SkSweepGradient**: `xy_to_unit_angle` + scale/bias
- **SkConicalGradient**: 根据子类型选择多种管线操作

### 2. 策略模式 (Strategy) + 状态模式

`SkConicalGradient` 内部通过 `Type` 枚举和 `FocalData` 实现了策略模式与状态模式的结合。不同的几何配置(同心圆、等半径、一般焦点)选择不同的管线操作序列,而不是通过继承产生更多子类。

### 3. 工厂方法模式 (Factory Method)

每种渐变类型的创建都通过命名空间 `SkShaders` 中的静态工厂方法完成:
- `SkShaders::LinearGradient()`
- `SkShaders::RadialGradient()`
- `SkShaders::SweepGradient()`
- `SkShaders::TwoPointConicalGradient()`

工厂方法统一处理参数验证、退化检测和对象创建,确保返回的着色器始终处于有效状态。`GRADIENT_FACTORY_EARLY_EXIT` 宏封装了通用的早期退出检查。

### 4. 享元模式 (Flyweight)

颜色和位置数据使用内联存储优化(`kInlineStopCount = 4`),通过 `AutoSTMalloc` 在栈上预分配小型缓冲区。仅当停靠点数量超过 4 个时才进行堆分配,减少了常见用例的内存分配开销。

### 5. 预计算优化模式

颜色填充阶段通过预计算 `factor` 和 `bias` 将运行时的颜色插值简化为简单的 `color = factor * t + bias` 线性运算。这避免了逐像素的二分查找和除法运算,是典型的以空间换时间的优化策略。三种情况分别处理:
- **2 停靠点均匀**: `evenly_spaced_2_stop_gradient`(最快路径)
- **N 停靠点均匀**: `evenly_spaced_gradient`(通过索引直接定位)
- **N 停靠点非均匀**: 基于阈值的查找 + 线性插值

## 数据流

### 渐变着色器创建流程

```
用户调用 SkShaders::LinearGradient(pts, grad, localMatrix)
     |
     v
GRADIENT_FACTORY_EARLY_EXIT 宏检查:
  - ValidGradient(): 验证颜色数、TileMode、插值参数
  - 单色渐变退化为 SkColorShader
  - 本地矩阵不可逆则返回 nullptr
     |
     v
退化检测:
  - 线性: 两点重合 -> MakeDegenerateGradient()
  - 径向: 半径为零 -> MakeDegenerateGradient()
  - 扫描: 角度重合 -> MakeDegenerateGradient() 或特殊 Clamp 处理
  - 锥形: 多种退化情况(同心等半径、半径为零等)
     |
     v
构造具体渐变对象:
  sk_make_sp<SkLinearGradient>(pts, grad)
     |
     v
SkGradientBaseShader 构造函数:
  1. 计算 ptsToUnit 矩阵
  2. 插入隐式首尾停靠点 (如果 pos[0] > 0 或 pos[n-1] < 1)
  3. 检测均匀分布 -> fPositions = nullptr
  4. 去除中间重复停靠点
     |
     v
s->makeWithLocalMatrix(lm) 包装为 SkLocalMatrixShader
     |
     v
返回 sk_sp<SkShader>
```

### 渐变光栅化管线构建流程

```
SkGradientBaseShader::appendStages(rec, matrixRec)
     |
     v
Step 1: 颜色空间变换
  SkColor4fXformer xformer(this, dstColorSpace)
  - 将停靠点颜色从存储色彩空间转换为插值色彩空间
  - 如果需要,强制生成显式位置数组
     |
     v
Step 2: 坐标变换
  matrixRec.concat(fPtsToUnit).apply(rec)
  - 向管线添加 seed_shader (如果 CTM 尚未应用)
  - 向管线添加矩阵变换阶段
     |
     v
Step 3: 子类坐标映射 [钩子方法]
  appendGradientStages(alloc, tPipeline, postPipeline)
  - 线性: (空)
  - 径向: xy_to_radius
  - 扫描: xy_to_unit_angle + scale/bias
  - 锥形: 根据 Type 选择对应操作
     |
     v
Step 4: TileMode 处理
  根据 fTileMode 添加:
  - kClamp:  clamp_x_1
  - kRepeat: repeat_x_1
  - kMirror: mirror_x_1
  - kDecal:  decal_x + check_decal_mask (post)
     |
     v
Step 5: 颜色填充
  AppendGradientFillStages(p, alloc, colors, positions, count)
  - 2-stop: evenly_spaced_2_stop_gradient
  - 均匀:  evenly_spaced_gradient
  - 非均匀: gradient (带阈值查找)
     |
     v
Step 6: 色彩空间转换到目标
  AppendInterpolatedToDstStages(p, alloc, ...)
  - 插值空间 -> 目标色彩空间
     |
     v
Step 7: 预乘处理
  - 如果需要: premul 阶段
     |
     v
Step 8: 后处理管线
  - 锥形退化遮罩: apply_vector_mask
  - Decal 遮罩: apply_vector_mask
```

### 锥形渐变子类型判定流程

```
SkConicalGradient::Create(c0, r0, c1, r1, desc, lm)
     |
     v
两圆心重合? (c0 == c1)
  |-- 是 --> r0 == r1? --> 退化返回 nullptr
  |          r0 == 0?  --> 简化为 RadialGradient
  |          其他      --> Type::kRadial (同心圆变体)
  |
  +-- 否 --> 计算 MapToUnitX 矩阵
             r0 == r1? --> Type::kStrip (条带)
             其他      --> Type::kFocal (焦点)
                            |
                            v
                       FocalData::set(r0/d, r1/d, &matrix)
                       计算焦点位置和缩放变换
```

## 相关文档与参考

- **渐变公共 API**: `include/effects/SkGradient.h` -- `SkGradient` 结构体定义(颜色、位置、TileMode、插值参数)
- **着色器基类**: `src/shaders/SkShaderBase.h` -- `GradientType` 枚举、`GradientInfo` 结构体、`SK_ALL_GRADIENTS(M)` 宏
- **光栅化管线操作**: `src/core/SkRasterPipelineOpList.h` -- 渐变相关操作码定义
- **管线上下文**: `src/core/SkRasterPipelineOpContexts.h` -- `GradientCtx`、`EvenlySpaced2StopGradientCtx`、`Conical2PtCtx` 等
- **色彩管理**: `modules/skcms/skcms.h` -- 用于色彩空间转换的底层库
- **Ganesh GPU 渐变**: `src/gpu/ganesh/gradients/` -- GPU 后端的渐变 Fragment Processor 实现
- **锥形渐变设计**: https://skia.org/dev/design/conical -- 官方锥形渐变算法设计文档
- **CSS Color 4 插值**: https://www.w3.org/TR/css-color-4/#interpolation -- 渐变插值色彩空间的标准参考
- **父目录文档**: `src/shaders/README.md` -- 着色器系统总体架构
