# SkGeometry

> 源文件：src/core/SkGeometry.h, src/core/SkGeometry.cpp

## 概述

SkGeometry 是 Skia 图形库中的核心几何计算模块,提供二次贝塞尔曲线(Quadratic Bezier)、三次贝塞尔曲线(Cubic Bezier)和圆锥曲线(Conic)的数学运算。该模块实现了曲线细分(chopping)、极值计算、曲率分析、拐点检测等高级几何算法,是 Skia 路径渲染和矢量图形的数学基础。

## 架构位置

```
Skia 图形库
└── src/core (核心模块)
    ├── 几何计算
    │   ├── SkGeometry (曲线几何算法)
    │   ├── SkPath (路径表示)
    │   ├── SkScan (扫描转换)
    │   └── SkEdge (边缘处理)
    └── 数学基础
        ├── SkBezierCurves
        ├── SkCubics
        └── SkVx (SIMD 向量运算)
```

该模块是路径渲染管道的核心,为扫描转换器提供单调曲线。

## 主要类与结构体

### SkConic (圆锥曲线)

**继承关系**
- 无继承,值类型结构体

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPts | SkPoint[3] | 控制点数组(P0, P1, P2) |
| fW | SkScalar | 权重(weight),决定曲线类型 |

**权重值的含义**

| 权重范围 | 曲线类型 |
|---------|---------|
| w = 0 | 直线段 |
| 0 < w < 1 | 椭圆弧 |
| w = 1 | 抛物线(等价于二次贝塞尔) |
| w > 1 | 双曲线弧 |

### SkQuadCoeff (二次贝塞尔系数)

**用途**: 存储二次曲线的多项式系数

**数学形式**: P(t) = A*t² + B*t + C

| 成员 | 类型 | 说明 |
|------|------|------|
| fA | skvx::float2 | 二次项系数 |
| fB | skvx::float2 | 一次项系数 |
| fC | skvx::float2 | 常数项 |

### SkCubicCoeff (三次贝塞尔系数)

**数学形式**: P(t) = A*t³ + B*t² + C*t + D

| 成员 | 类型 | 说明 |
|------|------|------|
| fA | skvx::float2 | 三次项系数 |
| fB | skvx::float2 | 二次项系数 |
| fC | skvx::float2 | 一次项系数 |
| fD | skvx::float2 | 常数项 |

### SkCubicType (三次曲线分类)

**枚举值**

| 类型 | 说明 | 特征 |
|------|------|------|
| kSerpentine | 蛇形曲线 | 两个拐点 |
| kLoop | 环形曲线 | 有自交点 |
| kLocalCusp | 局部尖点 | 尖点在有限参数 |
| kCuspAtInfinity | 无穷尖点 | 尖点在无穷远 |
| kQuadratic | 退化为二次 | 实际是二次曲线 |
| kLineOrPoint | 退化为线/点 | 更严重退化 |

## 公共 API 函数

### 二次贝塞尔曲线 API

#### 求值函数

```cpp
SkPoint SkEvalQuadAt(const SkPoint src[3], SkScalar t)
SkPoint SkEvalQuadTangentAt(const SkPoint src[3], SkScalar t)
void SkEvalQuadAt(const SkPoint src[3], SkScalar t,
                  SkPoint* pt, SkVector* tangent = nullptr)
```

计算曲线上 t 参数处的位置和切线。

**参数**
- src: 3 个控制点
- t: 参数值,范围 [0, 1]
- pt: 输出位置(可选)
- tangent: 输出切线方向(可选)

#### 细分函数

```cpp
void SkChopQuadAt(const SkPoint src[3], SkPoint dst[5], SkScalar t)
void SkChopQuadAtHalf(const SkPoint src[3], SkPoint dst[5])
void SkChopQuadAtMidTangent(const SkPoint src[3], SkPoint dst[5])
```

在指定参数处切割曲线为两段。

**输出布局**: dst[0..2] 为第一段,dst[2..4] 为第二段,共享中间点。

#### 极值处理

```cpp
int SkFindQuadExtrema(SkScalar a, SkScalar b, SkScalar c,
                      SkScalar tValues[1])
int SkChopQuadAtYExtrema(const SkPoint src[3], SkPoint dst[5])
int SkChopQuadAtXExtrema(const SkPoint src[3], SkPoint dst[5])
```

查找并在极值处细分,产生单调曲线。

**返回值**
- 0: 无需细分,已单调
- 1: 细分为两段

#### 曲率分析

```cpp
SkScalar SkFindQuadMaxCurvature(const SkPoint src[3])
int SkChopQuadAtMaxCurvature(const SkPoint src[3], SkPoint dst[5])
```

查找最大曲率点,用于曲线质量优化。

#### 格式转换

```cpp
void SkConvertQuadToCubic(const SkPoint src[3], SkPoint dst[4])
```

将二次曲线提升为等价的三次曲线。

### 三次贝塞尔曲线 API

#### 求值函数

```cpp
void SkEvalCubicAt(const SkPoint src[4], SkScalar t,
                   SkPoint* loc, SkVector* tangent, SkVector* curvature)
```

计算位置、切线和曲率(二阶导数)。

#### 细分函数

```cpp
void SkChopCubicAt(const SkPoint src[4], SkPoint dst[7], SkScalar t)
void SkChopCubicAt(const SkPoint src[4], SkPoint dst[10], float t0, float t1)
void SkChopCubicAt(const SkPoint src[4], SkPoint dst[],
                   const SkScalar t[], int count)
```

单点、双点或多点细分。

**优化**: 使用 SIMD 加速并行处理两个细分点。

#### 旋转分析

```cpp
float SkMeasureNonInflectCubicRotation(const SkPoint[4])
float SkFindCubicMidTangent(const SkPoint src[4])
void SkChopCubicAtMidTangent(const SkPoint src[4], SkPoint dst[7])
```

测量曲线旋转角度,用于细分决策。

#### 极值和拐点

```cpp
int SkFindCubicExtrema(SkScalar a, SkScalar b, SkScalar c, SkScalar d,
                       SkScalar tValues[2])
int SkChopCubicAtYExtrema(const SkPoint src[4], SkPoint dst[10])
int SkFindCubicInflections(const SkPoint src[4], SkScalar tValues[2])
int SkChopCubicAtInflections(const SkPoint src[4], SkPoint dst[10])
```

查找并处理极值点和拐点。

**返回值**: 产生的曲线段数量 - 1

#### 曲线分类

```cpp
SkCubicType SkClassifyCubic(const SkPoint p[4],
                            double t[2] = nullptr,
                            double s[2] = nullptr,
                            double d[4] = nullptr)
```

基于 Loop-Blinn 算法分类三次曲线类型。

**参考文献**: "Resolution Independent Curve Rendering using Programmable Graphics Hardware" (Loop & Blinn, 2005)

#### 单调曲线特殊操作

```cpp
bool SkChopMonoCubicAtY(const SkPoint src[4], SkScalar y, SkPoint dst[7])
bool SkChopMonoCubicAtX(const SkPoint src[4], SkScalar x, SkPoint dst[7])
```

在指定坐标值处切割单调曲线。

### 圆锥曲线 API

#### SkConic 成员方法

```cpp
void evalAt(SkScalar t, SkPoint* pos, SkVector* tangent = nullptr) const
SkPoint evalAt(SkScalar t) const
SkVector evalTangentAt(SkScalar t) const
```

求值方法,支持有理贝塞尔曲线。

```cpp
bool chopAt(SkScalar t, SkConic dst[2]) const
void chopAt(SkScalar t1, SkScalar t2, SkConic* dst) const
void chop(SkConic dst[2]) const  // 在 t=0.5 处细分
```

圆锥曲线细分,返回 false 表示生成非有限值。

#### 二次曲线近似

```cpp
int computeQuadPOW2(SkScalar tol) const
int chopIntoQuadsPOW2(SkPoint pts[], int pow2) const
```

将圆锥曲线近似为多段二次贝塞尔曲线。

**算法**: 基于 Floater 1993 的论文 "High order approximation of conic sections by quadratic splines"

#### 边界计算

```cpp
void computeTightBounds(SkRect* bounds) const
void computeFastBounds(SkRect* bounds) const
```

计算精确/快速边界框。

#### 单位圆弧构建

```cpp
static int BuildUnitArc(const SkVector& start, const SkVector& stop,
                        SkPathDirection dir, const SkMatrix* matrix,
                        SkConic conics[kMaxConicsForArc])
```

将圆弧表示为圆锥曲线序列(最多 5 个)。

### 工具函数

```cpp
int SkFindUnitQuadRoots(SkScalar A, SkScalar B, SkScalar C,
                        SkScalar roots[2])
float SkMeasureAngleBetweenVectors(SkVector a, SkVector b)
SkVector SkFindBisector(SkVector a, SkVector b)
```

基础数学工具。

## 内部实现细节

### SIMD 优化

使用 skvx::float2 和 skvx::float4 实现向量化:

```cpp
// 双点并行细分
float4 p00, p11, p22, p33, T;
p00.lo = p00.hi = sk_bit_cast<float2>(src[0]);
T.lo = t0;
T.hi = t1;
// ... 一次处理两个细分点
```

### 数值稳定性

#### 根查找算法

```cpp
// Numerical Recipes 公式
Q = -0.5 * (B + sign(B) * sqrt(B² - 4AC))
x1 = Q / A
x2 = C / Q
```

避免精度损失。

#### 混合插值

```cpp
// 不使用标准 lerp: a*(1-t) + b*t
// 使用: (b-a)*t + a
// 避免 t=1 时的浮点误差
```

### 曲线分类算法

基于拐点函数的判别式:

```cpp
D(t) = D₃t³ + D₂t² + D₁t + D₀

判别式 discr = 3D₂² - 4D₁D₃

if (discr > 0)  → Serpentine(蛇形)
if (discr < 0)  → Loop(环形)
if (discr == 0) → Cusp(尖点)
```

### 圆锥曲线近似误差

```cpp
// Floater 公式
error = k * |P₀ - 2P₁ + P₂|
其中 k = (w-1) / (4(2+w))
```

### 单调性保证

```cpp
// 确保细分后的曲线保持Y方向单调
if (!between(startY, midY, endY)) {
    // 修正中点到更接近的端点
    dst[0].fPts[2].fY = closerY;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPoint | 二维点表示 |
| SkMatrix | 变换矩阵 |
| SkVx | SIMD 向量运算 |
| SkBezierCurves | 贝塞尔曲线工具 |
| SkCubics | 三次方程求解器 |
| SkFloatingPoint | 浮点工具 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkPath | 路径操作(addQuad/addCubic/addConic) |
| SkScan | 扫描转换器(需要单调曲线) |
| SkStroke | 描边算法(曲线偏移) |
| SkPathMeasure | 路径测量(弧长计算) |
| GPU 后端 | 曲线细分着色器 |

## 设计模式与设计决策

### 设计决策

1. **为何区分二次、三次和圆锥曲线**
   - 性能: 不同曲线复杂度差异大
   - 精度: 各自优化的算法
   - 表达力: 圆锥曲线可精确表示圆弧

2. **单调曲线的重要性**
   - 扫描转换要求曲线单调
   - 避免自交简化光栅化
   - 保证填充规则正确性

3. **为何返回数组而非 vector**
   - 固定大小,栈分配
   - 避免堆开销
   - 性能关键路径

4. **使用 SIMD 的原因**
   - 曲线细分是热点代码
   - 向量运算天然并行
   - 2-4倍性能提升

5. **数值稳定性优先**
   - 使用 double 进行中间计算
   - 特殊处理边界情况
   - 防御性编程应对退化输入

## 性能考量

### 性能特征

| 操作 | 复杂度 | 典型耗时 |
|------|--------|---------|
| 二次曲线求值 | O(1) | ~10 ns |
| 三次曲线求值 | O(1) | ~15 ns |
| 曲线细分 | O(1) | ~20-50 ns |
| 查找极值 | O(1) | ~30 ns |
| 查找拐点 | O(1) | ~50 ns |
| 曲线分类 | O(1) | ~100 ns |
| 圆锥转二次 | O(n) | ~5 μs (n=8) |

### 优化策略

1. **SIMD 并行**: 使用 float2/float4 批量处理
2. **栈分配**: 避免动态内存分配
3. **提前返回**: 检测退化情况快速路径
4. **缓存友好**: 紧凑的数据布局
5. **LUT**: 圆弧构建使用查找表

### 内存占用

```cpp
sizeof(SkConic) = 3*8 + 4 = 28 字节
sizeof(SkQuadCoeff) = 3*8 = 24 字节
sizeof(SkCubicCoeff) = 4*8 = 32 字节

// 栈上临时数组
SkPoint dst[10];  // 最大三次细分: 40 字节
```

### 性能瓶颈

- **sqrt/三角函数**: 曲率和角度计算的主要开销
- **除法**: 求根公式中的除法操作
- **条件分支**: 退化情况处理

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkPath.h | 路径接口(使用曲线) |
| src/core/SkScan.cpp | 扫描转换器 |
| src/core/SkStroke.cpp | 描边算法 |
| src/core/SkPathMeasure.cpp | 路径测量 |
| src/base/SkBezierCurves.h | 贝塞尔曲线工具 |
| src/base/SkCubics.h | 三次方程求解 |
| src/gpu/ganesh/geometry/* | GPU 几何处理 |
| tests/GeometryTest.cpp | 单元测试 |
