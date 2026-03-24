# SkSVGLine

> 源文件: modules/svg/src/SkSVGLine.cpp

## 概述

`SkSVGLine` 实现了 SVG 基本形状 `<line>` 元素，用于在两个点之间绘制直线段。该类提供了线段的解析、坐标解析和渲染功能，支持 SVG 长度单位（包括百分比、像素、em 等）并正确处理坐标系统变换。作为 Skia SVG 模块的基础形状之一，`SkSVGLine` 展示了如何将 SVG 声明式的形状定义转换为 Skia 的绘图操作和路径表示。

## 架构位置

`SkSVGLine` 在 Skia SVG 架构中的位置：

- **模块路径**: `modules/svg/src/`
- **继承层次**: `SkSVGNode` → `SkSVGShape` → `SkSVGLine`
- **功能角色**: 基本形状节点，实现线段图形
- **形状类别**: 几何原语，与 `<rect>`、`<circle>`、`<polygon>` 并列

在形状节点家族中，`SkSVGLine` 是最简单的几何形状之一，只需要两个端点定义。

## 主要类与结构体

### SkSVGLine 类

继承自 `SkSVGShape`，实现线段特定的功能：

```cpp
class SkSVGLine : public SkSVGShape {
public:
    // 构造函数
    SkSVGLine() : INHERITED(SkSVGTag::kLine) {}

    // 属性: x1, y1, x2, y2（通过 SVG_ATTR 宏定义在头文件中）

protected:
    // 绘制实现
    void onDraw(SkCanvas*, const SkSVGLengthContext&,
                const SkPaint&, SkPathFillType) const override;

    // 路径转换
    SkPath onAsPath(const SkSVGRenderContext&) const override;

private:
    // 属性解析
    bool parseAndSetAttribute(const char* n, const char* v) override;

    // 坐标解析辅助方法
    std::tuple<SkPoint, SkPoint> resolve(const SkSVGLengthContext&) const;
};
```

### 关键属性

虽然实现文件中未显示属性声明，但从代码逻辑可知包含以下属性：

```cpp
SkSVGLength fX1;  // 起点 X 坐标
SkSVGLength fY1;  // 起点 Y 坐标
SkSVGLength fX2;  // 终点 X 坐标
SkSVGLength fY2;  // 终点 Y 坐标
```

## 公共 API 函数

### SkSVGLine::SkSVGLine()

构造函数，初始化为线段类型节点。

```cpp
SkSVGLine::SkSVGLine() : INHERITED(SkSVGTag::kLine) {}
```

**初始化**: 设置节点标签类型为 `kLine`，用于类型识别和调试。

### bool parseAndSetAttribute(const char* n, const char* v)

解析并设置线段的属性。

```cpp
bool SkSVGLine::parseAndSetAttribute(const char* n, const char* v) {
    return INHERITED::parseAndSetAttribute(n, v) ||
           this->setX1(SkSVGAttributeParser::parse<SkSVGLength>("x1", n, v)) ||
           this->setY1(SkSVGAttributeParser::parse<SkSVGLength>("y1", n, v)) ||
           this->setX2(SkSVGAttributeParser::parse<SkSVGLength>("x2", n, v)) ||
           this->setY2(SkSVGAttributeParser::parse<SkSVGLength>("y2", n, v));
}
```

**解析顺序**:
1. 首先尝试父类的属性解析（如 `stroke`、`fill`、`transform` 等）
2. 如果父类未处理，尝试解析 `x1`、`y1`、`x2`、`y2`
3. 使用短路求值，一旦匹配即返回 `true`

**支持的长度单位**: 像素（px）、百分比（%）、em、pt、cm、mm 等。

## 内部实现细节

### std::tuple<SkPoint, SkPoint> resolve(const SkSVGLengthContext& lctx) const

解析线段的两个端点坐标。

```cpp
std::tuple<SkPoint, SkPoint> SkSVGLine::resolve(const SkSVGLengthContext& lctx) const {
    return std::make_tuple(
        SkPoint::Make(lctx.resolve(fX1, SkSVGLengthContext::LengthType::kHorizontal),
                      lctx.resolve(fY1, SkSVGLengthContext::LengthType::kVertical)),
        SkPoint::Make(lctx.resolve(fX2, SkSVGLengthContext::LengthType::kHorizontal),
                      lctx.resolve(fY2, SkSVGLengthContext::LengthType::kVertical)));
}
```

**长度解析**:
- **水平坐标**: 使用 `kHorizontal` 类型，百分比相对于视口宽度
- **垂直坐标**: 使用 `kVertical` 类型，百分比相对于视口高度
- **返回值**: 元组包含起点和终点的 `SkPoint` 对象

**示例**:
```xml
<line x1="10%" y1="20" x2="90%" y2="80"/>
```
对于 800x600 的视口：
- 起点: (80, 20)
- 终点: (720, 80)

### void onDraw(SkCanvas*, const SkSVGLengthContext&, const SkPaint&, SkPathFillType) const

直接在画布上绘制线段。

```cpp
void SkSVGLine::onDraw(SkCanvas* canvas, const SkSVGLengthContext& lctx,
                       const SkPaint& paint, SkPathFillType) const {
    SkPoint p0, p1;
    std::tie(p0, p1) = this->resolve(lctx);

    canvas->drawLine(p0, p1, paint);
}
```

**绘制流程**:
1. 调用 `resolve()` 获取端点坐标
2. 使用结构化绑定（`std::tie`）解包元组
3. 调用 `SkCanvas::drawLine()` 直接绘制

**性能优势**: 直接绘制避免创建 `SkPath` 对象，对于简单线段更高效。

**参数说明**:
- `canvas`: 目标画布
- `lctx`: 长度上下文，用于解析坐标
- `paint`: 绘图属性（颜色、描边宽度等）
- `SkPathFillType`: 对于线段未使用（线段无填充）

### SkPath onAsPath(const SkSVGRenderContext& ctx) const

将线段转换为路径表示。

```cpp
SkPath SkSVGLine::onAsPath(const SkSVGRenderContext& ctx) const {
    SkPoint p0, p1;
    std::tie(p0, p1) = this->resolve(ctx.lengthContext());

    return this->mapToParent(SkPath::Line(p0, p1));
}
```

**转换流程**:
1. 从渲染上下文获取长度上下文
2. 解析端点坐标
3. 使用 `SkPath::Line()` 创建线段路径
4. 应用父节点的变换（`mapToParent()`）

**用途**:
- **裁剪路径**: 线段可以用作裁剪区域的边界
- **蒙版**: 线段路径可以用于创建蒙版
- **路径操作**: 支持路径合并、差集等操作
- **碰撞检测**: 提供几何表示用于相交测试

## 依赖关系

### Skia 核心依赖

- **include/core/SkCanvas.h**: 画布绘图接口
- **include/core/SkPath.h**: 路径表示和操作
- **include/core/SkPoint.h**: 二维点类型
- **include/core/SkPathTypes.h**: 路径填充类型枚举

### SVG 模块依赖

- **modules/svg/include/SkSVGLine.h**: 类声明
- **modules/svg/include/SkSVGAttributeParser.h**: 属性解析器
- **modules/svg/include/SkSVGRenderContext.h**: 渲染上下文，提供长度上下文访问

### 前置声明

```cpp
class SkPaint;  // 前置声明，避免包含重量级头文件
```

## 设计模式与设计决策

### 模板方法模式

`SkSVGLine` 实现了基类定义的虚函数：

- **onDraw**: 具体绘制实现
- **onAsPath**: 路径转换实现
- **parseAndSetAttribute**: 属性解析实现

基类控制整体流程，派生类提供特定行为。

### 延迟计算

坐标解析延迟到渲染时：

```cpp
std::tie(p0, p1) = this->resolve(lctx);
```

**优势**:
- **灵活性**: 支持百分比单位，依赖于实际视口大小
- **动态性**: 视口改变时无需重新解析 XML
- **内存效率**: 存储紧凑的 `SkSVGLength` 而非浮点坐标

### 直接绘制 vs 路径转换

提供两种接口：

1. **直接绘制** (`onDraw`): 优化的快速路径
2. **路径转换** (`onAsPath`): 通用接口，支持高级操作

这种双重接口设计平衡了性能和功能性。

### 坐标轴类型区分

解析 X 和 Y 坐标时使用不同的类型：

```cpp
lctx.resolve(fX1, LengthType::kHorizontal)
lctx.resolve(fY1, LengthType::kVertical)
```

**原因**: 确保百分比单位正确解析（X 相对于宽度，Y 相对于高度）。

## 性能考量

### 直接绘制优势

`onDraw` 使用 `SkCanvas::drawLine()` 而非通过 `SkPath`：

**性能优势**:
- **零分配**: 不创建堆对象
- **内联友好**: 简单调用易于编译器优化
- **GPU 优化**: Skia GPU 后端对直线有专门优化

### 路径创建开销

`onAsPath` 创建 `SkPath` 对象：

```cpp
return this->mapToParent(SkPath::Line(p0, p1));
```

**开销**:
- 分配 `SkPath` 对象
- 应用变换（`mapToParent`）
- 可能的路径数据拷贝

对于频繁调用，可能成为瓶颈。

### 属性解析优化

使用短路求值减少不必要的解析：

```cpp
return INHERITED::parseAndSetAttribute(n, v) ||  // 如果父类处理了，停止
       this->setX1(...) ||  // 否则尝试 x1
       this->setY1(...) ||  // 依次类推
       ...
```

平均情况下，只需要少量字符串比较。

### 内存占用

`SkSVGLine` 对象占用：

```
基类大小 + 4 × sizeof(SkSVGLength)
```

`SkSVGLength` 通常是 8-12 字节（值 + 单位），因此线段对象约 50-100 字节。

## 相关文件

### 头文件

- **modules/svg/include/SkSVGLine.h**: 类声明和属性定义

### 基类

- **modules/svg/include/SkSVGShape.h**: 形状基类，提供通用绘制接口
- **modules/svg/src/SkSVGShape.cpp**: 形状基类实现

### 相关形状

- **modules/svg/src/SkSVGRect.cpp**: 矩形实现
- **modules/svg/src/SkSVGCircle.cpp**: 圆形实现
- **modules/svg/src/SkSVGEllipse.cpp**: 椭圆实现
- **modules/svg/src/SkSVGPolygon.cpp**: 多边形实现
- **modules/svg/src/SkSVGPath.cpp**: 路径实现

### 渲染上下文

- **modules/svg/include/SkSVGRenderContext.h**: 提供长度解析和变换管理
- **modules/svg/src/SkSVGRenderContext.cpp**: 长度上下文实现

### 属性解析

- **modules/svg/include/SkSVGAttributeParser.h**: 通用属性解析接口
- **modules/svg/src/SkSVGAttributeParser.cpp**: `SkSVGLength` 解析器实现

### 使用示例

**基本线段**:
```xml
<line x1="10" y1="20" x2="100" y2="80" stroke="black" stroke-width="2"/>
```

**百分比坐标**:
```xml
<line x1="0%" y1="50%" x2="100%" y2="50%" stroke="red"/>
```

**混合单位**:
```xml
<line x1="10px" y1="1em" x2="50%" y2="100" stroke="blue"/>
```

**带变换**:
```xml
<line x1="0" y1="0" x2="50" y2="50" stroke="green" transform="rotate(45)"/>
```

该实现简洁高效，展示了 Skia SVG 模块如何将声明式 SVG 元素转换为高性能的图形渲染。
