# AnimBlur - 动画模糊效果演示

> 源文件: `tools/viewer/AnimBlurSlide.cpp`

## 概述

AnimBlurSlide 演示四种模糊样式（Normal/Inner/Solid/Outer）的动态效果，模糊半径和圆形半径随时间正弦振荡。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

AnimBlurSlide : Slide - 使用 get_anim_sin 辅助函数生成基于时间的正弦动画值。

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
