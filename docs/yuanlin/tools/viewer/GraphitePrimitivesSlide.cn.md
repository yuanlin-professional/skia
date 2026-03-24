# GraphitePrimitivesSlide

> 源文件: `tools/viewer/GraphitePrimitivesSlide.cpp`

## 概述

GraphitePrimitivesSlide 是一个高级渲染演示幻灯片，用于可视化 Graphite 后端渲染圆角矩形（RRect）时的内部三角形网格生成过程。它展示了 GPU 渲染管线中如何将圆角矩形分解为带抗锯齿的三角带，包括外部 AA 外扩、中心描边、内部 AA 内缩和中心填充四个层次的顶点布局。

## 架构位置

属于 `tools/viewer` 模块，是 Graphite GPU 渲染管线的算法可视化工具。它模拟了 Graphite 着色器中的顶点计算逻辑，帮助开发者理解和调试 RRect 渲染。

## 主要类与结构体

### LocalCornerVert
核心顶点模板结构，定义了标准化角落空间中的顶点属性：
- `fPosition`: 单位正方形中的位置
- `fNormal`: AA 外扩方向
- `fStrokeScale`: 描边半径缩放因子（-1/0/1）
- `fMirrorScale`: 镜像缩放（用于连接处理）
- `fCenterWeight`: 中心吸附权重
- `transform()`: 将标准化顶点变换到设备空间

### GraphitePrimitivesSlide
- 继承自 `ClickHandlerSlide`
- 三个控制点定义局部坐标系（原点、X轴、Y轴）
- 支持四种图元模式：填充矩形、填充 RRect、描边矩形、描边 RRect

### PrimitiveMode 枚举
- `kFillRect`, `kFillRRect`, `kStrokeRect`, `kStrokeRRect`

## 公共 API 函数

- `draw(SkCanvas*)`: 绘制参考图形和三角网格可视化
- `onChar(SkUnichar)`: 键盘控制（1-4 切换模式，-/= 调整线宽，q/w/e 切换连接模式）
- `onFindClickHandler/onClick`: 拖拽控制点

## 内部实现细节

### 角落顶点模板 (kCornerTemplate)
每个角落使用 19 个顶点，分为 5 层：
1. **AA 外扩顶点** (0-5): 设备空间法线外扩，实现抗锯齿渐变
2. **外部锚点** (6-9): 外曲线位置，无额外偏移
3. **描边中心** (10-13): 描边中间线位置
4. **内部 AA 内缩** (14-16): 局部空间法线内缩
5. **中心填充** (17-18): 可吸附到中心点

### 透视正确 AA 半径
`local_aa_radius()` 函数计算透视变换下的局部空间 AA 半径：
- 计算投影雅可比矩阵的奇异值
- 取最小奇异值的倒数乘以设备空间 AA 半径

### 索引缓冲区
使用三角带连接四个角落的对应层次，包括：
- `kOuterCornerIndices`: 外部角落三角带
- `kInnerCornerIndices`: 内部角落三角带
- `kEdgeIndices`: 边缘连接三角带
- `kInteriorIndices`: 内部填充三角带

### 设备空间法线计算
对于外扩顶点，使用逆转置矩阵计算设备空间法线方向，支持透视变换下的正确抗锯齿。对于 Miter 连接，对相邻边的法线进行角平分线计算。

## 依赖关系

- `include/core/SkM44.h`: 4x4 矩阵运算
- `include/core/SkRRect.h`: 圆角矩形定义
- `include/core/SkVertices.h`: 顶点网格绘制
- `tools/viewer/ClickHandlerSlide.h`: 可点击幻灯片基类

## 设计模式与设计决策

- **模板化顶点**: 使用标准化的角落顶点模板，通过旋转和翻转复用到四个角落
- **分层渲染**: 将 AA 和几何分为多个层次，每层有独立的颜色标识，便于调试
- **透视安全**: 所有计算考虑了透视除法，确保在任意 3D 变换下正确

## 性能考量

- 总顶点数为 4 * 19 = 76，索引缓冲区紧凑
- 设备空间法线计算需要矩阵求逆，但仅在控制点变化时更新
- 使用 `SkVertices::MakeCopy` 在 CPU 端构建网格后提交 GPU

## 相关文件

- `tools/viewer/ClickHandlerSlide.h`: 可点击幻灯片基类
- `src/gpu/graphite/render/AnalyticRRectRenderStep.cpp`: Graphite 中的实际 RRect 渲染实现
