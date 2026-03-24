# Mesh - 网格顶点动画演示

> 源文件: `tools/viewer/MeshSlide.cpp`

## 概述

MeshSlide 展示各种纹理映射到可变形网格上的效果。支持多种着色器（Mandrill图像、渐变等）和顶点动画器（Cylinderator/Squircillator/Twirlinator/Wigglynator）。使用 ImGui 控件和 SkCubicMap 缓动函数。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

MeshSlide : Slide - NxN 均匀网格生成（4x4到128x128），三角化为交替方向的三角形对。使用 SkVertices::MakeCopy 每帧重建顶点。

## 公共 API 函数

继承 Slide 接口：`load()`, `draw()`, `animate()`, `onChar()` 等。

## 内部实现细节

详见源文件中的具体实现逻辑。

## 依赖关系

- `tools/viewer/Slide.h` - Slide 基类
- Skia 核心绘图 API

## 设计模式与设计决策

- 继承 Slide 或 ClickHandlerSlide 框架，遵循 Viewer 的幻灯片注册机制（DEF_SLIDE 宏）

## 性能考量

作为交互式演示幻灯片，优先保证视觉效果和交互响应性。

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类
- `tools/viewer/ClickHandlerSlide.h` - 可点击幻灯片基类
