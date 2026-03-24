# SkColorMatrix

> 源文件: include/effects/SkColorMatrix.h, src/effects/SkColorMatrix.cpp

## 概述

SkColorMatrix 是 Skia 中用于表示和操作 5x4 颜色变换矩阵的核心类。该模块提供了一套完整的矩阵运算接口,包括恒等矩阵、缩放、平移、饱和度调整、矩阵级联等操作,并支持 RGB 与 YUV 色彩空间之间的转换矩阵生成。颜色矩阵通过线性变换实现丰富的颜色调整效果,是 SkColorFilter 和图像处理效果的数学基础。

## 架构位置

SkColorMatrix 位于 Skia 的效果层颜色处理子系统:

```
include/effects/
  └── SkColorMatrix.h          # 颜色矩阵类（本模块）
src/effects/
  └── SkColorMatrix.cpp        # 实现文件（本模块）
src/core/
  └── SkYUVMath.h/cpp           # YUV 转换数学
```

该模块为颜色滤镜和图像效果提供底层数学支持。

## 主要类与结构体

### SkColorMatrix 类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkColorMatrix` | 无 | `array<float, 20> fMat` | 5x4 矩阵,行主序存储 |

#### 矩阵布局

```
[ m00  m01  m02  m03  m04 ]   [ R ]
[ m10  m11  m12  m13  m14 ] * [ G ]
[ m20  m21  m22  m23  m24 ]   [ B ]
[ m30  m31  m32  m33  m34 ]   [ A ]
                               [ 1 ]

输出: R' = m00*R + m01*G + m02*B + m03*A + m04
      G' = m10*R + m11*G + m12*B + m13*A + m14
      B' = m20*R + m21*G + m22*B + m23*A + m24
      A' = m30*R + m31*G + m32*B + m33*A + m34
```

## 公共 API 函数

### 构造函数

```cpp
// 默认构造: 恒等矩阵
constexpr SkColorMatrix();

// 完全指定构造
constexpr SkColorMatrix(float m00, float m01, ..., float m34);
```

### 静态工厂方法

```cpp
// 创建 RGB 到 YUV 转换矩阵
static SkColorMatrix RGBtoYUV(SkYUVColorSpace);

// 创建 YUV 到 RGB 转换矩阵
static SkColorMatrix YUVtoRGB(SkYUVColorSpace);
```

### 矩阵操作

```cpp
// 设置为恒等矩阵
void setIdentity();

// 设置缩放矩阵
void setScale(float rScale, float gScale, float bScale, float aScale = 1.0f);

// 后置平移（加法偏移）
void postTranslate(float dr, float dg, float db, float da);

// 矩阵级联
void setConcat(const SkColorMatrix& a, const SkColorMatrix& b);
void preConcat(const SkColorMatrix& mat);  // this = this * mat
void postConcat(const SkColorMatrix& mat); // this = mat * this

// 设置饱和度矩阵
void setSaturation(float sat);

// 行主序数据访问
void setRowMajor(const float src[20]);
void getRowMajor(float dst[20]) const;
```

## 内部实现细节

### 矩阵索引常量

```cpp
enum {
    kR_Scale = 0,   // fMat[0]  - R 缩放系数
    kG_Scale = 6,   // fMat[6]  - G 缩放系数
    kB_Scale = 12,  // fMat[12] - B 缩放系数
    kA_Scale = 18,  // fMat[18] - A 缩放系数

    kR_Trans = 4,   // fMat[4]  - R 平移
    kG_Trans = 9,   // fMat[9]  - G 平移
    kB_Trans = 14,  // fMat[14] - B 平移
    kA_Trans = 19,  // fMat[19] - A 平移
};
```

### 矩阵级联算法

**set_concat 实现**:
```cpp
static void set_concat(float result[20], const float outer[20],
                       const float inner[20]) {
    float tmp[20];
    float* target;

    // 防止原地操作破坏输入
    if (outer == result || inner == result) {
        target = tmp;
    } else {
        target = result;
    }

    int index = 0;
    for (int j = 0; j < 20; j += 5) {  // 遍历外矩阵的行
        for (int i = 0; i < 4; i++) {  // 遍历前 4 列
            target[index++] = outer[j+0] * inner[i+ 0] +
                              outer[j+1] * inner[i+ 5] +
                              outer[j+2] * inner[i+10] +
                              outer[j+3] * inner[i+15];
        }
        // 第 5 列（平移）
        target[index++] = outer[j+0] * inner[4] +
                          outer[j+1] * inner[9] +
                          outer[j+2] * inner[14] +
                          outer[j+3] * inner[19] +
                          outer[j+4];
    }

    if (target != result) {
        std::copy_n(target, 20, result);
    }
}
```

### 恒等矩阵实现

```cpp
void SkColorMatrix::setIdentity() {
    fMat.fill(0.0f);
    fMat[kR_Scale] = fMat[kG_Scale] = fMat[kB_Scale] = fMat[kA_Scale] = 1;
}
```

结果:
```
[ 1  0  0  0  0 ]
[ 0  1  0  0  0 ]
[ 0  0  1  0  0 ]
[ 0  0  0  1  0 ]
```

### 缩放矩阵实现

```cpp
void SkColorMatrix::setScale(float rScale, float gScale,
                              float bScale, float aScale) {
    fMat.fill(0.0f);
    fMat[kR_Scale] = rScale;
    fMat[kG_Scale] = gScale;
    fMat[kB_Scale] = bScale;
    fMat[kA_Scale] = aScale;
}
```

### 后置平移实现

```cpp
void SkColorMatrix::postTranslate(float dr, float dg, float db, float da) {
    fMat[kR_Trans] += dr;
    fMat[kG_Trans] += dg;
    fMat[kB_Trans] += db;
    fMat[kA_Trans] += da;
}
```

### 饱和度矩阵

**setSaturation 实现**:
```cpp
void SkColorMatrix::setSaturation(float sat) {
    fMat.fill(0.0f);

    const float R = kHueR * (1 - sat);  // 0.213 * (1-sat)
    const float G = kHueG * (1 - sat);  // 0.715 * (1-sat)
    const float B = kHueB * (1 - sat);  // 0.072 * (1-sat)

    setrow(fMat.data() +  0, R + sat, G, B);
    setrow(fMat.data() +  5, R, G + sat, B);
    setrow(fMat.data() + 10, R, G, B + sat);
    fMat[kA_Scale] = 1;
}
```

饱和度常量:
```cpp
static const float kHueR = 0.213f;  // 红色亮度权重
static const float kHueG = 0.715f;  // 绿色亮度权重
static const float kHueB = 0.072f;  // 蓝色亮度权重
```

饱和度效果:
- `sat = 0`: 完全去色（灰度）
- `sat = 1`: 原始颜色
- `sat > 1`: 增强饱和度

### YUV 转换矩阵

**RGBtoYUV**:
```cpp
SkColorMatrix SkColorMatrix::RGBtoYUV(SkYUVColorSpace cs) {
    SkColorMatrix m;
    SkColorMatrix_RGB2YUV(cs, m.fMat.data());
    return m;
}
```

委托给 `src/core/SkYUVMath.cpp` 中的预编译矩阵表。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型定义 |
| `src/core/SkYUVMath.h` | YUV 转换数学 |
| `<array>` | STL 数组容器 |
| `<algorithm>` | std::copy_n |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `include/core/SkColorFilter.h` | 创建颜色矩阵滤镜 |
| `src/effects/SkColorMatrixFilter.cpp` | 光照效果实现 |
| GPU 着色器 | 硬件加速颜色变换 |

## 设计模式与设计决策

### 不可变性与链式操作

**决策**: 提供独立的设置方法和级联方法

```cpp
// 设置方法（替换内容）
matrix.setIdentity();
matrix.setScale(2, 2, 2);

// 级联方法（组合变换）
SkColorMatrix saturation;
saturation.setSaturation(0.5f);
matrix.postConcat(saturation);
```

**优点**: 灵活组合多个变换

### 行主序存储

**决策**: 使用行主序（Row-Major Order）

```cpp
fMat[0..4]   - 第 0 行 (R')
fMat[5..9]   - 第 1 行 (G')
fMat[10..14] - 第 2 行 (B')
fMat[15..19] - 第 3 行 (A')
```

**原因**:
- 符合数学习惯
- 便于按行访问（缓存友好）
- 与 GPU uniform 布局兼容

### 原地操作保护

**set_concat 临时缓冲区**:
```cpp
if (outer == result || inner == result) {
    target = tmp;  // 使用临时缓冲区
} else {
    target = result;  // 直接写入结果
}
```

支持: `matrix.setConcat(matrix, other)` 这样的原地级联

## 性能考量

### constexpr 构造

```cpp
constexpr SkColorMatrix() : SkColorMatrix(1, 0, 0, 0, 0,
                                          0, 1, 0, 0, 0,
                                          0, 0, 1, 0, 0,
                                          0, 0, 0, 1, 0) {}
```

优点: 编译时常量,无运行时开销

### 缓存友好布局

**连续内存**:
```cpp
std::array<float, 20> fMat;
```

优点:
- 单次内存分配
- 顺序访问效率高
- 易于传递给 GPU

### 矩阵级联优化

**展开循环**:
```cpp
for (int j = 0; j < 20; j += 5) {
    for (int i = 0; i < 4; i++) {
        target[index++] = ...;  // 展开为 4 次乘加
    }
}
```

编译器可以向量化为 SIMD 指令

### 饱和度计算

**预计算常量**:
```cpp
const float R = kHueR * (1 - sat);
```

避免重复计算 `(1 - sat)`

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColorFilter.h` | 使用者 | 颜色滤镜接口 |
| `src/core/SkYUVMath.h` | 依赖 | YUV 转换函数 |
| `src/effects/SkColorMatrixFilter.cpp` | 使用者 | 光照效果 |
| `src/gpu/ganesh/effects/` | 使用者 | GPU 着色器 |
