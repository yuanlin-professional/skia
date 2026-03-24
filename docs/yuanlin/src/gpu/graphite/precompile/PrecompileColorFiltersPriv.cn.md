# PrecompileColorFiltersPriv - 内部颜色滤镜预编译工厂

> 源文件: `src/gpu/graphite/precompile/PrecompileColorFiltersPriv.h`

## 概述

`PrecompileColorFiltersPriv` 是 Skia Graphite 预编译系统中的内部颜色滤镜工厂命名空间。它提供了三个工厂函数，对应 Skia 内部使用的颜色滤镜类型：高斯滤镜、颜色空间变换滤镜和工作格式滤镜。这些滤镜由 Skia 框架自动插入到渲染管线中，用户不直接创建它们，但管线预编译系统需要覆盖这些变体。

## 架构位置

```
预编译颜色滤镜体系
  ├── PrecompileColorFilters (公共工厂 - 用户可见的颜色滤镜)
  │     ├── Blend, Matrix, HSLAMatrix, Table, Lighting, ...
  └── PrecompileColorFiltersPriv (本文件 - 内部颜色滤镜)
        ├── Gaussian() - 高斯模糊色彩效果
        ├── ColorSpaceXform() - 颜色空间变换
        └── WithWorkingFormat() - 工作格式变换
```

这些内部工厂与 `src/core/SkColorFilterPriv.h` 中定义的运行时颜色滤镜一一对应。

## 主要类与结构体

本文件定义的是命名空间而非类。`PrecompileColorFiltersPriv` 命名空间包含三个工厂函数。

## 公共 API 函数

| 工厂函数 | 返回类型 | 说明 |
|----------|----------|------|
| `Gaussian()` | `sk_sp<PrecompileColorFilter>` | 创建高斯颜色滤镜预编译对象 |
| `ColorSpaceXform(src, dst)` | `sk_sp<PrecompileColorFilter>` | 创建颜色空间变换预编译对象 |
| `WithWorkingFormat(childOptions, tf, gamut, at)` | `sk_sp<PrecompileColorFilter>` | 创建工作格式变换预编译对象 |

### ColorSpaceXform 参数

```cpp
sk_sp<PrecompileColorFilter> ColorSpaceXform(
    SkSpan<const sk_sp<SkColorSpace>> src,   // 源颜色空间列表
    SkSpan<const sk_sp<SkColorSpace>> dst);  // 目标颜色空间列表
```

接受源和目标颜色空间的列表，预编译覆盖所有 src x dst 组合。

### WithWorkingFormat 参数

```cpp
sk_sp<PrecompileColorFilter> WithWorkingFormat(
    SkSpan<const sk_sp<PrecompileColorFilter>> childOptions,  // 子颜色滤镜选项
    const skcms_TransferFunction* tf,                          // 传输函数
    const skcms_Matrix3x3* gamut,                              // 色域矩阵
    const SkAlphaType* at);                                    // Alpha 类型
```

包装子颜色滤镜，在应用前转换到指定的工作格式，应用后转换回来。

## 内部实现细节

### Gaussian 滤镜

用于模糊相关的图像处理流程。在 Android 框架中常用于实现高斯模糊的颜色效果部分。对应运行时的 `SkColorFilterPriv::MakeGaussian()`。

### 颜色空间变换

`ColorSpaceXform` 对应 Skia 自动插入的颜色空间转换步骤。当源图像的颜色空间与渲染目标不同时，Skia 会自动插入此滤镜。预编译需要覆盖所有可能的源/目标颜色空间组合。

### 工作格式变换

`WithWorkingFormat` 对应 `SkColorFilterPriv::WithWorkingFormat()`，用于在特定的颜色工作空间（由传输函数、色域矩阵和 Alpha 类型定义）中应用子颜色滤镜。这在 HDR 内容处理中尤为重要。

## 依赖关系

- **include/core/SkRefCnt.h**: `sk_sp` 智能指针
- **include/core/SkSpan.h**: `SkSpan` 视图类型
- 前向声明: `PrecompileColorFilter`, `SkColorSpace`
- 隐式依赖: `skcms_TransferFunction`, `skcms_Matrix3x3`, `SkAlphaType`

## 设计模式与设计决策

### 与运行时 API 的镜像对应

文件注释明确指出这三个工厂函数与 `src/core/SkColorFilterPriv.h` 中的工厂一一对应。这种镜像设计确保了预编译覆盖范围与运行时实际使用的效果完全匹配。

### 参数化颜色空间

`ColorSpaceXform` 接受颜色空间列表而非单个颜色空间，允许一次调用覆盖多种颜色空间组合。这减少了预编译 API 的调用次数。

## 性能考量

- 颜色空间变换的组合数 = |src| x |dst|，可能产生大量管线变体
- 工厂函数仅创建预编译描述对象，不执行实际编译
- 实际管线编译在 `PaintOptions::buildCombinations()` 中延迟发生

## 相关文件

- `src/core/SkColorFilterPriv.h` - 运行时内部颜色滤镜工厂
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` - PrecompileColorFilter 基类
- `src/gpu/graphite/precompile/PaintOptionsPriv.h` - PaintOptions 内部（调用 addColorFilter）
- `include/gpu/graphite/precompile/PrecompileColorFilter.h` - 公共颜色滤镜工厂
