# AnimatedRectsSlide

> 源文件: `tools/viewer/AnimatedRectsSlide.cpp`

## 概述

AnimatedRectsSlide 是一个高压力矩形绘制性能基准幻灯片，改编自 benchmarks.slaylines.io 在线基准测试。它绘制 32000 个重叠的矩形（描边+填充），所有矩形以不同速度从右向左滑动，到达左边缘后重新从右侧出现。

## 架构位置

属于 `tools/viewer` 模块，是纯矩形绘制的性能压力测试。

## 主要类与结构体

### AnimatedRects
- 继承自 `Slide`
- `AnimatedRect[32000]`: 每个矩形的 x、y、size、speed
- `fStrokePaint`: 黑色描边（宽度 2）
- `fFillPaint`: 白色填充
- 画布区域: 1000x639

## 公共 API 函数

- `load()`: 随机初始化 32000 个矩形
- `draw(SkCanvas*)`: 绘制所有矩形
- `animate(double)`: 按速度和帧间隔更新位置

## 内部实现细节

每帧对每个矩形绘制两次（描边+填充），总计 64000 次 `drawRect` 调用。矩形尺寸 10-50，速度 1-2。使用增量时间乘以 60 的缩放因子确保帧率无关的动画速度。

## 依赖关系

- `tools/timer/TimeUtils.h`: 时间工具
- `src/base/SkRandom.h`: 随机数

## 设计模式与设计决策

- **Web 基准移植**: 忠实再现 Web 性能基准的测试条件
- **极高对象数量**: 32000 个矩形压力测试批处理和绘制管线

## 性能考量

- 64000 次 drawRect 调用/帧，是 GPU 矩形绘制管线的极限测试
- 使用抗锯齿增加像素着色开销

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
