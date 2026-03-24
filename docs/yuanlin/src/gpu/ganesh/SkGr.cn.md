# SkGr

> 源文件
> - `src/gpu/ganesh/SkGr.h`
> - `src/gpu/ganesh/SkGr.cpp`

## 概述

`SkGr` 是 Skia 的 Ganesh GPU 后端中的核心桥接模块,负责在 Skia 的 CPU 端数据结构与 Ganesh GPU 渲染对象之间进行转换。该模块提供了一系列实用函数和类型转换工具,是 Skia 高层 API 与底层 GPU 渲染管线之间的关键接口层。

主要功能包括:
- **颜色转换**: 在 `SkColor`、`SkPMColor4f` 和 `GrColor` 之间进行转换和色彩空间处理
- **Paint 转换**: 将 `SkPaint` 对象转换为 GPU 可用的 `GrPaint` 对象,包括着色器、混合模式和滤镜
- **纹理管理**: 从位图创建纹理代理,支持缓存和 mipmap 生成
- **类型映射**: 提供 Skia 类型(如 `SkTileMode`)到 Ganesh 类型(如 `GrSamplerState::WrapMode`)的映射

## 架构位置

```
Skia 框架
├── include/core/          # Skia 公共 API (SkPaint, SkColor, SkBitmap 等)
├── src/core/              # Skia CPU 端实现
└── src/gpu/ganesh/        # Ganesh GPU 后端
    ├── SkGr.h/cpp         # 【本模块】Skia 到 Ganesh 的桥接层
    ├── GrPaint            # GPU 端的绘制状态
    ├── GrFragmentProcessor # 片段着色器处理器
    ├── GrSurfaceProxy     # GPU 纹理代理
    └── SurfaceDrawContext # GPU 绘制上下文
```

该模块位于 Skia CPU API 和 Ganesh GPU 实现之间的适配层,是从上层绘制命令到 GPU 渲染管线的必经之路。

## 主要类与结构体

### 核心枚举类型

| 类型 | 说明 |
|------|------|
| `GrImageTexGenPolicy` | 纹理生成策略:<br>- `kDraw`: 优先使用缓存<br>- `kNew_Uncached_Unbudgeted`: 创建未缓存且不计入预算的纹理<br>- `kNew_Uncached_Budgeted`: 创建未缓存但计入预算的纹理 |

### 关键函数分类

本模块不定义新的类,而是提供一系列转换函数,功能上可分为四大类:

**1. 颜色转换函数**
- `SkColorToPremulGrColor()`: 转换为预乘 alpha 的 GPU 颜色
- `SkColorToUnpremulGrColor()`: 转换为非预乘 alpha 的 GPU 颜色
- `SkColorToPMColor4f()`: 考虑色彩空间的 4f 颜色转换
- `SkColor4fPrepForDst()`: 为目标色彩空间准备颜色

**2. Paint 转换函数**
- `SkPaintToGrPaint()`: 标准转换
- `SkPaintToGrPaintReplaceShader()`: 替换着色器的转换
- `SkPaintToGrPaintWithBlend()`: 带图元颜色混合的转换

**3. 纹理管理函数**
- `GrMakeCachedBitmapProxyView()`: 创建缓存的纹理代理
- `GrMakeUncachedBitmapProxyView()`: 创建非缓存的纹理代理
- `GrCopyBaseMipMapToTextureProxy()`: 复制基础纹理并生成 mipmap

**4. 辅助工具函数**
- `GrMakeKeyFromImageID()`: 生成纹理缓存键
- `GrMakeUniqueKeyInvalidationListener()`: 创建缓存失效监听器
- `SkTileModeToWrapMode()`: tile 模式转换

## 公共 API 函数

### 颜色转换 API

```cpp
// 内联函数:快速颜色格式转换
static inline GrColor SkColorToPremulGrColor(SkColor c);
static inline GrColor SkColorToUnpremulGrColor(SkColor c);

// 考虑色彩空间的转换
SkPMColor4f SkColorToPMColor4f(SkColor, const GrColorInfo&);
SkColor4f SkColor4fPrepForDst(SkColor4f, const GrColorInfo&);
```

### Paint 转换 API

```cpp
// 基础转换:将 SkPaint 转换为 GrPaint
bool SkPaintToGrPaint(
    skgpu::ganesh::SurfaceDrawContext* sdc,
    const SkPaint& skPaint,
    const SkMatrix& ctm,
    GrPaint* grPaint
);

// 替换着色器:使用自定义 FragmentProcessor 替代 SkPaint 的着色器
bool SkPaintToGrPaintReplaceShader(
    skgpu::ganesh::SurfaceDrawContext* sdc,
    const SkPaint& skPaint,
    const SkMatrix& ctm,
    std::unique_ptr<GrFragmentProcessor> shaderFP,
    GrPaint* grPaint
);

// 混合模式:支持图元颜色与着色器颜色的混合
bool SkPaintToGrPaintWithBlend(
    skgpu::ganesh::SurfaceDrawContext* sdc,
    const SkPaint& skPaint,
    const SkMatrix& ctm,
    SkBlender* primColorBlender,
    GrPaint* grPaint
);
```

### 纹理创建 API

```cpp
// 创建带缓存的位图纹理代理(支持 mipmap)
std::tuple<GrSurfaceProxyView, GrColorType> GrMakeCachedBitmapProxyView(
    GrRecordingContext* ctx,
    const GrMippedBitmap& bitmap,
    std::string_view label,
    skgpu::Mipmapped mipMapped = skgpu::Mipmapped::kNo
);

// 创建不缓存的纹理代理(可指定 fit 和 budget 策略)
std::tuple<GrSurfaceProxyView, GrColorType> GrMakeUncachedBitmapProxyView(
    GrRecordingContext* ctx,
    const GrMippedBitmap& bitmap,
    skgpu::Mipmapped mipMapped = skgpu::Mipmapped::kNo,
    SkBackingFit fit = SkBackingFit::kExact,
    skgpu::Budgeted budgeted = skgpu::Budgeted::kYes
);
```

### 工具函数 API

```cpp
// 生成图像唯一键(用于纹理缓存查找)
void GrMakeKeyFromImageID(
    skgpu::UniqueKey* key,
    uint32_t imageID,
    const SkIRect& imageBounds
);

// 创建资源失效监听器
sk_sp<SkIDChangeListener> GrMakeUniqueKeyInvalidationListener(
    skgpu::UniqueKey* key,
    uint32_t contextID
);

// Tile 模式转换
static constexpr GrSamplerState::WrapMode SkTileModeToWrapMode(SkTileMode tileMode);
```

## 内部实现细节

### Paint 转换核心逻辑

`skpaint_to_grpaint_impl()` 是三个 Paint 转换函数的共同实现,核心流程:

1. **颜色空间转换**: 将 `SkPaint` 的颜色转换到目标色彩空间
2. **着色器处理**:
   - 如果提供了替代着色器,使用替代着色器
   - 否则从 `SkPaint` 的 `SkShader` 创建 `GrFragmentProcessor`
3. **图元颜色混合**:
   - 如果存在 `primColorBlender`,设置着色器输入为不透明颜色,然后与图元颜色混合
   - 最后应用 paint 的 alpha 值
4. **颜色滤镜**: 应用 `SkColorFilter` 到 fragment processor 链
5. **蒙版滤镜**: 将 `SkMaskFilter` 转换为覆盖率 fragment processor
6. **抖动处理**: 根据表面属性和颜色格式添加抖动效果(使用 8x8 LUT)
7. **混合模式**:
   - 标准混合模式使用 `GrXPFactory`
   - 自定义混合器通过 fragment processor 实现,并强制 XP 为 `kSrc` 模式
8. **颜色钳位**: 对需要手动钳位的格式应用 [0, 1] 范围限制

### 抖动实现优化

代码注释中详细记录了抖动算法的演进:
- **旧方案**: 整数数学(sk_FragCoord)或浮点 fallback(4x4 网格)
- **新方案**: 预计算 8x8 抖动表纹理
- **性能测试数据**(代码第 334-338 行):
  - QuadroP1000: 表格抖动比无抖动慢 1.26x
  - PowerVRGE8320: 表格抖动比无抖动慢 1.98x
  - Adreno640: 表格抖动比无抖动慢 1.95x
  - Mali-G77: 表格抖动比无抖动慢 1.58x

### 纹理缓存机制

```cpp
// 缓存键生成:包含图像 ID 和边界矩形
void GrMakeKeyFromImageID(skgpu::UniqueKey* key, uint32_t imageID, const SkIRect& imageBounds) {
    static const skgpu::UniqueKey::Domain kImageIDDomain = skgpu::UniqueKey::GenerateDomain();
    skgpu::UniqueKey::Builder builder(key, kImageIDDomain, 5, "Image");
    builder[0] = imageID;
    builder[1] = imageBounds.fLeft;
    builder[2] = imageBounds.fTop;
    builder[3] = imageBounds.fRight;
    builder[4] = imageBounds.fBottom;
}
```

缓存失效监听器通过 `SkData` 附加到 `UniqueKey` 上,当键被销毁时自动触发失效通知。

### Mipmap 动态生成

`GrMakeCachedBitmapProxyView()` 中的 mipmap 处理逻辑(第 232-257 行):
1. 首先尝试查找已缓存的纹理
2. 如果找到的纹理不带 mipmap 但需要 mipmap:
   - 复制基础纹理到新的带 mipmap 的代理
   - 窃取原代理的缓存键并分配给新代理
   - 原代理保留在缓存中直到最后一个引用被删除

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPaint` | 输入的绘制状态对象 |
| `SkShaderBase` | 着色器转换 |
| `SkColorFilter` | 颜色滤镜处理 |
| `SkBlenderBase` | 混合模式处理 |
| `GrFragmentProcessor` | 构建 GPU 片段着色器链 |
| `GrFragmentProcessors` | 工厂函数集合 |
| `GrPaint` | 输出的 GPU 绘制状态 |
| `GrProxyProvider` | 纹理代理的创建和缓存管理 |
| `GrXPFactory` | 混合处理器工厂 |
| `GrColorSpaceXform` | 色彩空间转换 |
| `GrMippedBitmap` | 支持 mipmap 的位图封装 |
| `skgpu::DitherUtils` | 抖动查找表生成 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SurfaceDrawContext` | 调用 `SkPaintToGrPaint` 进行绘制准备 |
| `GrDrawOpAtlas` | 使用纹理创建函数生成 atlas 纹理 |
| `SkImage_Ganesh` | 使用 `GrMakeCachedBitmapProxyView` 创建图像纹理 |
| `GrGLSLFragmentShaderBuilder` | 使用颜色转换函数生成着色器代码 |
| 各种绘制 Op 类 | 间接依赖于 Paint 转换结果 |

## 设计模式与设计决策

### 1. 适配器模式

整个模块是 Skia API 到 Ganesh GPU 的适配器:
- **目标接口**: `GrPaint`、`GrSurfaceProxyView`、`GrColor`
- **适配对象**: `SkPaint`、`SkBitmap`、`SkColor`
- **适配方法**: 静态转换函数和工厂函数

### 2. 策略模式

Paint 转换提供三种策略:
- **标准策略**: 直接转换 SkPaint
- **着色器替换策略**: 注入自定义 FragmentProcessor
- **图元混合策略**: 支持顶点颜色插值

### 3. 延迟初始化

Mipmap 按需生成:
- 首次请求不带 mipmap 的纹理时,创建基础级别纹理并缓存
- 后续请求 mipmap 时,复制基础纹理并生成完整 mipmap 链
- 避免预先生成永不使用的 mipmap

### 4. 观察者模式

缓存失效通过 `SkIDChangeListener` 实现:
- 当 `SkPixelRef` 的 generation ID 改变时,自动发送失效消息
- 通过 `SkData` 作为 RAII 包装器,确保监听器正确注销

### 5. 类型安全的静态断言

使用 `static_assert` 确保枚举值对齐:
```cpp
static_assert((int)skgpu::BlendCoeff::kZero == (int)SkBlendModeCoeff::kZero);
static_assert((int)skgpu::BlendCoeff::kOne == (int)SkBlendModeCoeff::kOne);
// ... 共 10 个断言
```

## 性能考量

### 1. 内联热点函数

颜色转换函数被标记为 `static inline`,避免函数调用开销:
```cpp
static inline GrColor SkColorToPremulGrColor(SkColor c) {
    SkPMColor pm = SkPreMultiplyColor(c);
    // ... 直接在调用点展开
}
```

### 2. 纹理缓存复用

- 使用 `skgpu::UniqueKey` 基于图像 ID 和边界进行缓存查找
- 避免重复上传相同的位图数据到 GPU
- 支持从未 mipmap 纹理升级到 mipmap 纹理,复用基础级别数据

### 3. 条件编译优化

抖动功能可通过 `SK_IGNORE_GPU_DITHER` 宏完全禁用,减少测试/调试时的代码路径。

### 4. 提前退出策略

```cpp
if (range == 0 || inputFP == nullptr) {
    return inputFP;  // 无需抖动时直接返回
}
if (caps->avoidDithering()) {
    return inputFP;  // 硬件不支持时避免额外计算
}
```

### 5. 色彩空间转换优化

- 仅在需要时进行色彩空间转换(`colorSpaceXformFromSRGB()`)
- 对于非预乘 alpha 的情况,延迟预乘操作到必要时刻

### 6. Fragment Processor 链构建

使用 move 语义传递 `std::unique_ptr`,避免不必要的引用计数操作:
```cpp
paintFP = GrFragmentProcessor::OverrideInput(std::move(paintFP), shaderInput);
paintFP = GrFragmentProcessors::Make(as_BB(primColorBlender),
                                     std::move(paintFP), /*dstFP=*/nullptr, fpArgs);
```

### 7. 抖动表纹理共享

全局静态的 8x8 抖动查找表(`gLUT`)被所有绘制调用共享,只创建一次。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/GrPaint.h` | 输出的 GPU 绘制状态类 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | Fragment shader 处理器基类 |
| `src/gpu/ganesh/GrFragmentProcessors.h` | FP 工厂函数集合 |
| `src/gpu/ganesh/GrProxyProvider.h` | 纹理代理管理器 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 纹理代理视图 |
| `src/gpu/ganesh/GrXferProcessor.h` | 混合处理器基类 |
| `src/gpu/ganesh/GrColorInfo.h` | 颜色格式和色彩空间信息 |
| `src/gpu/ganesh/GrColorSpaceXform.h` | 色彩空间转换矩阵 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | GPU 绘制上下文 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 纹理采样效果 |
| `src/gpu/ganesh/effects/GrSkSLFP.h` | SkSL 运行时效果 |
| `src/gpu/ganesh/image/GrMippedBitmap.h` | 带 mipmap 的位图封装 |
| `src/core/SkBlenderBase.h` | 混合器基类 |
| `src/core/SkShaderBase.h` | 着色器基类 |
| `src/core/SkPaintPriv.h` | Paint 内部辅助函数 |
| `src/gpu/DitherUtils.h` | 抖动算法实用工具 |
| `src/gpu/Blend.h` | 混合系数定义 |
| `include/core/SkPaint.h` | Skia 公共绘制状态 API |
| `include/core/SkColor.h` | Skia 颜色类型定义 |
| `include/core/SkBlendMode.h` | Skia 混合模式枚举 |
