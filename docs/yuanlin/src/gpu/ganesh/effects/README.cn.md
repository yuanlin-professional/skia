# effects - Ganesh GPU 加速效果处理器集合

## 概述

`src/gpu/ganesh/effects` 目录是 Skia 图形库中 Ganesh GPU 后端的核心效果处理器集合。该目录包含了约 41 个源文件（头文件与实现文件成对出现），实现了渲染管线中三大类处理器：**片段处理器（Fragment Processor）**、**几何处理器（Geometry Processor）** 和 **混合传输处理器（Xfer Processor）**。这些处理器共同构成了 Ganesh 渲染管线中从几何输入到最终像素输出的完整 GPU 加速效果链。

片段处理器负责在片段着色器阶段对颜色进行变换和计算，包括纹理采样、颜色混合、矩阵变换、裁剪效果等。几何处理器负责处理顶点数据并生成顶点着色器代码，包括贝塞尔曲线渲染、距离场文字渲染、位图文字渲染等。混合传输处理器（XP）则负责管线的最后阶段，控制源颜色与目标颜色的混合方式，实现 Porter-Duff 混合、覆盖集合运算等。

该目录中的效果处理器是 Skia 高层绘图 API（如 `SkPaint`、`SkShader`、`SkColorFilter`、`SkBlender`）在 GPU 渲染路径上的底层实现。当用户调用 Skia 绘图 API 时，Ganesh 后端会将这些高层概念转换为相应的效果处理器树，再由 GLSL 代码生成器将其编译为着色器代码。

每个效果处理器都遵循统一的设计模式：提供静态工厂方法 `Make()` 创建实例、通过 `onMakeProgramImpl()` 生成对应的 `ProgramImpl` 用于着色器代码发射、通过 `onAddToKey()` 生成缓存键以支持着色器程序缓存、通过 `onIsEqual()` 支持处理器等价性比较。这种高度统一的架构使得新效果的添加和已有效果的维护都非常规范和高效。

## 架构图

```
                     ┌─────────────────────────────────────────┐
                     │           Skia 高层绘图 API              │
                     │  (SkPaint, SkShader, SkColorFilter...)  │
                     └──────────────────┬──────────────────────┘
                                        │
                                        v
                     ┌─────────────────────────────────────────┐
                     │        GrPipeline (渲染管线)             │
                     │  组装 GP + FP 链 + XP 为完整管线          │
                     └──────┬──────────┬───────────┬───────────┘
                            │          │           │
              ┌─────────────┘          │           └─────────────┐
              v                        v                         v
   ┌──────────────────┐   ┌───────────────────────┐   ┌──────────────────┐
   │  Geometry         │   │  Fragment              │   │  Xfer            │
   │  Processor (GP)   │   │  Processor (FP) 链     │   │  Processor (XP)  │
   │  几何处理器        │   │  片段处理器树           │   │  混合传输处理器   │
   ├──────────────────┤   ├───────────────────────┤   ├──────────────────┤
   │GrConicEffect     │   │GrTextureEffect        │   │GrPorterDuffXP    │
   │GrQuadEffect      │   │GrBicubicEffect        │   │  Factory         │
   │GrBitmapTextGeo   │   │GrSkSLFP              │   │GrCoverageSetOp   │
   │  Proc             │   │GrBlendFragment       │   │  XPFactory       │
   │GrDistanceFieldA8 │   │  Processor            │   │GrCustomXfermode  │
   │  TextGeoProc     │   │GrMatrixEffect         │   │GrDisableColorXP  │
   │GrDistanceFieldPath│   │GrConvexPolyEffect    │   │  Factory         │
   │  GeoProc         │   │GrOvalEffect           │   └──────────────────┘
   │GrDistanceFieldLCD│   │GrRRectEffect          │
   │  TextGeoProc     │   │GrYUVtoRGBEffect       │
   │GrRRectShadowGeo  │   │GrPerlinNoise2Effect   │
   │  Proc             │   │GrColorTableEffect     │
   └──────────────────┘   │GrModulateAtlas        │
                           │  CoverageEffect       │
                           └───────────────────────┘
                                        │
                                        v
                     ┌─────────────────────────────────────────┐
                     │        glsl/ 目录 (着色器代码生成)       │
                     │  GrGLSLShaderBuilder, ProgramBuilder... │
                     └─────────────────────────────────────────┘
```

## 文件分类索引

### 1. 片段处理器 (FP) — 纹理/变换/运行时

| 文件 | 说明 |
|------|------|
| GrTextureEffect.h / GrTextureEffect.cpp | 纹理采样效果（支持子集、环绕、边界模式） |
| GrBlendFragmentProcessor.h / GrBlendFragmentProcessor.cpp | 片段处理器级别的混合操作 |
| GrMatrixEffect.h / GrMatrixEffect.cpp | 坐标矩阵变换效果 |
| GrSkSLFP.h / GrSkSLFP.cpp | SkSL 运行时效果的片段处理器桥接 |
| GrBicubicEffect.h / GrBicubicEffect.cpp | 双三次插值纹理过滤效果 |

### 2. 形状/几何效果 (FP) — 裁剪与曲线

| 文件 | 说明 |
|------|------|
| GrOvalEffect.h / GrOvalEffect.cpp | 椭圆形裁剪效果 |
| GrRRectEffect.h / GrRRectEffect.cpp | 圆角矩形裁剪效果 |
| GrConvexPolyEffect.h / GrConvexPolyEffect.cpp | 凸多边形裁剪效果 |
| GrBezierEffect.h / GrBezierEffect.cpp | 贝塞尔曲线渲染（圆锥曲线 + 二次曲线几何处理器） |

### 3. 颜色/图像处理 (FP) — 颜色变换与噪声

| 文件 | 说明 |
|------|------|
| GrColorTableEffect.h / GrColorTableEffect.cpp | 颜色查找表效果 |
| GrYUVtoRGBEffect.h / GrYUVtoRGBEffect.cpp | YUV 到 RGB 颜色空间转换效果 |
| GrPerlinNoise2Effect.h / GrPerlinNoise2Effect.cpp | Perlin 噪声生成效果 |

### 4. 混合传输处理器 (XP) — Blend/XferProcessor

| 文件 | 说明 |
|------|------|
| GrPorterDuffXferProcessor.h / GrPorterDuffXferProcessor.cpp | Porter-Duff 混合模式处理器工厂 |
| GrCoverageSetOpXP.h / GrCoverageSetOpXP.cpp | 覆盖率集合运算处理器工厂 |
| GrCustomXfermode.h / GrCustomXfermode.cpp | 自定义混合模式（高级混合方程） |
| GrDisableColorXP.h / GrDisableColorXP.cpp | 禁用颜色输出处理器工厂 |

### 5. 文本渲染效果 (GP) — Text Geometry Processors

| 文件 | 说明 |
|------|------|
| GrBitmapTextGeoProc.h / GrBitmapTextGeoProc.cpp | 位图文字几何处理器 |
| GrDistanceFieldGeoProc.h / GrDistanceFieldGeoProc.cpp | 距离场文字几何处理器（A8/Path/LCD 三种模式） |
| GrShadowGeoProc.h / GrShadowGeoProc.cpp | 圆角矩形阴影几何处理器 |

### 6. 图集辅助 — Atlas Helpers

| 文件 | 说明 |
|------|------|
| GrAtlasedShaderHelpers.h | 图集纹理着色器辅助函数 |
| GrModulateAtlasCoverageEffect.h / GrModulateAtlasCoverageEffect.cpp | 图集覆盖率调制效果 |

## 关键类与函数

### 1. GrTextureEffect - 纹理采样效果

`GrTextureEffect` 是最基础也最常用的片段处理器之一，负责从 GPU 纹理中采样颜色。它支持多种创建模式：

```cpp
// 基本纹理采样（钳位模式）
static std::unique_ptr<GrFragmentProcessor> Make(
    GrSurfaceProxyView, SkAlphaType, const SkMatrix&,
    GrSamplerState::Filter, GrSamplerState::MipmapMode);

// 带完整采样器状态的纹理采样
static std::unique_ptr<GrFragmentProcessor> Make(
    GrSurfaceProxyView, SkAlphaType, const SkMatrix&,
    GrSamplerState, const GrCaps&, const float border[4]);

// 子集纹理采样 - 限定采样区域
static std::unique_ptr<GrFragmentProcessor> MakeSubset(
    GrSurfaceProxyView, SkAlphaType, const SkMatrix&,
    GrSamplerState, const SkRect& subset, const GrCaps&, ...);
```

内部使用 `ShaderMode` 枚举来控制着色器中环绕模式的实现策略，包括硬件模式（kNone）、着色器钳位（kClamp）、重复（kRepeat）、镜像重复（kMirrorRepeat）和边界颜色（kClampToBorder）等。

### 2. GrSkSLFP - SkSL 运行时效果桥接

`GrSkSLFP` 是连接 Skia 的 `SkRuntimeEffect`（SkSL 运行时效果）与 Ganesh GPU 后端的关键桥接类。它允许用户编写的 SkSL 着色器代码在 GPU 管线中作为片段处理器执行：

```cpp
// 使用变参模板工厂方法创建，自动匹配 uniform 名称和类型
template <typename... Args>
static std::unique_ptr<GrSkSLFP> Make(
    const SkRuntimeEffect* effect, const char* name,
    std::unique_ptr<GrFragmentProcessor> inputFP,
    OptFlags optFlags, Args&&... args);

// 使用原始数据 blob 创建
static std::unique_ptr<GrSkSLFP> MakeWithData(
    sk_sp<SkRuntimeEffect> effect, const char* name,
    sk_sp<SkColorSpace> dstColorSpace, ...);
```

该类使用了独特的内存布局策略——uniform 数据直接追加存储在 FP 对象后面，避免了额外的堆分配。同时支持 uniform 的"特化"（Specialize）机制，将特定值内联到着色器代码中以提高性能。

### 3. GrBlendFragmentProcessor - 混合片段处理器

提供片段处理器级别的颜色混合功能，支持所有 `SkBlendMode` 模式：

```cpp
// 运行时选择混合模式（共享混合逻辑减少着色器数量）
std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> src,
    std::unique_ptr<GrFragmentProcessor> dst,
    SkBlendMode mode, bool shareBlendLogic = true);

// 编译时固定混合模式（模板参数，略微降低复杂度）
template <SkBlendMode mode>
std::unique_ptr<GrFragmentProcessor> Make(
    std::unique_ptr<GrFragmentProcessor> src,
    std::unique_ptr<GrFragmentProcessor> dst);
```

### 4. GrPorterDuffXPFactory - Porter-Duff 混合传输处理器

管理 Porter-Duff 混合模式的 `GrXferProcessor` 创建，是渲染管线最终颜色混合阶段的核心：

```cpp
static const GrXPFactory* Get(SkBlendMode blendMode);
static sk_sp<const GrXferProcessor> MakeSrcOverXferProcessor(
    const GrProcessorAnalysisColor&, GrProcessorAnalysisCoverage, const GrCaps&);
static sk_sp<const GrXferProcessor> MakeNoCoverageXP(SkBlendMode);
static const GrXferProcessor& SimpleSrcOverXP();  // 全局单例
```

特别针对 src-over（最常见的混合模式）进行了专门优化，`SimpleSrcOverXP()` 返回一个全局单例以避免重复创建。

### 5. GrBezierEffect - 贝塞尔曲线效果

包含 `GrConicEffect` 和 `GrQuadEffect` 两个几何处理器，基于 Loop-Blinn 算法实现 GPU 上的曲线渲染：

```cpp
// GrConicEffect - 圆锥曲线（椭圆、双曲线、抛物线）
// 隐式方程 K^2 - LM，使用一阶 Taylor 近似计算距离
static GrGeometryProcessor* Make(SkArenaAlloc* arena,
    const SkPMColor4f& color, const SkMatrix& viewMatrix,
    const GrCaps& caps, const SkMatrix& localMatrix,
    bool usesLocalCoords, uint8_t coverage = 0xff);

// GrQuadEffect - 二次曲线
// 规范坐标 0=u^2-v，控制点坐标为 {0,0}, {1/2,0}, {1,1}
static GrGeometryProcessor* Make(/* 同上参数列表 */);
```

### 6. GrDistanceFieldGeoProc - 距离场文字渲染

包含三个几何处理器类，用于基于有符号距离场（SDF）的文字渲染：

- **`GrDistanceFieldA8TextGeoProc`**：A8 格式距离场文字，使用 smoothstep 函数在 0.5 附近平滑化
- **`GrDistanceFieldPathGeoProc`**：路径距离场渲染，不做 Gamma 校正
- **`GrDistanceFieldLCDTextGeoProc`**：LCD 子像素文字渲染，带 RGB 距离调整（`DistanceAdjust`）

这些处理器支持多种标志位（`GrDistanceFieldEffectFlags`），控制相似性变换、仅缩放、透视、LCD 显示方向等行为。

### 7. GrConvexPolyEffect / GrOvalEffect / GrRRectEffect - 几何裁剪效果

这组片段处理器用于在 GPU 上实现高效的几何裁剪：

- **`GrConvexPolyEffect`**：最多支持 8 条边的凸多边形裁剪，使用半平面方程计算覆盖率
- **`GrOvalEffect`**：椭圆裁剪效果
- **`GrRRectEffect`**：圆角矩形裁剪效果，支持抗锯齿

### 8. GrYUVtoRGBEffect - YUV 到 RGB 转换

将 YUV 颜色空间的纹理平面转换为 RGB 颜色空间，支持多种 YUV 布局（`SkYUVAInfo::YUVALocations`）和颜色空间（`SkYUVColorSpace`），常用于视频帧渲染。

### 9. GrBicubicEffect - 双三次插值

实现高质量的双三次纹理过滤，内置 Mitchell（1/3, 1/3）和 Catmull-Rom（0, 1/2）两种常用核函数。支持三种方向模式：仅 X 方向（kX）、仅 Y 方向（kY）和双向（kXY）。

### 10. GrPerlinNoise2Effect - Perlin 噪声

实现 GPU 加速的 Perlin 噪声生成，支持 fractal noise 和 turbulence 两种类型，可配置多个八度（octaves）和平铺缝合（stitch tiles）。

## 依赖关系

### 上游依赖（被谁使用）

| 上游模块 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrPipeline` | 渲染管线组装，管理 FP 链和 XP |
| `src/gpu/ganesh/ops/` | 绘图操作类（GrOp 子类）创建并使用这些效果处理器 |
| `src/gpu/ganesh/GrDrawOpAtlas` | 文字图集管理，使用文字相关的几何处理器 |
| `src/gpu/ganesh/GrClipStackClip` | 裁剪栈实现，使用几何裁剪效果（Convex/Oval/RRect） |
| `src/gpu/ganesh/SkGr.cpp` | Skia 到 Ganesh 的转换层，将 SkShader 等转换为 FP |
| `src/image/` | 图像处理，使用 GrTextureEffect 和 GrYUVtoRGBEffect |

### 下游依赖（依赖谁）

| 下游模块 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrFragmentProcessor` | 所有 FP 的基类 |
| `src/gpu/ganesh/GrGeometryProcessor` | 所有 GP 的基类 |
| `src/gpu/ganesh/GrXferProcessor` | 所有 XP 的基类和工厂基类 |
| `src/gpu/ganesh/glsl/` | GLSL 着色器代码生成框架 |
| `src/gpu/ganesh/GrSurfaceProxyView` | GPU 纹理代理视图 |
| `src/gpu/ganesh/GrSamplerState` | 纹理采样器状态 |
| `src/gpu/ganesh/GrCaps` | GPU 能力查询 |
| `src/gpu/ganesh/GrProcessorUnitTest` | 单元测试支持宏 |
| `include/effects/SkRuntimeEffect.h` | SkSL 运行时效果（GrSkSLFP 依赖） |
| `include/core/SkBlendMode.h` | 混合模式枚举 |

### 外部依赖

- **SkSL 编译器**：`GrSkSLFP` 依赖 SkSL 运行时效果系统
- **skcms**：颜色管理库（通过 `GrColorSpaceXform` 间接使用）
- **GPU 后端 API**：最终由 GL/Vulkan/Metal/Dawn 等后端消费着色器代码

## 设计模式分析

### 1. 工厂方法模式 (Factory Method)

所有处理器都使用静态 `Make()` 工厂方法创建，而非公开构造函数。这允许在创建时进行验证和优化：

```cpp
// GrConvexPolyEffect 的 Make 会验证边数
static GrFPResult Make(std::unique_ptr<GrFragmentProcessor> inputFP,
                       GrClipEdgeType edgeType, int n, const float edges[]) {
    if (n <= 0 || n > kMaxEdges) {
        return GrFPFailure(std::move(inputFP));  // 失败时返回输入 FP
    }
    return GrFPSuccess(/* ... */);
}
```

### 2. 策略模式 (Strategy)

XP 工厂（`GrXPFactory`）是典型的策略模式。`GrPorterDuffXPFactory`、`GrCoverageSetOpXPFactory`、`GrDisableColorXPFactory` 和 `GrCustomXfermode` 实现不同的混合策略，管线在运行时根据混合模式选择合适的工厂：

```cpp
// 根据 SkBlendMode 获取对应的 XP 工厂
const GrXPFactory* Get(SkBlendMode blendMode);
```

### 3. 组合模式 (Composite)

片段处理器形成树状结构。每个 FP 可以注册子 FP（通过 `registerChild()`），构成递归的处理器树。例如 `GrPerlinNoise2Effect` 内部组合了两个 `GrTextureEffect` 作为子处理器。

### 4. 模板方法模式 (Template Method)

基类 `GrFragmentProcessor` 定义了处理器的骨架方法：
- `onMakeProgramImpl()` - 创建着色器代码生成器
- `onAddToKey()` - 生成缓存键
- `onIsEqual()` - 等价性比较
- `constantOutputForConstantInput()` - 常量折叠优化

### 5. 享元模式 (Flyweight)

`GrPorterDuffXPFactory` 和 `GrDisableColorXPFactory` 使用 `constexpr` 构造函数和全局静态实例，避免重复创建：

```cpp
// GrDisableColorXPFactory - 全局单例
inline const GrDisableColorXPFactory* GrDisableColorXPFactory::Get() {
    static constexpr const GrDisableColorXPFactory gDisableColorXPFactory;
    return &gDisableColorXPFactory;
}
```

### 6. 变参模板链式处理 (Variadic Template Chaining)

`GrSkSLFP::Make()` 使用 C++ 变参模板实现了类型安全的命名参数传递，在编译时验证 uniform 名称和类型的匹配：

```cpp
auto fp = GrSkSLFP::Make(effect, "my_effect", nullptr, OptFlags::kNone,
                          "child", std::move(childFP),
                          "scale", scaleVal,
                          "pt", ptVal);
```

### 7. Arena 分配模式

几何处理器使用 `SkArenaAlloc` 分配，避免频繁的堆分配/释放，提高渲染帧内的内存分配性能：

```cpp
static GrGeometryProcessor* Make(SkArenaAlloc* arena, ...) {
    return arena->make([&](void* ptr) {
        return new (ptr) GrConicEffect(color, viewMatrix, ...);
    });
}
```

## 数据流

```
1. 用户 API 调用
   SkCanvas::drawRect(paint)
        │
        v
2. 绘图操作创建
   GrFillRRectOp / GrDrawAtlasOp / ...
        │
        v
3. 效果处理器树构建
   ┌──────────────────────────────────────────────────────────┐
   │  GrGeometryProcessor: 顶点属性 -> 顶点着色器输入         │
   │  GrFragmentProcessor 树:                                 │
   │    GrMatrixEffect                                        │
   │      └─> GrTextureEffect (纹理采样)                      │
   │    GrBlendFragmentProcessor                              │
   │      ├─> 子 FP (src)                                     │
   │      └─> 子 FP (dst)                                     │
   │  GrXferProcessor: 最终颜色混合                            │
   └──────────────────────────────────────────────────────────┘
        │
        v
4. GrPipeline 组装
   将 GP、FP 链、XP 组装为完整管线
        │
        v
5. 着色器程序生成 (通过 glsl/ 模块)
   GrGLSLProgramBuilder:
     a. GP.makeProgramImpl() -> 发射顶点着色器代码
     b. FP.onMakeProgramImpl() -> 发射片段着色器代码（递归遍历 FP 树）
     c. XP.makeProgramImpl() -> 发射混合代码
        │
        v
6. 着色器编译与缓存
   通过 onAddToKey() 生成的键进行着色器程序缓存
        │
        v
7. GPU 执行
   顶点数据 -> 顶点着色器(GP) -> 光栅化 -> 片段着色器(FPs) -> 混合(XP) -> 帧缓冲
```

### 关键数据流路径

**纹理渲染路径**：
```
SkImage -> GrSurfaceProxyView -> GrTextureEffect::Make() ->
  GrMatrixEffect::Make(matrix, textureEffect) -> 添加到 GrPipeline
```

**文字渲染路径**：
```
SkFont -> GrAtlasManager -> GrBitmapTextGeoProc 或 GrDistanceFieldA8TextGeoProc ->
  GrAtlasedShaderHelpers (纹理索引/UV 变量) -> 多纹理查找
```

**裁剪路径**：
```
SkClipStack -> GrClipStackClip ->
  GrConvexPolyEffect::Make() / GrOvalEffect::Make() / GrRRectEffect::Make() ->
  覆盖率作为 FP 树的一部分应用
```

**运行时效果路径**：
```
SkRuntimeEffect (SkSL) -> GrSkSLFP::Make(effect, uniforms, children) ->
  ProgramImpl 在着色器生成阶段发射 SkSL 代码 -> SkSL 到 GLSL/SPIR-V/MSL 编译
```

## 相关文档与参考

### 相关目录

| 路径 | 说明 |
|------|------|
| `src/gpu/ganesh/glsl/` | GLSL 着色器代码生成框架，处理器的 ProgramImpl 使用此框架发射代码 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 片段处理器基类定义 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 几何处理器基类定义 |
| `src/gpu/ganesh/GrXferProcessor.h` | 混合传输处理器基类及工厂定义 |
| `src/gpu/ganesh/GrProcessor.h` | 所有处理器的最终基类 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线，组装处理器 |
| `src/gpu/ganesh/ops/` | 绘图操作类，创建并使用效果处理器 |
| `include/effects/SkRuntimeEffect.h` | SkSL 运行时效果公共 API |
| `src/gpu/ganesh/GrShaderCaps.h` | GPU 着色器能力查询 |

### 算法参考

- **Loop-Blinn 曲线渲染**：`GrBezierEffect` 基于 "Resolution Independent Curve Rendering using Programmable Graphics Hardware" (Loop & Blinn, 2005)
- **距离场文字渲染**：`GrDistanceFieldGeoProc` 基于 "Improved Alpha-Tested Magnification for Vector Textures and Special Effects" (Valve, 2007)
- **Perlin 噪声**：`GrPerlinNoise2Effect` 实现 Ken Perlin 的经典噪声算法
- **双三次插值**：`GrBicubicEffect` 实现 Mitchell-Netravali 和 Catmull-Rom 滤波核
- **距离近似**：`GrBezierEffect` 注释中引用了 Gabriel Taubin 的论文 "Distance Approximations for Rasterizing Implicit Curves"

### 处理器类型速查表

| 类名 | 类型 | 用途 |
|------|------|------|
| `GrTextureEffect` | FP | 纹理采样，支持子集/环绕/边界 |
| `GrBicubicEffect` | FP | 双三次插值纹理过滤 |
| `GrSkSLFP` | FP | SkSL 运行时效果桥接 |
| `GrBlendFragmentProcessor` | FP | 两个 FP 的颜色混合 |
| `GrMatrixEffect` | FP | 坐标矩阵变换 |
| `GrConvexPolyEffect` | FP | 凸多边形裁剪 |
| `GrOvalEffect` | FP | 椭圆裁剪 |
| `GrRRectEffect` | FP | 圆角矩形裁剪 |
| `GrYUVtoRGBEffect` | FP | YUV->RGB 转换 |
| `GrPerlinNoise2Effect` | FP | Perlin 噪声生成 |
| `ColorTableEffect` | FP | 颜色查找表 |
| `GrModulateAtlasCoverageEffect` | FP | 图集覆盖率调制 |
| `GrConicEffect` | GP | 圆锥曲线渲染 |
| `GrQuadEffect` | GP | 二次曲线渲染 |
| `GrBitmapTextGeoProc` | GP | 位图文字渲染 |
| `GrDistanceFieldA8TextGeoProc` | GP | SDF A8 文字渲染 |
| `GrDistanceFieldPathGeoProc` | GP | SDF 路径渲染 |
| `GrDistanceFieldLCDTextGeoProc` | GP | SDF LCD 文字渲染 |
| `GrRRectShadowGeoProc` | GP | 圆角矩形阴影 |
| `GrPorterDuffXPFactory` | XP Factory | Porter-Duff 混合 |
| `GrCoverageSetOpXPFactory` | XP Factory | 覆盖率 CSG 运算 |
| `GrCustomXfermode` | XP Factory | 高级混合方程 |
| `GrDisableColorXPFactory` | XP Factory | 禁用颜色输出 |
