# Skia Vulkan Android 头文件

> 源文件: `platform_tools/android/vulkan/Skia_Vulkan_Android.h`

## 概述

此头文件为 Android 平台上使用 Vulkan 图形 API 提供必要的平台特定宏定义和头文件引入。它是 Skia 在 Android 上使用 Vulkan 渲染后端的入口点配置文件。

## 架构位置

位于 Skia 的平台工具层 (`platform_tools/android/`)，属于 Android 平台特定的 Vulkan 集成部分。作为一个桥接头文件，它确保 Vulkan 的 Android 平台扩展被正确启用。

## 主要类与结构体

此文件不定义任何类或结构体，仅包含预处理器指令和头文件引用。

## 公共 API 函数

无公共 API 函数。此文件仅进行编译时配置。

## 内部实现细节

- 通过 `#if !defined(SK_BUILD_FOR_ANDROID)` 进行编译期平台检查，确保此头文件只在 Android 构建中使用
- 定义 `VK_USE_PLATFORM_ANDROID_KHR` 宏，启用 Vulkan 的 Android 平台扩展（如 `VkAndroidSurfaceCreateInfoKHR` 等）
- 使用 `IWYU pragma: export` 注释让 Include-What-You-Use 工具知道 `<vulkan/vulkan.h>` 应被传递导出
- 引入 `include/core/SkTypes.h` 以获取 `SK_BUILD_FOR_ANDROID` 宏定义

## 依赖关系

- `include/core/SkTypes.h` - Skia 核心类型定义
- `<vulkan/vulkan.h>` - Vulkan API 头文件（系统级）

## 设计模式与设计决策

采用条件编译守卫模式，通过编译时断言确保此头文件不会被误用在非 Android 平台上。将 `VK_USE_PLATFORM_ANDROID_KHR` 的定义放在 Vulkan 头文件引入之前，是 Vulkan 规范要求的标准做法。

## 性能考量

作为纯编译时头文件，不产生任何运行时开销。

## 相关文件

- `include/core/SkTypes.h`
- Skia Vulkan 后端相关源文件
