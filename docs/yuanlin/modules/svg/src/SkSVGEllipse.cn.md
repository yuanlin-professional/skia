# SkSVGEllipse

> 源文件: [modules/svg/src/SkSVGEllipse.cpp](../../../../modules/svg/src/SkSVGEllipse.cpp)

## 概述

`SkSVGEllipse` 实现了 SVG `<ellipse>` 元素，用于绘制椭圆形状。它支持通过 `cx`、`cy`（中心坐标）和 `rx`、`ry`（水平和垂直半径）属性定义椭圆的几何参数，并遵循 SVG 2 规范中关于可选半径自动解析的规则。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGShape
              └── SkSVGEllipse     ← 本文件
```

## 主要类与结构体

### `SkSVGEllipse`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fCx` | `SkSVGLength` | 中心点 X 坐标 |
| `fCy` | `SkSVGLength` | 中心点 Y 坐标 |
| `fRx` | `std::optional<SkSVGLength>` | 水平半径（可选，auto 时从 ry 推导） |
| `fRy` | `std::optional<SkSVGLength>` | 垂直半径（可选，auto 时从 rx 推导） |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析椭圆的四个属性：`cx`、`cy`、`rx`、`ry`。

## 内部实现细节

### 几何解析 (`resolve`)

将 SVG 长度单位转换为绝对像素坐标：
1. 解析中心坐标 `cx`、`cy`
2. 调用 `ResolveOptionalRadii()` 处理可选半径，遵循 SVG 2 规范：
   - 如果两者都是 auto -> 均为 0（方角，不渲染）
   - 如果仅 rx 设定 -> ry = rx
   - 如果仅 ry 设定 -> rx = ry
   - 如果两者都设定 -> 各自独立解析
3. 如果任一半径为 0，返回空矩形（禁止渲染）
4. 否则返回以 (cx, cy) 为中心、(2*rx, 2*ry) 为尺寸的矩形

### 绘制 (`onDraw`)
直接调用 `SkCanvas::drawOval()` 绘制椭圆。

### 路径转换 (`onAsPath`)
将椭圆转换为 `SkPath::Oval()` 并通过 `mapToParent()` 应用父级变换。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkRect`, `SkPathTypes`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGRenderContext`, `SkSVGTypes`
- **内部**: `SkSVGRectPriv.h`（提供 `ResolveOptionalRadii` 函数）

## 设计模式与设计决策

1. **可选半径共享**: `rx` 和 `ry` 使用 `std::optional`，当一个未设置时自动采用另一个的值，与 SVG 2 规范一致。

2. **解析/绘制分离**: `resolve()` 方法集中处理所有长度解析逻辑，`onDraw()` 和 `onAsPath()` 只需使用解析结果。

3. **复用 ResolveOptionalRadii**: 与 `SkSVGRect` 共享半径解析逻辑，通过 `SkSVGRectPriv.h` 头文件提供。

## 性能考量

- `drawOval` 是 SkCanvas 的高效基元操作，通常有硬件加速支持
- 长度解析在每次绘制时重新执行，但计算量极小
- `resolve()` 在 `onDraw()` 和 `onAsPath()` 中分别调用，存在轻微的重复计算

## 相关文件

- `modules/svg/include/SkSVGEllipse.h` - 头文件定义
- `modules/svg/src/SkSVGRectPriv.h` - `ResolveOptionalRadii` 辅助函数声明
- `modules/svg/src/SkSVGRect.cpp` - 共享半径解析逻辑的实现
- `modules/svg/include/SkSVGShape.h` - 形状基类，定义 `onDraw()` 纯虚接口
- `modules/svg/include/SkSVGRenderContext.h` - 长度上下文，负责单位解析
