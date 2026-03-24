# GraphiteVulkanWindowContext_win - Windows Graphite Vulkan 窗口上下文

> 源文件: `tools/window/win/GraphiteVulkanWindowContext_win.cpp`

## 概述

此文件实现了 Windows 平台上 Graphite 渲染后端使用 Vulkan 图形 API 的窗口上下文工厂函数 `MakeGraphiteVulkanForWin`。它负责加载 Vulkan 库、创建 Win32 窗口表面（VkSurface）以及验证物理设备的呈现能力，最终创建一个可用于 Graphite 渲染的 Vulkan 窗口上下文。

## 架构位置

该文件是 Skia 窗口工具的平台特定实现层：
- 属于 `skwindow` 命名空间
- 提供工厂函数，实例化 `GraphiteVulkanWindowContext`
- 桥接 Windows 窗口系统（HWND）与 Vulkan/Graphite 渲染管线

## 主要类与结构体

本文件不定义新类，而是提供工厂函数。核心使用的类包括：
- `internal::GraphiteVulkanWindowContext` - 被实例化的窗口上下文
- `WindowContext` - 工厂函数返回的基类指针

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGraphiteVulkanForWin(HWND, unique_ptr<const DisplayParams>)` | 创建 Windows Graphite Vulkan 窗口上下文 |

## 内部实现细节

1. **Vulkan 库加载**: 调用 `sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs` 获取 `vkGetInstanceProcAddr`
2. **创建 VkSurface 的 Lambda**: 使用 `vkCreateWin32SurfaceKHR` 创建 Win32 特定的 Vulkan 表面
   - 通过 `VkWin32SurfaceCreateInfoKHR` 结构体传递 HWND 和 HINSTANCE
   - 使用 `static` 局部变量缓存函数指针，避免重复查找
3. **呈现能力检查 Lambda**: 使用 `vkGetPhysicalDeviceWin32PresentationSupportKHR` 验证队列族的呈现支持
4. **上下文验证**: 创建后检查 `isValid()`，无效则返回 `nullptr`

## 依赖关系

- `tools/window/win/WindowContextFactory_win.h` - 工厂函数声明
- `tools/sk_app/win/Window_win.h` - Windows 窗口类
- `tools/window/GraphiteNativeVulkanWindowContext.h` - Graphite Vulkan 上下文
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具
- `<Windows.h>` - Win32 API

## 设计模式与设计决策

- **工厂方法模式**: 通过 `MakeGraphiteVulkanForWin` 封装对象创建的复杂性
- **Lambda 回调**: 将平台特定的 VkSurface 创建和呈现检查封装为回调，传递给平台无关的上下文类
- **延迟查找**: Vulkan 函数指针使用 `static` 局部变量按需加载并缓存
- **RAII**: 使用 `unique_ptr` 管理窗口上下文的生命周期

## 性能考量

- Vulkan 函数指针使用静态变量缓存，仅在首次调用时查找
- 工厂函数在初始化时调用，不影响渲染帧率
- 如果 Vulkan 库不可用，快速返回 `nullptr` 避免不必要的初始化

## 相关文件

- `tools/window/win/VulkanWindowContext_win.cpp` - Ganesh Vulkan 对应实现
- `tools/window/GraphiteNativeVulkanWindowContext.h` - 跨平台 Graphite Vulkan 上下文
- `tools/window/win/WindowContextFactory_win.h` - Windows 工厂函数声明
