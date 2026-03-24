# GrMtlGpu

> 源文件
> - src/gpu/ganesh/mtl/GrMtlGpu.h
> - src/gpu/ganesh/mtl/GrMtlGpu.mm

## 概述

`GrMtlGpu` 是 Skia 图形库中 Metal 后端的核心 GPU 管理类,继承自 `GrGpu` 基类。它是 Metal 渲染后端的入口点,负责管理 Metal 设备、命令队列、资源提供者、纹理/缓冲区的创建与销毁、渲染通道管理、数据传输以及与 CPU 的同步。该类封装了所有与 Metal API 交互的复杂逻辑,为上层 Skia 代码提供统一的 GPU 接口。

## 架构位置

`GrMtlGpu` 是 Skia GPU Ganesh 架构中 Metal 后端的中心枢纽,连接上层渲染逻辑和底层 Metal API。

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrGpu                  (抽象GPU基类)
    ├── GrDirectContext        (渲染上下文)
    └── mtl/
        ├── GrMtlGpu           (Metal GPU管理器) ← 当前类
        ├── GrMtlCaps          (能力查询)
        ├── GrMtlCommandBuffer (命令缓冲区)
        ├── GrMtlResourceProvider (资源提供者)
        ├── GrMtlTexture       (纹理)
        ├── GrMtlBuffer        (缓冲区)
        └── GrMtlAttachment    (附件)
```

## 主要类与结构体

### GrMtlGpu

Metal GPU 管理器,封装所有 Metal 后端操作。

**继承关系:**
- 基类: `GrGpu`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMtlCaps` | `sk_sp<GrMtlCaps>` | Metal 能力查询对象 |
| `fDevice` | `id<MTLDevice>` | Metal 设备(GPU 抽象) |
| `fQueue` | `id<MTLCommandQueue>` | Metal 命令队列 |
| `fCurrentCmdBuffer` | `sk_sp<GrMtlCommandBuffer>` | 当前活动的命令缓冲区 |
| `fOutstandingCommandBuffers` | `SkDeque` | 已提交但未完成的命令缓冲区队列 |
| `fResourceProvider` | `GrMtlResourceProvider` | 资源缓存和管理 |
| `fStagingBufferManager` | `GrStagingBufferManager` | 暂存缓冲区管理器 |
| `fUniformsRingBuffer` | `GrRingBuffer` | Uniform 数据环形缓冲区 |
| `fDisconnected` | `bool` | 断开连接标志 |

## 公共 API 函数

### 工厂方法

```cpp
static std::unique_ptr<GrGpu> Make(
    const GrMtlBackendContext& context,
    const GrContextOptions& options,
    GrDirectContext* directContext
);
```
从 Metal 后端上下文创建 GPU 实例。

### 设备访问

```cpp
const GrMtlCaps& mtlCaps() const;
id<MTLDevice> device() const;
GrMtlResourceProvider& resourceProvider();
GrStagingBufferManager* stagingBufferManager() override;
GrMtlCommandBuffer* commandBuffer();
```

### 纹理创建与管理

```cpp
// 创建后端纹理
GrBackendTexture onCreateBackendTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    GrRenderable renderable,
    skgpu::Mipmapped mipmapped,
    GrProtected isProtected,
    std::string_view label
) override;

// 创建压缩纹理
GrBackendTexture onCreateCompressedBackendTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    skgpu::Mipmapped mipmapped,
    GrProtected isProtected
) override;

// 清空后端纹理
bool onClearBackendTexture(
    const GrBackendTexture& texture,
    sk_sp<skgpu::RefCntedCallback> finishedCallback,
    std::array<float, 4> color
) override;

// 删除后端纹理
void deleteBackendTexture(const GrBackendTexture& texture) override;
```

### 纹理包装

```cpp
sk_sp<GrTexture> onWrapBackendTexture(
    const GrBackendTexture& texture,
    GrWrapOwnership ownership,
    GrWrapCacheable cacheable,
    GrIOType ioType
) override;

sk_sp<GrTexture> onWrapRenderableBackendTexture(
    const GrBackendTexture& texture,
    int sampleCnt,
    GrWrapOwnership ownership,
    GrWrapCacheable cacheable
) override;

sk_sp<GrRenderTarget> onWrapBackendRenderTarget(
    const GrBackendRenderTarget& renderTarget
) override;
```

### 缓冲区创建

```cpp
sk_sp<GrGpuBuffer> onCreateBuffer(
    size_t size,
    GrGpuBufferType type,
    GrAccessPattern accessPattern
) override;
```

### 像素传输

```cpp
// 读取像素
bool onReadPixels(
    GrSurface* surface,
    SkIRect rect,
    GrColorType surfaceColorType,
    GrColorType bufferColorType,
    void* buffer,
    size_t rowBytes
) override;

// 写入像素
bool onWritePixels(
    GrSurface* surface,
    SkIRect rect,
    GrColorType surfaceColorType,
    GrColorType bufferColorType,
    const GrMipLevel texels[],
    int mipLevelCount,
    bool prepForTexSampling
) override;

// 传输像素到纹理
bool onTransferPixelsTo(
    GrTexture* texture,
    SkIRect rect,
    GrColorType textureColorType,
    GrColorType bufferColorType,
    sk_sp<GrGpuBuffer> buffer,
    size_t offset,
    size_t rowBytes
) override;

// 从表面传输像素
bool onTransferPixelsFrom(
    GrSurface* surface,
    SkIRect rect,
    GrColorType surfaceColorType,
    GrColorType bufferColorType,
    sk_sp<GrGpuBuffer> buffer,
    size_t offset
) override;
```

### 表面复制

```cpp
bool onCopySurface(
    GrSurface* dst, const SkIRect& dstRect,
    GrSurface* src, const SkIRect& srcRect,
    GrSamplerState::Filter filter
) override;

void copySurfaceAsBlit(
    GrSurface* dst, GrSurface* src,
    GrMtlAttachment* dstAttachment, GrMtlAttachment* srcAttachment,
    const SkIRect& srcRect, const SkIPoint& dstPoint
);

void copySurfaceAsResolve(GrSurface* dst, GrSurface* src);
```

### 渲染通道管理

```cpp
GrOpsRenderPass* onGetOpsRenderPass(
    GrRenderTarget* renderTarget,
    bool useMSAASurface,
    GrAttachment* stencilAttachment,
    GrSurfaceOrigin origin,
    const SkIRect& bounds,
    const GrOpsRenderPass::LoadAndStoreInfo& colorInfo,
    const GrOpsRenderPass::StencilLoadAndStoreInfo& stencilInfo,
    const skia_private::TArray<GrSurfaceProxy*, true>& sampledProxies,
    GrXferBarrierFlags renderPassXferBarriers
) override;

void submit(GrOpsRenderPass* renderPass) override;
```

### 同步与信号量

```cpp
std::unique_ptr<GrSemaphore> makeSemaphore(bool isOwned) override;
std::unique_ptr<GrSemaphore> wrapBackendSemaphore(
    const GrBackendSemaphore& semaphore,
    GrSemaphoreWrapType wrapType,
    GrWrapOwnership ownership
) override;

void insertSemaphore(GrSemaphore* semaphore) override;
void waitSemaphore(GrSemaphore* semaphore) override;
void checkFinishedCallbacks() override;
void finishOutstandingGpuWork() override;
```

### 附件创建

```cpp
sk_sp<GrAttachment> makeStencilAttachment(
    const GrBackendFormat& colorFormat,
    SkISize dimensions,
    int numStencilSamples
) override;

sk_sp<GrAttachment> makeMSAAAttachment(
    SkISize dimensions,
    const GrBackendFormat& format,
    int numSamples,
    GrProtected isProtected,
    GrMemoryless isMemoryless
) override;

GrBackendFormat getPreferredStencilFormat(
    const GrBackendFormat& colorFormat
) override;
```

### 其他操作

```cpp
// Mipmap 生成
bool onRegenerateMipMapLevels(GrTexture* texture) override;

// 渲染目标解析
void onResolveRenderTarget(
    GrRenderTarget* target,
    const SkIRect& resolveRect
) override;

// 着色器编译
bool compile(const GrProgramDesc& desc, const GrProgramInfo& info) override;

// 断开连接
void disconnect(DisconnectType type) override;
```

## 内部实现细节

### 命令缓冲区管理

#### 获取当前命令缓冲区
```cpp
GrMtlCommandBuffer* GrMtlGpu::commandBuffer() {
    if (!fCurrentCmdBuffer) {
        fCurrentCmdBuffer = GrMtlCommandBuffer::Make(fQueue);
    }
    return fCurrentCmdBuffer.get();
}
```

#### 提交命令缓冲区
```cpp
bool GrMtlGpu::submitCommandBuffer(SyncQueue sync) {
    if (!fCurrentCmdBuffer || !fCurrentCmdBuffer->hasWork()) {
        return true;
    }

    bool success = fCurrentCmdBuffer->commit(sync == kForce_SyncQueue);

    // 移动到未完成队列
    fOutstandingCommandBuffers.push_back(std::move(fCurrentCmdBuffer));
    fCurrentCmdBuffer.reset();

    return success;
}
```

#### 检查完成的命令缓冲区
```cpp
void GrMtlGpu::checkForFinishedCommandBuffers() {
    while (!fOutstandingCommandBuffers.empty()) {
        auto* cmdBuffer = static_cast<GrMtlCommandBuffer*>(
            fOutstandingCommandBuffers.front().get());

        if (!cmdBuffer->isCompleted()) {
            break;  // 队列是有序的,后续都未完成
        }

        cmdBuffer->callFinishedCallbacks();
        cmdBuffer->releaseResources();
        fOutstandingCommandBuffers.pop_front();
    }
}
```

### 纹理数据上传

Metal 使用私有存储模式(GPU专用内存)时需要通过暂存缓冲区传输:

```cpp
bool GrMtlGpu::uploadToTexture(
    GrMtlTexture* tex,
    SkIRect rect,
    GrColorType dataColorType,
    const GrMipLevel texels[],
    int mipLevels
) {
    // 1. 分配暂存缓冲区
    size_t bytesPerPixel = GrColorTypeBytesPerPixel(dataColorType);
    size_t bufferSize = rect.width() * rect.height() * bytesPerPixel;

    GrStagingBufferManager::Slice slice =
        fStagingBufferManager.allocateStagingBufferSlice(bufferSize);

    // 2. 拷贝数据到暂存缓冲区
    memcpy(slice.fOffsetMapPtr, texels[0].fPixels, bufferSize);

    // 3. 使用 Blit 编码器传输
    GrMtlCommandBuffer* cmdBuffer = this->commandBuffer();
    id<MTLBlitCommandEncoder> blitEncoder = cmdBuffer->getBlitCommandEncoder();

    [blitEncoder copyFromBuffer:stagingBuffer
                   sourceOffset:slice.fOffset
              sourceBytesPerRow:rowBytes
            sourceBytesPerImage:bufferSize
                     sourceSize:MTLSizeMake(rect.width(), rect.height(), 1)
                      toTexture:tex->mtlTexture()
               destinationSlice:0
               destinationLevel:mipLevel
              destinationOrigin:MTLOriginMake(rect.x(), rect.y(), 0)];

    return true;
}
```

### MSAA 解析

```cpp
void GrMtlGpu::copySurfaceAsResolve(GrSurface* dst, GrSurface* src) {
    GrMtlAttachment* srcAttachment = /* 获取MSAA附件 */;
    GrMtlAttachment* dstAttachment = /* 获取目标附件 */;

    MTLRenderPassDescriptor* desc = [MTLRenderPassDescriptor new];
    desc.colorAttachments[0].texture = srcAttachment->mtlTexture();
    desc.colorAttachments[0].resolveTexture = dstAttachment->mtlTexture();
    desc.colorAttachments[0].loadAction = MTLLoadActionLoad;
    desc.colorAttachments[0].storeAction = MTLStoreActionMultisampleResolve;

    // 创建空渲染通道触发解析
    GrMtlCommandBuffer* cmdBuffer = this->commandBuffer();
    GrMtlRenderCommandEncoder* encoder =
        cmdBuffer->getRenderCommandEncoder(desc, nullptr);
    encoder->endEncoding();
}
```

### 像素读回

```cpp
bool GrMtlGpu::onReadPixels(
    GrSurface* surface, SkIRect rect,
    GrColorType surfaceColorType,
    GrColorType dstColorType,
    void* buffer, size_t rowBytes
) {
    // 1. 分配传输缓冲区
    size_t transBufferSize = rect.width() * rect.height() * bytesPerPixel;
    GrStagingBufferManager::Slice slice =
        fStagingBufferManager.allocateStagingBufferSlice(
            transBufferSize, GrGpuBufferType::kXferGpuToCpu);

    // 2. 从纹理拷贝到传输缓冲区
    id<MTLBlitCommandEncoder> blitEncoder = cmdBuffer->getBlitCommandEncoder();
    [blitEncoder copyFromTexture:srcTexture
                     sourceSlice:0
                     sourceLevel:0
                    sourceOrigin:MTLOriginMake(rect.x(), rect.y(), 0)
                      sourceSize:MTLSizeMake(rect.width(), rect.height(), 1)
                        toBuffer:transferBuffer
               destinationOffset:slice.fOffset
          destinationBytesPerRow:rowBytes
        destinationBytesPerImage:transBufferSize];

    // 3. 提交并等待完成
    this->submitCommandBuffer(kForce_SyncQueue);

    // 4. 从传输缓冲区读取数据
    memcpy(buffer, slice.fOffsetMapPtr, transBufferSize);

    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrGpu` | 基类,提供跨后端GPU接口 |
| `GrMtlCaps` | 能力查询 |
| `GrMtlCommandBuffer` | 命令编码 |
| `GrMtlResourceProvider` | 资源缓存 |
| `GrMtlTexture` | 纹理管理 |
| `GrMtlBuffer` | 缓冲区管理 |
| `GrMtlAttachment` | 附件管理 |
| `GrStagingBufferManager` | 暂存缓冲区 |
| `GrRingBuffer` | 环形缓冲区 |
| `Metal/Metal.h` | Metal API |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrDirectContext` | 持有GPU实例 |
| `GrMtlOpsRenderPass` | 获取命令缓冲区 |
| `GrMtlTexture` | 通过GPU创建纹理 |
| `GrMtlBuffer` | 通过GPU创建缓冲区 |

## 设计模式与设计决策

### 单例模式(每个上下文)
每个 `GrDirectContext` 持有唯一的 `GrMtlGpu` 实例。

### 工厂模式
提供静态 `Make` 方法创建GPU实例,隐藏构造细节。

### 资源池模式
使用 `GrResourceProvider` 缓存和复用GPU资源,减少创建开销。

### 命令缓冲区批处理
延迟提交命令缓冲区,允许多个渲染操作批处理到单个提交。

### 双缓冲队列
`fCurrentCmdBuffer` + `fOutstandingCommandBuffers` 实现异步命令执行和资源回收。

## 性能考量

### 命令批处理
单个命令缓冲区可包含多个操作,减少提交次数和CPU-GPU同步点。

### 资源复用
通过 `GrMtlResourceProvider` 缓存管线状态、采样器、深度模板状态等,避免重复创建。

### 暂存缓冲区池
`GrStagingBufferManager` 管理暂存缓冲区池,复用内存,减少分配。

### 异步传输
使用 Blit 编码器异步传输数据,CPU可继续编码其他命令。

### 环形缓冲区
Uniform 数据使用环形缓冲区,避免频繁分配小缓冲区。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpu.h` | 基类 | GPU抽象基类 |
| `src/gpu/ganesh/mtl/GrMtlCaps.h` | 组合 | 能力查询 |
| `src/gpu/ganesh/mtl/GrMtlCommandBuffer.h` | 组合 | 命令缓冲区 |
| `src/gpu/ganesh/mtl/GrMtlResourceProvider.h` | 组合 | 资源提供者 |
| `src/gpu/ganesh/mtl/GrMtlTexture.h` | 管理 | 纹理对象 |
| `src/gpu/ganesh/mtl/GrMtlBuffer.h` | 管理 | 缓冲区对象 |
| `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h` | 协作 | 渲染通道 |
| `include/gpu/ganesh/mtl/GrMtlBackendContext.h` | 配置 | 后端上下文 |
