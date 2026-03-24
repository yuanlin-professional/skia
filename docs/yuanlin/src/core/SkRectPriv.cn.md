# SkRectPriv

> 源文件
> - src/core/SkRectPriv.h

## 概述

`SkRectPriv` 是 Skia 内部使用的矩形工具类,提供了一组高级矩形操作和查询方法,这些方法不属于公共 API,但在 Skia 内部广泛使用。该类主要解决特殊场景下的矩形问题,包括大矩形构造、定点数兼容性检查、矩形差集计算、四边形包含测试以及边缘查找等功能。

## 架构位置

`SkRectPriv` 位于 Skia 核心几何层的私有工具模块:
- **使用者**: SkCanvas, SkDevice, SkPath, SkMatrix, SkImage
- **依赖**: SkRect, SkIRect, SkMatrix, SkM44, SkMathPriv, SkVx
- **层级**: 基础几何私有工具,补充公共 SkRect API

## 主要类与结构体

### SkRectPriv

纯静态工具类,不包含成员变量。

**继承关系**:
```
SkRectPriv (纯静态类,无继承)
```

**方法分类**:
- 特殊矩形构造
- 几何查询和计算
- 定点数兼容性
- 四边形测试
- 边缘查找

## 公共 API 函数

### 特殊矩形构造

```cpp
static SkIRect MakeILarge()
```
创建一个非常大的整数矩形,范围 `[-2^29, -2^29, 2^29, 2^29]`。该值可以安全地与 SkRect 往返转换,且向外取整后仍然非空。

```cpp
static SkIRect MakeILargestInverted()
```
创建最大反向矩形 `[SK_MaxS32, SK_MaxS32, SK_MinS32, SK_MinS32]`,用于初始化需要累积扩展的矩形。

```cpp
static SkRect MakeLargeS32()
```
返回可表示为 int32 的最大浮点矩形 (基于 `MakeILarge()`)。

```cpp
static SkRect MakeLargest()
```
返回浮点数范围的最大矩形 `[SK_ScalarMin, SK_ScalarMin, SK_ScalarMax, SK_ScalarMax]`。

```cpp
static constexpr SkRect MakeLargestInverted()
```
返回最大反向浮点矩形,用于边界累积。

### 几何查询和计算

```cpp
static void GrowToInclude(SkRect* r, const SkPoint& pt)
```
扩展矩形 `r` 以包含点 `pt`。

```cpp
static constexpr float HalfWidth(const SkRect& r)
static constexpr float HalfHeight(const SkRect& r)
```
返回矩形宽度/高度的一半,使用中点计算避免溢出:
```cpp
HalfWidth = sk_float_midpoint(-r.fLeft, r.fRight)
```

### 定点数兼容性

```cpp
static bool FitsInFixed(const SkRect& r)
```
保守检查矩形坐标是否可以表示为 SkFixed (16.16 定点数)。

**SkFixed 范围**: `[-32768, 32767]`

### 矩形差集

```cpp
static bool Subtract(const SkRect& a, const SkRect& b, SkRect* out)
static bool Subtract(const SkIRect& a, const SkIRect& b, SkIRect* out)
```

**功能**: 计算 A - B 的差集。

**返回值**:
- `true`: 差集可表示为单个矩形,存储在 `out`
- `false`: 差集为空或无法表示为单矩形,`out` 包含差集内的最大矩形

**重载版本**:
```cpp
static SkRect Subtract(const SkRect& a, const SkRect& b)
static SkIRect Subtract(const SkIRect& a, const SkIRect& b)
```
返回差集的最大矩形 (不返回是否精确)。

### 四边形包含测试

```cpp
static bool QuadContainsRect(const SkMatrix& m,
                             const SkIRect& a,
                             const SkIRect& b,
                             float tol=0.f)
```

**功能**: 测试矩形 `a` 经过矩阵 `m` 变换后的四边形是否包含矩形 `b`。

**参数**:
- `m`: 2D 变换矩阵
- `a`: 源矩形
- `b`: 目标矩形
- `tol`: 容差 (以 `b` 的坐标空间为单位),相当于将 `b` 内缩 `tol`

```cpp
static bool QuadContainsRect(const SkM44& m, const SkRect& a, const SkRect& b, float tol=0.f)
```

3D 变换版本,支持透视投影。

```cpp
static skvx::int4 QuadContainsRectMask(const SkM44& m, const SkRect& a, const SkRect& b,
                                       float tol=0.f)
```

返回边测试掩码 (上, 右, 下, 左),每个分量为 -1 (通过) 或 0 (失败)。

### 边缘查找

```cpp
static SkIRect ClosestDisjointEdge(const SkIRect& src, const SkIRect& dst)
```

**功能**: 假设 `src` 和 `dst` 不相交,返回 `src` 中最接近 `dst` 的边或角。

**返回**:
- 至少一个维度的宽度或高度为 1 (表示边或角)
- 如果实际相交,返回 `src.intersect(dst)`

**用途**: Clamp 平铺模式下查找采样源边缘。

## 内部实现细节

### MakeILarge 的设计

**为什么是 `1 << 29` 而不是 `SK_MaxS32 >> 1`?**

1. **浮点精度**: `1 << 29` 可以精确表示为 float
2. **舍入安全**: 向外取整 (`roundOut()`) 后仍然在 int32 范围内
3. **对称性**: 正负值对称

### Subtract 实现策略

**可能的情况**:

1. **不相交**: 返回 `a`
2. **完全包含**: 返回空矩形
3. **部分重叠**: 尝试移除一条边

**示例**:
```
A = [0, 0, 100, 100]
B = [0, 0, 50, 100]
Result = [50, 0, 100, 100]  // 移除左边
```

**限制**:
```
A = [0, 0, 100, 100]
B = [25, 25, 75, 75]  // 中间挖空
Result = false  // 无法表示为单个矩形
```

### QuadContainsRect 算法

**核心思想**: 测试 `b` 的四个顶点是否都在 `transform(a)` 的四边形内部。

**半空间测试**:
1. 计算 `transform(a)` 的四条边方程
2. 测试 `b` 的顶点是否在所有半空间的同一侧
3. 容差 `tol` 通过内缩 `b` 实现

**3D 版本差异**:
- 需要透视除法 (投影)
- 处理 w 分量 (齐次坐标)

### ClosestDisjointEdge 逻辑

**距离计算**:
```cpp
int dx = (dst.fLeft > src.fRight) ? dst.fLeft - src.fRight :
         (dst.fRight < src.fLeft) ? src.fLeft - dst.fRight : 0;
int dy = (dst.fTop > src.fBottom) ? dst.fTop - src.fBottom :
         (dst.fBottom < src.fTop) ? src.fTop - dst.fBottom : 0;
```

**边选择**:
- `dx > dy`: 返回垂直边 (宽度=1)
- `dy > dx`: 返回水平边 (高度=1)
- `dx == dy`: 返回角 (宽度=1, 高度=1)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRect | 矩形基础类型 |
| SkIRect | 整数矩形类型 |
| SkMatrix | 2D 变换矩阵 |
| SkM44 | 4x4 变换矩阵 |
| SkMathPriv | 数学工具 (中点计算) |
| SkVx | SIMD 向量运算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkCanvas | 裁剪和边界计算 |
| SkDevice | 设备坐标转换 |
| SkImage | 图像边界处理 |
| SkPath | 路径边界计算 |
| SkMatrix | 变换边界计算 |

## 设计模式与设计决策

### 静态工具类

**设计选择**:
- 纯静态方法,无实例状态
- 避免污染公共 SkRect API
- 方便内部模块调用

### 安全性优先

**MakeILarge 设计**:
- 牺牲范围 (2^29 vs 2^30) 换取浮点精度
- 确保常见操作 (舍入) 不溢出

**FitsInFixed 保守检查**:
- 可能拒绝实际可以表示的值
- 优先避免溢出

### 功能泛化

**Subtract 的两种返回方式**:
- `bool` 版本: 明确指示是否精确
- 直接返回版本: 简化调用,适合不关心精确性的场景

## 性能考量

### 计算复杂度

| 方法 | 复杂度 | 说明 |
|------|--------|------|
| MakeILarge | O(1) | 常量返回 |
| GrowToInclude | O(1) | 4 次比较 |
| HalfWidth/HalfHeight | O(1) | 单次浮点运算 |
| Subtract | O(1) | 常数次边界比较 |
| QuadContainsRect | O(1) | 固定次数 (4个顶点 x 4条边) |
| ClosestDisjointEdge | O(1) | 常数次比较 |

### 优化策略

**constexpr 标记**:
- `MakeLargestInverted`, `HalfWidth`, `HalfHeight` 可编译时计算

**SIMD 加速**:
- `QuadContainsRectMask` 使用 `skvx::int4` 并行计算

**避免分支**:
- `sk_float_midpoint` 使用数学公式避免条件判断

### 浮点精度

**HalfWidth/HalfHeight**:
```cpp
// 避免溢出: (r.fRight - r.fLeft) / 2
// 使用中点: (-r.fLeft + r.fRight) / 2
constexpr float HalfWidth(const SkRect& r) {
    return sk_float_midpoint(-r.fLeft, r.fRight);
}
```

**好处**:
- 处理极大矩形不溢出
- 提高精度 (避免大数相减)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkRect.h | 公共矩形 API |
| src/base/SkMathPriv.h | 数学私有工具 |
| src/base/SkVx.h | SIMD 向量类型 |
| include/core/SkMatrix.h | 2D 变换矩阵 |
| include/core/SkM44.h | 4x4 变换矩阵 |
| include/core/SkPoint.h | 点类型 |
