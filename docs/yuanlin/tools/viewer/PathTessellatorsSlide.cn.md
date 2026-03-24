# PathTessellators - 路径细分可视化

> 源文件: `tools/viewer/PathTessellatorsSlide.cpp`

## 概述

PathTessellatorsSlide 是一个仅限 Ganesh GPU 的调试工具，以线框模式可视化路径细分器（tessellator）生成的三角形。支持 Wedge 和 Curve 两种 middle-out 细分模式，可交互拖动控制点。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

SamplePathTessellatorOp : GrDrawOp - 自定义 GPU 操作，直接使用 PathTessellator 绘制。支持 BreadcrumbTriangleList。

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
