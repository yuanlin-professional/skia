# GrPerlinNoise2Effect

> 源文件: src/gpu/ganesh/effects/GrPerlinNoise2Effect.h, src/gpu/ganesh/effects/GrPerlinNoise2Effect.cpp

## 概述

`GrPerlinNoise2Effect` 是 Ganesh GPU 后端中实现 Perlin 噪声效果的片段处理器。Perlin 噪声是计算机图形学中广泛使用的程序化纹理生成技术，用于创建自然的随机模式，如云彩、大理石纹理、波浪等。该模块实现了两种噪声类型：分形噪声（Fractal Noise）和湍流噪声（Turbulence），支持多八度音阶叠加和瓦片拼接。

该效果基于 Ken Perlin 的经典噪声算法，通过在 GPU 上计算多个频率的噪声叠加来生成复杂的自然模式。核心思想是从两个预计算的纹理（排列纹理和噪声梯度纹理）中采样，通过插值和叠加生成最终的噪声值。支持可配置的频率、八度音数量、以及瓦片无缝拼接功能。

## 架构位置

`GrPerlinNoise2Effect` 位于 Skia GPU 渲染架构的片段处理器效果层：

- **层级**: GPU 渲染后端 -> Ganesh 引擎 -> 片段处理器
- **模块**: `src/gpu/ganesh/effects/`
- **功能定位**: 程序化纹理生成，实现 Perlin 噪声算法
- **渲染管线位置**: 片段着色阶段，直接生成噪声颜色
- **应用场景**: 特效着色器、程序化纹理、自然现象模拟

该模块与 `SkPerlinNoiseShader` 紧密集成，是 Skia 着色器系统在 GPU 后端的实现。

## 主要类与结构体

### GrPerlinNoise2Effect 类

**继承关系**:
```
GrFragmentProcessor (基类)
    └── GrPerlinNoise2Effect
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fType` | `SkPerlinNoiseShaderType` | 噪声类型（分形或湍流） |
| `fNumOctaves` | `int` | 八度音数量（噪声叠加层数） |
| `fStitchTiles` | `bool` | 是否启用瓦片拼接 |
| `fPaintingData` | `std::unique_ptr<PaintingData>` | 噪声生成参数数据 |

**子处理器**:
- 子处理器 0: 排列纹理效果（permutations texture）
- 子处理器 1: 噪声梯度纹理效果（noise texture）

### SkPerlinNoiseShaderType 枚举

| 枚举值 | 说明 |
|--------|------|
| `kFractalNoise` | 分形噪声，值域 [0, 1]，适合云彩、烟雾 |
| `kTurbulence` | 湍流噪声，使用绝对值，适合大理石、湍流 |

### PaintingData 结构

存储噪声生成所需的参数（来自 `SkPerlinNoiseShader`）：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fBaseFrequency` | `SkVector` | 基础频率（X, Y 方向） |
| `fStitchDataInit` | `StitchData` | 瓦片拼接数据 |

### StitchData 结构

瓦片拼接参数：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fWidth` | `int` | 瓦片宽度 |
| `fHeight` | `int` | 瓦片高度 |

### Impl 内部类

着色器实现类：

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fStitchDataUni` | `UniformHandle` | 拼接数据 Uniform |
| `fBaseFrequencyUni` | `UniformHandle` | 基础频率 Uniform |

## 公共 API 函数

### Make 工厂函数

```cpp
static std::unique_ptr<GrFragmentProcessor> Make(
    SkPerlinNoiseShaderType type,
    int numOctaves,
    bool stitchTiles,
    std::unique_ptr<SkPerlinNoiseShader::PaintingData> paintingData,
    GrSurfaceProxyView permutationsView,
    GrSurfaceProxyView noiseView,
    const GrCaps& caps);
```

**功能**: 创建 Perlin 噪声片段处理器。

**参数说明**:
- `type`: 噪声类型（分形或湍流）
- `numOctaves`: 八度音数量（通常 2-10，越多越细腻但越慢）
- `stitchTiles`: 是否启用瓦片无缝拼接
- `paintingData`: 包含基础频率和拼接数据的参数对象
- `permutationsView`: 排列纹理视图（用于伪随机采样）
- `noiseView`: 噪声梯度纹理视图（存储预计算的梯度向量）
- `caps`: GPU 能力查询接口

**纹理采样器配置**:
- X 轴: `kRepeat` 重复模式
- Y 轴: `kClamp` 钳制模式
- 过滤: `kNearest` 最近邻过滤

**返回值**: 新创建的 Perlin 噪声片段处理器

### 访问器方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `name()` | `const char*` | 返回 `"PerlinNoise"` |
| `type()` | `SkPerlinNoiseShaderType` | 获取噪声类型 |
| `numOctaves()` | `int` | 获取八度音数量 |
| `stitchTiles()` | `bool` | 是否启用拼接 |
| `baseFrequency()` | `const SkVector&` | 获取基础频率 |
| `stitchData()` | `const StitchData&` | 获取拼接数据 |

### clone

```cpp
std::unique_ptr<GrFragmentProcessor> clone() const override;
```

**功能**: 创建效果的深拷贝，包括 `PaintingData` 的拷贝。

## 内部实现细节

### Perlin 噪声算法

核心算法在 `emitHelper` 方法中实现，生成一个辅助函数用于计算单个噪声值。

**算法步骤**:

1. **坐标整数化**:
   ```glsl
   half4 floorVal;
   floorVal.xy = floor(noiseVec);  // 当前格子
   floorVal.zw = floorVal.xy + 1;  // 相邻格子
   half2 fractVal = fract(noiseVec);  // 格子内小数部分
   ```

2. **Hermite 插值准备**:
   ```glsl
   half2 noiseSmooth = smoothstep(0, 1, fractVal);  // t^2*(3 - 2*t)
   ```

3. **瓦片拼接处理**（可选）:
   ```glsl
   floorVal -= step(stitchData.xyxy, floorVal) * stitchData.xyxy;
   ```
   当坐标超过瓦片尺寸时回绕。

4. **排列纹理采样**:
   ```glsl
   // 从排列纹理获取两个伪随机索引
   latticeIdx = half2(permutations(floorVal.x).a, permutations(floorVal.z).a);
   ```

5. **梯度纹理采样**:
   ```glsl
   // 获取四个角的梯度向量
   half4 lattice_A = noise(bcoords.x, chanCoord);
   half4 lattice_B = noise(bcoords.y, chanCoord);
   half4 lattice_C = noise(bcoords.w, chanCoord);
   half4 lattice_D = noise(bcoords.z, chanCoord);
   ```

6. **点积计算**:
   ```glsl
   // 解包 16 位整数为 [-1, 1] 向量并与 fractVal 点积
   half u = dot((lattice.ga + lattice.rb * (1.0/256.0)) * 2 - 1, fractVal);
   ```

7. **双线性插值**:
   ```glsl
   half a = mix(u, v, noiseSmooth.x);  // X 方向插值
   half b = mix(u2, v2, noiseSmooth.x);
   return mix(a, b, noiseSmooth.y);  // Y 方向插值
   ```

### 八度音叠加

在 `emitCode` 方法中实现多层噪声叠加：

```glsl
half4 color = half4(0);
half ratio = 1.0;

for (int octave = 0; octave < numOctaves; ++octave) {
    // 计算四个通道的噪声
    color += half4(
        noiseFuncName(0.5, noiseVec),
        noiseFuncName(1.5, noiseVec),
        noiseFuncName(2.5, noiseVec),
        noiseFuncName(3.5, noiseVec)
    ) * ratio;

    noiseVec *= 2.0;  // 频率加倍
    ratio *= 0.5;      // 振幅减半

    if (stitchTiles) {
        stitchData *= 2.0;  // 拼接数据同步
    }
}
```

**分形噪声后处理**:
```glsl
// FractalNoise: 映射 [-1, 1] 到 [0, 1]
color = color * 0.5 + 0.5;
```

**湍流噪声处理**:
```glsl
// Turbulence: 使用绝对值
color += abs(noiseValue) * ratio;
```

### 四通道并行计算

每次噪声函数调用计算一个标量值，通过调用四次生成 RGBA 四个分量：

- `chanCoord = 0.5`: R 通道（噪声纹理第 0 行）
- `chanCoord = 1.5`: G 通道（噪声纹理第 1 行）
- `chanCoord = 2.5`: B 通道（噪声纹理第 2 行）
- `chanCoord = 3.5`: A 通道（噪声纹理第 3 行）

这种设计允许每个通道使用独立的梯度向量，生成不相关的噪声。

### 设备特定修复

针对 Tegra 设备的精度问题：

```glsl
if (caps.fPerlinNoiseRoundingFix) {
    latticeIdx = floor(latticeIdx * 255.0 + 0.5) * (1.0/255.0);
}
```

**原因**: Tegra GPU 纹理采样精度不足，导致 124/255 = 0.486275 被采样为 0.484368。通过四舍五入到 1/255 的倍数来修复。

### 坐标偏移

为了与 WebKit 的遗留行为兼容：

```glsl
half2 noiseVec = (sampleCoord + 0.5) * baseFrequency;
```

添加 0.5 偏移确保"相同"的噪声模式（尽管现在在局部空间而非设备空间）。

### 预乘 Alpha

最终输出预乘 alpha：

```glsl
return half4(color.rgb * color.a, color.a);
```

## 依赖关系

### 依赖的模块

| 模块 | 类型 | 用途 |
|------|------|------|
| `GrFragmentProcessor` | Ganesh 核心 | 片段处理器基类 |
| `GrTextureEffect` | Ganesh 效果 | 纹理采样（排列和噪声纹理） |
| `SkPerlinNoiseShader` | Skia 着色器 | 噪声着色器接口和数据结构 |
| `GrSurfaceProxyView` | Ganesh 纹理 | 纹理视图封装 |
| `GrSamplerState` | Ganesh 采样 | 纹理采样参数 |
| `GrGLSLFragmentShaderBuilder` | GLSL 生成 | 着色器代码构建 |
| `GrGLSLProgramDataManager` | GLSL 运行时 | Uniform 数据管理 |

### 被依赖的模块

| 模块 | 关系 | 用途 |
|------|------|------|
| `SkPerlinNoiseShader` | 上层接口 | 公共 API 着色器 |
| 特效系统 | 应用场景 | 实现各种自然纹理效果 |
| 滤镜管线 | 效果组合 | 与其他效果组合使用 |
| 背景渲染 | 常见用途 | 生成程序化背景 |
| 粒子系统 | 高级应用 | 驱动粒子运动和外观 |

## 设计模式与设计决策

### 纹理查找表

使用两个预计算纹理而非实时随机：

- **排列纹理**: 存储伪随机排列，用于生成梯度索引
- **噪声纹理**: 存储预计算的梯度向量（打包为 RGBA）

**优势**:
- **确定性**: 相同输入始终产生相同输出
- **性能**: 避免在着色器中计算伪随机数
- **质量**: 使用预选的高质量梯度向量

### 八度音叠加设计

每个八度音频率加倍、振幅减半：

- **分形特性**: 模拟自然界的自相似结构
- **细节层次**: 高频八度音添加精细细节
- **性能权衡**: 八度音数量可配置，平衡质量和性能

### 四通道分离

每个颜色通道独立计算噪声：

- **并行性**: 利用 GPU 的向量处理能力
- **不相关性**: 每个通道使用不同行的梯度向量
- **灵活性**: 支持彩色噪声和灰度噪声

### 瓦片拼接机制

通过坐标回绕实现无缝拼接：

```glsl
floorVal -= step(stitchData, floorVal) * stitchData;
```

**原理**: 当坐标达到瓦片边界时，减去瓦片尺寸使其回到 0。

**应用**: 创建可平铺的纹理，用于大面积填充。

### 类型特定处理

分形噪声和湍流噪声的差异：

- **分形**: 输出 `[0, 1]`，适合云彩、烟雾（柔和）
- **湍流**: 使用 `abs()`，适合大理石、波浪（锐利）

### 着色器键优化

键编码 (32 位):
- 低 3 位: 噪声类型 (1=分形, 2=湍流) + 拼接标志 (4)
- 高位: 八度音数量

```cpp
key = (numOctaves << 3) | typeFlag | stitchFlag;
```

**优势**: 紧凑编码，减少着色器变体数量。

## 性能考量

### 纹理采样开销

每个八度音每个通道采样 6 次纹理：
- 排列纹理: 2 次
- 噪声纹理: 4 次（四角）

**总采样次数**: `numOctaves * 4 * 6 = 24 * numOctaves`

**示例**: 5 个八度音 = 120 次纹理采样（极高开销）

### ALU 指令密度

- 点积计算
- 双线性插值
- Smoothstep 函数
- 向量解包和归一化

**估计**: 每个噪声值约 30-40 条 ALU 指令

### 八度音数量权衡

| 八度音数 | 质量 | 性能 | 适用场景 |
|----------|------|------|----------|
| 1-2 | 粗糙 | 快 | 实时背景 |
| 3-5 | 良好 | 中等 | 一般效果 |
| 6-10 | 优秀 | 慢 | 高质量渲染 |

### 瓦片拼接成本

启用拼接增加开销：
- 每个八度音额外的条件判断（`step`）
- 额外的 Uniform（`stitchData`）
- 更新拼接数据（`stitchData *= 2`）

**建议**: 仅在需要平铺时启用。

### 纹理缓存效率

- **重复采样**: X 轴重复，Y 轴钳制
- **局部性**: 相邻片段采样相近位置，缓存友好
- **纹理大小**: 典型 256x4 (排列) 和 256x4 (噪声)，占用约 4KB

### 寄存器压力

- 多个临时向量（`floorVal`, `fractVal`, `noiseSmooth` 等）
- 四次纹理采样结果
- 插值中间值

**估计**: 约 10-15 个向量寄存器（40-60 个标量）

### 着色器变体控制

仅基于八度音数量、类型和拼接生成变体：
- 典型变体数: 2 类型 × 2 拼接 × 9 八度音 = 36 个
- 相对较少，但每个变体指令数较多

### 批处理影响

- **Uniform 更新**: 频繁改变频率会打断批处理
- **纹理绑定**: 需要绑定两个纹理
- **着色器切换**: 改变八度音数量需要切换着色器

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 基类 | 片段处理器基类 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 依赖 | 纹理采样效果 |
| `src/shaders/SkPerlinNoiseShaderImpl.h` | 依赖 | Perlin 噪声实现细节 |
| `include/effects/SkPerlinNoiseShader.h` | 公共 API | Perlin 噪声着色器接口 |
| `src/shaders/SkPerlinNoiseShaderType.h` | 依赖 | 噪声类型枚举 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 依赖 | 纹理视图封装 |
| `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h` | 依赖 | 着色器代码生成 |
| `src/gpu/ganesh/GrFragmentProcessors.h` | 上层使用 | 片段处理器工厂 |
