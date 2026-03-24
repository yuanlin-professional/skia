# SkSVGCircle

> 源文件: [modules/svg/src/SkSVGCircle.cpp](../../../../modules/svg/src/SkSVGCircle.cpp)

## 概述

`SkSVGCircle` 实现了 SVG `<circle>` 元素，用于绘制圆形。它通过 `cx`（中心 X 坐标）、`cy`（中心 Y 坐标）和 `r`（半径）三个属性定义圆的几何参数，支持将圆渲染到画布、转换为路径以及计算对象边界框。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGShape
              └── SkSVGCircle      ← 本文件
```

## 主要类与结构体

### `SkSVGCircle`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fCx` | `SkSVGLength` | 圆心 X 坐标 |
| `fCy` | `SkSVGLength` | 圆心 Y 坐标 |
| `fR` | `SkSVGLength` | 半径 |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析圆的三个属性：`cx`、`cy`、`r`。先调用基类方法处理通用属性，然后依次尝试解析圆特有的属性。

## 内部实现细节

### 几何解析 (`resolve`)

返回 `std::tuple<SkPoint, SkScalar>`（圆心和半径）：
1. `cx` 按水平方向解析长度
2. `cy` 按垂直方向解析长度
3. `r` 按"其他"方向解析长度（通常为视口对角线的某个比例）

### 绘制 (`onDraw`)

解析几何参数后，仅在 `r > 0` 时调用 `SkCanvas::drawCircle()`，遵循 SVG 规范中"零半径不渲染"的规则。

### 路径转换 (`onAsPath`)

使用 `SkPath::Circle()` 创建圆形路径，然后通过 `mapToParent()` 应用父级变换矩阵。

### 对象边界框 (`onTransformableObjectBoundingBox`)

返回以圆心为中心、直径为边长的正方形矩形 `SkRect::MakeXYWH(x-r, y-r, 2r, 2r)`。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkPoint`, `SkPathTypes`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGRenderContext`

## 设计模式与设计决策

1. **解析/绘制分离**: `resolve()` 集中处理长度单位转换，绘制和路径转换方法复用该结果。

2. **零半径保护**: `onDraw()` 中检查 `r > 0` 防止绘制退化的零半径圆，符合 SVG 规范。

3. **方向敏感的长度解析**: `cx` 使用水平方向、`cy` 使用垂直方向、`r` 使用"其他"方向解析，正确处理非正方形视口下的百分比单位。

4. **结构化绑定**: `onTransformableObjectBoundingBox` 使用 C++17 结构化绑定 `const auto [pos, r]` 简化代码。

## 性能考量

- `drawCircle` 是 SkCanvas 的基本高效操作，通常有 GPU 加速
- `resolve()` 涉及少量浮点运算，每次绘制调用一次
- `onAsPath()` 需要创建 SkPath 对象，比直接绘制开销稍大

## 相关文件

- `modules/svg/include/SkSVGCircle.h` - 头文件定义
- `modules/svg/include/SkSVGShape.h` - 形状基类
- `modules/svg/src/SkSVGEllipse.cpp` - 相似的椭圆实现
- `modules/svg/include/SkSVGRenderContext.h` - 长度上下文
