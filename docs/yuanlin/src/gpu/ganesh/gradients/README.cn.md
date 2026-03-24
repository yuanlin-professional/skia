# gradients - Ganesh GPU 渐变渲染模块

## 概述

`src/gpu/ganesh/gradients/` 目录是 Skia Ganesh GPU 渲染后端中负责渐变着色器 GPU 加速的模块。该模块将 Skia 的 `SkGradientShader`（线性、径向、扫描、双点锥形等渐变类型）转换为 GPU 片段处理器（`GrFragmentProcessor`）图，使渐变能够在 GPU 上高效渲染。

渐变渲染在 GPU 上的实现采用了精巧的分层架构，将渐变分解为三个独立的组件：**布局处理器（Layout）**、**颜色插值器（Colorizer）**和**顶层效果（Top-level Effect）**。布局处理器负责将 2D 坐标转换为一维插值参数 t；颜色插值器根据 t 值查找对应颜色；顶层效果则将两者组合并实现平铺模式（Clamp、Repeat、Mirror、Decal）。这种分离设计使得不同渐变类型可以共享颜色插值和平铺逻辑。

模块中的颜色插值策略经过精心优化，根据渐变的复杂度自动选择最佳方案。对于简单渐变（2色），使用单区间线性插值；对于中等复杂度（最多16色），使用手写展开的二分搜索着色器；对于较复杂（最多128色），使用循环二分搜索着色器；对于极复杂的渐变，则回退到纹理采样方案。这种自适应策略在保证渲染质量的同时最大化了性能。

`GrGradientBitmapCache` 提供了渐变纹理的缓存机制。当分析型着色器（analytic shader）无法处理渐变复杂度时，渐变被光栅化为 1x256（或更大）的位图纹理，该缓存使用 LRU 策略管理最多 32 个缓存条目，避免重复光栅化。

该模块还完整支持 CSS Color Level 4 规范中定义的多种颜色空间插值模式，包括 sRGB、OKLab、OKLCH、HSL、HWB、Lab、LCH 等，通过 SkSL 运行时效果实现颜色空间之间的转换。

## 架构图

```
+-------------------------------------------------------------------+
|                  SkGradientBaseShader (输入)                        |
|  - SkLinearGradient / SkRadialGradient / SkSweepGradient /        |
|    SkTwoPointConicalGradient                                       |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|              GrGradientShader::MakeGradientFP()                    |
|              (顶层工厂函数，组装完整渐变 FP 图)                    |
+-------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
+----------------+   +------------------+   +------------------+
| Layout FP      |   | Colorizer FP     |   | Tile Mode FP     |
| (布局处理器)   |   | (颜色插值器)     |   | (平铺效果)       |
|                |   |                  |   |                  |
| LinearLayout   |   | SingleInterval   |   | ClampedGradient  |
| RadialLayout   |   | DualInterval     |   | TiledGradient    |
| SweepLayout    |   | UnrolledBinary   |   | (Repeat/Mirror)  |
| ConicalLayout  |   | LoopingBinary    |   |                  |
+----------------+   | TexturedColorizer|   +------------------+
                      +------------------+
                              |
                     +--------+--------+
                     |                 |
                     v                 v
          +------------------+  +------------------+
          | Uniform-based    |  | Texture-based    |
          | (SkSL 着色器)    |  | (位图采样)       |
          | - scale/bias     |  | - GrTexture      |
          | - thresholds     |  |   Effect         |
          +------------------+  +------------------+
                                       |
                                       v
                              +------------------+
                              | GrGradientBitmap |
                              | Cache (LRU缓存)  |
                              +------------------+

+-------------------------------------------------------------------+
|              颜色空间转换管线                                       |
|  interpolated_to_rgb_unpremul() --> GrColorSpaceXformEffect        |
|  (OKLab/OKLCH/HSL/HWB/Lab/LCH -> 中间色彩空间 -> 目标色彩空间)   |
+-------------------------------------------------------------------+
```

## 文件分类索引

### 1. 梯度位图缓存 — Gradient Bitmap Cache

| 文件 | 说明 |
|------|------|
| GrGradientBitmapCache.h / GrGradientBitmapCache.cpp | 渐变位图纹理 LRU 缓存（复杂渐变回退方案） |

### 2. 梯度着色器生成 — Gradient Shader Factory

| 文件 | 说明 |
|------|------|
| GrGradientShader.h / GrGradientShader.cpp | 渐变 FP 工厂函数（布局+颜色插值+平铺模式组装） |

## 关键类与函数

### GrGradientShader 命名空间 - 渐变工厂

该命名空间提供了将 `SkGradientBaseShader` 转换为 GPU 片段处理器图的核心工厂函数：

```cpp
namespace GrGradientShader {
    // 通用渐变 FP 组装（组合 layout + colorizer + tile mode）
    std::unique_ptr<GrFragmentProcessor> MakeGradientFP(
        const SkGradientBaseShader& shader,
        const GrFPArgs& args,
        const SkShaders::MatrixRec&,
        std::unique_ptr<GrFragmentProcessor> layout,
        const SkMatrix* overrideMatrix = nullptr);

    // 线性渐变专用（创建 LinearLayout 并调用 MakeGradientFP）
    std::unique_ptr<GrFragmentProcessor> MakeLinear(
        const SkLinearGradient& shader,
        const GrFPArgs& args,
        const SkShaders::MatrixRec&);
}
```

`MakeGradientFP()` 是整个模块的核心入口。它执行以下步骤：

1. 应用变换矩阵到布局处理器
2. 将渐变颜色转换到目标颜色空间
3. 选择最优的颜色插值器策略
4. 根据平铺模式组装顶层效果

### 颜色插值器策略

模块实现了五种颜色插值器，按复杂度递增排列：

#### 1. 单区间插值器 (SingleIntervalColorizer)

用于只有两个颜色的渐变（最简单情况）：

```glsl
// SkSL 着色器
uniform half4 start;
uniform half4 end;
half4 main(float2 coord) {
    return mix(start, end, half(coord.x));
}
```

#### 2. 双区间插值器 (DualIntervalColorizer)

用于 3 色渐变或在同一位置有硬停靠的 4 色渐变：

```glsl
uniform float4 scale[2];
uniform float4 bias[2];
uniform half threshold;
half4 main(float2 coord) {
    half t = half(coord.x);
    float4 s, b;
    if (t < threshold) { s = scale[0]; b = bias[0]; }
    else { s = scale[1]; b = bias[1]; }
    return half4(t * s + b);
}
```

#### 3. 展开二分搜索插值器 (UnrolledBinaryColorizer)

用于最多 16 色的渐变。使用手写的嵌套 if 语句进行二分搜索，无需数组索引支持（兼容 ES2 硬件）：

```cpp
static constexpr int kMaxUnrolledColorCount = 16;
static constexpr int kMaxUnrolledIntervalCount = kMaxUnrolledColorCount / 2;  // 8
```

阈值被打包到两个 `half4` uniform 中以减少 uniform 使用量。

#### 4. 循环二分搜索插值器 (LoopingBinaryColorizer)

用于最多 128 色的渐变。使用真正的循环进行二分搜索（需要 `nonconstantArrayIndexSupport`）：

```cpp
static constexpr int kMaxLoopingColorCount = 128;
static constexpr int kMaxLoopingIntervalCount = kMaxLoopingColorCount / 2;  // 64
```

区间数量向上取整到 4 的倍数的下一个 2 的幂，以减少唯一着色器数量。

#### 5. 纹理颜色化器 (TexturedColorizer)

当分析型着色器无法处理时的回退方案。将渐变光栅化为 1x256 位图，通过线性滤波纹理采样：

```cpp
static const int kMaxNumCachedGradientBitmaps = 32;
static const int kGradientTextureSize = 256;
```

支持 8888 和 F16 两种格式，根据目标表面精度自动选择。

### 区间构建函数

```cpp
int build_intervals(int inputLength,
                    const SkPMColor4f* inColors,
                    const SkScalar* inPositions,
                    int outputLength,
                    SkPMColor4f* outScales,
                    SkPMColor4f* outBiases,
                    SkScalar* outThresholds);
```

将颜色停靠点和位置转换为 `scale * t + bias` 形式的线性函数参数。自动处理硬停靠（两个相同位置的颜色停靠）和退化区间。

### 顶层平铺效果

#### ClampedGradient (Clamp/Decal 模式)

```glsl
uniform shader colorizer;
uniform shader gradLayout;
uniform half4 leftBorderColor;   // t < 0
uniform half4 rightBorderColor;  // t > 1
half4 main(float2 coord) {
    half4 t = gradLayout.eval(coord);
    if (t.y < 0) return half4(0);           // 布局拒绝（如锥形渐变）
    if (t.x < 0) return leftBorderColor;    // 左边界
    if (t.x > 1.0) return rightBorderColor; // 右边界
    return colorizer.eval(t.x0);            // 正常采样
}
```

#### TiledGradient (Repeat/Mirror 模式)

```glsl
uniform shader colorizer;
uniform shader gradLayout;
uniform int mirror;  // 特化常量
half4 main(float2 coord) {
    float4 t = gradLayout.eval(coord);
    if (mirror) {
        float tiled_t = t_1 - 2 * floor(t_1 * 0.5) - 1;
        t.x = abs(tiled_t);
    } else {
        t.x = fract(t.x);  // 简单重复
    }
    return colorizer.eval(t.x0);
}
```

### 颜色空间转换

`make_interpolated_to_dst()` 处理从插值颜色空间到目标颜色空间的转换：

```cpp
// 支持的插值颜色空间 (CSS Color Level 4)
enum class ColorSpace {
    kDestination = 0,   // 目标颜色空间
    kSRGBLinear = 1,    // sRGB 线性
    kLab = 2,           // CIE Lab
    kOKLab = 3,         // OKLab
    kOKLabGamutMap = 4, // OKLab 色域映射
    kLCH = 5,           // CIE LCH
    kOKLCH = 6,         // OKLCH
    kOKLCHGamutMap = 7, // OKLCH 色域映射
    kSRGB = 8,          // sRGB
    kHSL = 9,           // HSL
    kHWB = 10,          // HWB
};
```

对于非 RGB 颜色空间（Lab、OKLab、LCH、OKLCH、HSL、HWB），颜色先被反预乘，然后通过 `$interpolated_to_rgb_unpremul()` SkSL 内置函数转换回 RGB，最后通过 `GrColorSpaceXformEffect` 转换到目标颜色空间。

### GrGradientBitmapCache - 渐变位图缓存

线程安全的 LRU 缓存，管理渐变纹理位图：

```cpp
class GrGradientBitmapCache : SkNoncopyable {
public:
    GrGradientBitmapCache(int maxEntries, int resolution);

    // 获取或生成渐变位图（线程安全）
    void getGradient(const SkPMColor4f* colors,
                     const SkScalar* positions,
                     int count,
                     bool colorsAreOpaque,
                     const SkGradient::Interpolation& interpolation,
                     const SkColorSpace* intermediateColorSpace,
                     const SkColorSpace* dstColorSpace,
                     SkColorType colorType,
                     SkAlphaType alphaType,
                     SkBitmap* bitmap);

private:
    SkMutex fMutex;          // 线程安全锁
    int fEntryCount;
    const int fMaxEntries;   // 最大缓存条目数（默认32）
    const int fResolution;   // 位图宽度（默认256）
    Entry* fHead;            // LRU 链表头
    Entry* fTail;            // LRU 链表尾
};
```

缓存以颜色/位置数据的哈希作为键进行查找。命中时将条目移到链表头部（MRU），未命中时在头部添加新条目，并在超过 `maxEntries` 时淘汰尾部条目。

## 依赖关系

### 向上依赖

- `src/shaders/gradients/SkGradientBaseShader.h` - 渐变着色器基类
- `src/shaders/gradients/SkLinearGradient.h` - 线性渐变定义
- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/effects/GrSkSLFP.h` - SkSL 片段处理器
- `src/gpu/ganesh/effects/GrMatrixEffect.h` - 矩阵变换效果
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理采样效果
- `src/gpu/ganesh/GrColorSpaceXform.h` - 颜色空间变换
- `src/gpu/ganesh/GrFPArgs.h` - 片段处理器参数
- `src/gpu/ganesh/GrShaderCaps.h` - 着色器能力查询
- `src/gpu/ganesh/image/GrMippedBitmap.h` - Mipmap 位图

### 向下依赖（被依赖者）

- `src/shaders/gradients/SkLinearGradient.cpp` 等 - 各渐变类型的 `asFragmentProcessor()` 调用
- `src/gpu/ganesh/GrFragmentProcessors.cpp` - FP 图构建

### SkSL 运行时效果依赖

模块大量使用 `SkRuntimeEffect::MakeForShader` 创建运行时着色器。这些着色器在首次使用时编译并通过 `SkOnce` 缓存，避免重复编译开销。

## 设计模式分析

### 策略模式 (Strategy)

颜色插值器的选择是典型的策略模式。`make_uniform_colorizer()` 作为策略选择器，根据颜色数量和硬件能力自动选择最佳策略：

```
2色 -> SingleInterval
3色或硬停靠4色 -> DualInterval
<=16色 (无数组索引) -> UnrolledBinary
<=128色 (有数组索引) -> LoopingBinary
>128色 或精度不足 -> 回退到 TexturedColorizer
```

### 组合模式 (Composite)

渐变的 FP 图是一个树形结构，顶层效果（Clamped/Tiled）组合了布局和颜色化子处理器。`GrSkSLFP::Make` 的 `"colorizer"` 和 `"gradLayout"` 参数将子 FP 作为着色器子节点注入。

### 特化常量优化 (Specialization)

多个 SkSL uniform 被标记为 `GrSkSLFP::Specialize<int>()`，这意味着它们的值在编译时就已确定。SkSL 编译器可以基于这些常量进行分支消除和代码简化。例如：

- `mirror` 标志决定是 repeat 还是 mirror 模式
- `layoutPreservesOpacity` 决定是否需要检查无效位置
- `useFloorAbsWorkaround` 处理特定 GPU 的着色器 bug

### 缓存模式 (Cache)

`GrGradientBitmapCache` 使用 LRU 策略缓存渐变位图，运行时效果着色器通过 `SkOnce` 缓存编译结果。这两级缓存避免了重复计算的开销。

## 数据流

```
SkGradientBaseShader
(颜色停靠点, 位置, 平铺模式, 插值模式)
            |
            v
GrGradientShader::MakeGradientFP()
            |
            +-- (1) 变换矩阵应用 ------------> apply_matrix()
            |                                      |
            |                                      v
            |                               GrMatrixEffect::Make()
            |
            +-- (2) 颜色空间转换 ------------> SkColor4fXformer
            |       (源色彩空间 -> 中间色彩空间,    |
            |        所有颜色预乘处理)              v
            |                               SkPMColor4f[] colors
            |                               SkScalar[] positions
            |
            +-- (3) 颜色化器选择:
            |       |
            |       +-- 尝试 make_uniform_colorizer()
            |       |       |
            |       |       +-- 2色? -> make_single_interval_colorizer()
            |       |       +-- 3色? -> make_dual_interval_colorizer()
            |       |       +-- <=16色? -> make_unrolled_binary_colorizer()
            |       |       |     (build_intervals -> scale/bias/thresholds)
            |       |       +-- <=128色? -> make_looping_binary_colorizer()
            |       |       +-- 精度不足? -> 返回 nullptr
            |       |
            |       +-- 如果 uniform 成功:
            |       |       -> make_interpolated_to_dst() (颜色空间后处理)
            |       |
            |       +-- 如果 uniform 失败:
            |               -> make_textured_colorizer()
            |                       |
            |                       v
            |               GrGradientBitmapCache::getGradient()
            |                       |
            |                       v
            |               GrMakeCachedBitmapProxyView() -> 纹理上传
            |                       |
            |                       v
            |               GrTextureEffect::Make() (线性滤波)
            |
            +-- (4) 平铺模式组装:
                    |
                    +-- kClamp  -> make_clamped_gradient(边界色)
                    +-- kDecal  -> make_clamped_gradient(透明色)
                    +-- kRepeat -> make_tiled_gradient(mirror=false)
                    +-- kMirror -> make_tiled_gradient(mirror=true)
                            |
                            v
                    最终 GrFragmentProcessor 图
                            |
                            v
                    GPU 着色器编译与执行
```

### 布局处理器的 t 值编码

布局处理器不直接返回颜色，而是将一维插值参数编码到 `half4` 输出中：

```
r = t 值 (未平铺的原始插值参数)
g = 正值表示有效, 负值表示拒绝该像素
b = 未使用
a = 未使用
```

颜色化器始终从 `(t, 0)` 坐标采样，y 坐标固定为 0。

## 相关文档与参考

- `src/gpu/ganesh/gradients/README.md` - 原始英文设计文档（详细描述三层架构）
- `src/shaders/gradients/SkGradientBaseShader.h` - 渐变着色器基类
- `src/shaders/gradients/SkLinearGradient.h` - 线性渐变
- `src/shaders/gradients/SkRadialGradient.h` - 径向渐变
- `src/shaders/gradients/SkSweepGradient.h` - 扫描渐变
- `src/shaders/gradients/SkTwoPointConicalGradient.h` - 双点锥形渐变
- `src/gpu/ganesh/effects/GrSkSLFP.h` - SkSL 片段处理器
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理采样效果
- `src/gpu/ganesh/GrColorSpaceXform.h` - 颜色空间变换效果
- CSS Color Level 4 规范 - 渐变颜色空间插值标准
- `include/effects/SkGradient.h` - 渐变插值配置
- Skia GPU 架构概览：https://skia.org/docs/dev/design/
