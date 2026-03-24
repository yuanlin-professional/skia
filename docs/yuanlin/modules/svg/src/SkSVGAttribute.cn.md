# SkSVGAttribute

> 源文件: [modules/svg/src/SkSVGAttribute.cpp](../../../../modules/svg/src/SkSVGAttribute.cpp)

## 概述

`SkSVGAttribute` 模块定义了 SVG 展示属性的枚举类型和初始值系统。源文件（50 行）仅包含一个静态工厂方法 `SkSVGPresentationAttributes::MakeInitial()`，用于创建符合 SVG 规范的默认展示属性集合。头文件则定义了 `SkSVGAttribute` 枚举和 `SkSVGPresentationAttributes` 结构体。

该模块是 SVG 渲染上下文初始化的基础，定义了所有 SVG 元素共享的展示属性的初始值。

## 架构位置

```
SkSVGAttribute                   ← 本文件
  ├── SkSVGAttribute 枚举          （属性标识符）
  └── SkSVGPresentationAttributes  （展示属性集合）
        ├── 被 SkSVGNode 持有       （每个节点的本地属性）
        └── 被 SkSVGRenderContext 使用 （属性继承和解析）
```

## 主要类与结构体

### `SkSVGAttribute` 枚举

定义了所有支持的 SVG 属性标识符，包括：
- 几何属性：`kCx`, `kCy`, `kR`, `kRx`, `kRy`, `kX`, `kY`, `kWidth`, `kHeight`
- 线段属性：`kX1`, `kX2`, `kY1`, `kY2`
- 引用属性：`kHref`, `kPoints`
- 变换属性：`kTransform`
- 视口属性：`kViewBox`, `kPreserveAspectRatio`
- 渐变属性：`kGradientUnits`, `kGradientTransform`, `kSpreadMethod`
- 滤镜属性：`kFilterUnits`
- 展示属性：`kFill`, `kStroke`, `kOpacity` 等
- 文本属性：`kText`, `kTextAnchor`, `kFontFamily` 等

### `SkSVGPresentationAttributes` 结构体

包含所有 SVG 展示属性的集合，使用 `SkSVGProperty` 模板封装每个属性，区分可继承（`true`）和不可继承（`false`）属性：

**可继承属性：**
- 填充：`fFill`, `fFillOpacity`, `fFillRule`, `fClipRule`
- 描边：`fStroke`, `fStrokeDashArray`, `fStrokeDashOffset`, `fStrokeLineCap`, `fStrokeLineJoin`, `fStrokeMiterLimit`, `fStrokeOpacity`, `fStrokeWidth`
- 可见性：`fVisibility`
- 颜色：`fColor`, `fColorInterpolation`, `fColorInterpolationFilters`
- 字体：`fFontFamily`, `fFontStyle`, `fFontSize`, `fFontWeight`, `fTextAnchor`

**不可继承属性：**
- `fOpacity`, `fClipPath`, `fDisplay`, `fMask`, `fFilter`
- `fStopColor`, `fStopOpacity`（渐变停止点）
- `fFloodColor`, `fFloodOpacity`（滤镜洪水填充）
- `fLightingColor`（光照颜色）

## 公共 API 函数

### `SkSVGPresentationAttributes::MakeInitial()`
静态工厂方法，创建并返回包含 SVG 规范定义的所有初始值的展示属性集合。

## 内部实现细节

### 初始值定义

`MakeInitial()` 按照 SVG 规范设置每个属性的初始值：

| 属性 | 初始值 | 说明 |
|------|--------|------|
| `fFill` | 黑色 (`SK_ColorBLACK`) | 默认填充颜色 |
| `fFillOpacity` | 1.0 | 完全不透明 |
| `fFillRule` | NonZero | 非零填充规则 |
| `fClipRule` | NonZero | 非零裁剪规则 |
| `fStroke` | None | 默认无描边 |
| `fStrokeDashArray` | None | 无虚线 |
| `fStrokeDashOffset` | 0 | 虚线偏移为零 |
| `fStrokeLineCap` | Butt | 平头线帽 |
| `fStrokeLineJoin` | Miter | 尖角连接 |
| `fStrokeMiterLimit` | 4 | 尖角限制为 4 |
| `fStrokeOpacity` | 1.0 | 完全不透明 |
| `fStrokeWidth` | 1 | 描边宽度为 1 |
| `fVisibility` | Visible | 可见 |
| `fColor` | 黑色 | currentColor 值 |
| `fColorInterpolation` | sRGB | 颜色插值空间 |
| `fColorInterpolationFilters` | linearRGB | 滤镜颜色插值空间 |
| `fFontFamily` | "Sans" | 默认字体族 |
| `fFontStyle` | Normal | 正常字体样式 |
| `fFontSize` | 24 | 默认字号 |
| `fFontWeight` | Normal | 正常字重 |
| `fTextAnchor` | Start | 文本锚点起始位置 |
| `fDisplay` | Inline | 默认显示模式 |
| `fStopColor` | 黑色 | 渐变停止点颜色 |
| `fStopOpacity` | 1.0 | 渐变停止点透明度 |
| `fFloodColor` | 黑色 | feFlood 颜色 |
| `fFloodOpacity` | 1.0 | feFlood 透明度 |
| `fLightingColor` | 白色 (`SK_ColorWHITE`) | 光照颜色 |

注意 `fFontSize` 初始值为 24 而非 CSS 默认的 medium，这可能是 Skia 特定的选择。

## 依赖关系

- **Skia Core**: `SkColor`（用于颜色常量）
- **SVG 模块**: `SkSVGTypes.h`（通过 `SkSVGAttribute.h` 间接引用）

## 设计模式与设计决策

1. **规范驱动的初始值**: 所有初始值严格遵循 SVG 1.1/2.0 规范定义，确保未设置属性时的渲染行为正确。

2. **继承性标记**: 使用模板参数 `bool` 区分可继承和不可继承属性，在编译期即确定继承行为。

3. **TODO 注释**: 代码中标注 `SkSVGProperty` 每个属性额外增加一个指针大小的开销，建议重构以减少内存占用。

## 性能考量

- `MakeInitial()` 创建完整的属性集合，包含约 30 个属性的设置操作，但仅在渲染上下文初始化时调用一次
- `SkSVGPresentationAttributes` 结构体大小较大（每个属性含一个 `SkSVGProperty` 包装），每个 SkSVGNode 都持有一份副本
- 头文件注释指出应使用稀疏存储优化内存，目前未实现

## 相关文件

- `modules/svg/include/SkSVGAttribute.h` - 头文件，定义枚举和结构体
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义
- `modules/svg/include/SkSVGNode.h` - 使用展示属性的节点基类
- `modules/svg/include/SkSVGRenderContext.h` - 属性继承和解析的上下文
