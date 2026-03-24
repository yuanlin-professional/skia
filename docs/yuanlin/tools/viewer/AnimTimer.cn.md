# AnimTimer - 动画定时器

> 源文件: `tools/viewer/AnimTimer.h`

## 概述

AnimTimer 是一个动画定时器类，支持三种状态：停止(stopped)、暂停(paused)和运行(running)。提供可变播放速度控制，调用者必须手动调用 updateTime() 同步时钟。设计确保同一帧内多次查询返回一致的时间值。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

AnimTimer - 维护 fPreviousNanos/fElapsedNanos/fSpeed/fState 四个状态。run() 支持从停止启动和从暂停恢复。

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
