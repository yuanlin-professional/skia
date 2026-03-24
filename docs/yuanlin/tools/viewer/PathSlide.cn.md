# Paths - 路径描边和几何体交互演示

> 源文件: `tools/viewer/PathSlide.cpp`

## 概述

PathSlide.cpp 包含多个路径相关的演示幻灯片：PathSlide（路径连接样式动画）、ArcToSlide（弧线连接和圆角效果）、FatStrokeSlide（粗笔画交互）。这些幻灯片展示了不同路径构造方式、笔画连接和端点样式，支持拖拽控制点交互。文件还包含三次贝塞尔曲线和路径边界计算的测试函数。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

PathSlide/ArcToSlide/FatStrokeSlide : ClickHandlerSlide - 支持拖拽控制点、切换描边样式、曲线/直线模式等交互。

## 公共 API 函数

继承 Slide 或 ClickHandlerSlide 接口。

## 内部实现细节

详见概述和主要类描述。

## 依赖关系

- `tools/viewer/Slide.h` - Slide 基类
- Skia 核心绘图 API

## 设计模式与设计决策

遵循 Viewer 幻灯片框架，通过 DEF_SLIDE 宏注册。

## 性能考量

作为演示/测试幻灯片，各幻灯片侧重于展示特定 Skia 功能的正确性和视觉效果。

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类
- `tools/viewer/ClickHandlerSlide.h` - 可交互幻灯片基类
