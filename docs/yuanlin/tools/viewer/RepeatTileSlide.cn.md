# RepeatTileSlide - 重复平铺着色器演示幻灯片

> 源文件: `tools/viewer/RepeatTileSlide.cpp`

## 概述

RepeatTileSlide 演示了 SkTileMode::kRepeat 平铺模式的位图着色器效果。它创建一个 100x100 的彩色条纹位图，将其设为重复平铺的着色器，并用 drawPaint 填充整个画布。

## 架构位置

位于 `tools/viewer/` 目录，属于 Viewer 基础功能演示幻灯片。

## 主要类与结构体

### `RepeatTileSlide : Slide`
简单的平铺效果演示。

## 内部实现细节

- `make_bitmap` 创建带红/绿/蓝/白交替竖线和顶部灰线的位图
- `make_paint` 用位图创建 kRepeat 平铺着色器
- 平移 (100,100) 后用 `drawPaint` 无限平铺

## 依赖关系

- `include/core/SkBitmap.h`, `SkShader.h`, `SkTileMode.h`

## 相关文件

- `tools/viewer/Slide.h` - 基类
