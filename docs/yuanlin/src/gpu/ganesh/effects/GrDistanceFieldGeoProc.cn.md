# GrDistanceFieldGeoProc

> 源文件: `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.h`, `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.cpp`

## 概述

该文件定义了三个用于有符号距离场（SDF）文本和路径渲染的几何处理器：`GrDistanceFieldA8TextGeoProc`（灰度 SDF 文本）、`GrDistanceFieldPathGeoProc`（SDF 路径）和 `GrDistanceFieldLCDTextGeoProc`（LCD SDF 文本）。这些处理器从距离场纹理图集中采样，使用平滑阶跃函数将距离值转换为覆盖率，实现高质量的缩放无关文本和路径渲染。

## 架构位置

位于 Ganesh 效果层，属于几何处理器（GrGeometryProcessor）。它们在文本渲染管线中被 `GrAtlasTextOp` 和路径绘制操作使用，与 Skia 的文本图集系统紧密配合。在 `SK_DISABLE_SDF_TEXT` 定义时，这些处理器会被完全排除。

## 主要类与结构体

### `GrDistanceFieldA8TextGeoProc`
- 用于灰度 SDF 文本渲染
- 支持 gamma 校正（`SK_GAMMA_APPLY_TO_A8`）
- 最多 4 个纹理图集（`kMaxTextures = 4`）
- 顶点属性：位置（float2/float3）、颜色（ubyte4）、纹理坐标（ushort2/float2）

### `GrDistanceFieldPathGeoProc`
- 用于 SDF 路径渲染
- 与 A8 类似但支持宽色域属性
- 位置始终为 float3（支持透视）

### `GrDistanceFieldLCDTextGeoProc`
- 用于 LCD 子像素 SDF 文本
- 使用 `DistanceAdjust` 结构体为 R/G/B 分别调整距离值
- 支持 BGR 排列和竖屏模式

### `GrDistanceFieldEffectFlags`
- 标志位枚举：相似变换、仅缩放、透视、LCD、BGR、竖屏、gamma 校正、走样、宽色域等

## 公共 API 函数

### 各处理器的 `Make()`
通过 `SkArenaAlloc` 工厂方法创建，接受着色器能力、纹理视图、采样状态、标志和局部矩阵参数。

### `addNewViews()`
动态添加新的纹理图集视图（用于图集按需增长）。

### `addToKey()`
将标志位和纹理数编码到 program key 中。

## 内部实现细节

### 距离场覆盖率计算
1. 从纹理采样距离值：`distance = 8 * (texColor.r - 0.5)`
2. 根据变换类型计算反走样宽度（afwidth）：
   - **均匀缩放**: 使用 `dFdx` 或 `dFdy` 的绝对值
   - **相似变换**: 使用梯度的长度
   - **一般变换**: 使用距离梯度方向投影到 Jacobian 矩阵后的长度
3. 生成覆盖率：
   - **走样模式**: 硬阈值 `distance > 0 ? 1 : 0`
   - **Gamma 校正**: 线性映射 `saturate((distance + afwidth) / (2 * afwidth))`
   - **标准**: `smoothstep(-afwidth, afwidth, distance)`

### 纹理图集处理
- 使用 `append_index_uv_varyings()` 和 `append_multitexture_lookup()` 处理多纹理图集
- 纹理坐标从 ushort2 转换为归一化浮点坐标

### Gamma 校正（A8 文本）
- 可选的 `SK_GAMMA_APPLY_TO_A8` 编译标志
- 通过 `fDistanceAdjust` uniform 调整距离阈值补偿 gamma 效果

## 依赖关系

- **GrGeometryProcessor** - 基类
- **GrAtlasedShaderHelpers** - 多纹理图集 varying 和查找辅助
- **SkDistanceFieldGen** - SDF 常量定义（`SK_DistanceFieldMultiplier`、`SK_DistanceFieldThreshold`）
- **GrSurfaceProxyView** - 纹理图集视图

## 设计模式与设计决策

1. **三处理器分离**: 灰度文本、路径和 LCD 文本各自优化，避免分支和无用计算
2. **动态图集扩展**: `addNewViews()` 支持图集在绘制过程中按需增长
3. **Mali GPU 规避**: 使用 `dFdy` 替代 `dFdx` 避免 Mali 400 的 bug
4. **precision 处理**: 使用 `float2 uv` 代替 half2 以避免低精度导致的走样

## 性能考量

- SDF 渲染允许单张纹理覆盖大范围缩放，减少纹理切换
- 均匀缩放路径最为高效（单次 dFdx/dFdy）
- 一般变换路径需要额外的梯度计算和矩阵投影
- LCD 模式需要三次距离值计算（R/G/B 分别调整）

## 相关文件

- `src/gpu/ganesh/effects/GrAtlasedShaderHelpers.h` - 图集着色器辅助
- `src/core/SkDistanceFieldGen.h` - SDF 生成常量
- `src/gpu/ganesh/text/GrAtlasManager.h` - 文本图集管理
- `src/gpu/ganesh/ops/AtlasTextOp.h` - SDF 文本绘制操作
