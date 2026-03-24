# ManyRects - 大量矩形绘制测试

> 源文件: `tools/viewer/ManyRectsSlide.cpp`

## 概述

ManyRectsSlide 每帧绘制 1000 个随机大小、位置和颜色的矩形，用于测试 GPU 绘制操作（draw op）合并效率。每个矩形都带有一个略大的裁剪矩形，给 GPU 操作合并代码增加额外挑战。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

ManyRectsSlide : Slide - 使用 SkRandom 生成随机矩形参数，注释中提到可选的旋转变换测试。

## 公共 API 函数

继承 Slide 或 ClickHandlerSlide 接口：`load()`, `draw()`, `animate()`, `onChar()`, `onFindClickHandler()` 等。

## 内部实现细节

详见概述和主要类描述中的实现说明。

## 依赖关系

- `tools/viewer/Slide.h` 或 `tools/viewer/ClickHandlerSlide.h` - 基类
- Skia 核心绘图 API（SkCanvas, SkPaint, SkPath 等）
- 部分幻灯片依赖 GPU 特定功能或第三方库

## 设计模式与设计决策

- 遵循 Viewer 幻灯片框架，通过 DEF_SLIDE 宏注册
- 交互式幻灯片使用 ClickHandlerSlide 的命中测试和拖拽机制
- 动画幻灯片覆写 animate() 方法实现基于时间的更新

## 性能考量

各幻灯片侧重于特定 Skia 功能的展示和测试，部分专门用于压力测试（如 MegaStroke、ManyRects、Chart）。

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类定义
- `tools/viewer/ClickHandlerSlide.h` - 可交互幻灯片基类
