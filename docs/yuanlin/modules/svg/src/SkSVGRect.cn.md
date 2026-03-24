# SkSVGRect

> 源文件: [modules/svg/src/SkSVGRect.cpp](../../../../modules/svg/src/SkSVGRect.cpp)

## 概述

`SkSVGRect` 实现了 SVG `<rect>` 元素，用于绘制矩形（包括圆角矩形）。它支持通过 `x`、`y`、`width`、`height` 定义矩形位置和尺寸，以及通过可选的 `rx`、`ry` 属性定义圆角半径。该文件还包含了与 `SkSVGEllipse` 共享的 `ResolveOptionalRadii` 辅助函数。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGShape
              └── SkSVGRect         ← 本文件
```

## 主要类与结构体

### `SkSVGRect`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fX` | `SkSVGLength` | 矩形左上角 X 坐标 |
| `fY` | `SkSVGLength` | 矩形左上角 Y 坐标 |
| `fWidth` | `SkSVGLength` | 矩形宽度 |
| `fHeight` | `SkSVGLength` | 矩形高度 |
| `fRx` | `std::optional<SkSVGLength>` | 水平圆角半径（可选） |
| `fRy` | `std::optional<SkSVGLength>` | 垂直圆角半径（可选） |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析矩形的六个属性：`x`、`y`、`width`、`height`、`rx`、`ry`。

## 内部实现细节

### 全局辅助函数 `ResolveOptionalRadii`

实现了 SVG 2 规范中矩形和椭圆的可选半径解析规则：

1. **双 auto 规则**: 如果 rx 和 ry 都未设置（auto），则两者均为 0（方角）
2. **单 auto 规则**:
   - 仅 rx 设定 -> ry 取 rx 的值
   - 仅 ry 设定 -> rx 取 ry 的值
3. **双设定规则**: 各自独立解析百分比（rx 相对于宽度，ry 相对于高度）

解析后返回 `std::tuple<float, float>`。

### 几何解析 (`resolve`)

返回 `SkRRect`（圆角矩形）：
1. 使用 `resolveRect()` 解析基本矩形
2. 使用 `ResolveOptionalRadii()` 解析圆角半径
3. 应用 SVG 2 规范的圆角半径钳位规则：
   - rx 不超过宽度的一半
   - ry 不超过高度的一半
4. 使用 `SkRRect::MakeRectXY()` 创建圆角矩形

### 绘制 (`onDraw`)
调用 `SkCanvas::drawRRect()` 绘制圆角矩形。对于零圆角的情况，`SkRRect` 退化为普通矩形，Skia 内部会优化处理。

### 路径转换 (`onAsPath`)
使用 `SkPath::RRect()` 创建圆角矩形路径并应用父级变换。

### 对象边界框 (`onTransformableObjectBoundingBox`)
返回不含圆角信息的纯矩形边界框。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkRRect`, `SkRect`, `SkPathTypes`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGRenderContext`
- **内部**: `SkSVGRectPriv.h`（`ResolveOptionalRadii` 函数声明）

## 设计模式与设计决策

1. **规范驱动实现**: 代码中多处引用 SVG 2 规范 URL，严格遵循规范定义的半径解析和钳位规则。

2. **共享辅助函数**: `ResolveOptionalRadii` 被 `SkSVGRect` 和 `SkSVGEllipse` 共享，通过 `SkSVGRectPriv.h` 内部头文件导出。

3. **SkRRect 统一表示**: 使用 `SkRRect` 统一表示普通矩形和圆角矩形，利用 Skia 对不同 RRect 类型的内部优化。

4. **可选属性**: `rx` 和 `ry` 使用 `std::optional` 表示，精确区分"未设置"（auto）和"设置为 0"两种语义。

## 性能考量

- `drawRRect` 是 SkCanvas 的高效基元操作，普通矩形和圆角矩形有不同的优化路径
- 圆角半径钳位使用 `std::min`，仅两次浮点比较
- `resolveRect()` 和 `ResolveOptionalRadii()` 均为简单的浮点运算
- `onTransformableObjectBoundingBox` 使用不含圆角的矩形，避免了 RRect 解析开销

## 相关文件

- `modules/svg/include/SkSVGRect.h` - 头文件定义
- `modules/svg/src/SkSVGRectPriv.h` - 内部头文件，`ResolveOptionalRadii` 声明
- `modules/svg/src/SkSVGEllipse.cpp` - 共享 `ResolveOptionalRadii` 的椭圆实现
- `modules/svg/include/SkSVGShape.h` - 形状基类
