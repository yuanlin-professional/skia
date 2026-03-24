# sksg/include - 公开头文件

## 概述

`include/` 目录包含 SkSG 模块的所有公开头文件。这些头文件定义了场景图的完整节点类型层次结构,从基础的 `Node` 类到各种具体的几何体、画笔、效果和容器节点。客户端通过这些接口构建和操控场景图。

SkSG 的头文件设计遵循"一个头文件一个关注点"的原则:每个头文件对应一个或一组紧密相关的节点类型。所有节点类使用 `sk_sp` 智能指针管理,通过静态 `Make()` 工厂方法创建。

## 目录结构

```
include/
├── BUILD.bazel
├── SkSGNode.h                  # Node 基类
├── SkSGRenderNode.h            # RenderNode, RenderContext, CustomRenderNode
├── SkSGGroup.h                 # Group 容器
├── SkSGDraw.h                  # Draw 绘制节点
├── SkSGEffectNode.h            # EffectNode 效果基类
├── SkSGGeometryNode.h          # GeometryNode 几何体基类
├── SkSGGeometryEffect.h        # TrimEffect, RoundEffect, OffsetEffect, DashEffect 等
├── SkSGPath.h                  # Path 路径节点
├── SkSGRect.h                  # Rect, RRect 节点
├── SkSGPlane.h                 # Plane 无限平面
├── SkSGMerge.h                 # Merge 路径合并
├── SkSGImage.h                 # Image 图像节点
├── SkSGText.h                  # Text 文本节点
├── SkSGPaint.h                 # PaintNode, Color, ShaderPaint
├── SkSGGradient.h              # Gradient, LinearGradient, RadialGradient
├── SkSGTransform.h             # Transform, Matrix<T>, TransformEffect
├── SkSGOpacityEffect.h         # OpacityEffect
├── SkSGClipEffect.h            # ClipEffect
├── SkSGMaskEffect.h            # MaskEffect
├── SkSGColorFilter.h           # ColorFilter, ExternalColorFilter, ModeColorFilter, GradientColorFilter
├── SkSGRenderEffect.h          # Shader, ShaderEffect, MaskShaderEffect, ImageFilter 族, BlenderEffect, LayerEffect
├── SkSGScene.h                 # Scene 高层入口
└── SkSGInvalidationController.h # InvalidationController
```

## 关键类与函数

### 基类层

**SkSGNode.h** - 所有节点的基类:
- `revalidate(ic, ctm)`: 重验证,返回边界
- `invalidate(damage)`: 标记失效
- `observeInval/unobserveInval`: 管理 DAG 父子关系
- `SG_ATTRIBUTE` / `SG_MAPPED_ATTRIBUTE`: 属性声明宏,自动失效

**SkSGRenderNode.h** - 可渲染节点:
- `render(canvas, ctx)`: 渲染
- `nodeAt(point)`: 命中测试
- `isVisible/setVisible`: 可见性
- `RenderContext`: 累积绘制覆盖
- `ScopedRenderContext`: RAII 上下文管理
- `CustomRenderNode`: 外部扩展基类

### 容器节点

**SkSGGroup.h**:
- `Group::Make()` / `Group::Make(children)`
- `addChild` / `removeChild` / `clear`
- 支持隔离渲染 (当内容需要时自动创建图层)

### 绘制节点

**SkSGDraw.h**:
- `Draw::Make(geo, paint)`: 将几何体和画笔组合为绘制操作

### 几何体节点

**SkSGGeometryNode.h**: `clip()`, `draw()`, `contains()`, `asPath()`

**SkSGPath.h**: `Path` - 包装 `SkPath`,属性: Path, FillType

**SkSGRect.h**: `Rect` (SkRect) 和 `RRect` (SkRRect),属性: L/T/R/B, Direction, InitialPointIndex

**SkSGPlane.h**: `Plane` - 无限平面,始终覆盖整个画布

**SkSGMerge.h**: `Merge` - 路径布尔运算,模式: Merge/Union/Intersect/Difference/ReverseDifference/XOR

**SkSGGeometryEffect.h**: 几何效果 (作用于子几何体):
- `TrimEffect`: 路径裁剪 (Start/Stop/Mode)
- `GeometryTransform`: 几何变换
- `FillTypeOverride`: 填充类型覆盖
- `DashEffect`: 虚线 (Intervals/Phase)
- `RoundEffect`: 圆角 (Radius)
- `OffsetEffect`: 偏移 (Offset/MiterLimit/Join)

### 画笔节点

**SkSGPaint.h**: `PaintNode` 基类 + `Color` (SkColor) + `ShaderPaint` (基于 Shader)
- 属性: AntiAlias, Opacity, BlendMode, StrokeWidth, StrokeMiter, Style, StrokeJoin, StrokeCap

**SkSGGradient.h**: `Gradient` 基类 + `LinearGradient` + `RadialGradient`
- 属性: ColorStops, TileMode, StartPoint/EndPoint (线性), StartCenter/EndCenter/StartRadius/EndRadius (径向)

### 变换节点

**SkSGTransform.h**:
- `Transform`: 变换基类,支持 `MakeConcat` 和 `MakeInverse`
- `Matrix<SkMatrix>` / `Matrix<SkM44>`: 具体矩阵变换
- `TransformEffect`: 将变换应用到子渲染节点

### 效果节点

**SkSGEffectNode.h**: 单子节点效果基类

**SkSGOpacityEffect.h**: `OpacityEffect` - 不透明度 (float)

**SkSGClipEffect.h**: `ClipEffect` - 裁剪 (GeometryNode + AntiAlias + ForceClip)

**SkSGMaskEffect.h**: `MaskEffect` - 遮罩
- 模式: AlphaNormal / AlphaInvert / LumaNormal / LumaInvert

**SkSGColorFilter.h**:
- `ColorFilter`: 颜色滤镜基类
- `ExternalColorFilter`: 外部 SkColorFilter 包装
- `ModeColorFilter`: 混合模式颜色滤镜
- `GradientColorFilter`: 梯度色调映射 (用于 Tint/Tritone 效果)

**SkSGRenderEffect.h** (综合):
- `Shader` / `ShaderEffect` / `MaskShaderEffect`: 着色器效果
- `ImageFilter` / `ImageFilterEffect` / `ExternalImageFilter`: 图像滤镜
- `DropShadowImageFilter` / `BlurImageFilter`: 具体图像滤镜
- `BlenderEffect`: 混合器
- `LayerEffect`: 图层混合模式

### 辅助类

**SkSGScene.h**: `Scene` - 高层入口 (render/revalidate/nodeAt)

**SkSGInvalidationController.h**: `InvalidationController` - 脏区域追踪 (inval/bounds/reset)

## 依赖关系

```
核心依赖链:
  SkSGNode.h -> SkRefCnt, SkRect
  SkSGRenderNode.h -> SkSGNode.h, SkBlender, SkColorFilter, SkShader
  SkSGGroup.h -> SkSGRenderNode.h
  SkSGDraw.h -> SkSGRenderNode.h, SkSGGeometryNode.h, SkSGPaint.h
  SkSGEffectNode.h -> SkSGRenderNode.h
  SkSGTransform.h -> SkSGEffectNode.h, SkSGNode.h, SkMatrix, SkM44
  SkSGGeometryEffect.h -> SkSGGeometryNode.h, SkSGTransform.h
  SkSGRenderEffect.h -> SkSGEffectNode.h, SkSGNode.h
  SkSGColorFilter.h -> SkSGEffectNode.h
```

## 设计模式分析

- **不可变创建**: 节点通过 `Make()` 工厂方法创建,构造函数为 private/protected
- **属性自动失效**: `SG_ATTRIBUTE` 宏确保属性设置时自动调用 `invalidate()`
- **值比较优化**: `SG_ATTRIBUTE` 在设置前比较新旧值,避免不必要的失效传播
- **空安全工厂**: `Make()` 方法在参数为空时返回 nullptr,简化调用方的空检查

## 相关文档与参考

- **sksg 主文档**: `docs/yuanlin/modules/sksg/README.md`
- **sksg 实现**: `docs/yuanlin/modules/sksg/src/README.md`
- **skottie 使用**: `docs/yuanlin/modules/skottie/README.md`
