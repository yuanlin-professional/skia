# StrokeTessellator

> 源文件
> - `src/gpu/ganesh/tessellate/StrokeTessellator.h`
> - `src/gpu/ganesh/tessellate/StrokeTessellator.cpp`

## 概述

`StrokeTessellator` 是 Ganesh 笔画渲染系统中的核心细分器,负责准备和绘制笔画的细分几何体。它使用固定段数三角带实例(fixed-count triangle strip instances)渲染笔画,将路径笔画转换为 GPU 可渲染的顶点数据。该类处理各种曲线类型(直线、二次曲线、圆锥曲线、三次曲线)的细分,自动检测和处理尖点(cusp)和 180 度转折,支持动态和静态笔画参数,并针对不支持 `sk_VertexID` 的硬件提供回退方案。

## 架构位置

`StrokeTessellator` 位于 Ganesh 细分曲面渲染管线的笔画细分层:

```
Skia GPU 笔画渲染架构
├── 路径和笔画描述层
│   ├── SkPath (路径)
│   └── SkStrokeRec (笔画记录)
├── 笔画迭代层
│   └── StrokeIterator (笔画迭代器)
├── 细分器层
│   ├── StrokeTessellator (笔画细分器) ← 当前类
│   └── PatchWriter (补丁写入器)
├── 顶点管理层
│   ├── GrVertexChunkArray (顶点块数组)
│   └── VertexChunkPatchAllocator (顶点块补丁分配器)
└── GPU 绘制层
    ├── GrMeshDrawTarget (网格绘制目标)
    └── GrOpFlushState (操作刷新状态)
```

该类是笔画从 CPU 路径描述到 GPU 顶点数据的关键转换器。

## 主要类与结构体

### 类继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `StrokeTessellator` | 独立类 | 笔画细分器主类 |

### 嵌套结构体

#### PathStrokeList

链表结构,存储多个路径-笔画-颜色组合:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fPath` | `SkPath` | 要细分的路径 |
| `fStroke` | `SkStrokeRec` | 笔画描述(宽度、帽样式、连接样式) |
| `fColor` | `SkPMColor4f` | 预乘 Alpha 颜色 |
| `fNext` | `PathStrokeList*` | 链表下一节点 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAttribs` | `PatchAttribs` | 补丁属性(始终包含 `kJoinControlPoint`) |
| `fVertexChunkArray` | `GrVertexChunkArray` | 顶点数据块数组 |
| `fVertexCount` | `int` | 每个补丁的顶点数 |
| `fVertexBufferIfNoIDSupport` | `sk_sp<const GrGpuBuffer>` | 回退顶点缓冲区(不支持 `sk_VertexID` 时) |

### 类型别名

```cpp
using PatchAttribs = tess::PatchAttribs;
```

可能的属性标志:
- `kJoinControlPoint`: 连接控制点(始终包含)
- `kStrokeParams`: 动态笔画参数
- `kColor`: 动态颜色
- `kWideColorIfEnabled`: 宽色域颜色
- `kExplicitCurveType`: 显式曲线类型

## 公共 API 函数

### 构造函数

```cpp
StrokeTessellator(PatchAttribs attribs);
```
初始化细分器,自动添加 `kJoinControlPoint` 属性:
```cpp
: fAttribs(attribs | PatchAttribs::kJoinControlPoint)
```

### 准备阶段

```cpp
void prepare(GrMeshDrawTarget* target,
             const SkMatrix& shaderMatrix,
             PathStrokeList* pathStrokeList,
             int totalCombinedStrokeVerbCnt);
```
在绘制前准备 GPU 缓冲区,包含要细分的几何体。

**参数:**
- `target`: 网格绘制目标,提供资源分配器
- `shaderMatrix`: 着色器变换矩阵(用于 Wang's Formula)
- `pathStrokeList`: 路径-笔画链表
- `totalCombinedStrokeVerbCnt`: 总笔画动词数(用于预分配)

**返回:** 通过 `fVertexCount` 返回每个补丁的固定边数。

### 绘制阶段

```cpp
void draw(GrOpFlushState* flushState) const;
```
发出细分笔画的绘制调用。调用者负责在调用前创建并绑定使用该类着色器的管线。

**实现:**
```cpp
for (const auto& instanceChunk : fVertexChunkArray) {
    flushState->bindBuffers(nullptr, instanceChunk.fBuffer, fVertexBufferIfNoIDSupport);
    flushState->drawInstanced(instanceChunk.fCount,
                              instanceChunk.fBase,
                              fVertexCount,
                              0);
}
```

## 内部实现细节

### StrokeWriter 类型

```cpp
using StrokeWriter = PatchWriter<
    VertexChunkPatchAllocator,
    Required<PatchAttribs::kJoinControlPoint>,
    Optional<PatchAttribs::kStrokeParams>,
    Optional<PatchAttribs::kColor>,
    Optional<PatchAttribs::kWideColorIfEnabled>,
    Optional<PatchAttribs::kExplicitCurveType>,
    ReplicateLineEndPoints,
    TrackJoinControlPoints>;
```

类型安全的补丁写入器,支持:
- 必需的连接控制点
- 可选的动态笔画参数、颜色、曲线类型
- 直线端点复制(用于连接)
- 连接控制点跟踪

### 固定段数补丁写入流程

```cpp
void write_fixed_count_patches(StrokeWriter&& patchWriter,
                               const SkMatrix& shaderMatrix,
                               PathStrokeList* pathStrokeList) {
    // 设置着色器变换
    patchWriter.setShaderTransform(
        wangs_formula::VectorXform{shaderMatrix},
        std::abs(shaderMatrix.getMaxScale()));

    // 静态笔画:一次性计算容差
    if (!(patchWriter.attribs() & PatchAttribs::kStrokeParams)) {
        patchWriter.updateUniformStrokeParams(pathStrokeList->fStroke);
    }

    // 遍历所有路径-笔画对
    for (auto* pathStroke = pathStrokeList; pathStroke; pathStroke = pathStroke->fNext) {
        // 动态笔画:每次更新
        if (patchWriter.attribs() & PatchAttribs::kStrokeParams) {
            patchWriter.updateStrokeParamsAttrib(stroke);
        }
        if (patchWriter.attribs() & PatchAttribs::kColor) {
            patchWriter.updateColorAttrib(pathStroke->fColor);
        }

        // 迭代笔画段
        StrokeIterator strokeIter(pathStroke->fPath, &pathStroke->fStroke, &shaderMatrix);
        while (strokeIter.next()) {
            // 处理各种动词...
        }
    }

    // 刷新最后记录的轮廓
    patchWriter.writeDeferredStrokePatch();
}
```

### 曲线类型处理

#### 1. 直线

```cpp
case Verb::kLine:
    patchWriter.writeLine(p[0], p[1]);
    break;
```

#### 2. 二次曲线(检测尖点)

```cpp
case Verb::kQuad:
    if (ConicHasCusp(p)) {
        // 尖点始终在中切线处
        SkPoint cusp = SkEvalQuadAt(p, SkFindQuadMidTangent(p));
        patchWriter.writeCircle(cusp);  // 圆形帽
        // 二次曲线只有在平坦且 180 度转折时才有尖点
        patchWriter.writeLine(p[0], cusp);
        patchWriter.writeLine(cusp, p[2]);
    } else {
        patchWriter.writeQuadratic(p);
    }
    break;
```

#### 3. 圆锥曲线(检测尖点)

```cpp
case Verb::kConic:
    if (ConicHasCusp(p)) {
        SkConic conic(p, strokeIter.w());
        SkPoint cusp = conic.evalAt(conic.findMidTangent());
        patchWriter.writeCircle(cusp);
        patchWriter.writeLine(p[0], cusp);
        patchWriter.writeLine(cusp, p[2]);
    } else {
        patchWriter.writeConic(p, strokeIter.w());
    }
    break;
```

#### 4. 三次曲线(检测 180 度转折和尖点)

```cpp
case Verb::kCubic:
    SkPoint chops[10];
    float T[2];
    bool areCusps;
    numChops = FindCubicConvex180Chops(p, T, &areCusps);

    if (numChops == 0) {
        // 无转折,直接写入
        patchWriter.writeCubic(p);
    } else if (numChops == 1) {
        // 一个转折点
        SkChopCubicAt(p, chops, T[0]);
        if (areCusps) {
            patchWriter.writeCircle(chops[3]);
            chops[2] = chops[4] = chops[3];  // 尖点处三点重合
        }
        patchWriter.writeCubic(chops);
        patchWriter.writeCubic(chops + 3);
    } else {
        // 两个转折点
        SkASSERT(numChops == 2);
        SkChopCubicAt(p, chops, T[0], T[1]);
        if (areCusps) {
            patchWriter.writeCircle(chops[3]);
            patchWriter.writeCircle(chops[6]);
            // 两个尖点仅在平坦线段有两个 180 度转折时可能
            patchWriter.writeLine(chops[0], chops[3]);
            patchWriter.writeLine(chops[3], chops[6]);
            patchWriter.writeLine(chops[6], chops[9]);
        } else {
            patchWriter.writeCubic(chops);
            patchWriter.writeCubic(chops + 3);
            patchWriter.writeCubic(chops + 6);
        }
    }
    break;
```

#### 5. 特殊动词

```cpp
case Verb::kCircle:
    // 圆形帽或空笔画指定为圆形
    patchWriter.writeCircle(p[0]);
    [[fallthrough]];
case Verb::kMoveWithinContour:
    // 常规 kMove 使上一个控制点失效
    patchWriter.updateJoinControlPointAttrib(p[0]);
    break;

case Verb::kContourFinished:
    patchWriter.writeDeferredStrokePatch();
    break;
```

### 准备阶段实现

```cpp
void StrokeTessellator::prepare(GrMeshDrawTarget* target,
                                const SkMatrix& shaderMatrix,
                                PathStrokeList* pathStrokeList,
                                int totalCombinedStrokeVerbCnt) {
    LinearTolerances worstCase;
    const int preallocCount = FixedCountStrokes::PreallocCount(totalCombinedStrokeVerbCnt);
    StrokeWriter patchWriter{fAttribs, &worstCase, target, &fVertexChunkArray, preallocCount};

    write_fixed_count_patches(std::move(patchWriter), shaderMatrix, pathStrokeList);
    fVertexCount = FixedCountStrokes::VertexCount(worstCase);

    // 处理不支持 sk_VertexID 的硬件
    if (!target->caps().shaderCaps()->fVertexIDSupport) {
        fVertexCount = std::min(fVertexCount, 2 * FixedCountStrokes::kMaxEdgesNoVertexIDs);

        SKGPU_DEFINE_STATIC_UNIQUE_KEY(gVertexIDFallbackBufferKey);

        fVertexBufferIfNoIDSupport = target->resourceProvider()->findOrMakeStaticBuffer(
            GrGpuBufferType::kVertex,
            FixedCountStrokes::VertexBufferSize(),
            gVertexIDFallbackBufferKey,
            FixedCountStrokes::WriteVertexBuffer);
    }
}
```

### 绘制阶段实现

```cpp
void StrokeTessellator::draw(GrOpFlushState* flushState) const {
    if (fVertexChunkArray.empty() || fVertexCount <= 0) {
        return;  // 无内容
    }
    if (!flushState->caps().shaderCaps()->fVertexIDSupport &&
        !fVertexBufferIfNoIDSupport) {
        return;  // 回退缓冲区创建失败
    }

    // 实例化绘制每个顶点块
    for (const auto& instanceChunk : fVertexChunkArray) {
        flushState->bindBuffers(nullptr,                      // 无索引缓冲区
                                instanceChunk.fBuffer,        // 实例缓冲区
                                fVertexBufferIfNoIDSupport);  // 顶点缓冲区(或 nullptr)
        flushState->drawInstanced(instanceChunk.fCount,  // 实例数
                                  instanceChunk.fBase,   // 基实例
                                  fVertexCount,          // 每实例顶点数
                                  0);                    // 基顶点
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrMeshDrawTarget` | 强依赖 | 提供资源分配和能力查询 |
| `GrOpFlushState` | 强依赖 | 执行绘制调用 |
| `GrVertexChunkArray` | 强依赖 | 存储顶点数据块 |
| `VertexChunkPatchAllocator` | 强依赖 | 分配补丁内存 |
| `PatchWriter` | 核心依赖 | 类型安全的补丁写入 |
| `StrokeIterator` | 核心依赖 | 迭代笔画段 |
| `FixedCountBufferUtils` | 工具 | 固定段数缓冲区工具 |
| `LinearTolerances` | 工具 | 线性容差计算 |
| `WangsFormula` | 工具 | 计算细分段数 |
| `SkGeometry` | 工具 | 几何操作(切分、尖点检测) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 笔画渲染操作 | 使用 StrokeTessellator 渲染笔画 |
| GrStrokeOp | 调用 prepare 和 draw |

## 设计模式与设计决策

### 两阶段渲染

**准备阶段** (`prepare`):
- 分配和填充 GPU 缓冲区
- 计算所需顶点数
- 可在后台线程执行(未来优化)

**绘制阶段** (`draw`):
- 仅发出绘制调用
- 必须在渲染线程执行
- 轻量级,支持多次绘制

### 固定段数策略

使用 Wang's Formula 计算最坏情况段数,所有实例使用相同顶点数:
```cpp
fVertexCount = FixedCountStrokes::VertexCount(worstCase);
```
优点:
- 简化实例化绘制(统一顶点数)
- 避免动态顶点缓冲区管理
- GPU 友好的批处理

缺点:
- 简单曲线生成多余三角形(退化为点/线)

### 尖点和转折处理

自动检测和切分有问题的曲线:
```cpp
numChops = FindCubicConvex180Chops(p, T, &areCusps);
if (numChops > 0) {
    SkChopCubicAt(p, chops, T[0], T[1]);
    // 单独处理每段
}
```
确保笔画连接和帽正确渲染。

### 硬件适配

为不支持 `sk_VertexID` 的硬件提供回退:
```cpp
if (!target->caps().shaderCaps()->fVertexIDSupport) {
    fVertexBufferIfNoIDSupport = ...;  // 预生成 ID 缓冲区
}
```

### 静态缓冲区复用

回退 ID 缓冲区使用静态唯一键:
```cpp
SKGPU_DEFINE_STATIC_UNIQUE_KEY(gVertexIDFallbackBufferKey);
fVertexBufferIfNoIDSupport = target->resourceProvider()->findOrMakeStaticBuffer(...);
```
多个帧和上下文共享同一缓冲区。

## 性能考量

### 预分配优化

```cpp
const int preallocCount = FixedCountStrokes::PreallocCount(totalCombinedStrokeVerbCnt);
```
根据动词数预估所需补丁数,避免动态扩容。

### Wang's Formula 向量变换

```cpp
patchWriter.setShaderTransform(
    wangs_formula::VectorXform{shaderMatrix},
    std::abs(shaderMatrix.getMaxScale()));
```
预计算变换,准确估算参数空间段数,避免过度细分。

### 批量处理

所有路径-笔画对合并到单个顶点块数组:
```cpp
for (auto* pathStroke = pathStrokeList; pathStroke; pathStroke = pathStroke->fNext) {
    // 写入同一 patchWriter
}
```
减少绘制调用次数。

### 实例化绘制

```cpp
flushState->drawInstanced(instanceChunk.fCount, instanceChunk.fBase, fVertexCount, 0);
```
利用 GPU 实例化,一次绘制多个笔画段。

### 静态/动态属性分离

静态笔画参数:
```cpp
if (!(patchWriter.attribs() & PatchAttribs::kStrokeParams)) {
    patchWriter.updateUniformStrokeParams(pathStrokeList->fStroke);
}
```
仅计算一次,减少每段开销。

动态参数每段更新:
```cpp
if (patchWriter.attribs() & PatchAttribs::kStrokeParams) {
    patchWriter.updateStrokeParamsAttrib(stroke);
}
```

### 最大边数限制

不支持 `sk_VertexID` 时限制边数:
```cpp
fVertexCount = std::min(fVertexCount, 2 * FixedCountStrokes::kMaxEdgesNoVertexIDs);
```
确保回退缓冲区足够大。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/tessellate/PatchWriter.h` | 核心 | 补丁写入器模板 |
| `src/gpu/tessellate/StrokeIterator.h` | 依赖 | 笔画段迭代器 |
| `src/gpu/ganesh/GrVertexChunkArray.h` | 依赖 | 顶点块数组 |
| `src/gpu/ganesh/tessellate/VertexChunkPatchAllocator.h` | 依赖 | 补丁分配器 |
| `src/gpu/tessellate/FixedCountBufferUtils.h` | 工具 | 固定段数工具 |
| `src/gpu/tessellate/WangsFormula.h` | 工具 | Wang's Formula |
| `src/gpu/tessellate/LinearTolerances.h` | 工具 | 线性容差 |
| `src/core/SkGeometry.h` | 工具 | 几何操作 |
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 协作 | 网格绘制目标 |
| `src/gpu/ganesh/GrOpFlushState.h` | 协作 | 操作刷新状态 |
