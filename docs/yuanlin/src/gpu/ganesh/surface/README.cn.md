# surface - Ganesh GPU 表面管理模块

## 概述

`src/gpu/ganesh/surface/` 目录是 Skia Ganesh GPU 渲染后端中负责绘制表面（Surface）管理的模块。绘制表面是 GPU 渲染的目标承载体，所有通过 `SkCanvas` 发出的绘制命令最终都会被渲染到某个表面上。该模块实现了 `SkSurface` 在 Ganesh GPU 后端的具体子类 `SkSurface_Ganesh`，以及围绕它的一系列工厂函数和平台适配。

`SkSurface_Ganesh` 是 Skia GPU 绘制管线的核心入口之一。它封装了底层的 `skgpu::ganesh::Device`（GPU 设备），管理着渲染目标代理（Render Target Proxy）、画布创建、图像快照、像素读写、延迟显示列表（Deferred Display List）回放等关键功能。每个 `SkSurface_Ganesh` 实例对应一个 GPU 渲染目标，可以是新创建的纹理、包装的外部后端纹理或渲染目标。

该模块还包含丰富的表面创建工厂函数，通过 `SkSurfaces` 命名空间提供多种创建路径：从特征描述创建（`RenderTarget` with `GrSurfaceCharacterization`）、从参数创建（`RenderTarget` with `SkImageInfo`）、从外部纹理包装（`WrapBackendTexture`）、从外部渲染目标包装（`WrapBackendRenderTarget`）。此外，还有 Android 和 Metal 平台的专用工厂函数。

写时复制（Copy-on-Write）机制是该模块的核心设计之一。当通过 `makeImageSnapshot()` 创建图像快照时，表面和图像可能共享底层纹理。只有当表面内容被修改时，才会触发后备纹理的复制，确保已创建的图像快照不受影响。这种延迟复制策略在大幅减少 GPU 内存拷贝的同时保证了不可变图像的语义正确性。

模块还实现了与 Chromium 的 `GrDeferredDisplayList`（DDL）系统的集成。DDL 允许在辅助线程上录制绘制命令，然后在主线程上回放到表面上，这对于多线程渲染性能至关重要。通过 `GrSurfaceCharacterization` 验证表面兼容性，确保 DDL 可以安全地在目标表面上回放。

## 架构图

```
+-------------------------------------------------------------------+
|                     SkSurface (公共 API)                           |
|  - makeImageSnapshot()                                             |
|  - getCanvas()                                                     |
|  - readPixels() / writePixels()                                    |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                   SkSurface_Base (内部基类)                        |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                   SkSurface_Ganesh (GPU 实现)                     |
|                                                                     |
|  +------------------+   +--------------------+                      |
|  | fDevice          |   | 工厂函数           |                      |
|  | (ganesh::Device) |   | (SkSurfaces::)     |                      |
|  +------------------+   +--------------------+                      |
|         |                       |                                    |
|         v                       v                                    |
|  +------------------+   +--------------------+                      |
|  | SkCanvas         |   | RenderTarget()     |                      |
|  | (绘制命令录制)   |   | WrapBackendTex()   |                      |
|  +------------------+   | WrapBackendRT()    |                      |
|                         +--------------------+                      |
+-------------------------------------------------------------------+
         |                        |
         v                        v
+-------------------+    +------------------------+
| GrRenderTarget    |    | GrSurfaceProxyView     |
| Proxy             |    |  (origin + swizzle +   |
| (渲染目标代理)    |    |   proxy)               |
+-------------------+    +------------------------+
         |
         v
+-------------------------------------------------------------------+
|                  GPU 后端资源                                       |
|  +-------------+  +------------------+  +-------------------+       |
|  | GL FBO/     |  | Vulkan           |  | Metal             |       |
|  | Texture     |  | VkImage/         |  | MTLTexture/       |       |
|  |             |  | VkRenderPass     |  | CAMetalDrawable   |       |
|  +-------------+  +------------------+  +-------------------+       |
+-------------------------------------------------------------------+
```

## 文件分类索引

### 1. 表面实现 — GPU Surface Core

| 文件 | 说明 |
|------|------|
| SkSurface_Ganesh.h / SkSurface_Ganesh.cpp | GPU 表面核心类 + SkSurfaces 工厂函数 |

### 2. 平台工厂 — Platform Factories

| 文件 | 说明 |
|------|------|
| SkSurface_AndroidFactories.cpp | Android 平台专用工厂（AHardwareBuffer） |
| SkSurface_GaneshMtl.mm | Metal 平台专用工厂（CAMetalLayer） |

## 关键类与函数

### SkSurface_Ganesh - GPU 表面核心类

这是 Ganesh GPU 渲染表面的完整实现，封装了 `skgpu::ganesh::Device`：

```cpp
class SkSurface_Ganesh : public SkSurface_Base {
public:
    SkSurface_Ganesh(sk_sp<skgpu::ganesh::Device>);
    ~SkSurface_Ganesh() override;

    // 基本属性
    SkImageInfo imageInfo() const override;
    SkSurface_Base::Type type() const override { return SkSurface_Base::Type::kGanesh; }

    // 画布与新表面创建
    SkCanvas* onNewCanvas() override;
    sk_sp<SkSurface> onNewSurface(const SkImageInfo&) override;

    // 图像快照（写时复制核心）
    sk_sp<SkImage> onNewImageSnapshot(const SkIRect* subset) override;

    // 像素操作
    void onWritePixels(const SkPixmap&, int x, int y) override;
    void onAsyncRescaleAndReadPixels(...) override;
    void onAsyncRescaleAndReadPixelsYUV420(...) override;

    // 写时复制支持
    bool onCopyOnWrite(ContentChangeMode) override;
    void onDiscard() override;

    // 后端资源访问
    bool replaceBackendTexture(const GrBackendTexture&, GrSurfaceOrigin,
                                ContentChangeMode, TextureReleaseProc, ReleaseContext) override;
    GrBackendTexture getBackendTexture(BackendHandleAccess);
    GrBackendRenderTarget getBackendRenderTarget(BackendHandleAccess);

    // DDL 支持
    bool onCharacterize(GrSurfaceCharacterization*) const override;
    bool onIsCompatible(const GrSurfaceCharacterization&) const override;
    bool draw(sk_sp<const GrDeferredDisplayList>);

    // GPU 操作
    void resolveMSAA();
    bool onWait(int numSemaphores, const GrBackendSemaphore*, bool) override;

    // 设备访问
    skgpu::ganesh::Device* getDevice();

private:
    sk_sp<skgpu::ganesh::Device> fDevice;
};
```

### 表面工厂函数 (SkSurfaces 命名空间)

所有 GPU 表面创建入口都在 `SkSurfaces` 命名空间中定义：

```cpp
namespace SkSurfaces {
    // 从特征描述创建（用于 DDL 录制后回放）
    sk_sp<SkSurface> RenderTarget(GrRecordingContext*,
                                   const GrSurfaceCharacterization&,
                                   skgpu::Budgeted);

    // 从参数创建（最常用的创建路径）
    sk_sp<SkSurface> RenderTarget(GrRecordingContext*,
                                   skgpu::Budgeted,
                                   const SkImageInfo&,
                                   int sampleCount,
                                   GrSurfaceOrigin,
                                   const SkSurfaceProps*,
                                   bool shouldCreateWithMips,
                                   bool isProtected);

    // 包装外部后端纹理
    sk_sp<SkSurface> WrapBackendTexture(GrRecordingContext*,
                                         const GrBackendTexture&,
                                         GrSurfaceOrigin,
                                         int sampleCnt,
                                         SkColorType,
                                         sk_sp<SkColorSpace>,
                                         const SkSurfaceProps*,
                                         TextureReleaseProc,
                                         ReleaseContext);

    // 包装外部后端渲染目标
    sk_sp<SkSurface> WrapBackendRenderTarget(GrRecordingContext*,
                                              const GrBackendRenderTarget&,
                                              GrSurfaceOrigin,
                                              SkColorType,
                                              sk_sp<SkColorSpace>,
                                              const SkSurfaceProps*,
                                              RenderTargetReleaseProc,
                                              ReleaseContext);

    // 后端资源访问
    GrBackendTexture GetBackendTexture(SkSurface*, BackendHandleAccess);
    GrBackendRenderTarget GetBackendRenderTarget(SkSurface*, BackendHandleAccess);
    void ResolveMSAA(SkSurface*);
}
```

### GPU 操作辅助函数 (skgpu::ganesh 命名空间)

```cpp
namespace skgpu::ganesh {
    GrSemaphoresSubmitted Flush(SkSurface*);
    GrSemaphoresSubmitted Flush(sk_sp<SkSurface>);
    void FlushAndSubmit(SkSurface*);
    void FlushAndSubmit(sk_sp<SkSurface>);
}
```

### 平台专用工厂函数

**Metal 平台** (`SkSurface_GaneshMtl.mm`):

```cpp
namespace SkSurfaces {
    // 包装 CAMetalLayer 为绘制表面
    sk_sp<SkSurface> WrapCAMetalLayer(GrRecordingContext*,
                                       GrMTLHandle layer,
                                       GrSurfaceOrigin,
                                       int sampleCnt,
                                       SkColorType,
                                       sk_sp<SkColorSpace>,
                                       const SkSurfaceProps*,
                                       GrMTLHandle* drawable);

    // 包装 MTKView 为绘制表面
    sk_sp<SkSurface> WrapMTKView(GrRecordingContext*, GrMTLHandle mtkView, ...);
}
```

**Android 平台** (`SkSurface_AndroidFactories.cpp`):

通过 `AHardwareBuffer` 创建 GPU 绘制表面，利用 Android 硬件缓冲区实现跨进程的 GPU 资源共享。

### 内部验证函数

```cpp
// 验证后端纹理是否可用作渲染目标
static bool validate_backend_texture(const GrCaps*, const GrBackendTexture&,
                                      int sampleCnt, GrColorType, bool texturable);

// 验证后端渲染目标
bool validate_backend_render_target(const GrCaps*, const GrBackendRenderTarget&, GrColorType);
```

## 依赖关系

### 向上依赖

- `include/core/SkSurface.h` / `src/image/SkSurface_Base.h` - Surface 基类
- `src/gpu/ganesh/Device.h` - Ganesh GPU 设备
- `src/gpu/ganesh/GrRecordingContext.h` - 录制上下文
- `src/gpu/ganesh/GrDirectContext.h` - 直接上下文（用于刷新和资源管理）
- `src/gpu/ganesh/GrRenderTargetProxy.h` - 渲染目标代理
- `src/gpu/ganesh/GrSurfaceProxyView.h` - 表面代理视图
- `src/gpu/ganesh/GrCaps.h` - GPU 能力查询
- `src/gpu/ganesh/GrProxyProvider.h` - 代理创建工厂

### 向下依赖（被依赖者）

- `include/gpu/ganesh/SkSurfaceGanesh.h` - 公共 API 头文件
- `src/gpu/ganesh/image/SkImage_Ganesh.h` - 快照图像的创建目标
- 应用程序代码 - 通过 `SkSurfaces::RenderTarget()` 等创建表面

### 平台依赖

- Metal: `<Metal/Metal.h>`, `<MetalKit/MetalKit.h>`, `<QuartzCore/CAMetalLayer.h>`
- Android: `AHardwareBuffer`, `AHardwareBufferUtils.h`
- Chromium: `GrDeferredDisplayList`, `GrSurfaceCharacterization`

## 设计模式分析

### 外观模式 (Facade)

`SkSurface_Ganesh` 是一个典型的外观类。它将底层复杂的 GPU 资源管理（代理、设备、上下文、渲染目标）封装在简洁的 `SkSurface` 接口之后。客户端只需通过 `getCanvas()` 获取画布并绘制，无需了解 GPU 资源的生命周期管理。

### 工厂方法模式 (Factory Method)

`SkSurfaces` 命名空间中的工厂函数是经典的工厂方法模式实现。不同的创建路径（新建、包装纹理、包装渲染目标、平台特定创建）都返回相同的 `sk_sp<SkSurface>` 接口，隐藏了内部构造的复杂性。

### 写时复制 (Copy-on-Write)

`onNewImageSnapshot()` 和 `onCopyOnWrite()` 协作实现了 COW 策略：

1. `onNewImageSnapshot()` 创建快照时，优先尝试共享纹理（通过 `SkImage_Ganesh::MakeWithVolatileSrc`）
2. 如果源是包装的外部纹理（`refsWrappedObjects`），则立即复制
3. `onCopyOnWrite()` 在表面修改前检查是否与快照共享纹理
4. 如果共享，通过 `fDevice->replaceBackingProxy()` 创建新的后备纹理

### 特征化模式 (Characterization)

`GrSurfaceCharacterization` 模式允许在没有实际 Surface 的情况下描述其特征（格式、尺寸、采样数等），用于 DDL 的录制和验证。`onCharacterize()` 提取当前表面特征，`onIsCompatible()` 验证录制的 DDL 是否可以在当前表面上回放。

## 数据流

```
创建阶段:
  SkSurfaces::RenderTarget(context, budgeted, info, ...)
            |
            v
  +----------------------------+
  | GrRecordingContext::priv() |
  |   .createDevice(...)       |
  +----------------------------+
            |
            v
  +----------------------------+
  | skgpu::ganesh::Device      |
  | (包含 GrRenderTargetProxy  |
  |  + SurfaceDrawContext)     |
  +----------------------------+
            |
            v
  +----------------------------+
  | SkSurface_Ganesh           |
  | (封装 Device)              |
  +----------------------------+

绘制阶段:
  surface->getCanvas()->drawRect(...)
            |
            v
  +----------------------------+
  | SkCanvas                   |
  |   -> skgpu::ganesh::Device |
  |     -> SurfaceDrawContext  |
  |       -> GrOps (延迟执行)  |
  +----------------------------+

快照阶段 (COW):
  surface->makeImageSnapshot()
            |
            v
  onNewImageSnapshot()
            |
            +-- 纹理源? --> MakeWithVolatileSrc()
            |                  (共享代理, 延迟复制)
            |
            +-- 外部源/子集? --> GrSurfaceProxyView::Copy()
                                   (立即复制)

  后续 surface 写入:
            |
            v
  onCopyOnWrite()
            |
            +-- 共享? --> fDevice->replaceBackingProxy()
            |               (创建新后备纹理)
            +-- 不共享? --> 继续使用当前纹理

刷新阶段:
  skgpu::ganesh::FlushAndSubmit(surface)
            |
            v
  GrDirectContext::flushAndSubmit()
            |
            v
  GPU 命令队列提交
```

## 相关文档与参考

- `include/core/SkSurface.h` - SkSurface 公共 API
- `include/gpu/ganesh/SkSurfaceGanesh.h` - Ganesh 特定的 Surface API
- `include/gpu/ganesh/GrDirectContext.h` - GPU 直接上下文
- `include/gpu/ganesh/GrRecordingContext.h` - 录制上下文
- `src/gpu/ganesh/Device.h` - Ganesh GPU 设备
- `src/gpu/ganesh/SurfaceDrawContext.h` - 表面绘制上下文
- `src/gpu/ganesh/image/SkImage_Ganesh.h` - 快照创建的图像类
- `include/private/chromium/GrDeferredDisplayList.h` - 延迟显示列表
- `include/private/chromium/GrSurfaceCharacterization.h` - 表面特征描述
- `include/android/SkSurfaceAndroid.h` - Android Surface API
- `include/gpu/ganesh/mtl/SkSurfaceMetal.h` - Metal Surface API
- Skia GPU 架构概览：https://skia.org/docs/dev/design/
