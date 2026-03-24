# PathInnerTriangulateOp

> 源文件
> - `src/gpu/ganesh/ops/PathInnerTriangulateOp.h`
> - `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp`

## 概述

`PathInnerTriangulateOp` 是 Ganesh GPU 后端中用于路径填充的三遍渲染操作，是标准 Redbook "先模板后覆盖"（stencil-then-cover）算法的改进版本。该操作通过以下三个步骤实现路径填充：

1. **第一遍**：将路径的外部曲线曲面细分到模板缓冲区
2. **第二遍**：三角化路径的内部扇形区域，并使用模板测试针对曲线进行填充
3. **第三遍**：绘制每条曲线周围的凸包，填充剩余的采样点

从 GPU 负载的角度来看，由于路径的内部扇形区域占据了大部分像素，这个操作实际上与单遍算法一样快，同时提供了更好的质量保证。该操作仅在未定义 `SK_ENABLE_OPTIMIZE_SIZE` 时可用。

## 架构位置

在 Skia 的 Ganesh 架构中，`PathInnerTriangulateOp` 位于以下层次：

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          GrOp (基类)
            GrDrawOp
              └── PathInnerTriangulateOp
        tessellate/
          PathTessellator (曲线细分器)
          GrTessellationShader (细分着色器)
```

它是 Ganesh 路径渲染系统的一部分，专门处理复杂路径的高质量填充。

## 主要类与结构体

### PathInnerTriangulateOp

路径内部三角化操作类。

**继承关系：** `GrDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPathFlags` | `FillPathFlags` | 路径填充标志（常量） |
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵（常量） |
| `fPath` | `SkPath` | 要绘制的路径（常量） |
| `fAAType` | `GrAAType` | 抗锯齿类型（常量） |
| `fColor` | `SkPMColor4f` | 填充颜色 |
| `fProcessors` | `GrProcessorSet` | 片段处理器集合 |
| `fFanTriangulator` | `GrInnerFanTriangulator*` | 内部扇形三角化器 |
| `fFanPolys` | `GrTriangulator::Poly*` | 扇形多边形 |
| `fFanBreadcrumbs` | `BreadcrumbTriangleList` | 面包屑三角形列表 |
| `fPipelineForFills` | `const GrPipeline*` | 填充管线 |
| `fTessellator` | `PathCurveTessellator*` | 曲线细分器 |
| `fStencilCurvesProgram` | `const GrProgramInfo*` | 模板曲线程序 |
| `fFanPrograms` | `STArray<2, const GrProgramInfo*>` | 扇形程序数组 |
| `fCoverHullsProgram` | `const GrProgramInfo*` | 覆盖凸包程序 |
| `fFanBuffer` | `sk_sp<const GrBuffer>` | 扇形顶点缓冲区 |
| `fBaseFanVertex` | `int` | 扇形基础顶点索引 |
| `fFanVertexCount` | `int` | 扇形顶点数量 |
| `fHullVertexBufferIfNoIDSupport` | `sk_sp<const GrGpuBuffer>` | 凸包顶点缓冲区（无顶点ID支持时） |

### HullShader

内部着色器类，用于绘制曲线周围的凸包。

**继承关系：** `GrPathTessellationShader`

**特性：**
- 处理三次曲线和圆锥曲线
- 生成包围曲线的凸包几何
- 支持有无顶点ID的两种模式

## 公共 API 函数

### 构造函数（私有）

```cpp
PathInnerTriangulateOp(
    const SkMatrix& viewMatrix,
    const SkPath& path,
    GrPaint&& paint,
    GrAAType aaType,
    FillPathFlags pathFlags,
    const SkRect& drawBounds
)
```
构造路径内部三角化操作。

**参数说明：**
- `viewMatrix`：视图变换矩阵
- `path`：要填充的路径（不能是反向填充）
- `paint`：绘制参数
- `aaType`：抗锯齿类型
- `pathFlags`：路径填充标志
- `drawBounds`：绘制边界

### 核心方法

```cpp
void pushFanStencilProgram(
    const GrTessellationShader::ProgramArgs& args,
    const GrPipeline* pipelineForStencils,
    const GrUserStencilSettings* stencil
)
```
添加扇形模板程序。

```cpp
void pushFanFillProgram(
    const GrTessellationShader::ProgramArgs& args,
    const GrUserStencilSettings* stencil
)
```
添加扇形填充程序。

```cpp
void prePreparePrograms(
    const GrTessellationShader::ProgramArgs& args,
    GrAppliedClip&& appliedClip
)
```
预准备所有渲染程序。

## 内部实现细节

### 三遍渲染流程

#### 第一遍：模板曲线

```cpp
if (!isLinear) {
    fTessellator = PathCurveTessellator::Make(...);
    auto* tessShader = GrPathTessellationShader::Make(...);
    fStencilCurvesProgram = GrTessellationShader::MakeProgram(
        args, tessShader, pipelineForStencils, stencilPathSettings
    );
}
```

只有当路径包含曲线时才执行此步骤。曲线被细分为线段并写入模板缓冲区。

#### 第二遍：填充内部扇形

根据不同情况，可能生成一到两个程序：

**情况1：强制 Redbook 模板遍（线框或仅模板）**
```cpp
if (forceRedbookStencilPass) {
    this->pushFanStencilProgram(...);  // 模板遍
    if (doFill) {
        this->pushFanFillProgram(...);  // 填充遍
    }
}
```

**情况2：纯线性路径（无曲线）**
```cpp
else if (isLinear) {
    this->pushFanFillProgram(args, &GrUserStencilSettings::kUnused);
}
```

**情况3：无模板裁剪的优化模板设置**
```cpp
else if (!fPipelineForFills->hasStencilClip()) {
    // 使用特殊的模板设置，允许直接填充或继续计数
    constexpr static GrUserStencilSettings kFillOrIncrDecrStencil(...);
    this->pushFanFillProgram(args, stencil);
}
```

**情况4：有模板裁剪时使用两遍**
```cpp
else {
    // 第一遍：直接填充模板值为零的样本
    this->pushFanFillProgram(args, &kFillIfZeroAndInClip);
    // 第二遍：对非零样本进行 Redbook 计数
    this->pushFanStencilProgram(args, pipelineForStencils, stencil);
}
```

#### 第三遍：覆盖凸包

```cpp
if (doFill && !isLinear) {
    auto* hullShader = args.fArena->make<HullShader>(...);
    fCoverHullsProgram = GrTessellationShader::MakeProgram(
        args, hullShader, fPipelineForFills,
        GrPathTessellationShader::TestAndResetStencilSettings()
    );
}
```

绘制每条曲线的凸包，填充剩余像素并重置模板值。

### 凸包着色器实现

`HullShader` 生成包围曲线的四边形凸包：

```cpp
// 顶点着色器伪代码
float2 p0, p1, p2, p3;  // 四个控制点

// 对于圆锥曲线，进行特殊处理
if (is_conic_curve()) {
    float w = p3.x;  // 权重
    p3 = p2;         // 复制端点
    if (is_non_triangular_conic_curve()) {
        // 转换为梯形外壳
        float2 p1w = p1 * w;
        float T = 0.51;  // 向外偏移
        p1 = mix(p0, p1w, T) / mix(1, w, T);
        p2 = mix(p2, p1w, T) / mix(1, w, T);
    }
}

// 重新排序点，使 p2 分割 p1 和 p3
// 计算转向方向并移除非凸顶点
// 输出凸包顶点
```

### 扇形三角化

使用 `GrInnerFanTriangulator` 将路径内部转换为三角形：

```cpp
fFanTriangulator = args.fArena->make<GrInnerFanTriangulator>(fPath, args.fArena);
fFanPolys = fFanTriangulator->pathToPolys(&fFanBreadcrumbs, &isLinear);

// 在 onPrepare 中生成顶点
fFanVertexCount = fFanTriangulator->polysToTriangles(
    fFanPolys, &alloc, &fFanBreadcrumbs
);
```

### 面包屑三角形（Breadcrumb Triangles）

面包屑三角形用于连接曲线和内部扇形：
- 在三角化过程中生成
- 确保曲线和扇形之间没有间隙
- 被曲线细分器使用

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrDrawOp` | 绘制操作基类 |
| `GrInnerFanTriangulator` | 内部扇形三角化器 |
| `GrTriangulator` | 通用三角化器 |
| `PathCurveTessellator` | 曲线细分器 |
| `GrPathTessellationShader` | 路径细分着色器 |
| `GrTessellationShader` | 细分着色器基类 |
| `GrProcessorSet` | 片段处理器集合 |
| `GrPipeline` | 渲染管线 |
| `GrUserStencilSettings` | 模板设置 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRenderer` 子类 | 路径渲染器可能使用此操作 |
| `SurfaceDrawContext` | 表面绘制上下文 |

## 设计模式与设计决策

### 多遍渲染策略

采用三遍渲染而不是单遍的原因：
1. **负载均衡**：大部分像素在第二遍填充，与单遍性能相当
2. **质量保证**：曲线的模板化确保精确的边界
3. **灵活性**：可以针对不同情况优化

### 延迟决策模式

许多决策延迟到 `prePreparePrograms` 时：
- 是否需要曲线细分
- 使用多少个填充遍
- 使用何种模板设置

这允许基于实际路径特征进行优化。

### 条件编译

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
// ... 实现 ...
#endif
```
在优化大小的构建中完全移除此操作，因为它需要大量代码。

### 模板优化技巧

**优化的模板设置示例：**
```cpp
constexpr static GrUserStencilSettings kFillOrIncrDecrStencil(
    GrUserStencilSettings::StaticInitSeparate<
        0x0000, 0x0000,                      // 参考值
        GrUserStencilTest::kEqual, kEqual,   // 测试
        0xffff, 0xffff,                      // 掩码
        GrUserStencilOp::kKeep, kKeep,       // 失败操作
        GrUserStencilOp::kIncWrap, kDecWrap, // 通过操作
        0xffff, 0xffff                       // 写入掩码
    >()
);
```

这允许在单遍中同时：
- 如果模板为零，直接填充
- 如果模板非零，继续 Redbook 计数

## 性能考量

### 内存布局优化

1. **紧凑的成员变量**：使用指针而非值存储大对象
2. **竞技场分配**：大部分临时数据从竞技场分配
3. **延迟分配**：顶点缓冲区在需要时才分配

### GPU 状态切换

最小化状态切换：
- 共享模板管线
- 共享填充管线
- 批量执行程序

### 顶点数据优化

```cpp
// 中等到大型复杂路径使用专用三角形着色器
if (fTotalCombinedPathVerbCnt > 50 &&
    this->bounds().height() * this->bounds().width() > 256 * 256) {
    // 6 个浮点数每三角形而不是 8 个
    // 更高效的中间外拓扑
    fStencilFanProgram = ...;
    fTessellator = PathCurveTessellator::Make(...);
} else {
    // 使用楔形细分器
    fTessellator = PathWedgeTessellator::Make(...);
}
```

### 条件执行

```cpp
void onExecute(GrOpFlushState* flushState, const SkRect& chainBounds) {
    if (fStencilCurvesProgram) {
        // 第一遍：只有在有曲线时执行
        fTessellator->draw(flushState);
    }

    if (fFanBuffer) {
        // 第二遍：只有在有扇形时执行
        for (const GrProgramInfo* fanProgram : fFanPrograms) {
            flushState->draw(fFanVertexCount, fBaseFanVertex);
        }
    }

    if (fCoverHullsProgram) {
        // 第三遍：只有在需要时执行
        fTessellator->drawHullInstances(flushState, ...);
    }
}
```

### 静态缓冲区缓存

```cpp
SKGPU_DECLARE_STATIC_UNIQUE_KEY(gHullVertexBufferKey);

// 对于无顶点ID支持的硬件，缓存静态顶点缓冲区
constexpr static float kStripOrderIDs[4] = {0, 1, 3, 2};
fHullVertexBufferIfNoIDSupport =
    flushState->resourceProvider()->findOrMakeStaticBuffer(
        GrGpuBufferType::kVertex,
        sizeof(kStripOrderIDs),
        kStripOrderIDs,
        gHullVertexBufferKey
    );
```

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrInnerFanTriangulator.h` | 依赖 | 内部扇形三角化 |
| `GrTriangulator.h` | 依赖 | 通用三角化 |
| `PathTessellator.h` | 依赖 | 曲线细分 |
| `GrPathTessellationShader.h` | 依赖 | 路径细分着色器 |
| `FillPathFlags.h` | 依赖 | 填充标志 |
| `PathStencilCoverOp.h` | 相关 | 另一种路径填充策略 |
| `PathTessellateOp.h` | 相关 | 单遍路径细分 |
