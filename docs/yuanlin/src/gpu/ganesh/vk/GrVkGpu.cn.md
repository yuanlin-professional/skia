# GrVkGpu

> 源文件
> - src/gpu/ganesh/vk/GrVkGpu.h
> - src/gpu/ganesh/vk/GrVkGpu.cpp

## 概述

`GrVkGpu` 是 Skia 图形库中 Ganesh 渲染引擎针对 Vulkan 图形 API 的核心 GPU 抽象类。它继承自 `GrGpu` 基类,实现了 Vulkan 特定的 GPU 操作接口,负责管理 Vulkan 设备、命令缓冲区、资源分配、纹理操作、渲染通道以及与 Vulkan API 的所有交互。该类是连接 Skia 高层渲染抽象与底层 Vulkan 实现的桥梁。

`GrVkGpu` 封装了 Vulkan 的物理设备、逻辑设备、队列、命令池等核心对象,并提供了创建纹理、缓冲区、渲染目标、执行绘制命令等完整的 GPU 操作能力。它还负责同步机制、内存分配、资源生命周期管理以及设备丢失处理等关键功能。

## 架构位置

```
Skia 渲染架构
├── GrDirectContext (Ganesh 上下文)
│   └── GrGpu (抽象 GPU 接口)
│       └── GrVkGpu (Vulkan GPU 实现) ← 当前类
│           ├── GrVkResourceProvider (资源提供者)
│           ├── GrVkCommandPool (命令池)
│           ├── GrVkPrimaryCommandBuffer (主命令缓冲区)
│           ├── GrStagingBufferManager (暂存缓冲区管理)
│           ├── GrVkMSAALoadManager (MSAA 加载管理)
│           └── VulkanMemoryAllocator (内存分配器)
```

`GrVkGpu` 在 Ganesh 架构中处于 GPU 抽象层,是 Vulkan 后端的核心实现类。它向上为 `GrDirectContext` 提供设备无关的 GPU 操作接口,向下管理 Vulkan 特定的资源和操作。

## 主要类与结构体

### 继承关系
```
GrGpu (基类 - GPU 抽象接口)
  ↑
GrVkGpu (派生类 - Vulkan 实现)
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInterface` | `sk_sp<const skgpu::VulkanInterface>` | Vulkan 函数指针表接口 |
| `fMemoryAllocator` | `sk_sp<skgpu::VulkanMemoryAllocator>` | Vulkan 内存分配器 |
| `fVkCaps` | `sk_sp<GrVkCaps>` | Vulkan 能力查询对象 |
| `fPhysicalDevice` | `VkPhysicalDevice` | Vulkan 物理设备句柄 |
| `fDevice` | `VkDevice` | Vulkan 逻辑设备句柄 |
| `fQueue` | `VkQueue` | Vulkan 图形队列句柄 |
| `fQueueIndex` | `uint32_t` | 队列族索引 |
| `fResourceProvider` | `GrVkResourceProvider` | 资源提供者和缓存管理 |
| `fStagingBufferManager` | `GrStagingBufferManager` | 暂存缓冲区管理器 |
| `fMSAALoadManager` | `GrVkMSAALoadManager` | MSAA 加载操作管理器 |
| `fMainCmdPool` | `GrVkCommandPool*` | 主命令池 |
| `fMainCmdBuffer` | `GrVkPrimaryCommandBuffer*` | 主命令缓冲区 |
| `fSemaphoresToWaitOn` | `STArray<1, GrVkSemaphore::Resource*>` | 待等待的信号量列表 |
| `fSemaphoresToSignal` | `STArray<1, GrVkSemaphore::Resource*>` | 待发信号的信号量列表 |
| `fDrawables` | `TArray<unique_ptr<SkDrawable::GpuDrawHandler>>` | 待处理的可绘制对象 |
| `fDisconnected` | `bool` | 设备是否已断开连接 |
| `fDeviceIsLost` | `bool` | 设备是否丢失 |
| `fProtectedContext` | `skgpu::Protected` | 是否为受保护上下文 |
| `fCachedOpsRenderPass` | `unique_ptr<GrVkOpsRenderPass>` | 缓存的渲染通道对象 |

## 公共 API 函数

### 创建与生命周期管理

| 函数签名 | 功能说明 |
|---------|---------|
| `static unique_ptr<GrGpu> Make(const VulkanBackendContext&, const GrContextOptions&, GrDirectContext*)` | 静态工厂方法,创建 GrVkGpu 实例 |
| `~GrVkGpu() override` | 析构函数,清理所有 Vulkan 资源 |
| `void disconnect(DisconnectType) override` | 断开与 GPU 的连接,释放资源 |

### 设备与能力查询

| 函数签名 | 功能说明 |
|---------|---------|
| `const VulkanInterface* vkInterface() const` | 获取 Vulkan 函数接口 |
| `const GrVkCaps& vkCaps() const` | 获取 Vulkan 能力查询对象 |
| `VkPhysicalDevice physicalDevice() const` | 获取物理设备句柄 |
| `VkDevice device() const` | 获取逻辑设备句柄 |
| `VkQueue queue() const` | 获取图形队列句柄 |
| `bool isDeviceLost() const override` | 检查设备是否丢失 |
| `bool protectedContext() const` | 检查是否为受保护上下文 |

### 资源创建

| 函数签名 | 功能说明 |
|---------|---------|
| `sk_sp<GrAttachment> makeStencilAttachment(...)` | 创建模板附件 |
| `sk_sp<GrAttachment> makeMSAAAttachment(...)` | 创建 MSAA 附件 |
| `GrBackendTexture onCreateBackendTexture(...)` | 创建后端纹理 |
| `sk_sp<GrTexture> onCreateTexture(...)` | 创建纹理对象 |
| `sk_sp<GrGpuBuffer> onCreateBuffer(...)` | 创建 GPU 缓冲区 |

### 命令提交与同步

| 函数签名 | 功能说明 |
|---------|---------|
| `bool submitCommandBuffer(const GrSubmitInfo&)` | 提交命令缓冲区到队列 |
| `void submit(GrOpsRenderPass*) override` | 提交渲染通道 |
| `unique_ptr<GrSemaphore> makeSemaphore(bool isOwned) override` | 创建信号量 |
| `void insertSemaphore(GrSemaphore*) override` | 插入信号量 |
| `void waitSemaphore(GrSemaphore*) override` | 等待信号量 |
| `void finishOutstandingGpuWork() override` | 完成所有未完成的 GPU 工作 |

### 渲染通道管理

| 函数签名 | 功能说明 |
|---------|---------|
| `bool beginRenderPass(const GrVkRenderPass*, ...)` | 开始渲染通道 |
| `void endRenderPass(GrRenderTarget*, GrSurfaceOrigin, const SkIRect&)` | 结束渲染通道 |
| `GrOpsRenderPass* onGetOpsRenderPass(...)` | 获取操作渲染通道对象 |

### 数据传输

| 函数签名 | 功能说明 |
|---------|---------|
| `bool onWritePixels(...)` | 向纹理写入像素数据 |
| `bool onReadPixels(...)` | 从表面读取像素数据 |
| `bool updateBuffer(...)` | 更新缓冲区数据 |
| `bool onCopySurface(...)` | 在表面之间复制数据 |

### 屏障与内存同步

| 函数签名 | 功能说明 |
|---------|---------|
| `void addBufferMemoryBarrier(...)` | 添加缓冲区内存屏障 |
| `void addImageMemoryBarrier(...)` | 添加图像内存屏障 |
| `void xferBarrier(GrRenderTarget*, GrXferBarrierType) override` | 添加传输屏障 |

### 管线缓存

| 函数签名 | 功能说明 |
|---------|---------|
| `bool compile(const GrProgramDesc&, const GrProgramInfo&) override` | 编译着色器程序 |
| `bool hasNewVkPipelineCacheData() const override` | 检查是否有新的管线缓存数据 |
| `void storeVkPipelineCacheData(size_t maxSize) override` | 存储管线缓存数据 |

## 内部实现细节

### 初始化流程

1. **工厂方法 `Make()`**:
   - 验证 Vulkan 后端上下文参数(实例、物理设备、逻辑设备、队列)
   - 创建 Vulkan 函数接口 `VulkanInterface`
   - 初始化能力对象 `GrVkCaps`,查询设备特性
   - 创建或使用提供的内存分配器 `VulkanMemoryAllocator`
   - 构造 `GrVkGpu` 实例

2. **构造函数初始化**:
   - 存储 Vulkan 设备句柄和队列信息
   - 初始化资源提供者 `fResourceProvider`
   - 创建主命令池 `fMainCmdPool`
   - 从命令池获取主命令缓冲区 `fMainCmdBuffer`
   - 开始命令记录 `begin()`

### 命令缓冲区管理

`GrVkGpu` 维护一个主命令缓冲区,用于记录所有 GPU 命令:

```cpp
bool GrVkGpu::submitCommandBuffer(const GrSubmitInfo& submitInfo) {
    // 检查命令缓冲区是否有实际工作
    if (!hasWork && syncNo && noSemaphores) {
        // 直接调用完成回调
        callFinishedProcs();
        return true;
    }

    // 结束当前命令缓冲区记录
    fMainCmdBuffer->end(this);
    fMainCmdPool->close();

    // 提交到队列(附带信号量)
    bool submitted = fMainCmdBuffer->submitToQueue(
        this, fQueue, fSemaphoresToSignal, fSemaphoresToWaitOn, submitInfo);

    // 同步等待(如果需要)
    if (submitted && submitInfo.fSync == GrSyncCpu::kYes) {
        fMainCmdBuffer->forceSync(this);
    }

    // 清理资源和信号量
    clearSemaphores();

    // 创建新的命令池和命令缓冲区
    fMainCmdPool = fResourceProvider.findOrCreateCommandPool();
    fMainCmdBuffer = fMainCmdPool->getPrimaryCommandBuffer();
    fMainCmdBuffer->begin(this);

    return submitted;
}
```

### 渲染通道创建

渲染通道的创建涉及帧缓冲区、渲染通道兼容性、加载/存储操作等:

```cpp
GrOpsRenderPass* GrVkGpu::onGetOpsRenderPass(...) {
    // 获取或创建 VkFramebuffer
    GrVkRenderTarget* vkRT = static_cast<GrVkRenderTarget*>(rt);
    sk_sp<GrVkFramebuffer> framebuffer = vkRT->getFramebuffer(...);

    // 处理 MSAA 可丢弃附件的特殊情况
    if (useMSAASurface && renderTargetSupportsDiscardableMSAA(vkRT)) {
        // 调整加载/存储操作
        localColorInfo.fStoreOp = GrStoreOp::kDiscard;
        if (colorInfo.fLoadOp == GrLoadOp::kLoad) {
            loadFromResolve = LoadFromResolve::kLoad;
        }
    }

    // 设置渲染通道参数
    fCachedOpsRenderPass->set(rt, framebuffer, origin, bounds, ...);
    return fCachedOpsRenderPass.get();
}
```

### 内存屏障管理

为确保 GPU 操作的正确顺序和数据可见性,`GrVkGpu` 提供了内存屏障机制:

```cpp
void GrVkGpu::addImageMemoryBarrier(
    const GrManagedResource* resource,
    VkPipelineStageFlags srcStageMask,
    VkPipelineStageFlags dstStageMask,
    bool byRegion,
    VkImageMemoryBarrier* barrier) {

    SkASSERT(fMainCmdBuffer);
    // 将屏障添加到当前命令缓冲区
    fMainCmdBuffer->pipelineBarrier(
        this, resource, srcStageMask, dstStageMask, byRegion,
        kMemory_BarrierType, barrier);
}
```

### 纹理上传策略

根据纹理的 tiling 模式选择不同的上传策略:

- **Linear Tiling**: 直接映射内存并复制数据
- **Optimal Tiling**: 使用暂存缓冲区,然后通过 `vkCmdCopyBufferToImage` 传输

### 设备丢失处理

`checkVkResult()` 函数检查每个 Vulkan 调用的结果:

```cpp
bool GrVkGpu::checkVkResult(VkResult result) {
    switch (result) {
        case VK_SUCCESS:
            return true;
        case VK_ERROR_DEVICE_LOST:
            fDeviceIsLost = true;
            if (fDeviceLostProc) {
                fDeviceLostProc(fDeviceLostContext, /*messages=*/"");
            }
            return false;
        case VK_ERROR_OUT_OF_DEVICE_MEMORY:
        case VK_ERROR_OUT_OF_HOST_MEMORY:
            // 处理内存不足情况
            return false;
        default:
            return false;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrGpu` | 基类,定义 GPU 抽象接口 |
| `GrVkCaps` | Vulkan 能力查询,提供设备特性信息 |
| `VulkanInterface` | Vulkan 函数指针表,封装 API 调用 |
| `VulkanMemoryAllocator` | 内存分配器,管理 GPU 内存 |
| `GrVkResourceProvider` | 资源提供者,管理管线、描述符集等 |
| `GrVkCommandBuffer` | 命令缓冲区封装 |
| `GrVkCommandPool` | 命令池管理 |
| `GrVkImage` | Vulkan 图像封装 |
| `GrVkTexture` | Vulkan 纹理对象 |
| `GrVkRenderTarget` | Vulkan 渲染目标 |
| `GrVkFramebuffer` | Vulkan 帧缓冲区 |
| `GrVkRenderPass` | Vulkan 渲染通道 |
| `GrVkBuffer` | Vulkan 缓冲区封装 |
| `GrStagingBufferManager` | 暂存缓冲区管理器 |
| `GrVkMSAALoadManager` | MSAA 加载管理器 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrDirectContext` | Ganesh 上下文通过 GrVkGpu 执行 GPU 操作 |
| `GrVkOpsRenderPass` | 渲染通道需要 GrVkGpu 提供设备和命令缓冲区 |
| `GrVkPipelineState` | 管线状态需要 GrVkGpu 创建和绑定 |
| `GrVkGpuCommandBuffer` | GPU 命令缓冲区需要访问 GrVkGpu 的队列 |

## 设计模式与设计决策

### 1. 工厂模式 (Factory Pattern)

使用静态工厂方法 `Make()` 创建 `GrVkGpu` 实例,封装复杂的初始化逻辑:

```cpp
static std::unique_ptr<GrGpu> GrVkGpu::Make(
    const skgpu::VulkanBackendContext& backendContext,
    const GrContextOptions& options,
    GrDirectContext* direct);
```

**优势**:
- 将构造逻辑与使用逻辑分离
- 允许在创建失败时返回 nullptr
- 支持复杂的参数验证和资源初始化

### 2. 资源获取即初始化 (RAII)

通过智能指针 `sk_sp` 和 `unique_ptr` 管理 Vulkan 资源生命周期,确保异常安全:

```cpp
sk_sp<const skgpu::VulkanInterface> fInterface;
sk_sp<skgpu::VulkanMemoryAllocator> fMemoryAllocator;
std::unique_ptr<GrVkOpsRenderPass> fCachedOpsRenderPass;
```

### 3. 策略模式 (Strategy Pattern)

通过 `GrVkCaps` 封装能力查询,根据设备特性选择不同的执行策略:

```cpp
if (fGpu->vkCaps().preferPrimaryOverSecondaryCommandBuffers()) {
    // 使用主命令缓冲区策略
} else {
    // 使用辅助命令缓冲区策略
}
```

### 4. 命令模式 (Command Pattern)

使用命令缓冲区模式,将所有 GPU 操作记录到命令缓冲区,然后批量提交:

```cpp
// 记录命令
fMainCmdBuffer->draw(...);
fMainCmdBuffer->bindPipeline(...);

// 批量提交
submitCommandBuffer(submitInfo);
```

### 5. 对象池模式 (Object Pool Pattern)

通过 `GrVkResourceProvider` 管理可重用资源(管线、描述符集、命令池):

```cpp
GrVkCommandPool* fMainCmdPool =
    fResourceProvider.findOrCreateCommandPool();
```

### 6. 单一职责原则

将不同功能分离到专门的管理器:
- `GrVkResourceProvider`: 资源创建和缓存
- `GrStagingBufferManager`: 暂存缓冲区管理
- `GrVkMSAALoadManager`: MSAA 加载操作
- 每个组件专注于单一职责,提高可维护性

## 性能考量

### 1. 命令缓冲区批处理

- **批量提交**: 将多个绘制命令记录到单个命令缓冲区,减少提交开销
- **延迟提交**: 只有在必要时(如需要同步、信号量等待)才提交命令缓冲区

### 2. 资源池化

- **命令池复用**: 通过 `findOrCreateCommandPool()` 复用命令池,避免频繁创建/销毁
- **渲染通道缓存**: `fCachedOpsRenderPass` 避免每次都创建新的渲染通道对象
- **管线状态缓存**: 由 `GrVkResourceProvider` 管理,避免重复编译

### 3. 内存管理优化

- **暂存缓冲区管理**: `GrStagingBufferManager` 统一管理数据上传的暂存缓冲区
- **内存分配器抽象**: 支持自定义内存分配器(如 VMA),优化内存分配策略
- **懒分配支持**: 对于瞬态附件,使用 `VK_IMAGE_USAGE_TRANSIENT_ATTACHMENT_BIT`

### 4. 同步优化

- **最小化同步点**: 只在必要时调用 `forceSync()`,避免 GPU-CPU 同步
- **细粒度屏障**: 根据实际访问模式精确设置内存屏障的阶段和访问掩码
- **信号量批处理**: 将多个信号量一次性提交,减少同步开销

### 5. 管线状态管理

- **动态状态**: 使用 Vulkan 动态状态(viewport、scissor、blend constants)减少管线对象数量
- **管线缓存**: 支持持久化管线缓存,加速应用启动

### 6. MSAA 优化

- **可丢弃 MSAA**: 支持 discardable MSAA,节省带宽和内存
- **MSAA Load Manager**: 专门的管理器处理从 resolve 附件加载到 MSAA 附件的场景

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrGpu.h` | 基类定义,提供 GPU 抽象接口 |
| `src/gpu/ganesh/vk/GrVkCaps.h/cpp` | Vulkan 能力查询实现 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp` | 资源提供者和缓存管理 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h/cpp` | 命令缓冲区封装 |
| `src/gpu/ganesh/vk/GrVkCommandPool.h/cpp` | 命令池管理 |
| `src/gpu/ganesh/vk/GrVkOpsRenderPass.h/cpp` | 操作渲染通道实现 |
| `src/gpu/ganesh/vk/GrVkImage.h/cpp` | Vulkan 图像封装 |
| `src/gpu/ganesh/vk/GrVkTexture.h/cpp` | Vulkan 纹理对象 |
| `src/gpu/ganesh/vk/GrVkRenderTarget.h/cpp` | Vulkan 渲染目标 |
| `src/gpu/ganesh/vk/GrVkFramebuffer.h/cpp` | Vulkan 帧缓冲区 |
| `src/gpu/ganesh/vk/GrVkRenderPass.h/cpp` | Vulkan 渲染通道 |
| `src/gpu/ganesh/vk/GrVkBuffer.h/cpp` | Vulkan 缓冲区封装 |
| `src/gpu/ganesh/vk/GrVkSemaphore.h/cpp` | Vulkan 信号量封装 |
| `src/gpu/ganesh/vk/GrVkUtil.h/cpp` | Vulkan 工具函数 |
| `src/gpu/vk/VulkanInterface.h/cpp` | Vulkan 函数接口 |
| `src/gpu/vk/VulkanMemoryAllocator.h` | 内存分配器接口 |
| `include/gpu/vk/VulkanBackendContext.h` | Vulkan 后端上下文定义 |
