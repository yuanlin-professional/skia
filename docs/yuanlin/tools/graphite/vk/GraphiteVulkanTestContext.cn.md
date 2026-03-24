# GraphiteVulkanTestContext - Graphite Vulkan 测试上下文

> 源文件:
> - `tools/graphite/vk/GraphiteVulkanTestContext.h`
> - `tools/graphite/vk/GraphiteVulkanTestContext.cpp`

## 概述

GraphiteVulkanTestContext 提供了基于 Vulkan 后端的 Graphite 测试上下文实现。它封装了 Vulkan 实例、设备、调试消息回调等底层资源的创建与管理，为 Skia 的 Graphite 渲染引擎提供 Vulkan 后端的测试环境。该类是 `GraphiteTestContext` 的子类，通过工厂方法 `Make()` 创建完整的 Vulkan 测试上下文。

## 架构位置

```
skiatest::graphite::GraphiteTestContext (基类)
    └── skiatest::graphite::VulkanTestContext (Vulkan 后端实现)
```

位于 Skia 测试工具链中的 Graphite 后端测试层。与 `MtlTestContext`（Metal）和 `DawnTestContext`（Dawn）并列，共同构成 Graphite 的多后端测试基础设施。

## 主要类与结构体

### `VulkanTestContext`

- **继承**: `GraphiteTestContext`
- **命名空间**: `skiatest::graphite`
- **成员变量**:
  - `fVulkan` (`skgpu::VulkanBackendContext`): Vulkan 后端上下文，包含实例、设备、队列等核心对象
  - `fExtensions` (`const skgpu::VulkanExtensions*`): Vulkan 扩展集合
  - `fFeatures` (`const sk_gpu_test::TestVkFeatures*`): Vulkan 设备特性集
  - `fDebugMessenger` (`VkDebugUtilsMessengerEXT`): Vulkan 调试消息句柄
  - `fDestroyDebugUtilsMessengerEXT`: 销毁调试消息回调的函数指针

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `Make()` | 静态工厂方法，创建并返回 `VulkanTestContext` 实例 |
| `backend()` | 返回 `skgpu::BackendApi::kVulkan` |
| `contextType()` | 返回 `skgpu::ContextType::kVulkan` |
| `makeContext(const TestOptions&)` | 创建 Graphite Vulkan 上下文用于测试 |
| `getBackendContext()` | 返回底层 `VulkanBackendContext` 的常量引用 |

## 内部实现细节

### Make() 工厂方法流程

1. 调用 `sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs` 加载 Vulkan 库并获取 `vkGetInstanceProcAddr`
2. 通过 `sk_gpu_test::CreateVkBackendContext` 创建完整的 Vulkan 后端上下文，包括实例、物理设备、逻辑设备和内存分配器
3. 配置调试消息回调（如果 `SK_ENABLE_VK_LAYERS` 启用）
4. 将所有资源包装到 `VulkanTestContext` 实例中

### 受保护上下文支持

通过全局变量 `gCreateProtectedContext` 支持受保护上下文（Protected Context）。当 `SK_GANESH` 定义时从 `GrContextFactory.cpp` 获取该标志，否则默认为 `false`。

### 资源释放（析构函数）

使用 `ACQUIRE_VK_PROC_LOCAL` 宏动态获取 Vulkan 函数指针，按以下顺序释放资源：
1. 释放内存分配器
2. 等待设备空闲 (`vkDeviceWaitIdle`)
3. 销毁逻辑设备 (`vkDestroyDevice`)
4. 销毁调试消息回调（仅在 `SK_ENABLE_VK_LAYERS` 下）
5. 销毁 Vulkan 实例 (`vkDestroyInstance`)
6. 释放扩展和特性对象

## 依赖关系

- **内部依赖**: `GraphiteTestContext`（基类）、`TestOptions`、`ContextOptionsPriv`
- **Vulkan 依赖**: `VulkanBackendContext`、`VulkanExtensions`、`VulkanMemoryAllocator`
- **测试工具**: `VkTestUtils`（Vulkan 测试实用工具）
- **Graphite 核心**: `Context`、`ContextOptions`、`VulkanGraphiteContext`

## 设计模式与设计决策

- **工厂方法模式**: `Make()` 封装了复杂的 Vulkan 初始化流程，失败时返回 `nullptr`
- **私有构造函数**: 防止直接构造，确保只能通过 `Make()` 创建有效实例
- **动态函数加载**: 通过 `ACQUIRE_VK_PROC_LOCAL` 宏在运行时动态获取 Vulkan 函数指针，避免链接时依赖
- **条件编译**: 使用 `SK_ENABLE_VK_LAYERS` 和 `SK_GANESH` 控制调试功能和受保护上下文支持

## 性能考量

- `makeContext` 中设置 `fStoreContextRefInRecorder = true`，这是使同步 `readPixels` 工作所必需的，但在 Recorder 中存储 Context 引用会增加内存开销
- 内存分配器在析构时首先释放，确保所有 Vulkan 资源在设备销毁前被正确回收

## 相关文件

- `tools/graphite/GraphiteTestContext.h` - 测试上下文基类
- `tools/graphite/mtl/GraphiteMtlTestContext.h` - Metal 后端对应实现
- `tools/graphite/dawn/GraphiteDawnTestContext.h` - Dawn 后端对应实现
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试实用工具
- `tools/graphite/TestOptions.h` - 测试选项定义
- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文定义
