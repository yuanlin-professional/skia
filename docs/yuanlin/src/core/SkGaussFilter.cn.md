# SkGaussFilter

> 源文件：src/core/SkGaussFilter.h, src/core/SkGaussFilter.cpp

## 概述

SkGaussFilter 是 Skia 图形库中的高斯滤波器实现,用于生成离散高斯卷积核。该类基于 Tony Lindeberg 的 "Scale-Space for Discrete Signals" 论文,使用修正贝塞尔函数(Bessel functions)计算高斯核系数,精度达到百万分之一。专门优化用于 sigma < 2 的情况。

## 架构位置

```
Skia 图形库
└── src/core (核心模块)
    └── 图像处理
        ├── SkGaussFilter (高斯滤波器)
        ├── SkBlurEngine (模糊引擎)
        └── SkMaskFilter (遮罩滤波器)
```

该类是 Skia 图像模糊和滤波系统的基础组件,为各种模糊效果提供数学核心。

## 主要类与结构体

### SkGaussFilter

**继承关系**
- 无继承,独立实现类

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fBasis | double[kGaussArrayMax] | 高斯核系数数组 |
| fN | int | 实际使用的系数数量 |

**静态常量**

| 常量 | 值 | 说明 |
|------|---|------|
| kGaussArrayMax | 6 | 最大核尺寸(支持 sigma < 2) |

## 公共 API 函数

### 构造函数

```cpp
explicit SkGaussFilter(double sigma)
```

创建指定 sigma 值的高斯滤波器。

**参数**
- sigma: 高斯分布标准差,必须满足 0 <= sigma < 2

**断言**
- 使用 SkASSERT 验证 sigma 范围

**功能**
- 计算贝塞尔系数
- 归一化核权重
- 确定核尺寸 fN

### size

```cpp
size_t size() const
```

返回核中的系数数量。

### radius

```cpp
int radius() const
```

返回核半径(size - 1),表示从中心到边缘的距离。

### width

```cpp
int width() const
```

返回核总宽度(2 * radius + 1),表示完整卷积窗口大小。

### begin / end

```cpp
const double* begin() const
const double* end() const
```

提供 C++ 范围迭代器接口,支持 range-based for 循环:

```cpp
for (double coefficient : gaussFilter) {
    // 处理每个系数
}
```

## 内部实现细节

### 贝塞尔函数计算

使用修正贝塞尔函数 I_n(x) 计算离散高斯核:

```cpp
// 修正贝塞尔函数 I_0
besselI_0(t) = sum_{k=0}^{inf} [(t^2/4)^k / (k!)^2]

// 修正贝塞尔函数 I_1
besselI_1(t) = (t/2) * sum_{k=0}^{inf} [(t^2/4)^k / (k!(k+1)!)]

// 高斯核公式
gauss(n; var) = besselI_n(var) / e^var
```

### 迭代计算策略

1. **自适应循环次数**: 当因子小于 1e-6 时停止迭代
2. **递归关系**: I_{n+1} = -(2n/var) * I_n + I_{n-1}
3. **提前终止**: 当系数小于阈值(1%)时停止扩展

### 归一化过程

```cpp
static void normalize(int n, double* gauss) {
    // 1. 从小到大累加计算总和(数值稳定)
    double sum = gauss[0] + 2 * sum(gauss[1..n-1])

    // 2. 归一化所有系数
    gauss[i] /= sum

    // 3. 修正浮点误差
    gauss[0] = 1 - 2 * sum(gauss[1..n-1])
}
```

确保所有系数之和恰好为 1.0,消除浮点累积误差。

### 核尺寸确定

```cpp
// 扩展核直到系数足够小
while (gauss[n] > kGoodEnough) {  // kGoodEnough = 1%
    计算下一个系数
    n++
}
```

动态确定核大小,平衡精度和性能。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkAssert | 参数验证和调试断言 |
| 标准数学库(cmath) | exp, sqrt 函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkBlurEngine | 图像模糊核心算法 |
| SkMaskFilter | 遮罩模糊效果 |
| SkImageFilter | 高级图像滤波 |
| Ganesh GPU 后端 | GPU 加速模糊 |

## 设计模式与设计决策

### 设计模式

1. **值对象模式**: 不可变对象,构造后不可修改
2. **迭代器模式**: 提供 begin/end 支持标准库算法
3. **策略模式**: 封装特定 sigma 范围的计算策略

### 设计决策

1. **为何限制 sigma < 2**
   - 保持核尺寸在 6 以内,避免性能开销
   - 更大的 sigma 应使用多次小模糊或分离卷积
   - 贝塞尔级数收敛更快

2. **使用 double 而非 float**
   - 归一化过程需要高精度
   - 避免累积误差导致总和偏离 1.0
   - 仅存储时使用 double,实际卷积可转换为 float

3. **预计算而非运行时生成**
   - 一次计算,多次使用
   - 避免每次模糊操作重复计算
   - 缓存友好的数组存储

4. **对称核的优化**
   - 只存储 [0, n) 的系数
   - 卷积时利用对称性减少计算
   - 节省内存和带宽

## 性能考量

### 性能优化

1. **固定大小数组**: fBasis[6] 栈分配,无堆开销
2. **提前终止**: 1% 阈值避免不必要的计算
3. **数值稳定算法**: 从小到大累加避免精度损失

### 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 构造函数 | O(n²) | n ≤ 6,实际很小 |
| 访问器方法 | O(1) | 内联函数 |
| 迭代访问 | O(n) | 直接指针访问 |

### 内存占用

```
sizeof(SkGaussFilter) = 8*6 + 4 = 52 字节
- fBasis: 48 字节 (6 个 double)
- fN: 4 字节 (int)
- 对齐填充: 可能额外 4 字节
```

### 数值精度

- **相对误差**: < 1e-6 (百万分之一)
- **归一化误差**: 通过修正步骤完全消除
- **适用范围**: sigma ∈ [0, 2) 的所有实数值

### 典型 sigma 值的核尺寸

| sigma | 核尺寸 n | 总宽度 | 说明 |
|-------|---------|--------|------|
| 0.5 | 2 | 3 | 轻微模糊 |
| 1.0 | 4 | 7 | 中等模糊 |
| 1.5 | 5 | 9 | 较强模糊 |
| 1.9 | 6 | 11 | 最大支持 |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| src/core/SkBlurEngine.cpp | 使用高斯核的模糊引擎 |
| src/core/SkMaskFilter.cpp | 遮罩模糊实现 |
| include/effects/SkBlurImageFilter.h | 图像模糊滤波器接口 |
| src/gpu/ganesh/effects/GrBlurEffect.cpp | GPU 模糊着色器 |
| tests/SkGaussFilterTest.cpp | 单元测试 |
