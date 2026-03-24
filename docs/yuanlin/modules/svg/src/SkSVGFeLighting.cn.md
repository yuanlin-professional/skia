# SkSVGFeLighting

> 源文件: [modules/svg/src/SkSVGFeLighting.cpp](../../../../modules/svg/src/SkSVGFeLighting.cpp)

## 概述

`SkSVGFeLighting` 实现了 SVG 光照滤镜效果族，包括漫反射光照（`<feDiffuseLighting>`）和镜面反射光照（`<feSpecularLighting>`）。该文件包含三个类的实现：基类 `SkSVGFeLighting` 负责光源类型派发和通用属性处理，`SkSVGFeSpecularLighting` 和 `SkSVGFeDiffuseLighting` 分别实现镜面和漫反射光照的具体参数配置。每种光照类型支持三种光源：远光（Distant）、点光（Point）和聚光（Spot）。

## 架构位置

```
SkSVGNode
  └── SkSVGFe (滤镜效果基类)
        └── SkSVGFeLighting (光照基类) ← 本文件实现
              ├── SkSVGFeSpecularLighting (镜面反射)
              └── SkSVGFeDiffuseLighting (漫反射)
                    └── 子节点: SkSVGFeDistantLight / SkSVGFePointLight / SkSVGFeSpotLight
```

## 主要类与结构体

### SkSVGFeLighting（基类）
- 继承自 `SkSVGFe`
- 管理通用属性：`surfaceScale`、`kernelUnitLength`
- 实现光源类型派发：遍历子节点找到第一个光源并委托给子类
- 提供辅助方法 `resolveLightingColor` 和 `resolveXYZ`

### SkSVGFeLighting::KernelUnitLength
- 结构体，包含 `fDx` 和 `fDy` 两个分量
- 用于定义光照核的单位长度

### SkSVGFeSpecularLighting
- 继承自 `SkSVGFeLighting`
- 额外属性：`specularConstant`（镜面常数）、`specularExponent`（镜面指数）
- 为三种光源类型分别实现 `SkImageFilters::*LitSpecular` 调用

### SkSVGFeDiffuseLighting
- 继承自 `SkSVGFeLighting`
- 额外属性：`diffuseConstant`（漫反射常数）
- 为三种光源类型分别实现 `SkImageFilters::*LitDiffuse` 调用

## 公共 API 函数

### `SkSVGFeLighting::parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* n, const char* v);
```
解析 `surfaceScale` 和 `kernelUnitLength` 属性。

### `SkSVGFeLighting::onMakeImageFilter`
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext&,
                                       const SkSVGFilterContext&) const;
```
遍历子节点查找光源，根据光源类型（distant/point/spot）委托给对应的虚方法。如果没有找到光源，输出调试信息并返回 nullptr。

### `SkSVGFeLighting::resolveLightingColor`
```cpp
SkColor resolveLightingColor(const SkSVGRenderContext& ctx) const;
```
解析 `lighting-color` 呈现属性。如果未设置，返回白色作为默认值。

### `SkSVGFeLighting::resolveXYZ`
```cpp
SkPoint3 resolveXYZ(const SkSVGRenderContext&, const SkSVGFilterContext&,
                    SkSVGNumberType x, SkSVGNumberType y, SkSVGNumberType z) const;
```
将光源坐标从对象边界框坐标系转换为绝对坐标系。

### `SkSVGFeSpecularLighting::parseAndSetAttribute`
解析 `specularConstant` 和 `specularExponent`。

### `SkSVGFeDiffuseLighting::parseAndSetAttribute`
解析 `diffuseConstant`。

## 内部实现细节

### 光源派发机制

`onMakeImageFilter` 在基类中实现为 `final`，遍历子节点列表，根据第一个匹配的光源标签类型（`kFeDistantLight`、`kFePointLight`、`kFeSpotLight`）调用对应的纯虚方法。非光源子节点（如 `<desc>`）被静默忽略。

### 坐标变换

`resolveXYZ` 方法处理复杂的坐标系变换：
1. 获取当前对象边界框变换（OBB Transform），包含缩放和偏移
2. 对 x/y 坐标应用缩放和偏移变换
3. 对 z 坐标通过 `SkSVGLengthContext` 按百分比解析（将 z 值乘以 100 作为百分比）

### KernelUnitLength 解析

`SkSVGAttributeParser::parse<KernelUnitLength>` 模板特化支持一个或两个数值：
- 单个数值时 `fDx = fDy = values[0]`
- 两个数值时分别赋值

### SpotLight 锥角处理

对于聚光灯，使用 `limitingConeAngle` 的 `value_or(180.f)` 处理缺省值，180 度意味着无截止角度限制。

## 依赖关系

- **Skia 核心**: `SkImageFilter`、`SkM44`、`SkPoint3`、`SkImageFilters`、`SkColor`
- **SVG 模块**: `SkSVGFe`（基类）、`SkSVGFeLightSource`（光源节点）、`SkSVGAttributeParser`、`SkSVGFilterContext`、`SkSVGRenderContext`

## 设计模式与设计决策

1. **模板方法模式**: 基类 `SkSVGFeLighting` 的 `onMakeImageFilter` 定义了光源查找算法骨架（标记为 `final`），具体光源类型的滤镜创建委托给子类的纯虚方法（`makeDistantLight`、`makePointLight`、`makeSpotLight`）。

2. **继承层次清晰**: 通用光照属性（surfaceScale、lightingColor）在基类处理，特定光照属性（specularConstant/Exponent、diffuseConstant）在子类处理。

3. **3x2 矩阵结构**: 2 种光照类型 x 3 种光源类型 = 6 种组合，每种都有独立的方法实现，但共享基类的坐标解析和颜色解析逻辑。

4. **第一个光源优先**: 根据 SVG 规范，光照滤镜恰好需要一个光源子节点，实现中取第一个匹配的光源并立即返回。如果存在多个光源子节点，后续光源被忽略。

5. **颜色解析安全**: `resolveLightingColor` 在未设置 `lighting-color` 属性时返回白色（`SK_ColorWHITE`）作为安全默认值，并输出调试信息。这种防御性设计确保即使在属性缺失的情况下也能产生合理的视觉输出。

## 性能考量

- 光源查找为子节点的线性遍历，但光照滤镜通常仅有一个光源子节点，实际为 O(1)。
- 坐标变换涉及矩阵运算和长度解析，但仅在滤镜构建时执行一次。
- 实际的光照计算由 Skia 的 `SkImageFilters` 在 GPU 或 CPU 后端执行，开销与图像尺寸相关。
- 镜面反射由于涉及指数运算（`specularExponent`），通常比漫反射更耗时。
- 远光源（Distant Light）计算最为简单，因为光线方向在整个表面上是恒定的。
- 聚光灯（Spot Light）最为复杂，因为需要计算每个像素到光源和目标点的方向向量，并应用锥角衰减。
- `surfaceScale` 参数影响法线计算的灵敏度，值越大凹凸效果越明显但计算量不变。
- `resolveXYZ` 方法中的 OBB 变换涉及 `SkV2` 向量运算和 `SkSVGLengthContext` 长度解析，但由于仅处理 3 个坐标分量，开销微不足道。

### 光照模型差异

**漫反射光照**（Diffuse）使用 Lambert 余弦定律，计算公式为：
```
I = kd * (N . L) * lightColor
```
其中 `kd` 为 `diffuseConstant`，`N` 为表面法线，`L` 为光源方向。

**镜面反射光照**（Specular）使用 Blinn-Phong 模型，计算公式为：
```
I = ks * (N . H)^n * lightColor
```
其中 `ks` 为 `specularConstant`，`H` 为半程向量，`n` 为 `specularExponent`。指数运算使得镜面反射的计算成本更高。

## 相关文件

- `modules/svg/include/SkSVGFeLighting.h` - 类声明与继承层次
- `modules/svg/include/SkSVGFeLightSource.h` - 光源节点（DistantLight、PointLight、SpotLight）
- `modules/svg/include/SkSVGFe.h` - 滤镜效果基类
- `modules/svg/include/SkSVGFilterContext.h` - 滤镜上下文
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂
- `include/core/SkPoint3.h` - 3D 点类型
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义（SkSVGNumberType）
- `modules/svg/include/SkSVGNode.h` - SVG 节点基类
