# ganesh_vulkan

> 源文件: example/external_client/src/ganesh_vulkan.cpp

## 概述

ganesh_vulkan 是一个 Ganesh Vulkan 后端的简化编译测试示例。该程序故意省略了实际的 Vulkan 初始化代码,主要目的是验证构建系统能正确链接 Vulkan 相关的 API。程序会失败运行(因为未正确设置 Vulkan 上下文),但应该能成功编译和链接。

## 主要特点

- **编译测试**: 验证头文件和库链接
- **不完整实现**: VkInstance/VkDevice 设为 NULL
- **预期失败**: `GrDirectContexts::MakeVulkan()` 会返回 nullptr
- **占位符代码**: 包含完整的绘制流程供参考

## 代码结构

```cpp
skgpu::VulkanBackendContext backendContext;
backendContext.fInstance = VK_NULL_HANDLE;  // 未初始化
backendContext.fDevice = VK_NULL_HANDLE;    // 未初始化
sk_sp<GrDirectContext> ctx = GrDirectContexts::MakeVulkan(backendContext);
if (!ctx) { return 1; }  // 总是会失败
```

## 用途

- 测试构建配置
- 作为 VulkanBasic.cpp 的简化版本
- 展示 Vulkan API 的最小引用

## 相关文件
- VulkanBasic.cpp: 完整的 Vulkan 示例
- ganesh_metal.cpp: Metal 后端对比
