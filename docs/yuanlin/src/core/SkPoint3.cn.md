# SkPoint3

> 源文件
> - include/core/SkPoint3.h
> - src/core/SkPoint3.cpp

## 概述

`SkPoint3` 是 Skia 中表示三维空间点或向量的核心数据结构。该类提供了三维几何运算的完整支持，包括向量归一化、缩放、点积、叉积、长度计算等操作。

`SkPoint3` 也被类型别名为 `SkVector3` 和 `SkColor3f`，分别用于表示三维向量和三通道颜色（RGB）。这种设计体现了 Skia 对几何和颜色运算的统一处理。

主要特性：
- 轻量级结构体（三个 `SkScalar` 成员）
- 支持数学运算符重载（+, -, *, ==）
- 提供静态工具函数和成员函数两种接口风格
- 处理浮点数精度和特殊值（无穷大、NaN）

## 架构位置

`SkPoint3` 位于 Skia 核心图形库的公共 API（`include/core`）中，是基础数学工具的一部分。

在 Skia 架构中的位置：
```
数学基础层 → SkPoint3（三维几何） → 光照计算、3D变换 → 渲染管线
```

应用场景：
- **光照系统**：法向量、光源方向计算
- **3D 变换**：三维矩阵运算的输入输出
- **颜色处理**：RGB 颜色空间运算

## 主要类与结构体

### SkPoint3

三维点或向量表示。

**继承关系**
- 无继承关系（POD 结构体）
- 标记为 `SK_API`（公共 API）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | `SkScalar` | X 坐标 |
| `fY` | `SkScalar` | Y 坐标 |
| `fZ` | `SkScalar` | Z 坐标 |

**类型别名**
```cpp
typedef SkPoint3 SkVector3;   // 三维向量
typedef SkPoint3 SkColor3f;   // 三通道颜色
```

## 公共 API 函数

### 构造和访问

**静态构造函数**
```cpp
static SkPoint3 Make(SkScalar x, SkScalar y, SkScalar z);
```
- 创建并返回一个 `SkPoint3` 实例

**访问器**
```cpp
SkScalar x() const;  // 获取 X 坐标
SkScalar y() const;  // 获取 Y 坐标
SkScalar z() const;  // 获取 Z 坐标
```

**设置函数**
```cpp
void set(SkScalar x, SkScalar y, SkScalar z);
```
- 一次性设置三个坐标

### 比较运算

```cpp
friend bool operator==(const SkPoint3& a, const SkPoint3& b);
friend bool operator!=(const SkPoint3& a, const SkPoint3& b);
```
- 逐分量精确比较（使用 `==`）

### 长度和归一化

**长度计算**
```cpp
static SkScalar Length(SkScalar x, SkScalar y, SkScalar z);
SkScalar length() const;
```
- 计算欧几里得距离：√(x² + y² + z²)

**归一化**
```cpp
bool normalize();
```
- 将向量归一化为单位长度
- 退化向量（长度接近 0）设为 (0,0,0) 并返回 `false`
- 成功返回 `true`

### 缩放操作

**创建缩放副本**
```cpp
SkPoint3 makeScale(SkScalar scale) const;
```
- 返回缩放后的新点，不修改原点

**原地缩放**
```cpp
void scale(SkScalar value);
```
- 将坐标乘以缩放因子

### 算术运算

**取负**
```cpp
SkPoint3 operator-() const;
```
- 返回坐标取反的新点

**加法和减法**
```cpp
friend SkPoint3 operator+(const SkPoint3& a, const SkPoint3& b);
friend SkPoint3 operator-(const SkPoint3& a, const SkPoint3& b);
void operator+=(const SkPoint3& v);
void operator-=(const SkPoint3& v);
```

**标量乘法**
```cpp
friend SkPoint3 operator*(SkScalar t, SkPoint3 p);
```

### 点积和叉积

**点积**
```cpp
static SkScalar DotProduct(const SkPoint3& a, const SkPoint3& b);
SkScalar dot(const SkPoint3& vec) const;
```
- 计算：`a.x * b.x + a.y * b.y + a.z * b.z`

**叉积**
```cpp
static SkPoint3 CrossProduct(const SkPoint3& a, const SkPoint3& b);
SkPoint3 cross(const SkPoint3& vec) const;
```
- 计算：
  ```
  result.x = a.y * b.z - a.z * b.y
  result.y = a.z * b.x - a.x * b.z
  result.z = a.x * b.y - a.y * b.x
  ```

### 有效性检查

```cpp
bool isFinite() const;
```
- 检查三个分量是否均为有限值（非无穷大、非 NaN）

## 内部实现细节

### 长度计算的数值稳定性

**单精度路径**
```cpp
float magSq = x * x + y * y + z * z;
if (SkIsFinite(magSq)) {
    return std::sqrt(magSq);
}
```
- 优先使用单精度计算，性能更高

**双精度回退**
```cpp
double xx = x, yy = y, zz = z;
return (float)sqrt(xx * xx + yy * yy + zz * zz);
```
- 当单精度溢出时（`magSq` 为无穷大），切换到双精度
- 避免极大值导致的数值错误

### 归一化算法

**退化检测**
```cpp
static inline bool is_length_nearly_zero(float x, float y, float z,
                                         float *lengthSquared) {
    *lengthSquared = get_length_squared(x, y, z);
    return *lengthSquared <= (SK_ScalarNearlyZero * SK_ScalarNearlyZero);
}
```
- 使用平方长度避免平方根计算
- 阈值：`SK_ScalarNearlyZero²`

**归一化步骤**
1. 计算长度的平方 `magSq`
2. 检查是否接近零（退化）
3. 计算倒数缩放因子：`invScale = 1 / sqrt(magSq)`
4. 如果溢出，使用双精度重新计算
5. 应用缩放因子：`fX *= scale`
6. 验证结果是否有限

**双精度精度要求**
```cpp
// sqrtf does not provide enough precision; since sqrt takes a double,
// there's no additional penalty to storing invScale in a double
double invScale;
```
- 使用 `double` 存储缩放因子以保持精度

### 特殊值处理

- **无穷大输入**：归一化失败，返回 (0,0,0)
- **NaN 输入**：归一化失败
- **极大值**：自动切换到双精度计算
- **极小值**：检测为退化向量

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkScalar` | 标量类型（通常为 `float`） |
| `SkFloatingPoint` | 浮点数工具（`SkIsFinite`, `SK_ScalarNearlyZero`） |
| `<cmath>` | 标准数学函数（`std::sqrt`） |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkMatrix44` | 三维变换矩阵 |
| `Sk3DView` | 三维视图变换 |
| `SkShadowUtils` | 阴影投射计算 |
| `SkLights` | 光源和法向量表示 |

## 设计模式与设计决策

### 设计模式

1. **POD（Plain Old Data）设计**
   - 简单结构体，无虚函数，支持直接内存操作
   - 高效拷贝和传递

2. **静态工具函数 + 成员函数双接口**
   - `Length()` vs `length()`
   - `DotProduct()` vs `dot()`
   - 灵活适应不同编程风格

### 设计决策

**为何使用 SkScalar 而非具体类型**
- 支持在不同精度配置下编译（float/double）
- 统一 Skia 内部的标量类型

**为何提供类型别名**
- `SkVector3` 和 `SkColor3f` 提高代码可读性
- 相同数据结构，不同语义

**为何归一化可能失败**
- 零向量无法归一化
- 明确失败语义，避免隐式错误

**为何支持双精度回退**
- 处理极端值场景（见 crbug.com/463920）
- 单精度可能在大值时完全失去精度

**为何点积和叉积都提供静态和成员版本**
- 静态版本：对称性，`DotProduct(a, b)` 更自然
- 成员版本：链式调用，`a.dot(b)` 更简洁

**为何使用 `==` 而非近似比较**
- 提供精确比较语义
- 用户可根据需要实现自定义比较

## 性能考量

### 优化策略

1. **单精度优先**
   - 默认使用 `float` 运算，速度快 2-3 倍
   - 仅在溢出时回退到 `double`

2. **避免不必要的平方根**
   - `is_length_nearly_zero` 使用平方长度比较

3. **内联函数**
   - 访问器函数非常短小，编译器会内联

4. **避免虚函数**
   - POD 结构体，无虚表开销

### 性能陷阱

- **归一化开销**：包含平方根、除法和三次乘法
- **双精度回退**：在极端值场景下性能降低约 3 倍

### 使用建议

- 对于已知单位向量，跳过归一化检查
- 批量处理时，考虑 SIMD 优化（Skia 内部使用）
- 避免频繁构造临时对象，使用原地操作

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkScalar.h` | 依赖 | 标量类型定义 |
| `include/private/base/SkFloatingPoint.h` | 依赖 | 浮点工具函数 |
| `include/core/SkMatrix44.h` | 使用者 | 三维矩阵运算 |
| `modules/skottie/src/Sk3DView.h` | 使用者 | 三维视图 |
| `src/utils/SkShadowUtils.cpp` | 使用者 | 阴影计算 |
| `include/core/SkPoint.h` | 相关 | 二维点结构 |
