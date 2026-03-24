# SkPerlinNoiseShader

> 源文件: `include/effects/SkPerlinNoiseShader.h`

## 概述

`SkPerlinNoiseShader` 提供了基于 **Perlin 噪声** 算法的着色器创建接口，用于生成程序化噪声纹理。该模块在 `SkShaders` 命名空间中实现了 SVG 规范中 `feTurbulence` 滤镜元素所定义的两种噪声类型：

1. **分形噪声（Fractal Noise）**: 产生平滑、连续的噪声图案，适合模拟云雾、大理石等自然纹理
2. **湍流（Turbulence）**: 产生更具对比度的噪声图案，适合模拟火焰、水面波纹等动态效果

两种噪声类型都支持以下核心参数：
- **基础频率（Base Frequency）**: 控制噪声图案的尺度，分别可在 X 和 Y 方向独立设置
- **八度数（Octaves）**: 控制噪声的细节层次，每增加一个八度频率翻倍
- **种子（Seed）**: 伪随机数种子，相同种子产生相同的噪声图案
- **平铺尺寸（Tile Size）**: 可选参数，使噪声图案可无缝平铺

Perlin 噪声广泛应用于计算机图形学中，用于模拟自然界中的各种不规则纹理（如云彩、大理石、木纹、火焰等）。该算法的参考实现基于 W3C SVG 规范：http://www.w3.org/TR/SVG/filters.html#feTurbulenceElement

## 架构位置

`SkPerlinNoiseShader` 的公共 API 定义在 `SkShaders` 命名空间中，是 Skia 着色器体系的一部分：

```
应用层 / SVG 渲染器
  │
  ▼
┌───────────────────────────────────────────────┐
│  include/effects/SkPerlinNoiseShader.h         │
│  namespace SkShaders {                         │
│    MakeFractalNoise()  ──┐                     │  ◄── 公共 API（本文件）
│    MakeTurbulence()    ──┤                     │
│  }                       │                     │
└──────────────────────────┼─────────────────────┘
                           │ 创建
                           ▼
┌───────────────────────────────────────────────┐
│  src/shaders/SkPerlinNoiseShaderImpl.h/.cpp    │  ◄── 内部实现
│  class SkPerlinNoiseShader : public SkShaderBase│
│    ├── fType (Fractal / Turbulence)            │
│    ├── fBaseFrequencyX/Y                       │
│    ├── fNumOctaves                             │
│    ├── fSeed                                   │
│    └── fTileSize / fStitchTiles                │
└──────────────────────────┬────────────────────┘
                           │ 渲染
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     CPU Raster       Ganesh GPU      Graphite GPU
     Pipeline        GrPerlinNoise    (precompile)
                      2Effect
```

与其他 Skia 效果类不同，`SkPerlinNoiseShader` 的公共 API 使用了 `SkShaders` **命名空间下的自由函数**而非类的静态方法，这体现了 Skia API 向现代 C++ 命名空间风格的演进。

- **上游调用者**: SVG 渲染引擎（`modules/svg/src/SkSVGFeTurbulence.cpp`）、需要程序化噪声纹理的应用程序、CanvasKit WebAssembly 绑定。
- **下游依赖**: `SkShader` 着色器框架，最终在 CPU 或 GPU 渲染管线中执行。

## 主要类与结构体

### `SkShaders` 命名空间中的工厂函数

公共 API 以命名空间中的自由函数形式提供，不在此头文件中定义新的类：

```cpp
namespace SkShaders {
    SK_API sk_sp<SkShader> MakeFractalNoise(...);
    SK_API sk_sp<SkShader> MakeTurbulence(...);
}
```

### 内部实现类 `SkPerlinNoiseShader`（非公共 API）

虽然不在此头文件中声明，但了解内部实现有助于理解整体设计。该类定义于 `src/shaders/SkPerlinNoiseShaderImpl.h`：

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fType` | `SkPerlinNoiseShaderType` | 噪声类型（分形噪声或湍流） |
| `fBaseFrequencyX` | `SkScalar` | X 方向基础频率 |
| `fBaseFrequencyY` | `SkScalar` | Y 方向基础频率 |
| `fNumOctaves` | `int` | 八度数（上限 255，即 `kMaxOctaves`） |
| `fSeed` | `SkScalar` | 随机种子 |
| `fTileSize` | `SkISize` | 平铺尺寸 |
| `fStitchTiles` | `bool` | 是否启用平铺缝合（由 tileSize 是否为空自动推断） |

内部还定义了关键常量 `kBlockSize = 256`，用于梯度向量表的大小。该常量在 SkSL 着色器实现和 Graphite 后端中也需要保持一致。

## 公共 API 函数

### `SkShaders::MakeFractalNoise()`

```cpp
SK_API sk_sp<SkShader> MakeFractalNoise(
    SkScalar baseFrequencyX,
    SkScalar baseFrequencyY,
    int numOctaves,
    SkScalar seed,
    const SkISize* tileSize = nullptr);
```

**功能**: 创建一个生成分形噪声的着色器。分形噪声的各八度分量以有符号形式叠加，产生平滑、柔和的噪声效果。

**参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `baseFrequencyX` | `SkScalar` | X 方向基础频率，通常范围 (0, 1)，必须非负 |
| `baseFrequencyY` | `SkScalar` | Y 方向基础频率，通常范围 (0, 1)，必须非负 |
| `numOctaves` | `int` | 噪声八度数，范围 [0, 255]，推荐使用较小值（4-6） |
| `seed` | `SkScalar` | 伪随机种子值，不同种子产生不同的噪声图案 |
| `tileSize` | `const SkISize*` | 可选的平铺尺寸，为 nullptr 或空尺寸时不启用平铺 |

**返回值**: `sk_sp<SkShader>` -- 分形噪声着色器。

### `SkShaders::MakeTurbulence()`

```cpp
SK_API sk_sp<SkShader> MakeTurbulence(
    SkScalar baseFrequencyX,
    SkScalar baseFrequencyY,
    int numOctaves,
    SkScalar seed,
    const SkISize* tileSize = nullptr);
```

**功能**: 创建一个生成湍流噪声的着色器。湍流噪声取各八度分量的绝对值后叠加，产生更具对比度和锐利边缘的噪声效果。

**参数**: 与 `MakeFractalNoise()` 完全一致。

**返回值**: `sk_sp<SkShader>` -- 湍流噪声着色器。

**两种噪声类型的对比**:

| 特性 | 分形噪声 (Fractal Noise) | 湍流 (Turbulence) |
|------|--------------------------|-------------------|
| 叠加方式 | 直接叠加有符号值 | 取绝对值后叠加 |
| 视觉效果 | 平滑、连续 | 对比度强、锐利 |
| 适用场景 | 云雾、水面、大理石 | 火焰、石材纹理、波纹 |
| 值域范围 | 约 [-1, 1] | 约 [0, 1] |

### 使用示例

```cpp
#include "include/effects/SkPerlinNoiseShader.h"
#include "include/core/SkPaint.h"

// 创建分形噪声着色器
SkPaint fractalPaint;
fractalPaint.setShader(
    SkShaders::MakeFractalNoise(
        0.05f,   // X 基础频率
        0.05f,   // Y 基础频率
        4,       // 4 个八度
        0.0f     // 种子
    )
);
canvas->drawRect(SkRect::MakeWH(256, 256), fractalPaint);

// 创建可平铺的湍流噪声着色器
SkISize tileSize = SkISize::Make(128, 128);
SkPaint turbPaint;
turbPaint.setShader(
    SkShaders::MakeTurbulence(
        0.1f, 0.1f, 3, 42.0f, &tileSize
    )
);
canvas->drawRect(SkRect::MakeWH(512, 512), turbPaint);
```

## 内部实现细节

### 噪声生成算法

Perlin 噪声的核心算法包含以下步骤：

1. **梯度向量生成**: 使用种子值初始化一个伪随机梯度场，包含 `kBlockSize (256)` 个梯度向量
2. **插值计算**: 对于每个像素坐标，在相邻梯度向量之间进行双线性插值
3. **多八度叠加**: 将多个不同频率的噪声层叠加在一起：
   - 每个八度的频率为前一个八度的两倍
   - 每个八度的振幅为前一个八度的一半
4. **分形 vs 湍流差异**:
   - 分形噪声：直接叠加各八度值
   - 湍流：叠加各八度值的绝对值

### 平铺缝合（Tile Stitching）

当提供了非空的 `tileSize` 时：
- 算法会调整频率值使其为平铺尺寸的整数倍，确保噪声图案在边界处无缝衔接
- 内部通过 `fStitchTiles` 标志（由 `!fTileSize.isEmpty()` 自动推断）控制是否启用
- 这对于需要大面积重复填充的场景非常重要；不启用平铺时，重复绘制会在拼接处出现可见的接缝

### 构造函数中的参数校验

```cpp
SkPerlinNoiseShader::SkPerlinNoiseShader(...) {
    SkASSERT(numOctaves >= 0 && numOctaves <= kMaxOctaves);
    SkASSERT(fBaseFrequencyX >= 0);
    SkASSERT(fBaseFrequencyY >= 0);
    // kBlockSize 必须为 256，与 SkSL 实现和 Graphite 后端保持一致
    static_assert(SkPerlinNoiseShader::kBlockSize == 256);
}
```

八度数在构造时会被截断到 `[0, kMaxOctaves]` 范围，基础频率必须非负。

### 序列化支持

内部实现类继承自 `SkFlattenable`，支持通过 `SkReadBuffer` / `SkWriteBuffer` 进行序列化和反序列化，使得噪声着色器可以被保存到 `SkPicture` 中。序列化时会写入噪声类型、频率、八度数、种子和平铺尺寸等全部参数。

## 依赖关系

### 直接依赖

| 依赖文件 | 用途 |
|----------|------|
| `include/core/SkRefCnt.h` | 提供 `sk_sp` 智能指针 |
| `include/core/SkScalar.h` | 提供 `SkScalar` 类型（`float`） |
| `include/core/SkShader.h` | 提供 `SkShader` 基类（IWYU pragma: keep） |
| `include/private/base/SkAPI.h` | 提供 `SK_API` 导出宏 |
| `SkISize` (前向声明) | 平铺尺寸参数类型 |

### 实现依赖

| 依赖文件 | 用途 |
|----------|------|
| `src/shaders/SkPerlinNoiseShaderImpl.h` | 内部实现类声明 |
| `src/shaders/SkPerlinNoiseShaderImpl.cpp` | 噪声生成核心算法实现 |
| `src/shaders/SkPerlinNoiseShaderType.h` | 噪声类型枚举定义 |
| `src/gpu/ganesh/effects/GrPerlinNoise2Effect.cpp` | Ganesh GPU 后端实现 |
| `src/gpu/graphite/precompile/PrecompileShader.cpp` | Graphite 后端预编译支持 |

### 被依赖关系

- `modules/svg/src/SkSVGFeTurbulence.cpp` -- SVG `feTurbulence` 滤镜实现
- `modules/canvaskit/canvaskit_bindings.cpp` -- CanvasKit WebAssembly 绑定
- `tests/ShaderTest.cpp` -- 着色器测试
- `tests/BlurTest.cpp`、`tests/ImageFilterTest.cpp` -- 其他相关测试

## 设计模式与设计决策

### 命名空间工厂函数

`SkPerlinNoiseShader` 的公共 API 使用 `SkShaders` 命名空间下的自由函数，而非传统的类静态方法。这种设计：

- 使 API 更加扁平化，调用方式为 `SkShaders::MakeFractalNoise(...)` 而非 `SkPerlinNoiseShader::MakeFractalNoise(...)`
- 与 Skia 其他着色器工厂函数（如 `SkShaders::Color()`, `SkShaders::Blend()`）保持一致
- 符合现代 C++ 的 ADL（Argument-Dependent Lookup）友好设计
- 历史上的 `SkPerlinNoiseShader` 类名仅保留在头文件名和文档注释中

### 两种噪声类型的统一参数

`MakeFractalNoise()` 和 `MakeTurbulence()` 使用完全相同的参数签名，仅在内部的叠加方式上不同。这简化了 API 设计，让用户可以轻松在两种噪声类型间切换。

### 可选的平铺支持

平铺尺寸参数设计为可选的指针类型（`const SkISize*`），默认为 `nullptr`。这种设计：
- 对不需要平铺的常见用例保持了 API 的简洁性
- 避免了使用特殊的"空"尺寸值作为标志
- 内部通过 `fTileSize.isEmpty()` 自动推断是否需要频率调整

### 八度数量限制

硬限制为 255（`kMaxOctaves`），防止因过多八度导致的计算资源浪费。头文件注释建议使用较小值，因为超过约 10 个八度后高频分量不可分辨，效果退化为普通随机噪声。

### SVG 规范兼容性

该实现严格遵循 W3C SVG `feTurbulence` 规范，确保在 SVG 渲染场景中产生与规范一致的结果。

## 性能考量

- **八度数与计算量**: 计算量与 `numOctaves` 成线性关系。建议在视觉效果满足需求的前提下使用尽可能少的八度数（通常 3-5 个即可）
- **频率选择**: 过高的基础频率会导致噪声图案接近随机噪点，既无视觉意义也浪费计算资源
- **GPU 加速**: 在 Ganesh 后端中，Perlin 噪声通过 `GrPerlinNoise2Effect` 片段处理器在 GPU 上并行计算，比 CPU 路径显著更快
- **内存占用**: 噪声着色器需要维护梯度向量表（基于 `kBlockSize = 256`），占用约 2KB 的内存
- **平铺模式的开销**: 启用平铺缝合会引入额外的频率调整计算，但这只在着色器创建时进行一次，不影响逐像素的渲染性能
- **平铺噪声的内存效率**: 使用可平铺噪声时，只需渲染一个平铺单元就可以通过重复绘制覆盖任意大小的区域，节省了存储大型噪声纹理的内存
- **缓存友好性**: Raster Pipeline 中的噪声计算按扫描线顺序执行，具有较好的空间局部性

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| `include/effects/SkPerlinNoiseShader.h` | 本文件，公共 API 声明 |
| `src/shaders/SkPerlinNoiseShaderImpl.h` | 内部实现类声明 |
| `src/shaders/SkPerlinNoiseShaderImpl.cpp` | 噪声生成核心算法实现 |
| `src/shaders/SkPerlinNoiseShaderType.h` | 噪声类型枚举（Fractal / Turbulence） |
| `src/gpu/ganesh/effects/GrPerlinNoise2Effect.cpp` | Ganesh GPU 后端的噪声效果实现 |
| `src/gpu/graphite/precompile/PrecompileShader.cpp` | Graphite 后端预编译支持 |
| `modules/svg/src/SkSVGFeTurbulence.cpp` | SVG `feTurbulence` 滤镜元素实现 |
| `include/core/SkShader.h` | `SkShader` 基类定义 |
| `tests/ShaderTest.cpp` | 着色器相关测试 |
