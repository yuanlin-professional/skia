# Audio - 音频播放演示

> 源文件: `tools/viewer/AudioSlide.cpp`

## 概述

AudioSlide 演示 SkAudioPlayer 模块的使用，提供简单的音频播放控制界面，包括播放/暂停切换（空格键）和进度条拖拽（点击）。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

AudioSlide : ClickHandlerSlide - 使用 SkAudioPlayer::Make 创建播放器，通过 normalizedTime 控制进度条。

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
