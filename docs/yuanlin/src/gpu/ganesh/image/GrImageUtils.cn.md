# GrImageUtils

> 源文件
> - src/gpu/ganesh/image/GrImageUtils.h
> - src/gpu/ganesh/image/GrImageUtils.cpp

## 概述

`GrImageUtils` 是 Skia Ganesh GPU 后端中的图像工具模块，提供了一系列用于图像到 GPU 纹理转换、片段处理器生成、以及图像滤镜后端创建的实用函数。该模块是 Ganesh 图像渲染管线的核心组件，负责将各种类型的 `SkImage`（光栅、懒加载、GPU 纹理等）转换为可供 GPU 渲染使用的表面代理视图和片段处理器。

该模块实现了复杂的纹理生成策略，包括缓存管理、mipmap 生成、YUVA 平面处理、以及跨上下文纹理共享等高级功能。

## 架构位置

```
SkImage (公共 API)
  ├── SkImage_Raster ────┐
  ├── SkImage_Lazy ──────┼──> GrImageUtils::AsView()
  ├── SkImage_Picture ───┤        ├──> GrSurfaceProxyView
  └── SkImage_GaneshBase─┘        └──> GrFragmentProcessor
                                         |
                                         v
                                  GrRecordingContext
                                         |
                                         v
                                  GPU 渲染管线
```

位于 Ganesh 图像层与 GPU 资源管理层之间，是图像内容到 GPU 资源的桥梁。

## 主要类与结构体

### GaneshBackend (skif 命名空间)

实现图像滤镜的 Ganesh GPU 后端。

**继承关系**:
- 继承自: `skif::Backend`, `SkShaderBlurAlgorithm`, `SkBlurEngine`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fContext` | `sk_sp<GrRecordingContext>` | GPU 录制上下文 |
| `fOrigin` | `GrSurfaceOrigin` | 表面原点方向 |

## 公共 API 函数

### 核心视图转换

```cpp
std::tuple<GrSurfaceProxyView, GrColorType> AsView(
    GrRecordingContext* rContext,
    const SkImage* img,
    skgpu::Mipmapped mipmapped,
    GrRenderTargetProxy* targetSurface,
    GrImageTexGenPolicy policy = GrImageTexGenPolicy::kDraw);
```
将任意类型的 `SkImage` 转换为 `GrSurfaceProxyView`，是模块的核心函数。支持光栅图像、懒加载图像、Picture 图像和 GPU 图像的统一转换。

### 光栅图像处理

```cpp
std::tuple<GrSurfaceProxyView, GrColorType> RasterAsView(
    GrRecordingContext* rContext,
    const SkImage_Raster* raster,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy policy = GrImageTexGenPolicy::kDraw);
```
专门处理光栅图像到 GPU 纹理的转换，支持 mipmap 智能检测。

### 懒加载纹理生成

```cpp
GrSurfaceProxyView LockTextureProxyView(
    GrRecordingContext* rContext,
    const SkImage_Lazy* img,
    GrImageTexGenPolicy texGenPolicy,
    skgpu::Mipmapped mipmapped);
```
锁定懒加载图像的纹理代理视图，支持四种纹理生成策略：
1. 从缓存中查找
2. 使用生成器原生创建
3. 从 YUVA 平面转换
4. 从位图转换

### 片段处理器生成

```cpp
std::unique_ptr<GrFragmentProcessor> AsFragmentProcessor(
    SurfaceDrawContext* sdc,
    const SkImage* img,
    SkSamplingOptions sampling,
    const SkTileMode tileModes[2],
    const SkMatrix& m,
    const SkRect* subset = nullptr,
    const SkRect* domain = nullptr);
```
将图像转换为片段处理器，用于着色器渲染。支持采样选项、平铺模式、变换矩阵和子集渲染。

```cpp
std::unique_ptr<GrFragmentProcessor> MakeFragmentProcessorFromView(
    GrRecordingContext* rContext,
    GrSurfaceProxyView view,
    SkAlphaType alphaType,
    SkSamplingOptions sampling,
    const SkTileMode tileModes[2],
    const SkMatrix& m,
    const SkRect* subset,
    const SkRect* domain);
```
从现有视图创建片段处理器，支持双三次插值和各向异性过滤。

### Mipmap 管理

```cpp
GrSurfaceProxyView FindOrMakeCachedMipmappedView(
    GrRecordingContext* rContext,
    GrSurfaceProxyView view,
    uint32_t imageUniqueID);
```
查找或创建带 mipmap 的缓存视图，使用图像唯一 ID 作为缓存键。

### 辅助工具

```cpp
GrSurfaceProxyView CopyView(
    GrRecordingContext* context,
    GrSurfaceProxyView src,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy policy,
    std::string_view label);
```
根据策略复制表面代理视图。

```cpp
GrColorType ColorTypeOfLockTextureProxy(const GrCaps* caps, SkColorType sct);
```
确定纹理代理的颜色类型，处理 GPU 不支持的格式（回退到 RGBA_8888）。

```cpp
SkYUVAPixmapInfo::SupportedDataTypes SupportedTextureFormats(const GrImageContext& context);
```
查询 GPU 上下文支持的 YUVA 纹理格式。

## 内部实现细节

### 四级纹理生成策略

`LockTextureProxyView` 实现了四级回退策略：

1. **缓存查找**: 使用 unique key 在代理提供者中查找
   - 如果找到但需要 mipmap 而缓存没有，则生成 mipmap 并更新缓存
2. **原生生成**:
   - Picture 图像：通过 `generate_picture_texture` 渲染到表面
   - GrTextureGenerator：调用 `generateTexture` 方法
3. **YUVA 转换**: 通过 `texture_proxy_view_from_planes` 从平面数据合成 RGB 纹理
4. **位图上传**: 使用 `GrMakeUncachedBitmapProxyView` 从位图创建纹理

### Mipmap 智能处理

光栅图像处理中的 mipmap 策略：

```cpp
if (raster->hasMipmaps()) {
    mipmapped = skgpu::Mipmapped::kYes;  // 优先使用现有 mipmap
}
```

对于已有 mipmap 的光栅图像，即使请求不需要 mipmap，也会上传完整的 mipmap 链，避免后续重新生成。

### YUVA 平面处理

`texture_proxy_view_from_planes` 实现了完整的 YUVA 到 RGB 转换流程：

1. 解析 YUVA 平面信息 (`yuvaPixmaps.numPlanes()`)
2. 为每个平面创建纹理代理
3. 使用 `GrYUVtoRGBEffect` 生成转换着色器
4. 应用颜色空间转换 (`GrColorSpaceXformEffect`)
5. 渲染到目标表面

### 采样模式优化

片段处理器生成时的采样优化：

- **双三次插值**: 使用 `GrBicubicEffect`，支持子集和域约束
- **各向异性过滤**: 检查 GPU 支持 (`caps->anisoSupport()`)，不支持时回退到线性过滤
- **Mipmap 处理**: 根据视图的 mipmap 状态调整采样参数

### Picture 纹理生成

`generate_picture_texture` 通过离屏渲染生成纹理：

```cpp
auto surface = SkSurfaces::RenderTarget(ctx, budgeted, img->imageInfo(),
                                        0, kTopLeft_GrSurfaceOrigin,
                                        img->props(), mipmapped);
img->replay(surface->getCanvas());
```

### 缓存键管理

使用专用域生成 mipmap 缓存键：

```cpp
static const skgpu::UniqueKey::Domain kMipmappedDomain =
    skgpu::UniqueKey::GenerateDomain();
```

确保 mipmap 版本与基础纹理使用不同的缓存键。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRecordingContext` | GPU 录制上下文 |
| `GrProxyProvider` | 纹理代理创建和缓存 |
| `GrThreadSafeCache` | 线程安全的纹理缓存 |
| `GrFragmentProcessor` | 着色器片段处理 |
| `GrYUVtoRGBEffect` | YUVA 到 RGB 转换效果 |
| `GrTextureEffect` | 纹理采样效果 |
| `GrBicubicEffect` | 双三次插值效果 |
| `GrColorSpaceXformEffect` | 颜色空间转换 |
| `GrMippedBitmap` | 带 mipmap 的位图包装 |
| `SkImageFilterCache` | 图像滤镜缓存 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkImage_GaneshBase` | 调用 `AsView` 获取视图 |
| `SkImage_Ganesh` | 使用片段处理器渲染 |
| `SkImage_RasterPinnable` | 光栅图像转换 |
| `SkSpecialImage_Ganesh` | 特殊图像处理 |
| 图像滤镜系统 | 使用 `GaneshBackend` 实现滤镜 |

## 设计模式与设计决策

### 策略模式

`GrImageTexGenPolicy` 定义了三种纹理生成策略：

- **kDraw**: 绘制时使用，优先缓存，预算可选
- **kNew_Uncached_Budgeted**: 新建有预算纹理，不使用缓存
- **kNew_Uncached_Unbudgeted**: 新建无预算纹理，用于临时资源

### 工厂方法模式

`AsView` 和 `AsFragmentProcessor` 根据图像类型分发到不同的处理函数：

```cpp
if (ib->type() == SkImage_Base::Type::kRaster) {
    return RasterAsView(...);
} else if (ib->type() == SkImage_Base::Type::kRasterPinnable) {
    return rp->asView(...);
} else if (ib->isGaneshBacked()) {
    return gb->asView(...);
} else if (ib->isLazyGenerated()) {
    return lazy_as_view(...);
}
```

### 装饰器模式

片段处理器通过链式装饰实现复杂效果：

```cpp
auto fp = GrTextureEffect::Make(view, alphaType, m, sampler, caps);
if (sampling.useCubic) {
    fp = GrBicubicEffect::Make(...);
}
if (colorSpaceTransform) {
    fp = GrColorSpaceXformEffect::Make(std::move(fp), ...);
}
```

### 缓存优先设计

所有纹理生成都优先检查缓存，减少重复创建：

- **基础纹理**: 通过 unique key 缓存
- **Mipmap 纹理**: 使用专用域的 unique key
- **线程安全缓存**: 支持 DDL 多线程场景

### 回退机制

各个转换路径都有完整的回退链：

- 颜色格式不支持 → RGBA_8888
- GPU 转换失败 → CPU 位图路径
- 各向异性不支持 → 线性过滤
- Mipmap 生成失败 → 无 mipmap 模式

## 性能考量

### 缓存分层

1. **代理缓存**: `GrProxyProvider` 管理纹理代理
2. **线程安全缓存**: `GrThreadSafeCache` 支持 DDL
3. **Mipmap 缓存**: 独立缓存 mipmap 版本

### 智能 Mipmap 生成

- 光栅图像：检测现有 mipmap，避免重复生成
- 懒加载图像：仅在需要时生成 mipmap
- 缓存命中：直接使用或按需升级

### 内存预算管理

根据 `GrImageTexGenPolicy` 决定纹理预算：

- **kDraw**: 默认有预算，长期保留
- **kNew_Uncached_Budgeted**: 有预算但不缓存
- **kNew_Uncached_Unbudgeted**: 无预算，临时使用

### GPU 操作优化

- **懒加载实例化**: 纹理代理延迟到真正使用时才实例化
- **表面复制**: 使用 GPU 端复制避免 CPU-GPU 数据传输
- **YUVA 转换**: 在 GPU 上执行 YUV 到 RGB 转换

### 采样优化

- **过滤降级**: 不支持的采样模式自动降级
- **Mipmap 适配**: 根据视图状态调整采样参数
- **子集渲染**: 支持精确的纹理子集和域约束

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/image/SkImage_GaneshBase.h` | GPU 图像基类 |
| `src/gpu/ganesh/image/SkImage_Ganesh.h` | 标准 GPU 图像 |
| `src/gpu/ganesh/image/SkImage_RasterPinnable.h` | 可固定光栅图像 |
| `src/gpu/ganesh/image/GrMippedBitmap.h` | 带 mipmap 的位图 |
| `src/image/SkImage_Lazy.h` | 懒加载图像 |
| `src/image/SkImage_Picture.h` | Picture 图像 |
| `src/gpu/ganesh/GrProxyProvider.h` | 纹理代理提供者 |
| `src/gpu/ganesh/GrThreadSafeCache.h` | 线程安全缓存 |
| `src/gpu/ganesh/effects/GrYUVtoRGBEffect.h` | YUVA 转换效果 |
| `src/core/SkImageFilterCache.h` | 图像滤镜缓存 |
