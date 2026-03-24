# PathTessellateOp

> 源文件
> - `src/gpu/ganesh/ops/PathTessellateOp.h`
> - `src/gpu/ganesh/ops/PathTessellateOp.cpp`

## 概述

`PathTessellateOp` 是 Ganesh GPU 后端中用于路径渲染的单遍细分操作。与其他多遍路径渲染方法不同，该操作通过一次渲染通道直接将路径细分到颜色缓冲区，目前仅支持凸路径（convex paths）的渲染。

该操作使用楔形细分器（Wedge Tessellator）将路径分解为三角形扇形，这种方法对于简单的凸路径非常高效，避免了模板缓冲区的使用和多遍渲染的开销。

## 架构位置

在 Skia 的 Ganesh 架构中，`PathTessellateOp` 位于以下层次：

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          GrOp (基类)
            GrDrawOp
              └── PathTessellateOp
        tessellate/
          PathTessellator (细分器基类)
            └── PathWedgeTessellator (楔形细分器)
```

它是 Ganesh 路径渲染系统中针对凸路径优化的快速路径。

## 主要类与结构体

### PathTessellateOp

单遍路径细分操作类。

**继承关系：** `GrDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAAType` | `GrAAType` | 抗锯齿类型（常量） |
| `fStencil` | `const GrUserStencilSettings*` | 模板设置（常量） |
| `fTotalCombinedPathVerbCnt` | `int` | 合并后的路径动词总数 |
| `fPatchAttribs` | `PatchAttribs` | 补丁属性标志 |
| `fPathDrawList` | `PathDrawList*` | 路径绘制列表头（常量） |
| `fPathDrawTail` | `PathDrawList**` | 路径绘制列表尾指针 |
| `fProcessors` | `GrProcessorSet` | 片段处理器集合 |
| `fShaderMatrix` | `SkMatrix` | 着色器变换矩阵 |
| `fTessellator` | `PathTessellator*` | 细分器实例 |
| `fTessellationProgram` | `const GrProgramInfo*` | 细分程序信息 |

### PathDrawList (类型别名)

```cpp
using PathDrawList = PathTessellator::PathDrawList;
```

路径绘制列表，包含路径、变换矩阵和颜色信息。

## 公共 API 函数

### 构造函数（私有）

```cpp
PathTessellateOp(
    SkArenaAlloc* arena,
    GrAAType aaType,
    const GrUserStencilSettings* stencil,
    const SkMatrix& viewMatrix,
    const SkPath& path,
    GrPaint&& paint,
    const SkRect& drawBounds
)
```
构造路径细分操作。

**参数说明：**
- `arena`：竞技场分配器
- `aaType`：抗锯齿类型
- `stencil`：模板设置
- `viewMatrix`：视图变换矩阵
- `path`：要绘制的路径（不能是反向填充）
- `paint`：绘制参数
- `drawBounds`：绘制边界

### 核心方法

```cpp
void prepareTessellator(
    const GrTessellationShader::ProgramArgs& args,
    GrAppliedClip&& clip
)
```
准备细分器和程序。

```cpp
void visitProxies(const GrVisitProxyFunc& func) const
```
访问代理。

```cpp
GrProcessorSet::Analysis finalize(
    const GrCaps& caps,
    const GrAppliedClip* clip,
    GrClampType clampType
)
```
最终化处理器。

```cpp
CombineResult onCombineIfPossible(
    GrOp* grOp,
    SkArenaAlloc* arena,
    const GrCaps& caps
)
```
尝试与另一个操作合并。

## 内部实现细节

### 细分器准备

```cpp
void PathTessellateOp::prepareTessellator(
    const GrTessellationShader::ProgramArgs& args,
    GrAppliedClip&& appliedClip
) {
    // 创建管线
    auto* pipeline = GrTessellationShader::MakePipeline(
        args, fAAType, std::move(appliedClip), std::move(fProcessors)
    );

    // 创建楔形细分器
    fTessellator = PathWedgeTessellator::Make(
        args.fArena,
        args.fCaps->shaderCaps()->fInfinitySupport,
        fPatchAttribs
    );

    // 创建细分着色器
    auto* tessShader = GrPathTessellationShader::Make(
        *args.fCaps->shaderCaps(),
        args.fArena,
        fShaderMatrix,
        this->headDraw().fColor,
        fTessellator->patchAttribs()
    );

    // 创建程序信息
    fTessellationProgram = GrTessellationShader::MakeProgram(
        args, tessShader, pipeline, fStencil
    );
}
```

### 处理器最终化优化

```cpp
GrProcessorSet::Analysis PathTessellateOp::finalize(...) {
    auto analysis = fProcessors.finalize(
        this->headDraw().fColor,
        GrProcessorAnalysisCoverage::kNone,
        clip, nullptr, caps, clampType,
        &this->headDraw().fColor
    );

    if (!analysis.usesLocalCoords()) {
        // 不需要本地坐标，可以在 CPU 上变换
        this->headDraw().fPathMatrix = fShaderMatrix;
        fShaderMatrix = SkMatrix::I();
    }

    return analysis;
}
```

**优化原理：**
- 如果不使用本地坐标（纹理映射等），可以在 CPU 上应用变换
- 所有路径使用相同的着色器矩阵，提高批处理效率
- 在 CPU 上变换比在 GPU 上更高效

### 操作合并

```cpp
GrDrawOp::CombineResult PathTessellateOp::onCombineIfPossible(
    GrOp* grOp,
    SkArenaAlloc* arena,
    const GrCaps& caps
) {
    auto* op = grOp->cast<PathTessellateOp>();

    // 检查是否会溢出
    bool verbCountOverflow =
        std::numeric_limits<int>::max() - fTotalCombinedPathVerbCnt <
        op->fTotalCombinedPathVerbCnt;

    // 检查兼容性
    bool canMerge =
        fAAType == op->fAAType &&
        fStencil == op->fStencil &&
        fProcessors == op->fProcessors &&
        fShaderMatrix == op->fShaderMatrix &&
        !verbCountOverflow;

    if (canMerge) {
        // 合并路径列表
        fTotalCombinedPathVerbCnt += op->fTotalCombinedPathVerbCnt;
        fPatchAttribs |= op->fPatchAttribs;

        // 如果颜色不再统一，移到补丁属性中
        if (!(fPatchAttribs & PatchAttribs::kColor) &&
            this->headDraw().fColor != op->headDraw().fColor) {
            fPatchAttribs |= PatchAttribs::kColor;
        }

        // 链接路径列表
        *fPathDrawTail = op->fPathDrawList;
        fPathDrawTail = op->fPathDrawTail;

        return CombineResult::kMerged;
    }

    return CombineResult::kCannotCombine;
}
```

### 准备和执行流程

```cpp
void PathTessellateOp::onPrepare(GrOpFlushState* flushState) {
    if (!fTessellator) {
        this->prepareTessellator(...);
    }

    // 准备细分数据
    fTessellator->prepare(
        flushState,
        fShaderMatrix,
        *fPathDrawList,
        fTotalCombinedPathVerbCnt
    );
}

void PathTessellateOp::onExecute(
    GrOpFlushState* flushState,
    const SkRect& chainBounds
) {
    // 绑定管线和裁剪
    flushState->bindPipelineAndScissorClip(*fTessellationProgram, this->bounds());

    // 绑定纹理
    flushState->bindTextures(
        fTessellationProgram->geomProc(),
        nullptr,
        fTessellationProgram->pipeline()
    );

    // 绘制
    fTessellator->draw(flushState);
}
```

### 补丁属性管理

```cpp
// 构造函数中初始化
PathTessellateOp(...) {
    if (!this->headDraw().fColor.fitsInBytes()) {
        fPatchAttribs |= PatchAttribs::kWideColorIfEnabled;
    }
}

// 合并时更新
if (!(fPatchAttribs & PatchAttribs::kColor) &&
    this->headDraw().fColor != op->headDraw().fColor) {
    fPatchAttribs |= PatchAttribs::kColor;
}
```

**补丁属性：**
- `kNone`：无额外属性
- `kColor`：每个补丁有不同颜色
- `kWideColorIfEnabled`：使用宽色域颜色

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrDrawOp` | 绘制操作基类 |
| `PathTessellator` | 路径细分器基类 |
| `PathWedgeTessellator` | 楔形细分器 |
| `GrPathTessellationShader` | 路径细分着色器 |
| `GrTessellationShader` | 细分着色器基类 |
| `GrProcessorSet` | 片段处理器集合 |
| `GrPipeline` | 渲染管线 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRenderer` | 路径渲染器可能使用此操作 |
| `SurfaceDrawContext` | 表面绘制上下文 |

## 设计模式与设计决策

### 单遍优化策略

相比多遍算法（如 PathInnerTriangulateOp）的优势：
1. **更少的 GPU 状态切换**
2. **不需要模板缓冲区**
3. **更简单的代码路径**

限制：
- 仅适用于凸路径
- 非凸路径需要使用其他操作

### CPU 变换优化

```cpp
if (!analysis.usesLocalCoords()) {
    this->headDraw().fPathMatrix = fShaderMatrix;
    fShaderMatrix = SkMatrix::I();
}
```

当不需要本地坐标时，在 CPU 上应用变换：
- 减少 GPU 计算
- 提高着色器效率
- 更好的批处理

### 延迟细分器创建

细分器在 `prepareTessellator` 或 `onPrepare` 时创建：
- 支持 DDL 模式
- 允许操作合并
- 延迟资源分配

### 路径列表链接

使用单链表管理多个路径：
```cpp
PathDrawList* const fPathDrawList;
PathDrawList** fPathDrawTail;
```

**优势：**
- O(1) 合并操作
- 最小内存开销
- 保持绘制顺序

## 性能考量

### 批处理优化

1. **合并检查**：
   - 抗锯齿类型
   - 模板设置
   - 处理器集
   - 着色器矩阵

2. **动词计数限制**：防止整数溢出

3. **颜色处理**：
   - 统一颜色：使用着色器常量
   - 变化颜色：使用顶点属性

### 内存效率

1. **竞技场分配**：路径列表从竞技场分配
2. **指针链接**：避免数组重新分配
3. **紧凑属性**：使用位标志

### GPU 效率

1. **单遍渲染**：最小化渲染通道
2. **无模板使用**：节省带宽
3. **批量绘制**：合并多个路径

### 宽色域支持

```cpp
if (!this->headDraw().fColor.fitsInBytes()) {
    fPatchAttribs |= PatchAttribs::kWideColorIfEnabled;
}
```

只在需要时启用宽色域，节省顶点属性空间。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `PathWedgeTessellator.h` | 依赖 | 楔形细分器 |
| `GrPathTessellationShader.h` | 依赖 | 路径细分着色器 |
| `PathInnerTriangulateOp.h` | 对比 | 多遍路径填充 |
| `PathStencilCoverOp.h` | 对比 | 模板覆盖路径填充 |
| `GrTessellationShader.h` | 依赖 | 细分着色器基类 |
| `PathTessellator.h` | 依赖 | 细分器基类 |
