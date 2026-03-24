# PathLerpSlide

> 源文件: `tools/viewer/PathLerpSlide.cpp`

## 概述

PathLerpSlide 实现了一个任意路径形态变换（morphing）的交互式演示。它扩展了 SkPath 内建的路径插值功能，允许在具有不同拓扑结构的两条路径之间进行平滑过渡动画。核心创新在于通过 t 值重采样将任意两条路径标准化为相同数量的三次贝塞尔曲线段，从而实现原本不支持的路径插值。

## 架构位置

属于 `tools/viewer` 模块，是 Viewer 应用中展示路径动画和几何算法的幻灯片。使用 ImGui 提供交互式控件。

## 主要类与结构体

### PathDesc
静态数据结构，包含路径名称和 SVG 字符串。预定义了 10 种路径（弧线、五边形、水滴、盾牌、螺旋、猫、兔子、鱼、乌龟等）。

### PathLerpSlide
- 继承自 `Slide`
- 核心成员:
  - `fPaths`: 当前动画的两条源路径
  - `fInterpolatedPath`: 插值结果路径
  - `fTimeMapper`: `SkCubicMap` 缓动曲线
  - `fPathTransform`: 路径到视口的变换矩阵
  - `fSelectedPaths[2]`: 指向 `gSamplePaths` 中选中路径的指针

## 公共 API 函数

- `load(SkScalar w, SkScalar h)`: 初始化路径和变换
- `resize(SkScalar w, SkScalar h)`: 窗口大小变化处理
- `draw(SkCanvas*)`: 绘制插值路径，可选显示顶点
- `animate(double)`: 驱动动画进度，调用 `generalInterpolate`
- `onChar(SkUnichar)`: 'v' 键切换顶点显示
- `onMouse(...)`: 底部区域悬停显示进度滑块

## 内部实现细节

### generalInterpolate 算法
这是本文件的核心算法，解决了两条拓扑不同的路径之间的插值问题：

1. **t 值提取**: `getTValues()` 使用 `SkPathMeasure` 计算每个路径段在总长度中的比例位置
2. **t 值合并**: `getTValuesToAdd()` 将两条路径的 t 值合并排序，确定需要在对方路径上添加的分割点
3. **路径重构**: `createPathFromTValues()` 将所有段转换为三次贝塞尔曲线，在需要的 t 值位置使用 `SkChopCubicAt` 分割
4. **标准插值**: 处理后的两条路径具有相同数量的段和类型，可直接调用 `SkPath::interpolate()`

### 路径标准化
所有路径先通过 SVG 字符串解析，再变换到统一的 512x512 标准化空间，确保不同路径占据相似大小。

### 动画系统
- 使用 `SkCubicMap` 实现缓动动画
- 进度在 0..1 间振荡
- 支持拖拽滑块手动控制进度，释放后自动续接时钟动画

### 顶点可视化
分别用红色（顶点）和蓝色（控制点）圆圈显示路径的控制结构，支持同时显示源路径和插值路径。

## 依赖关系

- `include/core/SkPathMeasure.h`: 路径长度测量
- `include/core/SkCubicMap.h`: 缓动曲线
- `include/utils/SkParsePath.h`: SVG 路径解析
- `src/core/SkGeometry.h`: `SkChopCubicAt` 贝塞尔分割
- `src/core/SkPathPriv.h`: 路径迭代器
- `imgui.h`: UI 控件

## 设计模式与设计决策

- **弧长参数化**: 使用路径弧长比例作为 t 值而非曲线参数 t，确保均匀的空间采样
- **全三次贝塞尔统一**: 将线段和二次贝塞尔提升为三次贝塞尔，简化后续的分割和插值逻辑
- **TODO**: 当前不支持多轮廓、圆锥段和闭合段

## 性能考量

- `generalInterpolate` 在每帧调用，涉及路径测量和重构，对复杂路径（如猫、兔子）可能较慢
- 路径分割使用 `SkChopCubicAt` 进行精确的贝塞尔细分，避免近似误差
- 注释建议将合成路径生成移至 `updateAnimatingPaths()` 中一次完成

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- `include/core/SkPath.h`: `isInterpolatable()` 和 `interpolate()` 方法
- `include/core/SkPathMeasure.h`: 路径测量 API
- `src/core/SkGeometry.h`: 贝塞尔曲线操作
