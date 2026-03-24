# SkSVGMask

> 源文件: modules/svg/src/SkSVGMask.cpp

## 概述

`SkSVGMask.cpp` 实现了 SVG `<mask>` 元素的功能，用于创建基于亮度的蒙版效果。蒙版是 SVG 中控制图形可见性的高级技术，通过将蒙版内容的亮度值（luma）映射到目标对象的透明度，实现复杂的显示/隐藏效果。该实现支持对象边界框和用户空间两种坐标系统，并正确处理颜色空间插值。蒙版在创建渐变消失、纹理叠加、局部透明等视觉效果中非常有用。

## 架构位置

该实现文件是 `SkSVGMask` 类的具体实现：

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGMask.h`
- **继承层次**: `SkSVGNode` → `SkSVGHiddenContainer` → `SkSVGMask`
- **功能角色**: 蒙版定义容器，不直接渲染，通过引用应用到目标元素

在 SVG 架构中，`SkSVGMask` 与裁剪路径（`SkSVGClipPath`）和滤镜（`SkSVGFilter`）共同构成高级效果系统。

## 主要类与结构体

该文件实现了 `SkSVGMask` 的三个核心方法。

### 实现的方法

1. **parseAndSetAttribute()**: 解析蒙版属性
2. **bounds()**: 计算蒙版应用区域
3. **renderMask()**: 渲染蒙版内容

## 公共 API 函数

### bool parseAndSetAttribute(const char* n, const char* v)

解析并设置 `<mask>` 元素的属性。

```cpp
bool SkSVGMask::parseAndSetAttribute(const char* n, const char* v) {
    return INHERITED::parseAndSetAttribute(n, v) ||
           this->setX(SkSVGAttributeParser::parse<SkSVGLength>("x", n, v)) ||
           this->setY(SkSVGAttributeParser::parse<SkSVGLength>("y", n, v)) ||
           this->setWidth(SkSVGAttributeParser::parse<SkSVGLength>("width", n, v)) ||
           this->setHeight(SkSVGAttributeParser::parse<SkSVGLength>("height", n, v)) ||
           this->setMaskUnits(
                SkSVGAttributeParser::parse<SkSVGObjectBoundingBoxUnits>("maskUnits", n, v)) ||
           this->setMaskContentUnits(
                SkSVGAttributeParser::parse<SkSVGObjectBoundingBoxUnits>("maskContentUnits", n, v));
}
```

**支持的属性**:
- **x, y, width, height**: 蒙版区域的位置和尺寸
- **maskUnits**: 定义 x/y/width/height 的坐标系统
- **maskContentUnits**: 定义蒙版内容的坐标系统

**默认值**（在头文件中定义）:
- x: -10%, y: -10%, width: 120%, height: 120%（覆盖对象并留出边距）
- maskUnits: objectBoundingBox（相对于目标对象）
- maskContentUnits: userSpaceOnUse（绝对坐标）

### SkRect bounds(const SkSVGRenderContext& ctx) const

计算蒙版的应用区域。

```cpp
SkRect SkSVGMask::bounds(const SkSVGRenderContext& ctx) const {
    return ctx.resolveOBBRect(fX, fY, fWidth, fHeight, fMaskUnits);
}
```

**实现**: 委托给渲染上下文的 `resolveOBBRect()` 方法，根据 `maskUnits` 设置解析为像素坐标的矩形。

**返回值**: 蒙版有效的矩形区域，超出此区域的蒙版效果被忽略。

## 内部实现细节

### void renderMask(const SkSVGRenderContext& ctx) const

渲染蒙版内容并应用亮度到 alpha 的转换。

```cpp
void SkSVGMask::renderMask(const SkSVGRenderContext& ctx) const {
    // 1. 创建局部渲染上下文
    SkSVGRenderContext lctx(ctx);
    this->onPrepareToRender(&lctx);

    // 2. 准备颜色空间插值滤镜
    const auto ci = *lctx.presentationContext().fInherited.fColorInterpolation;
    auto ci_filter = (ci == SkSVGColorspace::kLinearRGB)
            ? SkColorFilters::SRGBToLinearGamma()
            : nullptr;

    // 3. 创建亮度到 alpha 的颜色滤镜
    SkPaint mask_filter;
    mask_filter.setColorFilter(
                SkColorFilters::Compose(SkLumaColorFilter::Make(), std::move(ci_filter)));

    // 4. 创建蒙版颜色滤镜图层
    lctx.canvas()->saveLayer(nullptr, &mask_filter);

    // 5. 应用内容单位变换
    const auto obbt = ctx.transformForCurrentOBB(fMaskContentUnits);
    lctx.canvas()->translate(obbt.offset.x, obbt.offset.y);
    lctx.canvas()->scale(obbt.scale.x, obbt.scale.y);

    // 6. 渲染所有子节点（蒙版内容）
    for (const auto& child : fChildren) {
        child->render(lctx);
    }
}
```

### 详细步骤解析

#### 1. 局部上下文创建

```cpp
SkSVGRenderContext lctx(ctx);
this->onPrepareToRender(&lctx);
```

**目的**:
- 创建新的渲染上下文，继承当前上下文的状态
- 调用 `onPrepareToRender()` 传播继承属性（如 `color-interpolation`）
- 局部上下文在作用域结束时自动恢复画布状态

**注释说明**: 显式调用属性传播是必要的，因为 `SkSVGMask` 不参与正常的渲染遍历路径。

#### 2. 颜色空间处理

```cpp
const auto ci = *lctx.presentationContext().fInherited.fColorInterpolation;
auto ci_filter = (ci == SkSVGColorspace::kLinearRGB)
        ? SkColorFilters::SRGBToLinearGamma()
        : nullptr;
```

**颜色插值**:
- 如果指定为线性 RGB 颜色空间，应用 sRGB 到线性的 gamma 转换
- 否则使用默认的 sRGB 颜色空间（不需要滤镜）

**SVG 规范**: 支持 `color-interpolation` 属性控制混合和滤镜的颜色空间。

#### 3. 亮度到 Alpha 转换

```cpp
SkPaint mask_filter;
mask_filter.setColorFilter(
    SkColorFilters::Compose(SkLumaColorFilter::Make(), std::move(ci_filter)));
```

**滤镜链**:
1. **颜色空间转换** (可选): `ci_filter` 将颜色从 sRGB 转换到线性 RGB
2. **亮度提取**: `SkLumaColorFilter` 计算亮度值并映射到 alpha

**亮度计算公式**（ITU-R BT.709）:
```
luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
```

亮度值成为最终的 alpha 通道，控制被蒙版对象的透明度。

#### 4. 蒙版滤镜图层

```cpp
lctx.canvas()->saveLayer(nullptr, &mask_filter);
```

**图层作用**:
- 创建一个新的绘图图层
- 应用 `mask_filter` 颜色滤镜到整个图层内容
- 将处理后的图层合成回父画布

**注释说明**: 注释中提到可以通过反转堆叠顺序（蒙版/内容 → 内容/蒙版）避免额外图层，但会增加状态管理复杂性。当前设计优先考虑代码简洁性。

#### 5. 内容坐标变换

```cpp
const auto obbt = ctx.transformForCurrentOBB(fMaskContentUnits);
lctx.canvas()->translate(obbt.offset.x, obbt.offset.y);
lctx.canvas()->scale(obbt.scale.x, obbt.scale.y);
```

**坐标系统适配**:
- 根据 `maskContentUnits` 获取适当的变换
- **objectBoundingBox**: 缩放到 0-1 范围，映射到对象边界框
- **userSpaceOnUse**: 使用用户空间坐标，不进行特殊变换

**变换应用**: 平移和缩放确保蒙版内容在正确的坐标系统中渲染。

#### 6. 子节点渲染

```cpp
for (const auto& child : fChildren) {
    child->render(lctx);
}
```

**渲染蒙版内容**: 遍历所有子节点并渲染到蒙版图层。每个子节点的颜色被转换为亮度，最终影响目标对象的透明度。

## 依赖关系

### Skia 核心依赖

- **include/core/SkCanvas.h**: 画布图层和变换操作
- **include/core/SkColorFilter.h**: 颜色滤镜接口
- **include/core/SkM44.h**: 4x4 矩阵（用于高级变换）
- **include/core/SkPaint.h**: 绘图属性
- **include/effects/SkLumaColorFilter.h**: 亮度滤镜，核心蒙版效果

### SVG 模块依赖

- **modules/svg/include/SkSVGMask.h**: 类声明
- **modules/svg/include/SkSVGAttribute.h**: 属性类型定义
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

### 私有基础设施

- **include/private/base/SkTArray.h**: 动态数组容器

## 设计模式与设计决策

### 滤镜链模式

使用 `SkColorFilters::Compose()` 组合多个颜色滤镜：

```cpp
Compose(LumaFilter, ColorSpaceFilter)
```

**执行顺序**: 颜色空间转换 → 亮度提取 → 输出 alpha

这种组合模式允许灵活地添加或移除滤镜阶段。

### 延迟渲染

蒙版内容不在正常渲染遍历中渲染，而是在被引用时按需渲染：

```cpp
void renderMask(const SkSVGRenderContext& ctx) const
```

**优势**:
- 避免渲染未使用的蒙版
- 允许在不同上下文中多次使用同一蒙版
- 支持动态蒙版效果

### 图层隔离

使用 `saveLayer()` 隔离蒙版渲染：

**好处**:
- 蒙版内容不直接影响父画布
- 可以应用整体滤镜到蒙版内容
- 正确处理透明度混合

**代价**: 额外的内存和计算开销（创建和合成图层）

### 坐标系统双重支持

分离 `maskUnits` 和 `maskContentUnits`：

**设计理由**:
- **灵活性**: 蒙版区域和内容可以使用不同的坐标系统
- **SVG 兼容性**: 完全符合 SVG 规范
- **常见用例**: 区域通常相对于对象（objectBoundingBox），内容通常绝对定位（userSpaceOnUse）

## 性能考量

### 图层开销

每次应用蒙版都需要创建图层：

```
内存 = width × height × 4 bytes
```

对于大区域或多个蒙版，可能显著增加内存使用。

### 颜色滤镜计算

亮度计算需要对每个像素执行：

```
luma = 0.2126*R + 0.7152*G + 0.0722*B
```

这是相对轻量的操作，但在高分辨率下累积成本可观。

### GPU 加速

Skia 的颜色滤镜支持 GPU 加速：
- `SkLumaColorFilter` 可编译为片段着色器
- GPU 并行处理所有像素
- 图层合成也可以在 GPU 上执行

### 优化策略

1. **蒙版缓存**: 对于静态蒙版，缓存渲染结果
2. **区域裁剪**: 只渲染可见区域的蒙版
3. **简化蒙版**: 如果可能，使用更简单的蒙版形状

### 注释中的优化建议

代码注释提到的优化（反转堆叠顺序）：

**当前**: 内容 → 蒙版（使用 kSrcIn）→ 输出
**建议**: 蒙版 → 内容（使用 kDstIn）→ 输出

反转顺序可以省略蒙版滤镜图层，但需要：
- 延迟蒙版渲染到内容之后
- 更复杂的状态管理
- 可能的渲染顺序问题

目前选择简洁性而非极致性能。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGMask.h**: 类声明和属性定义

### 相关效果

- **modules/svg/include/SkSVGClipPath.h**: 裁剪路径，另一种可见性控制方式
- **modules/svg/src/SkSVGClipPath.cpp**: 裁剪路径实现
- **modules/svg/include/SkSVGFilter.h**: 滤镜容器

### Skia 滤镜

- **include/effects/SkLumaColorFilter.h**: 亮度滤镜声明
- **src/effects/colorfilters/SkLumaColorFilter.cpp**: 亮度滤镜实现
- **include/core/SkColorFilter.h**: 颜色滤镜基类

### 渲染上下文

- **modules/svg/include/SkSVGRenderContext.h**: 提供坐标解析和属性访问
- **modules/svg/src/SkSVGRenderContext.cpp**: 上下文实现

### 使用示例

**基本蒙版**:
```xml
<defs>
  <mask id="fade">
    <rect x="0" y="0" width="100%" height="100%" fill="url(#gradient)"/>
  </mask>
</defs>
<rect width="200" height="200" fill="blue" mask="url(#fade)"/>
```

**复杂蒙版**:
```xml
<defs>
  <mask id="text-mask" maskUnits="userSpaceOnUse">
    <text x="10" y="50" font-size="40" fill="white">MASK</text>
  </mask>
</defs>
<rect width="300" height="100" fill="red" mask="url(#text-mask)"/>
```

**渐变蒙版**:
```xml
<defs>
  <linearGradient id="grad">
    <stop offset="0%" stop-color="white"/>
    <stop offset="100%" stop-color="black"/>
  </linearGradient>
  <mask id="gradient-mask">
    <rect width="100%" height="100%" fill="url(#grad)"/>
  </mask>
</defs>
<circle cx="50" cy="50" r="40" fill="green" mask="url(#gradient-mask)"/>
```

该实现提供了完整的 SVG 蒙版功能，通过亮度到 alpha 的转换实现灵活的可见性控制。
