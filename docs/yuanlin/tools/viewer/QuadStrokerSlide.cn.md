# QuadStrokerSlide

> 源文件: `tools/viewer/QuadStrokerSlide.cpp`

## 概述

QuadStrokerSlide 是一个交互式描边（Stroke）算法可视化工具，允许用户拖拽控制点来实时调整三次贝塞尔、圆锥曲线、二次贝塞尔、圆弧、圆角矩形、圆形和文本路径的描边效果。它同时显示原始骨架线、描边后的线框轮廓和像素级放大视图，是调试 Skia 描边引擎的重要工具。

## 架构位置

属于 `tools/viewer` 模块，继承自 `ClickHandlerSlide`。是 Skia 描边算法（`SkStroke`）的深度调试和可视化工具。

## 主要类与结构体

### QuadStrokerSlide
- 继承自 `ClickHandlerSlide`
- 18 个可拖拽控制点（分别用于 7 种形状）
- 4 个滑块控件: weight、radius、error、width
- 7 个形状开关按钮: C(三次)、K(圆锥)、Q(二次)、A(圆弧)、R(圆角矩形)、O(圆形)、T(文本)

### StrokeTypeButton / CircleTypeButton
按钮结构体，存储边界、标签字符和启用状态。

### MyClick
自定义点击类，索引区分控制点和按钮。

## 公共 API 函数

- `load/resize`: 布局控件位置
- `draw(SkCanvas*)`: 绘制所有启用的形状和控件
- `onChar(SkUnichar)`: 文本模式下的字符输入
- `onFindClickHandler/onClick`: 处理控制点和按钮交互

## 内部实现细节

### 描边可视化管线
1. `draw_stroke()`: 核心绘制函数
   - 在微型 Surface 上绘制描边路径
   - 放大到像素级网格视图（`copyMinToMax`）
   - 以蓝色绘制原始骨架线
   - 使用 `skpathutils::FillPathWithPaint` 获取描边轮廓
   - 以红色半透明绘制线框

### 辅助可视化
- `draw_ribs()`: 沿路径等间距绘制法线"肋骨"
- `draw_t_divs()`: 按参数 t 等间距绘制法线
- `draw_points()`: 显示控制点和路径点

### 像素放大
使用缩放矩阵和离屏 Surface 实现像素级放大：
- `fMinSurface`: 原始尺寸渲染
- `fMaxSurface`: 放大后显示（带网格线）
- 棋盘格着色器作为背景

### 圆弧中心计算
`arcCenter()` 通过计算两个法线的交点确定弧线中心，用于圆形填充可视化。

## 依赖关系

- `src/core/SkStroke.h`: 描边引擎（调试变量 `gDebugStrokerError`）
- `src/core/SkGeometry.h`: 贝塞尔曲线求值
- `include/core/SkPathMeasure.h`: 路径测量
- `include/core/SkPathUtils.h`: `FillPathWithPaint` 描边轮廓提取
- `tools/viewer/ClickHandlerSlide.h`: 可点击幻灯片基类

## 设计模式与设计决策

- **交互式调试**: 直接拖拽控制点，实时观察描边结果变化
- **多级可视化**: 骨架、描边轮廓、法线、像素网格多层叠加
- **模式切换**: 7 种几何模式独立启用，便于聚焦测试

## 性能考量

- 离屏渲染和放大操作增加了绘制开销
- 适合交互式调试而非性能测试
- 宽度动画模式自动在 1-100 范围振荡

## 相关文件

- `src/core/SkStroke.h/cpp`: Skia 描边引擎实现
- `tools/viewer/ClickHandlerSlide.h`: 可点击基类
