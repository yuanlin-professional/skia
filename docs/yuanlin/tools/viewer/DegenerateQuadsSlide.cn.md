# DegenerateQuadsSlide

> 源文件: `tools/viewer/DegenerateQuadsSlide.cpp`

## 概述

DegenerateQuadsSlide 是一个 Ganesh GPU 后端的退化四边形（Degenerate Quad）AA 覆盖率可视化工具。它展示了三种不同的覆盖率计算方法（面积法、边距离法、GPU 网格法）在处理可能退化的四边形时的行为差异，用于调试 `GrQuadPerEdgeAA` 的正确性。

## 架构位置

属于 `tools/viewer` 模块，仅在 `SK_GANESH` 编译时可用。直接使用 Ganesh 内部的 `GrQuad` 和 `QuadPerEdgeAA` API。

## 主要类与结构体

### DegenerateQuadSlide
- 继承自 `ClickHandlerSlide`
- 4 个可拖拽角点（`fCorners`）
- 4 个边缘 AA 开关（`fEdgeAA`，1-4 键切换）
- 3 种覆盖率模式（q/w/e 键切换）

### CoverageMode 枚举
- `kArea`: 面积法 - 使用 `SkPathOps` 计算四边形与像素的交集面积
- `kEdgeDistance`: 边距离法 - 使用有符号距离函数计算覆盖率
- `kGPUMesh`: GPU 网格法 - 使用 `QuadPerEdgeAA::Tessellator` 的实际输出

## 公共 API 函数

- `draw(SkCanvas*)`: 渲染覆盖率热图和四边形轮廓
- `onChar(SkUnichar)`: 1-4 切换边 AA，q/w/e 切换模式
- `onFindClickHandler/onClick`: 拖拽角点

## 内部实现细节

### 覆盖率计算方法

**面积法** (`get_area_coverage`):
- 使用 `SkPathOps::Op(kIntersect)` 计算四边形与像素方块的交集
- Shoelace 公式计算交集多边形面积
- 非 AA 边外侧的像素覆盖率为 0

**边距离法** (`get_edge_dist_coverage`):
- 为每条边生成内缩和外扩线
- 计算像素到外扩线的有符号距离
- 取所有边距离的最小值作为覆盖率
- 处理反转四边形（使用内缩线替代）

**GPU 网格法** (`get_framed_coverage`):
- 使用 `QuadPerEdgeAA::Tessellator` 生成实际的 GPU 三角网格
- 通过重心坐标插值计算覆盖率
- 考虑几何域（geometric domain）约束

### 三角形点内测试
`inside_triangle()` 使用有符号距离和重心坐标判断点是否在三角形内，处理了顺时针/逆时针两种绕序。

### 可视化
- 100x 缩放显示（`kViewScale = 100`）
- 灰度表示覆盖率（白=0, 黑=1）
- 像素中心标记（绿=非零覆盖率, 红=零覆盖率）
- 虚线显示内缩/外扩线
- 凸性检测（非凸时显示红色轮廓）

## 依赖关系

- `src/gpu/ganesh/geometry/GrQuad.h`: Ganesh 四边形表示
- `src/gpu/ganesh/ops/QuadPerEdgeAA.h`: 逐边 AA 曲面细分
- `include/pathops/SkPathOps.h`: 路径布尔运算
- `include/effects/SkDashPathEffect.h`: 虚线效果

## 设计模式与设计决策

- **三重验证**: 面积法作为理论基准，边距离法和 GPU 网格法用于比较
- **退化处理**: 支持非凸、反转等退化四边形的正确可视化
- **逐像素分析**: 每帧遍历所有像素计算覆盖率

## 性能考量

- 面积法使用路径布尔运算，每像素一次，非常慢
- GPU 网格法需要 CPU 端模拟 GPU 的三角细分和重心插值
- 仅用于调试目的，渲染区域较小（约 8x8 个像素）

## 相关文件

- `src/gpu/ganesh/ops/QuadPerEdgeAA.h/cpp`: 核心 AA 实现
- `src/gpu/ganesh/geometry/GrQuad.h`: GrQuad 类型
- `tools/viewer/ClickHandlerSlide.h`: 可点击基类
