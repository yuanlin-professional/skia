# SkPointPriv

> 源文件
> - src/core/SkPointPriv.h

## 概述

`SkPointPriv` 是 Skia 中 `SkPoint` 的私有扩展工具类，提供了一组内部使用的几何计算和辅助函数。这些函数补充了 `SkPoint` 的公共 API，实现了点到线段/直线的距离计算、向量旋转、矩形顶点生成等高级功能。

该类仅供 Skia 内部使用（位于 `src/core`），不属于公共 API。它包含的函数通常更专业化，或者性能优化程度更高，不适合作为通用接口暴露。

主要功能：
- 点到线/线段的距离计算（带侧向判断）
- 向量旋转（顺时针/逆时针 90°）
- 快速长度设置
- 矩形顶点布局生成

## 架构位置

`SkPointPriv` 位于 Skia 核心内部工具层（`src/core`），是几何计算的辅助模块。

在 Skia 架构中的位置：
```
基础几何层 → SkPoint（公共API） → SkPointPriv（内部扩展） → 路径/渲染
```

使用场景：
- **路径处理**：点到曲线的距离判断
- **碰撞检测**：几何关系计算
- **图形算法**：侧向测试、旋转变换
- **顶点生成**：矩形扇形、三角带布局

## 主要类与结构体

### SkPointPriv

静态工具类，所有成员均为静态函数。

**继承关系**
- 无继承关系（纯静态工具类）

**枚举：Side**

表示点相对于有向直线的位置。

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `kLeft_Side` | -1 | 点在直线左侧 |
| `kOn_Side` | 0 | 点在直线上 |
| `kRight_Side` | 1 | 点在直线右侧 |

## 公共 API 函数

### 有限性和规范化检查

**数组有限性检查**
```cpp
static bool AreFinite(const SkPoint array[], int count);
```
- 检查数组中所有点是否有限（非无穷大、非 NaN）
- 优化：一次性检查 `count * 2` 个浮点数

**标量指针访问**
```cpp
static const SkScalar* AsScalars(const SkPoint& pt);
```
- 将 `SkPoint` 转换为标量数组指针
- 返回 `&pt.fX`，可访问 `[fX, fY]`

**可归一化判断**
```cpp
static bool CanNormalize(SkScalar dx, SkScalar dy);
```
- 判断向量 `(dx, dy)` 是否可归一化
- 条件：有限且非零

### 距离计算

**点到直线的距离平方**
```cpp
static SkScalar DistanceToLineBetweenSqd(const SkPoint& pt,
                                         const SkPoint& a,
                                         const SkPoint& b,
                                         Side* side = nullptr);
```
- 计算点 `pt` 到直线 `AB` 的垂直距离的平方
- 可选返回点在直线的哪一侧（通过 `side` 参数）

**点到直线的距离**
```cpp
static SkScalar DistanceToLineBetween(const SkPoint& pt,
                                      const SkPoint& a,
                                      const SkPoint& b,
                                      Side* side = nullptr);
```
- 返回实际距离（对距离平方开方）

**点到线段的距离平方**
```cpp
static SkScalar DistanceToLineSegmentBetweenSqd(const SkPoint& pt,
                                                const SkPoint& a,
                                                const SkPoint& b);
```
- 计算点 `pt` 到线段 `AB` 的最短距离平方
- 考虑线段端点

**点到线段的距离**
```cpp
static SkScalar DistanceToLineSegmentBetween(const SkPoint& pt,
                                             const SkPoint& a,
                                             const SkPoint& b);
```

**两点间距离平方**
```cpp
static SkScalar DistanceToSqd(const SkPoint& pt, const SkPoint& a);
```
- 计算 `(pt - a)` 的长度平方

### 相等性判断

**容差相等（默认容差）**
```cpp
static bool EqualsWithinTolerance(const SkPoint& p1, const SkPoint& p2);
```
- 使用 `CanNormalize` 判断两点是否"几乎相等"
- 等价于 `!CanNormalize(p1.fX - p2.fX, p1.fY - p2.fY)`

**容差相等（自定义容差）**
```cpp
static bool EqualsWithinTolerance(const SkPoint& pt,
                                  const SkPoint& p,
                                  SkScalar tol);
```
- 判断 `|pt.fX - p.fX| < tol && |pt.fY - p.fY| < tol`

### 向量运算

**长度平方**
```cpp
static SkScalar LengthSqd(const SkPoint& pt);
```
- 计算向量长度的平方：`pt.fX² + pt.fY²`
- 等价于 `SkPoint::DotProduct(pt, pt)`

**取负（整数点）**
```cpp
static void Negate(SkIPoint& pt);
```
- 将整数点坐标取反

**快速长度设置**
```cpp
static bool SetLengthFast(SkPoint* pt, float length);
```
- 快速设置点到原点的距离为 `length`
- 使用 `rsqrt` 优化（如果可用）

### 向量旋转

**逆时针旋转 90°**
```cpp
static void RotateCCW(const SkPoint& src, SkPoint* dst);
static void RotateCCW(SkPoint* pt);  // 原地旋转
```
- 变换：`(x, y) → (-y, x)`

**顺时针旋转 90°**
```cpp
static void RotateCW(const SkPoint& src, SkPoint* dst);
static void RotateCW(SkPoint* pt);  // 原地旋转
```
- 变换：`(x, y) → (y, -x)`

**正交向量**
```cpp
static SkPoint MakeOrthog(const SkPoint& vec, Side side = kLeft_Side);
```
- 生成垂直于 `vec` 的正交向量
- `side = kLeft_Side`：逆时针 90°
- `side = kRight_Side`：顺时针 90°

### 矩形顶点生成

**扇形布局（逆时针）**
```cpp
static void SetRectFan(SkPoint v[], SkScalar l, SkScalar t,
                       SkScalar r, SkScalar b, size_t stride);
```
- 生成矩形的四个顶点：`[(l,t), (l,b), (r,b), (r,t)]`
- `stride`：顶点间的字节间距（支持交错数组）

**三角带布局**
```cpp
static void SetRectTriStrip(SkPoint v[], SkScalar l, SkScalar t,
                            SkScalar r, SkScalar b, size_t stride);
static void SetRectTriStrip(SkPoint v[], const SkRect& rect, size_t stride);
```
- 生成三角带顶点：`[(l,t), (l,b), (r,t), (r,b)]`
- 适用于高效矩形渲染

## 内部实现细节

### 点到直线距离算法（SkPoint.cpp）

**DistanceToLineBetweenSqd 实现**

```cpp
float SkPointPriv::DistanceToLineBetweenSqd(const SkPoint& pt,
                                            const SkPoint& a,
                                            const SkPoint& b,
                                            Side* side) {
    SkVector u = b - a;  // 直线方向向量
    SkVector v = pt - a; // 点到起点的向量

    float uLengthSqd = LengthSqd(u);
    float det = u.cross(v);  // 叉积（有向面积）

    if (side) {
        *side = (Side)sk_float_sgn(det);  // 根据叉积符号判断侧向
    }

    // 距离平方 = det² / |u|²
    float temp = sk_ieee_float_divide(det, uLengthSqd);
    temp *= det;

    // 退化情况：直线长度为 0 或点距离太远导致数值不稳定
    if (!SkIsFinite(temp)) {
        return LengthSqd(v);  // 返回到点 A 的距离平方
    }
    return temp;
}
```

**数学原理**
- 点到直线的距离 = 叉积的绝对值 / 直线长度
- 距离平方 = 叉积平方 / 直线长度平方

### 点到线段距离算法

**DistanceToLineSegmentBetweenSqd 实现**

分三种情况：
1. **点在起点 A 之前**：`uDotV <= 0`
   - 最近点是 `A`
   - 距离 = `|v|²`

2. **点在终点 B 之后**：`uDotV > |u|²`
   - 最近点是 `B`
   - 距离 = `|pt - B|²`

3. **点在线段中间**：其他情况
   - 使用直线距离公式
   - 距离 = `det² / |u|²`

**判断依据**
- 投影长度 = `dot(u, v) / |u|`
- 比较 `dot(u, v)` 与 0 和 `|u|²`，避免开方

### 向量旋转实现

**逆时针 90° 旋转**
```cpp
static void RotateCCW(const SkPoint& src, SkPoint* dst) {
    SkScalar tmp = src.fX;
    dst->fX = src.fY;
    dst->fY = -tmp;
}
```
- 变换矩阵：`[0 -1; 1 0]`
- 使用临时变量支持原地旋转（`src == dst`）

**顺时针 90° 旋转**
```cpp
static void RotateCW(const SkPoint& src, SkPoint* dst) {
    SkScalar tmp = src.fX;
    dst->fX = -src.fY;
    dst->fY = tmp;
}
```
- 变换矩阵：`[0 1; -1 0]`

### 矩形顶点生成实现

**SetRectFan 实现**
```cpp
static void SetRectFan(SkPoint v[], SkScalar l, SkScalar t,
                       SkScalar r, SkScalar b, size_t stride) {
    ((SkPoint*)((intptr_t)v + 0 * stride))->set(l, t);
    ((SkPoint*)((intptr_t)v + 1 * stride))->set(l, b);
    ((SkPoint*)((intptr_t)v + 2 * stride))->set(r, b);
    ((SkPoint*)((intptr_t)v + 3 * stride))->set(r, t);
}
```
- 使用指针偏移处理交错数组
- 顶点顺序：左上 → 左下 → 右下 → 右上（逆时针）

**SetRectTriStrip 实现**
```cpp
// 顶点顺序：左上 → 左下 → 右上 → 右下
((SkPoint*)((intptr_t)v + 0 * stride))->set(l, t);
((SkPoint*)((intptr_t)v + 1 * stride))->set(l, b);
((SkPoint*)((intptr_t)v + 2 * stride))->set(r, t);
((SkPoint*)((intptr_t)v + 3 * stride))->set(r, b);
```
- 形成两个三角形：`(0,1,2)` 和 `(1,3,2)`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPoint` | 点和向量的基础表示 |
| `SkRect` | 矩形参数 |
| `SkFloatingPoint` | 浮点工具（`SkIsFinite`, `sk_ieee_float_divide`） |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径简化和几何计算 |
| `SkStroke` | 描边路径生成 |
| `SkScan` | 扫描转换（碰撞检测） |
| `SkEdge` | 边缘处理 |

## 设计模式与设计决策

### 设计模式

1. **静态工具类**
   - 无状态，所有函数为静态
   - 命名空间式组织

2. **函数重载**
   - 提供平方和开方两个版本
   - 满足不同性能需求

### 设计决策

**为何不在 SkPoint 中**
- **API 限制**：这些函数过于专业化
- **内部优化**：包含实现细节和特殊优化

**为何提供平方距离版本**
- **性能**：避免不必要的平方根计算
- **精度**：比较时不需要实际距离

**为何使用 Side 枚举**
- **语义清晰**：`kLeft_Side` 比 `-1` 更易读
- **类型安全**：避免整数混淆

**为何旋转使用临时变量**
- **支持原地操作**：`RotateCW(&pt, &pt)` 可正确工作
- **避免数据竞争**：先读后写

**为何 stride 使用字节偏移**
- **灵活性**：支持交错顶点数组（position + color + texcoord）
- **兼容性**：与 GPU 顶点缓冲区布局一致

**为何距离函数处理退化情况**
- **健壮性**：零长度线段不会导致除零
- **合理回退**：返回到端点的距离

**为何 SetLengthFast 独立**
- **优化选项**：使用平台特定的快速平方根倒数（rsqrt）
- **精度权衡**：快速但精度略低

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 距离计算（平方） | O(1) | 几次乘法和加法 |
| 距离计算（开方） | O(1) | 额外一次平方根 |
| 向量旋转 | O(1) | 简单赋值 |
| 矩形顶点生成 | O(1) | 固定 4 个顶点 |

### 优化策略

1. **平方距离优先**
   ```cpp
   // 优先使用平方比较
   if (DistanceToSqd(pt, target) < threshold * threshold) {
       // ...
   }
   ```

2. **避免不必要的侧向计算**
   ```cpp
   // 如果不需要侧向信息
   float dist = DistanceToLineBetweenSqd(pt, a, b, nullptr);
   ```

3. **批量有限性检查**
   ```cpp
   // 一次检查整个数组
   if (AreFinite(points, count)) {
       // 处理所有点
   }
   ```

4. **原地旋转**
   ```cpp
   RotateCW(&pt);  // 无临时对象
   ```

### 性能陷阱

- **频繁开方**：距离比较时使用平方版本
- **忽略退化情况**：零长度线段可能返回无穷大
- **不必要的侧向计算**：侧向检测有额外开销

### 使用建议

**距离判断优化**
```cpp
// 错误：不必要的开方
float dist = DistanceToLineSegmentBetween(pt, a, b);
if (dist < 10.0f) { ... }

// 正确：使用平方距离
float distSq = DistanceToLineSegmentBetweenSqd(pt, a, b);
if (distSq < 100.0f) { ... }
```

**旋转链式操作**
```cpp
SkPoint orthogonal = SkPointPriv::MakeOrthog(vec);  // 一次调用
```

**交错数组顶点生成**
```cpp
struct Vertex { SkPoint pos; SkColor color; };
Vertex vertices[4];
SetRectFan(&vertices[0].pos, l, t, r, b, sizeof(Vertex));
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkPoint.h` | 扩展 | 公共点类型 |
| `src/core/SkPoint.cpp` | 实现 | 距离计算实现 |
| `include/core/SkRect.h` | 依赖 | 矩形参数 |
| `src/core/SkPath.cpp` | 使用者 | 路径几何计算 |
| `src/core/SkStroke.cpp` | 使用者 | 描边算法 |
| `src/core/SkScan.cpp` | 使用者 | 扫描转换 |
| `include/private/base/SkFloatingPoint.h` | 依赖 | 浮点工具 |
