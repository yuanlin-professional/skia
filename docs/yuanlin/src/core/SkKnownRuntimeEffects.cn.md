# SkKnownRuntimeEffects

> 源文件
> - src/core/SkKnownRuntimeEffects.h
> - src/core/SkKnownRuntimeEffects.cpp

## 概述

`SkKnownRuntimeEffects` 是 Skia 中管理预定义运行时效果的命名空间,提供了一组已知的、稳定的 SkSL (Skia Shading Language) 着色器效果。这些效果被分配了稳定的键值(Stable Key),可以在序列化和缓存中保持一致性,避免了运行时动态编译的开销。

该模块为 Skia 内部的各种图像滤镜提供优化的着色器实现,包括模糊、混合、形态学、光照等常见图像处理效果。通过集中管理这些效果,Skia 可以保证跨平台和版本的一致性。

## 架构位置

`SkKnownRuntimeEffects` 在 Skia 渲染管道中处于着色器管理层:

```
应用层 (SkImageFilters, SkColorFilters, SkBlenders)
    ↓
SkKnownRuntimeEffects (稳定键管理和效果工厂)
    ↓
SkRuntimeEffect (SkSL 编译和执行)
    ↓
GPU 后端 (Ganesh/Graphite)
```

它作为高层图像处理 API 和底层运行时效果系统之间的桥梁。

## 主要类与结构体

### StableKey 枚举

**定义:**
```cpp
enum class StableKey : uint32_t {
    kStart = kSkiaKnownRuntimeEffectsStart,
    kInvalid = kStart,
    k1DBlur4, k1DBlur8, k1DBlur12, k1DBlur16, k1DBlur20, k1DBlur28,
    k2DBlur4, k2DBlur8, k2DBlur12, k2DBlur16, k2DBlur20, k2DBlur28,
    kBlend, kDecal, kDisplacement, kLighting,
    kLinearMorphology, kMagnifier,
    kMatrixConvUniforms, kMatrixConvTexSm, kMatrixConvTexLg,
    kNormal, kSparseMorphology,
    kArithmetic, kHighContrast, kLerp, kLuma, kOverdraw,
    kLast = kOverdraw,
};
```

**用途:** 为每个已知的运行时效果分配唯一的稳定标识符。

### 键值空间分配

系统将 32 位无符号整数空间分成几个区块:

| 区块 | 起始值 | 数量 | 用途 |
|------|--------|------|------|
| Skia 内建 | 0 | 500 | Skia 内建着色器 |
| Skia 已知效果 | 500 | 500 | 本模块管理的效果 |
| 用户定义已知效果 | 1000 | 100 | Chrome/Android 等第一方客户端 |
| 未知效果 | 1100+ | 不限 | 动态分配,不稳定 |

## 公共 API 函数

### IsSkiaKnownRuntimeEffect

```cpp
bool IsSkiaKnownRuntimeEffect(int candidate);
```

**功能:** 检查给定的整数是否是有效的 Skia 已知运行时效果键。

**返回值:** 如果 candidate 在 [kStart, kLast] 范围内,返回 true。

### IsUserDefinedRuntimeEffect

```cpp
bool IsUserDefinedRuntimeEffect(int candidate);
```

**功能:** 检查是否为未知运行时效果(动态分配)。

**返回值:** 如果 candidate >= kUnknownRuntimeEffectIDStart,返回 true。

### IsViableUserDefinedKnownRuntimeEffect

```cpp
bool IsViableUserDefinedKnownRuntimeEffect(int candidate);
```

**功能:** 粗略检查是否为用户定义的已知效果键值范围。

**注意:** 这只是范围检查,实际使用前需要进一步验证。

### MaybeGetKnownRuntimeEffect

```cpp
sk_sp<SkRuntimeEffect> MaybeGetKnownRuntimeEffect(uint32_t candidate);
```

**功能:** 安全地尝试获取已知运行时效果。

**返回值:** 如果是有效的 Skia 已知效果,返回对应的 `SkRuntimeEffect` 智能指针,否则返回 nullptr。

### GetKnownRuntimeEffect

```cpp
const SkRuntimeEffect* GetKnownRuntimeEffect(StableKey key);
```

**功能:** 根据 StableKey 获取对应的运行时效果。

**前提:** 调用者必须确保 key 是有效的 StableKey 值。

**返回值:** 返回指向静态 `SkRuntimeEffect` 对象的指针,如果是 kInvalid 返回 nullptr。

## 内部实现细节

### 1D 模糊着色器生成

```cpp
SkRuntimeEffect* make_blur_1D_shader(int kernelWidth, StableKey stableKey)
```

**特点:**
- 支持的核宽度: 4, 8, 12, 16, 20, 28 像素
- 使用循环展开技术,每次迭代处理 2 个样本
- 核宽度必须是偶数
- 系数存储在 uniform 数组中,最大支持 28/2 = 14 个 float4

**SkSL 代码结构:**
```glsl
const int kMaxLoopLimit = kernelWidth / 2;
uniform half4 offsetsAndKernel[kMaxLoopLimit];
uniform half2 dir;
uniform shader child;

half4 main(float2 coord) {
    half4 sum = half4(0);
    for (int i = 0; i < kMaxLoopLimit; ++i) {
        half4 s = offsetsAndKernel[i];
        sum += s.y * child.eval(coord + s.x*dir);
        sum += s.w * child.eval(coord + s.z*dir);
    }
    return sum;
}
```

### 2D 模糊着色器生成

```cpp
SkRuntimeEffect* make_blur_2D_shader(int maxKernelSize, StableKey stableKey)
```

**优化策略:**
- 将标量系数打包到 half4 中,每次处理 4 个样本
- 预先上传偏移量,避免运行时计算
- 支持的核大小必须是 4 的倍数

**内存布局:**
- `kernel[kMaxLoopLimit]`: 打包的系数 (每个 float4 包含 4 个系数)
- `offsets[2*kMaxLoopLimit]`: 预计算的坐标偏移

### 矩阵卷积着色器

有三种实现变体:

1. **基于 Uniform 的小核 (kMatrixConvUniforms)**
   - 最大支持 `MatrixConvolutionImageFilter::kMaxUniformKernelSize` (通常是 48)
   - 系数存储在 uniform 数组中
   - 适用于小卷积核

2. **基于纹理的中等核 (kMatrixConvTexSm)**
   - 使用纹理存储卷积核
   - 支持 `MatrixConvolutionImageFilter::kSmallKernelSize`
   - 通过纹理查找读取系数

3. **基于纹理的大核 (kMatrixConvTexLg)**
   - 支持 `MatrixConvolutionImageFilter::kLargeKernelSize`
   - 最适合大卷积核

**共同特性:**
- 支持 `convolveAlpha` 选项(是否卷积 alpha 通道)
- 包含 gain 和 bias 调整
- 处理未预乘和预乘 alpha

### 静态对象模式

所有运行时效果都使用静态局部变量模式:

```cpp
case StableKey::k1DBlur4: {
    static SkRuntimeEffect* s1DBlurEffect = make_blur_1D_shader(4, stableKey);
    return s1DBlurEffect;
}
```

**优势:**
- 延迟初始化,只在第一次使用时创建
- 全局共享,避免重复创建
- 线程安全 (C++11 保证静态局部变量初始化的线程安全性)

### 专用内置函数

某些着色器使用了 Skia 的私有内置函数:

- `sk_decal()`: 处理边界外的纹理采样
- `sk_displacement()`: 位移映射
- `sk_lighting()`: 光照计算
- `sk_linear_morphology()`: 线性形态学操作
- `sk_magnifier()`: 放大镜效果
- `sk_normal()`: 法线贴图生成
- `sk_sparse_morphology()`: 稀疏形态学
- `sk_arithmetic_blend()`: 算术混合
- `sk_high_contrast()`: 高对比度调整
- `sk_luma()`: 亮度计算
- `sk_overdraw()`: 过绘制可视化

这些函数通过 `SkRuntimeEffectPriv::AllowPrivateAccess()` 启用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRuntimeEffect | SkSL 编译和执行引擎 |
| SkString | 字符串格式化 (SkStringPrintf) |
| SkRuntimeEffectPriv | 私有 API 访问 |
| SkMatrixConvolutionImageFilter | 卷积核大小常量 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBlurImageFilter | 使用 1D/2D 模糊着色器 |
| SkBlendImageFilter | 使用混合着色器 |
| SkDisplacementMapEffect | 使用位移着色器 |
| SkLightingImageFilter | 使用光照着色器 |
| SkMorphologyImageFilter | 使用形态学着色器 |
| SkMagnifierImageFilter | 使用放大镜着色器 |
| SkMatrixConvolutionImageFilter | 使用矩阵卷积着色器 |
| SkColorFilters | 使用颜色滤镜着色器 |
| SkRuntimeShader | 序列化和反序列化 |
| ShaderCodeDictionary | Graphite 渲染器的着色器字典 |

## 设计模式与设计决策

### 工厂方法模式

每种效果类型都有对应的 `make_*_shader()` 工厂函数:
- `make_blur_1D_shader()`
- `make_blur_2D_shader()`
- `make_blend_shader()`
- `make_matrix_conv_shader()`
- 等等

这些工厂函数封装了复杂的 SkSL 代码生成逻辑。

### 单例模式变体

使用静态局部变量实现单例:
```cpp
static SkRuntimeEffect* sEffect = make_effect();
return sEffect;
```

这是一种线程安全的延迟初始化单例模式。

### 稳定键系统设计

**设计目标:**
1. **版本兼容性:** 旧的 SKP 文件可以在新版本 Skia 中正确加载
2. **缓存稳定性:** 着色器缓存可以跨会话使用
3. **扩展性:** 预留空间给未来的新效果

**键值分配策略:**
- 连续的键值范围用于同一类效果(如 1DBlur4-28)
- 使用 enum 和 static_assert 确保键值布局正确
- 预留大量未使用空间避免冲突

### 模板宏模式

使用宏来定义稳定键列表:

```cpp
#define SK_ALL_STABLEKEYS(M, M1, M2) \
    M2(Invalid, Start)      \
    M1(1DBlurBase)          \
    M2(1DBlur4, 1DBlurBase) \
    // ...
```

**优势:**
- 单一真实来源(Single Source of Truth)
- 可以生成 enum、switch case、static_assert 等多种代码
- 避免手动维护多个列表导致不一致

## 性能考量

### 着色器编译缓存

所有效果都是静态创建的,SkSL 编译只发生一次:
- 首次访问时编译
- 后续访问直接返回缓存的指针
- 避免了运行时编译开销

### 循环展开优化

模糊着色器使用固定迭代次数的循环:
```cpp
for (int i = 0; i < kMaxLoopLimit; ++i)
```

`kMaxLoopLimit` 是编译时常量,GPU 编译器可以完全展开循环,提高性能。

### 系数打包

2D 模糊将 4 个标量系数打包到 half4:
```cpp
uniform half4 kernel[kMaxUniformKernelSize];
```

**优势:**
- 减少 uniform 数量
- 更好的内存对齐
- 满足 std140 布局要求

### 纹理 vs Uniform 权衡

矩阵卷积提供三种变体:
- **小核 (Uniform):** 快速访问,但受 uniform 大小限制
- **中核 (纹理):** 灵活,适度开销
- **大核 (纹理):** 支持任意大小,但有纹理读取延迟

选择由卷积核大小自动决定。

### 私有函数内联

使用 SkRuntimeEffect 的私有内置函数:
- 这些函数可以被 GPU 编译器内联
- 避免函数调用开销
- 某些操作可以使用 GPU 专用指令

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/effects/SkRuntimeEffect.h | 依赖 | 运行时效果基础类 |
| src/core/SkRuntimeEffectPriv.h | 依赖 | 私有 API 和内置函数 |
| src/effects/imagefilters/SkMatrixConvolutionImageFilter.h | 依赖 | 卷积核大小常量 |
| src/effects/imagefilters/SkBlurImageFilter.cpp | 使用者 | 使用模糊着色器 |
| src/effects/imagefilters/SkMorphologyImageFilter.cpp | 使用者 | 使用形态学着色器 |
| src/effects/imagefilters/SkLightingImageFilter.cpp | 使用者 | 使用光照着色器 |
| src/effects/SkColorFilters.cpp | 使用者 | 使用颜色滤镜着色器 |
| src/gpu/graphite/ShaderCodeDictionary.h | 使用者 | Graphite 着色器字典 |
| src/core/SkRuntimeShader.cpp | 使用者 | 序列化支持 |
