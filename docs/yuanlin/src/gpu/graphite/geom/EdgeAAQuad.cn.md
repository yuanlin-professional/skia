# EdgeAAQuad - 带边缘抗锯齿标记的四边形

> 源文件: `src/gpu/graphite/geom/EdgeAAQuad.h`

## 概述

EdgeAAQuad 是 Skia Graphite 渲染后端中用于表示带有逐边抗锯齿（Edge Anti-Aliasing）标记的凸四边形的几何类型。它存储四边形的四个顶点坐标以及每条边是否需要抗锯齿处理的标志位，支持从矩形（SkRect/Rect）和任意四点构建。

该类是 `SkCanvas::drawImageRect` 等带有 `QuadAAFlags` 参数的绘制操作在 Graphite 后端的内部表示。通过 `Flags` 枚举的位掩码机制，调用者可以精确控制四边形的哪些边需要抗锯齿，哪些边可以保持硬边界（例如与相邻瓦片的拼接边）。

## 架构位置

```
Graphite 绘制管线
  -> Geometry (几何容器)
    -> EdgeAAQuad (带边缘AA的四边形)
      -> 顶点数据 + AA 标志
```

EdgeAAQuad 是 Graphite 几何系统中的基本几何类型之一，通过 `Geometry` 联合类型容器被传递到绘制管线中。

## 主要类与结构体

### `EdgeAAQuad`
- **职责**: 存储四边形的四个顶点和边缘抗锯齿标志
- **顶点布局**: 按 "左上(p0)、右上(p1)、右下(p2)、左下(p3)" 排列
- **边的定义**: 左(p0-p3)、上(p1-p0)、右(p2-p1)、下(p3-p2)
- **存储方式**: 使用两个 `skvx::float4` 分别存储 X 和 Y 坐标（SoA 布局）

### `Flags` 枚举
- **类型**: `uint8_t` 位掩码
- 值: `kLeft(0b0001)`, `kTop(0b0010)`, `kRight(0b0100)`, `kBottom(0b1000)`, `kNone(0b0000)`, `kAll(0b1111)`
- 通过 `SK_MAKE_BITMASK_OPS` 宏启用类型安全的位运算

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `EdgeAAQuad(const SkRect&, Flags)` | 从 SkRect 构建轴对齐四边形 |
| `EdgeAAQuad(const Rect&, Flags)` | 从 Graphite Rect 构建轴对齐四边形 |
| `EdgeAAQuad(const SkPoint[4], Flags)` | 从四个顶点构建任意凸四边形 |
| `EdgeAAQuad(float4, float4, Flags)` | 从 SIMD 向量构建 |
| `bounds()` | 计算并返回四边形的 AABB 边界框 |
| `xs()` / `ys()` | 访问四个顶点的 X/Y 坐标向量 |
| `edgeFlags()` | 获取边缘 AA 标志位 |
| `isRect()` | 判断是否为轴对齐矩形 |

## 内部实现细节

### SoA 数据布局
坐标采用 Structure-of-Arrays 布局：`fXs` 存储所有 X 坐标，`fYs` 存储所有 Y 坐标。这种布局便于 SIMD 批量处理，特别是在 `bounds()` 计算中通过 SIMD shuffle 和 min/max 操作高效计算包围盒。

### bounds() 的矩形快速路径
当 `fIsRect` 为 true 时，直接从 `fXs[0], fYs[0]`（左上）和 `fXs[2], fYs[2]`（右下）构建 Rect，无需计算 min/max。对于非矩形情况，将四个点分为两组，分别构建排序后的 Rect 再取并集。

### 默认构造函数已删除
`EdgeAAQuad() = delete` 防止创建未初始化的实例，确保所有实例都具有有效的几何数据和 AA 标志。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/geom/Rect.h` | Graphite SIMD 矩形类型，用于 bounds() 返回值 |
| `src/base/SkVx.h` | SIMD 向量类型 `skvx::float4` |
| `src/base/SkEnumBitMask.h` | 类型安全的枚举位掩码 |
| `include/core/SkPoint.h` | SkPoint 类型 |
| `include/core/SkRect.h` | SkRect 类型 |

## 设计模式与设计决策

1. **SoA 布局选择**: 选择将 X 和 Y 坐标分别存储为 `float4`，而不是使用 AoS（如 `SkPoint[4]`），是为了与 Graphite 的 SIMD 优先架构保持一致，方便后续的向量化计算。

2. **矩形标记优化**: `fIsRect` 标志位允许在已知四边形为轴对齐矩形时使用快速路径，避免不必要的 min/max 计算。

3. **类型安全位掩码**: 使用 `SkEnumBitMask<Flags>` 替代原始整数，提供编译时类型检查，避免将不相关的标志位意外混用。

## 性能考量

1. **SIMD 友好布局**: SoA 布局使得顶点坐标的批量变换和边界计算可以充分利用 SIMD 指令。
2. **矩形快速路径**: 对于常见的轴对齐矩形情况，`bounds()` 避免了 shuffle 和 min/max 操作。
3. **对象大小**: 类的大小为 2 个 `float4`（32 字节）+ 标志位（2 字节），紧凑且缓存友好。

## 相关文件

- `src/gpu/graphite/geom/Geometry.h` - 包含 EdgeAAQuad 的几何容器联合类型
- `src/gpu/graphite/geom/Rect.h` - SIMD 矩形，bounds() 的返回类型
- `src/gpu/graphite/Device.h` - 发起带有 EdgeAAQuad 的绘制调用
- `src/base/SkEnumBitMask.h` - 类型安全位掩码工具
