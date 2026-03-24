# SkPerlinNoiseShader - Perlin 噪声着色器

> 源文件: `src/shaders/SkPerlinNoiseShaderImpl.h`, `src/shaders/SkPerlinNoiseShaderImpl.cpp`

## 概述

SkPerlinNoiseShader 实现了 SVG 规范中的 feTurbulence 滤镜效果，支持两种噪声类型：分形噪声（Fractal Noise）和湍流（Turbulence）。该着色器基于 Perlin 噪声算法，通过多个八度（octave）叠加生成程序化的噪声图案，广泛用于生成自然纹理效果如云彩、大理石、木纹等。

实现严格遵循 W3C SVG 1.1 规范中 feTurbulence 元素的定义，包括随机数生成器、梯度生成、以及可选的平铺缝合（stitching）功能。

## 架构位置

```
SkShader (公共接口)
  └── SkShaderBase (内部基类)
        └── SkPerlinNoiseShader (Perlin 噪声着色器)
```

- **公共 API**: `SkShaders::MakeFractalNoise()`, `SkShaders::MakeTurbulence()`
- **管线集成**: 通过 `SkRasterPipelineOp::perlin_noise` 阶段执行
- **GPU 后端**: Graphite/Ganesh 通过 `ShaderType::kPerlinNoise` 识别并生成对应 SkSL 代码

## 主要类与结构体

### SkPerlinNoiseShader
核心着色器类，存储噪声参数并管理渲染数据。

**关键成员变量**:
- `fType` — 噪声类型（FractalNoise 或 Turbulence）
- `fBaseFrequencyX / fBaseFrequencyY` — X/Y 方向的基础频率
- `fNumOctaves` — 八度数量（0-255）
- `fSeed` — 随机种子
- `fTileSize` — 平铺大小（非空时启用缝合模式）
- `fStitchTiles` — 是否启用平铺缝合

### StitchData
平铺缝合参数，存储宽度、高度及对应的包裹值，确保噪声在平铺边界处连续。

### PaintingData
噪声生成的核心数据结构，包含：
- `fLatticeSelector[256]` — 晶格选择器排列表
- `fNoise[4][256][2]` — 四通道噪声梯度数据（归一化后存储为 uint16）
- `fBaseFrequency` — 实际使用的基频（缝合后可能调整）
- `fStitchDataInit` — 缝合初始数据
- 位图形式的排列和噪声数据（用于 GPU 纹理访问）

## 公共 API 函数

```cpp
// 创建分形噪声着色器
sk_sp<SkShader> SkShaders::MakeFractalNoise(
    SkScalar baseFrequencyX, SkScalar baseFrequencyY,
    int numOctaves, SkScalar seed, const SkISize* tileSize);

// 创建湍流着色器
sk_sp<SkShader> SkShaders::MakeTurbulence(
    SkScalar baseFrequencyX, SkScalar baseFrequencyY,
    int numOctaves, SkScalar seed, const SkISize* tileSize);
```

当 `numOctaves == 0` 时的特殊优化：
- FractalNoise 退化为透明灰色（0.5, 0.5, 0.5, 0.5）
- Turbulence 退化为全透明

### 实例方法
- `noiseType()` — 返回噪声类型
- `numOctaves()` — 返回八度数
- `stitchTiles()` — 是否缝合平铺
- `tileSize()` — 返回平铺大小
- `getPaintingData()` — 创建 PaintingData 实例

## 内部实现细节

### 随机数生成器
遵循 SVG 规范，使用线性同余生成器：
- 模数 m = 2^31 - 1 (2147483647)
- 乘数 a = 7^5 (16807)
- 使用 Schrage 方法避免溢出

### 噪声数据初始化（PaintingData::init）
1. 种子值被截断为整数并夹紧到 [1, m-1]
2. 生成 256 个晶格选择器和 4 通道 x 2 方向的随机数
3. Fisher-Yates 洗牌算法打乱晶格选择器
4. 对噪声数据执行基于晶格选择器的排列
5. 将随机值转换为归一化梯度向量，存储为 uint16 格式

### 平铺缝合（PaintingData::stitch）
调整基频使其与平铺大小对齐，确保噪声在平铺边界处无缝衔接。选择最接近原始频率的调整后频率。

### 光栅化管线集成
`appendStages` 方法使用 `SkOnce` 确保 PaintingData 仅初始化一次（线程安全的延迟初始化），然后将所有噪声参数打包到 `PerlinNoiseCtx` 中传递给 `perlin_noise` 管线阶段。

## 依赖关系

- `SkShaderBase` — 着色器基类
- `SkRasterPipeline` — 光栅化管线（perlin_noise 操作）
- `SkPerlinNoiseShaderType` — 噪声类型枚举
- `SkReadBuffer` / `SkWriteBuffer` — 序列化支持
- `SkOnce` — 线程安全的一次性初始化

## 设计模式与设计决策

1. **延迟初始化**: PaintingData 在首次使用时才计算，通过 `SkOnce` 保证线程安全
2. **SVG 兼容性**: 严格遵循 W3C SVG 1.1 feTurbulence 规范
3. **编译时断言**: `static_assert(kBlockSize == 256)` 确保与 SkSL 和 Graphite 后端的一致性
4. **0 八度优化**: numOctaves=0 时直接返回常量颜色着色器，避免不必要的计算
5. **kMaxOctaves = 255**: 限制八度数上限，防止过度计算

## 性能考量

- 噪声数据预计算并缓存，避免每像素重复生成
- PaintingData 的位图形式用于 GPU 纹理查找，避免 CPU 端逐像素计算
- 八度数直接影响性能，每增加一个八度计算量翻倍
- 缝合模式增加额外的取模运算开销

### 噪声类型差异

FractalNoise 和 Turbulence 的主要区别在于噪声值的后处理：
- **FractalNoise**: 每个八度的噪声值直接累加后偏移，结果范围 [-1,1] 映射到 [0,1]，可产生负值
- **Turbulence**: 每个八度取噪声的绝对值后累加，结果始终非负，产生更尖锐的纹理边缘

两者共享相同的底层梯度噪声生成和排列表。

### PerlinNoiseCtx 字段说明

传递给光栅化管线的上下文包含：
- `noiseType` — 噪声类型枚举
- `baseFrequencyX/Y` — 实际基频（可能经过缝合调整）
- `stitchDataInX/Y` — 缝合数据的宽度和高度
- `stitching` — 是否启用缝合
- `numOctaves` — 八度数
- `latticeSelector` — 指向 256 字节排列表的指针
- `noiseData` — 指向 4x256x2 噪声梯度数据的指针

### 常量说明

- `kBlockSize = 256` — 排列表和噪声数据的大小
- `kBlockMask = 255` — 用于模运算的掩码
- `kPerlinNoise = 4096` — 缝合参数的基础值
- `kRandMaximum = 2^31 - 1` — 随机数生成器的模数
- `kMaxOctaves = 255` — 八度数上限

### 输入验证

`valid_input` 函数检查：
- 基频非负
- 八度数在 [0, 255] 范围内
- 平铺大小（如果提供）非负
- 种子值有限

### Flattenable 兼容性

注册时同时使用当前名称 "SkPerlinNoiseShader" 和旧名称 "SkPerlinNoiseShaderImpl"，确保旧版 SKP 文件的兼容性。

## 相关文件

- `include/effects/SkPerlinNoiseShader.h` — 公共 API 头文件
- `src/shaders/SkPerlinNoiseShaderType.h` — 噪声类型枚举定义
- `src/core/SkRasterPipelineOpContexts.h` — PerlinNoiseCtx 定义
- `src/core/SkRasterPipelineOpList.h` — perlin_noise 操作定义
- `src/shaders/SkShaderBase.h` — 着色器基类
