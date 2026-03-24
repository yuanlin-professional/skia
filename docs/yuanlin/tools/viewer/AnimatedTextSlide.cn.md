# AnimatedText - 动画文本缓存测试

> 源文件: `tools/viewer/AnimatedTextSlide.cpp`

## 概述

AnimatedTextSlide 通过动态缩放和旋转文本来测试位图/距离场字体缓存行为。渲染不同大小的 Hamburgefons 文本，带有随机噪声的动画参数防止缓存进入稳态。支持 2x 缩放切换以测试 SDF 特殊路径。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

AnimatedTextSlide : Slide - 缩放在 1.0-2.0 之间振荡，旋转持续增加。

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
