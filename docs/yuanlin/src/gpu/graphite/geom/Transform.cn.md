# Transform

> 源文件
> - src/gpu/graphite/geom/Transform.h
> - src/gpu/graphite/geom/Transform.cpp

## 概述

`Transform` 类封装了 4x4 变换矩阵 `SkM44` 及其逆矩阵，并提供了渲染相关的便捷查询接口。它将变换矩阵分为多个类型（从恒等变换到透视变换），使得渲染管线能够针对不同类型的变换进行优化。该类是 Skia Graphite 图形后端中几何变换的核心组件，提供了点映射、矩形变换、缩放因子计算等关键功能。

`Transform` 不仅存储变换矩阵和逆矩阵，还缓存了最小/最大缩放因子（针对非透视变换），避免了重复计算。对于透视变换，它提供了逐点计算缩放因子的机制，以支持透视校正插值和精确的抗锯齿半径计算。

## 架构位置

`Transform` 位于 Skia Graphite 渲染架构的几何变换层，在渲染流程中的位置如下：

```
应用层绘制调用
    ↓
SkCanvas / SkM44 变换矩阵
    ↓
Transform（变换封装与分类）← 当前组件
    ↓
Shape（几何表示）
    ↓
Rect / Bounds 计算
    ↓
Device / Renderer（设备坐标渲染）
    ↓
GPU 命令缓冲区
```

`Transform` 桥接了 Skia 公共 API 的变换矩阵和 Graphite 内部的几何处理逻辑。它与 `Shape` 类协同工作，提供几何的正向和逆向变换能力。

## 主要类与结构体

### Transform::Type 枚举

变换类型分类，从简单到复杂排列：

```cpp
enum class Type : unsigned {
    kIdentity,            // 恒等变换，操作可跳过
    kSimpleRectStaysRect, // 正缩放+平移，矩形保持轴对齐
    kRectStaysRect,       // 含镜像/90度旋转，矩形映射为矩形
    kAffine,              // 仿射变换（含斜切/旋转），无透视
    kPerspective,         // 透视变换，需要齐次除法
    kInvalid,             // 不可逆或非有限矩阵
};
```

类型分类使得渲染器可以根据变换复杂度选择最优的代码路径。

### 核心成员变量

```cpp
SkM44 fM;                    // 正向变换矩阵
SkM44 fInvM;                 // 逆变换矩阵 M^-1
Type  fType;                 // 变换类型
float fMinScaleFactor;       // 最小缩放因子（非透视变换）
float fMaxScaleFactor;       // 最大缩放因子（非透视变换）
```

缓存的缩放因子避免了重复的奇异值分解计算，对于非透视变换，缩放因子在整个变换域内是常量。

## 公共 API 函数

### 构造与工厂方法

```cpp
// 从 SkM44 构造（自动计算逆矩阵和类型）
explicit Transform(const SkM44& m);

// 拷贝构造
Transform(const Transform& t) = default;

// 静态工厂
static constexpr Transform Identity();           // 恒等变换
static constexpr Transform Invalid();            // 无效变换
static Transform Translate(float x, float y);    // 平移变换
static Transform Inverse(const Transform& t);    // 求逆变换
```

### 类型与有效性查询

```cpp
Type type() const;                               // 获取变换类型
bool valid() const;                              // 是否有效（可逆）
const SkM44& matrix() const;                     // 获取正向矩阵
const SkM44& inverse() const;                    // 获取逆矩阵
```

### 缩放因子查询

```cpp
// 获取缓存的最大缩放因子（非透视变换）
float maxScaleFactor() const;

// 计算指定点处的 {最小, 最大} 缩放因子
std::pair<float, float> scaleFactors(const SkV2& p) const;

// 计算局部抗锯齿半径（保证变换后至少移动 1 像素）
float localAARadius(const Rect& bounds) const;
```

### 几何变换

```cpp
// 矩形变换（正向/逆向）
Rect mapRect(const Rect& rect) const;
Rect inverseMapRect(const Rect& rect) const;

// 点映射（批量操作）
void mapPoints(const Rect& localRect, SkV4 deviceOut[4]) const;
void mapPoints(const SkV2* localIn, SkV4* deviceOut, int count) const;
void mapPoints(const SkV4* localIn, SkV4* deviceOut, int count) const;
void inverseMapPoints(const SkV4* deviceIn, SkV4* localOut, int count) const;
```

### 变换组合

```cpp
// 平移复合
Transform preTranslate(float x, float y) const;  // this * T(x,y)
Transform postTranslate(float x, float y) const; // T(x,y) * this

// 矩阵乘法
Transform concat(const Transform& t) const;      // this * t
Transform concat(const SkM44& t) const;          // this * t

// 乘以逆矩阵
Transform concatInverse(const Transform& t) const;  // this * t^-1
Transform concatInverse(const SkM44& t) const;      // this * t^-1
```

## 内部实现细节

### 类型推断算法

构造函数 `Transform(const SkM44& m)` 通过分析矩阵结构推断变换类型：

1. **透视检测**：检查第 4 行是否为 `[0, 0, 0, 1]`，否则为 `kPerspective`
2. **正交投影检测**：检查 Z 轴相关元素，非标准 2D 则为 `kAffine`
3. **恒等检测**：完全等于单位矩阵则为 `kIdentity`
4. **对角矩阵**：`m01 == m10 == 0` 且 `m00 > 0 && m11 > 0` 则为 `kSimpleRectStaysRect`
5. **反对角矩阵**：`m00 == m11 == 0` 表示 90/270 度旋转，为 `kRectStaysRect`
6. **一般仿射**：其他情况为 `kAffine`

对于每种类型，都直接计算逆矩阵（避免调用通用求逆函数），并通过奇异值分解或简单的绝对值排序计算缩放因子。

### 逆矩阵计算优化

针对不同变换类型采用定制的逆矩阵计算：

- **恒等变换**：逆矩阵就是自身
- **对角矩阵**：逆矩阵元素为倒数
```cpp
fInvM = SkM44(1/sx, 0, 0, -tx/sx,
              0, 1/sy, 0, -ty/sy,
              0, 0, 1, 0,
              0, 0, 0, 1);
```
- **反对角矩阵**：类似对角矩阵但行列互换
- **一般仿射**：仅求 2x2 子矩阵的逆，然后推导平移分量
- **透视/正交投影**：调用 `SkM44::invert()`

这些优化避免了不必要的完整 4x4 矩阵求逆，显著提升性能。

### 奇异值分解（SVD）计算

对于 2x2 矩阵 `[m00 m01; m10 m11]`，其奇异值（即最小/最大缩放因子）通过以下公式计算：

```cpp
float s1 = m00² + m01² + m10² + m11²  // Frobenius 范数的平方
float e = m00² + m01² - m10² - m11²
float f = m00*m10 + m01*m11
float s2 = sqrt(e² + 4f²)
min_scale = sqrt(0.5 * (s1 - s2))
max_scale = sqrt(0.5 * (s1 + s2))
```

这等价于 `SkMatrix::getMinMaxScales()` 的实现，但针对 Graphite 的需求进行了封装。

### 透视缩放因子计算

对于透视变换，缩放因子随位置变化。`scaleFactors(const SkV2& p)` 计算点 `p` 处的雅可比矩阵：

```
设变换后的 2D 投影点为 p'(u,v) = [f(u,v), g(u,v)]
其中 f = x/w, g = y/w

雅可比矩阵 J = [df/du  df/dv]
                [dg/du  dg/dv]

df/du = (m00 - m30*f) / w
df/dv = (m01 - m31*f) / w
dg/du = (m10 - m30*g) / w
dg/dv = (m11 - m31*g) / w
```

然后对雅可比矩阵进行 SVD 分解得到局部缩放因子。

### 矩形快速映射

`map_rect` 函数针对不同类型优化：

- **kIdentity**：直接返回原矩形
- **kSimpleRectStaysRect**：直接缩放和平移四条边
```cpp
return Rect::FromVals(r * [sx,sy,sx,sy] + [tx,ty,-tx,-ty]);
```
- **kRectStaysRect**：区分对角和反对角矩阵，映射后排序
- **kAffine / kPerspective**：调用 `SkMatrixPriv::MapRect` 进行完整计算

### 局部抗锯齿半径

`localAARadius` 计算局部空间中需要移动多远，才能保证变换后至少移动 1 像素：

```cpp
aaRadius = 1 / min_scale_factor
```

对于透视变换，在边界框的四个角分别计算最小缩放因子，然后取最小值。这确保了边界内任意点的抗锯齿覆盖都足够。

### SIMD 优化的点映射

`mapPoints` 使用 SIMD 向量化批量点变换：

```cpp
auto c0 = skvx::float4::Load(M列0);
auto c1 = skvx::float4::Load(M列1);
auto c3 = skvx::float4::Load(M列3);

for (int i = 0; i < count; ++i) {
    out[i] = c0 * in[i].x + c1 * in[i].y + c3;
}
```

利用矩阵列主序存储和 SIMD 并行加速计算。

## 依赖关系

### 直接依赖

- **SkM44**：Skia 4x4 矩阵类，核心变换表示
- **SkMatrix**：3x3 矩阵，提供兼容性转换
- **Rect**：Graphite 矩形表示，矩形变换的输入输出
- **skvx**：SIMD 向量库，用于高效的批量点变换
- **SkMatrixPriv**：矩阵私有工具，提供特殊变换和访问器
- **SkMatrixInvert**：2x2 矩阵求逆工具

### 被依赖

- **Device**：设备坐标系统，使用 `Transform` 进行坐标转换
- **Renderer**：渲染器，根据 `Transform::type()` 选择优化路径
- **BoundsManager**：边界管理器，使用 `mapRect` 计算变换后的边界
- **Shape**：几何形状，与 `Transform` 协同进行几何查询

## 设计模式与设计决策

### 类型标签优化（Type Tagging）

通过将变换分为 6 种类型，`Transform` 使得下游代码可以针对简单情况进行特化：

```cpp
if (transform.type() <= Transform::Type::kRectStaysRect) {
    // 使用快速路径处理矩形
} else {
    // 使用通用路径处理复杂变换
}
```

这是典型的"按复杂度分层"设计，避免了为简单变换支付透视变换的成本。

### 逆矩阵预计算

`Transform` 在构造时即计算并存储逆矩阵，避免了运行时反复求逆：

- **优势**：逆向变换（如屏幕坐标到局部坐标）成为 O(1) 查询
- **劣势**：内存占用翻倍（两个 `SkM44`）

这是空间换时间的经典策略，适合 Graphite 频繁进行双向变换的场景。

### 缩放因子缓存

对于非透视变换，缩放因子在整个变换域内恒定，因此可以预计算并缓存：

```cpp
if (fType < Type::kPerspective) {
    return {fMinScaleFactor, fMaxScaleFactor};  // O(1)
}
```

透视变换则需要逐点计算，但这是透视变换的固有成本。

### 不可变值类型

`Transform` 设计为不可变对象，所有修改操作（如 `concat`）都返回新的 `Transform` 对象：

```cpp
Transform t2 = t1.concat(other);  // t1 不变
```

这简化了并发和缓存逻辑，避免了意外的状态修改。

### 静态工厂模式

提供 `Identity()` 和 `Translate()` 等静态工厂方法，避免了重复的类型推断开销：

```cpp
static constexpr Transform Identity() {
    return Transform(SkM44(), SkM44(), Type::kIdentity, 1.f, 1.f);
}
```

编译时常量构造进一步优化了性能。

## 性能考量

### 内存占用

```cpp
sizeof(Transform) = 2 * sizeof(SkM44) + sizeof(Type) + 2 * sizeof(float)
                  ≈ 2 * 64 + 4 + 8 = 136 字节
```

虽然较大，但考虑到逆矩阵的频繁使用，预计算是值得的。

### 类型推断开销

构造函数中的类型推断涉及多次浮点比较和条件分支，但这是一次性成本。对于频繁使用的变换（如画布变换栈），应缓存 `Transform` 对象而非重复构造。

### SIMD 批量点映射

`mapPoints` 使用 `skvx::float4` 实现 4 个浮点数的 SIMD 并行运算，理论上可达到 4 倍加速。实际性能取决于：
- 编译器优化（是否生成 SSE/NEON 指令）
- 内存对齐（未对齐访问会降低 SIMD 效率）
- 批量大小（小批量无法摊薄初始化成本）

### 矩形映射优化

`kSimpleRectStaysRect` 和 `kRectStaysRect` 的矩形映射通过 SIMD 向量运算完成，避免了逐点映射和边界重新计算：

```cpp
// 单次 SIMD 操作完成 4 条边的变换
xformed = r * [sx,sy,sx,sy] + [tx,ty,-tx,-ty];
```

相比通用路径，这减少了约 75% 的计算量。

### 透视缩放因子缓存策略

对于透视变换的 `localAARadius` 计算，只在边界框的 4 个角采样缩放因子。这是精度和性能的权衡：
- **更多采样点**：更精确但更慢
- **4 个角采样**：通常足够且成本可控

对于病态透视变换（如接近 w=0 的区域），返回无穷大作为安全值。

### concatInverse 优化

`concatInverse` 避免了显式求逆 `t`：

```cpp
// 计算 this * t^-1，不求 t^-1
// 利用 (t * this^-1)^-1 = this * t^-1
return Inverse(Transform(t * fInvM));
```

这节省了一次矩阵求逆的成本。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkM44.h` | 4x4 矩阵类定义 |
| `include/core/SkMatrix.h` | 3x3 矩阵类定义 |
| `src/gpu/graphite/geom/Rect.h` | Graphite 矩形表示 |
| `src/base/SkVx.h` | SIMD 向量库 |
| `src/core/SkMatrixPriv.h` | 矩阵私有工具函数 |
| `src/core/SkMatrixInvert.h` | 矩阵求逆算法 |
| `src/gpu/graphite/Device.h` | 设备坐标系统，使用 Transform |
| `src/gpu/graphite/Renderer.h` | 渲染器，根据变换类型优化 |
| `src/gpu/graphite/geom/Shape.h` | 几何形状，协同进行变换 |
| `src/gpu/graphite/geom/BoundsManager.h` | 边界管理器 |
