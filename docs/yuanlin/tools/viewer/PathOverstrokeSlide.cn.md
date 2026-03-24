# PathOverstroke - 路径过度描边可视化

> 源文件: `tools/viewer/PathOverstrokeSlide.cpp`

## 概述

OverstrokeSlide 演示不同路径类型（二次曲线、三次曲线、矩形、线性半圆）在大笔画宽度下的描边效果，支持交互式调整笔画宽度、路径类型、闭合状态和填充路径显示。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

OverstrokeSlide : Slide - 支持键盘控制（逗号/点号调宽度，x切换类型，c切换闭合，f切换填充路径，D转储十六进制）。提供 quadPath/cubicPath/linSemicirclePath/rectPath 四种路径生成器。

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
