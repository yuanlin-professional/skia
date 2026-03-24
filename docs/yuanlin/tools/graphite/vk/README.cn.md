# tools/graphite/vk - Graphite Vulkan 后端测试上下文

## 概述

`tools/graphite/vk` 目录实现了 Graphite GPU 后端的 Vulkan 测试上下文。与 Ganesh 的 Vulkan 后端类似，Graphite 的 Vulkan 后端直接使用 Vulkan API 提供高性能的 GPU 渲染能力，但在架构设计上遵循了 Graphite 更现代化的设计理念。

`VulkanTestContext` 类继承自 `GraphiteTestContext`，封装了 Vulkan 后端上下文的完整状态。与 Ganesh 的 `VkTestContext` 类似，它维护了 `VulkanBackendContext`（包含 VkInstance、VkPhysicalDevice、VkDevice、VkQueue 等 Vulkan 核心对象）、Vulkan 扩展信息、设备特性以及调试工具集成。

通过 `VulkanTestContext::Make()` 静态工厂方法创建测试上下文。该方法内部使用 `tools/gpu/vk/VkTestUtils.h` 中的辅助函数来初始化 Vulkan 实例和设备，并设置 `VkDebugUtilsMessengerEXT` 用于捕获验证层消息。

与 Ganesh 版本的一个关键区别是，Graphite 的 `VulkanTestContext` 使用 `std::unique_ptr<GraphiteTestContext>` 返回值（而非裸指针），并通过 `makeContext(const TestOptions&)` 方法创建 `skgpu::graphite::Context` 而非 `GrDirectContext`。这反映了 Graphite 更现代化的所有权管理模型。

所有代码受 `SK_VULKAN` 编译宏保护。

## 目录结构

```
tools/graphite/vk/
├── GraphiteVulkanTestContext.h      # Vulkan 测试上下文声明
└── GraphiteVulkanTestContext.cpp    # Vulkan 测试上下文实现
```

## 关键类与函数

### VulkanTestContext
- **命名空间**: `skiatest::graphite`
- **基类**: `GraphiteTestContext`
- **功能**: 封装 Graphite Vulkan GPU 上下文的测试基础设施
- **核心成员**:
  - `fVulkan` (`skgpu::VulkanBackendContext`) - Vulkan 后端上下文
  - `fExtensions` (`const skgpu::VulkanExtensions*`) - 已启用的 Vulkan 扩展
  - `fFeatures` (`const sk_gpu_test::TestVkFeatures*`) - Vulkan 设备特性
  - `fDebugMessenger` (`VkDebugUtilsMessengerEXT`) - 调试消息回调
  - `fDestroyDebugUtilsMessengerEXT` - 调试工具销毁函数指针
- **核心方法**:
  - `Make()` - 静态工厂方法，创建 Vulkan 测试上下文
  - `backend()` - 返回 `skgpu::BackendApi::kVulkan`
  - `contextType()` - 返回上下文类型
  - `makeContext(const TestOptions&)` - 创建 Graphite Context
  - `getBackendContext()` - 获取 Vulkan 后端上下文引用

### Vulkan 后端上下文组成
- `VkInstance` - Vulkan 实例
- `VkPhysicalDevice` - 物理设备
- `VkDevice` - 逻辑设备
- `VkQueue` - 命令队列
- Vulkan 扩展和设备特性配置

## 依赖关系

- **上游依赖**: `tools/graphite/GraphiteTestContext.h`（基类）
- **Vulkan 依赖**: `include/gpu/vk/VulkanBackendContext.h`、`tools/gpu/vk/VkTestUtils.h`
- **编译条件**: 需要定义 `SK_VULKAN`
- **被引用**: `tools/graphite/ContextFactory.cpp`（通过 Vulkan ContextType 使用）
- **共享工具**: 与 `tools/ganesh/vk/` 共享 `tools/gpu/vk/VkTestUtils.h` 工具函数

## 相关文档与参考

- `tools/graphite/GraphiteTestContext.h` - Graphite 测试上下文基类
- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文数据结构
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具函数（共享）
- `tools/ganesh/vk/` - Ganesh Vulkan 后端测试上下文（对比参考）
- `src/gpu/graphite/vk/` - Graphite Vulkan 后端核心实现
