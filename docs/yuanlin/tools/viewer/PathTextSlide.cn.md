# PathText - 路径文本性能测试

> 源文件: `tools/viewer/PathTextSlide.cpp`

## 概述

PathTextSlide 渲染 1500 个字形路径（从 52 个字母字形中选择），支持三种动画模式：静态（GlyphAnimator）、运动（MovingGlyphAnimator，多线程后台动画）和波浪（WavyGlyphAnimator，正弦波形变）。用于测试大量路径渲染和多线程动画性能。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

PathTextSlide/GlyphAnimator/MovingGlyphAnimator/WavyGlyphAnimator - 多态动画器层次。MovingGlyphAnimator 使用 SkTaskGroup 后台线程计算矩阵变换。WavyGlyphAnimator 使用 4 层正弦波叠加的水面效果变形路径控制点。

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
