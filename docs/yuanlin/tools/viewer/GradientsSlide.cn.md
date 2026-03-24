# Gradients - 渐变色彩空间对比演示

> 源文件: `tools/viewer/GradientsSlide.cpp`

## 概述

GradientsSlide 使用 ImGui 控件展示线性渐变在 11 种不同色彩空间（Destination/sRGB/Linear sRGB/CIELAB/Oklab/LCH/Oklch/HSL/HWB 等）下的渲染差异。支持动态添加/删除颜色停靠点和调整色相插值方法。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

GradientsSlide : Slide - 使用 SkGradient::Interpolation 配置色彩空间和色相方法。ImGui 控件支持颜色编辑、抖动和预乘选项。

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
