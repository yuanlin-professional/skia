# SkImageShader - 图像着色器

> 源文件: `src/shaders/SkImageShader.h`, `src/shaders/SkImageShader.cpp`

## 概述

SkImageShader 是 Skia 中将 SkImage（图像）作为着色器（Shader）使用的核心实现类。它允许将一张图像按照指定的平铺模式（TileMode）和采样选项（SamplingOptions）映射到绘制表面上。SkImageShader 支持常规图像着色、原始（raw）图像着色（跳过色彩空间转换）、子集图像着色（仅使用图像的一部分区域），以及将 drawImageRect 调用转换为 drawRect + shader 的优化路径。

该类是 Skia 渲染管线中处理图像纹理映射的基础组件，广泛应用于 Canvas 的 drawImage 系列 API 的底层实现。

## 架构位置

SkImageShader 位于 Skia 着色器子系统中：

```
SkShader (公共接口)
  └── SkShaderBase (内部基类)
        └── SkImageShader (图像着色器)
```

- **上层调用者**: SkCanvas::drawImage / drawImageRect、SkImage::makeShader、SkShaders::Image / RawImage
- **下层依赖**: SkRasterPipeline（光栅化管线阶段）、SkMipmapAccessor（多级渐远纹理访问）、SkColorSpaceXformSteps（色彩空间转换）
- **GPU 路径**: Graphite 和 Ganesh 后端通过 ShaderType::kImage 识别并生成对应的 GPU 着色器代码

## 主要类与结构体

### SkImageShader
继承自 `SkShaderBase`，是图像着色器的核心实现。

**关键成员变量**:
- `fImage` (sk_sp<SkImage>): 关联的图像对象
- `fSampling` (SkSamplingOptions): 采样选项，支持最近邻、双线性、双三次等
- `fTileModeX / fTileModeY` (SkTileMode): X/Y 轴的平铺模式（Clamp / Repeat / Mirror / Decal）
- `fSubset` (SkRect): 图像子集区域，目前仅 GPU 图像支持
- `fRaw` (bool): 是否跳过色彩空间转换
- `fClampAsIfUnpremul` (bool): 是否以非预乘模式进行 clamp

### MipLevelHelper（匿名命名空间）
辅助结构体，用于管理单个 Mip 级别的像素数据、逆矩阵以及 gather/tile 上下文信息。负责为光栅化管线分配和初始化采样相关的上下文。

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<SkShader> Make(sk_sp<SkImage>, SkTileMode tmx, SkTileMode tmy,
                            const SkSamplingOptions&, const SkMatrix* localMatrix,
                            bool clampAsIfUnpremul = false);
```
创建标准图像着色器。这是最常用的入口点，会进行完整的色彩空间转换。

```cpp
static sk_sp<SkShader> MakeRaw(sk_sp<SkImage>, SkTileMode tmx, SkTileMode tmy,
                                const SkSamplingOptions&, const SkMatrix* localMatrix);
```
创建"原始"图像着色器，跳过色彩空间转换和预乘 alpha 处理。不支持双三次采样。

```cpp
static sk_sp<SkShader> MakeSubset(sk_sp<SkImage>, const SkRect& subset,
                                   SkTileMode tmx, SkTileMode tmy,
                                   const SkSamplingOptions&, const SkMatrix* localMatrix,
                                   bool clampAsIfUnpremul = false);
```
创建支持子集区域的图像着色器。目前仅对 GPU 纹理支持的图像有效。

```cpp
static std::pair<SkRect, sk_sp<SkShader>> MakeForDrawRect(
    const SkImage*, const SkPaint&, const SkSamplingOptions&,
    SkRect src, SkRect dst, bool strictSrcSubset);
```
将 drawImageRect 转换为可用于 drawRect 的着色器和目标矩形。处理 alpha-only 图像与画笔着色器的混合。

### 静态辅助方法

```cpp
static SkM44 CubicResamplerMatrix(float B, float C);
```
根据 Mitchell-Netravali 参数 B 和 C 生成 4x4 双三次重采样矩阵。

### 实例查询方法

- `tileModeX()` / `tileModeY()` — 获取平铺模式
- `image()` — 获取关联的图像
- `sampling()` — 获取采样选项
- `subset()` — 获取子集区域
- `isRaw()` — 是否为原始模式
- `isOpaque()` — 当图像不透明且不使用 Decal 模式时返回 true

## 内部实现细节

### 平铺模式优化
构造函数中的 `optimize()` 函数对 1 像素宽/高的维度进行优化：mirror 和 repeat 模式退化为 clamp 模式（decal 除外），因为 clamp 更快。Android Framework 构建中为了测试兼容性禁用了此优化。

### 采样调整（tweak_sampling）
当逆变换矩阵仅包含整数平移时，双线性过滤退化为最近邻过滤，这是一种常见的性能优化。

### 光栅化管线阶段（appendStages）
`appendStages` 是核心渲染方法，负责将图像着色器转化为光栅化管线阶段序列：

1. **矩阵变换**: 计算逆变换矩阵并应用到管线
2. **Mipmap 处理**: 通过 SkMipmapAccessor 确定合适的 mip 级别，支持线性 mipmap 插值
3. **快速路径检测**: 对 RGBA_8888/BGRA_8888 + bilinear/bicubic + clamp 组合使用优化的融合阶段（bilerp_clamp_8888、bicubic_clamp_8888）
4. **平铺**: 根据 X/Y 轴的平铺模式追加 mirror/repeat/decal 阶段
5. **像素采集**: 根据颜色类型追加对应的 gather 阶段（支持 20+ 种颜色格式）
6. **双三次/双线性采样**: 双三次采样需要 16 个样本点（4x4），双线性需要 4 个样本点（2x2）
7. **色彩空间转换**: 非 raw 模式下执行从源色彩空间到目标色彩空间的转换

### 整数像素捕捉
最近邻采样模式下启用 `roundDownAtInteger`，确保精确整数坐标选择左/上方像素。这在镜像模式下有特殊处理以保证一致性。

### 高精度双线性
当采样坐标可能超出 INT16 范围时，使用 `bilerp_clamp_8888_force_highp` 避免溢出。

### 序列化
通过 `flatten` / `CreateProc` 支持 SkPicture 序列化。当前子集信息不参与序列化（因为仅用于特殊 GPU 图像）。支持旧版本格式的向后兼容读取。

## 依赖关系

### 内部依赖
- `SkShaderBase` — 着色器基类
- `SkRasterPipeline` — 光栅化管线
- `SkMipmapAccessor` — Mipmap 级别选择
- `SkColorSpaceXformSteps` — 色彩空间转换
- `SkBitmapProcState` / `SkBitmapProcShader` — 旧版着色器上下文（Legacy）
- `SkImage_Base` — 图像内部接口

### 外部依赖
- `skcms` — 色彩管理系统（sRGB 传递函数）

## 设计模式与设计决策

1. **工厂方法模式**: 通过 Make / MakeRaw / MakeSubset 静态方法创建实例，确保参数验证
2. **Flattenable 模式**: 实现 SK_FLATTENABLE_HOOKS 宏支持序列化/反序列化
3. **Raw 模式分离**: raw 模式与常规模式共享实现但跳过色彩转换，避免不可预期的颜色夹紧
4. **Subset 的 GPU 限制**: 子集功能仅限 GPU 后端使用，CPU 路径暂不支持（标记为 TODO）
5. **Legacy ShaderContext**: 在 SK_ENABLE_LEGACY_SHADERCONTEXT 宏控制下保留旧版渲染路径，支持 Android Framework 的特殊需求
6. **平铺模式优化**: 1 像素维度自动退化为 clamp，这是常见的边界条件优化

## 性能考量

- **快速路径**: RGBA_8888 + bilinear + clamp 组合使用单一融合管线阶段，避免多次采样和累加的开销
- **Mipmap 支持**: 自动选择合适的 mip 级别减少锯齿，支持线性 mipmap 插值
- **采样降级**: 整数平移时自动将双线性降级为最近邻
- **Legacy Context 限制**: 旧版渲染路径限制图像尺寸不超过 32767 像素，使用 SkFixed 16.16 定点数运算
- **高精度/低精度自适应**: 根据采样坐标范围自动选择高精度或低精度双线性路径
- **Decal 模式开销**: Decal 模式需要额外的掩码检查阶段，比其他平铺模式略慢

### 颜色格式支持详情

appendStages 中的 gather 阶段支持以下所有 SkColorType：

| 颜色类型 | 管线操作 | 额外处理 |
|---------|---------|---------|
| kAlpha_8 | gather_a8 | 无 |
| kA16_unorm | gather_a16 | 无 |
| kA16_float | gather_af16 | 无 |
| kRGB_565 | gather_565 | 无 |
| kARGB_4444 | gather_4444 | 无 |
| kRGBA_8888 | gather_8888 | 无 |
| kBGRA_8888 | gather_8888 | swap_rb |
| kSRGBA_8888 | gather_8888 | sRGB 传递函数 |
| kRGBA_F16 | gather_f16 | 无 |
| kRGBA_F32 | gather_f32 | 无 |
| kRGBA_1010102 | gather_1010102 | 无 |
| kBGRA_1010102 | gather_1010102 | swap_rb |
| kGray_8 | gather_a8 | alpha_to_gray |
| kR8_unorm | gather_a8 | alpha_to_red |
| kRGB_888x | gather_8888 | force_opaque |
| kRGBA_10x6 | gather_10x6 | 无 |

对于 alpha-only 图像（如 kAlpha_8），非 raw 模式下会使用画笔颜色进行着色。

### MipLevelHelper 详细说明

MipLevelHelper 的 `allocAndInit` 方法执行以下操作：
1. 创建 GatherCtx 并设置像素地址、步幅、宽度、高度
2. 如果使用双三次采样，将重采样矩阵权重写入 GatherCtx
3. 创建 TileCtx 设置 X/Y 方向的缩放和反缩放因子
4. 最近邻采样时设置 roundDownAtInteger 标志和 mirrorBiasDir
5. Decal 模式时创建 DecalTileCtx 设置边界限制

### Legacy ShaderContext 详细说明

在 `SK_ENABLE_LEGACY_SHADERCONTEXT` 编译选项下，`onMakeContext` 方法提供旧版渲染路径：
- 仅支持 kN32_SkColorType（平台原生 32 位颜色）
- 仅支持预乘 alpha
- X/Y 平铺模式必须相同
- 不支持 Decal 模式
- 支持的采样模式：Nearest+None、Linear+None、Linear+Nearest
- 不支持双三次采样和各向异性采样
- 图像尺寸限制为 32767x32767
- 逆矩阵不能有透视变换
- 目标色彩空间必须与源兼容

### 命名空间函数

```cpp
namespace SkShaders {
    sk_sp<SkShader> Image(sk_sp<SkImage>, SkTileMode, SkTileMode,
                          const SkSamplingOptions&, const SkMatrix*);
    sk_sp<SkShader> RawImage(sk_sp<SkImage>, SkTileMode, SkTileMode,
                             const SkSamplingOptions&, const SkMatrix*);
}
```

这两个命名空间函数是 Make 和 MakeRaw 的公共包装，分别委托给对应的静态方法。

### Flattenable 注册

`SkShaderBase::RegisterFlattenables()` 方法注册 SkImageShader 的序列化支持。这是 Skia Flattenable 系统的标准做法，确保 SkPicture 能正确序列化和反序列化图像着色器。

## 相关文件

- `include/core/SkShader.h` — SkShader 公共接口
- `src/shaders/SkShaderBase.h` — 着色器内部基类
- `include/core/SkSamplingOptions.h` — 采样选项定义
- `src/core/SkRasterPipeline.h` — 光栅化管线
- `src/core/SkMipmapAccessor.h` — Mipmap 访问器
- `src/core/SkColorSpaceXformSteps.h` — 色彩空间转换步骤
- `src/image/SkImage_Base.h` — 图像内部基类
- `src/core/SkBitmapProcState.h` — 位图处理状态（旧版路径）
- `src/core/SkRasterPipelineOpContexts.h` — 管线上下文定义
- `src/core/SkRasterPipelineOpList.h` — 管线操作列表
- `src/core/SkSamplingPriv.h` — 采样私有工具
