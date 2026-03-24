# ArcSlide

> 源文件: `tools/viewer/ArcSlide.cpp`

## 概述

ArcsSlide 是一个弧线绘制演示幻灯片，展示 `SkCanvas::drawArc` API 在不同起始角度和扫过角度组合下的渲染效果。它包含一个持续旋转的动画弧线和一组静态的弧线参考示例。

## 架构位置

属于 `tools/viewer` 模块，是基础 2D 图元绘制 API 的演示幻灯片。

## 主要类与结构体

### MyDrawable（内部类）
- 继承自 `SkDrawable`
- 绘制四种样式的弧线:
  1. 蓝色半透明填充扇形（useCenter=true）
  2. 绿色半透明填充弧线（useCenter=false）
  3. 红色描边扇形
  4. 蓝色发丝线弧线

### ArcsSlide
- `fAnimatingDrawable`: 可动画的弧线
- `fRootDrawable`: 通过 `SkPictureRecorder` 录制的静态内容

## 公共 API 函数

- `load()`: 创建动画弧线，将静态内容录制为 `SkDrawable`
- `draw(SkCanvas*)`: 绘制根 Drawable
- `animate(double nanos)`: 更新弧线扫过角度（24 秒一周期）

## 内部实现细节

### 静态弧线参考
`DrawArcs()` 绘制 9 组不同角度的弧线:
- (0, 360), (0, 45), (0, -45), (720, 135)
- (-90, 269), (-90, 270), (-90, 271)
- (-180, -270), (225, 90)

每组弧线带有矩形边框和对角线辅助线，以及角度标签。

### 动画机制
动画弧线的扫过角度由时间驱动: `angle = (nanos * 360 / 24) mod 360`。

### PictureRecorder 优化
使用 `SkPictureRecorder` 将静态内容录制一次，避免每帧重建。

## 依赖关系

- `include/core/SkDrawable.h`: 可绘制对象
- `include/core/SkPictureRecorder.h`: 图片录制
- `include/effects/Sk1DPathEffect.h`, `SkCornerPathEffect.h`: 路径效果
- `include/utils/SkParsePath.h`: SVG 路径解析

## 设计模式与设计决策

- **录制重放**: 静态内容录制为 Drawable，只创建一次
- **全面角度测试**: 覆盖正/负角度、超过 360 度、边界值（269/270/271）等边界情况

## 性能考量

- 使用 PictureRecorder 避免重复构建静态内容
- 动画弧线使用 `notifyDrawingChanged()` 触发最小化重绘

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- `include/core/SkCanvas.h`: drawArc API
