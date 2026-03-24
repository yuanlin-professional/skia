# DirectionalBlur - Skottie 方向模糊效果

> 源文件: `modules/skottie/src/effects/DirectionalBlur.cpp`

## 概述

DirectionalBlur 实现了 After Effects 中的"方向模糊"（Directional Blur / CC Radial Blur 的方向变体）效果。该效果在指定方向上应用一维高斯模糊，通过旋转-模糊-反旋转的三步变换实现。实现基于 `SkImageFilters` 图像滤镜链，使用 `sksg::ExternalImageFilter` 场景图节点。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），使用 `DiscardableAdapterBase` 将 Lottie 属性映射到 `sksg::ExternalImageFilter` 节点，再通过 `sksg::ImageFilterEffect` 将滤镜应用到图层。

```
AnimationBuilder
  └── EffectBuilder::attachDirectionalBlurEffect()
        ├── DirectionalBlurAdapter (DiscardableAdapterBase)
        │     └── sksg::ExternalImageFilter
        │           └── SkImageFilter 链
        └── sksg::ImageFilterEffect(layer, imageFilterNode)
```

## 主要类与结构体

### `DirectionalBlurAdapter`
- 继承自 `DiscardableAdapterBase<DirectionalBlurAdapter, sksg::ExternalImageFilter>`
- 两个动画属性：
  - `fDirection`：模糊方向角度
  - `fBlurLength`：模糊长度/强度

### 属性索引枚举
- `kDirection_Index = 0`
- `kBlurLength_Index = 1`

## 公共 API 函数

### `EffectBuilder::attachDirectionalBlurEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachDirectionalBlurEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：创建方向模糊适配器，然后将其包装为 `ImageFilterEffect` 应用到图层
- **返回值**：经 `sksg::ImageFilterEffect::Make()` 包装的渲染节点

## 内部实现细节

### onSync 方法

核心实现通过三个嵌套的 `SkImageFilter` 组合实现方向模糊：

```cpp
const auto rot = fDirection - 90;
auto filter =
    SkImageFilters::MatrixTransform(SkMatrix::RotateDeg(rot),       // 3. 反旋转
        SkSamplingOptions(SkFilterMode::kLinear),
        SkImageFilters::Blur(fBlurLength * kBlurSizeToSigma, 0,     // 2. 水平模糊
            SkImageFilters::MatrixTransform(SkMatrix::RotateDeg(-rot), // 1. 旋转
                SkSamplingOptions(SkFilterMode::kLinear), nullptr)));
```

执行流程：
1. **旋转**：将图像旋转 `-rot` 度，使目标模糊方向对齐到水平轴
2. **水平模糊**：应用一维高斯模糊（仅 X 方向，Y 方向 sigma=0）
3. **反旋转**：将图像旋转回原始角度

角度调整：`rot = fDirection - 90`，将 AE 的角度约定转换为 Skia 的旋转约定。

### 模糊参数转换

`fBlurLength * kBlurSizeToSigma` 将 AE 的模糊长度值转换为高斯模糊的 sigma 参数。`kBlurSizeToSigma` 是在基类或效果系统中定义的常量系数。

### 双重采样选项

两次矩阵变换均使用 `SkFilterMode::kLinear`（双线性过滤），平衡了旋转变换的图像质量和性能。

## 依赖关系

- **Skia 核心**：`SkMatrix`（旋转矩阵）、`SkImageFilter`
- **Skia 效果**：`SkImageFilters`（`MatrixTransform`、`Blur`）
- **Skia 采样**：`SkSamplingOptions`
- **Skottie 内部**：`Adapter.h`（`DiscardableAdapterBase`）、`Effects.h`（`EffectBinder`）
- **SkSG**：`SkSGRenderEffect.h`（`ExternalImageFilter`、`ImageFilterEffect`）

## 设计模式与设计决策

1. **旋转-处理-反旋转**：经典的方向性效果实现策略，将任意方向的处理转化为轴对齐处理，复用现有的轴对齐模糊滤镜。

2. **滤镜链组合**：利用 `SkImageFilter` 的可组合性，通过嵌套构建滤镜管线，无需自定义着色器。

3. **图像滤镜效果节点**：使用 `sksg::ExternalImageFilter` + `ImageFilterEffect` 的组合，与颜色滤镜效果（使用 `ExternalColorFilter`）形成对称的架构。

4. **适配器与效果节点分离**：适配器创建与图层附加在 `attachDirectionalBlurEffect` 中分两步完成，适配器先绑定到 `ExternalImageFilter`，再由 `ImageFilterEffect` 将其应用到图层。

## 性能考量

- 方向模糊需要两次矩阵变换和一次模糊操作，比普通高斯模糊更昂贵
- 使用一维模糊（仅 X 方向 sigma 非零）而非二维模糊，降低了模糊步骤的计算量
- 双线性过滤在旋转步骤中可能引入轻微的图像质量损失，但比双三次过滤更快
- 仅在属性（方向或模糊长度）变化时重建滤镜链
- 模糊长度为 0 时仍会创建滤镜链（可能可以优化为跳过）

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/sksg/include/SkSGRenderEffect.h` - ExternalImageFilter 和 ImageFilterEffect
- `include/effects/SkImageFilters.h` - SkImageFilters API
- `include/core/SkImageFilter.h` - SkImageFilter 基类
