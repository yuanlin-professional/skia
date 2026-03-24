# vk - Skia Graphite Vulkan 后端实现

## 概述

`src/gpu/graphite/vk` 目录是 Skia 图形库中 Graphite 渲染引擎的 Vulkan 后端实现。Graphite 是 Skia 的下一代 GPU 渲染架构，旨在替代传统的 Ganesh 后端，提供更现代化、更高效的 GPU 渲染能力。此目录包含了 Graphite 与 Vulkan 图形 API 之间的完整桥接层，将 Graphite 的抽象渲染概念映射到具体的 Vulkan API 调用。

Vulkan 后端的核心职责是管理 Vulkan 设备资源的生命周期、构建和提交 GPU 命令缓冲区、创建和缓存图形管线、处理内存分配和同步。该实现充分利用了 Vulkan 的显式控制特性，包括精细的内存管理、管线缓存持久化、描述符集池化以及多重采样解析（MSAA resolve）等高级功能。所有类都位于 `skgpu::graphite` 命名空间中。

该后端支持广泛的 Vulkan 特性，包括 YCbCr 色彩空间转换（用于视频纹理处理）、输入附件（Input Attachment）读取优化、图形管线库（Graphics Pipeline Library）、扩展动态状态（Extended Dynamic State）、主机图像拷贝（Host Image Copy）以及多重采样渲染到单采样（Multisampled Render to Single Sampled）等扩展。同时，代码中包含了针对不同 GPU 供应商驱动程序问题的兼容性修正。

从线程安全角度来看，`VulkanSharedContext` 作为共享上下文可被多个线程安全访问，而 `VulkanResourceProvider` 则专用于单个 Recorder 线程。设备丢失（Device Lost）检测通过互斥锁保护，确保在多线程环境下正确传播错误状态。管线缓存数据的持久化通过 `PersistentPipelineStorage` 接口实现，可以跨会话保存编译好的管线数据以加速后续启动。

## 架构图

```
+------------------------------------------------------------------+
|                    Graphite 上层抽象层                              |
|  (Context, Recorder, DrawPass, RenderPassDesc, GraphicsPipelineDesc)|
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                VulkanSharedContext                                 |
|  (VkDevice, VkPhysicalDevice, VulkanInterface,                   |
|   VulkanMemoryAllocator, VkPipelineCache)                        |
|                                                                   |
|   +---------------------------+  +----------------------------+   |
|   | VulkanCaps                |  | VulkanThreadSafeResource-  |   |
|   | (格式表, 设备能力,         |  |  Provider                  |   |
|   |  驱动兼容修正)             |  | (共享 RenderPass 缓存)     |   |
|   +---------------------------+  +----------------------------+   |
+------------------------------------------------------------------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
+----------------------------+  +----------------------------+
| VulkanResourceProvider     |  | VulkanQueueManager         |
| (每 Recorder 实例一个)      |  | (VkQueue, 命令提交)        |
|                            |  +----------------------------+
| - 纹理/缓冲区创建           |            |
| - 采样器/描述符集管理        |            v
| - RenderPass/Framebuffer   |  +----------------------------+
| - LoadMSAA 管线缓存        |  | VulkanCommandBuffer        |
| - UniformBuffer 描述符缓存  |  | (VkCommandBuffer,          |
+----------------------------+  |  VkCommandPool)             |
              |                 |                            |
    +---------+---------+       | - 渲染通道管理              |
    |         |         |       | - 管线绑定                  |
    v         v         v       | - 描述符集绑定              |
+------+ +------+ +--------+   | - 绘制/拷贝命令             |
|Vulkan| |Vulkan| |Vulkan  |   | - 内存屏障/信号量           |
|Texture|Buffer| |Sampler |   +----------------------------+
+------+ +------+ +--------+
    |                  |
    v                  v
+------+         +-------------+
|Vulkan|         |VulkanYcbcr  |
|Image |         |Conversion   |
|View  |         +-------------+
+------+

+----------------------------+      +----------------------------+
| VulkanGraphicsPipeline     |      | VulkanRenderPass           |
| (VkPipeline,               |      | (VkRenderPass,             |
|  VkPipelineLayout)         |      |  子通道配置,               |
| - 着色器模块管理            |      |  加载/存储操作)            |
| - 顶点输入配置              |      +----------------------------+
| - 动态状态管理              |               |
| - 不可变采样器引用          |               v
+----------------------------+      +----------------------------+
         |                          | VulkanFramebuffer          |
         v                          | (VkFramebuffer,            |
+----------------------------+      |  附件纹理引用)             |
| VulkanProgramInfo          |      +----------------------------+
| (VkShaderModule VS/FS,     |
|  VkPipelineLayout)         |
+----------------------------+

+----------------------------+      +----------------------------+
| VulkanDescriptorPool       |      | VulkanDescriptorSet        |
| (VkDescriptorPool,         | ---> | (VkDescriptorSet,          |
|  VkDescriptorSetLayout)    |      |  引用计数关联池)           |
+----------------------------+      +----------------------------+

+----------------------------+
| VulkanSpirvTransforms      |
| (SPIR-V 字节码变换,        |
|  多采样输入加载调整)        |
+----------------------------+
```

## 目录结构

```
src/gpu/graphite/vk/
|-- BUILD.bazel                      # Bazel 构建配置
|-- VulkanBackendSemaphore.cpp       # Vulkan 后端信号量实现
|-- VulkanBackendTexture.cpp         # Vulkan 后端纹理数据封装
|-- VulkanBuffer.cpp                 # Vulkan GPU 缓冲区实现
|-- VulkanBuffer.h                   # VulkanBuffer 头文件
|-- VulkanCaps.cpp                   # Vulkan 设备能力查询与格式表初始化
|-- VulkanCaps.h                     # VulkanCaps 头文件 (格式支持, 扩展检测, 限制值)
|-- VulkanCommandBuffer.cpp          # 命令缓冲区录制与提交
|-- VulkanCommandBuffer.h            # VulkanCommandBuffer 头文件
|-- VulkanDescriptorPool.cpp         # 描述符池创建与管理
|-- VulkanDescriptorPool.h           # VulkanDescriptorPool 头文件
|-- VulkanDescriptorSet.cpp          # 描述符集分配与绑定
|-- VulkanDescriptorSet.h            # VulkanDescriptorSet 头文件
|-- VulkanFramebuffer.cpp            # 帧缓冲区对象封装
|-- VulkanFramebuffer.h              # VulkanFramebuffer 头文件
|-- VulkanGraphicsPipeline.cpp       # 图形管线创建与状态管理
|-- VulkanGraphicsPipeline.h         # VulkanGraphicsPipeline 头文件
|-- VulkanGraphiteUtils.cpp          # Vulkan 工具函数与宏定义
|-- VulkanGraphiteUtils.h            # 工具函数头文件 (格式转换, 着色器模块创建)
|-- VulkanImageView.cpp              # 图像视图创建
|-- VulkanImageView.h                # VulkanImageView 头文件
|-- VulkanQueueManager.cpp           # 队列管理与命令提交
|-- VulkanQueueManager.h             # VulkanQueueManager 头文件
|-- VulkanRenderPass.cpp             # 渲染通道创建与键值计算
|-- VulkanRenderPass.h               # VulkanRenderPass 头文件
|-- VulkanResourceProvider.cpp       # 资源提供者 (工厂模式, 缓存管理)
|-- VulkanResourceProvider.h         # VulkanResourceProvider 头文件
|-- VulkanSampler.cpp                # 纹理采样器创建
|-- VulkanSampler.h                  # VulkanSampler 头文件
|-- VulkanSharedContext.cpp          # 共享上下文初始化与管线缓存持久化
|-- VulkanSharedContext.h            # VulkanSharedContext 头文件
|-- VulkanSpirvTransforms.cpp        # SPIR-V 着色器字节码变换
|-- VulkanSpirvTransforms.h          # SPIRVTransformOptions 与变换函数
|-- VulkanTexture.cpp                # 纹理创建、布局转换与主机上传
|-- VulkanTexture.h                  # VulkanTexture 头文件
|-- VulkanTextureInfo.cpp            # 纹理信息序列化与兼容性比较
|-- VulkanYcbcrConversion.cpp        # YCbCr 采样器转换对象
|-- VulkanYcbcrConversion.h          # VulkanYcbcrConversion 头文件
|-- precompile/                      # 预编译着色器子目录
    |-- BUILD.bazel
    |-- VulkanPrecompileShader.cpp
```

## 关键类与函数

### VulkanSharedContext
**文件**: `VulkanSharedContext.h`, `VulkanSharedContext.cpp`

`VulkanSharedContext` 是 Vulkan 后端的核心共享上下文，继承自 `SharedContext` 基类。它持有 Vulkan 设备的全局状态，可以被多个 Recorder 共享访问。

```cpp
class VulkanSharedContext final : public SharedContext {
public:
    static sk_sp<SharedContext> Make(const VulkanBackendContext&, const ContextOptions&);

    const skgpu::VulkanInterface* interface() const;
    skgpu::VulkanMemoryAllocator* memoryAllocator() const;
    VkPhysicalDevice physDevice() const;
    VkDevice device() const;
    VkPipelineCache getPipelineCache() const;
    bool checkVkResult(VkResult result) const;
    bool isDeviceLost() const override;
    void syncPipelineData(PersistentPipelineStorage*, size_t maxSize) override;
};
```

**核心职责**:
- 管理 `VkDevice`、`VkPhysicalDevice`、`VulkanInterface` 和 `VulkanMemoryAllocator`
- 创建并维护 `VkPipelineCache`，支持从 `PersistentPipelineStorage` 加载和保存缓存数据
- 检测和传播设备丢失（`VK_ERROR_DEVICE_LOST`）状态，并通过 `fDeviceLostProc` 回调通知客户端
- 通过 `VulkanThreadSafeResourceProvider` 提供线程安全的 RenderPass 查找/创建

### VulkanCaps
**文件**: `VulkanCaps.h`, `VulkanCaps.cpp`

设备能力检测与格式表管理类，继承自 `Caps` 基类。在构造时查询物理设备的所有属性和扩展支持情况。

```cpp
class VulkanCaps final : public Caps {
public:
    VulkanCaps(const ContextOptions&, const skgpu::VulkanInterface*,
               VkPhysicalDevice, uint32_t physicalDeviceVersion,
               const VkPhysicalDeviceFeatures2*, const skgpu::VulkanExtensions*, Protected);

    bool supportsYcbcrConversion() const;
    bool gpuOnlyBuffersMorePerformant() const;
    bool shouldPersistentlyMapCpuToGpuBuffers() const;
    bool supportsPipelineCreationCacheControl() const;
    uint32_t maxVertexAttributes() const;
    uint64_t maxUniformBufferRange() const;
};
```

**关键功能**:
- 内部维护 `FormatInfo` 格式表（`kNumVkFormats = 24` 种格式），记录每种 `VkFormat` 的纹理能力、采样计数和颜色类型映射
- 维护 `DepthStencilFormatInfo` 深度/模板格式表（`kNumDepthStencilVkFormats = 5` 种格式）
- 通过 `EnabledFeatures` 结构追踪启用的 Vulkan 特性（双源混合、YCbCr 转换、扩展动态状态、图形管线库等）
- `applyDriverCorrectnessWorkarounds()` 对已知驱动问题进行修正
- `makeGraphicsPipelineKey()` / `extractGraphicsDescs()` 实现管线键的序列化与反序列化

### VulkanCommandBuffer
**文件**: `VulkanCommandBuffer.h`, `VulkanCommandBuffer.cpp`

命令缓冲区类，继承自 `CommandBuffer` 基类，负责录制所有 GPU 命令并提交到队列。

```cpp
class VulkanCommandBuffer final : public CommandBuffer {
public:
    static std::unique_ptr<VulkanCommandBuffer> Make(const VulkanSharedContext*,
                                                     VulkanResourceProvider*, Protected);
    bool submit(VkQueue, const SubmitInfo&);
    bool isFinished();
    void waitUntilFinished();
    void addBufferMemoryBarrier(...);
    void addImageMemoryBarrier(...);
};
```

**核心机制**:
- 管理 `VkCommandPool` 和 `VkCommandBuffer` 的生命周期
- 支持渲染通道（`beginRenderPass` / `endRenderPass`）、绘制命令、拷贝操作和计算通道
- 通过 `VkFence` (`fSubmitFence`) 实现 CPU/GPU 同步
- 批量提交内存屏障（`fBufferBarriers`、`fImageBarriers`）以优化管线阻塞
- 使用 `VkSemaphore` 进行信号量等待和发信号
- 延迟绑定描述符集和 Uniform 缓冲区，通过脏标志（`fBindUniformBuffers`、`fBindTextureSamplers`）追踪变更
- 支持 GPU 统计查询（时间戳和遮挡查询）

### VulkanGraphicsPipeline
**文件**: `VulkanGraphicsPipeline.h`, `VulkanGraphicsPipeline.cpp`

图形管线类，继承自 `GraphicsPipeline` 基类，封装完整的 `VkPipeline` 和 `VkPipelineLayout`。

```cpp
class VulkanGraphicsPipeline final : public GraphicsPipeline {
public:
    // 描述符集索引常量
    static constexpr unsigned int kDstAsInputDescSetIndex = 0;
    static constexpr unsigned int kUniformBufferDescSetIndex = 1;
    static constexpr unsigned int kTextureBindDescSetIndex = 2;
    static constexpr unsigned int kLoadMsaaFromResolveInputDescSetIndex = 3;
    static constexpr unsigned int kMaxNumDescSets = 4;

    static sk_sp<VulkanGraphicsPipeline> Make(VulkanSharedContext*, ...);
    static sk_sp<VulkanGraphicsPipeline> MakeLoadMSAAPipeline(...);

    void updateDynamicState(const VulkanSharedContext*, VkCommandBuffer,
                            const VulkanGraphicsPipeline* previous) const;
};
```

**设计要点**:
- 采用固定的描述符集布局：集合 0 为目标纹理输入附件，集合 1 为 Uniform 缓冲区，集合 2 为纹理/采样器绑定，集合 3 为 MSAA 加载输入附件
- `VulkanProgramInfo` 辅助类用于管理着色器模块（VS/FS）和管线布局的生命周期
- 支持动态状态更新（`updateDynamicState`），仅设置与前一管线的差异部分
- 缓存顶点属性描述信息，避免重复计算
- 支持不可变采样器（`fImmutableSamplers`）用于 YCbCr 纹理

### VulkanResourceProvider
**文件**: `VulkanResourceProvider.h`, `VulkanResourceProvider.cpp`

资源提供者类，继承自 `ResourceProvider`，负责创建和缓存各种 Vulkan 资源。每个 Recorder 拥有一个独立的实例。

```cpp
class VulkanResourceProvider final : public ResourceProvider {
public:
    sk_sp<VulkanYcbcrConversion> findOrCreateCompatibleYcbcrConversion(...) const;
    sk_sp<VulkanDescriptorSet> findOrCreateDescriptorSet(SkSpan<DescriptorData>);
    sk_sp<VulkanDescriptorSet> findOrCreateUniformBuffersDescriptorSet(...);
    sk_sp<VulkanGraphicsPipeline> findOrCreateLoadMSAAPipeline(const RenderPassDesc&);
    sk_sp<VulkanRenderPass> findOrCreateRenderPass(const RenderPassDesc&, bool compatibleOnly);
    sk_sp<VulkanFramebuffer> findOrCreateFramebuffer(...);
};
```

**关键缓存策略**:
- `fLoadMSAAPipelines`: 按 RenderPass 哈希缓存 LoadMSAA 管线，共享着色器模块和管线布局
- `fUniformBufferDescSetCache`: 使用 LRU 缓存减少 Uniform 缓冲区描述符集的重复分配
- `fMockPipelineLayout`: 兼容的模拟管线布局，用于在绑定真实管线之前执行 Push Constant 更新和输入附件绑定

### VulkanTexture
**文件**: `VulkanTexture.h`, `VulkanTexture.cpp`

纹理类，继承自 `Texture`，封装 `VkImage` 及其关联的内存分配、图像视图和缓存。

```cpp
class VulkanTexture : public Texture {
public:
    static sk_sp<Texture> Make(const VulkanSharedContext*, SkISize, const TextureInfo&,
                               sk_sp<VulkanYcbcrConversion>, std::string_view label);
    static sk_sp<Texture> MakeWrapped(...);

    void setImageLayout(VulkanCommandBuffer*, VkImageLayout, VkAccessFlags,
                        VkPipelineStageFlags) const;
    const VulkanImageView* getImageView(VulkanImageView::Usage) const;
    bool canUploadOnHost(const UploadSource&) const override;
    bool uploadDataOnHost(const UploadSource&, const SkIRect&) override;
};
```

**特色功能**:
- 支持主机端图像上传（Host Image Copy），当 `VK_EXT_host_image_copy` 可用且格式高效时直接通过 CPU 写入
- 缓存单纹理描述符集（`fCachedSingleTextureDescSets`）和帧缓冲区（`fCachedFramebuffers`），避免重复创建
- 图像布局通过 `MutableTextureState` 跟踪，支持队列家族所有权转移

### VulkanBuffer
**文件**: `VulkanBuffer.h`, `VulkanBuffer.cpp`

缓冲区类，继承自 `Buffer`，封装 `VkBuffer` 及其内存分配。

```cpp
class VulkanBuffer final : public Buffer {
public:
    static sk_sp<Buffer> Make(const VulkanSharedContext*, size_t, BufferType,
                              AccessPattern, std::string_view label);
    VkBuffer vkBuffer() const;
    void setBufferAccess(VulkanCommandBuffer*, VkAccessFlags, VkPipelineStageFlags) const;
};
```

- 通过 `VulkanMemoryAllocator` 管理内存分配
- 支持持久映射（Persistent Mapping）用于 CPU 到 GPU 的数据传输
- 区分 CPU 读取和 CPU 写入的映射模式

### VulkanRenderPass
**文件**: `VulkanRenderPass.h`, `VulkanRenderPass.cpp`

渲染通道封装类，继承自 `Resource`。

```cpp
class VulkanRenderPass : public Resource {
public:
    static uint32_t GetRenderPassKey(const RenderPassDesc&, bool compatibleForPipelineKey);
    static void ExtractRenderPassDesc(uint32_t key, Swizzle, DstReadStrategy, RenderPassDesc*);
    static sk_sp<VulkanRenderPass> Make(const VulkanSharedContext*, const RenderPassDesc&);
};
```

- 渲染通道的关键信息被压缩到一个 `uint32_t` 键中，实现高效的缓存查找
- 区分"兼容"（用于管线创建）和"完整"（用于命令缓冲区 `beginRenderPass`）两种模式
- 存储渲染粒度（`fGranularity`）信息

### VulkanDescriptorPool / VulkanDescriptorSet
**文件**: `VulkanDescriptorPool.h`, `VulkanDescriptorSet.h`

描述符管理的两层架构:

- `VulkanDescriptorPool`：管理 `VkDescriptorPool` 和 `VkDescriptorSetLayout`，支持预分配固定数量的描述符集
- `VulkanDescriptorSet`：封装 `VkDescriptorSet`，通过引用计数关联到其所属的 `VulkanDescriptorPool`。当所有描述符集被释放后，池自动销毁

### VulkanSampler
**文件**: `VulkanSampler.h`, `VulkanSampler.cpp`

采样器类，封装 `VkSampler`，支持可选的 YCbCr 转换对象关联。

### VulkanImageView
**文件**: `VulkanImageView.h`, `VulkanImageView.cpp`

图像视图封装，生命周期由其关联的 `VulkanTexture` 管理（非 `Resource` 派生），区分 `kShaderInput` 和 `kAttachment` 两种用途。

### VulkanYcbcrConversion
**文件**: `VulkanYcbcrConversion.h`, `VulkanYcbcrConversion.cpp`

YCbCr 采样器转换资源，用于处理视频纹理（如 Android `AHardwareBuffer`）。提供 `ImmutableSamplerInfo` 与 `VulkanYcbcrConversionInfo` 之间的双向转换。

### VulkanSpirvTransforms
**文件**: `VulkanSpirvTransforms.h`, `VulkanSpirvTransforms.cpp`

SPIR-V 字节码变换工具，当前支持多采样输入附件加载调整变换。设计为可扩展的单遍变换系统。

```cpp
struct SPIRVTransformOptions {
    bool fMultisampleInputLoad = false;
};
SkSL::NativeShader TransformSPIRV(const SkSL::NativeShader& spirv,
                                  const SPIRVTransformOptions& options);
```

### 工具函数与宏 (VulkanGraphiteUtils)
**文件**: `VulkanGraphiteUtils.h`, `VulkanGraphiteUtils.cpp`

提供一系列重要的工具函数和调试宏:

```cpp
// Vulkan 调用宏
VULKAN_CALL(IFACE, X)                    // 不检查结果
VULKAN_CALL_RESULT(SHARED_CONTEXT, RESULT, X)  // 检查结果并处理设备丢失
VULKAN_CALL_ERRCHECK(SHARED_CONTEXT, X)  // 检查结果的简化版

// 工具函数
VkShaderModule CreateVulkanShaderModule(...);
VkFormat TextureFormatToVkFormat(TextureFormat);
TextureFormat VkFormatToTextureFormat(VkFormat);
bool RenderPassDescWillLoadMSAAFromResolve(const RenderPassDesc&);
```

## 依赖关系

### 内部依赖（Graphite 核心层）

| 依赖目标 | 说明 |
|---------|------|
| `src/gpu/graphite/SharedContext` | 共享上下文基类 |
| `src/gpu/graphite/ResourceProvider` | 资源提供者基类 |
| `src/gpu/graphite/CommandBuffer` | 命令缓冲区基类 |
| `src/gpu/graphite/GraphicsPipeline` | 图形管线基类 |
| `src/gpu/graphite/Texture` / `Buffer` / `Sampler` | 资源基类 |
| `src/gpu/graphite/Resource` | GPU 资源基类（引用计数） |
| `src/gpu/graphite/Caps` | 能力检测基类 |
| `src/gpu/graphite/DrawPass` | 绘制通道，提供绘制命令序列 |
| `src/gpu/graphite/RenderPassDesc` | 渲染通道描述信息 |
| `src/gpu/graphite/DescriptorData` | 描述符类型与数据定义 |
| `src/gpu/graphite/QueueManager` | 队列管理基类 |
| `src/gpu/graphite/ThreadSafeResourceProvider` | 线程安全资源提供者基类 |

### 内部依赖（共享 Vulkan 层）

| 依赖目标 | 说明 |
|---------|------|
| `src/gpu/vk/VulkanInterface` | Vulkan 函数指针表 |
| `src/gpu/vk/VulkanUtilsPriv` | 共享的 Vulkan 工具函数 |
| `include/gpu/vk/VulkanTypes` | 公共 Vulkan 类型定义 |
| `include/gpu/vk/VulkanBackendContext` | Vulkan 后端上下文参数 |
| `include/gpu/vk/VulkanMemoryAllocator` | 内存分配器接口 |
| `include/gpu/vk/VulkanExtensions` | Vulkan 扩展查询接口 |

### 外部依赖

| 依赖目标 | 说明 |
|---------|------|
| Vulkan SDK | Vulkan API 头文件和类型定义 |
| SkSL | Skia 着色语言编译器（SPIR-V 生成） |
| `src/sksl/codegen/SkSLNativeShader` | 本机着色器（SPIR-V）数据结构 |

### 公共头文件（API 层）

| 文件 | 说明 |
|------|------|
| `include/gpu/graphite/vk/VulkanGraphiteContext.h` | `ContextFactory::MakeVulkan()` 工厂函数 |
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | `VulkanTextureInfo`, `BackendTextures::MakeVulkan()` 等公共类型 |
| `include/gpu/graphite/vk/VulkanGraphiteUtils.h` | （已弃用，重定向到 VulkanGraphiteContext.h） |

## 设计模式分析

### 1. 工厂方法模式（Factory Method）

整个 Vulkan 后端广泛使用静态 `Make()` 工厂方法创建对象，所有构造函数都是私有的或受保护的:

- `VulkanSharedContext::Make()` - 验证 `VulkanBackendContext` 参数后创建共享上下文
- `VulkanCommandBuffer::Make()` - 创建命令池和命令缓冲区
- `VulkanGraphicsPipeline::Make()` - 编译着色器、创建管线布局和管线对象
- `VulkanTexture::Make()` / `MakeWrapped()` - 创建新纹理或封装外部 VkImage
- `VulkanRenderPass::Make()` - 根据 `RenderPassDesc` 创建渲染通道

### 2. 查找或创建模式（Find-or-Create / Cache Pattern）

`VulkanResourceProvider` 中大量使用 `findOrCreate*` 方法，先查缓存再创建:

```
findOrCreateRenderPass()       -> 按 RenderPass 键缓存
findOrCreateFramebuffer()      -> 在纹理对象上缓存
findOrCreateDescriptorSet()    -> 按描述符类型分配
findOrCreateUniformBuffersDescriptorSet() -> LRU 缓存
findOrCreateLoadMSAAPipeline() -> 按 RenderPass 哈希缓存
findOrCreateCompatibleYcbcrConversion() -> 按 YCbCr 配置缓存
```

### 3. 模板方法模式（Template Method）

Graphite 核心层定义了抽象接口（如 `SharedContext::createGraphicsPipeline`、`CommandBuffer::onAddRenderPass` 等），Vulkan 后端通过 `override` 提供具体实现。这种模式使得上层的渲染逻辑与具体的 GPU API 解耦。

### 4. 桥接模式（Bridge Pattern）

`BackendTextureData` / `BackendSemaphoreData` 等内部类作为桥接，将 Graphite 抽象类型与 Vulkan 具体类型连接:

```cpp
class VulkanBackendTextureData final : public BackendTextureData {
    VkImage fVkImage;
    VulkanAlloc fMemoryAlloc;
    sk_sp<skgpu::MutableTextureState> fMutableState;
};
```

### 5. RAII 与引用计数

- `VulkanDescriptorSet` 通过 `sk_sp<VulkanDescriptorPool>` 引用其所属池，当所有描述符集释放后池自动销毁
- `VulkanImageView` 的生命周期由父 `VulkanTexture` 管理
- `VulkanProgramInfo` 在析构时清理着色器模块和管线布局
- `VulkanYcbcrConversion` 作为 `Resource` 派生类通过引用计数管理

### 6. 延迟绑定与脏标志（Lazy Binding / Dirty Flags）

`VulkanCommandBuffer` 使用脏标志追踪描述符集变更:

```cpp
bool fBindUniformBuffers = false;
bool fBindTextureSamplers = false;
```

在执行绘制命令前通过 `syncDescriptorSets()` 统一处理所有待绑定的描述符集，减少 Vulkan API 调用次数。

### 7. 策略模式（Strategy Pattern）

`VulkanCaps` 通过 `EnabledFeatures` 和各种布尔标志动态选择不同的渲染策略:
- 是否使用扩展动态状态
- 是否使用图形管线库
- 是否支持光栅化顺序附件访问
- 输入附件读取是否需要屏障

## 数据流

### 1. 上下文初始化流程

```
VulkanBackendContext (用户提供)
    |
    v
VulkanSharedContext::Make()
    |-- 创建 VulkanInterface (函数指针表)
    |-- 查询物理设备版本
    |-- 创建 VulkanCaps
    |   |-- 检测 EnabledFeatures
    |   |-- 查询 PhysicalDeviceProperties
    |   |-- 初始化 FormatTable (24种VkFormat)
    |   |-- 初始化 DepthStencilFormatTable (5种格式)
    |   |-- 应用驱动兼容修正
    |   +-- 初始化着色器能力
    |-- 创建 VkPipelineCache (可选从持久存储加载)
    |-- 创建 VulkanThreadSafeResourceProvider
    +-- 返回 sk_sp<SharedContext>
```

### 2. 渲染命令录制流程

```
DrawPass (由 Graphite 上层生成)
    |
    v
VulkanCommandBuffer::onAddRenderPass()
    |-- beginRenderPass()
    |   |-- findOrCreateRenderPass() (完整版)
    |   |-- findOrCreateFramebuffer()
    |   |-- 设置纹理布局 (VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL 等)
    |   |-- 可选: loadMSAAFromResolve() (手动 MSAA 数据加载)
    |   +-- vkCmdBeginRenderPass()
    |
    |-- performOncePerRPUpdates()
    |   |-- pushConstants (rtAdjust + dstCopyBounds)
    |   +-- 可选: updateAndBindInputAttachment()
    |
    |-- addDrawPass() (遍历 DrawPass 命令)
    |   |-- BindGraphicsPipeline -> bindGraphicsPipeline()
    |   |   +-- updateDynamicState() (差量更新)
    |   |-- BindUniformBuffer -> recordBufferBindingInfo()
    |   |-- BindTexturesAndSamplers -> recordTextureAndSamplerDescSet()
    |   |-- BindInputBuffer / BindIndexBuffer / BindIndirectBuffer
    |   |-- SetScissor -> setScissor()
    |   |-- Draw / DrawIndexed / DrawInstanced / DrawIndexedInstanced
    |   |   +-- syncDescriptorSets() (延迟绑定)
    |   +-- AddBarrier -> addBarrier()
    |
    +-- endRenderPass() -> vkCmdEndRenderPass()
```

### 3. 图形管线创建流程

```
GraphicsPipelineDesc + RenderPassDesc
    |
    v
VulkanGraphicsPipeline::Make()
    |-- 编译 SkSL -> SPIR-V (通过 SkSL::Compiler)
    |-- 可选: TransformSPIRV() (多采样输入加载变换)
    |-- CreateVulkanShaderModule() (VS + FS)
    |-- 创建 VkDescriptorSetLayout x 4
    |-- 创建 VkPipelineLayout
    |-- MakePipeline()
    |   |-- 配置顶点输入状态
    |   |-- 配置输入装配 (图元类型)
    |   |-- 配置视口/裁剪 (动态)
    |   |-- 配置光栅化 (背面剔除等)
    |   |-- 配置多重采样
    |   |-- 配置深度/模板
    |   |-- 配置颜色混合
    |   |-- 配置动态状态列表
    |   +-- vkCreateGraphicsPipelines(pipelineCache)
    |
    +-- 返回 sk_sp<VulkanGraphicsPipeline>
```

### 4. 描述符集分配流程

```
绘制命令需要绑定资源
    |
    v
VulkanResourceProvider::findOrCreateDescriptorSet()
    |-- 根据 DescriptorData 计算所需池大小
    |-- VulkanDescriptorPool::Make()
    |   |-- 创建 VkDescriptorSetLayout
    |   +-- 创建 VkDescriptorPool
    |-- VulkanDescriptorSet::Make()
    |   +-- vkAllocateDescriptorSets()
    +-- 返回 sk_sp<VulkanDescriptorSet>

对于 Uniform 缓冲区:
findOrCreateUniformBuffersDescriptorSet()
    |-- 计算 UniformBindGroupKey (基于缓冲区绑定信息)
    |-- 查找 LRU 缓存 (fUniformBufferDescSetCache)
    |-- 未命中 -> 创建新描述符集 + vkUpdateDescriptorSets()
    +-- 命中 -> 直接返回缓存的描述符集
```

### 5. 管线缓存持久化流程

```
管线编译完成
    |
    v
VulkanSharedContext::pipelineCompileWasRequired()
    +-- fHasNewVkPipelineCacheData = true

Context::syncPipelineData()  (由用户显式调用)
    |
    v
VulkanSharedContext::syncPipelineData()
    |-- 检查 fHasNewVkPipelineCacheData
    |-- vkGetPipelineCacheData() (获取大小)
    |-- 可选: 比较大小避免不必要的写入
    |-- vkGetPipelineCacheData() (获取数据)
    |-- PersistentPipelineStorage::store()
    +-- fHasNewVkPipelineCacheData = false

下次启动:
VulkanSharedContext::createPipelineCache()
    |-- PersistentPipelineStorage::load()
    |-- 验证缓存头部 (版本, vendorID, deviceID, UUID)
    +-- vkCreatePipelineCache(initialData)
```

## 相关文档与参考

### Skia 内部文档
- [Graphite 架构概述](https://skia.org/docs/dev/graphite/) - Graphite 渲染引擎的整体设计
- `src/gpu/graphite/` - Graphite 核心抽象层源码
- `src/gpu/vk/` - 共享的 Vulkan 工具层（Ganesh 和 Graphite 共用）
- `include/gpu/graphite/vk/` - Vulkan 后端的公共 API 头文件
- `src/gpu/graphite/vk/precompile/` - Vulkan 特定的预编译着色器支持

### Vulkan 规范参考
- [Vulkan 1.3 规范](https://registry.khronos.org/vulkan/specs/1.3/html/) - Khronos 官方 Vulkan 规范
- [VkRenderPass](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#renderpass) - 渲染通道规范
- [VkPipeline](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#pipelines) - 管线规范
- [VkDescriptorSet](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#descriptorsets) - 描述符集规范
- [Pipeline Cache](https://registry.khronos.org/vulkan/specs/1.3/html/vkspec.html#pipelines-cache) - 管线缓存规范（第 9.6 节）

### 关键 Vulkan 扩展
- `VK_EXT_rasterization_order_attachment_access` - 光栅化顺序附件访问（输入附件读取一致性）
- `VK_EXT_multisampled_render_to_single_sampled` - 多重采样渲染到单采样优化
- `VK_EXT_extended_dynamic_state` / `VK_EXT_extended_dynamic_state2` - 扩展动态状态
- `VK_EXT_vertex_input_dynamic_state` - 动态顶点输入状态
- `VK_EXT_graphics_pipeline_library` - 图形管线库（分阶段编译）
- `VK_EXT_host_image_copy` - 主机端图像拷贝
- `VK_KHR_sampler_ycbcr_conversion` - YCbCr 采样器转换
- `VK_EXT_device_fault` - 设备故障信息查询
- `VK_EXT_frame_boundary` - 帧边界标记
- `VK_EXT_pipeline_creation_cache_control` - 管线创建缓存控制

### 相关后端实现对比
- `src/gpu/graphite/mtl/` - Metal 后端实现（macOS/iOS）
- `src/gpu/graphite/dawn/` - Dawn/WebGPU 后端实现
- `src/gpu/ganesh/vk/` - Ganesh（旧架构）的 Vulkan 后端实现
