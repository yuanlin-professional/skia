# SkDraw_atlas

> 源文件
> - src/core/SkDraw_atlas.cpp

## 概述

`SkDraw_atlas` 实现了 atlas（纹理集）的CPU光栅化绘制功能。它将一个大纹理中的多个矩形区域（sprites）通过RSXForm变换绘制到目标表面，支持可选的每sprite颜色调制和混合。该模块是 `SkCanvas::drawAtlas()` API 在CPU后端的实现，广泛用于高效绘制大量相似图形（如文字、粒子、UI元素）。实现基于 `SkRasterPipeline`，支持颜色空间转换和高质量混合。

## 架构位置

该文件位于 `src/core` 核心绘制层，属于 `skcpu::Draw` 命名空间。它是 `SkDraw` 绘制引擎的功能扩展，与 `SkDraw_vertices.cpp`、`SkDraw_text.cpp` 等并列。它连接高层API（`SkCanvas`）和底层光栅化器（`SkBlitter`），利用 `SkTransformShader` 动态更新着色器变换。

## 主要类与结构体

该文件不定义独立的类，而是为 `skcpu::Draw` 类添加成员函数。

### 核心函数

```cpp
namespace skcpu {
void Draw::drawAtlas(SkSpan<const SkRSXform> xform,
                     SkSpan<const SkRect> textures,
                     SkSpan<const SkColor> colors,
                     sk_sp<SkBlender> blender,
                     const SkPaint& paint)
```

绘制atlas的主函数，参数说明：

| 参数 | 类型 | 说明 |
|------|------|------|
| `xform` | `SkSpan<const SkRSXform>` | RSXForm变换数组（旋转、缩放、平移） |
| `textures` | `SkSpan<const SkRect>` | 纹理坐标矩形数组 |
| `colors` | `SkSpan<const SkColor>` | 可选的颜色调制数组 |
| `blender` | `sk_sp<SkBlender>` | 颜色与纹理的混合器 |
| `paint` | `const SkPaint&` | 绘制属性（包含atlas shader、alpha等） |

## 公共 API 函数

### drawAtlas

唯一的公共函数，完整流程：

1. **参数验证：** 检查 `xform` 和 `textures` 数组大小匹配，如果提供 `colors` 则必须与 `xform` 数量相同
2. **Shader提取：** 从 `paint` 中获取atlas纹理shader，如果没有则直接返回
3. **Paint配置：** 创建修改后的paint副本，禁用抗锯齿和遮罩滤镜，强制填充样式
4. **TransformShader创建：** 将atlas shader包装为 `SkTransformShader`，支持逐sprite更新变换矩阵
5. **Pipeline构建：** 构建光栅管线，追加shader的根阶段
6. **颜色调制：** 如果提供 `colors`，则添加 `uniform_color_dst` 阶段和混合阶段
7. **Alpha处理：** 如果paint alpha不为1.0，添加 `scale_1_float` 阶段
8. **Blitter创建：** 创建光栅管线blitter
9. **逐sprite绘制：** 遍历每个sprite，更新颜色、计算变换、填充矩形

## 内部实现细节

### RSXForm 变换处理

`SkRSXform` 编码旋转、缩放和平移的紧凑表示（4个浮点数）：
```cpp
SkMatrix mx;
mx.setRSXform(xform[i]);                    // 设置RSXForm变换
mx.preTranslate(-textures[i].fLeft, -textures[i].fTop);  // 纹理对齐
mx.postConcat(*fCTM);                       // 应用CTM
```

完整变换链：纹理坐标 → RSXForm → CTM → 设备坐标

### 透视支持

通过检查 `fCTM->hasPerspective()` 确定是否启用透视：
```cpp
const bool perspective = fCTM->hasPerspective();
auto transformShader = alloc.make<SkTransformShader>(*as_SB(atlasShader), perspective);
```
透视模式下，`SkTransformShader` 使用齐次坐标进行变换。

### 颜色处理管线

**颜色空间转换：**
```cpp
SkColorSpaceXformSteps steps(sk_srgb_singleton(), kUnpremul_SkAlphaType,
                             rec.fDstCS, kUnpremul_SkAlphaType);
SkColor4f c4 = SkColor4f::FromColor(colors[i]);
steps.apply(c4.vec());
```
将sRGB颜色转换到目标颜色空间（如Display P3）。

**Premultiply处理：**
```cpp
load_color(uniformCtx, c4.premul().vec());
```
颜色在混合前预乘alpha，匹配GPU行为。

**混合器验证：**
```cpp
std::optional<SkBlendMode> bm = as_BB(blender)->asBlendMode();
if (!bm.has_value()) {
    return;  // 不支持自定义blender（仅支持标准BlendMode）
}
```

### 矩形填充

使用辅助函数 `fill_rect` 处理透视和非透视情况：
- **非透视：** 直接调用 `SkScan::FillRect`，高效填充轴对齐矩形
- **透视：** 将矩形转换为 `SkPathRawShapes::Rect`，然后调用 `SkScan::FillPath`

### 不透明性优化

```cpp
bool isOpaque = colors.empty() && transformShader->isOpaque();
if (p.getAlphaf() != 1) {
    isOpaque = false;
}
```
通知blitter是否可以使用不透明优化路径（跳过alpha混合）。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkTransformShader` | 动态更新纹理采样变换 |
| `SkRasterPipeline` | 光栅化计算管线 |
| `SkColorSpaceXformSteps` | 颜色空间转换 |
| `SkBlendModePriv` | 混合模式管线阶段 |
| `SkScan` | 扫描线填充 |
| `SkPathRawShapes` | 透视矩形路径表示 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkCanvas::drawAtlas()` | 高层API，调用此实现 |
| `SkDevice` | 设备抽象层分发到CPU实现 |

## 设计模式与设计决策

**Shader包装模式：** 使用 `SkTransformShader` 包装原始shader，允许每次循环迭代时更新变换矩阵，而不需要重建整个管线。这是关键性能优化。

**Pipeline复用：** 管线一次构建，所有sprite共享。仅更新变换和颜色上下文（轻量级操作）。

**即时模式渲染：** 不缓存任何中间结果，直接逐sprite绘制。这适合atlas通常是动态内容的场景。

**限制策略：** 不支持复杂blender（必须能转换为 `SkBlendMode`），不支持mask filter。这些限制简化实现并保持性能。

**CTM折叠：** 将CTM折叠到每个sprite的变换矩阵中，然后对管线使用单位矩阵。这避免了管线需要处理全局变换。

## 性能考量

**栈分配器：** 使用 `SkSTArenaAlloc<256>` 避免堆分配。所有临时对象（shader、pipeline stages、context）在栈上分配。

**单次管线构建：** 管线构建是开销最大的操作，通过复用将其摊销到所有sprite上。

**矩阵求逆：** 每个sprite需要计算逆矩阵用于纹理采样：
```cpp
if (auto inv = mx.invert()) {
    if (transformShader->update(*inv)) {
        fill_rect(mx, *fRC, textures[i], blitter);
    }
}
```
如果矩阵不可逆（如缩放为0），跳过该sprite。

**抗锯齿禁用：** 代码明确禁用抗锯齿：
```cpp
p.setAntiAlias(false);  // we never respect this for drawAtlas(or drawVertices)
```
这是有意为之，因为atlas通常包含已预处理的内容（如预渲染的文字）。

**颜色转换批处理：** 颜色空间转换在每次绘制前单独应用，无法批处理。这是潜在优化点，但颜色数组通常不大。

**填充优化：** 非透视情况下使用专门的矩形填充路径，比通用路径填充快得多。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkCanvas.h` | 定义 `drawAtlas()` 公共API |
| `src/shaders/SkTransformShader.h` | 可更新变换的shader包装器 |
| `src/core/SkDraw.h` | 定义 `skcpu::Draw` 类 |
| `src/core/SkScan.h` | 扫描线填充入口 |
| `src/core/SkPathRawShapes.h` | 简化路径表示 |
| `src/core/SkRasterPipeline.h` | 光栅化管线框架 |
| `include/core/SkRSXform.h` | RSXForm变换定义 |
