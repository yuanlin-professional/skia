# src/gpu/ganesh/vk - Skia Ganesh Vulkan 后端实现

## 概述

本目录是 Skia 图形库中 Ganesh GPU 渲染引擎的 **Vulkan 后端**完整实现，包含约 70 个源文件（头文件与实现文件）。Ganesh 是 Skia 的传统 GPU 加速渲染管线（区别于新一代的 Graphite 后端），而 `vk` 目录则负责将 Ganesh 的通用 GPU 抽象层映射到 Vulkan API 的具体调用上。

Vulkan 后端实现了从 GPU 设备管理、命令缓冲区录制与提交、渲染管线（Pipeline）构建、资源（图像、缓冲区、采样器、描述符集）的创建与缓存、渲染通道（Render Pass）与帧缓冲区（Framebuffer）管理，到着色器编译（GLSL -> SPIR-V）、Uniform 数据布局等完整的渲染基础设施。它是 Skia 在 Android、Linux、Windows 等平台上使用 Vulkan 进行高性能 2D 渲染的核心模块。

本目录中的所有类均以 `GrVk` 为前缀，遵循 Skia 的命名约定。大部分类继承自 `src/gpu/ganesh/` 中定义的通用基类（如 `GrGpu`、`GrCaps`、`GrTexture`、`GrRenderTarget` 等），通过重写虚函数来提供 Vulkan 特定的行为。GPU 资源的生命周期管理采用引用计数机制（`sk_sp`、`GrManagedResource`），确保资源在命令缓冲区执行完成后才被安全释放。

该模块还包含大量针对特定 GPU 厂商和驱动程序的兼容性处理（workaround），例如 Nvidia Windows 驱动的 `QueueWaitIdle` 信号延迟问题、Intel 不同代次 GPU 的特殊行为等，这些都在 `GrVkCaps` 中集中管理。对 Android 硬件缓冲区（AHardwareBuffer）、YCbCr 色彩空间转换、DRM 格式修饰符等平台特性的支持也在此模块中实现。

## 架构图

```
                          +-------------------+
                          |   GrDirectContext  |
                          +--------+----------+
                                   |
                                   v
                          +-------------------+
                          |     GrVkGpu       |  <-- 核心入口：GPU 设备管理与操作调度
                          |  (继承 GrGpu)     |
                          +---+-----+-----+---+
                              |     |     |
              +---------------+     |     +------------------+
              |                     |                        |
              v                     v                        v
    +-------------------+  +------------------+  +------------------------+
    | GrVkCaps          |  | GrVkResource-    |  | GrVkCommandPool        |
    | (继承 GrCaps)     |  | Provider         |  +----------+-------------+
    | 能力查询/格式支持  |  | 资源缓存与复用    |             |
    +-------------------+  +---+----+----+---+             v
                               |    |    |      +------------------------+
              +----------------+    |    +----->| GrVkPrimaryCommandBuffer|
              |                     |           | GrVkSecondaryCommand-  |
              v                     v           | Buffer                 |
    +-------------------+  +------------------+ +----------+-------------+
    | GrVkPipeline-     |  | GrVkRenderPass   |            |
    | StateCache (LRU)  |  | CompatibleRP-    |            v
    | GrVkPipelineState |  | Set              |  +------------------------+
    +--------+----------+  +------------------+  | Vulkan 命令录制         |
             |                     |             | draw/bindPipeline/     |
             v                     v             | barrier/copy...        |
    +-------------------+  +------------------+  +------------------------+
    | GrVkPipeline      |  | GrVkFramebuffer  |
    | (VkPipeline封装)  |  | (VkFramebuffer   |
    +-------------------+  |  封装)           |
                           +------------------+
                                   |
              +--------------------+-------------------+
              |                    |                    |
              v                    v                    v
    +-------------------+  +------------------+  +-----------------+
    | GrVkImage         |  | GrVkTexture      |  | GrVkRenderTarget|
    | (VkImage 封装     |  | (纹理资源)       |  | (渲染目标)      |
    |  + ImageView)     |  +------------------+  +-----------------+
    +-------------------+          |                    |
                                   +--------------------+
                                   v
                           +------------------+
                           | GrVkTexture-     |
                           | RenderTarget     |
                           | (纹理+渲染目标)  |
                           +------------------+

    资源/描述符管理子系统:
    +---------------------+  +---------------------+  +-------------------+
    | GrVkDescriptorSet-  |  | GrVkDescriptorPool  |  | GrVkDescriptorSet |
    | Manager             |->| (VkDescriptorPool)  |->| (VkDescriptorSet) |
    +---------------------+  +---------------------+  +-------------------+

    采样器子系统:
    +-------------------+  +----------------------------+
    | GrVkSampler       |  | GrVkSamplerYcbcrConversion |
    | (VkSampler 封装)  |  | (YCbCr 色彩空间转换)       |
    +-------------------+  +----------------------------+

    着色器编译子系统:
    +----------------------------+  +-------------------+  +-------------------+
    | GrVkPipelineStateBuilder   |  | GrVkUniformHandler|  | GrVkVaryingHandler|
    | (GLSL -> SPIR-V -> State)  |  | (Uniform 布局)    |  | (Varying 布局)    |
    +----------------------------+  +-------------------+  +-------------------+
```

## 文件分类索引

### 1. 核心实现 — GPU/Caps/Context

| 文件 | 说明 |
|------|------|
| GrVkGpu.h / GrVkGpu.cpp | Vulkan GPU 设备管理核心类（~118KB 实现） |
| GrVkCaps.h / GrVkCaps.cpp | Vulkan 能力查询与格式支持（~97KB 实现） |
| GrVkDirectContext.cpp | GrDirectContext 的 Vulkan 创建入口 |
| GrVkContextThreadSafeProxy.h / GrVkContextThreadSafeProxy.cpp | 线程安全上下文代理 |

### 2. 命令/渲染 — Command Buffer/RenderPass

| 文件 | 说明 |
|------|------|
| GrVkCommandBuffer.h / GrVkCommandBuffer.cpp | 命令缓冲区基类及主/次命令缓冲区 |
| GrVkCommandPool.h / GrVkCommandPool.cpp | 命令池管理 |
| GrVkOpsRenderPass.h / GrVkOpsRenderPass.cpp | 操作渲染通道（绘制命令录制） |
| GrVkSemaphore.h / GrVkSemaphore.cpp | 信号量（GPU 同步） |

### 3. 管线管理 — Pipeline

| 文件 | 说明 |
|------|------|
| GrVkPipeline.h / GrVkPipeline.cpp | VkPipeline 封装（状态映射与创建） |
| GrVkPipelineState.h / GrVkPipelineState.cpp | 管线状态（Pipeline + Uniform + 采样器绑定） |
| GrVkPipelineStateBuilder.h / GrVkPipelineStateBuilder.cpp | 管线状态构建器（SkSL→SPIR-V 编译） |
| GrVkPipelineStateCache.cpp | 管线状态 LRU 缓存 |
| GrVkPipelineStateDataManager.h / GrVkPipelineStateDataManager.cpp | Uniform 数据管理器 |

### 4. 描述符管理 — Descriptor Sets

| 文件 | 说明 |
|------|------|
| GrVkDescriptorPool.h / GrVkDescriptorPool.cpp | VkDescriptorPool 封装 |
| GrVkDescriptorSet.h / GrVkDescriptorSet.cpp | VkDescriptorSet 封装 |
| GrVkDescriptorSetManager.h / GrVkDescriptorSetManager.cpp | 描述符集分配与回收管理 |

### 5. 渲染基础设施 — RenderPass/Framebuffer

| 文件 | 说明 |
|------|------|
| GrVkRenderPass.h / GrVkRenderPass.cpp | VkRenderPass 封装与兼容性管理 |
| GrVkFramebuffer.h / GrVkFramebuffer.cpp | VkFramebuffer 封装 |
| GrVkMSAALoadManager.h / GrVkMSAALoadManager.cpp | MSAA 加载管理器 |

### 6. 图像与纹理 — Image/Texture/RenderTarget

| 文件 | 说明 |
|------|------|
| GrVkImage.h / GrVkImage.cpp | VkImage 封装（含布局转换） |
| GrVkImageView.h / GrVkImageView.cpp | VkImageView 封装 |
| GrVkImageLayout.h | 图像布局定义 |
| GrVkTexture.h / GrVkTexture.cpp | Vulkan 纹理 |
| GrVkRenderTarget.h / GrVkRenderTarget.cpp | Vulkan 渲染目标 |
| GrVkTextureRenderTarget.h / GrVkTextureRenderTarget.cpp | 纹理 + 渲染目标复合资源 |
| GrVkBuffer.h / GrVkBuffer.cpp | VkBuffer 封装（顶点/索引/Uniform 缓冲区） |

### 7. 采样器 — Sampler

| 文件 | 说明 |
|------|------|
| GrVkSampler.h / GrVkSampler.cpp | VkSampler 封装 |
| GrVkSamplerYcbcrConversion.h / GrVkSamplerYcbcrConversion.cpp | YCbCr 采样转换 |

### 8. 能力/工具 — Utilities

| 文件 | 说明 |
|------|------|
| GrVkUtil.h / GrVkUtil.cpp | Vulkan 工具函数（SkSL→SPIR-V、格式转换等） |
| GrVkTypesPriv.h / GrVkTypesPriv.cpp | Vulkan 类型私有定义 |

### 9. Uniform/Varying — 着色器变量管理

| 文件 | 说明 |
|------|------|
| GrVkUniformHandler.h / GrVkUniformHandler.cpp | Vulkan Uniform 变量布局处理 |
| GrVkVaryingHandler.h / GrVkVaryingHandler.cpp | Vulkan Varying 变量处理 |

### 10. 资源管理 — Resource Provider

| 文件 | 说明 |
|------|------|
| GrVkResourceProvider.h / GrVkResourceProvider.cpp | 资源提供者（集中管理所有资源缓存） |
| GrVkManagedResource.h | Vulkan 托管资源基类 |

### 11. 后端表面/平台互操作 — Backend Surface

| 文件 | 说明 |
|------|------|
| GrVkBackendSurface.cpp / GrVkBackendSurfacePriv.h | 后端表面 Vulkan 实现 |
| GrVkBackendSemaphore.cpp | 后端信号量 |
| GrVkSecondaryCBDrawContext.cpp | 次级命令缓冲区绘制上下文 |
| AHardwareBufferVk.cpp | Android 硬件缓冲区 Vulkan 集成 |

## 关键类与函数

### 1. GrVkGpu（文件：`GrVkGpu.h` / `GrVkGpu.cpp`）

**职责**：Vulkan GPU 设备的核心管理类，继承自 `GrGpu`，是整个 Vulkan 后端的入口点和协调中心。

**关键方法**：
- `Make()` -- 静态工厂方法，根据 `VulkanBackendContext` 创建 GPU 实例
- `onCreateTexture()` / `onWrapBackendTexture()` -- 创建或包装纹理
- `onReadPixels()` / `onWritePixels()` -- CPU-GPU 数据传输
- `onCopySurface()` -- 表面拷贝（支持 CopyImage/Blit/Resolve 三种策略）
- `submitCommandBuffer()` -- 提交命令缓冲区到队列
- `beginRenderPass()` / `endRenderPass()` -- 渲染通道生命周期管理
- `checkVkResult()` -- 检查 Vulkan 调用结果，处理设备丢失和 OOM
- `addBufferMemoryBarrier()` / `addImageMemoryBarrier()` -- 内存屏障管理

**关键成员**：
- `fDevice` / `fPhysicalDevice` / `fQueue` -- Vulkan 设备句柄
- `fResourceProvider` -- 资源提供者，管理所有可缓存资源
- `fMainCmdPool` / `fMainCmdBuffer` -- 主命令池和命令缓冲区
- `fMemoryAllocator` -- Vulkan 内存分配器
- `fSemaphoresToWaitOn` / `fSemaphoresToSignal` -- GPU 同步信号量

### 2. GrVkCaps（文件：`GrVkCaps.h` / `GrVkCaps.cpp`）

**职责**：查询和存储 Vulkan 设备的能力信息、格式支持、驱动 workaround 等，继承自 `GrCaps`。

**关键方法**：
- `isFormatTexturable()` / `isFormatRenderable()` -- 格式支持查询
- `getRenderTargetSampleCount()` -- MSAA 采样数查询
- `canCopyImage()` / `canCopyAsBlit()` / `canCopyAsResolve()` -- 拷贝能力查询
- `preferredStencilFormat()` -- 首选模板格式
- `applyDriverCorrectnessWorkarounds()` -- 应用驱动兼容性修复
- `initFormatTable()` -- 初始化所有 Vulkan 格式的能力表

**关键特性标志**：
- `fSupportsSwapchain` -- 交换链支持
- `fSupportsAndroidHWBExternalMemory` -- Android 硬件缓冲区外部内存
- `fSupportsYcbcrConversion` -- YCbCr 色彩转换
- `fSupportsDRMFormatModifiers` -- DRM 格式修饰符
- `fMustSyncCommandBuffersWithQueue` -- 驱动级同步修复（Nvidia/Imagination）
- `fPreferPrimaryOverSecondaryCommandBuffers` -- 命令缓冲区策略选择

### 3. GrVkCommandBuffer（文件：`GrVkCommandBuffer.h` / `GrVkCommandBuffer.cpp`）

**职责**：封装 Vulkan 命令缓冲区，提供绘制命令、屏障、资源跟踪等功能。包含基类 `GrVkCommandBuffer` 及两个子类。

**类层次**：
- `GrVkCommandBuffer` -- 基类，实现通用命令（draw、bind、barrier）
- `GrVkPrimaryCommandBuffer` -- 主命令缓冲区，支持 render pass 管理、图像拷贝、提交
- `GrVkSecondaryCommandBuffer` -- 次级命令缓冲区，用于 render pass 内部录制

**关键方法（基类）**：
- `pipelineBarrier()` -- 管线屏障
- `bindPipeline()` / `bindDescriptorSets()` / `bindInputBuffer()` -- 绑定操作
- `draw()` / `drawIndexed()` / `drawIndirect()` / `drawIndexedIndirect()` -- 绘制命令
- `addResource()` / `addRecycledResource()` -- 资源生命周期跟踪

**关键方法（主命令缓冲区）**：
- `beginRenderPass()` / `endRenderPass()` -- 渲染通道管理
- `copyImage()` / `blitImage()` / `resolveImage()` -- 图像操作
- `copyBufferToImage()` / `copyImageToBuffer()` -- 缓冲区-图像传输
- `submitToQueue()` -- 提交到 Vulkan 队列
- `forceSync()` / `finished()` -- 同步控制

### 4. GrVkResourceProvider（文件：`GrVkResourceProvider.h` / `GrVkResourceProvider.cpp`）

**职责**：Vulkan 资源的集中管理和缓存中心，避免频繁创建/销毁 GPU 资源。

**关键方法**：
- `findCompatibleRenderPass()` -- 查找或创建兼容的渲染通道
- `findOrCreateCommandPool()` -- 查找或创建命令池
- `findOrCreateCompatibleSampler()` -- 查找或创建采样器
- `findOrCreateCompatiblePipelineState()` -- 查找或创建管线状态
- `getUniformDescriptorSet()` / `getSamplerDescriptorSet()` -- 获取描述符集
- `makePipeline()` -- 通过 VkPipelineCache 创建管线
- `storePipelineCacheData()` -- 持久化管线缓存数据

**缓存结构**：
- `fRenderPassArray` -- 兼容渲染通道集合（`CompatibleRenderPassSet`）
- `fSamplers` -- 采样器哈希表（`SkTDynamicHash`）
- `fYcbcrConversions` -- YCbCr 转换哈希表
- `fPipelineStateCache` -- 管线状态 LRU 缓存
- `fActiveCommandPools` / `fAvailableCommandPools` -- 命令池管理

### 5. GrVkPipeline（文件：`GrVkPipeline.h` / `GrVkPipeline.cpp`）

**职责**：封装 `VkPipeline` 对象，管理图形管线的创建，包括顶点输入、光栅化、混合、多重采样等状态。

**关键方法**：
- `Make()` -- 静态工厂方法（两个重载：详细参数版和 ProgramInfo 版）
- `SetDynamicScissorRectState()` -- 设置动态裁剪矩形
- `SetDynamicViewportState()` -- 设置动态视口
- `SetDynamicBlendConstantState()` -- 设置动态混合常量

### 6. GrVkRenderPass（文件：`GrVkRenderPass.h` / `GrVkRenderPass.cpp`）

**职责**：封装 `VkRenderPass`，管理附件描述、加载/存储操作、子通道依赖等。

**关键设计**：
- `AttachmentsDescriptor` -- 描述颜色、解析（Resolve）、模板附件的格式和采样数
- `AttachmentFlags` -- 标识附件类型（颜色/模板/解析/外部）
- `SelfDependencyFlags` -- 自依赖标志（用于输入附件和非相干高级混合）
- `LoadFromResolve` -- 从解析附件加载数据到 MSAA 附件的标志
- `isCompatible()` -- 渲染通道兼容性检查（Vulkan 规范要求）

### 7. GrVkImage（文件：`GrVkImage.h` / `GrVkImage.cpp`）

**职责**：封装 `VkImage` 及其关联的内存分配和 `VkImageView`，继承自 `GrAttachment`。

**关键方法**：
- `MakeStencil()` / `MakeMSAA()` / `MakeTexture()` / `MakeWrapped()` -- 静态工厂方法
- `setImageLayout()` / `setImageLayoutAndQueueIndex()` -- 图像布局转换（含屏障插入）
- `prepareForPresent()` / `prepareForExternal()` -- 队列族转移
- `inputDescSetForBlending()` / `inputDescSetForMSAALoad()` -- 输入附件描述符集

**内部资源类**：
- `Resource` -- 拥有 VkImage 和 VulkanAlloc 的引用计数资源
- `BorrowedResource` -- 用于包装外部纹理，不释放底层 VkImage

### 8. GrVkPipelineState（文件：`GrVkPipelineState.h` / `GrVkPipelineState.cpp`）

**职责**：聚合 `GrVkPipeline`、Uniform 数据、描述符集和采样器，提供完整的绘制状态绑定。

**关键方法**：
- `setAndBindUniforms()` -- 设置并绑定 Uniform 数据到命令缓冲区
- `setAndBindTextures()` -- 设置并绑定纹理和采样器
- `setAndBindInputAttachment()` -- 设置并绑定输入附件
- `bindPipeline()` -- 绑定图形管线

### 9. GrVkOpsRenderPass（文件：`GrVkOpsRenderPass.h` / `GrVkOpsRenderPass.cpp`）

**职责**：实现 `GrOpsRenderPass` 接口，负责将 Ganesh 的绘制操作转换为 Vulkan 命令录制。

**关键方法**：
- `set()` / `reset()` -- 配置和重置渲染通道
- `onBindPipeline()` -- 绑定管线（含动态状态设置）
- `onBindTextures()` -- 绑定纹理
- `onDrawInstanced()` / `onDrawIndexedInstanced()` -- 实例化绘制
- `onDrawIndirect()` / `onDrawIndexedIndirect()` -- 间接绘制
- `loadResolveIntoMSAA()` -- MSAA 解析加载

### 10. GrVkDescriptorSetManager（文件：`GrVkDescriptorSetManager.h` / `GrVkDescriptorSetManager.cpp`）

**职责**：管理特定 `VkDescriptorSetLayout` 的描述符集分配与回收。

**工厂方法**：
- `CreateUniformManager()` -- 创建 Uniform 缓冲区描述符管理器
- `CreateSamplerManager()` -- 创建采样器描述符管理器
- `CreateZeroSamplerManager()` -- 创建零采样器描述符管理器（管线布局占位）
- `CreateInputManager()` -- 创建输入附件描述符管理器

**内部结构**：
- `DescriptorPoolManager` -- 管理 `VkDescriptorPool` 的自动扩容（16 -> 1024）
- `fFreeSets` -- 可回收的描述符集列表

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块 | 路径 | 说明 |
|------|------|------|
| Ganesh 通用层 | `src/gpu/ganesh/` | 基类：`GrGpu`、`GrCaps`、`GrTexture`、`GrRenderTarget`、`GrOpsRenderPass` 等 |
| GLSL 编译器 | `src/gpu/ganesh/glsl/` | `GrGLSLProgramBuilder`、`GrGLSLUniformHandler`、`GrGLSLShaderBuilder` |
| GPU 通用层 | `src/gpu/` | `Swizzle`、`RefCntedCallback`、`GpuRefCnt` |
| Vulkan 公共头 | `include/gpu/vk/` | `VulkanTypes.h`、`VulkanMutableTextureState.h` |
| Ganesh Vulkan 公共头 | `include/gpu/ganesh/vk/` | `GrVkBackendSurface.h`、`GrVkTypes.h` |
| SkSL | `src/sksl/` | 着色器语言编译（GLSL -> SPIR-V） |
| 核心库 | `include/core/`、`src/core/` | `SkRefCnt`、`SkChecksum`、`SkLRUCache`、`SkTDynamicHash` |

### 下游依赖（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| `GrDirectContext` | 通过 `GrVkGpu::Make()` 创建 Vulkan GPU 后端 |
| Ganesh 绘制调度 | `GrDrawingManager`、`GrOpFlushState` 使用 `GrVkOpsRenderPass` 录制命令 |
| 外部应用 | 通过 `SkSurfaces`、`SkCanvas` 间接使用 Vulkan 渲染 |

### 外部依赖

| 依赖 | 说明 |
|------|------|
| Vulkan SDK | `vulkan/vulkan.h` -- Vulkan API 头文件 |
| VulkanMemoryAllocator | `skgpu::VulkanMemoryAllocator` -- GPU 内存分配 |
| VulkanInterface | `skgpu::VulkanInterface` -- Vulkan 函数指针表 |
| VulkanExtensions | `skgpu::VulkanExtensions` -- 扩展查询 |

## 设计模式分析

### 1. 工厂方法模式（Factory Method）

几乎所有 Vulkan 资源类都使用静态工厂方法 `Make()` 或 `Create()` 进行创建，而非直接暴露构造函数。这样可以在创建时执行验证、选择不同的内部实现路径，并在失败时返回 `nullptr` 而非抛出异常。

```cpp
// GrVkImage 的多种工厂方法
static sk_sp<GrVkImage> MakeStencil(GrVkGpu*, SkISize, int sampleCnt, VkFormat);
static sk_sp<GrVkImage> MakeMSAA(GrVkGpu*, SkISize, int numSamples, VkFormat, ...);
static sk_sp<GrVkImage> MakeTexture(GrVkGpu*, SkISize, VkFormat, uint32_t mipLevels, ...);
static sk_sp<GrVkImage> MakeWrapped(GrVkGpu*, SkISize, const GrVkImageInfo&, ...);
```

### 2. 模板方法模式（Template Method）

通过继承 Ganesh 基类并重写 `on*` 前缀的虚函数，Vulkan 后端在不改变通用流程的前提下注入特定行为。例如 `GrVkGpu` 继承 `GrGpu` 并重写 `onCreateTexture()`、`onReadPixels()` 等。

### 3. 对象池/缓存模式（Object Pool / Cache）

`GrVkResourceProvider` 是整个资源缓存体系的核心，采用多种策略：
- **LRU 缓存** -- `PipelineStateCache` 使用 `SkLRUCache` 缓存编译好的管线状态
- **哈希表复用** -- `fSamplers` 和 `fYcbcrConversions` 使用 `SkTDynamicHash` 按键查找
- **兼容集分组** -- `CompatibleRenderPassSet` 将兼容的渲染通道分组管理
- **命令池回收** -- `fActiveCommandPools` / `fAvailableCommandPools` 双队列管理

### 4. 引用计数与资源追踪（Reference Counting & Tracking）

```
GrManagedResource <-- GrVkManagedResource <-- GrVkPipeline, GrVkRenderPass, GrVkSampler, ...
GrRecycledResource <-- GrVkRecycledResource
GrTextureResource  <-- GrVkImage::Resource
```

命令缓冲区通过 `addResource()` / `addRecycledResource()` 持有资源引用，确保资源在 GPU 执行完成前不被释放。`GrVkCommandBuffer` 内部维护 `fTrackedResources` 和 `fTrackedRecycledResources` 数组。

### 5. 策略模式（Strategy）

表面拷贝操作根据源/目标的格式、采样数、Tiling 模式等条件，在三种策略间切换：
- `copySurfaceAsCopyImage()` -- 格式完全匹配时使用 `vkCmdCopyImage`
- `copySurfaceAsBlit()` -- 需要格式转换或缩放时使用 `vkCmdBlitImage`
- `copySurfaceAsResolve()` -- MSAA 解析时使用 `vkCmdResolveImage`

### 6. 描述符集绑定约定

Vulkan 描述符集按固定顺序绑定，避免高频重绑低索引集合：
```
Set 0: Uniform Buffer  -- 每管线绑定一次
Set 1: Sampler          -- 每绘制调用可能重绑（动态纹理状态）
Set 2: Input Attachment -- 采样器重绑后需要重绑
```

## 数据流

### 绘制命令执行流程

```
应用层 SkCanvas::drawRect()
       |
       v
GrDrawingManager -- 收集 GrOp 操作
       |
       v
GrOpFlushState -- 刷新操作到渲染通道
       |
       v
GrVkOpsRenderPass::set()
  |-- 查找/创建 GrVkRenderPass (通过 GrVkResourceProvider)
  |-- 查找/创建 GrVkFramebuffer
  |-- beginRenderPass() --> 开始命令录制
       |
       v
GrVkOpsRenderPass::onBindPipeline()
  |-- GrVkResourceProvider::findOrCreateCompatiblePipelineState()
  |   |-- PipelineStateCache::findOrCreatePipelineState()
  |   |   |-- GrVkPipelineStateBuilder::CreatePipelineState()
  |   |   |   |-- SkSL 编译 GLSL -> SPIR-V
  |   |   |   |-- GrVkPipeline::Make()  --> vkCreateGraphicsPipelines()
  |   |   |   +-- 返回 GrVkPipelineState
  |-- GrVkPipelineState::setAndBindUniforms()
  |-- GrVkPipelineState::bindPipeline()
       |
       v
GrVkOpsRenderPass::onBindTextures()
  |-- GrVkPipelineState::setAndBindTextures()
  |   |-- 获取 GrVkSampler (从 GrVkResourceProvider 缓存)
  |   |-- 更新 VkDescriptorSet
  |   +-- vkCmdBindDescriptorSets()
       |
       v
GrVkOpsRenderPass::onDrawInstanced()
  |-- GrVkCommandBuffer::draw() --> vkCmdDraw()
       |
       v
GrVkOpsRenderPass::submit()
  |-- endRenderPass() --> vkCmdEndRenderPass()
       |
       v
GrVkGpu::submitCommandBuffer()
  |-- GrVkPrimaryCommandBuffer::end()
  |-- GrVkPrimaryCommandBuffer::submitToQueue()
  |   |-- vkQueueSubmit() (附带信号量等待和触发)
  |-- 创建新的命令缓冲区准备下一帧
```

### 纹理数据上传流程

```
GrVkGpu::onWritePixels()
       |
       v
判断上传策略:
  |-- 线性布局(Linear Tiling)?
  |   +-- uploadTexDataLinear() --> 直接映射内存写入
  |
  +-- 最优布局(Optimal Tiling)?
      +-- uploadTexDataOptimal()
          |-- 分配 Staging Buffer (通过 GrStagingBufferManager)
          |-- 将像素数据拷贝到 Staging Buffer
          |-- GrVkImage::setImageLayout(TRANSFER_DST_OPTIMAL)  --> 插入屏障
          |-- GrVkPrimaryCommandBuffer::copyBufferToImage()
          |   +-- vkCmdCopyBufferToImage()
          +-- 后续使用时自动转换到 SHADER_READ_ONLY_OPTIMAL
```

### 图像布局转换流程

```
GrVkImage::setImageLayoutAndQueueIndex()
       |
       v
计算源访问掩码: LayoutToSrcAccessMask(oldLayout)
计算源管线阶段: LayoutToPipelineSrcStageFlags(oldLayout)
       |
       v
构建 VkImageMemoryBarrier:
  - srcAccessMask / dstAccessMask
  - oldLayout / newLayout
  - srcQueueFamilyIndex / dstQueueFamilyIndex
       |
       v
GrVkGpu::addImageMemoryBarrier()
  |-- GrVkCommandBuffer::pipelineBarrier()
  |   |-- 批量收集屏障 (fImageBarriers)
  +-- submitPipelineBarriers() (在下一个命令前提交)
      +-- vkCmdPipelineBarrier()
```

## 平台特定说明

### Android

- **AHardwareBuffer 支持**（`AHardwareBufferVk.cpp`）：通过 `VK_ANDROID_external_memory_android_hardware_buffer` 扩展，将 Android 的 AHardwareBuffer 导入为 Vulkan 图像。支持 YCbCr 格式的外部图像采样。
- **YCbCr 色彩转换**（`GrVkSamplerYcbcrConversion`）：支持 `VK_KHR_sampler_ycbcr_conversion` 扩展，用于视频帧和相机预览等 YUV 格式图像的自动色彩空间转换。
- **受保护内容**（Protected Content）：通过 `GrProtected` 标志支持 DRM 受保护内存和命令缓冲区，用于安全视频播放。

### Windows

- **Nvidia 驱动 workaround**：`fMustSyncCommandBuffersWithQueue = true` -- Windows Nvidia 驱动的 `vkQueueWaitIdle` 可能在命令缓冲区 fence 信号之前返回，需要额外调用 `vkWaitForFences` 确保同步正确。
- **Imagination GPU 驱动**同样存在上述问题。

### Intel GPU 特殊处理

`GrVkCaps` 中包含 Intel GPU 代次识别逻辑（`IntelGPUType`），支持从第 9 代 SkyLake 到最新的 PantherLake/Battlemage 架构，用于针对不同代次应用特定的 workaround：
- `fMustLoadFullImageWithDiscardableMSAA` -- 某些 Intel 驱动在使用 Discardable MSAA 时需要加载完整图像
- `fMustInvalidatePrimaryCmdBufferStateAfterClearAttachments` -- 部分 Intel 驱动在 `vkCmdClearAttachments` 后需要重新设置管线状态

### 通用 Vulkan 扩展支持

| 扩展 | 对应能力标志 |
|------|-------------|
| `VK_KHR_swapchain` | `fSupportsSwapchain` |
| `VK_ANDROID_external_memory_android_hardware_buffer` | `fSupportsAndroidHWBExternalMemory` |
| `VK_KHR_sampler_ycbcr_conversion` | `fSupportsYcbcrConversion` |
| `VK_EXT_image_drm_format_modifier` | `fSupportsDRMFormatModifiers` |
| `VK_EXT_device_fault` | `fSupportsDeviceFaultInfo` |
| `VK_EXT_frame_boundary` | `fSupportsFrameBoundary` |
| `VK_EXT_pipeline_creation_cache_control` | `fSupportsPipelineCreationCacheControl` |

### 内存管理策略

- **专用图像内存**：`fShouldAlwaysUseDedicatedImageMemory` -- 在某些设备上始终为 VkImage 使用专用内存分配（`VK_KHR_dedicated_allocation`）
- **持久映射**：`fShouldPersistentlyMapCpuToGpuBuffers` -- CPU-GPU 缓冲区（顶点、Uniform 等）默认持久映射，但在使用 DEVICE_LOCAL + HOST_VISIBLE 专用内存的离散 GPU 上可能关闭
- **GPU 专用缓冲区**：`fGpuOnlyBuffersMorePerformant` -- 某些设备上纯 GPU 缓冲区读取性能更优，值得额外拷贝开销
- **Memoryless 附件**：`fSupportsMemorylessAttachments` -- 支持无内存后备的临时附件（仅 tile-based GPU）

## 相关文档与参考

### Skia 内部文档
- `src/gpu/ganesh/GrGpu.h` -- GPU 后端基类定义
- `src/gpu/ganesh/GrCaps.h` -- 能力查询基类
- `src/gpu/ganesh/GrOpsRenderPass.h` -- 渲染通道操作基类
- `include/gpu/ganesh/vk/GrVkTypes.h` -- Vulkan 类型公共定义
- `include/gpu/vk/VulkanTypes.h` -- Vulkan 通用类型

### Vulkan 规范参考
- [Vulkan 1.3 规范](https://registry.khronos.org/vulkan/specs/1.3/html/) -- 官方 API 参考
- [VkRenderPass 兼容性](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#renderpass-compatibility) -- 渲染通道兼容性规则
- [VkPipeline 创建](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#pipelines-graphics) -- 图形管线创建
- [VkDescriptorSet 管理](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#descriptorsets) -- 描述符集规范
- [SPIR-V 规范](https://registry.khronos.org/SPIR-V/) -- 着色器中间表示

### 相关的 Skia 模块
- `src/gpu/ganesh/gl/` -- OpenGL 后端实现（同层级对比参考）
- `src/gpu/ganesh/d3d/` -- Direct3D 12 后端实现
- `src/gpu/ganesh/mtl/` -- Metal 后端实现
- `src/gpu/graphite/vk/` -- Graphite 新架构的 Vulkan 后端（下一代实现）
- `src/gpu/vk/` -- Vulkan 共享工具层（被 Ganesh 和 Graphite 共用）
