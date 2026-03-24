# SkPoint 点与向量实现模块

> 源文件: `include/private/base/SkPoint_impl.h`

## 概述
SkPoint_impl.h 定义了 Skia 中二维点和向量的核心数据结构,包括整数版本 (SkIPoint) 和浮点版本 (SkPoint)。该模块提供了丰富的几何运算、向量操作、距离计算等功能,是 Skia 图形几何计算的基础。

## 架构位置
位于 Skia 基础数学层 (private/base),为所有图形几何运算提供底层数据类型。被路径 (SkPath)、矩形 (SkRect)、变换 (SkMatrix)、渲染管线等模块广泛使用。

## 主要类与结构体

### SkIPoint - 整数点/向量

**职责**: 表示整数坐标的二维点或向量

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | int32_t | x 轴坐标 |
| `fY` | int32_t | y 轴坐标 |

**别名**: `SkIVector` 与 `SkIPoint` 完全等价,可互换使用

### SkPoint - 浮点点/向量

**职责**: 表示浮点坐标的二维点或向量

**继承关系**: 标记为 `SK_API` 导出类

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fX` | float | x 轴坐标 |
| `fY` | float | y 轴坐标 |

**别名**: `SkVector` 与 `SkPoint` 完全等价

## 公共 API 函数

### SkIPoint 方法

#### 构造与访问

##### `Make`
```cpp
static constexpr SkIPoint Make(int32_t x, int32_t y)
```
- **功能**: 静态工厂方法创建 SkIPoint
- **返回**: SkIPoint{x, y}
- **constexpr**: 支持编译期构造

##### `x()` / `y()`
```cpp
constexpr int32_t x() const
constexpr int32_t y() const
```
- **功能**: 获取坐标值
- **constexpr**: 编译期可用

#### 状态查询

##### `isZero`
```cpp
bool isZero() const
```
- **功能**: 检测是否为零点
- **实现**: `(fX | fY) == 0` - 位运算优化
- **返回**: fX 和 fY 都为 0 时返回 true

#### 修改操作

##### `set`
```cpp
void set(int32_t x, int32_t y)
```
设置新坐标值。

#### 运算符

##### 负号运算符
```cpp
SkIPoint operator-() const
```
- **功能**: 返回相反向量
- **返回**: {-fX, -fY}

##### 复合赋值运算符
```cpp
void operator+=(const SkIVector& v)  // 饱和加法
void operator-=(const SkIVector& v)  // 饱和减法
```
- **实现**: 使用 `Sk32_sat_add` / `Sk32_sat_sub`
- **特性**: 防止整数溢出,结果饱和到 int32 范围

##### 比较运算符
```cpp
friend bool operator==(const SkIPoint& a, const SkIPoint& b)
friend bool operator!=(const SkIPoint& a, const SkIPoint& b)
```

##### 算术运算符
```cpp
friend SkIVector operator-(const SkIPoint& a, const SkIPoint& b)
friend SkIPoint operator+(const SkIPoint& a, const SkIVector& b)
```
- 支持点与点的差 (得到向量)
- 支持点与向量的和 (得到点)
- 使用饱和运算防止溢出

#### 相等性检查

##### `equals`
```cpp
bool equals(int32_t x, int32_t y) const
```
检测是否等于指定坐标。

### SkPoint 方法

#### 构造与访问

##### `Make`
```cpp
static constexpr SkPoint Make(float x, float y)
```
静态工厂方法创建 SkPoint。

##### `x()` / `y()`
```cpp
constexpr float x() const
constexpr float y() const
```
获取坐标值。

#### 状态查询

##### `isZero`
```cpp
bool isZero() const
```
- **实现**: `(0 == fX) & (0 == fY)` - 使用位与避免分支
- **返回**: 两坐标都为 0 时返回 true

##### `isFinite`
```cpp
bool isFinite() const
```
- **功能**: 检测坐标是否为有限数 (非 NaN 且非无穷)
- **实现**: 调用 `SkIsFinite(fX, fY)`

#### 设置操作

##### `set`
```cpp
void set(float x, float y)
```
设置新坐标值。

##### `iset` (整数转换版本)
```cpp
void iset(int32_t x, int32_t y)
void iset(const SkIPoint& p)
```
- **功能**: 从整数安全转换到浮点
- **用途**: 避免大整数转浮点的缩窄警告

##### `setAbs`
```cpp
void setAbs(const SkPoint& pt)
```
设置为另一点坐标的绝对值。

#### 批量操作

##### `Offset` (静态方法)
```cpp
static void Offset(SkPoint points[], int count, const SkVector& offset)
static void Offset(SkPoint points[], int count, float dx, float dy)
```
- **功能**: 批量偏移点数组
- **参数**:
  - `points`: 点数组
  - `count`: 数组长度
  - `offset` 或 `dx,dy`: 偏移量

##### `offset` (实例方法)
```cpp
void offset(float dx, float dy)
```
偏移当前点。

#### 向量运算

##### `length`
```cpp
float length() const
```
- **功能**: 计算向量长度 (欧几里得距离)
- **公式**: `√(fX² + fY²)`
- **别名**: `distanceToOrigin()` 完全等价

##### `normalize`
```cpp
bool normalize()
```
- **功能**: 归一化向量,使长度为 1
- **返回**: 成功返回 true,原长度接近 0 返回 false
- **副作用**: 失败时设为 (0, 0)

##### `setNormalize`
```cpp
bool setNormalize(float x, float y)
```
- **功能**: 设为 (x, y) 的归一化版本
- **返回**: 成功返回 true,(x,y) 长度接近 0 返回 false

##### `setLength`
```cpp
bool setLength(float length)
bool setLength(float x, float y, float length)
```
- **功能**: 缩放向量到指定长度
- **返回**: 成功返回 true,原长度接近 0 返回 false

##### `scale`
```cpp
void scale(float scale, SkPoint* dst) const
void scale(float value)
```
- **功能**: 缩放向量
- **参数**: `dst` - 输出位置,可以是 this (原地修改)

##### `negate`
```cpp
void negate()
```
取反向量 (fX = -fX, fY = -fY)。

#### 运算符

##### 负号运算符
```cpp
SkPoint operator-() const
```
返回相反向量。

##### 复合赋值运算符
```cpp
void operator+=(const SkVector& v)
void operator-=(const SkVector& v)
```
向量加减法。

##### 乘法运算符
```cpp
SkPoint operator*(float scale) const
SkPoint& operator*=(float scale)
```
标量乘法。

##### 比较运算符
```cpp
friend bool operator==(const SkPoint& a, const SkPoint& b)
friend bool operator!=(const SkPoint& a, const SkPoint& b)
```

##### 算术运算符
```cpp
friend SkVector operator-(const SkPoint& a, const SkPoint& b)
friend SkPoint operator+(const SkPoint& a, const SkVector& b)
```

#### 静态几何函数

##### `Length`
```cpp
static float Length(float x, float y)
```
- **功能**: 计算 (x, y) 的欧几里得距离
- **公式**: `√(x² + y²)`

##### `Normalize`
```cpp
static float Normalize(SkVector* vec)
```
- **功能**: 归一化向量并返回原长度
- **返回**: 原向量长度,失败返回 0
- **副作用**: `vec` 被归一化,失败时设为 (0, 0)

##### `Distance`
```cpp
static float Distance(const SkPoint& a, const SkPoint& b)
```
- **功能**: 计算两点间距离
- **实现**: `Length(a.fX - b.fX, a.fY - b.fY)`

##### `DotProduct`
```cpp
static float DotProduct(const SkVector& a, const SkVector& b)
```
- **功能**: 计算点积
- **公式**: `a.fX * b.fX + a.fY * b.fY`
- **用途**: 判断角度、投影计算

##### `CrossProduct`
```cpp
static float CrossProduct(const SkVector& a, const SkVector& b)
```
- **功能**: 计算叉积的 z 分量
- **公式**: `a.fX * b.fY - a.fY * b.fX`
- **用途**: 判断方向、计算面积

##### 实例方法版本
```cpp
float dot(const SkVector& vec) const
float cross(const SkVector& vec) const
```
等价于静态版本,语法更简洁。

#### 相等性检查

##### `equals`
```cpp
bool equals(float x, float y) const
```
检测是否等于指定坐标 (精确相等)。

## 内部实现细节

### 饱和运算 (SkIPoint)
```cpp
void operator+=(const SkIVector& v) {
    fX = Sk32_sat_add(fX, v.fX);
    fY = Sk32_sat_add(fY, v.fY);
}
```
- 使用 `Sk32_sat_add` 防止整数溢出
- 结果饱和到 `[INT32_MIN, INT32_MAX]`

### 位运算优化
```cpp
// SkIPoint::isZero
return (fX | fY) == 0;  // 比 (fX == 0 && fY == 0) 更快

// SkPoint::isZero
return (0 == fX) & (0 == fY);  // 使用 & 避免短路求值的分支
```

### 浮点数安全性
```cpp
// 避免除零
bool normalize() {
    float len = length();
    if (len > 0 && SkIsFinite(len)) {
        fX /= len;
        fY /= len;
        return true;
    }
    set(0, 0);
    return false;
}
```

### 向量运算的几何意义

#### 点积 (Dot Product)
```cpp
float dot = a.dot(b);
```
- **几何意义**: `|a| * |b| * cos(θ)`,其中 θ 是夹角
- **应用**:
  - `dot > 0`: 夹角 < 90°
  - `dot == 0`: 垂直
  - `dot < 0`: 夹角 > 90°

#### 叉积 (Cross Product)
```cpp
float cross = a.cross(b);
```
- **几何意义**: 有向面积的两倍,符号表示方向
- **应用**:
  - `cross > 0`: b 在 a 的逆时针方向
  - `cross == 0`: 共线
  - `cross < 0`: b 在 a 的顺时针方向

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAPI.h` | SK_API 导出宏 |
| `SkFloatingPoint.h` | 浮点工具函数 |
| `SkSafe32.h` | 饱和运算函数 |
| `<cmath>` | sqrt 等数学函数 |
| `<cstdint>` | int32_t 类型 |

### 被依赖的模块
- `SkRect` - 矩形定义使用点
- `SkPath` - 路径由点序列构成
- `SkMatrix` - 变换点
- `SkCanvas` - 绘制操作的坐标
- 碰撞检测、几何算法

## 设计模式与设计决策

### POD (Plain Old Data) 结构
```cpp
struct SkIPoint {
    int32_t fX;
    int32_t fY;
    // 无虚函数,无构造函数体
};
```
- 可平凡复制
- 内存布局确定
- 可用于数组和缓冲区

### 静态工厂方法
```cpp
SkPoint p = SkPoint::Make(1.0f, 2.0f);
```
而非构造函数:
- 语义更清晰
- 支持 constexpr
- 便于扩展其他工厂方法

### 别名设计
```cpp
typedef SkPoint SkVector;
typedef SkIPoint SkIVector;
```
- 语义区分: 点表示位置,向量表示方向/偏移
- 实现统一: 避免代码重复
- 类型兼容: 可互换使用

### 饱和运算 (SkIPoint)
整数版本使用饱和运算,浮点版本不需要:
- **整数**: 溢出会导致错误结果
- **浮点**: 溢出得到无穷大,可检测

### 批量操作
```cpp
static void Offset(SkPoint points[], int count, ...)
```
提供数组操作接口提升性能,避免函数调用开销。

## 性能考量

### 内联小函数
所有方法都在头文件中定义,鼓励编译器内联。

### 位运算优化
`isZero` 使用位或/位与避免分支预测失败。

### SIMD 潜力
内存布局适合 SIMD 优化:
```cpp
struct SkPoint4 {
    __m128 xyzw;  // {x1, y1, x2, y2}
};
```

### 避免分支的归一化
```cpp
bool normalize() {
    float len = length();
    // 单次判断,而非多次 if
    if (len > 0 && SkIsFinite(len)) {
        fX /= len;
        fY /= len;
        return true;
    }
    set(0, 0);
    return false;
}
```

### 饱和运算的开销
`Sk32_sat_add` 比普通加法略慢,但换取正确性。

## 使用示例

### 基本点操作
```cpp
SkPoint p1 = SkPoint::Make(10.0f, 20.0f);
SkPoint p2 = SkPoint::Make(30.0f, 40.0f);

SkVector v = p2 - p1;  // {20, 20}
float distance = SkPoint::Distance(p1, p2);  // 28.28...
```

### 向量归一化
```cpp
SkVector v = {3.0f, 4.0f};
if (v.normalize()) {
    // v 现在是 {0.6, 0.8},长度为 1
}
```

### 点积和叉积
```cpp
SkVector a = {1.0f, 0.0f};
SkVector b = {0.0f, 1.0f};

float dot = a.dot(b);      // 0 (垂直)
float cross = a.cross(b);  // 1 (b 在 a 的逆时针 90°)
```

### 批量偏移
```cpp
SkPoint points[100];
// ... 初始化 points ...
SkPoint::Offset(points, 100, 10.0f, 20.0f);
```

### 判断点在线段的哪一侧
```cpp
bool IsLeft(SkPoint p, SkPoint lineStart, SkPoint lineEnd) {
    SkVector v1 = lineEnd - lineStart;
    SkVector v2 = p - lineStart;
    return v1.cross(v2) > 0;
}
```

### 向量投影
```cpp
SkVector ProjectOnto(SkVector v, SkVector onto) {
    float scale = v.dot(onto) / onto.dot(onto);
    return onto * scale;
}
```

### 整数点的饱和运算
```cpp
SkIPoint p = SkIPoint::Make(INT32_MAX - 10, 0);
SkIVector offset = {20, 0};
p += offset;  // p.fX 饱和到 INT32_MAX,而非溢出
```

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkRect.h` | 使用 SkPoint 定义矩形 |
| `SkMatrix.h` | 变换 SkPoint |
| `SkPath.h` | 路径由 SkPoint 序列组成 |
| `SkFloatingPoint.h` | 提供浮点工具 |
| `SkSafe32.h` | 提供饱和运算 |

## 历史与演进
- 文件历史可追溯到 2006 年 (Android Open Source Project)
- SkPoint 和 SkVector 最初是独立类型,后统一为别名
- 添加饱和运算支持整数版本的安全性
- 持续优化几何算法性能
- 提供丰富的静态工具函数
