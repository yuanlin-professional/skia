# EdgeBuilderVizSlide

> 源文件: `tools/viewer/EdgeBuilderVizSlide.cpp`

## 概述

EdgeBuilderVizSlide 是一个边缘构建器可视化工具，展示 Skia 别名（aliased）扫描转换器将贝塞尔曲线路径分解为线段边缘的过程。它以 32 倍放大显示像素网格，叠加显示原始路径（红色高分辨率轮廓）和生成的边缘（橙色线段），支持拖拽控制点观察边缘变化。

## 架构位置

属于 `tools/viewer` 模块，继承自 `ZoomInSlide`。直接使用 `SkBasicEdgeBuilder` 和 `SkEdge` 内部类。

## 主要类与结构体

### EdgeBuilderSlide
- 继承自 `ZoomInSlide`
- `fControl`: 可拖拽的贝塞尔控制点
- 缩放: 32x，区域: 15x25 像素

## 公共 API 函数

- `drawUnderGrid(SkCanvas*)`: 在网格下绘制填充路径
- `drawOverGrid(SkCanvas*)`: 绘制高分辨率路径轮廓、边缘可视化和控制点
- `handleClick()`: 更新控制点位置

## 内部实现细节

`drawEdges()` 使用 `SkBasicEdgeBuilder::buildEdges()` 构建边缘列表，遍历每条边缘的所有线段（通过 `nextSegment()`），将 FixedPoint X 坐标转换为浮点绘制。Y 坐标在半像素位置绘制（`y + 0.5`）。零高度边缘添加 0.2 偏移使其可见。

## 依赖关系

- `src/core/SkEdge.h`: SkEdge 边缘结构
- `src/core/SkEdgeBuilder.h`: 边缘构建器
- `tools/viewer/ZoomInSlide.h`: 缩放基类

## 设计模式与设计决策

- **分层绘制**: 路径填充在网格下方，轮廓和边缘在网格上方
- **交互式探索**: 拖拽控制点实时观察边缘生成变化

## 性能考量

- 仅处理小区域路径（15x25 像素），开销极小

## 相关文件

- `src/core/SkEdgeBuilder.h`: 边缘构建器
- `src/core/SkScan_Path.cpp`: 使用这些边缘的扫描转换器
