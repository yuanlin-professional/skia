# SkGlobalInitialization_default - Skia 全局效果反序列化注册

> 源文件: `src/ports/SkGlobalInitialization_default.cpp`

## 概述

`SkGlobalInitialization_default.cpp` 是 Skia 图形库的全局初始化文件，负责将所有内置效果（effects）和图像滤镜（image filters）注册到 `SkFlattenable` 反序列化系统中。该文件是 Skia 序列化/反序列化（serialization/deserialization）基础设施的关键组成部分，确保通过 `SkFlattenable` 机制序列化的对象能够在后续被正确地重建。

该文件提供了两个核心初始化函数：`InitEffects()` 和 `InitImageFilters()`，分别用于注册常规效果和图像滤镜的反序列化工厂。如果定义了宏 `SK_DISABLE_EFFECT_DESERIALIZATION`，则这两个函数将为空实现，以减小最终二进制文件的体积。

Skia 的序列化系统允许将绘图操作、效果链和完整的图片（`SkPicture`）序列化为二进制格式，跨进程或存储后重建。反序列化过程依赖于全局注册表来识别序列化数据中的类型标识符并调用对应的工厂函数创建对象实例。

## 架构位置

此文件位于 Skia 的 `src/ports/` 目录下，属于平台可移植层（ports layer）。它在 Skia 初始化的早期阶段被调用，通过 `SkFlattenable::PrivateInitializer` 内部类来完成注册工作。该文件是默认实现，用户可以根据需要替换或修改它来裁剪不需要的效果。

在 Skia 的整体架构中，该文件处于以下位置：
- **上层**: `SkFlattenable` 序列化框架调用此初始化器
- **同层**: 与其他 `ports/` 平台抽象层文件并列
- **下层**: 注册来自 `src/effects/`、`src/shaders/`、`src/core/` 的具体效果实现

## 主要类与结构体

### `SkFlattenable::PrivateInitializer`
- 该文件实现了 `PrivateInitializer` 的两个静态方法
- `InitEffects()`: 注册着色器、颜色滤镜、混合器、遮罩滤镜、路径效果等
- `InitImageFilters()`: 注册所有图像滤镜

### 注册宏
- `SK_REGISTER_FLATTENABLE(ClassName)`: 将特定类直接注册到反序列化工厂
- `SkRegister*Flattenable()` 系列函数: 各效果模块提供的独立注册函数

## 公共 API 函数

### `SkFlattenable::PrivateInitializer::InitEffects()`
注册以下类别的效果：

**着色器 (Shaders)**:
- `SkRegisterBlendShaderFlattenable()` - 混合着色器
- `SkColorFilterShader` - 颜色滤镜着色器
- `SkRegisterColorShaderFlattenable()` - 纯色着色器
- `SkRegisterCoordClampShaderFlattenable()` - 坐标钳制着色器
- `SkRegisterEmptyShaderFlattenable()` - 空着色器
- `SkLocalMatrixShader` - 局部矩阵着色器
- `SkPictureShader` - 图片着色器
- 四种渐变着色器：锥形、线性、径向、扫描渐变
- `SkRegisterPerlinNoiseShaderFlattenable()` - 柏林噪声着色器
- `SkRegisterWorkingColorSpaceShaderFlattenable()` - 工作色彩空间着色器

**颜色滤镜 (Color Filters)**:
- 矩阵颜色滤镜、组合颜色滤镜、模式颜色滤镜、色彩空间变换滤镜、工作格式颜色滤镜、查表颜色滤镜

**混合器 (Blenders)**:
- `SkBlendModeBlender` - 混合模式混合器

**遮罩滤镜 (Mask Filters)**:
- `SkEmbossMaskFilter` - 浮雕遮罩滤镜
- 基础遮罩滤镜、着色器遮罩滤镜、查表遮罩滤镜

**路径效果 (Path Effects)**:
- 圆角路径效果、虚线效果、离散路径效果、线条2D路径效果、路径2D效果、路径1D效果、裁剪路径效果

### `SkFlattenable::PrivateInitializer::InitImageFilters()`
注册所有图像滤镜，这些滤镜用于对已渲染内容进行后处理：

- `SkRegisterBlendImageFilterFlattenable()` - 混合图像滤镜，将两个图像源进行混合
- `SkRegisterBlurImageFilterFlattenable()` - 模糊图像滤镜，实现高斯模糊效果
- `SkRegisterColorFilterImageFilterFlattenable()` - 颜色滤镜图像滤镜，在图像层面应用颜色变换
- `SkRegisterComposeImageFilterFlattenable()` - 组合图像滤镜，串联多个图像滤镜
- `SkRegisterCropImageFilterFlattenable()` - 裁剪图像滤镜
- `SkRegisterDisplacementMapImageFilterFlattenable()` - 位移映射图像滤镜
- `SkRegisterImageImageFilterFlattenable()` - 图像源图像滤镜
- `SkRegisterLightingImageFilterFlattenables()` - 光照图像滤镜（注意函数名复数形式，注册多个光照类型）
- `SkRegisterMagnifierImageFilterFlattenable()` - 放大镜图像滤镜
- `SkRegisterMatrixConvolutionImageFilterFlattenable()` - 矩阵卷积图像滤镜
- `SkRegisterMatrixTransformImageFilterFlattenable()` - 矩阵变换图像滤镜
- `SkRegisterMergeImageFilterFlattenable()` - 合并图像滤镜
- `SkRegisterMorphologyImageFilterFlattenables()` - 形态学图像滤镜（膨胀和腐蚀）
- `SkRegisterPictureImageFilterFlattenable()` - 图片图像滤镜
- `SkRegisterRuntimeImageFilterFlattenable()` - 运行时图像滤镜（SkSL 实现）
- `SkRegisterShaderImageFilterFlattenable()` - 着色器图像滤镜
- `SkLocalMatrixImageFilter` - 局部矩阵图像滤镜
- `SkRegisterLegacyDropShadowImageFilterFlattenable()` - 旧版投影图像滤镜（向后兼容）

## 内部实现细节

### 条件编译机制
该文件通过预处理器宏 `SK_DISABLE_EFFECT_DESERIALIZATION` 实现了条件编译：
- 当该宏被定义时，两个初始化函数为空函数体，不包含任何头文件，从而有效减小二进制体积
- 当该宏未定义时，包含所有必要的头文件并执行完整注册

```cpp
#if defined(SK_DISABLE_EFFECT_DESERIALIZATION)
    void SkFlattenable::PrivateInitializer::InitEffects() {}
    void SkFlattenable::PrivateInitializer::InitImageFilters() {}
#else
    // ... 完整注册逻辑
#endif
```

### 注册机制
注册过程使用两种互补的机制：

1. **`SK_REGISTER_FLATTENABLE` 宏**: 直接注册具有标准工厂方法的类。该宏内部将类的名称字符串与其 `CreateProc` 函数指针关联，存入全局注册表。适用于遵循标准反序列化工厂模式的类。

2. **独立的 `SkRegister*Flattenable()` 函数**: 各效果模块各自提供的注册函数，允许封装更复杂的注册逻辑。例如渐变着色器需要注册多个内部类型，或者某些模块需要在注册时执行额外的初始化步骤。

### 注册分组
效果注册在 `InitEffects()` 中按功能类别分组，并通过注释清晰标注：
- Shaders（着色器）- 13 个注册项
- Color filters（颜色滤镜）- 6 个注册项
- Blenders（混合器）- 1 个注册项
- Runtime effects（运行时效果）- 1 个统一注册入口
- Mask filters（遮罩滤镜）- 4 个注册项
- Path effects（路径效果）- 8 个注册项
- Misc（杂项）- 1 个注册项

图像滤镜在 `InitImageFilters()` 中独立注册，共 18 个注册项，包括一个旧版兼容的投影滤镜 `SkRegisterLegacyDropShadowImageFilterFlattenable()`。

### 旧版兼容性
`SkRegisterLegacyDropShadowImageFilterFlattenable()` 的存在表明 Skia 维护了向后兼容性，确保使用旧版序列化格式的数据仍然能够被正确反序列化。

## 依赖关系

该文件依赖 Skia 的多个核心和效果模块：
- **核心**: `SkFlattenable.h`, `SkBBHFactory.h`, `SkColorFilter.h`, `SkPathEffect.h`
- **效果**: `Sk1DPathEffect.h`, `Sk2DPathEffect.h`, `SkCornerPathEffect.h`, `SkDiscretePathEffect.h`, `SkImageFilters.h`, `SkOverdrawColorFilter.h`, `SkPerlinNoiseShader.h`, `SkRuntimeEffect.h`, `SkShaderMaskFilter.h`, `SkTableMaskFilter.h`
- **内部核心**: `SkBlendModeBlender.h`, `SkImageFilter_Base.h`, `SkLocalMatrixImageFilter.h`, `SkRecordedDrawable.h`
- **内部效果**: `SkDashImpl.h`, `SkEmbossMaskFilter.h`, `SkTrimPE.h`
- **着色器**: `SkBitmapProcShader.h`, `SkColorFilterShader.h`, `SkImageShader.h`, `SkLocalMatrixShader.h`, `SkPictureShader.h`, `SkShaderBase.h`, `SkGradientBaseShader.h`

## 设计模式与设计决策

1. **工厂注册模式**: 采用集中式注册而非分散式自注册，使得可以通过简单的宏开关来控制整个反序列化支持的启用或禁用。这种集中式设计也便于审计哪些效果被包含在最终构建中
2. **条件编译**: `SK_DISABLE_EFFECT_DESERIALIZATION` 宏提供了一种零成本的裁剪方式，对于不需要反序列化的场景可以显著减小体积。这对于嵌入式设备和 WebAssembly 构建尤为重要
3. **模块化注册**: 各效果模块各自提供注册函数，主文件仅负责调用协调，保持了良好的模块边界。新增效果只需要添加一行注册调用即可
4. **默认实现模式**: 文件名中的 `_default` 表明这是默认实现，用户可提供自定义版本以满足特定需求。例如，一个仅需要模糊滤镜的应用可以创建自己的初始化文件，仅注册所需的效果
5. **两阶段注册**: 将效果和图像滤镜分为两个独立的函数注册，允许更细粒度的控制。这种分离反映了图像滤镜相对于其他效果的独立性

## 性能考量

- 该文件在 Skia 初始化时仅执行一次，运行时无性能影响
- 通过 `SK_DISABLE_EFFECT_DESERIALIZATION` 可以在编译期彻底消除所有注册代码，减小二进制体积和启动时间
- 注册过程本身是轻量级的，仅将函数指针存入全局注册表
- 不使用动态分配或复杂的初始化逻辑，所有注册操作都是简单的函数调用
- 二进制体积方面，当禁用反序列化时，不仅注册代码被消除，相关的头文件包含也被移除，避免了链接器引入未使用的效果实现代码
- 分离 `InitEffects` 和 `InitImageFilters` 两个函数的设计允许未来如果需要，可以选择性地仅注册其中一类

## 相关文件

- `include/core/SkFlattenable.h` - 定义 `SkFlattenable` 基类及 `PrivateInitializer`
- `src/core/SkFlattenable.cpp` - `SkFlattenable` 的核心实现，包含全局注册表的管理
- `include/effects/` - 各种效果的公共头文件，定义了用户可直接使用的效果 API
- `src/effects/` - 效果的内部实现，包含私有类和注册函数
- `src/shaders/` - 着色器实现，包括渐变、图片、颜色等着色器
- `src/shaders/gradients/SkGradientBaseShader.h` - 渐变着色器基类，注册四种渐变类型
- `src/core/SkImageFilter_Base.h` - 图像滤镜基类
- `src/core/SkBlendModeBlender.h` - 混合模式混合器实现
- `src/core/SkRecordedDrawable.h` - 可录制的 Drawable 实现
- `src/effects/SkDashImpl.h` - 虚线路径效果的内部实现
- `src/effects/SkEmbossMaskFilter.h` - 浮雕遮罩滤镜实现
- `src/effects/SkTrimPE.h` - 路径裁剪效果实现
- `src/core/SkLocalMatrixImageFilter.h` - 局部矩阵图像滤镜，用于对图像滤镜应用自定义变换
