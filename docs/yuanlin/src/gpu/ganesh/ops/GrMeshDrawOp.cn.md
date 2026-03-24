# GrMeshDrawOp

> 源文件
> - src/gpu/ganesh/ops/GrMeshDrawOp.h
> - src/gpu/ganesh/ops/GrMeshDrawOp.cpp

## 概述

`GrMeshDrawOp` 是 Ganesh GPU 后端中所有基于网格绘制操作的抽象基类。它继承自 `GrDrawOp`，专门处理需要顶点和索引缓冲区的几何绘制。该类提供了程序信息创建、网格准备和绘制提交的标准化框架，并包含两个实用辅助类 `PatternHelper` 和 `QuadHelper`，用于简化重复模式绘制和四边形批处理。

`GrMeshDrawOp` 定义了网格绘制的生命周期钩子，包括预准备（pre-prepare）、准备（prepare）和执行（execute）阶段，为子类提供了清晰的扩展点。

## 架构位置

`GrMeshDrawOp` 位于 Ganesh 绘制操作层次结构的中间层：

- **上层**：由 `GrOpsTask` 管理和调度
- **同层**：继承自 `GrDrawOp`，与其他绘制操作类型并列
- **下层**：被具体的几何操作继承，如 `FillRectOp`、`FillRRectOp`、`GrOvalOpFactory` 等

在渲染管线中，该类是高层形状描述和底层 GPU 网格渲染之间的关键抽象层。

## 主要类与结构体

### 类层次结构

```
GrOp
    └── GrDrawOp
        └── GrMeshDrawOp (抽象基类)
            ├── FillRectOp
            ├── FillRRectOp
            ├── CircularRRectOp
            └── 其他网格绘制操作
```

### GrMeshDrawOp 关键成员

`GrMeshDrawOp` 是纯抽象类，不包含成员变量，只定义接口：

**纯虚函数**：
- `programInfo()` - 返回程序信息指针
- `onCreateProgramInfo()` - 创建程序信息
- `onPrepareDraws()` - 准备绘制数据

### PatternHelper 辅助类

用于渲染使用模式化索引缓冲区的重复网格。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertices` | `void*` | 顶点数据指针 |
| `fMesh` | `GrSimpleMesh*` | 网格描述符 |
| `fPrimitiveType` | `GrPrimitiveType` | 图元类型（三角形、线段等） |

**构造参数**：
- `verticesPerRepetition`：每次重复的顶点数
- `indicesPerRepetition`：每次重复的索引数
- `repeatCount`：重复次数
- `maxRepetitions`：索引缓冲区支持的最大重复次数

### QuadHelper 辅助类

`PatternHelper` 的特化版本，专门用于非抗锯齿索引四边形渲染。

**简化参数**：
- `vertexStride`：顶点步长
- `quadsToDraw`：要绘制的四边形数量

自动使用标准的非 AA 四边形索引缓冲区。

## 公共 API 函数

### 静态工具方法

```cpp
static bool CanUpgradeAAOnMerge(GrAAType aa1, GrAAType aa2)
```
检查两个操作的抗锯齿类型是否可以在合并时升级。如果一个是 `kNone` 另一个是 `kCoverage`，则可以升级。

```cpp
static bool CombinedQuadCountWillOverflow(GrAAType aaType,
                                          bool willBeUpgradedToAA,
                                          int combinedQuadCount)
```
检查合并后的四边形数量是否会溢出索引缓冲区容量。AA 和非 AA 四边形有不同的最大数量限制。

### 程序信息创建

```cpp
void createProgramInfo(const GrCaps* caps,
                       SkArenaAlloc* arena,
                       const GrSurfaceProxyView& writeView,
                       bool usesMSAASurface,
                       GrAppliedClip&& appliedClip,
                       const GrDstProxyView& dstProxyView,
                       GrXferBarrierFlags renderPassXferBarriers,
                       GrLoadOp colorLoadOp)
```
创建程序信息对象，封装着色器、混合状态、裁剪等所有渲染状态。

```cpp
void createProgramInfo(GrMeshDrawTarget* target)
```
从 `GrMeshDrawTarget` 中提取参数创建程序信息的便捷版本。

### PatternHelper 方法

```cpp
PatternHelper(GrMeshDrawTarget* target,
              GrPrimitiveType primitiveType,
              size_t vertexStride,
              sk_sp<const GrBuffer> indexBuffer,
              int verticesPerRepetition,
              int indicesPerRepetition,
              int repeatCount,
              int maxRepetitions)
```
构造函数，分配顶点空间并设置模式化网格。

```cpp
void recordDraw(GrMeshDrawTarget* target, const GrGeometryProcessor* gp) const
```
记录绘制命令。

```cpp
void* vertices() const
```
返回顶点数据指针，用于填充顶点。

### QuadHelper 方法

```cpp
QuadHelper(GrMeshDrawTarget* target, size_t vertexStride, int quadsToDraw)
```
构造函数，自动设置四边形绘制所需的资源。

继承 `PatternHelper` 的 `vertices()`, `mesh()`, `recordDraw()` 方法。

## 内部实现细节

### 生命周期钩子

`GrMeshDrawOp` 实现了 `GrOp` 的虚函数，并提供新的扩展点：

```cpp
// GrOp 接口实现
void onPrePrepare(...) final {
    this->onPrePrepareDraws(...);  // 调用子类实现
}

void onPrepare(GrOpFlushState* state) final {
    this->onPrepareDraws(state);  // 调用子类实现
}

// 子类扩展点
virtual void onPrePrepareDraws(...);
virtual void onPrepareDraws(GrMeshDrawTarget*) = 0;
virtual void onCreateProgramInfo(...) = 0;
```

### 预准备实现

`onPrePrepareDraws` 的默认实现支持延迟显示列表（DDL）：

```cpp
void GrMeshDrawOp::onPrePrepareDraws(GrRecordingContext* context,
                                     const GrSurfaceProxyView& writeView,
                                     GrAppliedClip* clip,
                                     const GrDstProxyView& dstProxyView,
                                     GrXferBarrierFlags renderPassXferBarriers,
                                     GrLoadOp colorLoadOp) {
    SkArenaAlloc* arena = context->priv().recordTimeAllocator();
    bool usesMSAASurface = writeView.asRenderTargetProxy()->numSamples() > 1;
    GrAppliedClip appliedClip = clip ? std::move(*clip) : GrAppliedClip::Disabled();

    this->createProgramInfo(context->priv().caps(), arena, writeView, usesMSAASurface,
                            std::move(appliedClip), dstProxyView, renderPassXferBarriers,
                            colorLoadOp);

    context->priv().recordProgramInfo(this->programInfo());
}
```

关键步骤：
1. 从录制上下文获取内存分配器（记录时 arena）
2. 检测 MSAA 状态（注意：DDL 不支持 DMSAA）
3. 创建程序信息
4. 记录程序信息用于后续重用

### 四边形容量检查

`CombinedQuadCountWillOverflow` 检查是否超过索引缓冲区容量：

```cpp
bool GrMeshDrawOp::CombinedQuadCountWillOverflow(GrAAType aaType,
                                                 bool willBeUpgradedToAA,
                                                 int combinedQuadCount) {
    bool willBeAA = (aaType == GrAAType::kCoverage) || willBeUpgradedToAA;
    return combinedQuadCount > (willBeAA ? GrResourceProvider::MaxNumAAQuads()
                                         : GrResourceProvider::MaxNumNonAAQuads());
}
```

AA 和非 AA 四边形有不同的限制，因为它们使用不同的索引模式。

### PatternHelper 初始化

`PatternHelper::init` 执行以下步骤：

1. **溢出检查**：
```cpp
if (repeatCount < 0 || repeatCount > SK_MaxS32 / verticesPerRepetition) {
    return;
}
```

2. **分配顶点缓冲区**：
```cpp
int vertexCount = verticesPerRepetition * repeatCount;
fVertices = target->makeVertexSpace(vertexStride, vertexCount, &vertexBuffer, &firstVertex);
```

3. **设置模式化网格**：
```cpp
fMesh->setIndexedPatterned(std::move(indexBuffer), indicesPerRepetition, repeatCount,
                           maxRepetitions, std::move(vertexBuffer), verticesPerRepetition,
                           firstVertex);
```

模式化网格允许单个索引缓冲区支持多个重复实例，减少索引数据重复。

### QuadHelper 实现

`QuadHelper` 简化四边形绘制：

```cpp
GrMeshDrawOp::QuadHelper::QuadHelper(GrMeshDrawTarget* target,
                                     size_t vertexStride,
                                     int quadsToDraw) {
    sk_sp<const GrGpuBuffer> indexBuffer = target->resourceProvider()->refNonAAQuadIndexBuffer();
    if (!indexBuffer) {
        SkDebugf("Could not get quad index buffer.");
        return;
    }
    this->init(target, GrPrimitiveType::kTriangles, vertexStride, std::move(indexBuffer),
               GrResourceProvider::NumVertsPerNonAAQuad(),      // 4
               GrResourceProvider::NumIndicesPerNonAAQuad(),    // 6
               quadsToDraw,
               GrResourceProvider::MaxNumNonAAQuads());
}
```

每个四边形：
- 4 个顶点
- 6 个索引（两个三角形）
- 使用全局共享的非 AA 四边形索引缓冲区

### 记录绘制

`PatternHelper::recordDraw` 向目标记录绘制命令：

```cpp
void GrMeshDrawOp::PatternHelper::recordDraw(GrMeshDrawTarget* target,
                                             const GrGeometryProcessor* gp) const {
    target->recordDraw(gp, fMesh, 1, fPrimitiveType);
}
```

参数说明：
- `gp`：几何处理器（定义顶点属性和着色器）
- `fMesh`：网格描述符（1 个网格）
- `fPrimitiveType`：图元类型

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrDrawOp` | 基类 |
| `GrMeshDrawTarget` | 网格绘制目标，提供资源分配和绘制记录 |
| `GrOpFlushState` | 操作刷新状态 |
| `GrGeometryProcessor` | 几何处理器，定义顶点处理 |
| `GrProgramInfo` | 程序信息，封装渲染状态 |
| `GrSimpleMesh` | 网格描述符 |
| `GrBuffer` | GPU 缓冲区 |
| `GrResourceProvider` | 资源提供者，分配索引缓冲区 |
| `SkArenaAlloc` | 内存分配器 |
| `GrAppliedClip` | 应用的裁剪 |

### 被依赖的模块

`GrMeshDrawOp` 是众多具体网格绘制操作的基类：

| 操作类 | 用途 |
|--------|------|
| `FillRectOp` | 矩形填充 |
| `FillRRectOp` | 圆角矩形填充 |
| `CircularRRectOp` | 圆形圆角矩形 |
| `StrokeRectOp` | 矩形描边 |
| `TextureOp` | 纹理绘制 |
| `AAConvexPathRenderer` | 凸多边形路径 |
| 等等 | 所有基于网格的几何操作 |

## 设计模式与设计决策

### 模板方法模式

`GrMeshDrawOp` 使用模板方法模式定义操作生命周期：
- 公共方法 `onPrePrepare`, `onPrepare` 定义算法骨架
- 纯虚函数 `onPrepareDraws`, `onCreateProgramInfo` 由子类实现
- 子类只需关注具体的网格生成逻辑

### 辅助类模式

`PatternHelper` 和 `QuadHelper` 采用辅助类模式：
- 封装常见绘制模式的复杂性
- 提供简化的接口
- 减少子类重复代码

### 两阶段准备

操作支持两阶段准备：

**阶段 1：预准备（Pre-Prepare）**
- 在录制时执行（DDL）
- 创建程序信息
- 不访问 GPU 资源

**阶段 2：准备（Prepare）**
- 在刷新时执行
- 分配和填充缓冲区
- 生成实际几何数据

这种设计支持延迟显示列表（DDL），允许在不同线程/上下文中录制和执行。

### 程序信息抽象

`GrProgramInfo` 封装所有渲染状态：
- 几何处理器
- 管线状态（混合、深度、模板等）
- 裁剪
- 原语类型

优势：
- 状态可以预创建和重用
- 支持程序缓存
- 简化状态管理

### 模式化索引

`PatternHelper` 支持模式化索引缓冲区：
- 索引缓冲区包含多个重复的模式
- 通过 `repeatCount` 和 `maxRepetitions` 参数控制
- 减少索引数据重复和内存占用

例如，四边形索引模式 `[0,1,2,2,1,3]` 可以重复使用，只需偏移顶点起始位置。

### AA 升级策略

`CanUpgradeAAOnMerge` 允许在合并时升级抗锯齿类型：
- 混合 AA 和非 AA 操作时，统一升级为 AA
- 简化合并逻辑
- 避免复杂的混合渲染

### 容量溢出保护

显式检查索引缓冲区容量：
- `CombinedQuadCountWillOverflow` 防止索引溢出
- `PatternHelper::init` 检查顶点数量溢出
- 失败时优雅降级（返回空或跳过绘制）

## 性能考量

### 共享索引缓冲区

四边形和其他常见模式使用全局共享索引缓冲区：
- 减少缓冲区分配和上传
- 降低 GPU 内存占用
- 提高缓存命中率

### 批处理优化

`PatternHelper` 支持批量重复绘制：
- 单次绘制调用处理多个重复单元
- 减少 CPU 和驱动开销
- 提高 GPU 利用率

典型场景：绘制多个相似的四边形或重复图案。

### 延迟资源分配

顶点和索引缓冲区在 `onPrepareDraws` 阶段分配：
- 仅在实际需要时分配
- 操作可能在准备前被剔除或优化掉
- 减少不必要的资源创建

### 程序信息缓存

预准备阶段创建的 `GrProgramInfo` 可以被缓存和重用：
- 避免重复编译着色器
- 减少状态切换
- 提高 DDL 场景性能

### 内存分配策略

使用 `SkArenaAlloc` 进行快速分配：
- 线性分配，无碎片
- 批量释放，低开销
- 适合短生命周期对象（如程序信息）

### 溢出检查开销

早期溢出检查避免后续崩溃：
```cpp
if (repeatCount < 0 || repeatCount > SK_MaxS32 / verticesPerRepetition) {
    return;  // 早期退出，避免后续计算
}
```

虽然增加了检查开销，但保证了稳定性。

### 四边形特化

`QuadHelper` 专门为四边形优化：
- 硬编码顶点/索引数量（4/6）
- 使用预构建的索引缓冲区
- 简化接口减少函数调用

四边形是 2D 图形中最常见的图元，值得特殊优化。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrDrawOp.h` | 继承 | 绘制操作基类 |
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 使用 | 网格绘制目标接口 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | 操作刷新状态 |
| `src/gpu/ganesh/GrSimpleMesh.h` | 使用 | 网格描述符 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 使用 | 几何处理器 |
| `src/gpu/ganesh/GrProgramInfo.h` | 使用 | 程序信息 |
| `src/gpu/ganesh/GrResourceProvider.h` | 使用 | 资源提供者 |
| `src/gpu/ganesh/ops/FillRectOp.h` | 被继承 | 矩形填充操作 |
| `src/gpu/ganesh/ops/FillRRectOp.h` | 被继承 | 圆角矩形填充操作 |
| `src/gpu/ganesh/ops/TextureOp.h` | 被继承 | 纹理绘制操作 |
