# PrecompileImageShader - 图像着色器预编译实现

> 源文件: `src/gpu/graphite/precompile/PrecompileImageShader.h`

## 概述

`PrecompileImageShader` 是 Skia Graphite 预编译系统中用于图像着色器（Image Shader）管线预编译的具体实现类。图像着色器是最常用的着色器类型之一，用于将位图/纹理绘制到画布上。该类处理图像采样的各种变体，包括不同的颜色空间变换、平铺模式、采样方式（硬件平铺、立方体滤波等），以及对不可变采样器（用于 YCbCr 视频纹理等）的支持。

## 架构位置

```
预编译着色器层次
  ├── PrecompileShader (基类)
  │     └── PrecompileImageShader (本文件 - 图像着色器实现)
  │           ├── 颜色空间变换变体
  │           ├── 平铺模式变体
  │           ├── 采样模式变体 (HW Tiled / Cubic)
  │           └── 不可变采样器支持
  └── PrecompileYUVImageShader (YUV 图像着色器, 友元类)
```

## 主要类与结构体

### `PrecompileImageShader`

继承自 `PrecompileShader`，是 `final` 类。

**核心成员变量**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fNumExtraSamplingTilingCombos` | `const int` | 额外采样/平铺组合数 |
| `fColorInfos` | `const vector<SkColorInfo>` | 颜色信息列表 |
| `fTileModes` | `const vector<SkTileMode>` | 平铺模式列表 |
| `fUseDstColorInfo` | `const bool` | 是否使用目标颜色信息 |
| `fRaw` | `const bool` | 是否为原始图像着色器 |
| `fImmutableSamplerInfo` | `ImmutableSamplerInfo` | 不可变采样器信息 |

## 公共 API 函数

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `PrecompileImageShader(flags, colorInfos, tileModes, raw)` | 构造函数 | 从标志、颜色信息、平铺模式和原始模式创建 |
| `setImmutableSamplerInfo(const ImmutableSamplerInfo&)` | `void` | 设置不可变采样器信息 |

### 重写的虚方法

| 方法 | 说明 |
|------|------|
| `numIntrinsicCombinations()` | 返回本层固有组合数 |
| `addToKey(const KeyContext&, int)` | 将指定组合添加到管线键 |

## 内部实现细节

### 默认颜色信息系统

该类定义了一套精心设计的默认 `SkColorInfo` 列表，用于覆盖所有可能的颜色空间变换着色器变体（假设目标为 sRGB）：

| 静态方法 | 颜色类型 | Alpha | 颜色空间 | 对应的变换着色器 |
|----------|----------|-------|----------|------------------|
| `DefaultColorInfoPremul()` | RGBA_8888 | Premul | sRGB | 最特化（无实际变换） |
| `DefaultColorInfoSRGB()` | RGBA_8888 | Premul | sRGB (ColorSpin) | sRGB-to-sRGB 特化 |
| `DefaultColorInfoGeneral()` | RGBA_8888 | Premul | sRGBLinear | 通用颜色空间变换 |
| `DefaultColorInfoAlphaOnly()` | Alpha_8 | Premul | sRGBLinear | Alpha-only 通用变换 |

不同的组合列表：
- `DefaultColorInfos()`: 全部 4 种（完整覆盖）
- `NonAlphaOnlyDefaultColorInfos()`: 前 3 种（被 YUV 着色器使用）
- `RawImageDefaultColorInfos()`: Premul + AlphaOnly（原始图像模式）

### 额外采样/平铺组合

除了用户指定的平铺模式，还预编译两种额外变体：
- **`kHWTiled` (索引 0)**: 硬件平铺模式，使用 GPU 采样器原生平铺
- **`kCubicSampled` (索引 1)**: 立方体采样模式，始终使用最通用的平铺着色器

```cpp
inline static constexpr int kExtraNumSamplingTilingCombos = 2;
```

### 目标颜色信息决策

`fUseDstColorInfo` 控制颜色空间变换的目标侧行为：
- **true**: 使用 `KeyContext` 提供的实际目标颜色信息（客户端指定了颜色信息列表时）
- **false**: 始终假设 sRGB 目标，并使用源图像的 alphaType

### 原始图像模式

当 `fRaw = true` 时，跳过大部分颜色空间变换，但 Alpha-only 图像仍需要通用变换着色器（因为读取重排通过色域变换矩阵实现）。

### 不可变采样器

`setImmutableSamplerInfo()` 用于 Vulkan 上的外部格式纹理（如 Android AHardwareBuffer 的 YCbCr 视频帧）。不可变采样器在管线创建时绑定，不能在运行时更改。

## 依赖关系

- **include/gpu/graphite/precompile/PrecompileShader.h**: 基类
- **src/core/SkColorSpacePriv.h**: `sk_srgb_singleton()` 等颜色空间工具
- **src/gpu/graphite/ResourceTypes.h**: `ImmutableSamplerInfo` 类型

## 设计模式与设计决策

### 组合爆炸控制

图像着色器的变体空间很大（颜色信息 x 平铺模式 x 采样模式）。该类通过以下策略控制组合数：
1. 使用精选的默认颜色信息列表（仅 3-4 种）覆盖所有着色器变体
2. 额外采样组合固定为 2 种
3. 允许客户端通过构造函数参数精确控制覆盖范围

### 友元访问

`PrecompileYUVImageShader` 被声明为友元，以访问 `NonAlphaOnlyDefaultColorInfos()`。这避免了将内部默认列表公开，同时允许 YUV 着色器复用相同的颜色信息策略。

### 不变性设计

除 `fImmutableSamplerInfo` 外，所有成员变量都是 `const`。这确保了构造后对象状态不可变，线程安全且易于推理。`setImmutableSamplerInfo()` 是唯一的例外，因为采样器信息可能在对象创建后才确定。

## 性能考量

- 默认颜色信息列表在编译时或首次调用时确定，无运行时查询开销
- 组合数 = |colorInfos| x (|tileModes| + kExtraNumSamplingTilingCombos)，通常在 10-20 范围内
- 所有静态方法返回 `std::vector` 值类型，可被 RVO 优化
- `final` 类标记允许编译器对虚函数调用进行去虚化优化

## 相关文件

- `include/gpu/graphite/precompile/PrecompileShader.h` - PrecompileShader 基类
- `include/gpu/graphite/precompile/PrecompileShaders.h` - 公共着色器工厂
- `src/gpu/graphite/precompile/PrecompileShaderPriv.h` - Shader Priv 访问
- `src/gpu/graphite/ResourceTypes.h` - ImmutableSamplerInfo 定义
- `src/core/SkColorSpacePriv.h` - 颜色空间工具
