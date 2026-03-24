# SkM44

> 源文件
> - include/core/SkM44.h
> - src/core/SkM44.cpp

## 概述

`SkM44` 是 Skia 中的 4x4 矩阵类,用于表示三维空间的仿射变换和透视变换。它是 Skia 3D 变换系统的核心,支持平移、缩放、旋转和透视投影等操作。该类与传统的 3x3 SkMatrix 配合使用,为 Skia 提供了完整的 2D 和 3D 变换能力。

`SkM44` 采用列主序(column-major)存储,这与 OpenGL 和现代图形 API 的惯例一致,便于直接传递给 GPU。它还提供了向量类型(SkV2, SkV3, SkV4)用于配合矩阵运算。

## 架构位置

`SkM44` 在 Skia 变换系统中的位置:

```
应用层 (3D API)
    ↓
SkCanvas::concat44() / SkCanvas::setMatrix44()
    ↓
SkM44 (4x4 矩阵变换)
    ↓
GPU 后端 (Uniform 上传)
```

对于 2D 变换,可以与 SkMatrix 互相转换:
```
SkMatrix (3x3) ←→ SkM44 (4x4)
```

## 主要类与结构体

### SkV2

**2D 向量类**

| 成员 | 类型 | 说明 |
|------|------|------|
| x, y | float | 坐标分量 |

**关键方法:** dot, cross, length, normalize

### SkV3

**3D 向量类**

| 成员 | 类型 | 说明 |
|------|------|------|
| x, y, z | float | 坐标分量 |

**关键方法:** dot, cross, length, normalize

### SkV4

**4D 齐次向量类**

| 成员 | 类型 | 说明 |
|------|------|------|
| x, y, z, w | float | 坐标分量 |

**关键方法:** dot, length, normalize, operator[]

### SkM44

**4x4 矩阵类**

**继承关系:**
- 无继承,值类型

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMat[16] | SkScalar | 矩阵元素(列主序存储) |

**存储布局:**
```
列主序内存布局:
fMat[0]  fMat[4]  fMat[8]   fMat[12]     1  0  0  tx
fMat[1]  fMat[5]  fMat[9]   fMat[13]  =  0  1  0  ty
fMat[2]  fMat[6]  fMat[10]  fMat[14]     0  0  1  tz
fMat[3]  fMat[7]  fMat[11]  fMat[15]     0  0  0  1
```

## 公共 API 函数

### 构造函数

```cpp
constexpr SkM44();  // 单位矩阵
SkM44(const SkM44& a, const SkM44& b);  // a * b
explicit SkM44(Uninitialized_Constructor);  // 未初始化
constexpr SkM44(NaN_Constructor);  // NaN 矩阵
constexpr SkM44(SkScalar m0, SkScalar m4, ...);  // 行主序参数
explicit SkM44(const SkMatrix& src);  // 从 3x3 矩阵转换
```

**说明:**
- 默认构造生成单位矩阵
- 参数构造使用行主序(row-major),但内部存储为列主序
- 可以从 SkMatrix 构造(填充第三行和第三列为单位)

### 静态工厂方法

#### Rows / Cols

```cpp
static SkM44 Rows(const SkV4& r0, const SkV4& r1, const SkV4& r2, const SkV4& r3);
static SkM44 Cols(const SkV4& c0, const SkV4& c1, const SkV4& c2, const SkV4& c3);
```

**功能:** 从行向量或列向量构造矩阵。

#### RowMajor / ColMajor

```cpp
static SkM44 RowMajor(const SkScalar r[16]);
static SkM44 ColMajor(const SkScalar c[16]);
```

**功能:** 从数组构造,明确指定存储顺序。

#### Translate / Scale / Rotate

```cpp
static SkM44 Translate(SkScalar x, SkScalar y, SkScalar z = 0);
static SkM44 Scale(SkScalar x, SkScalar y, SkScalar z = 1);
static SkM44 Rotate(SkV3 axis, SkScalar radians);
```

**功能:** 创建基本变换矩阵。

#### LookAt / Perspective

```cpp
static SkM44 LookAt(const SkV3& eye, const SkV3& center, const SkV3& up);
static SkM44 Perspective(float near, float far, float angle);
```

**功能:** 创建视图矩阵和透视投影矩阵(用于 3D 场景)。

#### RectToRect

```cpp
static SkM44 RectToRect(const SkRect& src, const SkRect& dst);
```

**功能:** 创建将 src 矩形缩放并平移到 dst 矩形的矩阵。

### 元素访问

```cpp
SkScalar rc(int r, int c) const;  // 读取 (行, 列)
void setRC(int r, int c, SkScalar value);  // 设置 (行, 列)
SkV4 row(int i) const;  // 读取第 i 行
SkV4 col(int i) const;  // 读取第 i 列
void setRow(int i, const SkV4& v);  // 设置第 i 行
void setCol(int i, const SkV4& v);  // 设置第 i 列
```

### 矩阵运算

#### 矩阵乘法

```cpp
friend SkM44 operator*(const SkM44& a, const SkM44& b);
SkM44& setConcat(const SkM44& a, const SkM44& b);  // this = a * b
SkM44& preConcat(const SkM44& m);   // this = this * m
SkM44& postConcat(const SkM44& m);  // this = m * this
SkM44& preConcat(const SkMatrix& m);  // 与 3x3 矩阵乘法
```

#### 变换操作

```cpp
SkM44& preTranslate(SkScalar x, SkScalar y, SkScalar z = 0);
SkM44& postTranslate(SkScalar x, SkScalar y, SkScalar z = 0);
SkM44& preScale(SkScalar x, SkScalar y);
SkM44& preScale(SkScalar x, SkScalar y, SkScalar z);
```

**说明:**
- preXXX: 在当前变换之后应用(右乘)
- postXXX: 在当前变换之前应用(左乘)

#### 向量变换

```cpp
SkV4 map(float x, float y, float z, float w) const;
SkV4 operator*(const SkV4& v) const;
SkV3 operator*(SkV3 v) const;
```

**说明:** `SkV3` 变换假设 w=0(方向向量)。

#### 逆矩阵和转置

```cpp
[[nodiscard]] bool invert(SkM44* inverse) const;
[[nodiscard]] SkM44 transpose() const;
```

**说明:** `invert()` 如果矩阵不可逆返回 false。

### 与 SkMatrix 互操作

```cpp
SkMatrix asM33() const;  // 转换为 3x3 矩阵(丢弃 Z 行和列)
explicit SkM44(const SkMatrix& src);  // 从 3x3 矩阵构造
```

**转换规则:**
```
[ a b c ]      [ a b 0 c ]
[ d e f ]  ->  [ d e 0 f ]
[ g h i ]      [ 0 0 1 0 ]
               [ g h 0 i ]
```

### 辅助方法

```cpp
void normalizePerspective();  // 归一化透视矩阵
bool isFinite() const;  // 检查是否所有元素有限
void dump() const;  // 调试打印
```

## 内部实现细节

### SIMD 优化

矩阵运算使用 SIMD 向量化:

```cpp
bool SkM44::operator==(const SkM44& other) const {
    auto a0 = skvx::float4::Load(fMat +  0);
    auto a1 = skvx::float4::Load(fMat +  4);
    auto a2 = skvx::float4::Load(fMat +  8);
    auto a3 = skvx::float4::Load(fMat + 12);

    auto b0 = skvx::float4::Load(other.fMat +  0);
    // ...
    auto eq = (a0 == b0) & (a1 == b1) & (a2 == b2) & (a3 == b3);
    return (eq[0] & eq[1] & eq[2] & eq[3]) == ~0;
}
```

**优势:** 一次比较 4 个元素,加速运算。

### 矩阵乘法实现

```cpp
SkM44& SkM44::setConcat(const SkM44& a, const SkM44& b) {
    auto c0 = skvx::float4::Load(a.fMat +  0);
    auto c1 = skvx::float4::Load(a.fMat +  4);
    auto c2 = skvx::float4::Load(a.fMat +  8);
    auto c3 = skvx::float4::Load(a.fMat + 12);

    auto compute = [&](skvx::float4 r) {
        return c0*r[0] + (c1*r[1] + (c2*r[2] + c3*r[3]));
    };

    auto m0 = compute(skvx::float4::Load(b.fMat +  0));
    // ... m1, m2, m3
    m0.store(fMat +  0);
    // ...
}
```

**算法:** 列向量加权组合。

### 旋转矩阵

```cpp
SkM44& SkM44::setRotateUnitSinCos(SkV3 axis, SkScalar sinAngle, SkScalar cosAngle) {
    SkScalar x = axis.x, y = axis.y, z = axis.z;
    SkScalar c = cosAngle, s = sinAngle, t = 1 - c;

    *this = { t*x*x + c,   t*x*y - s*z, t*x*z + s*y, 0,
              t*x*y + s*z, t*y*y + c,   t*y*z - s*x, 0,
              t*x*z - s*y, t*y*z + s*x, t*z*z + c,   0,
              0,           0,           0,           1 };
    return *this;
}
```

**公式:** Rodrigues 旋转公式。

### LookAt 实现

```cpp
SkM44 SkM44::LookAt(const SkV3& eye, const SkV3& center, const SkV3& up) {
    SkV3 f = normalize(center - eye);  // 前向向量
    SkV3 u = normalize(up);             // 上向向量
    SkV3 s = normalize(f.cross(u));     // 右向向量

    SkM44 m(kUninitialized_Constructor);
    if (!SkM44::Cols(v4(s, 0), v4(s.cross(f), 0), v4(-f, 0), v4(eye, 1)).invert(&m)) {
        m.setIdentity();
    }
    return m;
}
```

**逻辑:**
1. 构造相机坐标系(右、上、前向量)
2. 构造变换矩阵
3. 求逆得到视图矩阵

### 透视投影

```cpp
SkM44 SkM44::Perspective(float near, float far, float angle) {
    float denomInv = sk_ieee_float_divide(1, far - near);
    float cot = sk_ieee_float_divide(1, std::tan(angle * 0.5f));

    SkM44 m;
    m.setRC(0, 0, cot);
    m.setRC(1, 1, cot);
    m.setRC(2, 2, (far + near) * denomInv);
    m.setRC(2, 3, 2 * far * near * denomInv);
    m.setRC(3, 2, -1);
    return m;
}
```

**标准透视投影矩阵。**

### 矩阵求逆

```cpp
bool SkM44::invert(SkM44* inverse) const {
    SkScalar tmp[16];
    if (SkInvert4x4Matrix(fMat, tmp) == 0.0f) {
        return false;  // 不可逆
    }
    memcpy(inverse->fMat, tmp, sizeof(tmp));
    return true;
}
```

**使用 Gauss-Jordan 消元法或 Cramer 法则。**

### normalizePerspective 优化

```cpp
void SkM44::normalizePerspective() {
    // 如果底行是 [0, 0, 0, X] (X != 0, X != 1)
    if (fMat[15] != 1 && fMat[15] != 0 &&
        fMat[3] == 0 && fMat[7] == 0 && fMat[11] == 0) {
        double inv = 1.0 / fMat[15];
        (skvx::float4::Load(fMat +  0) * inv).store(fMat +  0);
        // ... 其他列
        fMat[15] = 1.0f;
    }
}
```

**用途:** 将"伪透视"矩阵转换为标准形式,加速判断。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkMatrix | 2D 矩阵互操作 |
| SkRect | 矩形变换 |
| skvx | SIMD 向量运算 |
| SkMatrixInvert | 矩阵求逆 |
| SkMatrixPriv | 矩阵内部工具 |
| SkPathPriv | 路径裁剪常量 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkCanvas | 3D 变换 |
| SkM44Priv | 内部工具 |
| SkMatrixProvider | 统一变换接口 |
| GPU 后端 | Uniform 上传 |

## 设计模式与设计决策

### 值语义设计

`SkM44` 使用值语义,可以自由复制和赋值:
- **优势:** 简单、线程安全
- **成本:** 64 字节(16 个 float)的复制开销

**权衡:** 对于变换矩阵,值语义的简单性优于引用计数的复杂性。

### 列主序存储

选择列主序与 OpenGL 兼容:
```cpp
// 可以直接传递给 OpenGL
glUniformMatrix4fv(location, 1, GL_FALSE, m44.fMat);
```

**但 API 使用行主序参数:**
```cpp
SkM44(m0, m4, m8,  m12,   // 行主序参数
      m1, m5, m9,  m13,
      m2, m6, m10, m14,
      m3, m7, m11, m15);
```

**原因:** 行主序更直观,但内部存储列主序方便 GPU。

### 与 SkMatrix 的互操作性

提供双向转换:
- `SkM44(const SkMatrix&)`: 从 2D 升级到 3D
- `asM33()`: 从 3D 降级到 2D

**设计:** 保持与现有 2D API 的兼容性。

### SIMD 优化

使用 `skvx` 库进行 SIMD 优化:
- **跨平台:** 自动选择 SSE, NEON, WASM SIMD 等
- **类型安全:** 模板库避免汇编代码
- **可维护:** 比手写 intrinsics 更易读

## 性能考量

### SIMD 加速

矩阵运算使用 SIMD:
- 矩阵乘法: 约 4 倍加速
- 向量变换: 单指令处理 4 个分量

### 内联小方法

访问器和简单设置器在头文件中实现:
```cpp
SkScalar rc(int r, int c) const {
    return fMat[c*4 + r];  // 内联
}
```

### 缓存友好布局

fMat 是连续数组,缓存局部性好:
```cpp
SkScalar fMat[16];  // 64 字节,正好一个缓存行(某些架构)
```

### 双精度临时计算

某些计算使用 double 避免精度损失:
```cpp
double inv = 1.0 / fMat[15];  // double 精度
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkMatrix.h | 互操作 | 2D 矩阵 |
| src/base/SkVx.h | 依赖 | SIMD 向量库 |
| src/core/SkMatrixInvert.h | 依赖 | 矩阵求逆 |
| src/core/SkMatrixPriv.h | 相关 | 矩阵内部工具 |
| include/core/SkCanvas.h | 使用者 | Canvas 3D 变换 |
