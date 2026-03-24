# GrBlurUtils - Ganesh 模糊工具函数

> 源文件: `src/gpu/ganesh/GrBlurUtils.h`, `src/gpu/ganesh/GrBlurUtils.cpp`

## 概述

`GrBlurUtils` 命名空间提供了 Ganesh GPU 后端中所有与模糊（blur）相关的核心功能。它实现了高斯模糊的 GPU 加速管线，包括圆形模糊、矩形模糊、圆角矩形模糊、遮罩滤镜处理以及通用的二维高斯模糊。这是 Skia 中将 `SkMaskFilter`（特别是 `SkBlurMaskFilter`）转化为高效 GPU 渲染操作的关键模块。

## 架构位置

```
SkCanvas / Device
      |
GrBlurUtils (本文件 - 模糊策略与分发)
      |
      +-- GrFragmentProcessor (圆/矩形/RRect 专用 FP)
      +-- GaussianBlur (通用二维高斯模糊)
      +-- SW Mask Fallback (CPU 遮罩生成回退)
      |
SurfaceDrawContext -> GrOps -> GPU
```

该模块被 `skgpu::ganesh::Device` 在遇到带遮罩滤镜的绘制操作时调用，同时也被 Ganesh 的其他模糊相关功能（如模糊 RRect 特效）使用。

## 主要类与结构体

### 常量

```cpp
static constexpr int kBlurRRectMaxDivisions = 6;
```

RRect 模糊九宫格的最大分割数（X 和 Y 方向各最多 6 个控制点）。

### `DrawRectData` (内部)

```cpp
struct DrawRectData {
    SkIVector fOffset;
    SkISize   fSize;
};
```

缓存遮罩的绘制矩形元数据，用于从未裁剪的设备空间形状边界恢复实际绘制区域。

## 公共 API 函数

### `ComputeBlurredRRectParams()`

```cpp
bool ComputeBlurredRRectParams(const SkRRect& srcRRect, const SkRRect& devRRect,
                                SkScalar sigma, SkScalar xformedSigma,
                                SkRRect* rrectToDraw, SkISize* widthHeight,
                                SkScalar rectXs[], SkScalar rectYs[],
                                SkScalar texXs[], SkScalar texYs[]);
```

计算九宫格模糊 RRect 遮罩的所有参数。返回 `true` 表示可以使用九宫格优化。输出包含要绘制的整数化 RRect、遮罩尺寸以及覆盖几何和纹理坐标的网格分割。

### `DrawShapeWithMaskFilter()` (两个重载)

```cpp
void DrawShapeWithMaskFilter(GrRecordingContext*, SurfaceDrawContext*,
                              const GrClip*, const SkPaint&,
                              const SkMatrix&, const GrStyledShape&);

void DrawShapeWithMaskFilter(GrRecordingContext*, SurfaceDrawContext*,
                              const GrClip*, const GrStyledShape&,
                              GrPaint&&, const SkMatrix&, const SkMaskFilter*);
```

带遮罩滤镜的形状绘制入口。处理流程：
1. 尝试 `direct_filter_mask` 直接渲染（矩形、圆、RRect 的 GPU 快速路径）。
2. 回退到 `hw_create_filtered_mask`（GPU 创建遮罩纹理后应用高斯模糊）。
3. 最终回退到 `sw_create_filtered_mask`（CPU 生成遮罩纹理）。

### `GaussianBlur()`

```cpp
std::unique_ptr<SurfaceDrawContext> GaussianBlur(
        GrRecordingContext*, GrSurfaceProxyView srcView,
        GrColorType, SkAlphaType, sk_sp<SkColorSpace>,
        SkIRect dstBounds, SkIRect srcBounds,
        float sigmaX, float sigmaY,
        SkTileMode mode, SkBackingFit fit);
```

核心的二维高斯模糊函数。将纹理进行 X 和 Y 方向分离的高斯模糊处理。

### `MakeCircleBlur()`

```cpp
std::unique_ptr<GrFragmentProcessor> MakeCircleBlur(GrRecordingContext*,
                                                     const SkRect& circle, float sigma);
```

创建圆形模糊的 FragmentProcessor。使用预计算的一维模糊轮廓纹理（profile texture），通过 SkSL 运行时效果实现。

### `MakeRectBlur()`

```cpp
std::unique_ptr<GrFragmentProcessor> MakeRectBlur(GrRecordingContext*,
                                                   const GrShaderCaps&,
                                                   const SkRect& srcRect,
                                                   const std::optional<SkRect>& devRect,
                                                   const SkMatrix& viewMatrix,
                                                   float transformedSigma);
```

创建矩形模糊 FP。使用积分表（integral table）纹理，支持快速路径（宽矩形）和慢路径（窄矩形）。

### `MakeRRectBlur()`

```cpp
std::unique_ptr<GrFragmentProcessor> MakeRRectBlur(GrRecordingContext*, float sigma,
                                                    float xformedSigma,
                                                    const SkRRect& srcRRect,
                                                    const SkRRect& devRRect);
```

创建圆角矩形模糊 FP。通过九宫格（nine-patch）技术将预模糊的 RRect 遮罩纹理映射到任意大小的 RRect。

## 内部实现细节

### 线程安全缓存集成

所有模糊纹理（圆形轮廓、积分表、RRect 遮罩、过滤后的遮罩）都通过 `GrThreadSafeCache` 缓存：
- GPU 线程优先：使用 `CreateLazyView` 占位后异步填充。
- 录制线程回退到 CPU 生成。
- 使用 `UniqueKey` 确保缓存一致性。

### 遮罩渲染策略

`draw_shape_with_mask_filter` 函数实现了三级回退策略：

1. **直接渲染** (`direct_filter_mask`): 对矩形、圆和 RRect 形状使用专用的 FragmentProcessor。仅支持 `kNormal_SkBlurStyle` 和简单填充。
2. **GPU 遮罩渲染** (`hw_create_filtered_mask`): 在 GPU 上绘制形状到 alpha 遮罩，然后应用高斯模糊。需要 DirectContext。
3. **CPU 遮罩渲染** (`sw_create_filtered_mask`): 使用 CPU 路径光栅化和遮罩滤镜，结果上传为纹理。

### SkSL 运行时效果

圆形、矩形和 RRect 模糊都使用 `SkRuntimeEffect` 内联着色器：
- **CircleBlur**: 基于到圆心距离查找轮廓纹理。
- **RectBlur**: 分离计算 X/Y 方向的积分表查找并相乘；有 `isFast` 特化。
- **RRectBlur**: 将片段坐标映射到九宫格纹理坐标。

### 遮罩缓存策略

通过 `compute_key_and_clip_bounds` 决定是否缓存：
- 仅当矩阵保持轴对齐时缓存。
- 当未裁剪遮罩面积超过裁剪面积的 2 倍或超过最大纹理尺寸时不缓存。
- 缓存的遮罩使用包含矩阵 2x2 部分和子像素位移（8 位精度）的 UniqueKey。

### 非正常模糊样式处理

`filter_mask` 中处理四种模糊样式：
- **Normal**: 直接使用模糊结果。
- **Inner**: `dst = dst * src`（交集）。
- **Solid**: `dst = src + (1-src)*dst`（并集）。
- **Outer**: `dst = (1-src)*dst`（差集）。

## 依赖关系

- **上游依赖**: `GrRecordingContext`、`SurfaceDrawContext`、`GrClip`、`GrStyledShape`。
- **FP 依赖**: `GrTextureEffect`、`GrSkSLFP`、`GrBlendFragmentProcessor`、`GrMatrixEffect`。
- **模糊工具**: `src/gpu/BlurUtils.h`（积分表、RRect 遮罩生成）。
- **缓存**: `GrThreadSafeCache`、`UniqueKey`。
- **被依赖**: `skgpu::ganesh::Device`。

## 设计模式与设计决策

1. **分离高斯模糊**: 二维高斯分解为两次一维模糊（X 方向 + Y 方向），将 O(n^2) 降为 O(n)。
2. **九宫格纹理**: RRect 模糊使用小尺寸预模糊纹理 + 九宫格映射，实现任意大小 RRect 的常数时间模糊。
3. **多级回退**: GPU 直接渲染 -> GPU 遮罩渲染 -> CPU 遮罩渲染，确保所有情况都有正确输出。
4. **轮廓纹理缓存**: 圆形模糊的 sigma/radius 比率量化后缓存，避免重复计算。
5. **特化着色器**: 矩形模糊的 `isFast` 参数通过 `GrSkSLFP::Specialize` 编译为专用着色器变体。

## 性能考量

- **GPU/CPU 阈值**: 小形状 (<=64px) 且低 sigma (<=32) 时优先使用 CPU 模糊，因为 GPU 启动开销不值得。
- **线程安全缓存**: 避免多线程竞争重复计算相同的模糊遮罩。
- **纹理复用**: 遮罩缓存支持跨帧和跨线程复用。
- **精度保护**: 矩形模糊在非 32 位浮点 GPU 上，对大坐标 (>16000) 回退。
- **TRACE_EVENT**: 关键路径有性能追踪埋点。

## 相关文件

- `src/gpu/BlurUtils.h` - 通用模糊工具（积分表、RRect 遮罩生成）
- `src/gpu/ganesh/Device.h` - 主要调用者
- `src/gpu/ganesh/GrFragmentProcessor.h` - Fragment Processor 基类
- `src/gpu/ganesh/effects/GrSkSLFP.h` - SkSL 运行时效果 FP
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理效果 FP
- `src/gpu/ganesh/GrThreadSafeCache.h` - 线程安全缓存
- `src/core/SkBlurMaskFilterImpl.h` - CPU 模糊遮罩滤镜实现
