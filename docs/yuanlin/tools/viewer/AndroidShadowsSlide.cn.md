# AndroidShadows - Android 风格阴影演示

> 源文件: `tools/viewer/AndroidShadowsSlide.cpp`

## 概述

ShadowsSlide 全面演示 SkShadowUtils 的各种功能，包括 11 种不同形状（矩形/圆角矩形/圆形/不规则/星形等）在不同高度和 3D 透视旋转下的阴影效果。支持环境光和聚光灯开关、路径操作裁剪动画、alpha 动画等。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

ShadowsSlide : Slide - 使用 pathops 实现 circular reveal 动画。Sk3DView 实现透视旋转。多种键盘快捷键控制阴影参数。

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
