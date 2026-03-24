# BlurUtils

> 源文件: src/gpu/BlurUtils.h, src/gpu/BlurUtils.cpp

## 概述

`BlurUtils` 是 Skia GPU 模糊效果工具模块,提供了多种模糊算法的实现和辅助功能。该模块封装了高斯模糊、矩形模糊、圆形模糊和圆角矩形模糊的核心算法,为 GPU 渲染提供高性能的模糊效果支持。它包含了模糊核(blur kernel)的计算、积分表的生成、模糊轮廓(profile)的创建等关键功能,是 Skia 模糊渲染管线的基础设施。

该模块主要作为 `SkBlurEngine` 的包装层和扩展,同时提供了一些专用的模糊遮罩生成功能,如圆形轮廓和圆角矩形遮罩的CPU端计算。

## 架构位置

在 Skia 架构中,`BlurUtils` 位于 GPU 抽象层:

- **上游依赖**: 依赖 `SkBlurEngine` 和 `SkShaderBlurAlgorithm` 提供的核心模糊算法
- **同级模块**: 与 GPU 渲染模块协作,为着色器提供模糊参数
- **下游使用**: 被 Ganesh 和 Graphite 等 GPU 后端的模糊渲染路径使用
- **应用场景**: 阴影效果、背景模糊、UI 模糊效果等

该模块是跨平台的,不依赖特定的 GPU API,提供通用的模糊计算工具。

## 主要类与结构体

本模块主要提供静态工具函数,没有定义类,但使用了以下数据结构:

### 核心数据结构

**ETC1Block (内部)**
```cpp
struct ETC1Block {
    uint32_t fHigh;
    uint32_t fLow;
};
```
用于 ETC1 纹理压缩的数据块结构(内部使用)。

**BC1Block (内部)**
```cpp
struct BC1Block {
    uint16_t fColor0;
    uint16_t fColor1;
    uint32_t fIndices;
};
```
用于 BC1 纹理压缩的数据块结构(内部使用)。

### 常量定义

| 常量 | 值 | 说明 |
|------|-----|------|
| `kMaxBlurSamples` | `SkShaderBlurAlgorithm::kMaxSamples` | 最大模糊采样数 |
| `kMaxLinearBlurSigma` | `SkShaderBlurAlgorithm::kMaxLinearSigma` | 线性模糊的最大 sigma 值 |

## 公共 API 函数

### 包装函数 (Wrapper Functions)

以下函数是对 `SkBlurEngine` 和 `SkShaderBlurAlgorithm` 的包装:

#### BlurKernelWidth
```cpp
constexpr int BlurKernelWidth(int radius)
```
**功能**: 计算给定半径的模糊核宽度。
**返回**: 核宽度(像素数)。

#### BlurLinearKernelWidth
```cpp
constexpr int BlurLinearKernelWidth(int radius)
```
**功能**: 计算线性优化模糊核的宽度。
**返回**: 优化后的核宽度。

#### BlurIsEffectivelyIdentity
```cpp
constexpr bool BlurIsEffectivelyIdentity(float sigma)
```
**功能**: 判断给定 sigma 值的模糊是否等效于恒等变换(无模糊效果)。
**返回**: `true` 表示无需模糊。

#### BlurSigmaRadius
```cpp
inline int BlurSigmaRadius(float sigma)
```
**功能**: 将模糊强度 sigma 转换为像素半径。
**返回**: 模糊半径(像素)。

### 着色器效果获取

#### GetBlur2DEffect
```cpp
inline const SkRuntimeEffect* GetBlur2DEffect(const SkISize& radii)
```
**功能**: 获取二维模糊的运行时效果对象。
**参数**: `radii` - X和Y方向的模糊半径。
**返回**: 对应的 `SkRuntimeEffect` 指针。

#### GetLinearBlur1DEffect
```cpp
inline const SkRuntimeEffect* GetLinearBlur1DEffect(int radius)
```
**功能**: 获取一维线性模糊的运行时效果对象。
**参数**: `radius` - 模糊半径。
**返回**: 对应的 `SkRuntimeEffect` 指针。

### 模糊核计算

#### Compute2DBlurKernel (数组版本)
```cpp
inline void Compute2DBlurKernel(SkSize sigma, SkISize radius, SkSpan<float> kernel)
```
**功能**: 计算二维高斯模糊核的权重值。
**参数**:
- `sigma`: X和Y方向的模糊强度
- `radius`: 核半径
- `kernel`: 输出缓冲区

#### Compute2DBlurKernel (SkV4数组版本)
```cpp
inline void Compute2DBlurKernel(SkSize sigma, SkISize radius,
                                std::array<SkV4, kMaxBlurSamples/4>& kernel)
```
**功能**: 计算二维模糊核,输出为向量数组(优化版本)。

#### Compute1DBlurKernel
```cpp
inline void Compute1DBlurKernel(float sigma, int radius, SkSpan<float> kernel)
```
**功能**: 计算一维高斯模糊核。

#### Compute2DBlurOffsets
```cpp
inline void Compute2DBlurOffsets(SkISize radius, std::array<SkV4, kMaxBlurSamples/2>& offsets)
```
**功能**: 计算二维模糊采样的偏移量。

#### Compute1DBlurLinearKernel
```cpp
inline void Compute1DBlurLinearKernel(float sigma, int radius,
                                      std::array<SkV4, kMaxBlurSamples/2>& offsetsAndKernel)
```
**功能**: 计算线性优化的一维模糊核(合并相邻采样点)。

### 矩形模糊工具

#### CreateIntegralTable
```cpp
SkBitmap CreateIntegralTable(int width)
```
**功能**: 创建用于分析矩形模糊的积分表。该表存储在位图的红色通道中。
**参数**: `width` - 积分表宽度。
**返回**: 包含积分值的 1D 位图(高度为1)。
**算法**: 使用误差函数 `erf()` 计算高斯分布的累积分布函数。

#### ComputeIntegralTableWidth
```cpp
int ComputeIntegralTableWidth(float sixSigma)
```
**功能**: 计算给定 6σ 范围所需的积分表宽度。
**返回**: 优化后的表宽度(2的幂次,最小为32)。
**优化**: 使用 `SkNextPow2()` 对齐到2的幂次以提高缓存效率。

### 圆形模糊工具

#### CreateCircleProfile
```cpp
SkBitmap CreateCircleProfile(float sigma, float radius, int profileWidth)
```
**功能**: 创建模糊圆形的轮廓位图。
**参数**:
- `sigma`: 模糊强度
- `radius`: 圆形半径
- `profileWidth`: 轮廓宽度(像素)
**返回**: A8 格式的轮廓位图。
**算法**: 使用半核卷积和累加表技术计算径向模糊分布。

#### CreateHalfPlaneProfile
```cpp
SkBitmap CreateHalfPlaneProfile(int profileWidth)
```
**功能**: 创建半平面近似的模糊轮廓。
**参数**: `profileWidth` - 轮廓宽度(必须是偶数)。
**返回**: A8 格式的轮廓位图。
**用途**: 用于边缘模糊的快速近似。

### 圆角矩形模糊

#### CreateRRectBlurMask
```cpp
SkBitmap CreateRRectBlurMask(const SkRRect& rrectToDraw, const SkISize& dimensions, float sigma)
```
**功能**: 创建模糊圆角矩形的遮罩位图。
**参数**:
- `rrectToDraw`: 要绘制的圆角矩形(在 dimensions 中心)
- `dimensions`: 输出遮罩的尺寸(包含模糊区域)
- `sigma`: 模糊强度
**返回**: A8 格式的遮罩位图。
**算法**: 结合积分表和水平高斯核进行二维模糊计算。

## 内部实现细节

### 矩形模糊算法
使用误差函数 `std::erf()` 计算高斯分布的积分值:
```
integral(x) = 0.5 * (erf((-6*x + 3) * sqrt(2)/2) + 1)
```
这种方法将连续的高斯模糊转化为查表操作,大幅提升性能。

### 圆形模糊算法
采用三步法:
1. **半核生成**: 使用 `make_unnormalized_half_kernel()` 生成高斯半核
2. **累加表**: 通过 `make_half_kernel_and_summed_table()` 创建累积分布
3. **二维卷积**: `apply_kernel_in_y()` 在垂直方向应用核,`eval_at()` 在水平方向合并结果

### 圆角矩形模糊算法
1. 为每个 X 坐标计算顶部边界位置(考虑圆角)
2. 使用垂直积分表评估模糊 (`eval_V`)
3. 应用水平高斯核 (`eval_H`)
4. 利用对称性只计算四分之一,然后镜像复制

### ETC1/BC1 压缩支持
内部实现了纹理压缩块的创建,用于优化纹理存储:
- **ETC1**: 使用差分模式编码,通过修改器表匹配目标颜色
- **BC1**: 使用 RGB565 颜色对和索引表

### 内存安全
- 所有位图创建都使用 `tryAllocPixels()` 防止分配失败
- 对溢出进行检查(如 `kAllocLimit` 限制)
- 使用 `SkASSERT` 验证参数合法性

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `src/core/SkBlurEngine.h` | `SkShaderBlurAlgorithm` | 模糊算法实现 |
| `include/core/SkBitmap.h` | `SkBitmap` | 位图存储 |
| `include/core/SkRRect.h` | `SkRRect` | 圆角矩形定义 |
| `include/core/SkSize.h` | `SkISize`, `SkSize` | 尺寸类型 |
| `src/core/SkMathPriv.h` | `SkNextPow2`, 数学工具 | 数学计算 |
| `include/private/base/SkTemplates.h` | `AutoTArray` | 自动数组 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 模糊路径 | 积分表、圆形轮廓 | 模糊渲染 |
| Graphite 模糊效果 | 模糊核计算函数 | 着色器参数 |
| 阴影渲染器 | `CreateRRectBlurMask` | 软阴影效果 |
| 背景模糊滤镜 | 包装函数 | 实时模糊效果 |

## 设计模式与设计决策

### 1. 包装器模式
对 `SkBlurEngine` 的包装函数简化了 GPU 代码的调用接口,同时保持了与上游 API 的兼容性,便于未来迁移。

### 2. 查表优化
矩形模糊使用积分表而非直接卷积,将 O(n²) 复杂度降低到 O(n),是经典的空间换时间策略。

### 3. 对称性利用
圆角矩形模糊只计算四分之一区域,利用镜像对称性减少75%的计算量。

### 4. 纹理复用
通过位图格式的轮廓(profile)可以被上传到 GPU 作为纹理,支持硬件加速的模糊效果。

### 5. 精度控制
积分表宽度使用 `SkNextPow2()` 对齐,既保证精度(2倍过采样),又优化缓存访问和纹理采样。

### 6. 分离可卷积操作
圆形模糊分解为先垂直再水平的两次一维操作,利用高斯核的可分离性提升性能。

## 性能考量

### 1. 算法复杂度
- **矩形模糊**: O(1) 通过积分表查询
- **圆形模糊**: O(n*m) 其中 n 是轮廓宽度,m 是核半径
- **圆角矩形**: O(w*h*k) 其中 k 是核大小,但利用对称性减半

### 2. 内存优化
- 使用 `AutoTArray` 自动管理临时数组,栈上分配小数组
- 位图使用 A8 格式(单字节),最小化内存占用
- 积分表宽度对齐到2的幂次,优化缓存行利用率

### 3. 数值稳定性
- 使用 `std::erf()` 标准库函数保证精度
- 归一化处理避免累积误差
- 边界检查防止数组越界

### 4. GPU 友好设计
- 轮廓位图格式与 GPU 纹理兼容,可直接上传
- 预计算的核和偏移量减少着色器计算
- 使用 `SkRuntimeEffect` 动态生成着色器,支持不同半径的优化

### 5. 早期退出
`BlurIsEffectivelyIdentity()` 在 sigma 过小时避免无用计算,提升小模糊场景的性能。

### 6. 并行友好
圆角矩形模糊的像素独立计算,易于并行化(虽然当前是 CPU 实现)。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/BlurUtils.h` | 定义 | 模糊工具接口 |
| `src/gpu/BlurUtils.cpp` | 实现 | 模糊算法实现 |
| `src/core/SkBlurEngine.h` | 依赖 | 核心模糊算法 |
| `src/gpu/ganesh/GrBlurUtils.h` | 使用者 | Ganesh 模糊实现 |
| `src/gpu/graphite/BlurUtils.h` | 使用者 | Graphite 模糊实现 |
| `src/effects/SkBlurMaskFilter.cpp` | 间接使用 | 模糊遮罩滤镜 |
| `src/core/SkMipmap.cpp` | 相关 | Mipmap 生成 |
| `include/core/SkRuntimeEffect.h` | 依赖 | 动态着色器生成 |

**备注**: 该模块是 Skia GPU 模糊效果的核心工具库,所有需要高性能模糊的场景都会使用其提供的算法和数据结构。
