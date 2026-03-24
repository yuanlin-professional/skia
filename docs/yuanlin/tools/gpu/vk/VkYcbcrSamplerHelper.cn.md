# VkYcbcrSamplerHelper - Vulkan YCbCr 采样器测试助手

> 源文件:
> - [tools/gpu/vk/VkYcbcrSamplerHelper.h](../../../tools/gpu/vk/VkYcbcrSamplerHelper.h)
> - [tools/gpu/vk/VkYcbcrSamplerHelper.cpp](../../../tools/gpu/vk/VkYcbcrSamplerHelper.cpp)

## 概述

VkYcbcrSamplerHelper 是一个测试辅助类，用于创建和管理 Vulkan YCbCr 格式的后端纹理。YCbCr 格式在 Vulkan 中特别有趣，因为其采样器是不可变的（immutable sampler）。该类同时支持 Ganesh 和 Graphite 两种 GPU 后端，封装了 YCbCr 纹理创建的完整 Vulkan API 调用流程。

## 架构位置

位于 `tools/gpu/vk/` 目录下，属于 Vulkan GPU 测试工具层。它直接操作 Vulkan API 创建 YCbCr 纹理，然后将其包装为 Ganesh 的 `GrBackendTexture` 或 Graphite 的 `BackendTexture`。

## 主要类与结构体

### `VkYcbcrSamplerHelper`
管理 VkImage、VkDeviceMemory 以及后端纹理的创建和生命周期。

- 支持 Graphite（通过 `VulkanSharedContext`）和 Ganesh（通过 `GrDirectContext`）两种构造方式
- 持有 `VkImage` 和 `VkDeviceMemory` 原始 Vulkan 对象

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `VkYcbcrSamplerHelper(VulkanSharedContext*)` | Graphite 后端构造函数 |
| `VkYcbcrSamplerHelper(GrDirectContext*)` | Ganesh 后端构造函数 |
| `isYCbCrSupported()` | 检查设备是否支持 YCbCr 转换 |
| `createBackendTexture(width, height)` | 创建 Graphite 后端纹理 |
| `createGrBackendTexture(width, height)` | 创建 Ganesh 后端纹理 |
| `backendTexture()` | 获取 Graphite 后端纹理引用 |
| `grBackendTexture()` | 获取 Ganesh 后端纹理引用 |
| `GetExpectedY(x, y, w, h)` | 计算期望的 Y 通道值（静态） |
| `GetExpectedUV(x, y, w, h)` | 计算期望的 UV 通道值对（静态） |

## 内部实现细节

- **纹理格式**：使用 `VK_FORMAT_G8_B8R8_2PLANE_420_UNORM`（双平面 4:2:0 YCbCr）
- **创建流程**：CreateImage -> GetImageMemoryRequirements -> AllocateMemory -> MapMemory -> 写入像素 -> FlushMappedMemoryRanges -> UnmapMemory -> BindImageMemory
- **Y 通道数据**：`16 + (x+y) * 219 / (w+h-2)`，模拟 ITU 窄范围 [16, 235]
- **UV 通道数据**：U = `16 + x * 224 / (w-1)`，V = `16 + y * 224 / (h-1)`，范围 [16, 240]
- **YCbCr 转换配置**：使用 BT.709 颜色模型、ITU 窄范围、COSITED_EVEN 色度位置、线性滤波
- **内存类型选择**：遍历物理设备内存属性，查找 `HOST_VISIBLE` 的内存类型索引
- **析构函数**：分别处理 Graphite 和 Ganesh 后端的资源清理

## 依赖关系

- **Vulkan API**：VkImage、VkDeviceMemory、VkImageCreateInfo、VkFormatProperties 等
- **Graphite**：BackendTexture、VulkanSharedContext、VulkanGraphiteTypes
- **Ganesh**：GrBackendTexture、GrVkGpu、GrDirectContext
- **通用 GPU**：VulkanTypes、VulkanInterface、VulkanYcbcrConversionInfo

## 设计模式与设计决策

- **双后端支持**：通过条件编译（`SK_GRAPHITE` / `SK_GANESH`）同时支持两种 GPU 后端。
- **确定性测试数据**：Y 和 UV 值由坐标公式计算，便于验证采样结果的正确性。
- **线性平铺**：使用 `VK_IMAGE_TILING_LINEAR` 以便直接 CPU 映射写入数据。
- **能力检查分离**：`isYCbCrSupported()` 独立于纹理创建，允许优雅地跳过不支持的设备。

## 性能考量

- 仅用于测试场景，不需要优化性能。
- 使用 HOST_VISIBLE 内存和线性平铺以简化数据上传，生产代码通常使用 staging buffer。
- 每个 Helper 实例管理独立的 VkImage 和 VkDeviceMemory。

## 相关文件

- `tools/gpu/vk/VkTestHelper.h` - Vulkan 测试环境设置
- `tests/VkYcbcrSamplerTest.cpp` - 使用此 Helper 的测试
- `include/gpu/vk/VulkanTypes.h` - Vulkan 类型定义
