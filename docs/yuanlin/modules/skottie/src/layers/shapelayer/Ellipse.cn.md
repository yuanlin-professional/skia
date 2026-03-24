# Ellipse

> 源文件: modules/skottie/src/layers/shapelayer/Ellipse.cpp

## 概述

`Ellipse.cpp` 实现了 Skottie 形状层系统中的椭圆几何生成器。该模块创建椭圆和圆形路径,支持尺寸和位置的动画。这是 After Effects Ellipse 形状在 Skottie 中的实现。

## 架构位置

- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **角色**: 几何生成器,通过 `ShapeBuilder` 创建椭圆几何节点

## 主要类与结构体

### EllipseGeometryAdapter
```cpp
class EllipseGeometryAdapter final : public DiscardableAdapterBase<EllipseGeometryAdapter, sksg::RRect>
```

椭圆几何适配器,管理椭圆属性的动画和同步。

**成员变量**:
- `fSize`: 椭圆尺寸(宽度和高度)
- `fPosition`: 中心位置

## 公共 API 函数

### AttachEllipseGeometry
```cpp
sk_sp<sksg::GeometryNode> ShapeBuilder::AttachEllipseGeometry(
    const skjson::ObjectValue& jellipse,
    const AnimationBuilder* abuilder)
```

**JSON 参数**:
- `"s"`: 尺寸(Size),{width, height}
- `"p"`: 位置(Position,中心点)
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
从中心和尺寸计算椭圆的外接矩形。

### 椭圆创建
```cpp
this->node()->setRRect(SkRRect::MakeOval(bounds));
```
使用 `SkRRect::MakeOval` 创建椭圆,这是圆角矩形的特殊情况(圆角半径为半宽/半高)。

### 起始点设置
```cpp
this->node()->setInitialPointIndex(1); // (Center, Top)
```
设置路径起始点为顶部中心,匹配 AE 行为。

## 依赖关系

- **Skia 核心**: `SkRRect`, `SkRect`, `SkPathDirection`
- **SkSG**: `sksg::RRect`(圆角矩形/椭圆节点)
- **Skottie**: `DiscardableAdapterBase`, `Vec2Value`

## 设计模式与设计决策

### 适配器模式
`EllipseGeometryAdapter` 适配 JSON 动画数据到 `sksg::RRect` 节点。

### 几何节点复用
使用 `SkRRect` 表示椭圆而非通用路径:
- 更高效的渲染
- 更好的抗锯齿
- 可能的 GPU 加速

## 性能考量

- **可丢弃优化**: 尺寸为 0 时可优化掉适配器
- **高效表示**: `SkRRect` 比贝塞尔曲线路径更高效
- **移动语义**: 智能指针传递避免引用计数开销

## 相关文件

- `modules/sksg/include/SkSGRect.h`: `RRect` 节点实现
- `modules/skottie/src/layers/shapelayer/Rectangle.cpp`: 矩形生成器
- `modules/skottie/src/layers/shapelayer/Polystar.cpp`: 多边形/星形生成器
- `include/core/SkRRect.h`: Skia 圆角矩形 API
