# MotionMarkSlide

> 源文件: `tools/viewer/MotionMarkSlide.cpp`

## 概述

MotionMarkSlide 是 WebKit MotionMark 基准测试套件在 Skia 中的 C++ 实现。它包含四个子测试：Canvas Lines（线段绘制）、Canvas Arcs（弧线绘制）、Paths（路径绘制）和 Bouncing Tagged Images（弹跳图像），用于评估 Skia 在典型 2D 图形工作负载下的渲染性能。

## 架构位置

属于 `tools/viewer` 模块，是性能基准测试幻灯片。通过 `DEF_SLIDE` 注册四个独立幻灯片。

## 主要类与结构体

### MMObject（抽象基类）
所有可绘制/可动画对象的接口。

### Stage（基类）
管理 `MMObject` 集合的舞台框架：
- 默认绘制/动画遍历所有对象
- +/- 键增减对象数量
- 子类实现 `createObject()` 工厂方法

### MotionMarkSlide
轻量级 Slide 包装器，将调用委托给 `Stage`。

### Canvas Lines 相关
- `CanvasLineSegment`: 从圆形分布的起点绘制振荡长度的线段
- `CanvasLineSegmentStage`: 管理 5000 个线段，绘制 4 个带渐变背景的圆形区域

### Canvas Arcs 相关
- `CanvasArc`: 绘制带有角度动画的弧线（描边或填充）
- `CanvasArcStage`: 管理 1000 个弧线
- 辅助函数: `canonicalize_angle()`, `adjust_end_angle()` 模拟 Chrome Canvas2D 角度处理

### Paths 相关
- `CanvasLinePoint`: 基础线段点，网格坐标系移动
- `CanvasQuadraticSegment`: 二次贝塞尔段
- `CanvasBezierSegment`: 三次贝塞尔段
- `CanvasLinePathStage`: 管理 5000 个路径段，随机组合线段、二次和三次曲线

### Bouncing Particles 相关
- `BouncingParticle`: 带速度、旋转和边界反弹的粒子
- `Rotater`: 旋转动画辅助类
- `BouncingTaggedImage`: 带变换矩阵的弹跳图像
- `BouncingTaggedImagesStage`: 管理 3000 个弹跳 YUV 图像

## 公共 API 函数

各子幻灯片通过 `load()` 初始化对应的 Stage：
- `CanvasLinesSlide`: `CanvasLineSegmentStage`
- `CanvasArcsSlide`: `CanvasArcStage`
- `PathsSlide`: `CanvasLinePathStage`
- `BouncingTaggedImagesSlide`: `BouncingTaggedImagesStage`

## 内部实现细节

### Chrome Canvas2D 兼容性
弧线处理函数严格匹配 Chrome 的角度标准化和调整逻辑，确保测试结果可与 WebKit 版本比较。

### 时间系统
- `time_counter_value`: 纳秒转周期值
- `time_fractional_value`: 纳秒转 0-1 周期小数
- 弹跳粒子使用增量时间

### YUV 图像加载
`BouncingTaggedImagesStage` 使用 `LazyYUVImage` 加载 YUV 格式图像，支持 Ganesh 和 Graphite 后端。

## 依赖关系

- `include/effects/SkGradient.h`: 线性渐变
- `src/base/SkRandom.h`: 随机数生成
- `tools/gpu/YUVUtils.h`: YUV 图像加载

## 设计模式与设计决策

- **模板方法模式**: Stage 定义框架，子类实现 `createObject()`
- **动态对象池**: +/- 键允许运行时调整对象数量
- **忠实移植**: 参照 WebKit MotionMark JS 源码，保持算法一致性

## 性能考量

- Canvas Lines: 默认 5000 条线段，每帧动画振荡长度
- Canvas Arcs: 默认 1000 条弧线，每帧更新角度
- Paths: 默认 5000 段路径，随机拆分和颜色变化
- Bouncing Images: 默认 3000 个带旋转的 YUV 图像
- 所有测试均使用抗锯齿绘制

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- `tools/gpu/YUVUtils.h`: YUV 图像工具
- WebKit MotionMark: https://github.com/WebKit/MotionMark
