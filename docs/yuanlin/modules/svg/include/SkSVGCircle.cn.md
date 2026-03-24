# SkSVGCircle

> 源文件: modules/svg/include/SkSVGCircle.h

## 概述

`SkSVGCircle.h` 定义了 SVG 圆形元素类,继承自 `SkSVGShape`,实现 SVG `<circle>` 元素的表示和渲染。该类管理圆心坐标和半径属性,并提供将圆形转换为 Skia 图形原语的功能。

## 架构位置

- **继承关系**: `SkSVGCircle` → `SkSVGShape` → `SkSVGTransformableNode` → `SkSVGNode`
- **职责**: SVG 圆形元素的解析、存储和渲染

## 主要类与结构体

```cpp
class SK_API SkSVGCircle final : public SkSVGShape
```

### SVG 属性
```cpp
SVG_ATTR(Cx, SkSVGLength, SkSVGLength(0))  // 圆心 X 坐标
SVG_ATTR(Cy, SkSVGLength, SkSVGLength(0))  // 圆心 Y 坐标
SVG_ATTR(R, SkSVGLength, SkSVGLength(0))   // 半径
```

### 核心方法
- `resolve()`: 解析 SVG 长度为实际圆心和半径,返回 `std::tuple<SkPoint, SkScalar>`
- `onDraw()`: 使用 `SkCanvas::drawCircle()` 绘制
- `onAsPath()`: 转换为包含圆形的 `SkPath`
- `onTransformableObjectBoundingBox()`: 计算边界矩形

## 内部实现细节

### SVG 语法示例
```xml
<circle cx="50" cy="50" r="40"/>
```

### 长度解析
使用 `SkSVGLengthContext` 将 `cx`, `cy`, `r` 转换为绝对像素值,支持百分比、em 等单位。

### 渲染优化
直接调用 `SkCanvas::drawCircle()` 而非通用路径绘制,性能更优。

## 依赖关系

- `modules/svg/include/SkSVGShape.h`: 形状基类
- `modules/svg/include/SkSVGTypes.h`: SVG 类型系统
- `include/core/SkPoint.h`: 圆心坐标
- `include/core/SkScalar.h`: 标量类型(半径)

## 设计模式

使用元组返回多个值(`resolve()`),避免定义临时结构体。

## 性能考量

圆形是最简单的形状之一,使用专门的绘制方法比通用路径更高效。

## 相关文件

- `modules/svg/src/SkSVGCircle.cpp`: 实现文件
- `modules/svg/include/SkSVGEllipse.h`: 椭圆元素(广义形式)
- `modules/svg/include/SkSVGRect.h`: 矩形元素

该类提供了 SVG 圆形元素的高效实现,是 SVG 基础形状渲染的核心组件。
