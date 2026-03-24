# DisplacementMapEffect - Skottie 位移贴图效果

> 源文件: `modules/skottie/src/effects/DisplacementMapEffect.cpp`

## 概述

DisplacementMapEffect 实现了 After Effects 中的"位移贴图"（Displacement Map）效果。该效果使用一个位移源图层的像素值来偏移目标图层的像素位置，实现扭曲变形效果。与 SVG 的 `feDisplacementMap` 类似，但提供更多选择器选项（红/绿/蓝/Alpha/亮度/色相/饱和度/明度/全量/半量/关闭）和各向异性缩放（独立的 X/Y 缩放因子）。实现基于 SkRuntimeEffect 运行时着色器。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），采用三层架构：SkSL 着色器定义位移算法，自定义渲染节点管理着色器构建和渲染，适配器处理属性绑定。

```
AnimationBuilder
  └── EffectBuilder::attachDisplacementMapEffect()
        ├── DisplacementMapAdapter::GetDisplacementSource() // 获取位移源图层
        └── DisplacementMapAdapter (DiscardableAdapterBase)
              └── DisplacementNode (CustomRenderNode)
                    ├── child (目标图层)
                    ├── fDisplSource (位移源图层)
                    └── SkRuntimeEffect (gDisplacementSkSL)
```

## 主要类与结构体

### `DisplacementNode`
- 继承自 `sksg::CustomRenderNode`
- 管理两个渲染子树：目标图层（child）和位移源图层（fDisplSource）
- 枚举类型：
  - `Pos`：位移贴图定位模式（Center/Stretch/Tile）
  - `Selector`：通道选择器（R/G/B/A/Luminance/Hue/Lightness/Saturation/Full/Half/Off，共 11 种）
- 通过 `SG_ATTRIBUTE` 宏暴露 6 个可动画属性

### `SelectorCoeffs`
内部结构，定义每个选择器的位移和覆盖系数：
```cpp
struct SelectorCoeffs {
    float dr, dg, db, da, d_offset;  // 位移贡献
    float c_scale, c_offset;          // 覆盖率（作为 alpha 函数）
};
```

### `DisplacementMapAdapter`
- 继承自 `DiscardableAdapterBase<DisplacementMapAdapter, DisplacementNode>`
- 绑定 7 个效果属性（水平/垂直选择器、最大水平/垂直偏移、贴图行为、边缘行为、扩展输出）
- 提供静态方法 `GetDisplacementSource()` 从 JSON 中获取位移源图层

## 公共 API 函数

### `EffectBuilder::attachDisplacementMapEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachDisplacementMapEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```
- **功能**：将位移贴图效果附加到目标图层
- **流程**：先获取位移源图层，然后创建 DisplacementNode，最后创建适配器

## 内部实现细节

### SkSL 着色器 (gDisplacementSkSL)

```glsl
uniform shader child;     // 目标图层
uniform shader displ;     // 位移源
uniform half4x4 selector_matrix;  // 选择器矩阵
uniform half4   selector_offset;  // 选择器偏移

half4 main(float2 xy) {
    half4 d = displ.eval(xy);
    d = selector_matrix * unpremul(d) + selector_offset;
    return child.eval(xy + d.xy * d.zw);
}
```

着色器的工作流程：
1. 采样位移源在当前位置的颜色
2. 通过选择器矩阵和偏移量提取位移值和覆盖率
3. 将 R/G 用作水平/垂直位移，B/A 用作覆盖率调制
4. 在偏移后的位置采样目标图层

### 选择器系数表 (Coeffs)

`gCoeffs` 数组定义了 11 种选择器模式的系数：
- **R/G/B**：直接使用对应通道值作为位移，alpha 作为覆盖率
- **A**：使用 alpha 作为位移，覆盖率为 1.0
- **Luminance**：使用亮度系数 `(SK_LUM_COEFF_R, _G, _B)` 加权 RGB
- **H/L/S**：在 HSLA 颜色空间中选择分量（TODO：RGB->HSL 转换未实现）
- **Full/Half/Off**：常量位移值 1.0/0.5/0.0

### 选择器矩阵构建

将 X/Y 选择器系数组合为 4x4 矩阵和 4 维偏移向量：
```
列 R: 水平位移, 垂直位移, 0, 0
列 G: 水平位移, 垂直位移, 0, 0
列 B: 水平位移, 垂直位移, 0, 0
列 A: 水平位移, 垂直位移, 水平调制, 垂直调制
```
缩放因子 `s = fScale * 2`，偏移量中减去 0.5 以将 [0,1] 范围居中到 [-0.5, 0.5]。

### 位移贴图定位

三种定位模式通过不同的矩阵变换实现：
- **Center**：平移使位移源居中于目标
- **Stretch**：缩放使位移源填满目标区域
- **Tile**：恒等矩阵，配合 `SkTileMode::kRepeat` 实现平铺

### 效果着色器构建 (buildEffectShader)

1. AE 特殊行为：两个选择器都是常量模式时不触发效果
2. 将子节点和位移源渲染为 `SkPicture`，然后转换为着色器
3. 根据定位模式设置位移源的变换矩阵和平铺模式
4. 构建 `SkRuntimeShaderBuilder`，设置子着色器和 uniform 变量

### 边界扩展

当 `fExpandBounds` 为 true 时，将渲染边界向外扩展 `|fScale|` 像素，以容纳最大位移。

## 依赖关系

- **Skia 核心**：`SkCanvas`、`SkPicture`、`SkShader`、`SkMatrix`、`SkM44`
- **Skia 效果**：`SkRuntimeEffect`（运行时着色器）
- **Skia 内部**：`SkColorData.h`（`SK_LUM_COEFF_*` 亮度系数）
- **Skottie 内部**：`Adapter.h`、`SkottieJson.h`、`SkottiePriv.h`、`Effects.h`
- **SkSG**：`CustomRenderNode`、`RenderNode`
- **JSON**：`SkJSONReader.h`（`ParseDefault`）

## 设计模式与设计决策

1. **运行时着色器**：使用 SkRuntimeEffect 实现矩阵化的通道选择，单个着色器支持 11 种选择器的任意组合，避免了组合爆炸。

2. **双子树观察**：DisplacementNode 通过 `observeInval/unobserveInval` 监听位移源的失效通知，确保位移源变化时触发重新验证。

3. **AE 行为模拟**：代码注释了多处 AE 的特殊行为（如常量选择器不触发效果、R/G/B 选择器需要非透明覆盖率等）。

4. **中间 Picture 渲染**：将子树渲染为 SkPicture 再转为着色器，这是在运行时着色器中组合多个渲染子树的标准做法。

5. **单例着色器效果**：`displacement_effect_singleton()` 使用静态局部变量实现单例模式，避免重复编译 SkSL。

## 性能考量

- SkSL 着色器在 GPU 上高效执行，实现逐像素并行位移计算
- 选择器逻辑通过矩阵乘法统一处理，避免了着色器中的条件分支
- 中间 Picture 渲染增加了一次额外绘制，但允许着色器采样任意位置
- 常量选择器短路检测和零缩放检测避免不必要的着色器构建
- 着色器效果通过单例模式缓存，仅编译一次
- `fExpandBounds` 选项允许用户在精确边界和性能之间权衡

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义和 LayerContent 结构
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/skottie/src/SkottieJson.h` - JSON 解析辅助函数
- `modules/sksg/include/SkSGRenderNode.h` - CustomRenderNode 基类
- `include/effects/SkRuntimeEffect.h` - SkRuntimeEffect API
- `modules/skottie/src/effects/SphereEffect.cpp` - 另一个使用 SkRuntimeEffect 的效果
