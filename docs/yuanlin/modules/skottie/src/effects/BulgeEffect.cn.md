# BulgeEffect - Skottie 凸起变形效果

> 源文件: `modules/skottie/src/effects/BulgeEffect.cpp`

## 概述

BulgeEffect 实现了 After Effects 中的凸起（Bulge）效果，通过球面位移和指数位移的组合在指定椭圆区域内对图像进行膨胀或收缩变形。效果使用 SkSL 运行时着色器实现，将子图层捕获为纹理后通过数学变换对采样坐标进行扭曲。支持椭圆区域的中心点、水平/垂直半径和凸起高度（正值膨胀、负值收缩）的动画控制。

## 架构位置

BulgeEffect 位于 Skottie 效果子系统中，使用自定义渲染节点和 SkSL 着色器实现。

```
EffectBuilder::attachBulgeEffect()
  |
  +-> BulgeNode (自定义渲染节点)
  |     +-> CustomRenderNode
  |     +-> contentShader() [子内容 -> Picture -> Shader]
  |     +-> buildEffectShader() [SkSL 位移着色器]
  |     +-> onRender() [SaveLayer + 着色器绘制]
  |
  +-> BulgeEffectAdapter (属性适配器)
        +-> DiscardableAdapterBase
        +-> EffectBinder [绑定中心、半径、高度]
```

## 主要类与结构体

### BulgeNode
- 继承自 `sksg::CustomRenderNode`
- SG 属性：`Center` (SkPoint)、`Radius` (SkVector)、`Height` (float)
- `contentShader()` - 将子节点捕获为可重复平铺的 Picture 着色器（带脏缓存）
- `buildEffectShader()` - 根据参数构建 SkSL 位移着色器
- `onRender()` - Height=0 时直接渲染子节点，否则使用效果着色器

### BulgeEffectAdapter
- 继承自 `DiscardableAdapterBase<BulgeEffectAdapter, BulgeNode>`
- 属性：
  - `fCenter` (Vec2Value) - 凸起中心
  - `fHorizontalRadius` / `fVerticalRadius` (ScalarValue) - 椭圆半径
  - `fBulgeHeight` (ScalarValue) - 凸起高度
- JSON 属性索引：Horizontal=0, Vertical=1, Center=2, Height=3

## 公共 API 函数

### `EffectBuilder::attachBulgeEffect`
```cpp
sk_sp<sksg::RenderNode> attachBulgeEffect(const skjson::ArrayValue& jprops,
                                           sk_sp<sksg::RenderNode> layer) const;
```
- 创建 `BulgeNode` 包装子图层（传入 fLayerSize）
- 创建 `BulgeEffectAdapter` 绑定动画参数
- 返回配置好的渲染节点

## 内部实现细节

### SkSL 位移着色器

**Uniform 参数：**
- `u_center` - 凸起中心（像素坐标）
- `u_radius` / `u_radius_inv` - 椭圆半径及其倒数
- `u_h` - 指数位移高度参数
- `u_rcpR` - 球面位移半径的倒数
- `u_rcpAsinInvR` - `1/asin(1/R)` 预计算值
- `u_selector` - 膨胀/收缩选择器（+1 或 -1）
- `u_layer` - 子内容着色器

**坐标归一化：**
着色器内部将坐标归一化到单位圆空间：`(xy - u_center) * u_radius_inv`，计算完成后恢复：`xy * u_radius + u_center`。

**位移算法：**

1. **球面位移（displace_sph）：**
   ```glsl
   float arc_ratio = asin(length(v) * u_rcpR) * u_rcpAsinInvR;
   return normalize(v) * arc_ratio - v;
   ```
   将平面坐标映射到球面弧长比例，产生球面透镜效果。

2. **指数位移（displace_exp）：**
   ```glsl
   return v * pow(dot(v,v), u_h) - v;
   ```
   沿径向方向按距离的指数函数进行位移。

3. **组合位移（displace）：**
   - 在单位圆外（`dot(v,v) >= 1`）无位移
   - 在单位圆内：`v + (displace_sph(v) + displace_exp(v)) * u_selector`
   - `u_selector = +1` 为膨胀，`-1` 为收缩

### 参数预计算（buildEffectShader）
```cpp
float adjHeight = std::abs(fHeight) / 4.f;
float r = (1.f + adjHeight) / 2.f / sqrt(adjHeight);
float h = std::pow(adjHeight, 3) * 1.3f;
```
- `adjHeight` - 调整后的高度（原值的 1/4 取绝对值）
- `r` - 球面位移的等效球半径
- `h` - 指数位移的幂指数
- 这些常数经过调整以视觉匹配 AE 的凸起效果

### 内容着色器缓存
```cpp
sk_sp<SkShader> contentShader() {
    if (!fContentShader || this->hasChildrenInval()) {
        // 重新捕获子内容
        SkPictureRecorder recorder;
        child->render(recorder.beginRecording(SkRect::MakeSize(fChildSize)));
        fContentShader = recorder.finishRecordingAsPicture()
            ->makeShader(SkTileMode::kRepeat, SkTileMode::kRepeat, ...);
    }
    return fContentShader;
}
```
- 仅在子节点失效时重新捕获
- 使用 kRepeat 平铺模式处理边缘采样

### 渲染快速路径
- `fHeight == 0` 时直接渲染子节点（`children()[0]->render(canvas, ctx)`），跳过着色器
- 非零时使用 SaveLayer + SrcOver 混合模式绘制效果着色器

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkRuntimeEffect.h` | SkSL 运行时着色器 |
| `SkPicture.h` / `SkPictureRecorder.h` | 子内容捕获 |
| `SkCanvas.h` / `SkPaint.h` | 渲染和混合 |
| `SkShader.h` | 着色器对象 |
| `Adapter.h` | DiscardableAdapterBase |
| `Effects.h` | EffectBinder |
| `SkSGRenderNode.h` / `SkSGNode.h` | CustomRenderNode |
| `SkottieValue.h` | Vec2Value / ScalarValue |

## 设计模式与设计决策

- **球面+指数组合位移**：两种位移算法的组合视觉匹配了 AE 的凸起行为，球面位移提供光学透镜效果，指数位移增加径向衰减。
- **坐标空间归一化**：在 SkSL 中将椭圆归一化为单位圆进行计算，简化了数学表达。注释指出之前通过 local matrix 实现但与 Picture shader 冲突。
- **全局缓存着色器**：`bulge_effect()` 静态缓存编译后的 SkRuntimeEffect。
- **Height=0 快速路径**：高度为零时完全跳过着色器流程，直接渲染原始内容。
- **SrcOver 混合**：与 FractalNoise/SkSL 效果的 SrcIn 不同，凸起效果使用 SrcOver，因为位移着色器本身已经采样了原始内容。

## 性能考量

- SkSL 着色器在 GPU 上执行，`asin`/`sqrt`/`pow` 等数学函数为 GPU 原生支持。
- 内容着色器缓存避免每帧重新捕获子内容。
- 归一化参数（`u_radius_inv` 等）预计算，减少着色器内的除法运算。
- 单位圆外的快速剔除（`dot(v,v) >= 1`）跳过位移计算。
- Picture 着色器允许 GPU 高效处理子内容纹理采样。
- TODO 注释提到 Taper 和 AA 参数尚未实现。

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBinder
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase
- `modules/sksg/include/SkSGRenderNode.h` - CustomRenderNode
- `include/effects/SkRuntimeEffect.h` - SkSL 运行时效果
- `modules/skottie/src/effects/FractalNoiseEffect.cpp` - 类似的自定义渲染节点 + SkSL 模式
- `modules/skottie/src/effects/SkSLEffect.cpp` - 类似的 contentShader 捕获模式
