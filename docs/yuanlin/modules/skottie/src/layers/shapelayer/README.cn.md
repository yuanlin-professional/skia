# skottie/src/layers/shapelayer - 形状图层实现

## 概述

`shapelayer/` 目录实现了 Lottie 形状图层 (Shape Layer) 的解析和场景图构建。形状图层是 Lottie 动画中最常用的图层类型,它通过嵌套的形状元素(几何体、绘制、修饰器)来定义矢量图形。该目录中的 `ShapeBuilder` 类提供了所有形状相关的静态构建方法。

After Effects 的形状图层模型是递归的:一个形状组可以包含子形状组,几何体和绘制节点按照 AE 的特定规则进行匹配。Skottie 将这些元素转换为 sksg 场景图中的 `GeometryNode`、`PaintNode` 和 `Draw` 节点。

## 目录结构

```
shapelayer/
├── BUILD.bazel          # Bazel 构建配置
├── ShapeLayer.h         # ShapeBuilder 类定义
├── ShapeLayer.cpp       # 形状图层解析主逻辑 (attachShape)
├── Rectangle.cpp        # 矩形几何体 (rc)
├── Ellipse.cpp          # 椭圆几何体 (el)
├── Polystar.cpp         # 多角星/多边形几何体 (sr)
├── FillStroke.cpp       # 填充/描边绘制 (fl/st/gf/gs)
├── Gradient.cpp         # 渐变填充/描边
├── MergePaths.cpp       # 路径合并 (mm)
├── TrimPaths.cpp        # 路径裁剪 (tm)
├── RoundCorners.cpp     # 圆角效果 (rd)
├── Repeater.cpp         # 重复器 (rp)
├── PuckerBloat.cpp      # 膨胀/收缩效果 (pb)
└── OffsetPaths.cpp      # 路径偏移 (op)
```

## 关键类与函数

### ShapeBuilder

```cpp
class ShapeBuilder final : SkNoncopyable {
    // 几何体构建
    static sk_sp<sksg::GeometryNode> AttachPathGeometry(jobj, abuilder);
    static sk_sp<sksg::GeometryNode> AttachRRectGeometry(jobj, abuilder);
    static sk_sp<sksg::GeometryNode> AttachEllipseGeometry(jobj, abuilder);
    static sk_sp<sksg::GeometryNode> AttachPolystarGeometry(jobj, abuilder);

    // 绘制构建
    static sk_sp<sksg::PaintNode> AttachColorFill(jobj, abuilder);
    static sk_sp<sksg::PaintNode> AttachColorStroke(jobj, abuilder);
    static sk_sp<sksg::PaintNode> AttachGradientFill(jobj, abuilder);
    static sk_sp<sksg::PaintNode> AttachGradientStroke(jobj, abuilder);

    // 几何效果
    static vector<sk_sp<GeometryNode>> AttachMergeGeometryEffect(...);
    static vector<sk_sp<GeometryNode>> AttachTrimGeometryEffect(...);
    static vector<sk_sp<GeometryNode>> AttachRoundGeometryEffect(...);
    static vector<sk_sp<GeometryNode>> AttachOffsetGeometryEffect(...);
    static vector<sk_sp<GeometryNode>> AttachPuckerBloatGeometryEffect(...);

    // 绘制效果
    static vector<sk_sp<RenderNode>> AttachRepeaterDrawEffect(...);

    // 路径合并
    static sk_sp<sksg::Merge> MergeGeometry(geos, mode);
};
```

### 形状元素类型映射

| Lottie `ty` | 类型 | 文件 | 场景图节点 |
|:---:|------|------|------|
| `sh` | 路径 | (Path.cpp) | `sksg::Path` |
| `rc` | 矩形 | Rectangle.cpp | `sksg::RRect` |
| `el` | 椭圆 | Ellipse.cpp | `sksg::RRect` |
| `sr` | 多角星 | Polystar.cpp | `sksg::Path` |
| `fl` | 颜色填充 | FillStroke.cpp | `sksg::Color` (Fill) |
| `st` | 颜色描边 | FillStroke.cpp | `sksg::Color` (Stroke) |
| `gf` | 渐变填充 | Gradient.cpp | `sksg::ShaderPaint` |
| `gs` | 渐变描边 | Gradient.cpp | `sksg::ShaderPaint` |
| `mm` | 路径合并 | MergePaths.cpp | `sksg::Merge` |
| `tm` | 路径裁剪 | TrimPaths.cpp | `sksg::TrimEffect` |
| `rd` | 圆角 | RoundCorners.cpp | `sksg::RoundEffect` |
| `rp` | 重复器 | Repeater.cpp | 多个 `RenderNode` 副本 |
| `pb` | 膨胀/收缩 | PuckerBloat.cpp | `sksg::GeometryEffect` |
| `op` | 路径偏移 | OffsetPaths.cpp | `sksg::OffsetEffect` |

### 形状构建流程

```
ShapeLayer.cpp :: attachShape(jshapes, ctx)
    |
    遍历 JSON 形状数组 (逆序处理):
    |
    +---> 几何体 (sh/rc/el/sr):
    |       创建 GeometryNode, 加入 geos[]
    |
    +---> 几何效果 (mm/tm/rd/op/pb):
    |       包装现有 geos[] 并替换
    |
    +---> 绘制 (fl/st/gf/gs):
    |       创建 PaintNode
    |       与所有 geos[] 配对生成 Draw 节点
    |       加入 draws[]
    |
    +---> 形状组 (gr):
    |       递归调用 attachShape()
    |       包装 TransformEffect
    |
    +---> 绘制效果 (rp):
    |       复制 draws[] 并应用变换
    |
    +---> 最终: draws[] -> Group (或单个节点)
```

## 依赖关系

```
shapelayer/
  ├── sksg::GeometryNode (Path, Rect, RRect, Merge)
  ├── sksg::PaintNode (Color, ShaderPaint)
  ├── sksg::Draw
  ├── sksg::GeometryEffect (TrimEffect, RoundEffect, OffsetEffect)
  ├── sksg::Gradient (LinearGradient, RadialGradient)
  ├── sksg::Group
  └── sksg::TransformEffect
```

## 相关文档与参考

- **父目录**: `docs/yuanlin/modules/skottie/src/layers/README.md`
- **sksg 几何节点**: `modules/sksg/include/SkSGGeometryNode.h`
- **sksg 几何效果**: `modules/sksg/include/SkSGGeometryEffect.h`
