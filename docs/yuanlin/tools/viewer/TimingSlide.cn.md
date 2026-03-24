# TimingSlide

> 源文件: `tools/viewer/TimingSlide.cpp`

## 概述

TimingSlide 是一个性能分析演示幻灯片，通过逐像素测量 `drawImageRect` 调用的耗时，以可视化热图的方式展示图像渲染中各像素的绘制开销分布。它帮助开发者直观理解哪些像素区域的渲染代价更高。

## 架构位置

属于 `tools/viewer` 模块，是用于渲染性能诊断的工具幻灯片。

## 主要类与结构体

### TimingSlide
- 继承自 `Slide`
- 成员:
  - `fImg`: 预渲染的文本图像（24x16 像素）
  - `W = 24, H = 16`: 图像尺寸常量

## 公共 API 函数

- `load(SkScalar w, SkScalar h)`: 创建一个包含 "abc" 文本的小位图
- `draw(SkCanvas* canvas)`: 执行计时测量并可视化结果

## 内部实现细节

### 绘制流程（四行显示）
1. **原始图像**: 直接以 8x 缩放绘制原始图像
2. **逐像素计时（直接渲染）**: 对每个像素调用 `drawImageRect(1x1 -> 1x1)`，使用 `std::chrono::steady_clock` 精确计时，将耗时映射为 alpha 值绘制热图
3. **离屏计时**: 在离屏 Surface 中对每个像素调用 `drawImageRect(1x1 -> 1024x1024)`，测量放大绘制的开销
4. 两种热图均将最快像素映射为完全透明，最慢像素映射为完全不透明

### 归一化方法
使用 `(cost - min) / (max - min)` 将耗时线性映射到 [0, 1] 区间，作为每个像素的 alpha 值。

## 依赖关系

- `include/core/SkCanvas.h`: 画布操作
- `include/core/SkSurface.h`: 离屏渲染
- `<chrono>`: 高精度计时

## 设计模式与设计决策

- **微基准可视化**: 将性能测量结果直接转换为可视图形，而非仅输出数字
- **SrcRectConstraint**: 使用 `kStrict_SrcRectConstraint` 确保精确的子图像采样
- **对比分析**: 同时展示直接渲染和离屏放大渲染的开销差异

## 性能考量

- 每帧执行 24*16*2 = 768 次 `drawImageRect` 调用并逐一计时，本身开销较大
- 离屏渲染版本将 1x1 像素放大到 1024x1024，测试纹理采样开销
- 仅适合在调试/分析场景使用，不适合生产渲染

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- `tools/timer/Timer.h`: Skia 计时工具
