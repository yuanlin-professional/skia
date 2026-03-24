# SkImage_GaneshBase

> 源文件
> - src/gpu/ganesh/image/SkImage_GaneshBase.h
> - src/gpu/ganesh/image/SkImage_GaneshBase.cpp

## 概述

`SkImage_GaneshBase` 是 Skia 的 Ganesh GPU 后端中所有基于纹理的图像类的抽象基类。它继承自 `SkImage_Base`，为 GPU 支持的图像提供了统一的接口和通用实现。该类管理与 GPU 上下文的关联，并提供了像素读取、子集创建、颜色空间转换等核心功能。

该类是 Ganesh 图像层次结构的核心，为 `SkImage_Ganesh`、`SkImage_GaneshYUVA` 等具体实现提供了基础框架。它封装了 GPU 图像的通用行为，包括纹理代理视图的管理、后端纹理的验证以及 Promise Image 的延迟加载机制。

## 架构位置

```
SkImage (公共 API)
  └── SkImage_Base (内部基类)
      └── SkImage_GaneshBase (Ganesh GPU 基类)
          ├── SkImage_Ganesh (标准 GPU 纹理图像)
          └── SkImage_GaneshYUVA (YUVA 多平面图像)
```

位于 Ganesh GPU 渲染管线的图像层，负责桥接上层 `SkImage` API 和底层的 GPU 资源管理。与 `GrRecordingContext`、`GrDirectContext` 紧密协作。

## 主要类与结构体

### SkImage_GaneshBase

**继承关系**:
- 继承自: `SkImage_Base`
- 实现接口: `SkImageChromium` 相关功能
- 被继承: `SkImage_Ganesh`, `SkImage_GaneshYUVA`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fContext` | `sk_sp<GrImageContext>` | 关联的 GPU 图像上下文 |

### PromiseLazyInstantiateCallback (内部类)

负责 Promise Image 的延迟实例化回调，管理纹理的创建和释放。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFulfillProc` | `SkImages::PromiseImageTextureFulfillProc` | 纹理生成回调函数 |
| `fReleaseHelper` | `sk_sp<skgpu::RefCntedCallback>` | 资源释放辅助对象 |
| `fTexture` | `sk_sp<GrTexture>` | 缓存的纹理对象 |
| `fTextureContextID` | `GrDirectContext::DirectContextID` | 纹理所属上下文 ID |
| `fFulfillProcFailed` | `bool` | 标记填充过程是否失败 |

## 公共 API 函数

### 核心验证函数

```cpp
static bool ValidateBackendTexture(const GrCaps* caps,
                                   const GrBackendTexture& tex,
                                   GrColorType grCT,
                                   SkColorType ct,
                                   SkAlphaType at,
                                   sk_sp<SkColorSpace> cs);
```
验证后端纹理是否与指定的颜色类型和格式兼容。

```cpp
static bool ValidateCompressedBackendTexture(const GrCaps* caps,
                                             const GrBackendTexture& tex,
                                             SkAlphaType at);
```
验证压缩格式的后端纹理是否有效。

### 像素访问

```cpp
bool getROPixels(GrDirectContext* dContext,
                 SkBitmap* dst,
                 CachingHint chint) const final;
```
获取图像的只读像素数据，支持缓存提示以优化性能。

```cpp
bool onReadPixels(GrDirectContext* dContext,
                  const SkImageInfo& dstInfo,
                  void* dstPixels,
                  size_t dstRB,
                  int srcX, int srcY,
                  CachingHint) const override;
```
从 GPU 纹理读取像素数据到 CPU 内存。

### 图像转换

```cpp
sk_sp<SkImage> onMakeSubset(SkRecorder* recorder,
                            const SkIRect& subset,
                            RequiredProperties) const final;
```
创建图像的子集副本，通过 GPU 纹理复制实现。

```cpp
sk_sp<SkImage> makeColorTypeAndColorSpace(SkRecorder* recorder,
                                         SkColorType targetColorType,
                                         sk_sp<SkColorSpace> targetCS,
                                         RequiredProperties) const final;
```
转换图像的颜色类型和颜色空间。

### Promise Image 支持

```cpp
static sk_sp<GrTextureProxy> MakePromiseImageLazyProxy(
    GrContextThreadSafeProxy* tsp,
    SkISize dimensions,
    const GrBackendFormat& backendFormat,
    skgpu::Mipmapped mipmapped,
    SkImages::PromiseImageTextureFulfillProc fulfillProc,
    sk_sp<skgpu::RefCntedCallback> releaseHelper);
```
创建延迟实例化的 Promise Image 代理纹理。

### 纯虚函数 (子类必须实现)

```cpp
virtual std::tuple<GrSurfaceProxyView, GrColorType> asView(
    GrRecordingContext*,
    skgpu::Mipmapped,
    GrImageTexGenPolicy,
    GrRenderTargetProxy*) const = 0;
```
将图像转换为 GPU 表面代理视图。

```cpp
virtual std::unique_ptr<GrFragmentProcessor> asFragmentProcessor(
    skgpu::ganesh::SurfaceDrawContext*,
    SkSamplingOptions,
    const SkTileMode[2],
    const SkMatrix&,
    const SkRect* subset,
    const SkRect* domain) const = 0;
```
生成用于着色器的片段处理器。

## 内部实现细节

### 上下文验证机制

所有操作都会验证传入的 `GrDirectContext` 是否与图像创建时的上下文匹配，确保跨上下文安全：

```cpp
if (!fContext->priv().matches(dContext)) {
    return false;
}
```

### 后端纹理验证流程

1. 检查纹理有效性 (`backendTexture.isValid()`)
2. 验证颜色信息有效性 (`SkColorInfoIsValid`)
3. 确认后端格式有效性 (`backendFormat.isValid()`)
4. 验证颜色类型与格式的兼容性 (`caps->areColorTypeAndFormatCompatible`)

### Promise Image 延迟加载

Promise Image 通过 `PromiseLazyInstantiateCallback` 实现纹理的延迟创建：

- **首次访问**: 调用 `fFulfillProc` 生成 `GrPromiseImageTexture`
- **后续访问**: 直接返回缓存的 `fTexture`
- **失败处理**: 标记 `fFulfillProcFailed` 避免重复调用
- **资源管理**: 通过消息机制在适当线程释放纹理

### 子集创建优化

子集创建时会保留原始纹理的预算状态：

```cpp
skgpu::Budgeted isBudgeted = view.proxy()->isBudgeted();
auto copyView = GrSurfaceProxyView::Copy(direct, std::move(view),
                                         skgpu::Mipmapped::kNo,
                                         subset,
                                         SkBackingFit::kExact,
                                         isBudgeted,
                                         /*label=*/"ImageGpuBase_MakeSubset");
```

### 颜色空间转换短路

在进行颜色空间转换前，会检查是否需要实际转换：

```cpp
if (colorType == targetColorType &&
    (SkColorSpace::Equals(colorSpace, targetCS.get()) || this->isAlphaOnly())) {
    return sk_ref_sp(const_cast<SkImage_GaneshBase*>(this));
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrImageContext` | GPU 图像上下文管理 |
| `GrDirectContext` | GPU 直接上下文操作 |
| `GrSurfaceProxyView` | 表面代理视图 |
| `GrTextureProxy` | 纹理代理 |
| `GrCaps` | GPU 能力查询 |
| `GrBackendTexture` | 后端纹理封装 |
| `SkBitmapCache` | 位图缓存系统 |
| `SurfaceContext` | 表面操作上下文 |
| `GrProxyProvider` | 代理提供者 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkImage_Ganesh` | 标准 GPU 纹理图像实现 |
| `SkImage_GaneshYUVA` | YUVA 格式图像实现 |
| `GrImageUtils` | 图像工具函数 |
| `SkImages` 命名空间 | 公共图像工厂函数 |

## 设计模式与设计决策

### 模板方法模式

`SkImage_GaneshBase` 定义了 GPU 图像的通用流程，将具体实现委托给子类：

- **通用逻辑**: `getROPixels`, `onReadPixels`, `onMakeSubset`
- **子类定制**: `asView`, `asFragmentProcessor`, `origin`

### 策略模式

通过 `GrImageTexGenPolicy` 枚举控制纹理生成策略：

- `kDraw`: 绘制时使用缓存纹理
- `kNew_Uncached_Budgeted`: 创建新的有预算纹理
- `kNew_Uncached_Unbudgeted`: 创建新的无预算纹理

### 延迟实例化

Promise Image 采用延迟实例化模式，只在真正需要时才创建 GPU 纹理：

- **优势**: 减少内存占用，支持跨上下文纹理共享
- **实现**: `PromiseLazyInstantiateCallback` 包装 fulfill/release 回调
- **线程安全**: 使用 `GrResourceCache::ReturnResourceFromThread` 处理跨线程释放

### 上下文绑定设计

图像创建时绑定 `GrImageContext`，后续操作都需验证上下文匹配：

- **安全性**: 防止跨上下文错误使用资源
- **灵活性**: 支持 `GrRecordingContext` 和 `GrDirectContext` 的层次结构

## 性能考量

### 缓存策略

1. **位图缓存**: `getROPixels` 使用 `SkBitmapCache` 缓存读取的像素数据
2. **纹理复用**: Promise Image 通过 unique key 机制复用纹理
3. **条件缓存**: 根据 `CachingHint` 决定是否缓存像素数据

### 内存优化

- **引用计数**: 使用 `sk_sp` 智能指针管理 GPU 资源生命周期
- **延迟复制**: 子集创建时只在必要时复制纹理数据
- **预算管理**: 区分有预算和无预算纹理，便于 GPU 内存管理

### GPU 操作优化

- **批量刷新**: `flush` 操作可以批量提交 GPU 命令
- **表面复制优化**: 使用 `GrSurfaceProxyView::Copy` 执行高效的 GPU 端复制
- **mipmap 管理**: 根据需要动态生成或复制 mipmap 层级

### 跨线程安全

- **上下文验证**: 所有操作验证上下文匹配
- **资源释放**: Promise Image 的纹理通过消息机制在正确线程释放
- **只读访问**: `getROPixels` 提供线程安全的只读像素访问

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/image/SkImage_Ganesh.h` | 标准 GPU 纹理图像实现 |
| `src/gpu/ganesh/image/SkImage_GaneshYUVA.h` | YUVA 格式图像实现 |
| `src/gpu/ganesh/image/GrImageUtils.h` | GPU 图像工具函数 |
| `src/image/SkImage_Base.h` | 图像基类定义 |
| `include/gpu/ganesh/GrDirectContext.h` | GPU 直接上下文 API |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 表面代理视图 |
| `src/gpu/ganesh/GrTextureProxy.h` | 纹理代理 |
| `src/core/SkBitmapCache.h` | 位图缓存系统 |
