# SkImage_Ganesh

> 源文件
> - src/gpu/ganesh/image/SkImage_Ganesh.h
> - src/gpu/ganesh/image/SkImage_Ganesh.cpp

## 概述

`SkImage_Ganesh` 是 Skia Ganesh GPU 后端中标准 GPU 纹理图像的具体实现类，继承自 `SkImage_GaneshBase`。它封装了一个 GPU 纹理代理及其相关的视图信息（swizzle、origin），并实现了所有必要的图像操作接口。该类的核心特性是支持 volatile/stable 双代理机制，用于优化从 `SkSurface` 快照创建的图像，避免不必要的纹理复制。

这是 Ganesh 后端最常用的图像类型，大多数 GPU 纹理图像都由这个类的实例表示。

## 架构位置

```
SkImage (公共 API)
  └── SkImage_Base
      └── SkImage_GaneshBase
          └── SkImage_Ganesh (标准 GPU 纹理图像)
              ├── 单代理模式 (直接纹理)
              └── 双代理模式 (volatile + stable)
```

位于 Ganesh 图像层次结构的叶子节点，是 GPU 纹理图像的最终实现类。

## 主要类与结构体

### SkImage_Ganesh

**继承关系**:
- 继承自: `SkImage_GaneshBase`
- 实现接口: 完整的 GPU 图像 API

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fChooser` | `ProxyChooser` | 代理选择器，管理 volatile/stable 代理 |
| `fSwizzle` | `skgpu::Swizzle` | 纹理通道重排 |
| `fOrigin` | `GrSurfaceOrigin` | 纹理原点方向 |

### ProxyChooser (内部类)

线程安全的代理选择器，负责在 volatile 和 stable 代理之间动态切换。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStableProxy` | `sk_sp<GrSurfaceProxy>` (guarded) | 稳定代理，始终有效 |
| `fVolatileProxy` | `sk_sp<GrSurfaceProxy>` (guarded) | 易变代理，可能被 Surface 修改 |
| `fVolatileToStableCopyTask` | `sk_sp<GrRenderTask>` | 复制任务 |
| `fVolatileProxyTargetCount` | `const int` | 创建时的目标计数 |
| `fLock` | `mutable SkSpinlock` | 保护并发访问的自旋锁 |

## 公共 API 函数

### 构造函数

```cpp
SkImage_Ganesh(sk_sp<GrImageContext> context,
               uint32_t uniqueID,
               GrSurfaceProxyView view,
               SkColorInfo info);
```
标准构造函数，创建单代理模式的图像。

**双代理模式工厂**:

```cpp
static sk_sp<SkImage> MakeWithVolatileSrc(
    sk_sp<GrRecordingContext> rContext,
    GrSurfaceProxyView volatileSrc,
    SkColorInfo colorInfo);
```
创建双代理模式的图像，用于 Surface 快照优化。

### SkImage_Base 接口实现

```cpp
SkImage_Base::Type type() const override { return SkImage_Base::Type::kGanesh; }
size_t textureSize() const override;
bool onHasMipmaps() const override;
bool onIsProtected() const override;
```
实现图像类型查询和属性查询接口。

### 图像转换

```cpp
sk_sp<SkImage> onMakeColorTypeAndColorSpace(
    GrDirectContext* dContext,
    SkColorType targetColorType,
    sk_sp<SkColorSpace> targetCS) const final;
```
创建不同颜色类型和颜色空间的副本。

```cpp
sk_sp<SkImage> onReinterpretColorSpace(sk_sp<SkColorSpace> newCS) const final;
```
重新解释颜色空间（不做转换，只改变元数据）。

### 异步像素读取

```cpp
void onAsyncRescaleAndReadPixels(
    const SkImageInfo& info,
    SkIRect srcRect,
    RescaleGamma rescaleGamma,
    RescaleMode rescaleMode,
    ReadPixelsCallback callback,
    ReadPixelsContext context) const override;
```
异步读取像素，支持缩放和颜色校正。

```cpp
void onAsyncRescaleAndReadPixelsYUV420(
    SkYUVColorSpace yuvColorSpace,
    bool readAlpha,
    sk_sp<SkColorSpace> dstColorSpace,
    SkIRect srcRect,
    SkISize dstSize,
    RescaleGamma rescaleGamma,
    RescaleMode rescaleMode,
    ReadPixelsCallback callback,
    ReadPixelsContext context) const override;
```
异步读取并转换为 YUV420 格式。

### SkImage_GaneshBase 接口实现

```cpp
GrSemaphoresSubmitted flush(GrDirectContext* dContext,
                            const GrFlushInfo& info) const override;
```
刷新 GPU 命令，确保渲染完成。

```cpp
std::tuple<GrSurfaceProxyView, GrColorType> asView(
    GrRecordingContext* rContext,
    skgpu::Mipmapped mipmapped,
    GrImageTexGenPolicy policy,
    GrRenderTargetProxy* targetProxy) const override;
```
获取表面代理视图，根据策略可能创建副本。

```cpp
std::unique_ptr<GrFragmentProcessor> asFragmentProcessor(
    skgpu::ganesh::SurfaceDrawContext* sdc,
    SkSamplingOptions sampling,
    const SkTileMode tileModes[2],
    const SkMatrix& m,
    const SkRect* subset,
    const SkRect* domain) const override;
```
生成片段处理器用于着色器渲染。

### Surface 交互

```cpp
bool surfaceMustCopyOnWrite(GrSurfaceProxy* surfaceProxy) const;
```
检查 Surface 写入前是否需要复制（COW 机制）。

```cpp
void generatingSurfaceIsDeleted() override;
```
通知生成此图像的 Surface 已被删除，触发 volatile 到 stable 的转换。

### 后端纹理访问

```cpp
bool getExistingBackendTexture(
    GrBackendTexture* outTexture,
    bool flushPendingGrContextIO,
    GrSurfaceOrigin* origin) const;
```
获取底层的后端纹理句柄，支持与外部 API 互操作。

## 内部实现细节

### ProxyChooser 的代理选择逻辑

`chooseProxy` 方法实现了智能代理选择：

```cpp
sk_sp<GrSurfaceProxy> ProxyChooser::chooseProxy(
    GrRecordingContext* context,
    GrRenderTargetProxy* targetProxy) {
    SkAutoSpinlock hold(fLock);
    if (fVolatileProxy) {
        // 检查 volatile 代理是否仍然有效
        if (context->asDirectContext() &&
            fVolatileProxyTargetCount == fVolatileProxy->getTaskTargetCount()) {
            // 不能绘制到自身
            if (!targetProxy ||
                targetProxy->underlyingUniqueID() != fVolatileProxy->underlyingUniqueID()) {
                return fVolatileProxy;
            }
        }
        // volatile 已失效，释放并使用 stable
        fVolatileProxy.reset();
        fVolatileToStableCopyTask.reset();
        return fStableProxy;
    }
    return fStableProxy;
}
```

### Volatile/Stable 双代理机制

双代理模式优化 Surface 快照场景：

1. **创建时**: 同时持有 volatile（Surface 的纹理）和 stable（复制任务的结果）
2. **首次使用**: 检查 volatile 是否被修改（通过 target count）
3. **未修改**: 直接使用 volatile，跳过复制任务
4. **已修改**: 切换到 stable，丢弃 volatile
5. **析构时**: 如果 volatile 从未被使用，标记复制任务为可跳过

### 复制任务的延迟执行

```cpp
~ProxyChooser() {
    if (fVolatileToStableCopyTask) {
        fVolatileToStableCopyTask->makeSkippable();
    }
}
```

如果图像从未需要 stable 代理，复制任务会被标记为可跳过，避免浪费 GPU 资源。

### 颜色空间转换实现

`onMakeColorTypeAndColorSpace` 创建转换后的图像：

```cpp
auto sfc = dContext->priv().makeSFCWithFallback(...);
auto texFP = GrTextureEffect::Make(view, alphaType);
auto colorFP = GrColorSpaceXformEffect::Make(std::move(texFP), ...);
sfc->fillWithFP(std::move(colorFP));
return sk_make_sp<SkImage_Ganesh>(..., sfc->readSurfaceView(), ...);
```

1. 创建目标表面上下文
2. 生成纹理效果片段处理器
3. 应用颜色空间转换效果
4. 填充表面并读取结果视图

### Mipmap 处理

`asView` 中的 mipmap 逻辑：

```cpp
if (mipmapped == skgpu::Mipmapped::kYes) {
    view = skgpu::ganesh::FindOrMakeCachedMipmappedView(
        recordingContext, std::move(view), this->uniqueID());
}
```

如果需要 mipmap 但视图没有，会查找或创建缓存的 mipmap 版本。

### 线程安全设计

`ProxyChooser` 使用 `SkSpinlock` 保护内部状态：

```cpp
SkAutoSpinlock hold(fLock);  // 自动加锁
```

所有公共方法都标记为 `SK_EXCLUDES(fLock)`，确保线程安全分析。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrSurfaceProxyView` | 表面代理视图 |
| `GrTextureProxy` | 纹理代理 |
| `GrRenderTask` | 渲染任务管理 |
| `GrSurfaceProxy` | 表面代理基类 |
| `GrDirectContext` | GPU 直接上下文 |
| `GrTextureEffect` | 纹理采样效果 |
| `GrColorSpaceXformEffect` | 颜色空间转换 |
| `SurfaceContext` | 表面操作上下文 |
| `skgpu::Swizzle` | 通道重排 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkImages::TextureFromImage` | 创建纹理图像 |
| `SkSurface` | Surface 快照 |
| `GrImageUtils::AsView` | 图像到视图转换 |
| `SkSpecialImage_Gpu` | 特殊图像实现 |

## 设计模式与设计决策

### 策略模式 - ProxyChooser

`ProxyChooser` 封装了代理选择策略，隔离了单/双代理模式的复杂性：

- **单代理**: 直接持有一个 stable 代理
- **双代理**: 动态选择 volatile 或 stable 代理

### 写时复制 (COW) 优化

双代理机制本质上是一种延迟 COW：

- **初始状态**: 共享 Surface 的纹理（volatile）
- **写入检测**: 通过 target count 检测 Surface 是否被修改
- **延迟复制**: 只在 volatile 失效时才使用 stable 副本

### RAII 资源管理

使用智能指针和 RAII 类管理资源：

```cpp
SkAutoSpinlock hold(fLock);  // 自动锁管理
sk_sp<GrTexture> texture;    // 自动引用计数
```

### 不可变性与缓存

图像创建后不可变，支持安全缓存：

- **唯一 ID**: 用于缓存键
- **线程安全**: 不可变对象天然线程安全
- **代理共享**: 多个图像可以共享同一个代理

### 延迟实例化

纹理代理采用延迟实例化：

- **创建时**: 只创建代理，不实际分配 GPU 内存
- **使用时**: 首次访问时才实例化真正的纹理

## 性能考量

### Surface 快照优化

双代理机制显著优化了 Surface 快照场景：

- **零复制**: 如果 Surface 未被修改，图像直接使用原纹理
- **延迟复制**: 只在必要时执行复制
- **任务跳过**: 未使用的复制任务可以完全跳过

### Mipmap 缓存

`FindOrMakeCachedMipmappedView` 缓存 mipmap 版本：

- **避免重复生成**: 同一图像的 mipmap 只生成一次
- **共享缓存**: 多个引用共享同一份 mipmap 数据

### 内存管理

- **智能指针**: 自动管理纹理生命周期
- **代理轻量**: 代理对象比实际纹理轻量得多
- **按需实例化**: 代理只在需要时才实例化

### 异步操作

`onAsyncRescaleAndReadPixels` 支持异步像素读取：

- **不阻塞渲染**: 读取操作在 GPU 上异步执行
- **回调通知**: 完成后通过回调返回结果
- **缩放优化**: 在 GPU 上执行缩放，避免 CPU 处理

### 线程安全性能

使用自旋锁而非互斥锁：

- **低延迟**: 自旋锁适合短时间持锁场景
- **无上下文切换**: 避免线程切换开销
- **临界区小**: 锁持有时间极短

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/image/SkImage_GaneshBase.h` | GPU 图像基类 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 表面代理视图 |
| `src/gpu/ganesh/GrTextureProxy.h` | 纹理代理 |
| `src/gpu/ganesh/GrRenderTask.h` | 渲染任务 |
| `src/gpu/ganesh/SurfaceContext.h` | 表面操作上下文 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 纹理效果 |
| `src/gpu/ganesh/effects/GrColorSpaceXformEffect.h` | 颜色空间转换 |
| `include/gpu/ganesh/SkImageGanesh.h` | Ganesh 图像公共 API |
