# PathStencilCoverOp

> 源文件
> - `src/gpu/ganesh/ops/PathStencilCoverOp.h`
> - `src/gpu/ganesh/ops/PathStencilCoverOp.cpp`

## 概述

`PathStencilCoverOp` 是 Ganesh GPU 后端中使用标准 Redbook "先模板后覆盖"方法绘制路径的操作。该操作将路径曲线线性化（通过 GPU 细分着色器或间接绘制），并使用两遍渲染：第一遍将路径写入模板缓冲区，第二遍根据模板测试填充路径。该操作不应用分析抗锯齿，需要 MSAA 来实现抗锯齿效果。

这是最经典的路径填充算法，适用于所有类型的路径（包括非凸路径和含孔路径），是最通用的路径渲染策略。

## 架构位置

```
skia/src/gpu/ganesh/ops/
  PathStencilCoverOp
    ├── 继承自 GrDrawOp
    ├── 使用 PathTessellator (曲线/楔形细分)
    └── 使用 BoundingBoxShader (覆盖着色器)
```

## 主要类与结构体

### PathStencilCoverOp

**继承关系：** `GrDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPathDrawList` | `const PathDrawList*` | 路径绘制列表 |
| `fTotalCombinedPathVerbCnt` | `int` | 总路径动词数 |
| `fPathCount` | `int` | 路径数量 |
| `fPathFlags` | `FillPathFlags` | 路径填充标志 |
| `fAAType` | `GrAAType` | 抗锯齿类型 |
| `fColor` | `SkPMColor4f` | 填充颜色 |
| `fProcessors` | `GrProcessorSet` | 片段处理器集 |
| `fTessellator` | `PathTessellator*` | 路径细分器 |
| `fStencilFanProgram` | `const GrProgramInfo*` | 模板扇形程序 |
| `fStencilPathProgram` | `const GrProgramInfo*` | 模板路径程序 |
| `fCoverBBoxProgram` | `const GrProgramInfo*` | 覆盖边界框程序 |
| `fFanBuffer` | `sk_sp<const GrBuffer>` | 扇形顶点缓冲区 |
| `fBBoxBuffer` | `sk_sp<const GrBuffer>` | 边界框缓冲区 |

### BoundingBoxShader

内部几何处理器，用于绘制路径的边界框。

**关键特性：**
- 填充路径的边界框
- 亚像素外扩以避免 T-junction
- 根据模板测试填充颜色

## 公共 API 函数

### 构造函数（私有）

```cpp
PathStencilCoverOp(
    SkArenaAlloc* arena,
    const SkMatrix& viewMatrix,
    const SkPath& path,
    GrPaint&& paint,
    GrAAType aaType,
    FillPathFlags pathFlags,
    const SkRect& drawBounds
)
```

对于反向填充路径，`drawBounds` 必须是渲染目标的整个后备存储尺寸。

### 核心方法

```cpp
void prePreparePrograms(
    const GrTessellationShader::ProgramArgs& args,
    GrAppliedClip&& clip
)
```
选择渲染方法并创建细分器和模板/覆盖程序。

```cpp
SkPathFillType pathFillType() const
```
返回路径填充类型（所有路径必须相同）。

## 内部实现细节

### 两遍渲染流程

#### 第一遍：模板路径

根据路径复杂度选择策略：

**大型复杂路径（>50动词且面积>256×256）：**
```cpp
// 使用专用的三角形扇形着色器
auto shader = GrPathTessellationShader::MakeSimpleTriangleShader(...);
fStencilFanProgram = GrTessellationShader::MakeProgram(
    args, shader, stencilPipeline, stencilSettings
);
fTessellator = PathCurveTessellator::Make(...);
```

**小型或简单路径：**
```cpp
// 使用楔形细分器
fTessellator = PathWedgeTessellator::Make(...);
```

**曲线细分：**
```cpp
auto* tessShader = GrPathTessellationShader::Make(...);
fStencilPathProgram = GrTessellationShader::MakeProgram(
    args, tessShader, stencilPipeline, stencilSettings
);
```

#### 第二遍：覆盖边界框

```cpp
if (!(fPathFlags & FillPathFlags::kStencilOnly)) {
    auto* bboxShader = args.fArena->make<BoundingBoxShader>(...);
    auto* bboxPipeline = GrTessellationShader::MakePipeline(...);
    auto* bboxStencil = GrPathTessellationShader::TestAndResetStencilSettings(
        SkPathFillType_IsInverse(this->pathFillType())
    );
    fCoverBBoxProgram = ...;
}
```

### 边界框着色器实现

```glsl
// 顶点着色器伪代码
float2x2 M = inverse(float2x2(matrix2d));
float2 bloat = (abs(M[0]) + abs(M[1])) * 0.25;  // 0.25像素外扩

float2 localcoord = mix(
    pathBounds.xy - bloat,
    pathBounds.zw + bloat,
    unitCoord
);
float2 vertexpos = matrix2d * localcoord + translate;
```

**外扩的目的：**
- 确保重置所有模板值
- 避免边界上的 T-junction 问题
- 保证完全覆盖

### 扇形三角化

对于大型复杂路径，生成中间外拓扑的三角形扇形：

```cpp
// 准备扇形顶点
GrEagerDynamicVertexAllocator vertexAlloc(...);

for (auto [pathMatrix, path, color] : *fPathDrawList) {
    tess::AffineMatrix m(pathMatrix);
    for (tess::PathMiddleOutFanIter it(path); !it.done();) {
        for (auto [p0, p1, p2] : it.nextStack()) {
            // 写入三角形顶点
            triangleVertexWriter << m.map2Points(p0, p1) << m.mapPoint(p2);
            ++fanTriangleCount;
        }
    }
}
```

**中间外拓扑的优势：**
- PCI 带宽更小（6浮点数/三角形 vs 8浮点数）
- 更好的缓存局部性
- GPU 友好的拓扑

### 模板设置选择

```cpp
const GrUserStencilSettings* stencilSettings =
    GrPathTessellationShader::StencilPathSettings(
        GrFillRuleForPathFillType(this->pathFillType())
    );
```

根据填充规则选择：
- 偶奇规则：使用反转操作
- 非零缠绕规则：使用递增/递减操作

### CPU 路径变换

```cpp
// 在 CPU 上变换路径
const SkMatrix& shaderMatrix = SkMatrix::I();

// 这允许更好的批处理
for (auto [pathMatrix, path, color] : *fPathDrawList) {
    // pathMatrix 包含实际变换
}
```

所有路径使用相同的着色器矩阵（单位矩阵），实际变换在 CPU 上完成。

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrDrawOp` | 绘制操作基类 |
| `PathTessellator` | 路径细分器 |
| `PathCurveTessellator` | 曲线细分器 |
| `PathWedgeTessellator` | 楔形细分器 |
| `GrPathTessellationShader` | 路径细分着色器 |
| `PathMiddleOutFanIter` | 中间外扇形迭代器 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRenderer` | 路径渲染器 |
| `SurfaceDrawContext` | 表面绘制上下文 |

## 设计模式与设计决策

### 策略模式

根据路径特征选择不同的细分策略：
- 大型复杂路径：专用扇形 + 曲线细分
- 小型简单路径：楔形细分

### 两遍标准算法

使用经典的模板-覆盖方法：
1. **通用性**：适用于所有路径类型
2. **可靠性**：经过广泛测试
3. **兼容性**：所有 GPU 都支持

### CPU 变换优化

在 CPU 上变换路径而非 GPU：
- 更好的批处理
- 减少着色器变化
- 提高缓存效率

### 条件程序创建

只在需要时创建扇形程序：
```cpp
if (fTotalCombinedPathVerbCnt > 50 && area > 256*256) {
    // 创建专用扇形程序
}
```

## 性能考量

### 路径复杂度阈值

使用50个动词和256×256像素作为阈值：
- 小路径：使用简单策略
- 大路径：使用优化策略

### 模板带宽优化

通过两遍算法减少模板操作：
- 第一遍：只写模板
- 第二遍：测试模板并填充颜色

### 扇形三角化优化

中间外拓扑减少：
- PCI 带宽（6 vs 8浮点数）
- 提升 GPU 缓存效率

### 静态缓冲区复用

```cpp
SKGPU_DECLARE_STATIC_UNIQUE_KEY(gUnitQuadBufferKey);

// 单位四边形缓冲区在多次绘制间复用
fBBoxVertexBufferIfNoIDSupport =
    flushState->resourceProvider()->findOrMakeStaticBuffer(...);
```

### 溢出保护

```cpp
if ((std::numeric_limits<int>::max() >> 2) < maxTrianglesInFans) SK_UNLIKELY {
    SKIA_LOG_W("Excessive triangle count, dropping draw: %d", maxTrianglesInFans);
    return;
}
```

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `PathTessellator.h` | 依赖 | 细分器基类 |
| `GrPathTessellationShader.h` | 依赖 | 路径细分着色器 |
| `PathInnerTriangulateOp.h` | 对比 | 三遍路径填充 |
| `PathTessellateOp.h` | 对比 | 单遍凸路径填充 |
| `MiddleOutPolygonTriangulator.h` | 依赖 | 中间外三角化 |
| `FillPathFlags.h` | 依赖 | 填充标志 |
