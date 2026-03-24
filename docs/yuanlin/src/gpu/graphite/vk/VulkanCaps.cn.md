# VulkanCaps

> 源文件
> - `src/gpu/graphite/vk/VulkanCaps.h`
> - `src/gpu/graphite/vk/VulkanCaps.cpp`

## 概述

`VulkanCaps` 是 Skia Graphite 的 Vulkan 后端能力查询与管理系统的核心类。它负责在初始化时查询物理设备的功能特性、限制参数、扩展支持和格式属性，并将这些信息转换为 Graphite 可以使用的能力标志。该类继承自 `Caps` 基类，为上层渲染系统提供统一的能力查询接口，同时封装了 Vulkan 特定的格式支持判定、管线键生成、内存策略决策等功能。

## 架构位置

`VulkanCaps` 位于 Vulkan 后端的初始化和配置层：

```
skgpu::graphite
    └── Caps (基类)
         └── VulkanCaps
              ├── 查询 VkPhysicalDevice 属性
              ├── 管理 FormatInfo 表（格式能力）
              ├── 管理 DepthStencilFormatInfo 表
              ├── 提供管线键生成 (UniqueKey)
              └── 被 VulkanSharedContext 使用
```

它在设备初始化阶段创建，为整个 Vulkan 后端的资源分配、格式选择、管线创建和渲染策略提供决策依据。

## 主要类与结构体

### VulkanCaps

```cpp
class VulkanCaps final : public Caps
```

**核心成员变量：**
- `FormatInfo fFormatTable[kNumVkFormats]` - VkFormat 格式能力表（24种格式）
- `DepthStencilFormatInfo fDepthStencilFormatTable[kNumDepthStencilVkFormats]` - 深度模板格式表（5种格式）
- `VkPhysicalDeviceMemoryProperties2 fPhysicalDeviceMemoryProperties2` - 设备内存属性
- `uint32_t fMaxVertexAttributes` - 最大顶点属性数量
- `uint64_t fMaxUniformBufferRange` - 统一缓冲区最大范围
- `uint64_t fMaxStorageBufferRange` - 存储缓冲区最大范围
- 多个能力标志（如 `fSupportsYcbcrConversion`、`fGpuOnlyBuffersMorePerformant` 等）

**核心方法：**
- `VulkanCaps()` - 构造函数，触发能力初始化
- `void init()` - 主初始化流程
- `void initFormatTable()` - 初始化格式支持表
- `UniqueKey makeGraphicsPipelineKey()` - 生成图形管线唯一键

### EnabledFeatures

```cpp
struct EnabledFeatures
```

存储已启用的 Vulkan 功能特性（从 `VkPhysicalDeviceFeatures2` 链中提取）：
- `fDualSrcBlend` - 双源混合
- `fSamplerYcbcrConversion` - YCbCr 采样器转换
- `fAdvancedBlendModes` - 高级混合模式
- `fGraphicsPipelineLibrary` - 图形管线库
- `fHostImageCopy` - 主机图像拷贝（Vulkan 1.4）
- 等20多个特性标志

### FormatInfo

```cpp
struct FormatInfo
```

存储每个 `VkFormat` 的详细能力信息：
- `ColorTypeInfo[] fColorTypeInfos` - 颜色类型映射表
- `VkFormatProperties fFormatProperties` - Vulkan 格式属性
- `SupportedSampleCounts fSupportedSampleCounts` - 支持的采样数
- `bool fIsEfficientWithHostImageCopy` - 主机图像拷贝效率标志

**核心方法：**
- `void init()` - 查询格式属性
- `bool isTexturable()` - 判断是否可用作纹理
- `bool isRenderable()` - 判断是否可渲染
- `bool isStorage()` - 判断是否支持存储图像

### PhysicalDeviceProperties

```cpp
struct PhysicalDeviceProperties
```

聚合多个 Vulkan 设备属性结构：
- `VkPhysicalDeviceProperties2 fBase` - 基础属性
- `VkPhysicalDeviceDriverProperties fDriver` - 驱动信息
- `VkPhysicalDeviceGraphicsPipelineLibraryPropertiesEXT fGpl` - 管线库属性
- `VkPhysicalDeviceHostImageCopyPropertiesEXT fHic` - 主机图像拷贝属性

## 公共 API 函数

### 能力查询

```cpp
bool gpuOnlyBuffersMorePerformant() const
```

返回 GPU 独占缓冲区是否比主机可见缓冲区性能更好（通常在离散 GPU 上为 true）。

```cpp
bool shouldPersistentlyMapCpuToGpuBuffers() const
```

返回是否应该持久映射 CPU->GPU 缓冲区（集成 GPU 通常为 true，离散 GPU 为 false）。

```cpp
bool supportsYcbcrConversion() const
```

返回是否支持 YCbCr 采样器转换（用于视频纹理）。

```cpp
bool isInputAttachmentReadCoherent() const
```

返回输入附件读取是否一致（影响子通道依赖的设置）。

### 格式查询

```cpp
std::pair<SkEnumBitMask<TextureUsage>, SkEnumBitMask<SampleCount>>
getTextureSupport(TextureFormat format, Tiling tiling) const
```

查询指定格式和平铺模式支持的纹理用途和采样数。

### 管线键生成

```cpp
UniqueKey makeGraphicsPipelineKey(
    const GraphicsPipelineDesc& pipelineDesc,
    const RenderPassDesc& renderPassDesc
) const override
```

为图形管线生成唯一键，用于管线缓存和查找。

```cpp
bool extractGraphicsDescs(
    const UniqueKey& key,
    GraphicsPipelineDesc* pipelineDesc,
    RenderPassDesc* renderPassDesc,
    const RendererProvider* rendererProvider
) const override
```

从管线键反向解析出管线描述和渲染通道描述（用于预热管线缓存）。

### 纹理键构建

```cpp
void buildKeyForTexture(
    SkISize dimensions,
    const TextureInfo& textureInfo,
    ResourceType resourceType,
    GraphiteResourceKey* key
) const override
```

为纹理资源生成资源键，用于资源缓存和查找。

### 目标读取策略

```cpp
DstReadStrategy getDstReadStrategy() const override
```

返回目标读取策略，Vulkan 后端根据输入附件一致性选择：
- 一致时使用 `kInputAttachment`
- 不一致时使用 `kInputAttachmentWithBarrier`

### 不可变采样器信息

```cpp
ImmutableSamplerInfo getImmutableSamplerInfo(const TextureInfo& textureInfo) const override
```

为需要不可变采样器的纹理（如 YCbCr）返回采样器信息。

## 内部实现细节

### 初始化流程

```cpp
void init(const ContextOptions& contextOptions,
          const skgpu::VulkanInterface* vkInterface,
          VkPhysicalDevice physDev,
          uint32_t physicalDeviceVersion,
          const VkPhysicalDeviceFeatures2* features,
          const skgpu::VulkanExtensions* extensions,
          Protected isProtected)
```

**步骤：**
1. **提取启用特性**：遍历 `VkPhysicalDeviceFeatures2` 的 pNext 链，记录所有已启用的特性
2. **查询设备属性**：获取物理设备的限制、驱动信息、扩展属性
3. **查询内存属性**：获取内存类型、堆信息，判断是否支持 Lazy 分配（无内存附件）
4. **设置基础能力**：纹理大小限制、缓冲区对齐要求、最大 Varying 数量等
5. **配置资源绑定需求**：设置描述符集索引、布局类型、绑定位置
6. **应用供应商特定优化**：根据 vendorID 设置性能策略（NVIDIA/AMD 离散 GPU 策略）
7. **应用驱动修正**：针对已知驱动 bug 启用 workarounds
8. **初始化格式表**：查询每个格式的属性和采样支持
9. **完成初始化**：调用基类 `finishInitialization()`

### 格式表初始化

```cpp
void initFormatTable(const skgpu::VulkanInterface* vkInterface,
                     VkPhysicalDevice physDev,
                     const VkPhysicalDeviceProperties& deviceProperties,
                     const EnabledFeatures& enabledFeatures)
```

对每个支持的 `VkFormat`（如 `VK_FORMAT_R8G8B8A8_UNORM`、`VK_FORMAT_BC1_RGB_UNORM_BLOCK` 等）：
1. 调用 `vkGetPhysicalDeviceFormatProperties` 查询格式属性
2. 初始化 `SupportedSampleCounts`（查询不同用途的采样支持）
3. 查询主机图像拷贝效率（`VkHostImageCopyDevicePerformanceQuery`）
4. 设置 `ColorTypeInfo` 映射（如 `kRGBA_8888_SkColorType` -> `VK_FORMAT_R8G8B8A8_UNORM`）

### 供应商特定优化

```cpp
// NVIDIA 和 AMD 离散 GPU 优化
if (vendorID == skgpu::kNvidia_VkVendor || vendorID == skgpu::kAMD_VkVendor) {
    fGpuOnlyBuffersMorePerformant = true;
    fShouldPersistentlyMapCpuToGpuBuffers = false;
}

// AMD 顶点属性限制 workaround
fMaxVertexAttributes = vendorID == skgpu::kAMD_VkVendor ?
                       32 : deviceLimits.maxVertexInputAttributes;

// ARM GPU 输入附件一致性优化
fIsInputAttachmentReadCoherent = fSupportsRasterizationOrderColorAttachmentAccess ||
                                 vendorID == kARM_VkVendor ||
                                 vendorID == kImagination_VkVendor;
```

### 驱动修正

```cpp
void applyDriverCorrectnessWorkarounds(const PhysicalDeviceProperties& deviceProperties)
```

应用已知驱动 bug 的修正，例如：
- 特定驱动版本的 MSAA 加载问题（`fMustLoadFullImageForMSAA`）
- 某些设备的专用内存分配需求

### 资源绑定配置

```cpp
void populate_resource_binding_reqs(ResourceBindingRequirements& reqs) {
    reqs.fBackendApi = BackendApi::kVulkan;
    reqs.fStorageBufferLayout = Layout::kStd430;
    reqs.fUniformBufferLayout = Layout::kStd140;
    reqs.fUsePushConstantsForIntrinsicConstants = true;
    reqs.fCombinedUniformBufferBinding = VulkanGraphicsPipeline::kCombinedUniformIndex;
    reqs.fUniformsSetIdx = VulkanGraphicsPipeline::kUniformBufferDescSetIndex;
    reqs.fTextureSamplerSetIdx = VulkanGraphicsPipeline::kTextureBindDescSetIndex;
    // ...
}
```

为着色器生成器提供 Vulkan 特定的绑定配置。

### 管线键生成

管线键包含：
- 管线描述的序列化数据
- 渲染通道描述的序列化数据
- 自定义领域 ID（用于区分不同后端）

键用于在管线缓存中查找已编译的管线对象。

## 依赖关系

**直接依赖：**
- `Caps` - 基类，提供跨平台能力接口
- `skgpu::VulkanInterface` - Vulkan 函数指针表
- `skgpu::VulkanExtensions` - 扩展查询
- `VulkanGraphiteUtils` - Vulkan 工具函数
- `TextureInfo` / `VulkanTextureInfo` - 纹理信息结构

**被依赖者：**
- `VulkanSharedContext` - 使用 `VulkanCaps` 进行设备初始化和能力判定
- `VulkanResourceProvider` - 根据能力创建资源
- `VulkanGraphicsPipeline` - 根据能力配置管线状态
- Graphite 上层渲染系统 - 通过 `Caps` 接口查询能力

## 设计模式与设计决策

### 查询与缓存模式
在初始化时一次性查询所有设备能力，存储在成员变量中，避免运行时重复查询 Vulkan API。

### 分层格式管理
- `FormatInfo` 表：存储详细的纹理格式能力
- `DepthStencilFormatInfo` 表：深度模板格式的轻量级信息
- 分离管理避免深度格式承担不必要的颜色类型映射开销

### 供应商感知优化
根据 `vendorID` 应用特定的性能策略和 workarounds，平衡跨设备兼容性和性能。

### 特性链遍历
使用 Vulkan 1.1+ 的 pNext 链机制，统一处理核心特性和扩展特性，代码清晰可维护。

### 延迟决策
某些能力（如 `DstReadStrategy`）不在初始化时固定，而是在使用时根据具体情况动态查询。

### 版本兼容性
支持 Vulkan 1.1 到 1.4 的渐进式特性：
- Vulkan 1.1：YCbCr 转换、多视图
- Vulkan 1.3：扩展动态状态成为核心
- Vulkan 1.4：主机图像拷贝成为核心

## 性能考量

1. **格式查询优化**
   所有格式属性在初始化时查询并缓存，运行时仅进行表查找（O(1)）。

2. **离散 GPU 内存策略**
   在 NVIDIA/AMD 离散 GPU 上优先使用设备本地内存，避免持久映射，减少 PCIe 总线压力。

3. **输入附件一致性**
   在 ARM/Imagination GPU 上利用硬件保证的一致性，避免不必要的子通道依赖和内存屏障。

4. **管线库快速链接**
   在支持 `graphicsPipelineLibraryFastLinking` 的设备上启用管线库，减少编译时间。

5. **无内存附件支持**
   在支持 Lazy 分配的设备上使用无内存附件（transient attachments），节省内存带宽。

6. **主机图像拷贝判定**
   通过 `VkHostImageCopyDevicePerformanceQuery` 查询格式是否高效支持主机拷贝，避免因 `VK_IMAGE_USAGE_HOST_TRANSFER_BIT` 导致帧缓冲压缩禁用。

7. **存储缓冲区禁用**
   当前由于性能回归（b/353983969），存储缓冲区支持被禁用，所有缓冲区使用 UBO。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Caps.h` | 能力基类定义 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
| `src/gpu/graphite/vk/VulkanResourceProvider.h` | Vulkan 资源提供者 |
| `src/gpu/graphite/vk/VulkanGraphicsPipeline.h` | Vulkan 图形管线 |
| `src/gpu/graphite/vk/VulkanTextureInfo.h` | Vulkan 纹理信息 |
| `src/gpu/vk/VulkanInterface.h` | Vulkan 函数指针接口 |
| `src/gpu/vk/VulkanExtensions.h` | Vulkan 扩展管理 |
| `src/gpu/vk/VulkanUtilsPriv.h` | Vulkan 工具函数 |
| `include/gpu/graphite/ContextOptions.h` | 上下文选项 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 图形管线描述 |
| `src/gpu/graphite/RenderPassDesc.h` | 渲染通道描述 |
