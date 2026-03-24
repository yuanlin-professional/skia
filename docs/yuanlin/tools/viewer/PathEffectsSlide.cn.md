# PathEffects - 路径效果动画演示

> 源文件: `tools/viewer/PathEffectsSlide.cpp`

## 概述

PathEffectSlide 展示 SkPathEffect 的组合使用，包括 SkCornerPathEffect（圆角）、Sk1DPathEffect（路径重复）及其 Compose 组合。路径效果的 phase 参数随时间动画化，呈现沿路径移动的装饰效果。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

PathEffectSlide : Slide - 展示三种配置：单独路径重复、组合圆角+路径重复、以及 Morph 样式的路径扭曲效果。

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
