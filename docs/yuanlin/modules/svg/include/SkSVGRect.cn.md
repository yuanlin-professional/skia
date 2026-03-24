# SkSVGRect

> 源文件: modules/svg/include/SkSVGRect.h

## 概述

`SkSVGRect.h` 定义了 Skia SVG 模块中的矩形元素类。该类继承自 `SkSVGShape`,实现了 SVG `<rect>` 元素的解析、属性管理和渲染功能,支持圆角矩形。作为 Skia SVG DOM 树的节点类型之一,它负责将 SVG 标记语言中的 `<rect>` 元素转换为可渲染的图形对象。

## 架构位置

- **路径**: `modules/svg/include/SkSVGRect.h`
- **模块层次**: SVG 模块 > 形状元素
- **继承关系**: `SkSVGRect` → `SkSVGShape` → `SkSVGTransformableNode` → `SkSVGNode`
- **职责**: SVG 矩形元素的表示和渲染

## 主要类与结构体

### SkSVGRect 类

```cpp
class SK_API SkSVGRect final : public SkSVGShape
```

**核心功能**:
- SVG `<rect>` 元素的内存表示
- 矩形属性解析(位置、尺寸、圆角)
- 转换为 Skia `SkRRect` 或 `SkPath`
- 渲染到 Canvas

### 主要成员

#### 工厂方法
```cpp
static sk_sp<SkSVGRect> Make()
```

#### SVG 属性
```cpp
SVG_ATTR(X, SkSVGLength, SkSVGLength(0))        // 左上角 X 坐标
SVG_ATTR(Y, SkSVGLength, SkSVGLength(0))        // 左上角 Y 坐标
SVG_ATTR(Width, SkSVGLength, SkSVGLength(0))    // 宽度
SVG_ATTR(Height, SkSVGLength, SkSVGLength(0))   // 高度
SVG_OPTIONAL_ATTR(Rx, SkSVGLength)              // X 方向圆角半径
SVG_OPTIONAL_ATTR(Ry, SkSVGLength)              // Y 方向圆角半径
```

## 公共 API 函数

### 属性访问
- `getX()`, `setX()`: X 坐标
- `getY()`, `setY()`: Y 坐标
- `getWidth()`, `setWidth()`: 宽度
- `getHeight()`, `setHeight()`: 高度
- `getRx()`, `setRx()`: X 圆角半径(可选)
- `getRy()`, `setRy()`: Y 圆角半径(可选)

### 渲染接口(重写)
- `parseAndSetAttribute()`: 解析 SVG 属性字符串
- `onDraw()`: 绘制矩形到 Canvas
- `onAsPath()`: 转换为 `SkPath`
- `onTransformableObjectBoundingBox()`: 计算边界框

### 私有辅助方法
- `resolve()`: 解析 SVG 长度值为实际的 `SkRRect`

## 内部实现细节

### 属性解析

**SVG 语法示例**:
```xml
<rect x="10" y="10" width="100" height="50" rx="5" ry="5"/>
```

**属性特性**:
- `x`, `y`: 默认为 0
- `width`, `height`: 必须 > 0 才有效
- `rx`, `ry`: 可选,控制圆角半径
  - 如果只指定一个,另一个取相同值
  - 自动限制为宽/高的一半

### 圆角处理

**规则**:
1. 如果 `rx` 和 `ry` 都未指定,绘制普通矩形
2. 如果只指定一个,另一个默认等于指定值
3. 圆角半径会被裁剪到最大允许值(宽高的一半)

### 渲染流程

```
SVG 属性 → resolve()
    ↓
计算 SkRRect (考虑 LengthContext)
    ↓
onDraw() 使用 SkCanvas::drawRRect()
```

**长度解析**: 使用 `SkSVGLengthContext` 将 SVG 长度单位(px, %, em 等)转换为绝对像素值。

## 依赖关系

**核心依赖**:
- `modules/svg/include/SkSVGShape.h`: 形状基类
- `modules/svg/include/SkSVGTypes.h`: `SkSVGLength` 等类型
- `include/core/SkRRect.h`: 圆角矩形数据结构
- `include/core/SkPath.h`: 路径数据结构

**渲染依赖**:
- `modules/svg/include/SkSVGLengthContext.h`: 长度单位转换
- `modules/svg/include/SkSVGRenderContext.h`: 渲染上下文

## 设计模式与设计决策

### 1. 宏驱动属性系统

使用 `SVG_ATTR` 和 `SVG_OPTIONAL_ATTR` 宏:
- 自动生成 getter/setter
- 类型安全
- 减少样板代码

### 2. 延迟计算

`resolve()` 方法在需要时计算实际几何形状,而非构造时计算,支持动态的视口和单位系统。

### 3. 类型安全的单位系统

使用 `SkSVGLength` 而非原始数值,保留单位信息直到渲染时解析。

## 性能考量

### 1. 圆角矩形优化

- 如果无圆角,可使用更快的 `SkCanvas::drawRect()`
- 圆角矩形使用优化的 `drawRRect()` 而非通用路径

### 2. 路径转换成本

`onAsPath()` 将矩形转换为路径,仅在需要时调用(如裁剪、布尔运算)。

### 3. 属性访问效率

属性直接存储为成员变量,访问为 O(1)。

## 相关文件

### 实现和测试

1. **`modules/svg/src/SkSVGRect.cpp`**: 实现文件,包含 `resolve()` 和渲染逻辑
2. **`tests/SVGTest.cpp`**: SVG 模块测试,可能包含矩形测试用例

### 相关 SVG 元素

3. **`modules/svg/include/SkSVGCircle.h`**: 圆形元素
4. **`modules/svg/include/SkSVGEllipse.h`**: 椭圆元素
5. **`modules/svg/include/SkSVGPath.h`**: 通用路径元素
6. **`modules/svg/include/SkSVGPoly.h`**: 多边形/折线元素

### 基础设施

7. **`modules/svg/include/SkSVGShape.h`**: 所有形状的基类
8. **`modules/svg/include/SkSVGNode.h`**: SVG 节点基类,定义属性系统
9. **`modules/svg/include/SkSVGDOM.h`**: SVG 文档对象模型,解析入口

该类是 Skia SVG 渲染管线的核心组件之一,提供了 SVG 矩形元素到 Skia 图形原语的高效映射,支持标准 SVG 矩形语法和圆角扩展。
