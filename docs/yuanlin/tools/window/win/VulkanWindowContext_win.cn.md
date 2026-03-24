# VulkanWindowContext_win - Windows Ganesh Vulkan 窗口上下文

> 源文件: `tools/window/win/VulkanWindowContext_win.cpp`

## 概述

此文件实现了 Windows 平台上基于 Ganesh 渲染后端的 Vulkan 窗口上下文工厂函数 `MakeVulkanForWin`。它与 `GraphiteVulkanWindowContext_win.cpp` 结构几乎相同，但目标是创建 Ganesh（而非 Graphite）后端的 Vulkan 窗口上下文。函数负责 Vulkan 库加载、Win32 表面创建和呈现能力验证。

## 架构位置

该文件位于 Skia 窗口工具的 Windows 平台实现层：
- 属于 `skwindow` 命名空间
- 使用 Ganesh 后端的 `internal::VulkanWindowContext` 类
- 与 Graphite Vulkan 变体（`GraphiteVulkanWindowContext_win`）平行

## 主要类与结构体

本文件不定义新类，使用：
- `internal::VulkanWindowContext` - Ganesh Vulkan 窗口上下文
- `WindowContext` - 返回的基类类型

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeVulkanForWin(HWND, unique_ptr<const DisplayParams>)` | 创建 Windows Ganesh Vulkan 窗口上下文 |

## 内部实现细节

实现流程与 Graphite 版本完全一致：
1. 通过 `sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs` 加载 Vulkan 并获取入口点
2. 定义 `createVkSurface` lambda，使用 `vkCreateWin32SurfaceKHR` 创建 Win32 Vulkan 表面
3. 定义 `canPresent` lambda，使用 `vkGetPhysicalDeviceWin32PresentationSupportKHR` 检测呈现支持
4. 实例化 `VulkanWindowContext`（非 Graphite 版本），传入回调和参数
5. 验证上下文有效性

关键区别在于：
- 引用 `tools/window/VulkanWindowContext.h`（Ganesh 版本）
- 额外包含 `src/gpu/ganesh/vk/GrVkUtil.h`
- 创建的是 `internal::VulkanWindowContext` 实例

## 依赖关系

- `tools/window/win/WindowContextFactory_win.h` - 工厂函数声明
- `tools/window/VulkanWindowContext.h` - Ganesh Vulkan 上下文基类
- `src/gpu/ganesh/vk/GrVkUtil.h` - Ganesh Vulkan 工具
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具
- `<Windows.h>` - Win32 API

## 设计模式与设计决策

- **工厂方法模式**: 封装 Vulkan 上下文创建的平台特定逻辑
- **Lambda 回调注入**: 将平台相关的表面创建和呈现检查逻辑注入平台无关上下文
- **Ganesh/Graphite 并行架构**: 与 Graphite 版本保持相同的代码结构，便于维护

## 性能考量

- 静态变量缓存 Vulkan 函数指针，减少重复的符号查找
- 初始化阶段一次性开销，不影响运行时性能

## 相关文件

- `tools/window/win/GraphiteVulkanWindowContext_win.cpp` - Graphite 版本对应实现
- `tools/window/VulkanWindowContext.h` - Ganesh Vulkan 上下文基类
- `tools/window/win/WindowContextFactory_win.h` - Windows 工厂函数声明
