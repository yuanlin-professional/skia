# tools/ganesh/vk - Ganesh Vulkan 后端测试上下文

## 概述

`tools/ganesh/vk` 目录实现了 Ganesh GPU 后端的 Vulkan 测试上下文。Vulkan 是一种现代的跨平台低级图形 API，提供了比 OpenGL 更精细的 GPU 控制能力。本目录为 Skia 的 Vulkan 渲染路径提供了完整的测试基础设施。

`VkTestContext` 类继承自 `TestContext`，封装了 Vulkan 后端上下文的核心状态，包括 `VulkanBackendContext`（包含 VkInstance、VkDevice、VkQueue 等 Vulkan 核心对象）、Vulkan 扩展信息以及调试工具集成。该类通过 `CreatePlatformVkTestContext()` 工厂函数创建平台特定的 Vulkan 测试上下文。

值得注意的是，Vulkan 后端在放弃（abandon）上下文时有特殊的处理顺序要求：`GrDirectContext::abandonContext()` 必须在 `VkTestContext` 被销毁之前调用（即"提前放弃"），这与其他后端不同。这是因为 Vulkan 设备资源的销毁依赖于设备对象的有效性。

本目录中还维护了 VkDebugUtilsMessenger 集成，用于在测试期间捕获和报告 Vulkan 验证层的错误信息，这对调试 GPU 问题非常有帮助。

所有代码受 `SK_VULKAN` 编译宏保护，仅在启用 Vulkan 支持时编译。

## 目录结构

```
tools/ganesh/vk/
├── BUILD.bazel          # Bazel 构建配置
├── VkTestContext.h      # Vulkan 测试上下文声明
└── VkTestContext.cpp    # Vulkan 测试上下文实现
```

## 关键类与函数

### VkTestContext
- **命名空间**: `sk_gpu_test`
- **基类**: `TestContext`
- **功能**: 封装 Vulkan GPU 上下文的测试基础设施
- **核心成员**:
  - `fVk` (`skgpu::VulkanBackendContext`) - Vulkan 后端上下文，包含 VkInstance、VkDevice 等
  - `fExtensions` (`const skgpu::VulkanExtensions*`) - 已启用的 Vulkan 扩展列表
  - `fFeatures` (`const sk_gpu_test::TestVkFeatures*`) - 测试用 Vulkan 设备特性
  - `fOwnsContext` (`bool`) - 标记是否拥有上下文的所有权
  - `fDebugMessenger` (`VkDebugUtilsMessengerEXT`) - Vulkan 调试消息回调
- **核心方法**:
  - `backend()` - 返回 `GrBackendApi::kVulkan`
  - `getVkBackendContext()` - 获取 Vulkan 后端上下文引用
  - `getVkExtensions()` - 获取 Vulkan 扩展信息
  - `getVkFeatures()` - 获取 Vulkan 设备特性

### CreatePlatformVkTestContext
- **签名**: `VkTestContext* CreatePlatformVkTestContext(VkTestContext* shareContext)`
- **功能**: 创建绑定到原生 Vulkan 库的平台 Vulkan 测试上下文
- **参数**: `shareContext` - 可选的共享上下文，用于上下文共享组

## 依赖关系

- **上游依赖**: `tools/ganesh/TestContext.h`（基类）
- **Vulkan 依赖**: `include/gpu/vk/VulkanBackendContext.h`、`tools/gpu/vk/VkTestUtils.h`、`tools/gpu/vk/VulkanDefines.h`
- **编译条件**: 需要定义 `SK_VULKAN`
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（通过 `ContextType::kVulkan` 使用）
- **特殊说明**: 在 NVIDIA GPU 上，GrContextFactory 会创建一个哨兵 GL 上下文以防止 Vulkan 设备销毁时挂起

## 使用注意事项

### Vulkan 验证层
在开发和测试模式下，Vulkan 后端默认启用验证层（Validation Layers）。验证层通过 `VkDebugUtilsMessengerEXT` 报告 API 使用错误和性能警告。如果测试中出现验证层错误，通常表示存在需要修复的 Vulkan API 调用问题。

### 上下文销毁顺序
Vulkan 后端对资源销毁顺序有严格要求。`GrContextFactory` 中的实现确保 Vulkan 上下文按照创建的逆序销毁，且 `abandonContext()` 在 `VkDevice` 销毁前被调用。违反此顺序可能导致 Vulkan 驱动崩溃或资源泄漏。

### NVIDIA GPU 兼容性
代码中包含了一个重要的兼容性措施：在 Vulkan 后端创建时，`GrContextFactory` 会同时创建一个"哨兵" GL 上下文（`fSentinelGLContext`）。这是因为在 NVIDIA GPU 上，如果没有活跃的 GL 上下文，Vulkan 设备的销毁偶尔会挂起，或在 TSAN 测试中运行极慢。

### 受保护内容支持
Vulkan 后端支持受保护内存分配（`VK_EXT_protected_memory`），可通过全局变量 `gCreateProtectedContext` 启用，用于 DRM 内容渲染测试。

## 相关文档与参考

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具函数
- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文数据结构
- `src/gpu/ganesh/vk/` - Ganesh Vulkan 后端核心实现
- `tools/graphite/vk/` - Graphite Vulkan 后端测试上下文（对比参考）
- Vulkan 规范: https://www.khronos.org/vulkan/
