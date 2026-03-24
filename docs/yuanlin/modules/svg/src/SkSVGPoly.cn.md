# SkSVGPoly

> 源文件: modules/svg/src/SkSVGPoly.cpp

## 概述

`SkSVGPoly.cpp` 实现了 SVG 多边形（`<polygon>`）和折线（`<polyline>`）的共享功能。这两种元素都由一系列点定义，唯一区别是多边形自动闭合首尾点。该实现解析点列表并构建 `SkPath` 对象，利用 `SkPath::Polygon()` 方法高效创建多边形路径。实现简洁，只有 55 行代码，展示了如何通过继承和条件逻辑共享相似元素的实现。

## 架构位置

- **模块路径**: `modules/svg/src/`
- **对应头文件**: `modules/svg/include/SkSVGPoly.h`
- **继承层次**: `SkSVGNode` → `SkSVGShape` → `SkSVGPoly`
- **派生类**: `SkSVGPolygon` 和 `SkSVGPolyline`（标签不同但逻辑相同）

## 主要类与结构体

### 实现的方法

1. **SkSVGPoly(SkSVGTag)**: 构造函数，接受标签类型
2. **parseAndSetAttribute()**: 解析点列表
3. **onDraw()**: 绘制多边形/折线
4. **onAsPath()**: 路径转换
5. **onTransformableObjectBoundingBox()**: 边界框计算

## 公共 API 函数

### SkSVGPoly::SkSVGPoly(SkSVGTag t)

构造函数，接受标签类型（`kPolygon` 或 `kPolyline`）。

```cpp
SkSVGPoly::SkSVGPoly(SkSVGTag t) : INHERITED(t) {}
```

### bool parseAndSetAttribute(const char* n, const char* v)

解析 `points` 属性并构建路径。

```cpp
bool SkSVGPoly::parseAndSetAttribute(const char* n, const char* v) {
    if (INHERITED::parseAndSetAttribute(n, v)) {
        return true;
    }

    if (this->setPoints(SkSVGAttributeParser::parse<SkSVGPointsType>("points", n, v))) {
        // TODO: 可以只保存点数组，按需创建路径
        // 只有多边形自动闭合
        fPath = SkPath::Polygon(fPoints, this->tag() == SkSVGTag::kPolygon);
    }

    return false;  // 此节点无其他属性
}
```

**关键逻辑**:
- 解析 `points` 属性为点数组 `fPoints`
- 使用 `SkPath::Polygon()` 创建路径
- 根据标签类型决定是否闭合路径（`kPolygon` 闭合，`kPolyline` 不闭合）
- TODO 注释表明可能的优化：延迟路径创建

## 内部实现细节

### void onDraw()

绘制多边形或折线。

```cpp
void SkSVGPoly::onDraw(SkCanvas* canvas, const SkSVGLengthContext&,
                       const SkPaint& paint, SkPathFillType fillType) const {
    // 继承的填充类型需要在绘制时应用
    fPath.setFillType(fillType);
    canvas->drawPath(fPath, paint);
}
```

**填充类型处理**: `fillType` 遵循继承规则，在绘制时动态设置到路径。

### SkPath onAsPath()

转换为路径表示。

```cpp
SkPath SkSVGPoly::onAsPath(const SkSVGRenderContext& ctx) const {
    SkPath path = fPath;

    // clip-rule 可以继承，需要在裁剪时应用
    path.setFillType(ctx.presentationContext().fInherited.fClipRule->asFillType());

    return this->mapToParent(path);
}
```

**裁剪规则**: 从渲染上下文获取继承的 `clip-rule` 并应用到路径。

### SkRect onTransformableObjectBoundingBox()

计算边界框。

```cpp
SkRect SkSVGPoly::onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const {
    return fPath.getBounds();
}
```

**简单实现**: 直接使用路径的边界框。

## 依赖关系

### Skia 核心依赖

- **include/core/SkCanvas.h**: 绘图操作
- **include/core/SkPath.h**: 路径创建和操作
- **include/core/SkPoint.h**: 点类型

### SVG 模块依赖

- **modules/svg/include/SkSVGPoly.h**: 类声明
- **modules/svg/include/SkSVGAttribute.h**: 属性类型（`SkSVGPointsType`）
- **modules/svg/include/SkSVGAttributeParser.h**: 点列表解析
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文

## 设计模式与设计决策

### 共享实现模式

使用单一类实现两种相似元素：

```cpp
fPath = SkPath::Polygon(fPoints, this->tag() == SkSVGTag::kPolygon);
//                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//                                根据标签决定是否闭合
```

**优势**:
- 减少代码重复
- 两种元素的行为差异最小化
- 易于维护

### 路径缓存

在属性解析时预计算路径：

```cpp
fPath = SkPath::Polygon(fPoints, ...);
```

**权衡**:
- **优点**: 避免每次绘制时重建路径
- **缺点**: 增加内存使用（存储点数组和路径）
- **TODO 注释**: 建议延迟路径创建，只存储点

### 填充类型延迟设置

填充类型和裁剪规则在使用时动态设置：

```cpp
fPath.setFillType(fillType);  // 绘制时
path.setFillType(...);        // 裁剪时
```

**原因**: 这些属性可以继承，需要在上下文确定后应用。

## 性能考量

### 路径预计算

优势：
- 避免每次绘制时解析点和构建路径
- 绘制性能优化

劣势：
- 内存占用增加（点数组 + 路径数据）
- 对于大量点的多边形可能浪费内存

### SkPath::Polygon 效率

`SkPath::Polygon()` 是高效的路径创建方法：
- 一次性分配路径数据
- 直接从点数组构建
- 内部优化的连续线段

### 潜在优化

TODO 注释提到的优化：

```cpp
// TODO: 可以只保存点数组，按需创建路径
```

延迟路径创建可以：
- 减少内存使用
- 允许在不同上下文中使用不同的填充类型
- 适合大量但不常绘制的多边形

## 相关文件

### 头文件

- **modules/svg/include/SkSVGPoly.h**: 类声明和派生类

### 基类

- **modules/svg/include/SkSVGShape.h**: 形状基类
- **modules/svg/src/SkSVGShape.cpp**: 形状基类实现

### 相关形状

- **modules/svg/src/SkSVGPath.cpp**: 通用路径元素
- **modules/svg/src/SkSVGLine.cpp**: 简单线段
- **modules/svg/src/SkSVGRect.cpp**: 矩形

### 属性解析

- **modules/svg/src/SkSVGAttributeParser.cpp**: 点列表解析实现

### 使用示例

**多边形（自动闭合）**:
```xml
<polygon points="100,10 40,198 190,78 10,78 160,198"
         fill="lime" stroke="purple" stroke-width="3"/>
```

**折线（不闭合）**:
```xml
<polyline points="20,20 40,25 60,40 80,120 120,140 200,180"
          fill="none" stroke="blue" stroke-width="2"/>
```

**复杂多边形**:
```xml
<polygon points="50,5 100,50 50,95 5,50"
         fill="yellow" stroke="black" fill-rule="evenodd"/>
```

**坐标列表格式**:
```xml
<polygon points="0,0 100,0 100,100 0,100"/>        <!-- 逗号分隔 -->
<polygon points="0 0 100 0 100 100 0 100"/>        <!-- 空格分隔 -->
<polygon points="0,0, 100,0, 100,100, 0,100"/>    <!-- 混合格式 -->
```

该实现通过共享代码优雅地支持了多边形和折线两种元素，展示了如何在保持代码简洁的同时支持相似但略有差异的 SVG 元素。
