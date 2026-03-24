# RasterPipelineVizSlide 光栅管线可视化演示

> 源文件: `tools/viewer/RasterPipelineVizSlide.cpp`

## 概述

此文件实现了 Skia Viewer 中的光栅管线可视化 Slide（`RPVizSlide`），它提供了一种直观的方式来观察 Skia 光栅渲染管线（Raster Pipeline）中各阶段的中间数据。通过在管线中插入调试阶段（debug stages），将管线中流动的数据（坐标、颜色分量等）渲染为独立的面板图像，帮助开发者理解 Skia 光栅管线的内部工作原理。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 工具）
- 角色：渲染管线内部状态的调试可视化工具
- 依赖内部 API：`SkRasterPipelineVisualizer`（光栅管线可视化器）
- 基类：`ClickHandlerSlide`

## 主要类与结构体

### `RPVizSlide`
- 继承自 `ClickHandlerSlide`
- 名称：`"RasterPipelineViz"`
- 提供可拖拽的渐变端点控制

**核心字段：**
- `fStartDX/fStartDY`：渐变起始点坐标
- `fEndX/fEndY`：渐变终止点坐标
- `fOutputCornerX/fOutputCornerY`：输出面板位置

### `RPVizSlide::Click`（内部类）
自定义点击处理器，存储被拖拽端点的坐标指针。

## 公共 API 函数

| 方法 | 描述 |
|------|------|
| `draw(canvas)` | 执行完整的管线可视化绘制 |
| `onFindClickHandler(x, y, modi)` | 查找最近的渐变端点进行拖拽 |
| `onClick(click)` | 更新被拖拽端点的坐标 |

### 辅助函数
| 函数 | 描述 |
|------|------|
| `make_panel()` | 创建 100x100 的黑色面板位图 |
| `rgb(r, g, b)` | 创建 SkColor4f 颜色 |

## 内部实现细节

### 管线可视化流程
1. 创建一个彩虹色线性渐变着色器和 SkPaint
2. 使用 `DebugStageBuilder` 定义需要捕获的管线阶段：
   - 第 1 行：x 和 y 坐标（debug_x, debug_y）
   - 第 2 行：x 坐标
   - 第 3 行：x 坐标
   - 第 4 行：R、G、B、A 颜色分量（0-255）
3. 调用 `CreateBlitter` 创建带调试阶段的 blitter
4. 执行 `blitRect` 填充 100x100 区域
5. 将每个调试阶段的面板排列为网格显示
6. 在输出图像上绘制可拖拽的渐变端点手柄

### 布局参数
- `kPanelSize`：100 像素（面板尺寸）
- `kPadding`：10 像素（面板间距）
- `kBorder`：2 像素（面板边框）
- `kHandleRadius`：3 像素（拖拽手柄半径）

### 渐变配置
- 使用 6 色彩虹渐变（红、橙、黄、绿、蓝、紫）
- 混合模式为 `SkBlendMode::kSrc`
- 渐变端点可通过拖拽实时调整

### 调试阶段操作符
- `debug_x`：捕获管线中的 X 坐标
- `debug_y`：捕获管线中的 Y 坐标
- `debug_r_255`、`debug_g_255`、`debug_b_255`、`debug_a_255`：捕获颜色分量（映射到 0-255）

## 依赖关系

- Skia 核心：`SkCanvas`、`SkBitmap`、`SkImage`、`SkPaint`、`SkMatrix`
- Skia 内部：
  - `SkBlitter`、`SkCoreBlitters`：blitter 接口
  - `SkRasterPipelineOpList`：管线操作列表
  - `SkRasterPipelineVizualizer`：可视化器核心
  - `SkArenaAlloc`：栈内存分配器
- 渐变：`SkGradient`、`SkShaders::LinearGradient`
- Viewer 框架：`ClickHandlerSlide`

## 设计模式与设计决策

- **可视化调试模式**：通过在渲染管线中插入捕获节点来可视化中间数据，不影响最终输出
- **Builder 模式**：`DebugStageBuilder` 使用链式调用（`.add().add()`）构建调试阶段
- **交互式探索**：可拖拽的渐变端点允许实时观察管线在不同输入下的行为变化
- **注释引导**：代码中详细注释了自定义此 Slide 的步骤（5 步流程），方便开发者创建自己的管线可视化

## 性能考量

- 调试阶段的插入会增加管线执行的开销
- 每帧重新创建 blitter 和重新执行 blitRect，适合交互式探索但不适合性能敏感场景
- 使用 `SkSTArenaAlloc<1024>` 进行栈内存分配，减少堆分配开销
- 面板尺寸固定为 100x100，保持适中的可视化分辨率

## 相关文件

- `src/core/SkRasterPipelineVizualizer.h` - 管线可视化器内部实现
- `src/core/SkRasterPipelineOpList.h` - 管线操作定义
- `src/core/SkBlitter.h` - Blitter 接口
- `tools/viewer/ClickHandlerSlide.h` - Slide 基类
