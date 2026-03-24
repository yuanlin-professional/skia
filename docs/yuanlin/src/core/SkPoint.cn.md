# SkPoint

> 源文件
> - include/core/SkPoint.h
> - src/core/SkPoint.cpp

## 概述

`SkPoint` 是 Skia 中表示二维空间点或向量的核心数据结构。该模块提供两种类型的点表示：
- **SkPoint**：浮点坐标点（`float` 类型）
- **SkIPoint**：整数坐标点（`int32_t` 类型）

两者都支持完整的二维几何运算，包括向量加减、缩放、归一化、点积、叉积、距离计算等操作。`SkPoint` 也被别名为 `SkVector`，用于明确表示向量语义。

**注意**：`include/core/SkPoint.h` 实际上是一个转发头文件，真正的实现在 `include/private/base/SkPoint_impl.h` 中。

## 架构位置

`SkPoint` 是 Skia 最基础的数学类型之一，位于核心公共 API（`include/core`）中。几乎所有图形操作都依赖它。

在 Skia 架构中的位置：
```
基础数学层 → SkPoint（二维几何） → 路径、变换、裁剪 → 渲染管线
```

应用场景：
- **路径构建**：定义曲线和线段的控制点
- **坐标变换**：矩阵变换的输入输出
- **碰撞检测**：几何关系判断
- **用户交互**：触摸点、鼠标位置

## 主要类与结构体

### SkIPoint

整数坐标点。

**继承关系**
- 无继承关系（POD 结构体）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | `int32_t` | X 坐标 |
| `fY` | `int32_t` | Y 坐标 |

**类型别名**
```cpp
typedef SkIPoint SkIVector;  // 整数向量
```

**特点**
- 算术运算使用饱和运算（`Sk32_sat_add`, `Sk32_sat_sub`）
- 避免整数溢出导致的未定义行为

### SkPoint

浮点坐标点。

**继承关系**
- 无继承关系（POD 结构体）
- 标记为 `SK_API`（公共 API）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | `float` | X 坐标 |
| `fY` | `float` | Y 坐标 |

**类型别名**
```cpp
typedef SkPoint SkVector;  // 二维向量
```

## 公共 API 函数

### SkIPoint

**构造和访问**
```cpp
static constexpr SkIPoint Make(int32_t x, int32_t y);
constexpr int32_t x() const;
constexpr int32_t y() const;
void set(int32_t x, int32_t y);
```

**判断**
```cpp
bool isZero() const;  // 检查是否为 (0, 0)
bool equals(int32_t x, int32_t y) const;
```

**算术运算**
```cpp
SkIPoint operator-() const;  // 取负
void operator+=(const SkIVector& v);  // 加法赋值（饱和）
void operator-=(const SkIVector& v);  // 减法赋值（饱和）
friend SkIVector operator-(const SkIPoint& a, const SkIPoint& b);  // 减法
friend SkIPoint operator+(const SkIPoint& a, const SkIVector& b);   // 加法
```

### SkPoint

**构造和访问**
```cpp
static constexpr SkPoint Make(float x, float y);
constexpr float x() const;
constexpr float y() const;
void set(float x, float y);
void iset(int32_t x, int32_t y);  // 从整数设置
void iset(const SkIPoint& p);      // 从 SkIPoint 设置
void setAbs(const SkPoint& pt);    // 设为绝对值
```

**判断**
```cpp
bool isZero() const;
bool isFinite() const;  // 检查是否为有限值
bool equals(float x, float y) const;
```

**偏移操作**
```cpp
static void Offset(SkPoint points[], int count, const SkVector& offset);
static void Offset(SkPoint points[], int count, float dx, float dy);
void offset(float dx, float dy);
```

**长度和距离**
```cpp
float length() const;                                // 到原点的距离
float distanceToOrigin() const;                      // 同 length()
static float Length(float x, float y);               // 静态版本
static float Distance(const SkPoint& a, const SkPoint& b);  // 两点间距离
```

**归一化**
```cpp
bool normalize();                                    // 归一化为单位向量
bool setNormalize(float x, float y);                 // 从 (x, y) 归一化
static float Normalize(SkVector* vec);               // 静态版本，返回原长度
```

**长度设置**
```cpp
bool setLength(float length);                        // 设置为指定长度
bool setLength(float x, float y, float length);      // 从 (x, y) 设为指定长度
```

**缩放**
```cpp
void scale(float scale, SkPoint* dst) const;  // 缩放到 dst
void scale(float value);                       // 原地缩放
SkPoint operator*(float scale) const;          // 乘法运算符
SkPoint& operator*=(float scale);              // 乘法赋值
```

**取负**
```cpp
void negate();              // 原地取负
SkPoint operator-() const;  // 返回取负副本
```

**算术运算**
```cpp
void operator+=(const SkVector& v);
void operator-=(const SkVector& v);
friend SkVector operator-(const SkPoint& a, const SkPoint& b);
friend SkPoint operator+(const SkPoint& a, const SkVector& b);
```

**点积和叉积**
```cpp
static float DotProduct(const SkVector& a, const SkVector& b);
float dot(const SkVector& vec) const;

static float CrossProduct(const SkVector& a, const SkVector& b);
float cross(const SkVector& vec) const;
```

## 内部实现细节

### 长度计算（`SkPoint.cpp`）

**基础算法**
```cpp
float SkPoint::Length(float dx, float dy) {
    float mag2 = dx * dx + dy * dy;
    if (SkIsFinite(mag2)) {
        return std::sqrt(mag2);
    } else {
        // 溢出回退到双精度
        double xx = dx, yy = dy;
        return sk_double_to_float(sqrt(xx * xx + yy * yy));
    }
}
```

### 归一化算法

使用模板函数 `set_point_length` 处理：
```cpp
template <bool use_rsqrt>
bool set_point_length(SkPoint* pt, float x, float y, float length,
                      float* orig_length = nullptr);
```

**核心步骤**
1. 计算 `(x, y)` 的长度的平方
2. 检查溢出和退化情况
3. 使用双精度计算 `scale = length / sqrt(mag²)`
4. 应用缩放：`pt->set(x * scale, y * scale)`
5. 验证结果有效性

**数值稳定性考虑**
- 使用双精度除法：`sk_ieee_double_divide`
- 检查结果是否有限且非零
- 溢出时切换到双精度路径

### 饱和运算（SkIPoint）

**加法饱和**
```cpp
void operator+=(const SkIVector& v) {
    fX = Sk32_sat_add(fX, v.fX);
    fY = Sk32_sat_add(fY, v.fY);
}
```

**Sk32_sat_add 行为**
- 正常情况：返回 `a + b`
- 上溢出：返回 `INT32_MAX`
- 下溢出：返回 `INT32_MIN`

### 距离计算（SkPointPriv.cpp）

**到线段的距离平方**
```cpp
float SkPointPriv::DistanceToLineSegmentBetweenSqd(
    const SkPoint& pt, const SkPoint& a, const SkPoint& b);
```

**算法逻辑**
1. 计算向量 `u = b - a`（线段方向）
2. 计算向量 `v = pt - a`（点到起点）
3. 计算点积 `uDotV = dot(u, v)`
4. 判断投影位置：
   - `uDotV <= 0`：最近点是 `a`
   - `uDotV > |u|²`：最近点是 `b`
   - 其他：最近点在线段内部，计算垂直距离

**到直线的距离平方**
```cpp
float SkPointPriv::DistanceToLineBetweenSqd(
    const SkPoint& pt, const SkPoint& a, const SkPoint& b, Side* side);
```
- 使用叉积计算垂直距离：`det = cross(u, v)`
- 距离平方 = `det² / |u|²`
- 返回点在直线的哪一侧（`Side` 枚举）

### 零判断优化

**SkIPoint::isZero()**
```cpp
bool isZero() const { return (fX | fY) == 0; }
```
- 使用位或运算，单次比较

**SkPoint::isZero()**
```cpp
bool isZero() const { return (0 == fX) & (0 == fY); }
```
- 使用位与避免短路，确保两个比较都执行

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFloatingPoint` | 浮点工具（`SkIsFinite`, `sk_ieee_double_divide`） |
| `SkSafe32` | 饱和整数运算（`Sk32_sat_add`, `Sk32_sat_sub`） |
| `<cmath>` | 数学函数（`std::sqrt`, `std::abs`） |

### 被依赖的模块

几乎所有 Skia 模块都使用 `SkPoint`，包括：

| 模块 | 用途 |
|------|------|
| `SkPath` | 路径控制点 |
| `SkMatrix` | 变换输入输出 |
| `SkCanvas` | 绘制坐标 |
| `SkRect` | 矩形顶点 |
| `SkRegion` | 区域坐标 |

## 设计模式与设计决策

### 设计模式

1. **POD（Plain Old Data）**
   - 简单结构体，无虚函数
   - 支持高效内存操作和数组处理

2. **类型别名模式**
   - `SkVector` = `SkPoint`
   - `SkIVector` = `SkIPoint`
   - 提高代码语义清晰度

3. **静态工具函数 + 成员函数**
   - `Length()` vs `length()`
   - 灵活适应不同场景

### 设计决策

**为何提供整数和浮点两个版本**
- 整数：用于像素坐标、索引
- 浮点：用于几何计算、插值

**为何 SkIPoint 使用饱和运算**
- 避免整数溢出导致的环绕（wrap-around）
- 确保坐标始终有效

**为何 SkPoint 使用位与判断零**
```cpp
(0 == fX) & (0 == fY)  // 不是 &&
```
- 避免分支预测失败
- 确保两个比较都执行（性能可预测）

**为何提供 iset 函数**
- 避免编译器警告（narrowing conversion）
- 明确整数到浮点转换的意图

**为何归一化可能失败**
- 零向量无法归一化
- 明确失败语义，调用者需检查返回值

**为何叉积返回标量而非向量**
- 二维叉积的 Z 分量是唯一非零值
- 返回标量更简洁（表示有向面积）

**为何使用双精度回退**
- 处理极端值（非常大或非常小的坐标）
- 保证数值稳定性

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 构造、访问 | O(1) | 直接内存访问 |
| 加减乘除 | O(1) | 基本算术运算 |
| `length()` | O(1) | 平方根计算 |
| `normalize()` | O(1) | 包含除法和平方根 |
| `cross()`, `dot()` | O(1) | 几次乘法和加法 |

### 性能优化

1. **内联函数**
   - 简单函数（如访问器）会被编译器内联
   - 无函数调用开销

2. **避免不必要的平方根**
   - 距离比较时使用平方距离

3. **SIMD 潜力**
   - 结构体布局支持 SIMD 指令（SSE、NEON）
   - Skia 内部使用 SIMD 优化批量操作

4. **数值稳定性**
   - 单精度优先，双精度回退
   - 避免频繁使用双精度

### 性能陷阱

- **归一化开销**：包含平方根和除法
- **双精度回退**：极端值时性能降低
- **不必要的长度计算**：能用平方比较就不要开方

### 使用建议

**高频操作优化**
```cpp
// 错误：频繁计算长度
for (auto& pt : points) {
    if (pt.length() < threshold) { ... }
}

// 正确：使用平方长度
float thresholdSq = threshold * threshold;
for (auto& pt : points) {
    if (pt.fX * pt.fX + pt.fY * pt.fY < thresholdSq) { ... }
}
```

**批量偏移**
```cpp
SkPoint::Offset(points, count, dx, dy);  // 批量操作
```

**避免临时对象**
```cpp
pt.scale(2.0f);        // 原地操作
// 优于
pt = pt * 2.0f;        // 创建临时对象
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/private/base/SkPoint_impl.h` | 实现 | 真正的类定义 |
| `src/core/SkPointPriv.h` | 扩展 | 私有辅助函数 |
| `include/core/SkRect.h` | 相关 | 使用 SkPoint 表示顶点 |
| `include/core/SkMatrix.h` | 使用者 | 变换 SkPoint |
| `include/core/SkPath.h` | 使用者 | 路径控制点 |
| `src/core/SkGeometry.h` | 使用者 | 几何计算 |
| `include/private/base/SkFloatingPoint.h` | 依赖 | 浮点工具 |
| `include/private/base/SkSafe32.h` | 依赖 | 饱和整数运算 |
