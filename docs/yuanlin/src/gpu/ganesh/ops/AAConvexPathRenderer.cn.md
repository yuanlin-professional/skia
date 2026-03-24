# AAConvexPathRenderer

> 源文件: `src/gpu/ganesh/ops/AAConvexPathRenderer.h`, `src/gpu/ganesh/ops/AAConvexPathRenderer.cpp`

## 概述

`AAConvexPathRenderer` 是 Ganesh 中专门用于渲染抗锯齿凸路径的路径渲染器。它将凸路径分解为线段和二次曲线段，为每个段生成包含距离场信息的几何数据，并通过着色器导数计算实现像素级覆盖率抗锯齿。该渲染器只处理简单填充的凸路径。

## 架构位置

位于 Ganesh 路径渲染系统中，作为 `PathRenderer` 的具体实现之一。在路径绘制时由 `PathRendererChain` 根据路径特征选择。仅处理 Coverage AA 类型的凸路径，其他路径（凹面、描边等）由其他渲染器处理。

## 主要类与结构体

### `AAConvexPathRenderer`
- 继承自 `PathRenderer`
- `onCanDrawPath()` - 检查是否可处理当前路径
- `onDrawPath()` - 创建并提交绘制操作

### `Segment`（内部）
- 表示路径的一个段（线段或二次曲线），包含控制点、法线和中间向量

### `QuadEdgeEffect`（内部几何处理器）
- 实现基于二次曲线的边缘距离场抗锯齿
- 顶点属性：位置（float2）、颜色、四元边缘数据（float4）
- 使用着色器导数（dFdx/dFdy）计算平滑的边缘覆盖率

### `AAConvexPathOp`（内部绘制操作）
- 继承自 `GrMeshDrawOp`
- 将路径转换为段，计算法线和中间向量，生成三角形网格
- 支持操作合并（`onCombineIfPossible`）

## 公共 API 函数

- `onCanDrawPath()` - 当着色器支持导数、使用 Coverage AA、简单填充、非反转、已知凸且方向确定时返回 `kYes`
- `onDrawPath()` - 从路径创建 `AAConvexPathOp` 并提交到 `SurfaceDrawContext`

## 内部实现细节

### 路径处理流程
1. `get_segments()` - 将路径转换为段数组（线段和二次曲线），处理退化检测
2. `compute_vectors()` - 计算每段的法线向量和段间中间向量
3. `center_of_mass()` - 计算多边形质心作为扇形中心点
4. `create_vertices()` - 生成包含位置、颜色、UV 和距离数据的顶点

### 着色器覆盖率计算
- 二次曲线段：使用 `u^2 - v` 距离场，通过 `dFdx/dFdy` 计算梯度长度
- 线段：使用退化二次曲线（u=0），直接用有符号距离计算覆盖率
- 角楔形：在段交汇处使用额外三角形确保平滑过渡
- 距离值 D0/D1 用于裁剪到有限的二次曲线区域

### 透视处理
- 透视路径先通过 `SkPath::makeTransform()` 变换到设备空间
- 非透视路径在拷贝到段时按需应用视图矩阵

## 依赖关系

- **PathRenderer** - 基类
- **GrMeshDrawOp** - 操作基类
- **GrGeometryProcessor** - `QuadEdgeEffect` 的基类
- **GrPathUtils** - 三次曲线到二次曲线的转换
- **GrSimpleMeshDrawOpHelperWithStencil** - 管线和模板设置辅助

## 设计模式与设计决策

1. **段化方法**: 将所有曲线类型统一为线段和二次曲线，简化着色器逻辑
2. **退化检测**: 多阶段退化测试（点、线、非退化），避免对退化路径生成伪影
3. **索引溢出处理**: 当顶点数超过 65536 时自动分割为多个绘制调用
4. **着色器导数 AA**: 利用 GPU 硬件导数指令实现高质量的分析抗锯齿

## 性能考量

- 仅适用于凸路径，避免了复杂的凹面路径分割
- 三次曲线先转为二次曲线，增加了段数但简化了着色器
- 不使用 MSAA，通过分析覆盖率实现 AA，适合单采样渲染目标
- 支持操作合并，多个凸路径可在同一绘制调用中渲染

## 相关文件

- `src/gpu/ganesh/PathRenderer.h` - 路径渲染器基类
- `src/gpu/ganesh/ops/GrMeshDrawOp.h` - 网格绘制操作基类
- `src/gpu/ganesh/geometry/GrPathUtils.h` - 路径工具函数
- `src/gpu/ganesh/ops/TriangulatingPathRenderer.h` - 凹面路径渲染器
