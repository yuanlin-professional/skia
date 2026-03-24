# GrRecordingContextPriv

> 源文件
> - src/gpu/ganesh/GrRecordingContextPriv.h
> - src/gpu/ganesh/GrRecordingContextPriv.cpp

## 概述

`GrRecordingContextPriv` 是 `GrRecordingContext` 的特权访问类,提供了仅供 Skia 内部使用的接口。它遵循"特权窗口"(Privileged Window)设计模式,暴露 `GrRecordingContext` 中不应对外公开但需要被内部模块访问的功能。

该类的主要职责包括:
- 提供内部组件的访问接口(ProxyProvider、DrawingManager、Allocators 等)
- 创建设备(Device)和表面上下文(SurfaceContext/SurfaceFillContext)
- 管理程序信息记录和 DDL(Deferred Display List)操作
- 提供内部统计和调试支持
- 管理刷新回调对象

`GrRecordingContextPriv` 确保了 API 的清晰分层:公共 API 在 `GrRecordingContext`,内部 API 在 `GrRecordingContextPriv`。

## 架构位置

`GrRecordingContextPriv` 在 Ganesh 上下文层次结构中的位置:

```
GrContext_Base (基础上下文)
    └── GrImageContext (图像上下文)
        └── GrRecordingContext (记录上下文)
            └── GrRecordingContextPriv (特权访问器)
                ├── GrProxyProvider (代理提供者)
                ├── GrDrawingManager (绘制管理器)
                ├── Arenas (内存分配器)
                └── 创建各种上下文和设备
```

它继承自 `GrImageContextPriv`,进一步扩展了特权接口。

## 主要类与结构体

### GrRecordingContextPriv 类

**继承关系**:
- 继承自 `GrImageContextPriv`
- 作为 `GrRecordingContext` 的友元类

**核心访问方法**:

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| context() | GrRecordingContext* | 获取记录上下文 |
| proxyProvider() | GrProxyProvider* | 获取代理提供者 |
| drawingManager() | GrDrawingManager* | 获取绘制管理器 |
| recordTimeAllocator() | SkArenaAlloc* | 获取记录时分配器 |
| recordTimeSubRunAllocator() | SubRunAllocator* | 获取文本子运行分配器 |
| arenas() | GrRecordingContext::Arenas | 获取分配器集合 |
| threadSafeCache() | GrThreadSafeCache* | 获取线程安全缓存 |
| auditTrail() | GrAuditTrail* | 获取审计跟踪 |

## 公共 API 函数

### 组件访问

```cpp
GrProxyProvider* proxyProvider();
const GrProxyProvider* proxyProvider() const;
GrDrawingManager* drawingManager();
sktext::gpu::TextBlobRedrawCoordinator* getTextBlobCache();
GrThreadSafeCache* threadSafeCache();
GrAuditTrail* auditTrail();
```

### 内存分配器

```cpp
SkArenaAlloc* recordTimeAllocator();
sktext::gpu::SubRunAllocator* recordTimeSubRunAllocator();
GrRecordingContext::Arenas arenas();
GrRecordingContext::OwnedArenas&& detachArenas();
```

### 程序信息管理

```cpp
void recordProgramInfo(const GrProgramInfo* programInfo);
void detachProgramData(skia_private::TArray<GrRecordingContext::ProgramData>* dst);
```

记录程序信息用于 DDL(延迟显示列表)。

### DDL 操作

```cpp
void moveRenderTasksToDDL(GrDeferredDisplayList*);
```

将渲染任务移动到 DDL 中,用于跨线程渲染。

### 刷新回调

```cpp
void addOnFlushCallbackObject(GrOnFlushCallbackObject*);
```

注册刷新回调对象,在 flush 时执行自定义逻辑。

### 设备创建

```cpp
sk_sp<skgpu::ganesh::Device> createDevice(
    GrColorType, sk_sp<GrSurfaceProxy>, sk_sp<SkColorSpace>,
    GrSurfaceOrigin, const SkSurfaceProps&,
    skgpu::ganesh::Device::InitContents);

sk_sp<skgpu::ganesh::Device> createDevice(
    skgpu::Budgeted, const SkImageInfo&, SkBackingFit,
    int sampleCount, skgpu::Mipmapped, skgpu::Protected,
    GrSurfaceOrigin, const SkSurfaceProps&,
    skgpu::ganesh::Device::InitContents);
```

创建 GPU 支持的绘制设备。

### 表面上下文创建

```cpp
// 创建通用表面上下文
std::unique_ptr<skgpu::ganesh::SurfaceContext> makeSC(
    GrSurfaceProxyView readView, const GrColorInfo&);

std::unique_ptr<skgpu::ganesh::SurfaceContext> makeSC(
    const GrImageInfo&, const GrBackendFormat&, std::string_view label,
    SkBackingFit, GrSurfaceOrigin, skgpu::Renderable,
    int renderTargetSampleCnt, skgpu::Mipmapped, skgpu::Protected,
    skgpu::Budgeted);

// 创建填充上下文
std::unique_ptr<skgpu::ganesh::SurfaceFillContext> makeSFC(
    GrImageInfo, std::string_view label, SkBackingFit,
    int sampleCount, skgpu::Mipmapped, skgpu::Protected,
    GrSurfaceOrigin, skgpu::Budgeted);

// 带回退的创建
std::unique_ptr<skgpu::ganesh::SurfaceFillContext> makeSFCWithFallback(
    GrImageInfo, SkBackingFit, int sampleCount,
    skgpu::Mipmapped, skgpu::Protected, GrSurfaceOrigin,
    skgpu::Budgeted);

// 从后端纹理创建
std::unique_ptr<skgpu::ganesh::SurfaceFillContext> makeSFCFromBackendTexture(
    GrColorInfo, const GrBackendTexture&, int sampleCount,
    GrSurfaceOrigin, sk_sp<skgpu::RefCntedCallback> releaseHelper);
```

### 文本渲染配置

```cpp
sktext::gpu::SubRunControl getSubRunControl(bool useSDFTForSmallText) const;
```

获取文本子运行控制配置,支持 SDF(有向距离场)文本渲染。

### 调试和测试

```cpp
GrRecordingContext::Stats* stats();

#if GR_GPU_STATS && defined(GPU_TEST_UTILS)
DMSAAStats& dmsaaStats();
#endif

#if defined(GPU_TEST_UTILS)
class AutoSuppressWarningMessages;
void incrSuppressWarningMessages();
void decrSuppressWarningMessages();
#endif

void printWarningMessage(const char* msg) const;
```

### 静态工厂方法

```cpp
static sk_sp<GrRecordingContext> MakeDDL(sk_sp<GrContextThreadSafeProxy>);
```

创建用于 DDL 的记录上下文(没有资源缓存)。

## 内部实现细节

### 设备创建实现

直接委托给 `skgpu::ganesh::Device::Make`:

```cpp
sk_sp<skgpu::ganesh::Device> GrRecordingContextPriv::createDevice(
        GrColorType colorType, sk_sp<GrSurfaceProxy> proxy,
        sk_sp<SkColorSpace> colorSpace, GrSurfaceOrigin origin,
        const SkSurfaceProps& props,
        skgpu::ganesh::Device::InitContents init) {
    return skgpu::ganesh::Device::Make(
        this->context(), colorType, std::move(proxy),
        std::move(colorSpace), origin, props, init);
}
```

### 表面上下文创建逻辑

`makeSC` 方法根据代理类型创建不同的上下文:

```cpp
if (proxy->asRenderTargetProxy()) {
    // 可渲染 -> SurfaceDrawContext 或 SurfaceFillContext
    if (info.alphaType() == kPremul_SkAlphaType ||
        info.alphaType() == kOpaque_SkAlphaType) {
        sc = std::make_unique<SurfaceDrawContext>(...);
    } else {
        sc = std::make_unique<SurfaceFillContext>(...);
    }
} else {
    // 仅纹理 -> SurfaceContext
    sc = std::make_unique<SurfaceContext>(...);
}
```

### 颜色类型回退

`makeSFCWithFallback` 处理不支持的颜色类型:

```cpp
auto [ct, _] = caps->getFallbackColorTypeAndFormat(
    info.colorType(), sampleCount);
if (ct == GrColorType::kUnknown) {
    return nullptr;
}
info = info.makeColorType(ct);
```

### SubRunControl 配置

根据能力和选项配置文本渲染:

```cpp
return sktext::gpu::SubRunControl{
    this->caps()->shaderCaps()->supportsDistanceFieldText(),
    useSDFTForSmallText,
    !this->caps()->disablePerspectiveSDFText(),
    this->options().fMinDistanceFieldFontSize,
    this->options().fGlyphsAsPathsFontSize
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrRecordingContext | 被访问的主上下文 |
| GrProxyProvider | 代理管理 |
| GrDrawingManager | 绘制任务管理 |
| GrCaps | GPU 能力查询 |
| skgpu::ganesh::Device | GPU 设备 |
| SurfaceContext/SurfaceFillContext | 表面绘制上下文 |
| SkArenaAlloc | 内存分配器 |
| sktext::gpu::SubRunAllocator | 文本分配器 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrOpsTask | 通过 priv 访问内部功能 |
| GrDrawingManager | 通过 priv 访问上下文组件 |
| SkGpuDevice | 通过 priv 创建表面上下文 |
| DDL 相关代码 | 使用 priv 进行 DDL 操作 |

## 设计模式与设计决策

### 特权窗口模式(Privileged Window)

这是该类的核心模式:
- 不增加数据成员或虚函数
- 仅提供访问接口
- 通过友元关系访问私有成员
- 使用 `priv()` 方法获取实例

```cpp
inline GrRecordingContextPriv GrRecordingContext::priv() {
    return GrRecordingContextPriv(this);
}
```

### 封装和访问控制

将内部 API 与公共 API 清晰分离:
- 公共 API:面向应用开发者
- Priv API:面向 Skia 内部开发者

### 工厂模式

提供多种工厂方法创建设备和上下文,封装复杂的创建逻辑。

### 委托模式

大部分方法直接委托给 `GrRecordingContext` 的私有方法,避免代码重复。

### 条件编译

使用 `#if defined(GPU_TEST_UTILS)` 隔离测试和调试代码,减少发布版本大小。

## 性能考量

### 零开销抽象

`GrRecordingContextPriv` 不增加额外数据成员,只是一个指针的包装,编译器通常能完全优化掉这层抽象。

### 内联访问器

简单的访问方法内联在头文件中。

### 避免虚函数

明确声明不应有虚函数,避免虚表开销。

### 分配器优化

- `SkArenaAlloc`:快速栈式分配,适合大量小对象
- `SubRunAllocator`:专门优化文本子运行分配
- 支持分离(detach)和转移所有权,避免拷贝

### 表面上下文缓存

使用线程安全缓存复用表面上下文,减少创建开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/gpu/ganesh/GrRecordingContext.h | 主类 | 被访问的记录上下文 |
| src/gpu/ganesh/GrImageContextPriv.h | 基类 | 图像上下文特权访问 |
| src/gpu/ganesh/GrProxyProvider.h/cpp | 组件 | 代理提供者 |
| src/gpu/ganesh/GrDrawingManager.h/cpp | 组件 | 绘制管理器 |
| src/gpu/ganesh/Device.h/cpp | 使用 | GPU 设备 |
| src/gpu/ganesh/SurfaceContext.h/cpp | 创建 | 表面上下文 |
| src/gpu/ganesh/SurfaceFillContext.h/cpp | 创建 | 填充上下文 |
| src/gpu/ganesh/SurfaceDrawContext.h/cpp | 创建 | 绘制上下文 |
| include/private/gpu/ganesh/GrImageContext.h | 继承 | 图像上下文基类 |
| src/gpu/ganesh/GrCaps.h | 依赖 | GPU 能力 |
| src/text/gpu/SubRunControl.h | 使用 | 文本渲染控制 |
| src/gpu/ganesh/GrDeferredDisplayList.h | 使用 | DDL 支持 |
