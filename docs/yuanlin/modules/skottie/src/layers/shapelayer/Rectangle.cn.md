# Rectangle

> 源文件: modules/skottie/src/layers/shapelayer/Rectangle.cpp

## 概述

`Rectangle.cpp` 实现了 Skottie 形状层系统中的矩形几何生成器。该模块创建矩形和圆角矩形路径,支持尺寸、位置和圆角半径的动画。这是 After Effects Rectangle 形状在 Skottie 中的实现。

## 架构位置

- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **角色**: 几何生成器,通过 `ShapeBuilder` 创建矩形几何节点

## 主要类与结构体

### RectangleGeometryAdapter
```cpp
class RectangleGeometryAdapter final : public DiscardableAdapterBase<RectangleGeometryAdapter, sksg::RRect>
```

矩形几何适配器,管理矩形属性的动画和同步。

**成员变量**:
- `fSize`: 矩形尺寸(默认 {0,0})
- `fPosition`: 中心位置(默认 {0,0})
- `fRoundness`: 圆角半径(默认 0)

**核心方法**:
- `onSync()`: 计算边界矩形并创建圆角矩形

## 公共 API 函数

### AttachRRectGeometry
```cpp
sk_sp<sksg::GeometryNode> ShapeBuilder::AttachRRectGeometry(
    const skjson::ObjectValue& jrect,
    const AnimationBuilder* abuilder)
```

创建矩形几何节点。

**JSON 参数**:
- `"s"`: 尺寸(Size)
- `"p"`: 位置(Position,中心点)
- `"r"`: 圆角半径(Roundness)
- `"d"`: 方向(Direction)
  - `3`: 逆时针(CCW)
  - `其他`: 顺时针(CW,默认)

## 内部实现细节

### 边界计算
```cpp
const auto bounds = SkRect::MakeXYWH(fPosition.x - fSize.x / 2,
                                     fPosition.y - fSize.y / 2,
                                     fSize.x, fSize.y);
```
从中心位置和尺寸计算左上角坐标。

### 起始点设置
```cpp
this->node()->setInitialPointIndex(2); // (Right, Top - radius.y)
```
设置路径起始点为右上角减去圆角半径,匹配 AE 行为。

### 圆角矩形创建
```cpp
this->node()->setRRect(SkRRect::MakeRectXY(bounds, fRoundness, fRoundness));
```
使用相同的 X/Y 圆角半径创建对称圆角。

## 依赖关系

- **Skia 核心**: `SkRRect`, `SkRect`, `SkPathDirection`
- **SkSG**: `sksg::RRect`(圆角矩形几何节点)
- **Skottie**: `DiscardableAdapterBase`, `Vec2Value`, `ScalarValue`

## 设计模式与设计决策

### 适配器模式
`RectangleGeometryAdapter` 适配 JSON 动画数据到 `sksg::RRect` 节点。

### 几何节点复用
使用 SkSG 的 `RRect` 节点而非直接创建路径,利用优化的矩形渲染路径。

## 性能考量

- **可丢弃优化**: 尺寸为 0 时可优化掉适配器
- **高效矩形**: `SkRRect` 比通用 `SkPath` 更高效
- **移动语义**: 智能指针传递避免引用计数开销

## 相关文件

- `modules/sksg/include/SkSGRect.h`: `RRect` 节点实现
- `modules/skottie/src/layers/shapelayer/Ellipse.cpp`: 椭圆几何生成器
- `modules/skottie/src/layers/shapelayer/Polystar.cpp`: 多边形/星形生成器
