# src/effects/colorfilters - 颜色滤镜实现

## 概述

`src/effects/colorfilters` 目录实现了 Skia 图形库中所有**颜色滤镜**（Color Filter）的具体子类。颜色滤镜是 Skia 渲染管线中的重要组件，能够在绘制过程中对每个像素的颜色值进行变换。所有颜色滤镜均继承自本目录中定义的 `SkColorFilterBase` 基类，该基类又继承自公共接口 `SkColorFilter`。

Skia 的颜色滤镜体系共包含 **8 种具体实现类型**，通过 `SK_ALL_COLOR_FILTERS` 宏统一枚举：`BlendMode`（混合模式）、`ColorSpaceXform`（色彩空间转换）、`Compose`（组合）、`Gaussian`（高斯）、`Matrix`（矩阵）、`Runtime`（运行时）、`Table`（查找表）和 `WorkingFormat`（工作色彩格式）。每种类型都针对特定的颜色变换需求进行了优化实现。

颜色滤镜的核心执行机制基于 Skia 的**光栅化管线**（Raster Pipeline）。每个滤镜子类必须实现 `appendStages()` 纯虚函数，将自己的颜色变换操作以管线阶段（stages）的形式追加到 `SkRasterPipeline` 中。这种设计使得多个颜色滤镜可以高效地串联执行，避免了中间缓冲区的分配和像素的多次读写。

除了光栅化管线执行路径外，颜色滤镜还支持通过 `onFilterColor4f()` 直接对单个颜色值进行变换，这在需要预计算颜色或判断滤镜特性（如 `affectsTransparentBlack()`）时非常有用。默认实现会构建一个临时的单像素光栅管线来完成颜色变换。

颜色滤镜体系还提供了完整的**序列化/反序列化**支持。所有滤镜类都实现了 `SkFlattenable` 接口，通过 `flatten()` 写入和 `CreateProc()` 读取，支持向后兼容旧版序列化格式。每种滤镜类型都有对应的注册函数（如 `SkRegisterModeColorFilterFlattenable()`），确保反序列化时能正确匹配类型。

## 架构图

```
                    +------------------------+
                    |    SkColorFilter        |
                    |  (include/core 公共接口) |
                    +-----------+------------+
                                |
                    +-----------v------------+
                    |  SkColorFilterBase      |
                    |  (颜色滤镜基类)         |
                    |  - appendStages() = 0   |
                    |  - type() = 0           |
                    |  - onFilterColor4f()    |
                    |  - affectsTransparent   |
                    |    Black()              |
                    +-----------+------------+
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
+-------v---+ +----v------+ +--v--------+ +v---------+ |
|BlendMode  | |Matrix     | |Compose    | |Table     | |
|ColorFilter| |ColorFilter| |ColorFilter| |ColorFilter| |
|           | |           | |           | |           | |
|fColor     | |fMatrix[20]| |fOuter     | |fTable    | |
|fMode      | |fDomain    | |fInner     | |(SkColor  | |
|           | |fClamp     | |           | | Table)   | |
+-----------+ +-----------+ +-----------+ +----------+ |
        |           |           |                       |
+-------v---+ +----v------+ +--v--------+ +----------+ |
|ColorSpace | |Gaussian   | |Runtime    | |Working   | |
|Xform      | |ColorFilter| |ColorFilter| |Format    | |
|ColorFilter| |           | |           | |ColorFilter|
|           | |           | |fEffect    | |           |
|fSrc, fDst | |(alpha ->  | |fUniforms  | |fChild    |
|fSteps     | | gaussian) | |fChildren  | |fWorking  |
+-----------+ +-----------+ +-----------+ |FormatCalc|
                                          +-----------+
                                                |
                               +----------------v---------+
                               |   SkRasterPipeline        |
                               |   (光栅化管线执行引擎)      |
                               +---------------------------+
```

## 目录结构

```
src/effects/colorfilters/
|-- BUILD.bazel                          # Bazel 构建配置
|-- SkColorFilterBase.h                  # 颜色滤镜基类头文件（定义所有类型枚举）
|-- SkColorFilterBase.cpp                # 颜色滤镜基类实现（默认 onFilterColor4f）
|-- SkBlendModeColorFilter.h             # 混合模式颜色滤镜头文件
|-- SkBlendModeColorFilter.cpp           # 混合模式颜色滤镜实现
|-- SkColorSpaceXformColorFilter.h       # 色彩空间转换滤镜头文件
|-- SkColorSpaceXformColorFilter.cpp     # 色彩空间转换滤镜实现
|-- SkComposeColorFilter.h              # 组合颜色滤镜头文件
|-- SkComposeColorFilter.cpp            # 组合颜色滤镜实现
|-- SkGaussianColorFilter.h             # 高斯颜色滤镜头文件
|-- SkGaussianColorFilter.cpp           # 高斯颜色滤镜实现
|-- SkMatrixColorFilter.h               # 矩阵颜色滤镜头文件
|-- SkMatrixColorFilter.cpp             # 矩阵颜色滤镜实现
|-- SkRuntimeColorFilter.h              # 运行时颜色滤镜头文件
|-- SkRuntimeColorFilter.cpp            # 运行时颜色滤镜实现
|-- SkTableColorFilter.h                # 查找表颜色滤镜头文件
|-- SkTableColorFilter.cpp              # 查找表颜色滤镜实现
|-- SkWorkingFormatColorFilter.h         # 工作色彩格式滤镜头文件
|-- SkWorkingFormatColorFilter.cpp       # 工作色彩格式滤镜实现
```

## 关键类与函数

### SkColorFilterBase - 颜色滤镜基类

`SkColorFilterBase` 是所有颜色滤镜实现的基类，定义了以下核心接口：

```cpp
class SkColorFilterBase : public SkColorFilter {
public:
    // 将颜色变换操作追加到光栅化管线（纯虚函数，所有子类必须实现）
    virtual bool appendStages(const SkStageRec& rec, bool shaderIsOpaque) const = 0;

    // 返回滤镜类型枚举
    virtual Type type() const = 0;

    // 判断滤镜是否不修改 alpha 通道
    virtual bool onIsAlphaUnchanged() const { return false; }

    // 判断滤镜是否影响透明黑色（用于优化决策）
    bool affectsTransparentBlack() const;

    // 直接对单个颜色值进行变换
    virtual SkPMColor4f onFilterColor4f(const SkPMColor4f& color, SkColorSpace* dstCS) const;
};
```

辅助函数 `as_CFB()` 和 `as_CFB_sp()` 提供了从 `SkColorFilter` 到 `SkColorFilterBase` 的安全向下转型。

### SkBlendModeColorFilter - 混合模式颜色滤镜

将指定颜色与源像素按照 `SkBlendMode` 进行混合。颜色始终以 sRGB 存储，在实际使用时转换到目标色彩空间。

```cpp
class SkBlendModeColorFilter final : public SkColorFilterBase {
    SkColor4f fColor;   // 混合颜色，sRGB 格式
    SkBlendMode fMode;  // 混合模式
};
```

工厂方法 `SkColorFilters::Blend()` 会自动优化特殊情况：`kClear` 模式转为 `kSrc`，全透明的 `kSrcOver` 转为 `kDst`，以及识别各种无操作（noop）组合并返回 `nullptr`。

### SkMatrixColorFilter - 矩阵颜色滤镜

使用 4x5 矩阵（20 个浮点数）对颜色进行线性变换。支持在 RGBA 和 HSLA 两个域中操作：

```cpp
class SkMatrixColorFilter final : public SkColorFilterBase {
    float fMatrix[20];        // 4x5 颜色变换矩阵
    bool fAlphaIsUnchanged;   // alpha 通道是否不变（缓存结果）
    Domain fDomain;           // 操作域：kRGBA 或 kHSLA
    Clamp fClamp;             // 是否钳位到 [0,1]
};
```

在 `appendStages()` 中，HSLA 域需要额外的 `rgb_to_hsl` 和 `hsl_to_rgb` 管线阶段。矩阵运算通过 `SkRasterPipelineOp::matrix_4x5` 高效执行。

### SkComposeColorFilter - 组合颜色滤镜

将两个颜色滤镜串联执行，先执行内部滤镜（`fInner`），再执行外部滤镜（`fOuter`）：

```cpp
class SkComposeColorFilter final : public SkColorFilterBase {
    sk_sp<SkColorFilterBase> fOuter;  // 外部滤镜（后执行）
    sk_sp<SkColorFilterBase> fInner;  // 内部滤镜（先执行）
};
```

通过 `SkColorFilter::makeComposed()` 创建，`appendStages()` 依次追加内外滤镜的管线阶段。

### SkColorSpaceXformColorFilter - 色彩空间转换滤镜

在源色彩空间和目标色彩空间之间进行颜色变换：

```cpp
class SkColorSpaceXformColorFilter final : public SkColorFilterBase {
    const sk_sp<SkColorSpace> fSrc;      // 源色彩空间
    const sk_sp<SkColorSpace> fDst;      // 目标色彩空间
    SkColorSpaceXformSteps fSteps;       // 预计算的变换步骤
};
```

使用 `SkColorSpaceXformSteps` 进行高效的色彩空间转换，包含传递函数和色域映射。

### SkGaussianColorFilter - 高斯颜色滤镜

将输入颜色的 alpha 值映射到高斯曲线，然后输出预乘白色。主要用于阴影和模糊相关的内部效果：

```cpp
class SkGaussianColorFilter final : public SkColorFilterBase {
    // 无额外成员，行为固定：alpha -> 高斯映射 -> 预乘白色
};
```

### SkRuntimeColorFilter - 运行时颜色滤镜

使用 SkSL 编写的自定义颜色变换程序：

```cpp
class SkRuntimeColorFilter : public SkColorFilterBase {
    sk_sp<SkRuntimeEffect> fEffect;                        // SkSL 运行时效果
    sk_sp<const SkData> fUniforms;                         // uniform 参数数据
    std::vector<SkRuntimeEffect::ChildPtr> fChildren;      // 子效果引用
};
```

通过 `SkRuntimeEffect` 编译 SkSL 程序，支持光栅管线（RP）后端执行。反序列化时支持 Luma 和 Overdraw 等已知滤镜的特殊处理。

### SkTableColorFilter - 查找表颜色滤镜

使用 `SkColorTable`（包含 256 个条目的查找表）对每个颜色分量进行映射：

```cpp
class SkTableColorFilter final : public SkColorFilterBase {
    sk_sp<SkColorTable> fTable;  // 颜色查找表
};
```

查找表存储在 `SkBitmap` 中，通过 `table_a`、`table_r`、`table_g`、`table_b` 管线阶段执行。

### SkWorkingFormatColorFilter - 工作色彩格式滤镜

包装另一个颜色滤镜，在指定的工作色彩格式（传递函数、色域、alpha 类型）中执行：

```cpp
class SkWorkingFormatColorFilter final : public SkColorFilterBase {
    sk_sp<SkColorFilter> fChild;                          // 被包装的子滤镜
    SkWorkingFormatCalculator fWorkingFormatCalculator;    // 工作格式计算器
};
```

在 `appendStages()` 中，先将颜色从目标空间转到工作空间，执行子滤镜，再转回目标空间。这对于需要在线性色彩空间中操作的效果（如高对比度滤镜）至关重要。

## 依赖关系

### 向上依赖（被以下模块使用）

- `include/core/SkColorFilter` - 公共接口，通过 `SkColorFilters` 命名空间提供工厂方法
- `src/effects/imagefilters/SkColorFilterImageFilter` - 图像滤镜中使用颜色滤镜
- `src/core/SkPaint` - 绘制属性中引用颜色滤镜
- `src/gpu/ganesh/` - Ganesh GPU 后端将颜色滤镜转换为 GPU 着色器片段
- `src/gpu/graphite/` - Graphite GPU 后端同样使用颜色滤镜

### 向下依赖（依赖以下模块）

- `src/core/SkRasterPipeline` - 光栅化管线，颜色变换的执行引擎
- `src/core/SkRasterPipelineOpList.h` - 管线操作枚举（`matrix_4x5`、`clamp_01` 等）
- `src/core/SkColorSpaceXformSteps` - 色彩空间变换步骤
- `src/core/SkEffectPriv.h` - 效果的内部辅助工具（`SkStageRec` 结构体）
- `src/core/SkReadBuffer` / `SkWriteBuffer` - 序列化/反序列化
- `src/core/SkBlendModePriv.h` - 混合模式的管线追加函数
- `src/core/SkKnownRuntimeEffects` - 预编译运行时效果
- `src/sksl/codegen/SkSLRasterPipelineBuilder` - SkSL 到光栅管线的编译
- `modules/skcms/skcms.h` - 颜色管理系统（传递函数、色域矩阵）
- `include/core/SkColorTable` - 颜色查找表数据结构

## 设计模式分析

### 类型枚举与多态分派

`SkColorFilterBase::Type` 枚举通过 `SK_ALL_COLOR_FILTERS` 宏自动生成，配合 `type()` 虚函数实现运行时类型识别（RTTI 的轻量替代）。这种模式允许 GPU 后端根据滤镜类型选择最优的着色器生成路径，避免了 `dynamic_cast` 的开销：

```cpp
enum class Type {
    kNoop,
    kBlendMode,
    kColorSpaceXform,
    kCompose,
    kGaussian,
    kMatrix,
    kRuntime,
    kTable,
    kWorkingFormat,
};
```

### 装饰器模式（Decorator Pattern）

`SkComposeColorFilter` 和 `SkWorkingFormatColorFilter` 都是装饰器模式的经典应用：

- `SkComposeColorFilter`：将两个颜色滤镜组合为一个，对外表现为单个滤镜
- `SkWorkingFormatColorFilter`：在子滤镜执行前后插入色彩空间转换，增强了子滤镜的色彩空间感知能力

### 空对象优化

`SkColorFilters::Blend()` 工厂方法中，对于不会产生任何视觉效果的参数组合（如 `kDst` 模式、透明色的 `kSrcOver` 等），直接返回 `nullptr` 而非创建空操作对象。这遵循了 Skia 中"null 表示无效果"的惯例，上层代码可以跳过整个滤镜处理路径。

### 管线阶段追加模式

所有颜色滤镜通过 `appendStages()` 将操作追加到 `SkRasterPipeline`。这是一种**构建器模式**的变体：滤镜不直接执行颜色变换，而是将变换步骤"描述"到管线中，由管线统一执行。这使得以下优化成为可能：
- 多个滤镜的管线阶段可以在同一次像素遍历中连续执行
- `SkComposeColorFilter` 只需连续调用两个子滤镜的 `appendStages()`
- GPU 后端可以将管线阶段转换为 GPU 着色器指令

### Flattenable 注册机制

每种滤镜类型都有独立的注册函数（如 `SkRegisterModeColorFilterFlattenable()`），在序列化系统初始化时调用。注册函数使用 `SK_REGISTER_FLATTENABLE` 宏注册当前类名，并通过 `SkFlattenable::Register()` 注册旧类名以保持向后兼容：

```cpp
void SkRegisterMatrixColorFilterFlattenable() {
    SK_REGISTER_FLATTENABLE(SkMatrixColorFilter);
    SkFlattenable::Register("SkColorFilter_Matrix", SkMatrixColorFilter::CreateProc);
}
```

## 数据流

### 颜色滤镜执行流程（光栅管线路径）

```
输入像素颜色 (SkPMColor4f, 预乘 alpha)
    |
    v
SkStageRec 构建 (包含 pipeline、alloc、dstCS 等上下文)
    |
    v
appendStages(rec, shaderIsOpaque)
    |
    +-- SkBlendModeColorFilter:
    |       1. move_src_dst (保存源颜色到 dst 寄存器)
    |       2. appendConstantColor (加载混合颜色到 src 寄存器)
    |       3. SkBlendMode_AppendStages (执行混合模式)
    |
    +-- SkMatrixColorFilter:
    |       1. unpremul (如果源不透明则跳过)
    |       2. rgb_to_hsl (如果是 HSLA 域)
    |       3. matrix_4x5 (应用 4x5 矩阵)
    |       4. hsl_to_rgb (如果是 HSLA 域)
    |       5. clamp_01 或 clamp_a_01
    |       6. premul (如果结果可能不透明)
    |
    +-- SkComposeColorFilter:
    |       1. fInner->appendStages() (先执行内部滤镜)
    |       2. fOuter->appendStages() (再执行外部滤镜)
    |
    +-- SkWorkingFormatColorFilter:
    |       1. dstToWorking->apply() (目标空间 -> 工作空间)
    |       2. fChild->appendStages() (在工作空间执行子滤镜)
    |       3. workingToDst->apply() (工作空间 -> 目标空间)
    |
    +-- SkRuntimeColorFilter:
    |       1. 获取 SkSL RP Program
    |       2. 准备 uniform 数据和子效果
    |       3. program->appendStages() (追加 SkSL 编译后的管线阶段)
    |
    +-- SkTableColorFilter:
    |       1. unpremul
    |       2. table_r, table_g, table_b, table_a (查表映射)
    |       3. premul
    |
    +-- SkColorSpaceXformColorFilter:
    |       1. fSteps.apply() (追加色彩空间变换步骤)
    |
    +-- SkGaussianColorFilter:
    |       1. gauss_a_to_rgba (alpha -> 高斯映射 -> 预乘白色)
    |
    v
输出像素颜色 (SkPMColor4f)
```

### 单色滤镜执行流程

```
SkPMColor4f inputColor
    |
    v
SkColorFilterBase::onFilterColor4f()
    |
    v
创建临时 SkSTArenaAlloc (2048 字节)
    |
    v
创建临时 SkRasterPipeline
    |
    +-- appendConstantColor(inputColor)
    +-- appendStages(rec)  // 追加滤镜的管线阶段
    +-- store_f32(&dst)    // 存储结果
    |
    v
pipeline.run(0, 0, 1, 1)  // 执行单像素管线
    |
    v
SkPMColor4f outputColor
```

### 序列化/反序列化流程

```
序列化：
    SkColorFilter -> flatten(SkWriteBuffer)
        |
        +-- 写入滤镜特定数据
        |   (颜色、矩阵、模式、子滤镜等)
        v
    二进制数据流

反序列化：
    二进制数据流 -> SkFlattenable::Deserialize()
        |
        v
    根据类型名查找 CreateProc
        |
        v
    CreateProc(SkReadBuffer) -> sk_sp<SkColorFilter>
        |
        +-- 读取滤镜特定数据
        +-- 调用工厂方法创建实例
        +-- 处理版本兼容性
        v
    SkColorFilter 实例
```

## 相关文档与参考

### 公共 API 入口

| 接口 | 描述 |
|------|------|
| `SkColorFilters::Blend(color, colorSpace, mode)` | 创建混合模式颜色滤镜 |
| `SkColorFilters::Matrix(array[20], clamp)` | 创建 RGBA 矩阵颜色滤镜 |
| `SkColorFilters::HSLAMatrix(array[20])` | 创建 HSLA 矩阵颜色滤镜 |
| `SkColorFilters::Table(table)` | 创建查找表颜色滤镜 |
| `SkColorFilter::makeComposed(inner)` | 创建组合颜色滤镜 |
| `SkColorFilters::LinearToSRGBGamma()` | 线性到 sRGB 转换 |
| `SkColorFilters::SRGBToLinearGamma()` | sRGB 到线性转换 |
| `SkRuntimeEffect::makeColorFilter(uniforms)` | 从 SkSL 创建运行时颜色滤镜 |

### 相关模块

- `src/effects/` - 效果子系统顶层，包含使用颜色滤镜的其他效果组件
- `src/effects/imagefilters/SkColorFilterImageFilter.cpp` - 将颜色滤镜适配为图像滤镜
- `src/core/SkColorFilterPriv.h` - 颜色滤镜的内部辅助函数（如 `WithWorkingFormat`）
- `src/gpu/ganesh/effects/GrSkSLFP` - Ganesh 后端的颜色滤镜 GPU 实现
- `src/gpu/graphite/KeyHelpers.cpp` - Graphite 后端的颜色滤镜键生成
- `include/core/SkColorFilter.h` - 颜色滤镜公共接口
- `include/effects/SkColorMatrix.h` - 颜色矩阵工具类
- `include/effects/SkRuntimeEffect.h` - 运行时效果框架
