# VkTestHelper - Vulkan 测试环境助手

> 源文件:
> - [tools/gpu/vk/VkTestHelper.h](../../../tools/gpu/vk/VkTestHelper.h)
> - [tools/gpu/vk/VkTestHelper.cpp](../../../tools/gpu/vk/VkTestHelper.cpp)

## 概述

VkTestHelper 是一个抽象基类，封装了 Vulkan 测试环境的完整初始化流程。它负责创建 Vulkan 实例、设备、内存分配器，以及加载必要的 Vulkan 函数指针。通过工厂方法根据测试类型（Ganesh 或 Graphite）创建对应的子类实现，支持受保护内容（protected content）测试。

## 架构位置

位于 `tools/gpu/vk/` 目录下，是 Vulkan 相关测试的核心基础设施。它是 Ganesh 和 Graphite Vulkan 测试的统一入口，管理从 Vulkan 库加载到 GPU 上下文创建的完整生命周期。

## 主要类与结构体

### `VkTestHelper`（抽象基类）
管理 Vulkan 后端上下文和函数指针。

### `GaneshVkTestHelper`（内部子类）
Ganesh 后端实现，持有 `GrDirectContext`。
- 使用 DMSAA（`kDynamicMSAA_Flag`）以更好匹配 Graphite 行为

### `GraphiteVkTestHelper`（内部子类）
Graphite 后端实现，持有 `skgpu::graphite::Context` 和 `Recorder`。
- 设置 `fStoreContextRefInRecorder = true` 以支持 ManagedGraphiteTexture 的释放流程

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Make(TestType, isProtected)` | 静态工厂方法，创建对应后端的测试助手 |
| `isValid()` | 检查初始化是否成功 |
| `createSurface(size, textureable, isProtected)` | 创建测试用 SkSurface |
| `submitAndWaitForCompletion(completionMarker)` | 提交 GPU 工作并等待完成 |
| `directContext()` | 获取 Ganesh 上下文（仅 Ganesh 子类有效） |
| `recorder()` | 获取 Graphite Recorder（仅 Graphite 子类有效） |
| `context()` | 获取 Graphite Context（仅 Graphite 子类有效） |

## 内部实现细节

- **Vulkan 函数加载**：通过 `ACQUIRE_INST_VK_PROC` 和 `ACQUIRE_DEVICE_VK_PROC` 宏加载实例级和设备级 Vulkan 函数指针。
- **后端上下文创建**：`setupBackendContext()` 调用 `sk_gpu_test::CreateVkBackendContext` 完成 Vulkan 实例、设备创建和扩展/特性配置。
- **调试消息**：支持 Vulkan 调试工具消息（`VkDebugUtilsMessengerEXT`），析构时正确清理。
- **资源清理顺序**：析构时先等待设备空闲、销毁设备、清理调试回调，最后销毁实例。
- **受保护内容**：`fIsProtected` 标志贯穿初始化流程，确保上下文支持受保护内容。
- **等待完成机制**：通过轮询 `completionMarker` 标志实现异步等待。

## 依赖关系

- **Vulkan**：VulkanBackendContext、VulkanExtensions、VulkanMemoryAllocator
- **Ganesh**：GrDirectContext、GrVkDirectContext
- **Graphite**：Context、Recorder、ContextOptions、VulkanGraphiteContext
- **测试工具**：VkTestUtils（Vulkan 后端创建）、ProtectedUtils（受保护 Surface 创建）、TestType

## 设计模式与设计决策

- **抽象工厂模式**：`Make()` 根据 `TestType` 创建不同后端的具体子类。
- **模板方法模式**：`setupBackendContext()` 在基类中实现通用的 Vulkan 初始化，`init()` 由子类实现特定后端的上下文创建。
- **宏简化函数加载**：`DECLARE_VK_PROC` / `ACQUIRE_*_VK_PROC` 宏减少 Vulkan 函数指针管理的样板代码。
- **DMSAA 对齐**：Ganesh 子类启用 DMSAA 以更好匹配 Graphite 的渲染行为，确保测试结果一致性。

## 性能考量

- 仅用于测试环境初始化，性能不是关键考虑。
- `submitAndWaitForCompletion` 使用忙等待（轮询），适合测试场景但不适合生产环境。
- 析构时先 flush 并同步等待，确保所有 GPU 工作完成。

## 相关文件

- `tools/gpu/vk/VkTestUtils.h` - Vulkan 后端创建工具函数
- `tools/gpu/ProtectedUtils.h` - 受保护内容 Surface 创建
- `tests/TestType.h` - 测试类型枚举
- `tools/gpu/vk/VkYcbcrSamplerHelper.h` - YCbCr 纹理测试
