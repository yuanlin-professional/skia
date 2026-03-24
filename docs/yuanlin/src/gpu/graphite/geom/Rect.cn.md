# Rect - SIMD 加速矩形

> 源文件: `src/gpu/graphite/geom/Rect.h`

## 概述

Rect 是 Skia Graphite 渲染后端中使用 SIMD 指令优化的矩形类。与 Skia 核心库中的 `SkRect` 不同，Graphite 的 Rect 将内部值存储为 `[left, top, -right, -bottom]` 的取反形式，这种布局使得大量矩形操作（如交集、并集、内缩、外扩）可以通过简单的 SIMD min/max/加减运算完成，无需逐分量处理。

Rect 是 Graphite 几何系统的基础数据类型，几乎所有涉及边界框计算的组件都依赖它。所有公共方法都标记了 `SK_ALWAYS_INLINE` 以确保编译器内联展开。

## 架构位置

```
Graphite 几何系统
  -> Rect (SIMD 矩形基础类型)
    -> BoundsManager (边界查询加速)
    -> Geometry 各类型 (bounds() 返回值)
    -> DrawPass / Device (裁剪和边界计算)
```

Rect 是 Graphite 几何模块的核心基础类型，被几乎所有几何类型和绘制管线组件使用。

## 主要类与结构体

### `Rect`
- **内部表示**: `float4 fVals = [left, top, -right, -bottom]`
- **设计原理**: 右和底的取反使得交集运算变为 `max(a, b)`，并集运算变为 `min(a, b)`，每个操作仅需一条 SIMD 指令

### `Rect::ComplementRect`
- **内部表示**: `float4 fVals = [right, bottom, -left, -top]`
- **用途**: 预计算补矩形，使得 `intersects()` 检测可以通过 `all(a.fVals < comp.fVals)` 完成
- **优化场景**: 当需要对同一矩形进行多次相交检测时（例如 BruteForceBoundsManager 的查询循环）

## 公共 API 函数

### 静态工厂方法
| 函数 | 说明 |
|------|------|
| `LTRB(float4)` | 从标准 LTRB 值创建（自动取反 RB） |
| `XYWH(x, y, w, h)` | 从位置和尺寸创建 |
| `WH(w, h)` | 从尺寸创建（原点为 0,0） |
| `Point(float2)` | 创建零面积的点矩形 |
| `FromVals(float4)` | 从已取反的内部表示创建 |
| `Infinite()` | 创建无穷大矩形（用于交集累积） |
| `InfiniteInverted()` | 创建反向无穷大矩形（用于并集累积） |

### 访问器
| 函数 | 说明 |
|------|------|
| `x()`, `y()`, `left()`, `top()` | 获取左/上坐标（直接读取） |
| `right()`, `bot()` | 获取右/下坐标（取反后返回） |
| `topLeft()`, `botRight()` | 获取角点（float2） |
| `ltrb()` | 获取标准 LTRB 表示（取反 RB） |
| `vals()` | 直接访问内部存储（含取反分量） |
| `size()`, `center()`, `area()` | 几何属性查询 |

### 变换操作（make系列 + 就地版本）
| 函数 | 说明 |
|------|------|
| `makeRoundIn()` / `roundIn()` | 向内取整（ceil） |
| `makeRoundOut()` / `roundOut()` | 向外取整（floor） |
| `makeRound()` / `round()` | 标准四舍五入 |
| `makeInset(float)` / `inset(float)` | 向内收缩 |
| `makeOutset(float)` / `outset(float)` | 向外扩展 |
| `makeOffset(float2)` / `offset(float2)` | 平移 |
| `makeJoin(Rect)` / `join(Rect)` | 并集（取 min） |
| `makeIntersect(Rect)` / `intersect(Rect)` | 交集（取 max） |
| `makeSorted()` / `sort()` | 确保非负宽高 |

### 判断操作
| 函数 | 说明 |
|------|------|
| `isEmptyNegativeOrNaN()` | 判断矩形是否为空/负/NaN |
| `intersects(ComplementRect)` | 使用补矩形快速判断相交 |
| `contains(Rect)` | 判断是否完全包含另一矩形 |
| `nearlyEquals(Rect, epsilon)` | 近似相等比较 |

## 内部实现细节

### 取反存储的数学基础
将 `right` 和 `bottom` 取反存储后：
- **交集**: `max([l1,t1,-r1,-b1], [l2,t2,-r2,-b2])` = `[max(l),max(t),-min(r),-min(b)]`，正确
- **并集**: `min([l1,t1,-r1,-b1], [l2,t2,-r2,-b2])` = `[min(l),min(t),-max(r),-max(b)]`，正确
- **内缩**: 加上一个标量即可：`[l+d, t+d, -(r-d), -(b-d)]`
- **空判断**: `!(topLeft + (-botRight) < 0)` 等价于 `width <= 0 || height <= 0`

### NegateBotRight 位操作
```cpp
static float4 NegateBotRight(float4 vals) {
    return sk_bit_cast<float4>(sk_bit_cast<uint4>(vals) ^ uint4(0, 0, 1u << 31, 1u << 31));
}
```
通过 XOR 翻转第三和第四个 float 的符号位实现取反，避免了浮点乘法或减法。

### isEmptyNegativeOrNaN 的 NaN 检测
使用 `!all(fVals.xy() + fVals.zw() < 0)` 而非 `any(... >= 0)`，因为 NaN 参与的比较总是返回 false，`!(<0)` 可以正确检测 NaN 情况。

### asSkRect 和 asSkIRect
通过 SIMD store 操作直接将内部表示（取反还原后）写入 SkRect/SkIRect 的内存，避免逐字段赋值。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/base/SkVx.h` | SIMD 向量类型和操作 |
| `include/core/SkRect.h` | 与 SkRect 互转 |
| `include/core/SkScalar.h` | SK_FloatNegativeInfinity 等常量 |
| `include/private/base/SkAttributes.h` | SK_ALWAYS_INLINE 宏 |
| `include/private/base/SkFloatingPoint.h` | 浮点数工具 |
| `src/base/SkUtils.h` | sk_bit_cast 位转换 |

## 设计模式与设计决策

1. **性能优先设计**: 所有方法标记 `SK_ALWAYS_INLINE`，确保编译器不会产生函数调用开销。取反存储是整个类的核心设计决策，将多种操作统一为 SIMD min/max。

2. **不可变 vs 可变 API**: 提供 `makeXxx()` 和 `xxx()` 两套接口，前者返回新 Rect 不修改原对象，后者就地修改。

3. **显式空矩形处理**: 类不自动处理空/负矩形，将检查责任交给调用者。这避免了每次操作的额外分支判断。

4. **ComplementRect 预计算模式**: 将相交检测分为"准备"和"检测"两步，当需要重复使用同一矩形进行多次检测时，预计算可显著减少重复运算。

## 性能考量

1. **单指令操作**: 交集、并集、内缩、外扩等操作均可通过一条 SIMD 指令（min/max/add）完成。
2. **零分支**: 大多数操作不包含条件分支，对 CPU 流水线友好。
3. **16 字节对齐**: float4 类型的 Rect 自然 16 字节对齐，满足 SIMD 指令的对齐要求。
4. **NaN 传播**: 空矩形操作虽然行为定义明确，但结果可能不符合直觉，调用者需要显式检查。

## 相关文件

- `src/gpu/graphite/geom/BoundsManager.h` - 大量使用 Rect 进行空间查询
- `src/gpu/graphite/geom/Geometry.h` - 所有几何类型的 bounds() 返回 Rect
- `src/gpu/graphite/geom/EdgeAAQuad.h` - EdgeAAQuad 的 bounds() 返回 Rect
- `src/gpu/graphite/geom/CoverageMaskShape.h` - CoverageMaskShape 的 bounds() 返回 Rect
- `src/base/SkVx.h` - 底层 SIMD 向量库
