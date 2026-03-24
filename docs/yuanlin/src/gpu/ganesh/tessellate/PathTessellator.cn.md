# PathTessellator

> 源文件
> - `src/gpu/ganesh/tessellate/PathTessellator.h`
> - `src/gpu/ganesh/tessellate/PathTessellator.cpp`

## 概述

`PathTessellator` 是 Ganesh 路径渲染系统中的核心细分器基类,负责准备和绘制路径的细分几何体。该类提供两个具体实现:`PathCurveTessellator`(绘制独立外曲线补丁)和 `PathWedgeTessellator`(绘制楔形补丁)。它使用固定段数实例化绘制,将路径转换为 GPU 可渲染的顶点数据,支持动态颜色、宽色域和显式曲线类型,并自动处理曲线切分和内三角化。

## 架构位置

```
Skia GPU 路径渲染架构
├── 路径描述层
│   └── SkPath (路径)
├── 细分器基类层
│   └── PathTessellator (路径细分器基类) ← 当前类
├── 具体细分器层
│   ├── PathCurveTessellator (外曲线细分器)
│   └── PathWedgeTessellator (楔形细分器)
├── 补丁写入层
│   ├── CurveWriter (曲线补丁写入器)
│   └── WedgeWriter (楔形补丁写入器)
└── GPU 绘制层
    ├── GrMeshDrawTarget (网格绘制目标)
    └── GrOpFlushState (操作刷新状态)
```

## 主要类与结构体

### 继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `PathTessellator` | 抽象基类 | 路径细分器通用接口 |
| `PathCurveTessellator` | 派生类 | 外曲线补丁细分器 |
| `PathWedgeTessellator` | 派生类 | 楔形补丁细分器 |

### 嵌套结构体 - PathDrawList

链表结构,存储多个路径-矩阵-颜色组合:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fPathMatrix` | `SkMatrix` | 路径变换矩阵 |
| `fPath` | `SkPath` | 要细分的路径 |
| `fColor` | `SkPMColor4f` | 预乘 Alpha 颜色 |
| `fNext` | `PathDrawList*` | 链表下一节点 |

提供范围迭代器:
```cpp
for (auto [pathMatrix, path, color] : pathDrawList) { ... }
```

### 关键成员变量(基类)

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAttribs` | `PatchAttribs` | 补丁属性(颜色/曲线类型等) |
| `fVertexChunkArray` | `GrVertexChunkArray` | 顶点数据块数组 |
| `fMaxVertexCount` | `int` | 最大顶点数(累积容差) |
| `fFixedVertexBuffer` | `sk_sp<const GrGpuBuffer>` | 固定顶点缓冲区 |
| `fFixedIndexBuffer` | `sk_sp<const GrGpuBuffer>` | 固定索引缓冲区 |

## 公共 API 函数

### 基类接口

```cpp
virtual void prepare(GrMeshDrawTarget* target,
                     const SkMatrix& shaderMatrix,
                     const PathDrawList& pathDrawList,
                     int totalCombinedPathVerbCnt) = 0;
```
准备 GPU 缓冲区,包含要细分的几何体。

```cpp
virtual void draw(GrOpFlushState* flushState) const = 0;
```
发出固定段数实例化绘制调用。调用者负责提前绑定管线。

### PathCurveTessellator

```cpp
void prepareWithTriangles(GrMeshDrawTarget* target,
                          const SkMatrix& shaderMatrix,
                          GrInnerFanTriangulator::BreadcrumbTriangleList* extraTriangles,
                          const PathDrawList& pathDrawList,
                          int totalCombinedPathVerbCnt);
```
准备曲线补丁,可选地包含额外三角形(面包屑三角形)用于内三角化连接。

```cpp
void drawHullInstances(GrOpFlushState*, sk_sp<const GrGpuBuffer> vertexBufferIfNeeded) const;
```
为每个补丁绘制 4 点实例(用于 `GrFillCubicHullShader` 绘制三次曲线凸包)。

### PathWedgeTessellator

```cpp
PathWedgeTessellator(bool infinitySupport, PatchAttribs attribs = PatchAttribs::kNone);
```
构造函数自动添加 `PatchAttribs::kFanPoint` 属性。

## 内部实现细节

### 曲线补丁写入(PathCurveTessellator)

```cpp
using CurveWriter = PatchWriter<
    VertexChunkPatchAllocator,
    Optional<PatchAttribs::kColor>,
    Optional<PatchAttribs::kWideColorIfEnabled>,
    Optional<PatchAttribs::kExplicitCurveType>,
    AddTrianglesWhenChopping,  // 切分时添加三角形
    DiscardFlatCurves>;        // 丢弃平坦曲线

void write_curve_patches(CurveWriter&& patchWriter,
                         const SkMatrix& shaderMatrix,
                         const PathDrawList& pathDrawList) {
    for (auto [pathMatrix, path, color] : pathDrawList) {
        AffineMatrix m(pathMatrix);
        for (auto [verb, pts, w] : SkPathPriv::Iterate(path)) {
            switch (verb) {
                case SkPathVerb::kQuad:
                    patchWriter.writeQuadratic(m.map2Points(pts), m.map1Point(pts+2));
                    break;
                case SkPathVerb::kConic:
                    patchWriter.writeConic(m.map2Points(pts), m.map1Point(pts+2), *w);
                    break;
                case SkPathVerb::kCubic:
                    patchWriter.writeCubic(m.map2Points(pts), m.map2Points(pts+2));
                    break;
            }
        }
    }
}
```

**特征:**
- 仅处理曲线(二次/圆锥/三次),忽略直线
- 二次曲线转换为三次曲线
- 三角形转换为权重为无穷的圆锥曲线
- 切分时自动添加连接三角形

### 楔形补丁写入(PathWedgeTessellator)

```cpp
using WedgeWriter = PatchWriter<
    VertexChunkPatchAllocator,
    Required<PatchAttribs::kFanPoint>,  // 必需扇形点
    Optional<PatchAttribs::kColor>,
    Optional<PatchAttribs::kWideColorIfEnabled>,
    Optional<PatchAttribs::kExplicitCurveType>>;

void write_wedge_patches(WedgeWriter&& patchWriter,
                         const SkMatrix& shaderMatrix,
                         const PathDrawList& pathDrawList) {
    for (auto [pathMatrix, path, color] : pathDrawList) {
        AffineMatrix m(pathMatrix);
        MidpointContourParser parser(path);
        while (parser.parseNextContour()) {
            patchWriter.updateFanPointAttrib(m.mapPoint(parser.currentMidpoint()));
            SkPoint lastPoint = {0, 0};
            SkPoint startPoint = {0, 0};
            for (auto [verb, pts, w] : parser.currentContour()) {
                switch (verb) {
                    case SkPathVerb::kLine:
                        // 直线显式转换为四点三次曲线,扇形更好且避免双击像素
                        patchWriter.writeLine(m.map2Points(pts));
                        lastPoint = pts[1];
                        break;
                    // ... 处理其他曲线类型
                }
            }
            // 闭合轮廓
            if (lastPoint != startPoint) {
                SkPoint pts[2] = {lastPoint, startPoint};
                patchWriter.writeLine(m.map2Points(pts));
            }
        }
    }
}
```

**特征:**
- 每个轮廓计算中点作为扇形点
- 直线显式转换为三次曲线避免退化
- 自动闭合轮廓

### 准备阶段(PathCurveTessellator)

```cpp
void PathCurveTessellator::prepareWithTriangles(...) {
    int patchPreallocCount = FixedCountCurves::PreallocCount(totalCombinedPathVerbCnt) +
                             (extraTriangles ? extraTriangles->count() : 0);

    LinearTolerances worstCase;
    CurveWriter writer{fAttribs, &worstCase, target, &fVertexChunkArray, patchPreallocCount};

    // 写入面包屑三角形
    if (extraTriangles) {
        for (const auto* tri = extraTriangles->head(); tri; tri = tri->fNext) {
            auto p0 = skvx::float2::Load(tri->fPts);
            auto p1 = skvx::float2::Load(tri->fPts + 1);
            auto p2 = skvx::float2::Load(tri->fPts + 2);
            if (any((p0 == p1) & (p1 == p2))) {
                continue;  // 剔除完全水平或垂直的退化三角形
            }
            writer.writeTriangle(p0, p1, p2);
        }
    }

    write_curve_patches(std::move(writer), shaderMatrix, pathDrawList);
    fMaxVertexCount = FixedCountCurves::VertexCount(worstCase);

    // 获取静态缓冲区
    fFixedVertexBuffer = rp->findOrMakeStaticBuffer(..., WriteVertexBuffer);
    fFixedIndexBuffer = rp->findOrMakeStaticBuffer(..., WriteIndexBuffer);
}
```

### 绘制阶段

```cpp
void PathCurveTessellator::draw(GrOpFlushState* flushState) const {
    if (!fFixedVertexBuffer || !fFixedIndexBuffer) {
        return;
    }
    for (const GrVertexChunk& chunk : fVertexChunkArray) {
        flushState->bindBuffers(fFixedIndexBuffer, chunk.fBuffer, fFixedVertexBuffer);
        // fMaxVertexCount 是逻辑顶点数,作为 "index count" 参数
        flushState->drawIndexedInstanced(fMaxVertexCount, 0, chunk.fCount, chunk.fBase, 0);
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrMeshDrawTarget` | 强依赖 | 提供资源分配和能力查询 |
| `GrOpFlushState` | 强依赖 | 执行绘制调用 |
| `PatchWriter` | 核心依赖 | 类型安全的补丁写入 |
| `VertexChunkPatchAllocator` | 强依赖 | 补丁内存分配 |
| `FixedCountBufferUtils` | 工具 | 固定段数缓冲区工具 |
| `WangsFormula` | 工具 | 计算细分段数 |
| `MidpointContourParser` | 工具 | 解析轮廓中点(楔形) |
| `GrInnerFanTriangulator` | 可选 | 内三角化器 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| 路径渲染操作 | 使用 PathTessellator 渲染填充路径 |
| GrPathOp | 调用 prepare 和 draw |

## 设计模式与设计决策

### 策略模式

两种细分策略:
- **Curve**: 外曲线补丁(需要单独绘制内扇形)
- **Wedge**: 楔形补丁(包含扇形,独立完整路径)

### 两阶段渲染

分离准备(CPU 密集)和绘制(GPU 调用),支持异步准备。

### 固定段数策略

使用 Wang's Formula 计算最坏情况,所有实例统一顶点数,简化实例化绘制。

### 静态缓冲区复用

顶点和索引缓冲区使用静态唯一键全局共享:
```cpp
SKGPU_DEFINE_STATIC_UNIQUE_KEY(gFixedCountCurveVertexBufferKey);
```

### 硬件适配

不支持无穷大时自动添加显式曲线类型:
```cpp
PathTessellator(bool infinitySupport, PatchAttribs attribs) {
    if (!infinitySupport) {
        fAttribs |= PatchAttribs::kExplicitCurveType;
    }
}
```

## 性能考量

### 预分配优化

```cpp
int patchPreallocCount = FixedCountCurves::PreallocCount(totalCombinedPathVerbCnt);
```
根据动词数预估补丁数,避免动态扩容。

### 仿射矩阵优化

```cpp
AffineMatrix m(pathMatrix);  // 仅提取仿射部分
auto [p0, p1] = m.map2Points(pts);  // 批量映射
```
针对仿射变换优化,比通用矩阵快。

### 退化三角形剔除

```cpp
if (any((p0 == p1) & (p1 == p2))) {
    continue;  // 剔除
}
```
使用 SIMD 快速检测退化几何。

### 实例化绘制

```cpp
flushState->drawIndexedInstanced(fMaxVertexCount, 0, chunk.fCount, chunk.fBase, 0);
```
一次绘制多个路径,减少绘制调用。

### 凸包绘制优化

```cpp
void drawHullInstances(...) const {
    flushState->drawInstanced(chunk.fCount, chunk.fBase, 4, 0);  // 仅 4 个顶点
}
```
用于保守光栅化,绘制凸包而非完整细分。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/tessellate/PatchWriter.h` | 核心 | 补丁写入器模板 |
| `src/gpu/ganesh/tessellate/VertexChunkPatchAllocator.h` | 依赖 | 补丁分配器 |
| `src/gpu/tessellate/FixedCountBufferUtils.h` | 工具 | 固定段数工具 |
| `src/gpu/tessellate/WangsFormula.h` | 工具 | Wang's Formula |
| `src/gpu/tessellate/MidpointContourParser.h` | 工具 | 轮廓中点解析 |
| `src/gpu/ganesh/geometry/GrInnerFanTriangulator.h` | 协作 | 内三角化器 |
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 协作 | 网格绘制目标 |
| `src/gpu/ganesh/GrOpFlushState.h` | 协作 | 操作刷新状态 |
