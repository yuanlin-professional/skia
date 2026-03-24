# AALinearizingConvexPathRenderer

> 源文件
> - src/gpu/ganesh/ops/AALinearizingConvexPathRenderer.h
> - src/gpu/ganesh/ops/AALinearizingConvexPathRenderer.cpp

## 概述

`AALinearizingConvexPathRenderer` 是 Skia Ganesh GPU 后端的路径渲染器，专门用于渲染具有抗锯齿效果的凸多边形路径。该渲染器采用线性化（Linearizing）技术，将凸路径分解为三角形网格，并通过镶嵌（Tessellation）生成带有覆盖率信息的顶点，从而实现高质量的抗锯齿效果。

该渲染器的核心优势在于使用 `GrAAConvexTessellator` 进行 CPU 端的路径镶嵌，生成包含边缘覆盖率的几何数据，避免了在片段着色器中进行复杂的距离计算。它支持填充和描边模式，但对描边宽度和连接类型有一定限制。

## 架构位置

`AALinearizingConvexPathRenderer` 位于 Skia 的 GPU 渲染管线中的路径渲染层：

```
Skia GPU 渲染架构:
├── GrContext / GrRecordingContext
├── SurfaceDrawContext
├── PathRenderer 系统 ← AALinearizingConvexPathRenderer 位于此处
│   ├── AAConvexPathRenderer
│   ├── AALinearizingConvexPathRenderer (本类)
│   ├── AAHairLinePathRenderer
│   ├── AtlasPathRenderer
│   └── DefaultPathRenderer
├── GrOp 操作层
│   └── AAFlatteningConvexPathOp (内部实现的操作)
└── GPU 底层
```

该渲染器作为 `PathRenderer` 的一个具体实现，通过 `onCanDrawPath` 方法判断是否能处理特定路径，并在 `onDrawPath` 中生成对应的 GPU 操作。

## 主要类与结构体

### AALinearizingConvexPathRenderer 类

继承自 `PathRenderer` 基类。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无公共成员变量 | - | 该类为无状态渲染器，所有状态封装在生成的 Op 中 |

### AAFlatteningConvexPathOp 类（内部实现）

继承自 `GrMeshDrawOp`，封装实际的绘制操作。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPaths` | `STArray<1, PathData, true>` | 待渲染的路径数据数组，支持批处理 |
| `fHelper` | `GrSimpleMeshDrawOpHelperWithStencil` | 操作辅助工具，处理管线、混合、模板等 |
| `fWideColor` | `bool` | 是否使用宽色域颜色 |
| `fMeshes` | `SkTDArray<GrSimpleMesh*>` | 生成的网格数组 |
| `fProgramInfo` | `GrProgramInfo*` | GPU 程序信息 |

### PathData 结构体

存储单个路径的渲染参数：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fPath` | `SkPath` | 待渲染的路径对象 |
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fStrokeWidth` | `SkScalar` | 描边宽度（填充时为 -1） |
| `fMiterLimit` | `SkScalar` | 斜接限制值 |
| `fStyle` | `SkStrokeRec::Style` | 渲染样式（填充/描边/两者） |
| `fJoin` | `SkPaint::Join` | 线段连接类型 |

## 公共 API 函数

### PathRenderer 接口实现

```cpp
const char* name() const override
```
返回渲染器名称 "AALinear"，用于调试和日志记录。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否能够渲染给定的路径。返回值：
- `CanDrawPath::kYes`：可以渲染
- `CanDrawPath::kNo`：不能渲染

支持的路径条件：
- 必须是凸多边形（`knownToBeConvex()`）
- 使用覆盖率抗锯齿（`GrAAType::kCoverage`）
- 不能有 path effect
- 不能是反向填充
- 填充模式不能有透视变换
- 描边模式需要相似变换（`isSimilarity()`）
- 描边宽度不超过 20 像素（非矩形）
- 不支持圆角连接（`kRound_Join`）

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行实际的路径渲染，创建 `AAFlatteningConvexPathOp` 并添加到绘制上下文。

## 内部实现细节

### 镶嵌算法

该渲染器使用 `GrAAConvexTessellator` 在 CPU 端进行路径镶嵌：

1. **路径线性化**：将贝塞尔曲线和圆弧转换为直线段
2. **三角剖分**：生成覆盖路径区域的三角形网格
3. **边缘处理**：为路径边缘生成额外的顶点，包含覆盖率信息
4. **抗锯齿**：边缘顶点的覆盖率从 0 渐变到 1，实现平滑过渡

### 顶点数据结构

每个顶点包含以下数据：
- **位置**（2 floats）：世界空间坐标
- **颜色**（4 bytes 或 8 bytes）：顶点颜色，支持宽色域
- **局部坐标**（2 floats，可选）：用于纹理映射或效果处理
- **覆盖率**（1 float）：边缘抗锯齿覆盖率（0.0 到 1.0）

### 批处理机制

`AAFlatteningConvexPathOp` 支持合并多个路径操作：

1. **兼容性检查**：通过 `fHelper.isCompatible()` 判断是否可以合并
2. **动态缓冲区**：使用可增长的内存缓冲区累积顶点和索引
3. **溢出处理**：当顶点数超过 `UINT16_MAX` 时，分批绘制
4. **内存管理**：使用 `sk_malloc_throw` 和 `sk_realloc_throw` 管理临时缓冲区

### 绘制流程

```
onPrepareDraws:
├── 遍历所有路径
├── 使用 GrAAConvexTessellator 镶嵌每个路径
├── 提取顶点和索引数据
├── 累积到缓冲区
├── 检查溢出条件，必要时分批 recordDraw
└── 最终 recordDraw 剩余数据

onExecute:
├── 绑定管线和裁剪
├── 绑定纹理
└── 遍历所有 mesh 执行绘制
```

### 坐标变换

如果着色器需要局部坐标（用于纹理或效果处理）：
1. 计算视图矩阵的逆矩阵 `ivm`
2. 将每个顶点的世界坐标通过 `ivm` 映射到局部坐标空间
3. 将局部坐标作为顶点属性传递给着色器

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrAAConvexTessellator` | 核心依赖 | 执行路径镶嵌，生成抗锯齿几何 |
| `GrDefaultGeoProcFactory` | 强依赖 | 创建几何处理器 |
| `GrSimpleMeshDrawOpHelperWithStencil` | 强依赖 | 管理绘制操作的管线、混合、模板 |
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `GrMeshDrawOp` | 继承 | 网格绘制操作基类 |
| `VertexWriter` | 强依赖 | 写入顶点数据 |
| `GrStyledShape` | 强依赖 | 封装路径和样式信息 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `SurfaceDrawContext` | 使用 | 通过路径渲染器选择机制调用此渲染器 |
| `PathRendererChain` | 注册 | 作为可选路径渲染器之一 |
| `GrContext` | 间接使用 | 通过绘制上下文管理渲染操作 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）

`AALinearizingConvexPathRenderer` 实现了 `PathRenderer` 接口，作为路径渲染策略的一种。Skia 的路径渲染系统通过策略链选择最合适的渲染器。

### 2. 工厂方法模式

使用 `Helper::FactoryHelper` 创建 `AAFlatteningConvexPathOp`，封装了对象创建的复杂性和内存管理。

### 3. 延迟计算（Lazy Evaluation）

- **程序信息延迟创建**：`fProgramInfo` 在首次需要时才创建（`onPrepareDraws` 中）
- **镶嵌延迟执行**：路径镶嵌在 `onPrepareDraws` 阶段才执行，而不是在 Op 创建时

### 4. CPU 端镶嵌的设计决策

**选择 CPU 镶嵌而非 GPU 镶嵌**：
- **优点**：
  - 避免 GPU 着色器中的复杂距离场计算
  - 覆盖率信息在顶点中，插值后直接使用
  - 兼容性好，不依赖 GPU 几何着色器
- **缺点**：
  - CPU 计算开销
  - 数据传输量较大

对于凸多边形，CPU 镶嵌的成本是可接受的，且能提供高质量的抗锯齿效果。

### 5. 限制圆角连接

不支持 `kRound_Join` 的设计决策：
- 圆角连接需要生成大量额外的顶点
- 镶嵌复杂度显著增加
- 其他渲染器（如 `DefaultPathRenderer`）更适合处理圆角

### 6. 描边宽度限制

设置最大描边宽度 20 像素的原因：
- 宽描边的高质量镶嵌计算成本高
- 超过阈值时，软件渲染或其他技术更高效
- 对于矩形，可以放宽限制（矩形镶嵌简单）

## 性能考量

### 1. 批处理优化

通过 `onCombineIfPossible` 合并兼容的路径操作，减少绘制调用次数和状态切换开销。

### 2. 动态缓冲区增长

使用倍增策略 (`maxVertices * 2`) 扩展缓冲区，平衡内存分配次数和空间利用率。

### 3. 索引溢出检查

在累积顶点数超过 `UINT16_MAX` 之前提前分批绘制，避免索引溢出，同时最大化批处理效率。

### 4. 内存管理

- 使用栈上的 `STArray<1, PathData, true>` 优化单路径场景（最常见）
- 临时缓冲区在 `onPrepareDraws` 结束时释放，避免持久占用

### 5. 快速路径判断

`onCanDrawPath` 通过多个快速检查提前退出：
- 凸性检查
- 抗锯齿类型检查
- Path effect 检查
- 边界大小检查

这些检查成本低，避免不必要的镶嵌尝试。

### 6. 局部坐标计算优化

只有在着色器需要时才计算局部坐标（`fHelper.usesLocalCoords()`），避免不必要的矩阵逆运算。

### 7. 覆盖率插值

将覆盖率信息编码为顶点属性，利用 GPU 硬件插值，避免片段着色器中的复杂计算。

### 8. 相似变换优化

对于描边路径，要求相似变换（`isSimilarity()`）简化了描边宽度的计算和镶嵌逻辑。

### 9. 默认缓冲区大小

`DEFAULT_BUFFER_SIZE = 100` 是经验值，平衡了小路径的内存占用和大路径的重新分配次数。

### 10. 宽色域条件编译

通过 `fWideColor` 标志在需要时才启用宽色域支持，节省不必要的顶点数据空间和带宽。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器抽象接口 |
| `src/gpu/ganesh/geometry/GrAAConvexTessellator.h` | 核心依赖 | 凸路径抗锯齿镶嵌器 |
| `src/gpu/ganesh/GrDefaultGeoProcFactory.h` | 依赖 | 创建默认几何处理器 |
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 基类 | 网格绘制操作基类 |
| `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelperWithStencil.h` | 辅助 | 简化操作创建和管线管理 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文，管理绘制操作 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 依赖 | 封装路径和样式 |
| `src/gpu/BufferWriter.h` | 依赖 | 顶点数据写入工具 |
| `src/gpu/ganesh/ops/AAConvexPathRenderer.h` | 相关 | 另一种凸路径渲染器（不使用线性化） |
