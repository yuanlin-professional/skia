# SkBlurEngine

> 源文件：src/core/SkBlurEngine.h, src/core/SkBlurEngine.cpp

## 概述

`SkBlurEngine` 是 Skia 中后端无关（backend-agnostic）的模糊算法提供者。它定义了模糊算法的抽象接口，并为 CPU 后端提供了具体实现。每个 Skia 后端（CPU、GPU）可以定义自己的模糊引擎，包含针对特定颜色类型、sigma 范围或硬件优化的算法实现。

核心特性：
- 后端无关的算法接口设计
- 支持多种模糊算法（高斯模糊、盒式模糊、着色器模糊）
- 自动处理大 sigma 值的降采样策略
- 为 RGBA8、BGRA8、A8 提供专用优化
- 支持运行时效果（SkRuntimeEffect）实现的着色器模糊

## 架构位置

`SkBlurEngine` 位于 Skia 图形栈的中间层，连接上层模糊效果和底层后端实现：

```
高层 API
├── SkImageFilter
├── SkMaskFilter
└── FilterResult::Builder::blur()
          ↓
      SkBlurEngine (抽象层)
          ↓
    ┌─────┴─────┐
    ↓           ↓
RasterBlur   GPUBlur
(CPU实现)    (GPU实现)
```

该引擎通过算法接口（`Algorithm`）提供具体的模糊实现，隐藏后端细节。

## 主要类与结构体

### 1. SkBlurEngine

**继承关系：**无基类，纯虚接口类

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无实例成员 | - | 纯接口类，无状态 |

**关键虚函数：**

| 方法 | 说明 |
|------|------|
| `findAlgorithm()` | 根据 sigma 和颜色类型查找合适算法 |
| `GetRasterBlurEngine()` | 获取 CPU 后端的单例引擎 |

**静态工具函数：**

| 方法 | 说明 |
|------|------|
| `IsEffectivelyIdentity()` | 判断 sigma 是否过小（≤0.03）可跳过模糊 |
| `SigmaToRadius()` | 将 sigma 转换为像素半径（3σ原则）|
| `BoxBlurWindow()` | 计算盒式模糊窗口大小 |

### 2. SkBlurEngine::Algorithm

**继承关系：**纯虚基类

**关键虚函数：**

| 方法 | 说明 |
|------|------|
| `maxSigma()` | 返回算法支持的最大 sigma 值 |
| `supportsOnlyDecalTiling()` | 是否仅支持 kDecal 平铺模式 |
| `blur()` | 执行实际的模糊操作 |

### 3. SkShaderBlurAlgorithm

**继承关系：**`SkBlurEngine::Algorithm`

使用运行时效果（SkRuntimeEffect）实现的通用模糊算法，支持所有后端。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| kMaxLinearSigma | constexpr float (4.0f) | 线性采样模糊的最大 sigma |
| kMaxSamples | constexpr int (28) | 单次模糊的最大采样点数 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `GetBlur2DEffect()` | 获取 2D 模糊的运行时效果 |
| `GetLinearBlur1DEffect()` | 获取 1D 线性模糊的运行时效果 |
| `Compute2DBlurKernel()` | 计算 2D 高斯卷积核 |
| `Compute1DBlurLinearKernel()` | 计算利用硬件线性插值的 1D 核 |

### 4. CPU 后端实现类

#### GaussianPass (模板类)

用于小 sigma（< 2.0）的真高斯模糊，支持 `uint8_t`（A8）和 `uint32_t`（RGBA8）。

#### ThreeBoxApproxPass

使用三次盒式滤波器近似高斯模糊，支持 sigma ≤ 135。

#### TentPass

使用两次盒式滤波器近似 Tent 滤波器，支持 sigma ≤ 2183。

#### RasterA8BlurAlgorithm / Raster8888BlurAlgorithm

针对 A8 和 RGBA8/BGRA8 颜色类型的专用优化实现。

## 公共 API 函数

### 1. 查找算法

```cpp
virtual const Algorithm* findAlgorithm(SkSize sigma,
                                       SkColorType colorType) const = 0
```

**功能：**根据请求的 sigma 和颜色类型，返回最适合的算法实现。

**返回值：**算法指针（由引擎管理生命周期），不支持时返回 `nullptr`。

### 2. 获取光栅引擎

```cpp
static const SkBlurEngine* GetRasterBlurEngine()
```

**功能：**返回 CPU 后端的单例模糊引擎。

**特性：**
- 为 RGBA8/BGRA8 提供盒式模糊优化
- 为 A8 提供专用快速路径
- 其他颜色类型使用着色器模糊

### 3. 执行模糊（Algorithm 接口）

```cpp
virtual sk_sp<SkSpecialImage> blur(SkSize sigma,
                                    sk_sp<SkSpecialImage> src,
                                    const SkIRect& srcRect,
                                    SkTileMode tileMode,
                                    const SkIRect& dstRect) const = 0
```

**参数：**
- `sigma`: X/Y 方向的模糊标准差
- `src`: 输入图像
- `srcRect`: 参与模糊的源区域
- `tileMode`: 边界平铺模式（Clamp/Repeat/Mirror/Decal）
- `dstRect`: 输出区域

**返回值：**模糊后的图像，失败返回 `nullptr`。

### 4. 计算高斯核（SkShaderBlurAlgorithm）

```cpp
static void Compute2DBlurKernel(SkSize sigma, SkISize radius,
                                SkSpan<float> kernel)
```

**功能：**计算归一化的 2D 高斯卷积核。

**核大小：**`KernelWidth(radius.x) × KernelWidth(radius.y)`，其中 `KernelWidth(r) = 2r + 1`。

### 5. 计算线性采样核

```cpp
static void Compute1DBlurLinearKernel(float sigma, int radius,
                                      std::array<SkV4, kMaxSamples/2>& offsetsAndKernel)
```

**功能：**计算利用硬件双线性插值的 1D 模糊核，将相邻样本合并以减少采样次数。

**优化原理：**
```
Wi * Ci + Wj * Cj = W' * (Ci * (1-x) + Cj * x)
其中 W' = Wi + Wj, x = Wj / (Wi + Wj)
```

## 内部实现细节

### 1. 三次盒式卷积近似

三次盒式滤波器产生分段二次函数，其积分为分段三次函数：

```
盒式函数: rect(x)
一次卷积: triangle(x)
二次卷积: 分段二次函数
三次卷积: 分段三次函数（近似高斯）
```

`gaussianIntegral()` 实现该分段函数：
```cpp
if (x > 1.5)  return 0.0;
if (x > 0.5)  return 0.5625 - (x³/6 - 3x²/4 + 9x/8);
if (x > -0.5) return 0.5 - (3x/4 - x³/3);
if (x > -1.5) return 0.4375 + (-x³/6 - 3x²/4 - 9x/8);
return 1.0;
```

### 2. Pass 类设计

所有扫描线处理器继承自 `Pass` 基类：

```cpp
template <typename T>
void blur(int srcLeft, int srcRight, int dstRight,
          const T* src, int srcStride,
          T* dst, int dstStride)
```

该设计通过状态机方式处理模糊窗口的前沿、中部和尾部：
1. **前沿阶段**：窗口逐渐填充
2. **稳定阶段**：窗口完全覆盖源数据
3. **尾部阶段**：窗口逐渐排空

### 3. 循环缓冲区优化

`GaussianPass` 和 `ThreeBoxApproxPass` 使用循环缓冲区存储窗口状态：

```cpp
// 更新循环索引
base = (base + 1) % fWindow;
// 读取缓冲区
value = fBuffer[(base + offset) % fWindow];
```

避免每次迭代都移动整个窗口数据。

### 4. SIMD 优化

盒式模糊在支持的平台使用向量指令：
- **LSX**（LoongArch）：`__lsx_*` 指令集
- **通用**：`skvx::Vec<4, uint32_t>` 抽象

### 5. 着色器模糊的分块渲染

`SkShaderBlurAlgorithm::renderBlur()` 将输出区域分为：
1. **快速区域**：内部安全区，使用硬件平铺
2. **严格区域**：边界区域，使用子集着色器精确平铺

这样在保证边界正确性的同时最大化快速路径覆盖。

### 6. 两阶段模糊策略

对于大卷积核，使用两次 1D 模糊代替单次 2D 模糊：

```
如果 kernelArea > kMaxSamples 或任一维度为 0:
    X 方向模糊 -> 中间图像 -> Y 方向模糊
否则:
    单次 2D 模糊
```

### 7. 降采样触发机制

虽然 `SkBlurEngine` 本身不直接处理降采样，但定义了 `maxSigma()` 接口，调用者（如 `FilterResult::Builder`）据此决定是否先降采样输入。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkSpecialImage` | 图像数据抽象 |
| `SkDevice` | 设备上下文（用于渲染） |
| `SkRuntimeEffect` | 动态着色器编译 |
| `SkBitmap` | 位图数据访问 |
| `skvx` | SIMD 向量抽象 |
| `SkArenaAlloc` | 快速内存分配 |
| `SkKnownRuntimeEffects` | 内置运行时效果管理 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `skif::FilterResult` | 调用 `findAlgorithm()` 和 `blur()` |
| `SkImageFilter` | 通过 FilterResult 间接使用 |
| `SkBlurImageFilter` | 构造时注册模糊引擎 |

## 设计模式与设计决策

### 1. 策略模式

`SkBlurEngine` 是策略接口，各后端提供不同的策略实现（`RasterBlurEngine`、`GPUBlurEngine` 等）。

**优势：**调用者无需知道具体后端，统一接口处理所有平台。

### 2. 工厂方法模式

```cpp
const Algorithm* findAlgorithm(SkSize sigma, SkColorType ct) const override {
    if (a8Blur) return &fA8BlurAlgorithm;
    if (rgba8Blur) return &fRGBA8BlurAlgorithm;
    return &fShaderBlurAlgorithm;
}
```

引擎根据输入参数选择最佳算法，调用者无需了解选择逻辑。

### 3. 单例模式

```cpp
static const SkBlurEngine* GetRasterBlurEngine() {
    static const RasterBlurEngine kInstance;
    return &kInstance;
}
```

CPU 模糊引擎采用单例设计，避免重复初始化。

### 4. 模板方法模式

`Pass` 基类定义了模糊流程框架：
```cpp
void blur(...) {
    this->startBlur();
    // 前沿处理
    // 稳定处理
    // 尾部处理
}
```

子类实现 `startBlur()` 和 `blurSegment()` 细节。

### 5. 桥接模式

`SkShaderBlurAlgorithm` 作为桥梁，连接后端无关的着色器代码和各平台的 `SkDevice` 实现。

### 6. 性能分层决策

提供三层精度/性能权衡：
1. **GaussianPass**：小 sigma，真高斯，最准确
2. **ThreeBoxApproxPass**：中等 sigma，盒式近似，快速通用
3. **TentPass**：大 sigma，Tent 近似，支持极大模糊

每层在其适用范围内达到最佳性能。

## 性能考量

### 1. 算法性能特征

| 算法 | 适用 Sigma | 复杂度 | 特点 |
|------|-----------|--------|------|
| GaussianPass | < 2.0 | O(σ×n) | 真高斯，最准确 |
| ThreeBoxApprox | 2.0 ~ 135 | O(n) | 常数时间，与 σ 无关 |
| TentPass | 135 ~ 2183 | O(n) | 支持超大模糊 |
| ShaderBlur | 任意 | O(σ²×n) | GPU 友好，通用 |

### 2. 内存优化

**循环缓冲区：**盒式模糊使用固定大小缓冲区，内存占用为 `O(窗口大小)` 而非 `O(图像大小)`。

**原地处理：**X 方向模糊后，结果直接用于 Y 方向模糊，避免额外拷贝。

**栈分配：**小尺寸缓冲区使用 `SkSTArenaAlloc<1024>`，避免堆分配开销。

### 3. 线性采样优化

利用 GPU 硬件双线性插值，将采样点数减半：

```
原始: 需要 2r+1 次采样
优化: 只需 r+1 次采样
```

对 r=27 的情况，从 55 次采样降至 28 次。

### 4. 预取优化

```cpp
SK_PREFETCH(dstCursor);
```

在 x86 和其他支持的平台，预取下一个缓存行，减少内存延迟。

### 5. 缓存友好性

**连续访问：**扫描线处理保证内存访问局部性。

**转置技巧：**Y 方向模糊时，通过转置确保线性读写：
```cpp
// X 方向：行优先
for (y) for (x) process(x, y);
// Y 方向：列优先但转置缓冲区确保连续性
```

### 6. 着色器批处理

`to_stablekey()` 将相似大小的核批处理到同一着色器变体，减少着色器编译开销：
- 2~4 样本 -> 变体 0
- 5~8 样本 -> 变体 1
- ...

### 7. 性能陷阱

**小 sigma 用盒式模糊：**sigma < 2 时盒式近似精度极差，应使用真高斯。

**大 sigma 未降采样：**sigma > 135 时，建议先降采样 2x~4x，否则窗口过大。

**不必要的边界精确性：**内部区域使用快速平铺，边界才用严格子集。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| src/core/SkBlurMask.h | 相关工具 | 遮罩模糊底层实现 |
| src/core/SkMaskBlurFilter.h | 内部依赖 | 盒式滤波器具体逻辑 |
| src/core/SkKnownRuntimeEffects.h | 运行时效果 | 着色器管理 |
| src/core/SkSpecialImage.h | 数据类型 | 图像抽象 |
| src/core/SkBitmapDevice.h | 设备实现 | CPU 设备上下文 |
| include/effects/SkImageFilters.h | 上层 API | 图像滤镜接口 |
| src/base/SkVx.h | SIMD 工具 | 向量化计算 |
