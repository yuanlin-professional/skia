# MaterialShadows - Material Design 阴影演示

> 源文件: `tools/viewer/MaterialShadowsSlide.cpp`

## 概述

MaterialShadowsSlide 展示 Material Design 风格阴影在不同高度（1/3/6/8/12/24 dp）和不同形状（圆形/胶囊/大圆角矩形/小圆角矩形）下的渲染效果。使用定向光源和 SkShadowUtils 绘制。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

MaterialShadowsSlide : Slide - 使用 kDirectionalLight_ShadowFlag，环境阴影 alpha=0.05，聚光阴影 alpha=0.35。

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
