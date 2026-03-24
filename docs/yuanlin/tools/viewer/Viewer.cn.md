# Viewer - Skia 交互式查看器应用

> 源文件:
> - [tools/viewer/Viewer.h](../../../tools/viewer/Viewer.h)
> - [tools/viewer/Viewer.cpp](../../../tools/viewer/Viewer.cpp)

## 概述

Viewer 是 Skia 最重要的交互式演示和调试应用程序。它集成了 GM 测试、SKP 文件回放、Lottie 动画、SVG 渲染等多种幻灯片类型，提供了丰富的 GPU 后端切换、颜色空间配置、性能统计和实时参数调整功能。通过 ImGui 界面提供完整的调试工具，是 Skia 开发者最常用的视觉调试工具。

## 架构位置

位于 `tools/viewer/` 目录下，是 Skia 工具生态中最复杂的应用程序。它建立在 sk_app::Window 之上，整合了幻灯片系统、ImGui 层、统计层、GPU 后端管理等多个子系统。

## 主要类与结构体

### `Viewer`
继承 `sk_app::Application`，是 Viewer 应用的核心类。管理幻灯片集合、渲染配置、输入事件分发和 ImGui 界面。

## 公共 API 函数

Viewer 主要通过 sk_app::Application 生命周期和 Window::Layer 回调工作，包含大量内部方法管理幻灯片切换、后端配置、统计显示等。

## 内部实现细节

- **幻灯片管理**：加载 GM、SKP、MSKP、SVG、Skottie 等多种类型的幻灯片。
- **后端切换**：运行时在 GL、Vulkan、Metal、Dawn、Raster 等后端间切换。
- **ImGui 集成**：提供颜色空间选择、MSAA 配置、缩放控制等参数面板。
- **统计覆盖**：实时显示帧率、GPU 时间、内存使用等性能指标。
- **键盘快捷键**：丰富的键盘快捷键用于幻灯片切换、缩放、旋转等。

## 依赖关系

- **sk_app**：Window、Application
- **Viewer 组件**：Slide、ImGuiLayer、StatsLayer
- **渲染后端**：所有支持的 GPU/Raster 后端
- **模块**：Skottie、sksg

## 设计模式与设计决策

- **Layer 架构**：通过 Window::Layer 叠加多个功能层（Slide、ImGui、Stats）。
- **幻灯片抽象**：统一的 Slide 接口支持各种内容类型。
- **运行时配置**：几乎所有渲染参数都可在运行时动态调整。

## 性能考量

- 支持 FPS 统计和 GPU 计时器。
- 可选的 MSAA、HDR 等高开销功能。
- 幻灯片按需加载/卸载。

## 相关文件

- `tools/viewer/Slide.h` - 幻灯片基类
- `tools/viewer/ImGuiLayer.h` - ImGui 集成层
- `tools/sk_app/Window.h` - 窗口框架
