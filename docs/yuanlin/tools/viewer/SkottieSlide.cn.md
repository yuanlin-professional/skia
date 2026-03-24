# SkottieSlide - Lottie 动画幻灯片

> 源文件:
> - [tools/viewer/SkottieSlide.h](../../../tools/viewer/SkottieSlide.h)
> - [tools/viewer/SkottieSlide.cpp](../../../tools/viewer/SkottieSlide.cpp)

## 概述

SkottieSlide 是 Skia Viewer 中用于播放和调试 Lottie 动画的幻灯片组件。它基于 Skottie（Skia 的 Lottie 动画引擎）实现动画加载、播放控制和交互式调试功能，支持动画属性检查和编辑。

## 架构位置

位于 `tools/viewer/` 目录下，继承 Slide 基类，集成 Skottie 动画引擎和 ImGui 调试界面到 Viewer 应用中。

## 主要类与结构体

### `SkottieSlide`
继承 Slide，管理 Skottie 动画实例的加载和播放。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `load/unload()` | 加载/卸载 Lottie JSON 文件 |
| `draw(SkCanvas*)` | 渲染当前帧 |
| `animate(double)` | 推进动画时间 |
| `onChar/onMouse()` | 处理交互输入 |

## 内部实现细节

- 使用 Skottie::Animation 解析和渲染 Lottie JSON。
- 集成 ImGui 提供动画属性的实时编辑界面。
- 支持动画时间轴控制和帧预览。

## 依赖关系

- **Skottie 模块**：Animation、AnimationBuilder
- **Viewer**：Slide 基类
- **ImGui**：调试界面

## 设计模式与设计决策

- **MVC 模式**：动画数据（Model）、渲染（View）和 UI 控制（Controller）分离。

## 性能考量

- Skottie 动画以 60fps 目标渲染。
- ImGui 叠加层仅在需要时绘制。

## 相关文件

- `modules/skottie/` - Skottie 动画引擎
- `tools/viewer/Slide.h` - Slide 基类
