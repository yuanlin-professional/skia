# SkImageFilterTypes

> 源文件: src/core/SkImageFilterTypes.h, src/core/SkImageFilterTypes.cpp

## 概述

`SkImageFilterTypes` 是 Skia 图像滤镜系统的核心类型定义模块，位于 `skif` 命名空间下。该模块提供了一套完整的类型安全坐标空间系统，用于在图像滤镜处理过程中管理不同坐标空间之间的转换。它通过模板类实现了参数空间 (ParameterSpace)、设备空间 (DeviceSpace) 和层空间 (LayerSpace) 之间的类型安全映射，并提供了 `FilterResult`、`Mapping`、`Context` 和 `Backend` 等关键类来支持整个图像滤镜 DAG（有向无环图）的求值过程。

该模块的设计目标是：
1. 通过类型系统强制正确的坐标空间使用
2. 延迟执行图像操作以优化性能
3. 支持复杂的滤镜组合和变换
4. 提供统一的后端抽象（光栅化、GPU 等）

## 架构位置

`SkImageFilterTypes` 位于 Skia 核心渲染管线的图像滤镜层，是连接高层图像滤镜 API 和底层设备渲染的关键桥梁：

```
SkImageFilter (公共 API)
        ↓
SkImageFilter_Base (内部基类)
        ↓
SkImageFilterTypes (坐标空间类型系统) ← 本模块
        ↓
SkDevice / SkSpecialImage (设备抽象)
```

该模块被以下组件依赖：
- 所有具体的图像滤镜实现（如 SkBlurImageFilter、SkColorFilterImageFilter 等）
- SkCanvas 的 saveLayer 机制
- GPU 和 CPU 后端的图像滤镜渲染路径

## 主要类与结构体

### 坐标空间模板类

| 类名 | 继承关系 | 用途 |
|------|---------|------|
| `ParameterSpace<T>` | - | 封装参数/局部坐标空间的几何数据 |
| `DeviceSpace<T>` | - | 封装设备坐标空间的几何数据 |
| `LayerSpace<T>` | - | 封装层坐标空间的几何数据（主要工作空间） |

### LayerSpace 特化

LayerSpace 为多种几何类型提供了特化实现：

| 特化类型 | 关键成员变量 | 说明 |
|---------|-------------|------|
| `LayerSpace<SkIRect>` | `SkIRect fData` | 整数矩形，支持交集、并集等操作 |
| `LayerSpace<SkRect>` | `SkRect fData` | 浮点矩形，支持精确变换 |
| `LayerSpace<SkIPoint>` | `SkIPoint fData` | 整数点坐标 |
| `LayerSpace<SkPoint>` | `SkPoint fData` | 浮点点坐标 |
| `LayerSpace<IVector>` | `IVector fData` | 整数方向向量 |
| `LayerSpace<Vector>` | `Vector fData` | 浮点方向向量 |
| `LayerSpace<SkISize>` | `SkISize fData` | 整数尺寸 |
| `LayerSpace<SkSize>` | `SkSize fData` | 浮点尺寸 |
| `LayerSpace<SkMatrix>` | `SkMatrix fData` | 层内变换矩阵 |

### 核心类

| 类名 | 继承关系 | 关键成员变量 | 用途 |
|------|---------|-------------|------|
| `Mapping` | - | `fLayerToDevMatrix`, `fParamToLayerMatrix`, `fDevToLayerMatrix` | 管理三个坐标空间之间的映射关系 |
| `FilterResult` | - | `fImage`, `fTransform`, `fTileMode`, `fSamplingOptions`, `fColorFilter`, `fLayerBounds` | 表示延迟求值的图像结果 |
| `FilterResult::Builder` | - | `fContext`, `fInputs` | 用于构建新的 FilterResult |
| `Context` | - | `fBackend`, `fMapping`, `fDesiredOutput`, `fSource`, `fColorSpace` | 封装滤镜求值的上下文信息 |
| `Backend` | `SkRefCnt` | `fCache`, `fSurfaceProps`, `fColorType` | 后端抽象接口 |
| `RasterBackend` | `Backend` | - | CPU 光栅化后端实现 |

### 辅助类型

```cpp
enum class MatrixCapability {
    kTranslate,        // 仅支持平移
    kScaleTranslate,   // 支持缩放和平移
    kComplex           // 支持任意复杂变换
};

enum class PixelBoundary {
    kUnknown,          // 边界像素值未知
    kTransparent,      // 边界像素为透明黑色
    kInitialized       // 边界像素已初始化
};

struct Stats {
    int fNumVisitedImageFilters;     // 访问的滤镜数量
    int fNumCacheHits;               // 缓存命中次数
    int fNumOffscreenSurfaces;       // 离屏表面数量
    int fNumShaderClampedDraws;      // 着色器限制绘制次数
    int fNumShaderBasedTilingDraws;  // 基于着色器的平铺绘制次数
};
```

## 公共 API 函数

### Mapping 类

```cpp
// 构造函数
explicit Mapping(const SkM44& paramToLayer);
Mapping(const SkM44& layerToDev, const SkM44& devToLayer, const SkM44& paramToLayer);

// CTM 分解
bool decomposeCTM(const SkM44& ctm, const SkImageFilter* filter,
                  const ParameterSpace<SkPoint>& representativePt);
bool decomposeCTM(const SkM44& ctm, MatrixCapability capability,
                  const ParameterSpace<SkPoint>& representativePt);

// 坐标空间转换
template<typename T>
LayerSpace<T> paramToLayer(const ParameterSpace<T>& paramGeometry) const;

template<typename T>
LayerSpace<T> deviceToLayer(const DeviceSpace<T>& devGeometry) const;

template<typename T>
DeviceSpace<T> layerToDevice(const LayerSpace<T>& layerGeometry) const;

// 层空间调整
bool adjustLayerSpace(const SkM44& layer);
void applyOrigin(const LayerSpace<SkIPoint>& origin);
void concatLocal(const SkMatrix& local);
```

### FilterResult 类

```cpp
// 静态工厂方法
static FilterResult MakeFromPicture(const Context& ctx, sk_sp<SkPicture> pic,
                                    ParameterSpace<SkRect> cullRect);
static FilterResult MakeFromShader(const Context& ctx, sk_sp<SkShader> shader, bool dither);
static FilterResult MakeFromImage(const Context& ctx, sk_sp<SkImage> image,
                                  SkRect srcRect, ParameterSpace<SkRect> dstRect,
                                  const SkSamplingOptions& sampling);

// 图像操作
FilterResult applyCrop(const Context& ctx, const LayerSpace<SkIRect>& crop,
                       SkTileMode tileMode = SkTileMode::kDecal) const;
FilterResult applyTransform(const Context& ctx, const LayerSpace<SkMatrix>& transform,
                           const SkSamplingOptions& sampling) const;
FilterResult applyColorFilter(const Context& ctx, sk_sp<SkColorFilter> colorFilter) const;

// 访问器
LayerSpace<SkIRect> layerBounds() const;
SkTileMode tileMode() const;
SkSamplingOptions sampling() const;
const SkColorFilter* colorFilter() const;

// 图像提取
sk_sp<SkSpecialImage> imageAndOffset(const Context& ctx, SkIPoint* offset) const;
std::pair<sk_sp<SkSpecialImage>, LayerSpace<SkIPoint>> imageAndOffset(const Context& ctx) const;

// 渲染
void draw(const Context& ctx, SkDevice* target, const SkBlender* blender) const;
```

### FilterResult::Builder 类

```cpp
// 构造函数
explicit Builder(const Context& context);

// 添加输入
Builder& add(const FilterResult& input,
             std::optional<LayerSpace<SkIRect>> sampleBounds = {},
             SkEnumBitMask<ShaderFlags> inputFlags = ShaderFlags::kNone,
             const SkSamplingOptions& inputSampling = kDefaultSampling);

// 组合操作
FilterResult merge();  // 使用 src-over 混合合并所有输入
FilterResult blur(const LayerSpace<SkSize>& sigma);  // 高斯模糊

// 通用着色器求值
template<typename ShaderFn>
FilterResult eval(ShaderFn shaderFn,
                  std::optional<LayerSpace<SkIRect>> explicitOutput = {},
                  bool evaluateInParameterSpace = false);
```

### Context 类

```cpp
// 构造函数
Context(sk_sp<Backend> backend, const Mapping& mapping,
        const LayerSpace<SkIRect>& desiredOutput, const FilterResult& source,
        const SkColorSpace* colorSpace, Stats* stats);

// 访问器
const Backend* backend() const;
const Mapping& mapping() const;
const LayerSpace<SkIRect>& desiredOutput() const;
SkColorSpace* colorSpace() const;
const FilterResult& source() const;

// 上下文派生
Context withNewMapping(const Mapping& mapping) const;
Context withNewDesiredOutput(const LayerSpace<SkIRect>& desiredOutput) const;
Context withNewColorSpace(SkColorSpace* cs) const;
Context withNewSource(const FilterResult& source) const;
```

### Backend 类

```cpp
// 纯虚函数（子类必须实现）
virtual sk_sp<SkDevice> makeDevice(SkISize size, sk_sp<SkColorSpace> cs,
                                   const SkSurfaceProps* props = nullptr) const = 0;
virtual sk_sp<SkSpecialImage> makeImage(const SkIRect& subset,
                                        sk_sp<SkImage> image) const = 0;
virtual sk_sp<SkImage> getCachedBitmap(const SkBitmap& data) const = 0;
virtual const SkBlurEngine* getBlurEngine() const = 0;

// 访问器
const SkSurfaceProps& surfaceProps() const;
SkColorType colorType() const;
SkImageFilterCache* cache() const;
```

## 内部实现细节

### 坐标空间转换系统

模块的核心是类型安全的坐标空间系统，通过三个模板类实现：

1. **ParameterSpace**: 表示滤镜参数定义的局部坐标空间
2. **DeviceSpace**: 表示最终绘制目标的设备坐标空间
3. **LayerSpace**: 表示滤镜求值的共享层坐标空间

这三个空间通过 `Mapping` 类进行转换，`Mapping` 内部维护两个 4x4 矩阵：
- `fParamToLayerMatrix`: 参数空间到层空间
- `fLayerToDevMatrix`: 层空间到设备空间

### FilterResult 延迟求值机制

`FilterResult` 采用延迟求值策略，避免产生不必要的中间图像。它包含以下可延迟的操作：

1. **平铺模式** (`fTileMode`): 通过 `SkTileMode` 控制图像边界外的采样行为
2. **变换** (`fTransform`): 层空间内的矩阵变换
3. **采样** (`fSamplingOptions`): 图像采样质量设置
4. **颜色滤镜** (`fColorFilter`): 应用于采样后的颜色变换
5. **裁剪** (`fLayerBounds`): 限制输出区域

这些操作按照特定顺序组合：平铺 → 变换/采样 → 颜色滤镜 → 裁剪

### 边界分析系统

`FilterResult::analyzeBounds()` 实现了复杂的边界分析，决定是否需要解析为实际图像：

```cpp
enum class BoundsAnalysis {
    kSimple = 0,                      // 可直接绘制
    kDstBoundsNotCovered = 1 << 0,    // 目标区域未完全覆盖
    kHasLayerFillingEffect = 1 << 1,  // 存在填充层边界的效果
    kRequiresLayerCrop = 1 << 2,      // 需要应用层裁剪
    kRequiresShaderTiling = 1 << 3,   // 需要着色器平铺
    kRequiresDecalInLayerSpace = 1 << 4  // 需要层空间的 decal 处理
};
```

该分析考虑以下因素：
- 变换的类型（整数平移、缩放、复杂变换）
- 像素对齐情况
- 采样半径和边界像素
- 硬件平铺能力

### AutoSurface 助手类

`FilterResult::AutoSurface` 是一个 RAII 类，用于创建临时渲染表面：

```cpp
AutoSurface surface{ctx, dstBounds, boundary, renderInParameterSpace};
if (surface) {
    surface->drawFoo(...);
}
return surface.snap();  // 自动处理分配失败
```

它自动处理：
- 表面分配和坐标系统设置
- 透明边界像素的填充
- 裁剪区域的配置
- 将结果转换为 `FilterResult`

### CTM 分解算法

`Mapping::decomposeCTM()` 根据滤镜的能力将总变换矩阵分解为两部分：

```cpp
总 CTM = 层到设备矩阵 × 参数到层矩阵
```

分解策略取决于 `MatrixCapability`：
- **kTranslate**: 所有变换都在后处理（层到设备）
- **kScaleTranslate**: 如果 CTM 是缩放平移，层矩阵 = CTM
- **kComplex**: 提取缩放到层矩阵，其余到后处理矩阵

### 周期平铺优化

`periodic_axis_transform()` 函数检测当周期平铺（repeat/mirror）只覆盖输出一次时，可以简化为单纯的变换：

```cpp
auto periodicTransform = periodic_axis_transform(tileMode, crop, output);
if (periodicTransform) {
    return applyTransform(ctx, *periodicTransform, kDefaultSampling);
}
```

这避免了设置昂贵的着色器平铺。

### 像素边界追踪

`PixelBoundary` 枚举追踪图像边界外像素的状态：
- **kUnknown**: 未初始化，采样需要使用 decal 模式
- **kTransparent**: 已知为透明黑色，可优化为 clamp 模式
- **kInitialized**: 已初始化，但值未知

这允许在某些情况下将 decal 平铺降级为更高效的 clamp 平铺。

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 类型 |
|------|------|------|
| `SkSpecialImage` | 表示受限子集的图像 | 核心类型 |
| `SkDevice` | 设备抽象接口 | 渲染目标 |
| `SkM44` / `SkMatrix` | 矩阵变换 | 数学运算 |
| `SkColorFilter` | 颜色变换 | 滤镜效果 |
| `SkSamplingOptions` | 采样配置 | 图像质量 |
| `SkTileMode` | 平铺模式 | 边界处理 |
| `SkBlurEngine` | 模糊实现 | 特殊效果 |
| `SkImageFilterCache` | 滤镜缓存 | 性能优化 |
| `SkShader` | 着色器抽象 | 渲染效果 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `SkImageFilter_Base` | 所有图像滤镜的基类实现 |
| `SkBlurImageFilter` | 模糊滤镜实现 |
| `SkColorFilterImageFilter` | 颜色滤镜实现 |
| `SkComposeImageFilter` | 组合滤镜实现 |
| `SkCropImageFilter` | 裁剪滤镜实现 |
| `SkCanvas` | saveLayer 图像滤镜集成 |
| GPU 后端 | GPU 图像滤镜路径 |

## 设计模式与设计决策

### 1. 类型安全的坐标空间系统

**模式**: Phantom Type Pattern（幽灵类型模式）

使用模板类封装相同的底层类型（如 `SkRect`），但通过不同的包装类型（`ParameterSpace`、`DeviceSpace`、`LayerSpace`）在编译期强制类型安全：

```cpp
ParameterSpace<SkRect> paramRect;
LayerSpace<SkRect> layerRect = mapping.paramToLayer(paramRect);
// 编译错误：不能直接混用不同坐标空间的值
// layerRect = paramRect;
```

**优势**:
- 编译期错误检测，避免坐标空间混淆
- 零运行时开销
- API 自说明性强

### 2. 延迟求值与操作合并

**模式**: Lazy Evaluation + Command Pattern

`FilterResult` 不立即执行图像操作，而是记录待执行的操作序列。只有在真正需要像素数据时才解析：

```cpp
FilterResult result = ...;
result = result.applyCrop(ctx, crop, tileMode);           // 延迟
result = result.applyTransform(ctx, transform, sampling); // 延迟
result = result.applyColorFilter(ctx, colorFilter);       // 延迟
// 只有在调用 imageAndOffset() 或 draw() 时才实际执行
```

**优势**:
- 多个操作可以合并为单次渲染
- 减少中间图像分配
- 提升整体性能

### 3. Builder 模式用于复杂构建

`FilterResult::Builder` 使用 Builder 模式管理多输入的滤镜操作：

```cpp
FilterResult::Builder builder(ctx);
builder.add(input1, sampleBounds1, flags1, sampling1)
       .add(input2, sampleBounds2, flags2, sampling2);
return builder.eval([](SkSpan<sk_sp<SkShader>> inputs) {
    return SkShaders::Blend(mode, inputs[0], inputs[1]);
});
```

**优势**:
- 灵活的输入配置
- 延迟着色器创建直到所有输入就绪
- 自动优化输出边界

### 4. 策略模式的后端抽象

`Backend` 抽象类定义接口，具体后端（`RasterBackend`、GPU Backend）实现不同策略：

```cpp
class Backend {
    virtual sk_sp<SkDevice> makeDevice(...) const = 0;
    virtual const SkBlurEngine* getBlurEngine() const = 0;
};
```

**优势**:
- 算法和实现解耦
- 易于添加新后端
- 统一的接口保证一致性

### 5. 边界分析驱动的优化决策

通过详细的边界分析，系统在多个优化路径中做出智能选择：

```cpp
auto analysis = analyzeBounds(dstBounds);
if (!(analysis & BoundsAnalysis::kRequiresShaderTiling)) {
    // 使用硬件平铺，更快
} else {
    // 使用着色器平铺，更慢但正确
}
```

**设计决策**:
- 性能优化与正确性之间的平衡
- 根据实际需求选择最优路径
- 避免过度工程

### 6. RAII 管理资源生命周期

`AutoSurface` 使用 RAII 确保表面资源正确管理：

```cpp
{
    AutoSurface surface{ctx, bounds, boundary, renderInParameterSpace};
    if (surface) {
        surface->draw(...);
    }
    // 自动清理和快照
}
```

## 性能考量

### 1. 延迟求值减少中间分配

通过延迟操作执行，系统能够：
- 合并多个变换为单次采样
- 跳过不影响最终结果的操作
- 减少离屏表面分配次数

### 2. 整数平移快速路径

对于整数对齐的平移变换，使用优化的子集视图而非实际渲染：

```cpp
if (is_nearly_integer_translation(fTransform, &origin)) {
    return subset(origin, bounds);  // 零成本
}
```

### 3. 硬件平铺 vs 着色器平铺

系统优先使用 GPU 硬件平铺能力（当图像子集对齐到纹理边界时），降级到着色器平铺只在必要时：

```cpp
if (all(edgeMask | hwEdge)) {
    // 使用快速硬件平铺
} else {
    analysis |= BoundsAnalysis::kRequiresShaderTiling;
}
```

### 4. 双精度计算防止溢出

对于大坐标值，使用 `double` 中间计算防止 32 位整数溢出：

```cpp
double l = (double)matrix.getScaleX()*geom.fLeft + (double)matrix.getTranslateX();
// 然后安全饱和到 int
return {sk_double_saturate2int(std::floor(l + kRoundEpsilon)), ...};
```

### 5. 缓存系统

`Backend` 集成 `SkImageFilterCache`，避免重复计算相同的滤镜子图：

```cpp
SkImageFilterCache* cache() const { return fCache.get(); }
```

### 6. 像素边界优化

跟踪 `PixelBoundary` 状态允许：
- 将 decal 采样降级为更快的 clamp 采样
- 避免不必要的透明边界处理
- 减少着色器复杂度

### 7. 统计信息收集

`Stats` 结构收集性能指标，用于分析和优化：

```cpp
void markNewSurface() const;      // 追踪表面分配
void markCacheHit() const;        // 追踪缓存效率
void markShaderBasedTilingRequired(SkTileMode) const;  // 追踪昂贵操作
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkImageFilter_Base.h` | 使用者 | 图像滤镜基类，使用坐标空间系统 |
| `src/core/SkSpecialImage.h` | 依赖 | 受限子集图像表示 |
| `src/core/SkDevice.h` | 依赖 | 设备抽象接口 |
| `src/core/SkBlurEngine.h` | 依赖 | 模糊引擎抽象 |
| `src/core/SkImageFilterCache.h` | 依赖 | 滤镜结果缓存 |
| `src/effects/imagefilters/*.cpp` | 使用者 | 各种具体滤镜实现 |
| `src/gpu/ganesh/GrImageFilter.cpp` | 使用者 | GPU 滤镜路径 |
| `include/core/SkImageFilter.h` | 间接使用者 | 公共图像滤镜 API |

---

**注**: 本模块是 Skia 图像滤镜系统的核心，理解其坐标空间系统和延迟求值机制对于实现自定义图像滤镜至关重要。代码总行数约 3520 行，涵盖了从类型定义、坐标转换、边界分析到实际渲染的完整流程。
