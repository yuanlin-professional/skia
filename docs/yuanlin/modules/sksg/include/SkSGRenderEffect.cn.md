# SkSGRenderEffect -- 渲染效果节点集合

> 源文件: `modules/sksg/include/SkSGRenderEffect.h`

## 概述

`SkSGRenderEffect.h` 定义了 Skia Scene Graph 中一组高级渲染效果节点，包括着色器（Shader）、图像滤镜（ImageFilter）、混合器（Blender）和图层效果（Layer）。这些效果通过场景图的 `EffectNode` 机制附加到渲染子树上，在渲染时通过 `RenderContext` 的调制（modulate）机制延迟应用，支持与内容隔离（saveLayer）配合使用。该文件是 sksg 效果体系中最丰富的头文件，包含 10 个类的定义。

## 架构位置

```
Node
├── Shader (着色器数据节点)
│   └── [自定义着色器子类]
├── ImageFilter (图像滤镜数据节点)
│   ├── ExternalImageFilter
│   ├── DropShadowImageFilter
│   └── BlurImageFilter
└── RenderNode
    └── EffectNode
        ├── ShaderEffect (着色器效果)
        ├── MaskShaderEffect (遮罩着色器效果)
        ├── ImageFilterEffect (图像滤镜效果)
        ├── BlenderEffect (混合器效果)
        └── LayerEffect (图层混合效果)
```

该文件定义了两层结构：**数据节点**（Shader、ImageFilter）和**效果节点**（ShaderEffect、ImageFilterEffect 等）。数据节点负责创建和缓存 Skia 的原生对象（`SkShader`、`SkImageFilter`），效果节点负责将这些对象应用到渲染子树。

## 主要类与结构体

### 数据节点基类

#### `Shader`
```cpp
class Shader : public Node {
public:
    const sk_sp<SkShader>& getShader() const;
protected:
    virtual sk_sp<SkShader> onRevalidateShader() = 0;
};
```
着色器数据节点基类。子类实现 `onRevalidateShader` 创建具体的 `SkShader`。`onRevalidate` 为 `final`，确保着色器缓存机制不被绕过。

#### `ImageFilter`
```cpp
class ImageFilter : public Node {
public:
    const sk_sp<SkImageFilter>& getFilter() const;
    SG_ATTRIBUTE(CropRect, SkImageFilters::CropRect, fCropRect)
protected:
    virtual sk_sp<SkImageFilter> onRevalidateFilter() = 0;
};
```
图像滤镜数据节点基类。支持可选的裁剪矩形（CropRect）。子类实现 `onRevalidateFilter` 创建具体的 `SkImageFilter`。

### 效果节点

#### `ShaderEffect`
```cpp
class ShaderEffect final : public EffectNode {
public:
    static sk_sp<ShaderEffect> Make(sk_sp<RenderNode> child, sk_sp<Shader> shader = nullptr);
    void setShader(sk_sp<Shader>);
};
```
将 `Shader` 数据节点附加到渲染子树。着色器可以在创建后动态更换。

#### `MaskShaderEffect`
```cpp
class MaskShaderEffect final : public EffectNode {
public:
    static sk_sp<MaskShaderEffect> Make(sk_sp<RenderNode>, sk_sp<SkShader> = nullptr);
    SG_ATTRIBUTE(Shader, sk_sp<SkShader>, fShader)
};
```
遮罩着色器效果，直接接受 `SkShader`（而非 Shader 数据节点），用于将着色器作为遮罩应用。

#### `ImageFilterEffect`
```cpp
class ImageFilterEffect final : public EffectNode {
public:
    static sk_sp<RenderNode> Make(sk_sp<RenderNode> child, sk_sp<ImageFilter> filter);
    enum class Cropping { kNone, kContent };
    SG_ATTRIBUTE(Cropping, Cropping, fCropping)
};
```
将图像滤镜链附加到渲染子树。`Cropping` 枚举控制是否使用内容边界作为裁剪区域。注意 `Make` 返回的是 `sk_sp<RenderNode>` 而非 `sk_sp<ImageFilterEffect>`。

#### `BlenderEffect`
```cpp
class BlenderEffect final : public EffectNode {
public:
    static sk_sp<BlenderEffect> Make(sk_sp<RenderNode> child, sk_sp<SkBlender> = nullptr);
    SG_ATTRIBUTE(Blender, sk_sp<SkBlender>, fBlender)
};
```
将 `SkBlender` 应用到渲染子树，控制内容如何与目标混合。

#### `LayerEffect`
```cpp
class LayerEffect final : public EffectNode {
public:
    static sk_sp<LayerEffect> Make(sk_sp<RenderNode> child,
                                   SkBlendMode mode = SkBlendMode::kSrcOver);
    SG_ATTRIBUTE(Mode, SkBlendMode, fMode)
};
```
图层混合效果，使用指定的 `SkBlendMode` 将内容合成到目标上。

### 具体图像滤镜

#### `ExternalImageFilter`
```cpp
class ExternalImageFilter final : public ImageFilter {
public:
    static sk_sp<ExternalImageFilter> Make();
    SG_ATTRIBUTE(ImageFilter, sk_sp<SkImageFilter>, fImageFilter)
};
```
外部管理的图像滤镜包装器，允许将非 sksg 创建的 `SkImageFilter` 集成到场景图中。

#### `DropShadowImageFilter`
```cpp
class DropShadowImageFilter final : public ImageFilter {
    enum class Mode { kShadowAndForeground, kShadowOnly };
    SG_ATTRIBUTE(Offset, SkVector, fOffset)
    SG_ATTRIBUTE(Sigma,  SkVector, fSigma)
    SG_ATTRIBUTE(Color,  SkColor,  fColor)
    SG_ATTRIBUTE(Mode,   Mode,     fMode)
};
```
投影滤镜，支持偏移、模糊半径、颜色和模式（含前景/仅阴影）。

#### `BlurImageFilter`
```cpp
class BlurImageFilter final : public ImageFilter {
    SG_ATTRIBUTE(Sigma,    SkVector,   fSigma)
    SG_ATTRIBUTE(TileMode, SkTileMode, fTileMode)
};
```
高斯模糊滤镜，支持 X/Y 方向独立的模糊半径和瓦片模式。

## 公共 API 函数

各类的 `Make` 工厂方法和 `SG_ATTRIBUTE` 生成的属性访问器已在上文描述。所有工厂方法都进行空指针检查，无效输入返回 nullptr。

## 内部实现细节

- **Shader/ImageFilter 的 final onRevalidate**：基类的 `onRevalidate` 为 `final`，在其中调用子类的 `onRevalidateShader/onRevalidateFilter` 并缓存结果，然后调用 `getShader/getFilter` 时断言无失效。

- **ShaderEffect 的动态着色器**：`setShader` 允许运行时替换着色器节点，内部需要更新失效观察关系。

- **ImageFilterEffect::Make 返回 RenderNode**：这允许实现在 filter 为空时直接返回 child 节点（消除不必要的效果节点层级）。

- **DropShadowImageFilter 默认值**：偏移和模糊均为 (0,0)，颜色为黑色，模式为 kShadowAndForeground。

- **BlurImageFilter 默认值**：模糊半径 (0,0)，瓦片模式 kDecal。

- **CropRect**：使用 `std::optional` 的 `SkImageFilters::CropRect`（即 `std::nullopt` 表示不裁剪）。

## 依赖关系

- `include/core/SkBlendMode.h` -- 混合模式枚举
- `include/core/SkBlender.h` -- SkBlender 类
- `include/core/SkImageFilter.h` -- SkImageFilter 类
- `include/core/SkShader.h` -- SkShader 类
- `include/effects/SkImageFilters.h` -- CropRect 类型
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGNode.h` -- Node 基类

## 设计模式与设计决策

1. **数据/效果两层分离**：Shader 和 ImageFilter 是纯数据节点（不参与渲染），ShaderEffect 和 ImageFilterEffect 是效果节点（参与渲染链）。这允许多个效果共享同一个数据源。

2. **模板方法模式**：Shader 和 ImageFilter 基类的 `onRevalidate` 为 `final`，定义了缓存更新流程，子类只实现创建逻辑。

3. **外部对象集成**：`ExternalImageFilter` 和 `MaskShaderEffect` 直接接受 Skia 原生对象，允许在场景图之外创建和管理这些对象。

4. **RenderContext 调制机制**：效果通过 `ScopedRenderContext` 的 modulate 方法累积到渲染上下文中，而非直接修改 Canvas，这支持了延迟应用和内容隔离优化。

5. **可选裁剪**：ImageFilterEffect 的 Cropping 枚举和 ImageFilter 的 CropRect 提供了两个层次的裁剪控制。

## 性能考量

- Shader 和 ImageFilter 的缓存机制避免了每帧重新创建 Skia 原生对象。
- ImageFilterEffect 的 Cropping::kContent 模式利用内容边界限制滤镜的处理范围。
- DropShadow 和 Blur 滤镜的计算开销与模糊半径 (sigma) 成正比。
- BlenderEffect 和 LayerEffect 可能触发 saveLayer，这是一个相对昂贵的操作。
- RenderContext 的调制机制允许将多个效果合并应用到一个 layer 上，减少 saveLayer 次数。

## 相关文件

- `modules/sksg/src/SkSGRenderEffect.cpp` -- 各效果的实现
- `modules/sksg/include/SkSGEffectNode.h` -- EffectNode 基类
- `modules/sksg/include/SkSGRenderNode.h` -- RenderContext 和 ScopedRenderContext
- `modules/sksg/include/SkSGColorFilter.h` -- 另一类渲染效果
- `modules/sksg/include/SkSGNode.h` -- SG_ATTRIBUTE 宏
