# SkPerlinNoiseShaderType — Perlin 噪声着色器类型枚举

> 源文件: `src/shaders/SkPerlinNoiseShaderType.h`

## 概述

`SkPerlinNoiseShaderType.h` 定义了 Perlin 噪声着色器所支持的噪声类型枚举。Perlin 噪声是计算机图形学中广泛使用的程序化纹理生成算法，常用于创建自然界中的随机纹理效果（如云彩、大理石、火焰等）。

该枚举区分了两种噪声变体：
- **分形噪声（Fractal Noise）**: 产生平滑、柔和的噪声效果
- **湍流（Turbulence）**: 产生更锐利、对比更强的噪声效果

两种类型的底层噪声生成算法相同，仅在输出映射阶段有所不同。

## 架构位置

```
Skia
└── src/shaders/
    ├── SkPerlinNoiseShaderType.h       // 本文件：类型枚举
    ├── SkPerlinNoiseShaderImpl.h       // Perlin 噪声着色器实现
    └── SkPerlinNoiseShaderImpl.cpp     // Perlin 噪声着色器实现
```

该枚举被 Perlin 噪声着色器的实现和公共 API 引用，定义了噪声的输出特性。

## 主要类与结构体

### `enum class SkPerlinNoiseShaderType`

```cpp
enum class SkPerlinNoiseShaderType { kFractalNoise, kTurbulence, kLast = kTurbulence };
```

| 值 | 输出映射 | 视觉效果 |
|----|---------|---------|
| `kFractalNoise` | `noise * 0.5 + 0.5` | 平滑，值在 [0, 1] 范围内均匀分布，包含正负变化 |
| `kTurbulence` | `abs(noise)` | 锐利，所有值为正，纹理褶皱更明显 |
| `kLast` | 等同于 `kTurbulence` | 哨兵值，用于枚举遍历或验证 |

## 公共 API 函数

本文件不包含函数，仅定义枚举类型。

## 内部实现细节

### 噪声映射差异

两种噪声类型共享相同的基础 Perlin 噪声算法，噪声原始值在 [-1, 1] 范围内。区别仅在于最后一步如何将其映射到 [0, 1] 范围：

- **分形噪声**: `output = noise * 0.5 + 0.5` — 线性映射，保留了噪声的正负对称性，结果看起来像柔和的云彩
- **湍流**: `output = abs(noise)` — 取绝对值，原本的零交叉点变成了锐利的"褶皱"，结果看起来像翻涌的烟雾或火焰

### `kLast` 哨兵值

`kLast = kTurbulence` 是 Skia 枚举中的常见模式，用于：
- 运行时验证枚举值的有效性（`SkASSERT(type <= kLast)`）
- 枚举遍历
- 序列化/反序列化时的范围检查

## 依赖关系

本文件无外部依赖，是一个纯定义文件。

## 设计模式与设计决策

1. **强类型枚举**: 使用 `enum class` 而非 `enum`，提供类型安全性
2. **算法统一**: 两种噪声类型共享底层算法，仅通过输出映射区分，简化了实现
3. **独立头文件**: 将枚举单独放在一个头文件中，减少编译依赖——需要引用噪声类型的代码无需引入整个着色器实现
4. **哨兵值模式**: `kLast` 遵循 Skia 的枚举设计规范

## 性能考量

- 枚举值在编译时确定，运行时无开销
- 噪声类型的差异仅影响最终映射步骤，不影响核心噪声生成的性能

## 相关文件

- `src/shaders/SkPerlinNoiseShaderImpl.h` — Perlin 噪声着色器实现
- `src/shaders/SkPerlinNoiseShaderImpl.cpp` — Perlin 噪声着色器实现
- `include/effects/SkPerlinNoiseShader.h` — 公共 API
