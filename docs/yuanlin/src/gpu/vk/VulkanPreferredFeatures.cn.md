# VulkanPreferredFeatures

> 源文件：
> - include/gpu/vk/VulkanPreferredFeatures.h
> - src/gpu/vk/VulkanPreferredFeatures.cpp

## 概述

`VulkanPreferredFeatures` 是 Skia 用于在应用程序创建 Vulkan 设备之前，向实例扩展列表和设备功能列表中添加 Skia 所需扩展和功能的辅助类。它允许应用程序无需了解 Skia 内部需求，就能正确启用 Skia 所需的 Vulkan 扩展和功能特性，避免性能下降。

该类的核心设计理念是：Skia 需要应用程序创建 Vulkan 实例和设备，但应用程序不一定知道 Skia 想要使用的所有扩展和功能。通过使用这个类，应用程序可以让 Skia 在设备创建前修改扩展和功能列表。

## 架构位置

该类位于 Skia GPU 后端的 Vulkan 实现层：

```
skia/
├── include/gpu/vk/          # Vulkan 公共接口
│   └── VulkanPreferredFeatures.h
└── src/gpu/vk/              # Vulkan 实现
    ├── VulkanPreferredFeatures.cpp
    └── VulkanUtilsPriv.h    # 内部工具函数
```

该类是 Skia Vulkan 后端初始化流程的关键组件，在应用程序创建 VkInstance 和 VkDevice 时提供扩展和功能管理。

## 主要类与结构体

### VulkanPreferredFeatures

公共 API 类，负责协调 Vulkan 扩展和功能的启用流程。

**继承关系：**
- 无继承关系

**关键成员变量：**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fAPIVersion` | `uint32_t` | 应用程序使用的 Vulkan API 版本 |
| `fHasAddedToInstanceExtensions` | `bool` | 跟踪是否调用了实例扩展添加 |
| `fHasAddedFeaturesToQuery` | `bool` | 跟踪是否调用了功能查询添加 |
| `fHasAddedFeaturesToEnable` | `bool` | 跟踪是否调用了功能启用添加 |
| `fVulkan11/12/13/14` | `VkPhysicalDeviceVulkanNNFeatures` | Vulkan 1.1-1.4 核心功能结构体 |
| `fRasterizationOrderAttachmentAccess` | `VkPhysicalDeviceRasterizationOrderAttachmentAccessFeaturesEXT` | 光栅化顺序附件访问功能 |
| `fBlendOperationAdvanced` | `VkPhysicalDeviceBlendOperationAdvancedFeaturesEXT` | 高级混合操作功能 |
| `fExtendedDynamicState` | `VkPhysicalDeviceExtendedDynamicStateFeaturesEXT` | 扩展动态状态功能 |
| `fExtendedDynamicState2` | `VkPhysicalDeviceExtendedDynamicState2FeaturesEXT` | 扩展动态状态 2 功能 |
| `fVertexInputDynamicState` | `VkPhysicalDeviceVertexInputDynamicStateFeaturesEXT` | 顶点输入动态状态功能 |
| `fGraphicsPipelineLibrary` | `VkPhysicalDeviceGraphicsPipelineLibraryFeaturesEXT` | 图形管线库功能 |
| `fSamplerYcbcrConversion` | `VkPhysicalDeviceSamplerYcbcrConversionFeatures` | YCbCr 采样器转换功能 |
| `fRGBA10x6Formats` | `VkPhysicalDeviceRGBA10X6FormatsFeaturesEXT` | RGBA10x6 格式支持 |
| `fDynamicRendering` | `VkPhysicalDeviceDynamicRenderingFeatures` | 动态渲染功能 |
| `fDynamicRenderingLocalRead` | `VkPhysicalDeviceDynamicRenderingLocalReadFeatures` | 动态渲染本地读取功能 |
| `fMultisampledRenderToSingleSampled` | `VkPhysicalDeviceMultisampledRenderToSingleSampledFeaturesEXT` | 多采样到单采样渲染 |
| `fHostImageCopy` | `VkPhysicalDeviceHostImageCopyFeatures` | 主机图像复制功能 |
| `fPipelineCreationCacheControl` | `VkPhysicalDevicePipelineCreationCacheControlFeatures` | 管线创建缓存控制 |
| `fFrameBoundary` | `VkPhysicalDeviceFrameBoundaryFeaturesEXT` | 帧边界功能 |

### DeviceExtensions（内部结构体）

在实现文件中定义的辅助结构体，用于跟踪哪些设备扩展可用或已启用。

### FeaturesToAdd（内部结构体）

在实现文件中定义的辅助结构体，用于决定需要查询或启用哪些功能结构体。

## 公共 API 函数

### 初始化与配置

| 函数签名 | 说明 |
|---------|------|
| `void init(uint32_t appAPIVersion)` | 初始化类实例，设置应用程序使用的 API 版本（最低 1.1，最高 1.4） |

### 扩展和功能管理

| 函数签名 | 说明 |
|---------|------|
| `void addToInstanceExtensions(const VkExtensionProperties*, size_t, std::vector<const char*>&)` | 在创建 VkInstance 前，向实例扩展列表添加 Skia 需要的扩展 |
| `void addFeaturesToQuery(const VkExtensionProperties*, size_t, VkPhysicalDeviceFeatures2&)` | 在查询设备功能前，添加 Skia 想要查询的功能结构体到 pNext 链 |
| `void addFeaturesToEnable(std::vector<const char*>&, VkPhysicalDeviceFeatures2&)` | 在创建 VkDevice 前，向扩展列表和功能链添加 Skia 需要启用的项 |

### 使用流程

推荐的 Vulkan 初始化流程：

```cpp
// 1. 查询加载器，决定使用的 API 版本
skgpu::VulkanPreferredFeatures skiaFeatures;
skiaFeatures.init(apiVersion);

// 2. 让 Skia 添加实例扩展
skiaFeatures.addToInstanceExtensions(...);

// 3. 创建实例，选择物理设备，查询可用扩展

// 4. 让 Skia 添加要查询的功能
skiaFeatures.addFeaturesToQuery(...);

// 5. 查询功能，决定要启用的扩展和功能

// 6. 让 Skia 添加要启用的扩展和功能
skiaFeatures.addFeaturesToEnable(...);

// 7. 创建 Vulkan 设备
```

## 内部实现细节

### 功能提升规则处理

实现代码详细处理了 Vulkan 扩展提升到核心版本的规则：

- **Vulkan 1.1 提升的功能**：包括 YCbCr 采样器转换等
- **Vulkan 1.2 提升的功能**：包括驱动属性、创建 renderpass2 等
- **Vulkan 1.3 提升的功能**：包括同步 2、动态渲染、管线创建缓存控制等
- **Vulkan 1.4 提升的功能**：包括动态渲染本地读取、主机图像复制等

当使用更高版本的 Vulkan API 时，类会自动使用 `VkPhysicalDeviceVulkanNNFeatures` 结构体代替单独的扩展功能结构体。

### 功能查询逻辑

`addFeaturesToQuery()` 的实现包含三个主要步骤：

1. **检查可用扩展**：使用 `mark_device_extensions()` 和 `get_supported_device_extensions()` 标记可用的设备扩展
2. **决定要查询的功能**：`get_features_to_query()` 根据 API 版本和可用扩展决定需要添加哪些功能结构体
3. **链接功能结构体**：将需要查询的功能结构体添加到 `VkPhysicalDeviceFeatures2` 的 pNext 链

### 功能启用逻辑

`addFeaturesToEnable()` 的实现更为复杂：

1. **添加扩展**：如果应用程序未启用但 Skia 需要的扩展，添加到扩展列表
2. **禁用不需要的功能**：在 Skia 自己的功能结构体中禁用不使用的功能以减少开销
3. **处理互斥规则**：根据 Vulkan 规范，某些功能结构体不能同时存在（如 `VkPhysicalDeviceVulkan12Features` 和其提升的扩展结构体），代码会合并这些功能并移除冗余结构体
4. **启用必需功能**：如果扩展已启用，确保其主要功能也被启用

### 扩展依赖管理

某些扩展依赖其他扩展，类会自动处理这些依赖：

- `VK_EXT_graphics_pipeline_library` 依赖 `VK_KHR_pipeline_library`
- `VK_EXT_host_image_copy` 依赖 `VK_KHR_copy_commands2` 和 `VK_KHR_format_feature_flags2`
- `VK_EXT_multisampled_render_to_single_sampled` 依赖 `VK_KHR_depth_stencil_resolve`
- Android 上的 `VK_ANDROID_external_memory_android_hardware_buffer` 依赖 `VK_EXT_queue_family_foreign`

### 特殊处理

- **YCbCr 转换**：从 Vulkan 1.4 开始是必需功能，代码确保其被启用
- **可选功能选择性禁用**：如光栅化顺序深度/模板附件访问，即使支持也可能被禁用以避免性能成本
- **扩展选择性禁用**：通过预处理宏（如 `SK_DISABLE_GRAPHICS_PIPELINE_LIBRARY`）可以禁用某些实验性扩展

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/private/base/SkAPI.h` | API 导出宏定义 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型和函数定义 |
| `include/private/base/SkAssert.h` | 断言宏 |
| `include/private/base/SkDebug.h` | 调试输出 |
| `src/gpu/vk/VulkanUtilsPriv.h` | Vulkan 工具函数（如 `AddToPNextChain`） |

### 被依赖的模块

该类主要被以下场景使用：

- Skia 应用程序的 Vulkan 初始化代码
- `VulkanBackendContext` 的创建流程
- 测试代码（如 `tests/VkPreferredFeaturesTest.cpp`）

## 设计模式与设计决策

### 构建器模式

该类采用类似构建器模式的设计，通过三个独立的步骤（添加实例扩展、查询功能、启用功能）逐步构建完整的 Vulkan 设备配置。

### 无侵入式设计

类的设计理念是"无侵入"：只添加应用程序未启用的扩展和功能，不强制覆盖应用程序的选择。这允许应用程序保留对 Vulkan 配置的完全控制权。

### 版本感知

实现对不同 Vulkan 版本高度敏感，根据应用程序使用的 API 版本自动选择合适的功能结构体，遵循 Vulkan 规范的有效使用规则。

### 防御性编程

- 析构函数中检查是否正确使用了所有 API 函数
- 使用断言验证假设条件
- 提供警告信息帮助开发者正确使用

### 扩展性设计

代码注释中详细说明了如何添加新扩展支持和新 Vulkan 版本支持，使得维护和扩展变得容易。

## 性能考量

### 避免不必要的功能

代码显式禁用 Skia 不使用的功能，即使这些功能可用：

- 禁用深度/模板附件的光栅化顺序访问以避免潜在的性能成本
- 禁用未使用的动态状态功能

### 选择最优 API

优先使用 `VkPhysicalDeviceVulkanNNFeatures` 结构体而非单独的扩展结构体，因为某些驱动程序可能不暴露已提升到核心的扩展。

### 条件编译

通过预处理宏允许禁用某些扩展（如图形管线库），用于性能测试或规避驱动问题。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/vk/VulkanBackendContext.h` | 使用 | VulkanBackendContext 使用该类配置设备 |
| `src/gpu/vk/VulkanUtilsPriv.h` | 依赖 | 提供 pNext 链操作工具函数 |
| `tests/VkPreferredFeaturesTest.cpp` | 测试 | 单元测试文件 |
| `include/gpu/vk/VulkanExtensions.h` | 相关 | 扩展管理辅助类 |
| `include/gpu/vk/VulkanTypes.h` | 相关 | Vulkan 类型定义 |

### 使用建议

1. **必须按顺序调用**：`init()` → `addToInstanceExtensions()` → `addFeaturesToQuery()` → `addFeaturesToEnable()`
2. **对象生命周期**：该对象必须保持有效直到设备创建完成，因为它拥有可能被链接到 `VkPhysicalDeviceFeatures2` 的结构体
3. **不要强制禁用功能**：应用程序不应该有意包含功能结构体只是为了禁用功能，这会阻止 Skia 利用这些功能
4. **API 版本范围**：支持 Vulkan 1.1 到 1.4，不支持 1.0 或更高未来版本
