# PatchSlide

> 源文件: `tools/viewer/PatchSlide.cpp`

## 概述

PatchSlide.cpp 包含两个幻灯片。`PatchSlide` 是一个交互式 Coons 面片（Patch）渲染演示，使用 12 个可拖拽控制点定义贝塞尔边界，在四种模式下（线框、纹理、颜色、纹理+颜色）绘制面片。`PseudoInkSlide` 是一个笔画模拟工具，将手绘路径转换为带宽度的三角带顶点网格。

## 架构位置

属于 `tools/viewer` 模块，演示 Skia 的顶点绘制（`SkVertices`）和面片插值能力。

## 主要类与结构体

### Patch 类
面片核心类，13 个控制点（12 + 首点重复）：
- `setPatch()`: 设置 12 个贝塞尔控制点
- `draw()`: 使用 `eval_sheet()` 双线性插值生成三角带网格
- 支持纹理坐标映射和颜色插值

### PatchSlide
- 继承自 `ClickHandlerSlide`
- 12 个控制点定义 4 条边界曲线
- 两行显示：图片着色器和渐变着色器

### PseudoInkSlide
- 继承自 `ClickHandlerSlide`
- 使用 `SkContourMeasure` 沿路径等距采样
- 在采样点两侧生成宽度为 30 的三角带

## 公共 API 函数

- `PatchSlide::draw()`: 四列显示（线框/纹理/颜色/纹理+颜色）
- `PseudoInkSlide::draw()`: 绘制 100 个偏移的笔画副本
- 点击拖拽交互

## 内部实现细节

### 面片插值算法
`eval_sheet()` 实现 Coons 面片的双线性插值：
- 先在四条边界上用三次贝塞尔求值（`eval_patch_edge`）
- 内部点通过边界值的双线性插值减去角点贡献计算

### 三角带生成
每行（`nv` 行中的一行）生成 `(nu+1)*2` 个顶点的三角带，包含位置、纹理坐标和颜色。

### 笔画模拟
`make_verts()` 使用 `SkContourMeasure::getMatrix()` 获取路径上每个采样点的切线矩阵，将法线方向的两个点（±width/2）映射到路径空间。

## 依赖关系

- `include/core/SkVertices.h`: 三角网格绘制
- `include/core/SkContourMeasure.h`: 轮廓测量
- `include/effects/SkGradient.h`: 渐变着色器
- `src/core/SkGeometry.h`: `SkEvalCubicAt` 贝塞尔求值

## 设计模式与设计决策

- **CPU 曲面细分**: 面片在 CPU 端完成细分和插值
- **四模式对比**: 同一面片在四种渲染模式下并排展示
- **笔画宽度**: PseudoInk 使用几何宽度而非描边宽度

## 性能考量

- 面片绘制使用 `SkVertices::MakeCopy`，每帧重建顶点缓冲区
- 10x10 细分产生约 200 个三角形
- PseudoInk 绘制 100 个副本测试顶点绘制吞吐量

## 相关文件

- `include/core/SkVertices.h`: 顶点绘制 API
- `include/core/SkContourMeasure.h`: 轮廓测量
