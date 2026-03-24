# SkRect

> 源文件: include/core/SkRect.h, src/core/SkRect.cpp

## 概述

`SkRect` 和 `SkIRect` 是 Skia 中用于表示矩形区域的核心数据结构。`SkIRect` 使用整数坐标,`SkRect` 使用浮点坐标。两者都以"左-上-右-下"(LTRB)格式存储边界,提供了丰富的构造、查询、变换和运算方法。这些类型在 Skia 的几何计算、边界检测、裁剪操作中无处不在,是图形系统的基础数据类型。

## 架构位置

`SkRect` 和 `SkIRect` 位于 Skia 核心几何层:
- 用于所有需要矩形区域的场景(边界、裁剪、布局)
- 被 Canvas、Path、Image、Surface 等广泛使用
- 提供与 `SkPoint`、`SkSize`、`SkMatrix` 的互操作
- 支持空矩形、反向矩形等特殊状态
- 是 Skia 坐标系统的基础组件

## 主要类与结构体

### SkIRect

**继承关系:** 独立结构体(POD 类型)

**关键成员变量:**

| 成员变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `fLeft` | `int32_t` | 0 | X 轴较小值 |
| `fTop` | `int32_t` | 0 | Y 轴较小值 |
| `fRight` | `int32_t` | 0 | X 轴较大值 |
| `fBottom` | `int32_t` | 0 | Y 轴较大值 |

### SkRect

**继承关系:** 独立结构体(POD 类型)

**关键成员变量:**

| 成员变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `fLeft` | `float` | 0 | X 轴较小值 |
| `fTop` | `float` | 0 | Y 轴较小值 |
| `fRight` | `float` | 0 | X 轴较大值 |
| `fBottom` | `float` | 0 | Y 轴较大值 |

## 公共 API 函数

### 构造方法

#### SkIRect

```cpp
static constexpr SkIRect MakeEmpty()
static constexpr SkIRect MakeWH(int32_t w, int32_t h)
static constexpr SkIRect MakeSize(const SkISize& size)
static constexpr SkIRect MakePtSize(SkIPoint pt, SkISize size)
static constexpr SkIRect MakeLTRB(int32_t l, int32_t t, int32_t r, int32_t b)
static constexpr SkIRect MakeXYWH(int32_t x, int32_t y, int32_t w, int32_t h)
```

**特点:**
- 全部为 `constexpr`,支持编译期构造
- `MakeXYWH` 使用饱和加法 `Sk32_sat_add` 防止溢出

#### SkRect

```cpp
static constexpr SkRect MakeEmpty()
static constexpr SkRect MakeWH(float w, float h)
static SkRect MakeIWH(int w, int h)  // 整数版本
static constexpr SkRect MakeSize(const SkSize& size)
static constexpr SkRect MakeLTRB(float l, float t, float r, float b)
static constexpr SkRect MakeXYWH(float x, float y, float w, float h)
static SkRect Make(const SkISize& size)
static SkRect Make(const SkIRect& irect)  // 从整数矩形转换
```

### 查询方法

#### SkIRect

```cpp
constexpr int32_t left() const
constexpr int32_t top() const
constexpr int32_t right() const
constexpr int32_t bottom() const
constexpr int32_t x() const  // 等同于 left()
constexpr int32_t y() const  // 等同于 top()
constexpr int32_t width() const  // fRight - fLeft
constexpr int32_t height() const  // fBottom - fTop
constexpr int64_t width64() const  // 防溢出版本
constexpr int64_t height64() const  // 防溢出版本
constexpr SkISize size() const
constexpr SkIPoint topLeft() const
bool isEmpty64() const  // fRight <= fLeft || fBottom <= fTop
bool isEmpty() const  // 检查是否为空或溢出
```

**isEmpty 实现:**
```cpp
bool isEmpty() const {
    int64_t w = this->width64();
    int64_t h = this->height64();
    if (w <= 0 || h <= 0) {
        return true;
    }
    return !SkTFitsIn<int32_t>(w | h);  // 检查是否溢出
}
```

#### SkRect

```cpp
constexpr float x() const
constexpr float y() const
constexpr float left() const
constexpr float top() const
constexpr float right() const
constexpr float bottom() const
constexpr float width() const
constexpr float height() const
constexpr float centerX() const  // sk_float_midpoint(fLeft, fRight)
constexpr float centerY() const
constexpr SkPoint center() const
bool isEmpty() const  // !(fLeft < fRight && fTop < fBottom)
bool isSorted() const  // fLeft <= fRight && fTop <= fBottom
bool isFinite() const  // 所有值都是有限的
```

**isEmpty 实现技巧:**
```cpp
bool isEmpty() const {
    // 使用逻辑非,使得 NaN 返回 true
    return !(fLeft < fRight && fTop < fBottom);
}
```

### 修改方法

#### SkIRect

```cpp
void setEmpty()
void setLTRB(int32_t left, int32_t top, int32_t right, int32_t bottom)
void setXYWH(int32_t x, int32_t y, int32_t width, int32_t height)
void setWH(int32_t width, int32_t height)
void setSize(SkISize size)
```

#### SkRect

```cpp
void setEmpty()
void set(const SkIRect& src)  // 从整数矩形设置
void setLTRB(float left, float top, float right, float bottom)
void setXYWH(float x, float y, float width, float height)
void setWH(float width, float height)
void setIWH(int32_t width, int32_t height)
void set(const SkPoint& p0, const SkPoint& p1)  // 两点构造
void setBounds(SkSpan<const SkPoint> pts)
bool setBoundsCheck(SkSpan<const SkPoint> pts)
void setBoundsNoCheck(SkSpan<const SkPoint> pts)
```

### 变换方法

#### SkIRect

```cpp
constexpr SkIRect makeOffset(int32_t dx, int32_t dy) const
constexpr SkIRect makeOffset(SkIVector offset) const
SkIRect makeInset(int32_t dx, int32_t dy) const
SkIRect makeOutset(int32_t dx, int32_t dy) const
void offset(int32_t dx, int32_t dy)
void offset(const SkIPoint& delta)
void offsetTo(int32_t newX, int32_t newY)
void inset(int32_t dx, int32_t dy)
void outset(int32_t dx, int32_t dy)
void adjust(int32_t dL, int32_t dT, int32_t dR, int32_t dB)
```

**使用饱和算术:**
所有变换使用 `Sk32_sat_add` 和 `Sk32_sat_sub` 防止溢出。

#### SkRect

```cpp
constexpr SkRect makeOffset(float dx, float dy) const
constexpr SkRect makeOffset(SkVector v) const
SkRect makeInset(float dx, float dy) const
SkRect makeOutset(float dx, float dy) const
void offset(float dx, float dy)
void offset(const SkPoint& delta)
void offsetTo(float newX, float newY)
void inset(float dx, float dy)
void outset(float dx, float dy)
```

### 几何运算

#### contains

```cpp
// SkIRect
bool contains(int32_t x, int32_t y) const
bool contains(const SkIRect& r) const
bool contains(const SkRect& r) const
bool containsNoEmptyCheck(const SkIRect& r) const

// SkRect
bool contains(float x, float y) const
bool contains(const SkRect& r) const
bool contains(const SkIRect& r) const
```

**语义:** `fLeft <= x < fRight && fTop <= y < fBottom`

#### intersect

```cpp
// SkIRect
bool intersect(const SkIRect& r)
bool intersect(const SkIRect& a, const SkIRect& b)
static bool Intersects(const SkIRect& a, const SkIRect& b)

// SkRect
bool intersect(const SkRect& r)
bool intersect(const SkRect& a, const SkRect& b)
bool intersects(const SkRect& r) const  // 不修改自身
static bool Intersects(const SkRect& a, const SkRect& b)
```

**返回值:** 有交集返回 true 并更新矩形,否则返回 false 且不修改。

#### join

```cpp
// SkIRect
void join(const SkIRect& r)

// SkRect
void join(const SkRect& r)
void joinNonEmptyArg(const SkRect& r)  // 假设 r 非空
void joinPossiblyEmptyRect(const SkRect& r)  // 可能产生错误结果
```

**语义:** 计算并集,扩展矩形以包含 `r`。

### 排序与舍入

#### SkIRect

```cpp
void sort()  // 确保 left <= right, top <= bottom
SkIRect makeSorted() const
```

#### SkRect

```cpp
void sort()
SkRect makeSorted() const
void round(SkIRect* dst) const  // 四舍五入
void roundOut(SkIRect* dst) const  // 向外扩展
void roundOut(SkRect* dst) const  // 浮点版本
void roundIn(SkIRect* dst) const  // 向内收缩
SkIRect round() const
SkIRect roundOut() const
SkIRect roundIn() const
```

### 辅助方法

#### SkRect

```cpp
SkPoint TL() const  // 左上角
SkPoint TR() const  // 右上角
SkPoint BL() const  // 左下角
SkPoint BR() const  // 右下角
std::array<SkPoint, 4> toQuad(SkPathDirection dir = kCW) const
void copyToQuad(SkSpan<SkPoint> pts, SkPathDirection dir = kCW) const
const float* asScalars() const  // 作为数组访问
void dump(bool asHex) const  // 调试输出
SkString dumpToString(bool asHex) const
```

### 静态工具方法

#### SkRect

```cpp
static std::optional<SkRect> Bounds(SkSpan<const SkPoint> pts)
static SkRect BoundsOrEmpty(SkSpan<const SkPoint> pts)
```

**实现:** 使用 SIMD 优化(32 位平台)或标准算法(64 位平台)。

**返回:** `std::optional` 在包含 Inf/NaN 时返回空。

## 内部实现细节

### 饱和算术(Saturating Arithmetic)

`SkIRect` 使用饱和算术防止整数溢出:
```cpp
Sk32_sat_add(x, w)  // x + w,溢出时饱和到 INT32_MAX/MIN
Sk32_sat_sub(x, w)  // x - w,溢出时饱和
```

### 空矩形判断

两种策略:
1. **SkIRect:** 检查 64 位宽高是否 <= 0 或超出 32 位范围
2. **SkRect:** 使用 `!(fLeft < fRight && fTop < fBottom)` 使 NaN 返回 true

### Bounds 计算优化

`SkRect::Bounds` 根据平台选择策略:

**64 位平台:**
```cpp
float L = points[0].fX, R = points[0].fX, ...;
float nx = 0, ny = 0;
for (auto p : points) {
    L = std::fminf(p.fX, L);
    R = std::fmaxf(p.fX, R);
    nx *= p.fX;  // 检测 Inf/NaN
    ny *= p.fY;
}
if (nx == 0 && ny == 0) {
    return {{L, T, R, B}};
}
return {};  // 包含 Inf/NaN
```

**32 位平台:**
使用 `skvx::float4` SIMD 指令并行处理。

### 交集计算宏

```cpp
#define CHECK_INTERSECT(al, at, ar, ab, bl, bt, br, bb) \
    float L = std::max(al, bl);                         \
    float R = std::min(ar, br);                         \
    float T = std::max(at, bt);                         \
    float B = std::min(ab, bb);                         \
    do { if (!(L < R && T < B)) return false; } while (0)
```

使用 `!(L < R && T < B)` 使 NaN 比较返回 false。

### centerX/centerY 实现

```cpp
constexpr float centerX() const {
    return sk_float_midpoint(fLeft, fRight);
}
```

使用特殊的中点计算避免溢出:
```cpp
constexpr float sk_float_midpoint(float a, float b) {
    return (a + b) * 0.5f;  // 简化版
}
```

实际实现更复杂,处理 Inf 等边界情况。

### SkRectPriv 私有工具

`SkRectPriv` 提供额外的内部工具:

#### Subtract

```cpp
bool SkRectPriv::Subtract(const SkRect& a, const SkRect& b, SkRect* out)
```

**功能:** 计算 `a - b`,尽可能返回矩形表示。

**策略:**
- 计算 4 个可能的剩余区域(左、右、上、下)
- 选择面积最大的一个
- 返回是否可以精确表示为单个矩形

#### QuadContainsRect

```cpp
bool SkRectPriv::QuadContainsRect(const SkM44& m,
                                  const SkRect& a,
                                  const SkRect& b,
                                  float tol)
```

**功能:** 判断矩形 `a` 经过变换 `m` 后是否包含矩形 `b`。

**实现:**
1. 计算 `a` 四个角点经过 `m` 变换后的齐次坐标
2. 用叉积计算四条边的齐次直线方程
3. 计算 `b` 四个角点到这些直线的距离
4. 所有距离 >= -tol 则返回 true

#### ClosestDisjointEdge

```cpp
SkIRect SkRectPriv::ClosestDisjointEdge(const SkIRect& src, const SkIRect& dst)
```

**功能:** 返回 `src` 与 `dst` 最接近的边缘。

**用途:** 图像处理中的边缘采样。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkPoint` / `SkSize` | 构造和查询 |
| `SkMatrix` / `SkM44` | 变换计算 |
| `SkTPin` | 夹取工具 |
| `SkSafe32` | 饱和算术 |
| `SkFloatingPoint` | 浮点工具 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkCanvas` | 裁剪和边界 |
| `SkPath` | 边界计算 |
| `SkImage` | 图像边界 |
| `SkSurface` | 表面边界 |
| `SkRegion` | 区域运算 |
| 几乎所有 Skia 模块 | 基础几何类型 |

## 设计模式与设计决策

### 1. 值语义(Value Semantics)
作为 POD 类型,支持高效的拷贝和按值传递。

### 2. 不变性倾向(Immutability Preference)
提供大量 `make*` 方法返回新矩形,避免修改原对象。

### 3. 防御性编程(Defensive Programming)
处理溢出、NaN、Inf 等边界情况。

### 4. 饱和算术(Saturating Arithmetic)
防止整数溢出导致的错误结果。

### 5. constexpr 支持(Compile-Time Evaluation)
尽可能使用 `constexpr` 允许编译期计算。

### 6. 平台优化(Platform-Specific Optimization)
根据平台选择 SIMD 或标准实现。

### 7. 空对象模式(Null Object Pattern)
`MakeEmpty()` 提供标准的空矩形表示。

## 性能考量

### 1. POD 类型
- 无虚函数,无动态分配
- 适合栈分配和寄存器传递
- 编译器可以高度优化

### 2. 饱和算术开销
- 虽然有额外检查,但避免了未定义行为
- 现代 CPU 有高效的饱和指令

### 3. SIMD 优化
- 32 位平台的 Bounds 计算使用 SIMD
- 显著提升大量点的边界计算

### 4. 内联友好
- 大多数方法很小,适合内联
- constexpr 方法可完全优化掉

### 5. 缓存友好
- 紧凑的内存布局(16 或 32 字节)
- 适合数组存储

### 6. NaN 处理
- 使用 `!(a < b)` 模式自然处理 NaN
- 避免显式 isnan 检查

### 7. 早期退出
- `isEmpty()` 检查使后续计算可以跳过

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkPoint.h` | 点和向量 |
| `include/core/SkSize.h` | 尺寸 |
| `include/core/SkMatrix.h` | 2D 变换 |
| `include/core/SkM44.h` | 4x4 变换矩阵 |
| `include/core/SkSpan.h` | 数组视图 |
| `include/private/base/SkSafe32.h` | 饱和算术 |
| `include/private/base/SkFloatingPoint.h` | 浮点工具 |
| `include/private/base/SkTPin.h` | 夹取工具 |
| `src/core/SkRectPriv.h` | 私有工具 |
| `include/core/SkString.h` | 字符串(调试) |
