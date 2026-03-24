# VulkanResourceProvider

> 源文件: `src/gpu/graphite/vk/VulkanResourceProvider.h`, `src/gpu/graphite/vk/VulkanResourceProvider.cpp`

## 概述

`VulkanResourceProvider` 是 Skia Graphite Vulkan 后端的资源提供者，继承自通用的 `ResourceProvider` 基类。它负责创建和缓存所有 Vulkan 特有的 GPU 资源，包括纹理、缓冲区、采样器、描述符集、渲染通道、帧缓冲区和图形管线。该类还管理一个模拟管线布局（mock pipeline layout），用于在绑定实际管线之前执行每渲染通道操作。

## 架构位置

- **上层**: 继承自 `ResourceProvider`，由 `Recorder` 持有
- **核心角色**: 作为 Vulkan 资源创建的中心工厂
- **下游**: 创建的资源被 `VulkanCommandBuffer` 和其他 Vulkan 组件使用

## 主要类与结构体

### `VulkanResourceProvider` 类

**关键常量**:
- `kIntrinsicConstantSize` = 32 字节 — 固有常量（rtAdjust + dst copy bounds）的推送常量大小
- `kIntrinsicConstantStageFlags` — 顶点和片段着色器阶段
- `kLoadMSAAPushConstantSize` = 16 字节 — MSAA 加载推送常量大小

**私有成员**:
- `fMockPipelineLayout` — 模拟管线布局，与所有实际管线布局的推送常量和输入附件描述符集兼容
- `fLoadMSAAPipelines` — MSAA 加载管线缓存
- `fLoadMSAAProgram` — 共享的 MSAA 加载着色器模块和管线布局
- `fUniformBufferDescSetCache` — Uniform 缓冲区描述符集的 LRU 缓存（最大 1024 条）
- `fCurrentPoolSizes` — 每种描述符集布局的当前池大小追踪

## 公共 API 函数

### 资源查找/创建

- **`findOrCreateCompatibleYcbcrConversion(VulkanYcbcrConversionInfo)`** — 查找或创建 YCbCr 颜色空间转换对象
- **`findOrCreateDescriptorSet(SkSpan<DescriptorData>)`** — 查找或创建描述符集
- **`findOrCreateUniformBuffersDescriptorSet(SkSpan<DescriptorData>, SkSpan<BindBufferInfo>)`** — 查找或创建 uniform 缓冲区描述符集（带 LRU 缓存）
- **`findOrCreateLoadMSAAPipeline(RenderPassDesc)`** — 查找或创建 MSAA 加载管线
- **`findOrCreateRenderPass(RenderPassDesc, bool compatibleOnly)`** — 查找或创建渲染通道（兼容或完整）
- **`findOrCreateFramebuffer(...)`** — 查找或创建帧缓冲区

### 访问器

- **`mockPipelineLayout()`** — 返回模拟管线布局

## 内部实现细节

### 模拟管线布局

`create_mock_layout()` 创建一个与所有实际管线布局兼容的管线布局：
- 包含与固有常量匹配的推送常量范围
- 包含输入附件描述符集布局
- 允许在绑定实际管线之前更新推送常量和输入附件

### 描述符集管理

描述符集采用池化分配策略：
- 首次为某种布局分配时创建 16 个描述符集
- 后续按 1.5 倍增长，最大 512 个
- 描述符集通过 `GraphiteResourceKey` 缓存在资源缓存中
- Uniform 缓冲区描述符集额外使用 LRU 缓存，键基于缓冲区唯一 ID 和大小

### 资源创建代理

覆盖基类的创建方法，委托给具体的 Vulkan 资源类：
- `createTexture()` → `VulkanTexture::Make()`
- `createBuffer()` → `VulkanBuffer::Make()`
- `createSampler()` → `VulkanSampler::Make()`
- `onCreateWrappedTexture()` → `VulkanTexture::MakeWrapped()`

### YCbCr 转换

纹理和采样器创建时检查 YCbCr 转换信息，如果有效则先查找或创建兼容的转换对象。

## 依赖关系

- `ResourceProvider` — 基类
- `VulkanSharedContext` — Vulkan 设备和能力
- `VulkanDescriptorPool/Set` — 描述符管理
- `VulkanRenderPass` — 渲染通道
- `VulkanFramebuffer` — 帧缓冲区
- `VulkanGraphicsPipeline` — 图形管线
- `VulkanTexture/Buffer/Sampler` — 基础资源

## 设计模式与设计决策

### LRU 缓存

Uniform 缓冲区描述符集使用 LRU 缓存（最大 1024 条），因为这些描述符集的创建频率高但重复率也高。键包含缓冲区 ID 和大小。

### 池大小增长策略

描述符池大小从 16 开始，按 1.5 倍增长到最大 512。这种策略平衡了初始内存分配和后续分配频率。

### 模拟布局的兼容性

模拟管线布局确保在渲染通道开始时（实际管线尚未绑定）就能更新推送常量和输入附件描述符集，避免了渲染通道内的管线绑定顺序依赖。

## 性能考量

- **描述符集预分配**: 批量分配多个描述符集以减少 Vulkan API 调用频率
- **LRU 缓存命中**: Uniform 缓冲区描述符集的缓存命中率通常很高
- **资源共享**: 渲染通道和帧缓冲区通过资源缓存共享
- **Android 硬件缓冲**: 支持直接从 AHardwareBuffer 创建后端纹理

## 相关文件

- `src/gpu/graphite/ResourceProvider.h` — 基类
- `src/gpu/graphite/vk/VulkanSharedContext.h` — Vulkan 共享上下文
- `src/gpu/graphite/vk/VulkanDescriptorSet.h` — 描述符集
- `src/gpu/graphite/vk/VulkanRenderPass.h` — 渲染通道
- `src/gpu/graphite/vk/VulkanGraphicsPipeline.h` — 图形管线
