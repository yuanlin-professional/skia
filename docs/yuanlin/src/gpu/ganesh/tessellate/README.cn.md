# tessellate - GPU 曲线细分处理模块

## 概述

`src/gpu/ganesh/tessellate` 目录是 Skia 图形库 Ganesh GPU 后端中负责路径细分（Tessellation）的核心模块。该模块实现了将矢量路径（包括直线、二次贝塞尔曲线、三次贝塞尔曲线和圆锥曲线）转换为 GPU 可直接渲染的三角形网格的功能。细分过程是 GPU 加速矢量图形渲染的关键步骤，它将数学定义的曲线近似为一系列小三角形，使 GPU 的光栅化硬件能够高效处理。

该模块的核心设计理念是"固定数量实例化绘制"（Fixed-Count Instanced Drawing）。每条曲线段作为一个独立的"patch"实例被写入 GPU 缓冲区，着色器在运行时通过 Wang 公式动态确定每条曲线需要多少细分段，并在不需要的顶点位置生成退化三角形（面积为零的三角形），从而在不浪费 GPU 计算资源的同时保持统一的绘制调用格式。

模块支持两大类路径渲染场景：路径填充（Path Fill）和路径描边（Path Stroke）。路径填充采用 Redbook 模板缓冲算法，通过模板测试和颜色填充两个 pass 完成。描边渲染则通过在曲线两侧生成等距的正交边，构建四边形条带（quad strip）来模拟笔画效果。描边着色器同时考虑参数边和径向边，能够处理任意曲率的曲线。

该模块与 `src/gpu/tessellate` 中的通用细分基础设施紧密协作。通用模块提供 `PatchWriter`、`WangsFormula`、`LinearTolerances` 等算法工具，而 `ganesh/tessellate` 则负责将这些算法与 Ganesh 渲染管线（着色器、缓冲区管理、绘制命令）集成在一起。通过 `VertexChunkPatchAllocator` 适配器，通用 `PatchWriter` 模板与 Ganesh 特有的 `GrVertexChunkArray` 缓冲区管理系统无缝对接。

## 架构图

```
                    +-------------------------------+
                    |        应用层 (SkPath)         |
                    +-------------------------------+
                                  |
                                  v
              +-------------------------------------------+
              |           PathTessellator (抽象基类)         |
              |  - prepare(): 准备 GPU 缓冲区数据           |
              |  - draw(): 发起实例化绘制调用               |
              +-------------------------------------------+
                     /                        \
                    v                          v
    +---------------------------+  +---------------------------+
    | PathCurveTessellator      |  | PathWedgeTessellator      |
    | (外部曲线 Patch)           |  | (楔形 Patch，含扇形点)    |
    | - 4 控制点曲线实例         |  | - 5 点闭合轮廓            |
    | - prepareWithTriangles()  |  | - 自带扇形中心点          |
    +---------------------------+  +---------------------------+
                |                          |
                v                          v
    +----------------------------------------------+
    |     VertexChunkPatchAllocator (适配器)          |
    |  PatchWriter <--> GrVertexChunkBuilder         |
    +----------------------------------------------+
                          |
                          v
    +----------------------------------------------+
    |         GrTessellationShader (着色器基类)       |
    |  - MakePipeline(): 创建渲染管线               |
    |  - MakeProgram(): 创建着色器程序               |
    |  - WangsFormulaSkSL(): Wang 公式 SkSL 代码    |
    +----------------------------------------------+
              /                          \
             v                            v
+----------------------------+  +-----------------------------+
| GrPathTessellationShader   |  | GrStrokeTessellationShader  |
| - SimpleTriangleShader     |  | - 参数边 + 径向边组合细分     |
| - MiddleOutShader          |  | - 动态笔画/颜色属性          |
| - Redbook 模板缓冲设置      |  | - 连接类型处理 (圆/斜/平)   |
+----------------------------+  +-----------------------------+

    +----------------------------------------------+
    |          StrokeTessellator                     |
    |  - 描边路径细分器                              |
    |  - 固定数量三角形条带实例绘制                   |
    |  - PathStrokeList 链表遍历                     |
    +----------------------------------------------+
```

## 文件分类索引

### 1. 细分着色器 — Tessellation Shaders

| 文件 | 说明 |
|------|------|
| GrTessellationShader.h / GrTessellationShader.cpp | 细分着色器基类（管线创建与 Wang 公式 SkSL 代码） |
| GrPathTessellationShader.h / GrPathTessellationShader.cpp | 路径填充细分着色器（SimpleTriangle/MiddleOut 实现） |
| GrStrokeTessellationShader.h / GrStrokeTessellationShader.cpp | 描边细分着色器 GPU 代码生成 |

### 2. 细分算法 — Tessellator Implementations

| 文件 | 说明 |
|------|------|
| PathTessellator.h / PathTessellator.cpp | 路径细分器（Curve/Wedge 细分器实现） |
| StrokeTessellator.h / StrokeTessellator.cpp | 描边细分器（固定数量实例化绘制） |

### 3. 内存管理 — Allocator

| 文件 | 说明 |
|------|------|
| VertexChunkPatchAllocator.h | PatchWriter 与 GrVertexChunkBuilder 适配器 |

## 关键类与函数

### GrTessellationShader
所有细分着色器的公共基类，继承自 `GrGeometryProcessor`。提供视图矩阵、颜色和图元类型的统一管理。

- `MakePipeline()` - 创建包含处理器集和裁剪信息的渲染管线
- `MakeProgram()` - 在 Arena 内存中构建 `GrProgramInfo` 对象
- `WangsFormulaSkSL()` - 返回 Wang 公式的 SkSL 着色器代码，包含 `wangs_formula_cubic()`、`wangs_formula_conic()` 及其 log2 变体

### GrPathTessellationShader
路径填充专用的细分着色器基类。内部有两个私有子类：

- `SimpleTriangleShader` - 直接绘制三角形数组，用于内部扇形三角化
- `MiddleOutShader` - 使用中间优先拓扑（Middle-Out Topology）进行实例化曲线细分，通过 `sk_VertexID` 控制细分深度
- `StencilPathSettings()` - 返回 Redbook 模板缓冲的 stencil 设置，支持 Nonzero（递增/递减）和 EvenOdd（反转）填充规则
- `TestAndResetStencilSettings()` - 返回颜色填充 pass 的 stencil 设置
- `MakeStencilOnlyPipeline()` - 创建不输出颜色的纯模板管线

### GrStrokeTessellationShader
描边细分着色器。生成的 GPU 代码在顶点着色器中完成完整的描边细分计算：

- 使用参数边（parametric edges）均匀分布曲线参数空间
- 使用径向边（radial edges）均匀分布曲线旋转角度
- 通过二分搜索合并两组边为统一的四边形条带
- 支持动态笔画参数（`PatchAttribs::kStrokeParams`）和动态颜色（`PatchAttribs::kColor`）
- 处理三种连接类型：圆角（Round）、斜接（Miter）、平角（Bevel）

### PathTessellator
路径细分器的抽象基类，位于 `skgpu::ganesh` 命名空间。定义了 `prepare()` 和 `draw()` 的虚函数接口。

- `PathDrawList` - 路径绘制列表的链表结构，每项包含路径矩阵、SkPath 和颜色
- `PathCurveTessellator` - 外部曲线细分器，每个 patch 是独立的 4 点曲线
  - `prepareWithTriangles()` - 可附带额外的面包屑三角形（breadcrumb triangles）
  - `drawHullInstances()` - 绘制凸包实例用于填充
- `PathWedgeTessellator` - 楔形细分器，每个 patch 包含 4 个控制点加 1 个扇形中心点，楔形自身定义完整路径

### StrokeTessellator
描边路径细分器。使用固定数量的三角形条带实例进行绘制。

- `PathStrokeList` - 描边路径链表，每项包含路径、笔画记录和颜色
- `prepare()` - 通过 `StrokeWriter`（即 `PatchWriter` 模板特化）将描边数据写入 GPU 缓冲区
- `draw()` - 对每个顶点块发起实例化绘制

### VertexChunkPatchAllocator
适配器类，使 `skgpu::tess::PatchWriter` 模板能与 Ganesh 的 `GrVertexChunkBuilder` 配合工作。每次 `append()` 调用会累积最坏情况线性容差并分配一个顶点。

## 依赖关系

### 上游依赖（本模块依赖的模块）
- `src/gpu/tessellate/` - 通用细分基础设施（`PatchWriter`、`WangsFormula`、`FixedCountBufferUtils`、`LinearTolerances`、`StrokeIterator`、`MidpointContourParser`、`AffineMatrix`）
- `src/gpu/ganesh/` - Ganesh 核心（`GrGeometryProcessor`、`GrPipeline`、`GrProgramInfo`、`GrVertexChunkArray`、`GrMeshDrawTarget`、`GrOpFlushState`、`GrResourceProvider`）
- `include/core/` - Skia 核心类型（`SkPath`、`SkMatrix`、`SkStrokeRec`）
- `src/gpu/ganesh/glsl/` - GLSL 着色器代码生成器
- `src/gpu/ganesh/geometry/` - `GrInnerFanTriangulator`（内部扇形三角化）

### 下游依赖（依赖本模块的模块）
- Ganesh 路径渲染操作（Path Ops）使用 `PathTessellator` 和 `StrokeTessellator`
- Ganesh 渲染管线通过 `GrTessellationShader` 子类创建着色器程序

## 设计模式分析

### 模板方法模式（Template Method Pattern）
`GrPathTessellationShader::Impl` 基类定义了 `onEmitCode()` 的框架流程（设置 uniform、调用 `emitVertexCode()`、设置片段着色器），而具体的顶点着色器代码由 `SimpleTriangleShader::Impl` 和 `MiddleOutShader::Impl` 等子类通过 `emitVertexCode()` 纯虚函数实现。

### 策略模式（Strategy Pattern）
`PathTessellator` 定义了统一的 `prepare()`/`draw()` 接口，`PathCurveTessellator` 和 `PathWedgeTessellator` 提供不同的细分策略。调用方可以根据路径特征选择合适的策略。

### 适配器模式（Adapter Pattern）
`VertexChunkPatchAllocator` 是经典的适配器，它将 `GrVertexChunkBuilder` 的 API 适配为 `PatchWriter` 模板参数所要求的 `PatchAllocator` 接口。

### 工厂方法模式（Factory Method Pattern）
`GrPathTessellationShader::Make()` 和 `GrPathTessellationShader::MakeSimpleTriangleShader()` 是工厂方法，根据参数在 Arena 内存中创建具体的着色器子类实例。

### Arena 分配模式
所有着色器和管线对象都在 `SkArenaAlloc` 中分配，避免频繁的堆内存分配和释放，提升渲染帧率期间的内存管理效率。

## 数据流

```
1. 输入阶段
   SkPath (矢量路径) + SkMatrix (变换) + SkStrokeRec (笔画参数)
       |
       v
2. 路径迭代与分解
   PathDrawList / PathStrokeList 链表遍历
   SkPathPriv::Iterate 分解为 Move/Line/Quad/Conic/Cubic 指令
       |
       v
3. Patch 写入
   PatchWriter 将曲线段写入 VertexChunkPatchAllocator
   - CurveWriter: 写入 4 点曲线 patch（二次曲线提升为三次，线段转为圆锥）
   - WedgeWriter: 写入 5 点楔形 patch（含轮廓中心点）
   - StrokeWriter: 写入描边 patch（含连接控制点、笔画参数）
   - 同时通过 Wang 公式计算并累积 LinearTolerances
       |
       v
4. GPU 缓冲区准备
   GrVertexChunkBuilder 将数据分块写入 GrGpuBuffer
   GrResourceProvider 创建/复用固定计数的顶点和索引缓冲区
       |
       v
5. 着色器编译
   GrTessellationShader 子类生成 SkSL 顶点和片段着色器代码
   - Wang 公式在 GPU 上动态计算每条曲线所需的细分段数
   - De Casteljau 算法在 GPU 上评估曲线上的点
   - 二分搜索在 GPU 上合并参数边和径向边（描边场景）
       |
       v
6. 绘制执行
   GrOpFlushState 绑定缓冲区并发起 drawIndexedInstanced 调用
   - 固定数量的顶点/索引缓冲区 + 实例缓冲区（patch 数据）
   - 不需要的顶点生成退化三角形
```

## 相关文档与参考

- `src/gpu/tessellate/` - 通用细分算法实现（`WangsFormula.h`、`PatchWriter.h`、`FixedCountBufferUtils.h`）
- `src/gpu/ganesh/GrGeometryProcessor.h` - 几何处理器基类
- `src/gpu/ganesh/GrVertexChunkArray.h` - 顶点块数组管理
- `src/gpu/ganesh/GrOpFlushState.h` - 操作刷新状态，管理绘制命令发出
- `src/gpu/ganesh/geometry/GrInnerFanTriangulator.h` - 内部扇形三角化器，产生面包屑三角形
- Wang 公式参考：Charles Loop and Jim Blinn, "Resolution Independent Curve Rendering using Programmable Graphics Hardware" (2005)
- Redbook 模板缓冲算法：OpenGL Programming Guide 中的路径填充算法
- Middle-Out 拓扑：一种广度优先的曲线细分策略，避免了深度优先方法可能产生的裂缝
