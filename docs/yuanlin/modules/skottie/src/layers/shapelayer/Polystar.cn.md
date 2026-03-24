# Polystar

> 源文件: modules/skottie/src/layers/shapelayer/Polystar.cpp

## 概述

`Polystar.cpp` 实现了 Skottie 形状层系统中的多边形和星形几何生成器。该模块通过指定顶点数、半径和圆角参数生成规则多边形或星形路径,支持所有参数的动画。这是 After Effects Polystar 形状在 Skottie 中的实现。

## 架构位置

- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **角色**: 几何生成器,通过 `ShapeBuilder` 创建多边形/星形几何节点

## 主要类与结构体

### PolystarGeometryAdapter
```cpp
class PolystarGeometryAdapter final : public DiscardableAdapterBase<PolystarGeometryAdapter, sksg::Path>
```

**Type 枚举**:
```cpp
enum class Type { kStar, kPoly };
```
- **kStar**: 星形(有内外半径)
- **kPoly**: 多边形(仅外半径)

**成员变量**:
- `fPosition`: 中心位置
- `fPointCount`: 顶点数量
- `fRotation`: 旋转角度
- `fInnerRadius`: 内半径(星形)
- `fOuterRadius`: 外半径
- `fInnerRoundness`: 内圆角(TODO: 未实现)
- `fOuterRoundness`: 外圆角(TODO: 未实现)

## 公共 API 函数

### AttachPolystarGeometry
```cpp
sk_sp<sksg::GeometryNode> ShapeBuilder::AttachPolystarGeometry(
    const skjson::ObjectValue& jstar,
    const AnimationBuilder* abuilder)
```

**JSON 参数**:
- `"sy"`: 类型(Shape Type)
  - `1`: 星形
  - `2`: 多边形
- `"pt"`: 点数(Point Count)
- `"p"`: 位置(Position)
- `"r"`: 旋转(Rotation)
- `"ir"`: 内半径(Inner Radius,星形)
- `"or"`: 外半径(Outer Radius)
- `"is"`: 内圆角(Inner Roundness,未实现)
- `"os"`: 外圆角(Outer Roundness,未实现)

## 内部实现细节

### 路径生成算法
```cpp
const auto count = SkToUInt(SkTPin(SkScalarRoundToInt(fPointCount), 0, kMaxPointCount));
const auto arc = sk_ieee_float_divide(SK_ScalarPI * 2, count);

auto angle = SkDegreesToRadians(fRotation - 90);
poly.moveTo(pt_on_circle(fPosition, fOuterRadius, angle));

for (unsigned i = 0; i < count; ++i) {
    if (fType == Type::kStar) {
        poly.lineTo(pt_on_circle(fPosition, fInnerRadius, angle + arc * 0.5f));
    }
    angle += arc;
    poly.lineTo(pt_on_circle(fPosition, fOuterRadius, angle));
}
```

**星形**: 在每两个外顶点之间插入一个内顶点
**多边形**: 只连接外顶点

### 圆周点计算
```cpp
const auto pt_on_circle = [](const SkV2& c, SkScalar r, SkScalar a) {
    return SkPoint::Make(c.x + r * std::cos(a),
                         c.y + r * std::sin(a));
};
```

### 顶点数限制
```cpp
static constexpr int kMaxPointCount = 100000;
```
防止过大的顶点数导致性能问题。

### 起始角度调整
```cpp
auto angle = SkDegreesToRadians(fRotation - 90);
```
减去 90 度使 0 度旋转对应顶部(Y 轴负方向)。

### 路径预留
```cpp
poly.incReserve(fType == Type::kStar ? count * 2 : count);
```
星形需要两倍顶点数(内外交替)。

## 依赖关系

- **Skia 核心**: `SkPathBuilder`, `SkPoint`, `std::cos`, `std::sin`
- **SkSG**: `sksg::Path`(路径几何节点)
- **Skottie**: `DiscardableAdapterBase`, `Vec2Value`, `ScalarValue`

## 设计模式与设计决策

### 策略模式
`Type` 枚举实现不同的形状生成策略(星形 vs 多边形)。

### Lambda 函数
使用 lambda 函数 `pt_on_circle` 简化圆周点计算,提高代码可读性。

## 性能考量

- **顶点数限制**: 最大 100000 个顶点防止性能崩溃
- **路径预留**: `incReserve` 避免动态增长导致的重新分配
- **安全除法**: `sk_ieee_float_divide` 处理除零情况
- **四舍五入**: 将浮点顶点数转换为整数,避免部分顶点

## 相关文件

- `modules/sksg/include/SkSGPath.h`: `Path` 节点实现
- `modules/skottie/src/layers/shapelayer/Rectangle.cpp`: 矩形生成器
- `modules/skottie/src/layers/shapelayer/Ellipse.cpp`: 椭圆生成器
- `include/core/SkPathBuilder.h`: 路径构建器 API
