# ImGuiLayer - ImGui 集成层

> 源文件:
> - [tools/viewer/ImGuiLayer.h](../../../tools/viewer/ImGuiLayer.h)
> - [tools/viewer/ImGuiLayer.cpp](../../../tools/viewer/ImGuiLayer.cpp)

## 概述

ImGuiLayer 是 Skia Viewer 中将 Dear ImGui 即时模式 GUI 库集成到 sk_app::Window 的桥接层。它处理 ImGui 的输入事件转发、字体渲染和 Skia Canvas 绘制，并提供 `DragCanvas` 辅助类支持在 ImGui 控件中嵌入可拖拽的点。还支持在 ImGui 面板内嵌入自定义 Skia 绘图区域。

## 架构位置

位于 `tools/viewer/` 目录下，作为 sk_app::Window::Layer 实现叠加在窗口渲染管线中。为 Viewer 的调试面板、参数控制等 UI 功能提供基础。

## 主要类与结构体

### `ImGuiLayer`
继承 `sk_app::Window::Layer`，管理 ImGui 的生命周期和渲染。
- `fWindow` - 所属窗口
- `fFontPaint` - ImGui 字体绘制画笔
- `fSkiaWidgetFuncs` - 自定义 Skia 绘图回调数组

### `ImGui::DragCanvas`
ImGui 命名空间下的辅助结构，提供坐标变换和可拖拽点绘制。
- `fLocalToScreen` / `fScreenToLocal` - 坐标变换矩阵
- `dragPoint(SkPoint*)` - 创建可拖拽的控制点
- `fillColor()` - 填充背景色

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `setScaleFactor(float)` | 设置 HiDPI 缩放因子 |
| `skiaWidget(size, func)` | 注册自定义 Skia 绘图区域 |
| `onAttach/onPrePaint/onPaint(...)` | Window::Layer 生命周期回调 |
| `onMouse/onMouseWheel/onKey/onChar(...)` | 输入事件处理并转发给 ImGui |

## 内部实现细节

- **DragCanvas 坐标变换**：使用 `SkMatrix::setPolyToPoly` 在逻辑坐标和屏幕坐标之间映射。
- **拖拽点**：使用 ImGui 的 InvisibleButton（10x10 像素）实现可拖拽的控制点，限制在画布范围内。
- **输入转发**：将 sk_app 的输入事件转换为 ImGui 的 IO 事件。
- **Skia 绘图回调**：`skiaWidget` 注册的回调在 `onPaint` 时执行，在 SkSurface 上直接绘制。

## 依赖关系

- **ImGui**：imgui.h（Dear ImGui 库）
- **sk_app**：Window::Layer 基类
- **Skia 核心**：SkCanvas、SkSurface、SkMatrix、SkPaint

## 设计模式与设计决策

- **Layer 模式**：作为独立层叠加，与主渲染内容解耦。
- **RAII 画布**：DragCanvas 使用构造/析构管理 ImGui 状态（PushID/PopID）。
- **即时模式扩展**：通过 `skiaWidget` 在即时模式 GUI 中嵌入保留模式绘图。

## 性能考量

- ImGui 渲染开销通常很低。
- DragCanvas 的矩阵变换预计算，拖拽时仅需映射单个点。

## 相关文件

- `tools/viewer/Viewer.h` - 使用 ImGuiLayer 的主应用
- `third_party/imgui/` - ImGui 库
- `tools/sk_app/Window.h` - Layer 接口
