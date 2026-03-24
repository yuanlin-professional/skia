# TessellationPathRenderer

> 源文件
> - src/gpu/ganesh/ops/TessellationPathRenderer.h
> - src/gpu/ganesh/ops/TessellationPathRenderer.cpp

## 概述

`TessellationPathRenderer` 是 Skia Ganesh GPU 后端中专门用于路径渲染的一个实现类，采用 GPU 硬件曲面细分（tessellation）技术来绘制复杂路径。该渲染器采用经典的 Red Book "先模板后覆盖"（stencil-then-cover）方法，利用 GPU 的曲面细分着色器将贝塞尔曲线线性化，提供高性能的路径渲染能力。该渲染器不支持解析抗锯齿（analytic AA），如需抗锯齿效果则必须使用 MSAA（多重采样抗锯齿）。

## 架构位置

`TessellationPathRenderer` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/ops/` - Ganesh GPU 操作层
- **继承关系**：继承自 `PathRenderer` 基类
- **命名空间**：`skgpu::ganesh`
- **依赖组件**：
  - 上层依赖：`SurfaceDrawContext`、`GrCaps`、`GrStyledShape`
  - 同层依赖：`PathTessellateOp`、`StrokeTessellateOp`、`PathStencilCoverOp`、`PathInnerTriangulateOp`
  - 底层依赖：`skgpu::tess` 曲面细分核心库、Wang's Formula 计算模块

## 主要类与结构体

### TessellationPathRenderer

```cpp
class TessellationPathRenderer final : public PathRenderer
```

**核心职责**：
- 作为路径渲染器的具体实现，负责判断路径是否可以使用曲面细分技术渲染
- 管理路径的绘制和模板化流程
- 根据路径特性选择最优的渲染策略

**关键成员函数**：
- `IsSupported(const GrCaps&)` - 静态方法，检查硬件能力是否支持曲面细分
- `name()` - 返回渲染器名称 "Tessellation"
- `onGetStencilSupport()` - 查询模板支持能力
- `onCanDrawPath()` - 判断是否能够绘制给定路径
- `onDrawPath()` - 执行路径绘制
- `onStencilPath()` - 执行路径模板化操作

## 公共 API 函数

### IsSupported

```cpp
static bool IsSupported(const GrCaps& caps)
```

**功能**：检查当前 GPU 能力是否支持曲面细分路径渲染器

**条件判断**：
- 模板缓冲区可用（`!caps.avoidStencilBuffers()`）
- 支持实例化绘制（`caps.drawInstancedSupport()`）
- 未显式禁用曲面细分路径渲染器（`!caps.disableTessellationPathRenderer()`）

### name

```cpp
const char* name() const override
```

返回渲染器标识名称 "Tessellation"，用于调试和性能分析。

## 内部实现细节

### 路径预切割机制

**ChopPathIfNecessary 函数**：
- **目的**：处理极大路径，防止单个曲线段的细分段数超过硬件限制
- **触发条件**：当路径边界框的 Wang's Formula 计算值超过 `kMaxSegmentsPerCurve_p4` 时
- **处理策略**：
  - 计算视口区域（考虑笔触宽度）
  - 使用 `PreChopPathCurves` 预切割曲线
  - 扁平化完全落在视口外的曲线

**关键代码逻辑**：
```cpp
float n4 = wangs_formula::worst_case_cubic_p4(
    tess::kPrecision, pathDevBounds.width(), pathDevBounds.height());
if (n4 > tess::kMaxSegmentsPerCurve_p4) {
    // 需要预切割
}
```

### 非凸路径优化策略

**make_non_convex_fill_op 函数**：

该函数实现了智能选择算法，根据 CPU 三角化工作量和 GPU 片段填充工作量的对比，动态选择最优路径：

1. **PathInnerTriangulateOp 路径**：
   - **适用场景**：大型简单路径，CPU 三角化代价低于 GPU 多通道渲染
   - **判断公式**：`cpuTessellationWork * kCpuWeight + kMinNumPixelsToTriangulate < gpuFragmentWork`
   - **优势**：仅需模板化曲线，内部扇形区域直接填充，减少渲染通道

2. **PathStencilCoverOp 路径**：
   - **适用场景**：复杂路径或小型路径
   - **流程**：标准的模板-覆盖两阶段渲染

**权重参数**：
- `kCpuWeight = 512` - CPU 计算成本权重因子
- `kMinNumPixelsToTriangulate = 256 * 256` - 最小像素阈值

### 路径分类处理

**onDrawPath 实现的决策树**：

1. **笔触路径**：使用 `StrokeTessellateOp`
2. **空路径**：
   - 普通空路径：不渲染
   - 反向填充空路径：使用 `drawPaint` 填充整个画布
3. **凸路径**：使用 `PathTessellateOp` 直接渲染
4. **非凸路径**：调用 `make_non_convex_fill_op` 选择最优策略

### 模板化流程

**onStencilPath 实现**：
- **凸路径**：使用 `PathTessellateOp` + 自定义模板设置
- **非凸路径**：使用 `make_non_convex_fill_op` + `FillPathFlags::kStencilOnly` 标志

## 依赖关系

**直接依赖**：
- `PathRenderer` - 基类接口
- `GrCaps` - GPU 能力查询
- `GrStyledShape` - 样式化形状表示
- `PathTessellateOp` - 凸路径曲面细分操作
- `StrokeTessellateOp` - 笔触曲面细分操作
- `PathStencilCoverOp` - 模板-覆盖操作
- `PathInnerTriangulateOp` - 内部三角化操作

**核心算法依赖**：
- `skgpu::tess::WangsFormula` - 曲线细分段数估算
- `skgpu::tess::PreChopPathCurves` - 路径预切割
- `skgpu::tess::kMaxSegmentsPerCurve` - 最大段数限制常量

**图形管线依赖**：
- `SurfaceDrawContext` - 渲染上下文
- `GrPaint` - 绘制参数
- `GrClip` - 裁剪区域
- `GrUserStencilSettings` - 用户模板设置

## 设计模式与设计决策

### 策略模式（Strategy Pattern）

`TessellationPathRenderer` 作为 `PathRenderer` 的一个具体策略实现，通过多态接口提供专门的曲面细分渲染能力。系统可以在运行时根据路径特性选择最合适的渲染器。

### 工厂方法模式（Factory Method Pattern）

使用 `GrOp::Make<T>` 创建各种操作对象（Op），将操作对象的创建逻辑封装，便于管理和扩展。

### 启发式优化决策

**代价评估模型**：系统通过量化的代价模型来选择渲染路径，而非简单的阈值判断。这种设计考虑了：
- CPU 三角化的 O(N log N) 复杂度
- GPU 片段填充的线性像素复杂度
- 硬件性能差异（通过权重因子调整）

### 防御性编程

**笔触宽度限制**：
```cpp
if (shape.style().strokeRec().getWidth() * args.fViewMatrix->getMaxScale() > 10000) {
    return CanDrawPath::kNo;
}
```

防止极宽笔触导致视口爆炸性增长和内存耗尽问题（参考 crbug.com/1266446）。

### 渐进式降级

当路径过于复杂无法用曲面细分处理时，系统会返回 `CanDrawPath::kNo`，允许其他渲染器接管处理，保证系统健壮性。

## 性能考量

### 曲面细分段数控制

通过 Wang's Formula 预估曲线细分所需段数，确保不超过硬件限制 `kMaxSegmentsPerCurve`。对于超限路径，采用预切割策略将长曲线分解为多个短曲线。

### CPU 与 GPU 负载平衡

**自适应策略**：
- 小路径：GPU 直接渲染更快
- 大简单路径：CPU 三角化 + GPU 单通道填充更优
- 复杂路径：GPU 多通道模板-覆盖方法

### 内存优化

使用 `SkArenaAlloc` 进行快速内存分配，避免频繁的堆分配开销。所有操作对象通过 Arena 分配器管理生命周期。

### 视口裁剪优化

在预切割阶段考虑裁剪区域，扁平化视口外的曲线，减少不必要的细分计算。对于笔触路径，视口会根据笔触宽度扩展，确保边缘正确渲染。

### 早期剔除

- 空路径快速返回（特殊处理反向填充）
- 不支持的路径类型在 `onCanDrawPath` 阶段拒绝
- 极宽笔触提前拒绝，避免后续处理开销

## 相关文件

**操作实现**：
- `src/gpu/ganesh/ops/PathTessellateOp.h/cpp` - 凸路径曲面细分操作
- `src/gpu/ganesh/ops/StrokeTessellateOp.h/cpp` - 笔触曲面细分操作
- `src/gpu/ganesh/ops/PathStencilCoverOp.h/cpp` - 模板-覆盖操作
- `src/gpu/ganesh/ops/PathInnerTriangulateOp.h/cpp` - 内部三角化操作

**核心算法**：
- `src/gpu/tessellate/Tessellation.h` - 曲面细分核心接口
- `src/gpu/tessellate/WangsFormula.h` - Wang's Formula 实现

**基础设施**：
- `src/gpu/ganesh/PathRenderer.h` - 路径渲染器基类
- `src/gpu/ganesh/GrCaps.h` - GPU 能力管理
- `src/gpu/ganesh/geometry/GrStyledShape.h` - 样式化形状表示

**渲染上下文**：
- `src/gpu/ganesh/SurfaceDrawContext.h` - 表面绘制上下文
- `src/gpu/ganesh/GrPaint.h` - 绘制参数封装
