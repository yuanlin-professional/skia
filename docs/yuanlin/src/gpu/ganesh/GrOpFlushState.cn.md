# GrOpFlushState

> 源文件
> - src/gpu/ganesh/GrOpFlushState.h
> - src/gpu/ganesh/GrOpFlushState.cpp

## 概述

`GrOpFlushState` 是 Ganesh GPU 后端中用于跟踪和管理 OpsTask 刷新过程中所有 `GrOp`（主要是 `GrDrawOp`）状态的核心类。它同时实现了 `GrDeferredUploadTarget` 和 `GrMeshDrawTarget` 两个接口，负责管理顶点/索引缓冲区分配、网格绘制记录、延迟纹理上传以及绘制执行。该类在刷新管线中扮演中央协调者的角色，连接 Op 准备阶段和 GPU 执行阶段。

## 架构位置

`GrOpFlushState` 位于 Ganesh 渲染管线的刷新执行层，处于 OpsTask 和底层 GPU 之间：

```
GrDrawingManager
    └── GrOpsTask
        └── GrOpFlushState (刷新状态管理)
            ├── GrOpsRenderPass (渲染通道)
            ├── GrVertexBufferAllocPool (顶点缓冲池)
            ├── GrIndexBufferAllocPool (索引缓冲池)
            ├── GrDrawIndirectBufferAllocPool (间接绘制缓冲池)
            └── GrGpu (底层 GPU 接口)
```

它作为 Op 执行期间的状态容器和资源提供者，管理从 Op 准备到 GPU 绘制的整个数据流。

## 主要类与结构体

### GrOpFlushState

主要的刷新状态管理类。

**继承关系**
- 基类：`GrDeferredUploadTarget`, `GrMeshDrawTarget`
- 子类：无（final 类）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fArena` | `SkArenaAllocWithReset` | 用于存储管线、绘制和上传的内存池 |
| `fVertexPool` | `GrVertexBufferAllocPool` | 顶点缓冲区分配池 |
| `fIndexPool` | `GrIndexBufferAllocPool` | 索引缓冲区分配池 |
| `fDrawIndirectPool` | `GrDrawIndirectBufferAllocPool` | 间接绘制缓冲区分配池 |
| `fASAPUploads` | `SkArenaAllocList<GrDeferredTextureUploadFn>` | 尽快执行的纹理上传列表 |
| `fInlineUploads` | `SkArenaAllocList<InlineUpload>` | 内联纹理上传列表 |
| `fDraws` | `SkArenaAllocList<Draw>` | 绘制命令列表 |
| `fBaseDrawToken` | `skgpu::Token` | 首个绘制的令牌 |
| `fOpArgs` | `OpArgs*` | 当前正在准备或执行的 Op 参数 |
| `fSampledProxies` | `skia_private::TArray<GrSurfaceProxy*, true>*` | 采样的代理数组 |
| `fGpu` | `GrGpu*` | GPU 接口 |
| `fResourceProvider` | `GrResourceProvider*` | 资源提供者 |
| `fTokenTracker` | `skgpu::TokenTracker*` | 令牌跟踪器 |
| `fOpsRenderPass` | `GrOpsRenderPass*` | 当前渲染通道 |
| `fCurrDraw` | `SkArenaAllocList<Draw>::Iter` | 当前绘制迭代器 |
| `fCurrUpload` | `SkArenaAllocList<InlineUpload>::Iter` | 当前上传迭代器 |

### OpArgs

封装每个 Op 执行所需的额外数据。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fOp` | `GrOp*` | 当前操作的指针 |
| `fSurfaceView` | `const GrSurfaceProxyView&` | 表面视图 |
| `fRenderTargetProxy` | `GrRenderTargetProxy*` | 渲染目标代理 |
| `fUsesMSAASurface` | `bool` | 是否使用 MSAA 表面 |
| `fAppliedClip` | `GrAppliedClip*` | 应用的裁剪 |
| `fDstProxyView` | `GrDstProxyView` | 目标代理视图 |
| `fRenderPassXferBarriers` | `GrXferBarrierFlags` | 渲染通道屏障标志 |
| `fColorLoadOp` | `GrLoadOp` | 颜色加载操作 |

### Draw

存储共享几何处理器和管线的连续绘制。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fGeometryProcessor` | `const GrGeometryProcessor*` | 几何处理器 |
| `fGeomProcProxies` | `const GrSurfaceProxy* const*` | 几何处理器纹理代理 |
| `fMeshes` | `const GrSimpleMesh*` | 网格数组 |
| `fOp` | `const GrOp*` | 所属的 Op |
| `fMeshCnt` | `int` | 网格数量 |
| `fPrimitiveType` | `GrPrimitiveType` | 图元类型 |

### InlineUpload

内联纹理上传结构。

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fUpload` | `GrDeferredTextureUploadFn` | 上传函数 |
| `fUploadBeforeToken` | `skgpu::Token` | 上传前的令牌 |

## 公共 API 函数

### 构造和生命周期

| 函数签名 | 说明 |
|----------|------|
| `GrOpFlushState(GrGpu*, GrResourceProvider*, skgpu::TokenTracker*, sk_sp<GrBufferAllocPool::CpuBufferCache>)` | 构造函数，初始化刷新状态 |
| `~GrOpFlushState()` | 析构函数，调用 reset() 清理资源 |
| `void reset()` | 重置所有状态和缓冲池 |

### 执行控制

| 函数签名 | 说明 |
|----------|------|
| `void preExecuteDraws()` | 在执行绘制前调用，解除缓冲区映射并执行 ASAP 上传 |
| `void executeDrawsAndUploadsForMeshDrawOp(const GrOp*, const SkRect&, const GrPipeline*, const GrUserStencilSettings*)` | 为网格绘制 Op 执行绘制和上传 |

### 延迟上传（GrDeferredUploadTarget 接口）

| 函数签名 | 说明 |
|----------|------|
| `skgpu::Token addInlineUpload(GrDeferredTextureUploadFn&&)` | 添加内联上传，返回上传令牌 |
| `skgpu::Token addASAPUpload(GrDeferredTextureUploadFn&&)` | 添加尽快执行的上传 |
| `void doUpload(GrDeferredTextureUploadFn&, bool)` | 执行延迟的纹理上传 |
| `const skgpu::TokenTracker* tokenTracker()` | 获取令牌跟踪器 |

### 网格绘制（GrMeshDrawTarget 接口）

| 函数签名 | 说明 |
|----------|------|
| `void recordDraw(const GrGeometryProcessor*, const GrSimpleMesh[], int, const GrSurfaceProxy* const[], GrPrimitiveType)` | 记录网格绘制 |
| `void* makeVertexSpace(size_t, int, sk_sp<const GrBuffer>*, int*)` | 分配顶点空间 |
| `uint16_t* makeIndexSpace(int, sk_sp<const GrBuffer>*, int*)` | 分配索引空间 |
| `void* makeVertexSpaceAtLeast(size_t, int, int, sk_sp<const GrBuffer>*, int*, int*)` | 分配至少指定大小的顶点空间 |
| `uint16_t* makeIndexSpaceAtLeast(int, int, sk_sp<const GrBuffer>*, int*, int*)` | 分配至少指定大小的索引空间 |
| `void putBackIndices(int)` | 归还未使用的索引 |
| `void putBackVertices(int, size_t)` | 归还未使用的顶点 |

### 间接绘制

| 函数签名 | 说明 |
|----------|------|
| `GrDrawIndirectWriter makeDrawIndirectSpace(int, sk_sp<const GrBuffer>*, size_t*)` | 分配间接绘制空间 |
| `GrDrawIndexedIndirectWriter makeDrawIndexedIndirectSpace(int, sk_sp<const GrBuffer>*, size_t*)` | 分配索引间接绘制空间 |
| `void putBackIndirectDraws(int)` | 归还间接绘制 |
| `void putBackIndexedIndirectDraws(int)` | 归还索引间接绘制 |

### 渲染通道操作

| 函数签名 | 说明 |
|----------|------|
| `void bindPipeline(const GrProgramInfo&, const SkRect&)` | 绑定管线 |
| `void setScissorRect(const SkIRect&)` | 设置裁剪矩形 |
| `void bindTextures(const GrGeometryProcessor&, const GrSurfaceProxy* const[], const GrPipeline&)` | 绑定纹理 |
| `void bindBuffers(sk_sp<const GrBuffer>, sk_sp<const GrBuffer>, sk_sp<const GrBuffer>, GrPrimitiveRestart)` | 绑定缓冲区 |
| `void draw(int, int)` | 执行绘制 |
| `void drawIndexed(int, int, uint16_t, uint16_t, int)` | 执行索引绘制 |
| `void drawInstanced(int, int, int, int)` | 执行实例化绘制 |
| `void drawIndexedInstanced(int, int, int, int, int)` | 执行索引实例化绘制 |
| `void drawIndirect(const GrBuffer*, size_t, int)` | 执行间接绘制 |
| `void drawIndexedIndirect(const GrBuffer*, size_t, int)` | 执行索引间接绘制 |
| `void drawIndexPattern(int, int, int, int, int)` | 执行索引模式绘制 |

### 便利方法

| 函数签名 | 说明 |
|----------|------|
| `void bindPipelineAndScissorClip(const GrProgramInfo&, const SkRect&)` | 绑定管线并设置裁剪 |
| `void drawMesh(const GrSimpleMesh&)` | 绘制单个网格 |

### 状态访问

| 函数签名 | 说明 |
|----------|------|
| `GrOpsRenderPass* opsRenderPass()` | 获取渲染通道 |
| `void setOpsRenderPass(GrOpsRenderPass*)` | 设置渲染通道 |
| `GrGpu* gpu()` | 获取 GPU 接口 |
| `const OpArgs& drawOpArgs() const` | 获取当前 Op 参数 |
| `void setOpArgs(OpArgs*)` | 设置当前 Op 参数 |

## 内部实现细节

### 三阶段执行模型

`GrOpFlushState` 实现了三阶段的执行模型：

1. **准备阶段（Prepare）**：Op 调用 `recordDraw`、`makeVertexSpace` 等方法准备数据
2. **预执行阶段（PreExecute）**：调用 `preExecuteDraws()` 解除缓冲区映射，执行 ASAP 上传
3. **执行阶段（Execute）**：调用 `executeDrawsAndUploadsForMeshDrawOp()` 执行绘制

### 缓冲池管理

该类管理三个专用缓冲池：

```cpp
GrVertexBufferAllocPool fVertexPool;
GrIndexBufferAllocPool fIndexPool;
GrDrawIndirectBufferAllocPool fDrawIndirectPool;
```

所有池共享同一个 CPU 缓冲缓存，优化内存使用。初始大小为 `GrBufferAllocPool::kDefaultBufferSize`，需要更大缓冲时才分配 CPU 内存。

### 延迟上传机制

支持两种纹理上传方式：

1. **ASAP 上传**：在 `preExecuteDraws()` 中立即执行
2. **内联上传**：在特定绘制令牌之前执行，插入到绘制流中

```cpp
void GrOpFlushState::executeDrawsAndUploadsForMeshDrawOp(...) {
    while (fCurrDraw != fDraws.end() && fCurrDraw->fOp == op) {
        skgpu::Token drawToken = fTokenTracker->nextFlushToken();
        // 执行该令牌之前的所有内联上传
        while (fCurrUpload != fInlineUploads.end() &&
               fCurrUpload->fUploadBeforeToken == drawToken) {
            this->opsRenderPass()->inlineUpload(this, fCurrUpload->fUpload);
            ++fCurrUpload;
        }
        // 执行绘制
        ...
    }
}
```

### 绘制合并

`Draw` 结构体将共享相同几何处理器和管线的多个网格合并在一起，允许 GPU 一次性设置共享状态后执行多个绘制，减少状态切换开销。

### 像素上传转换

`doUpload` 方法智能处理像素格式转换：

```cpp
GrCaps::SupportedWrite supportedWrite =
    fGpu->caps()->supportedWritePixelsColorType(colorType, dstSurface->backendFormat(), colorType);

if (supportedWrite.fColorType != colorType ||
    (!fGpu->caps()->writePixelsRowBytesSupport() && rowBytes != tightRB)) {
    // 需要转换，分配临时缓冲区
    tmpPixels.reset(new char[rect.height()*tightRB]);
    GrConvertPixels(...);
}
```

### Arena 分配器

使用 `SkArenaAllocWithReset` 管理 Op 执行期间的所有临时分配：

```cpp
SkArenaAllocWithReset fArena{sizeof(GrPipeline) * 100};
```

初始大小为 100 个管线对象，避免小分配的开销。所有 `Draw`、`InlineUpload` 等结构都从 arena 分配。

### 令牌跟踪

使用令牌（Token）系统跟踪绘制顺序和资源生命周期：

- `fBaseDrawToken`：首个绘制的令牌
- 每次 `recordDraw` 发出一个绘制令牌
- 内联上传关联到特定令牌，确保在正确时机执行

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `GrGpu` | 底层 GPU 操作接口 |
| `GrResourceProvider` | 资源创建和管理 |
| `GrBufferAllocPool` | 缓冲区池管理 |
| `GrOpsRenderPass` | 渲染通道执行 |
| `skgpu::TokenTracker` | 令牌跟踪和同步 |
| `GrGeometryProcessor` | 几何处理器 |
| `GrPipeline` | 渲染管线状态 |
| `GrSimpleMesh` | 网格数据结构 |
| `SkArenaAlloc` | 内存分配器 |
| `GrAtlasManager` | 图集管理 |
| `sktext::gpu::StrikeCache` | 字形缓存 |
| `skgpu::ganesh::SmallPathAtlasMgr` | 小路径图集管理 |
| `GrThreadSafeCache` | 线程安全缓存 |
| `GrCaps` | GPU 能力查询 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| `GrOp` 及其子类 | 使用 flush state 准备和执行绘制 |
| `GrOpsTask` | 创建和管理 flush state 生命周期 |
| `GrDrawOp` | 主要的绘制操作使用者 |
| 各种图集 | 通过延迟上传机制上传纹理数据 |

## 设计模式与设计决策

### 状态对象模式（State Object Pattern）

`GrOpFlushState` 封装了刷新过程中的所有状态，作为参数在各个组件间传递，避免全局状态。

### 资源池模式（Object Pool Pattern）

使用三个缓冲池预分配和重用缓冲区，避免频繁的分配/释放操作。池在 `reset()` 时回收所有资源。

### 迭代器模式（Iterator Pattern）

使用迭代器遍历绘制和上传列表：

```cpp
SkArenaAllocList<Draw>::Iter fCurrDraw;
SkArenaAllocList<InlineUpload>::Iter fCurrUpload;
```

这允许在执行期间线性遍历，同时支持在遍历过程中检查条件。

### 双接口继承

同时继承 `GrDeferredUploadTarget` 和 `GrMeshDrawTarget`，提供两组独立但互补的功能：

- `GrDeferredUploadTarget`：延迟纹理上传
- `GrMeshDrawTarget`：网格绘制和缓冲管理

这种设计允许不同组件通过适当的接口访问 flush state。

### Final 类设计

声明为 `final` 类，防止继承，确保：

- 性能优化（编译器可内联虚函数调用）
- 设计意图明确（这是具体实现，不是扩展点）
- 简化内存布局

### 命令记录与执行分离

准备阶段只记录命令（`recordDraw`），执行阶段才真正发送到 GPU（`executeDrawsAndUploadsForMeshDrawOp`）。这种分离允许：

- 批处理和优化机会
- 延迟决策（如资源分配）
- 更好的错误处理

## 性能考量

### 内存分配优化

- **Arena 分配器**：所有临时对象从单个 arena 分配，避免碎片化
- **预分配池**：缓冲池预分配大块内存，减少系统调用
- **共享 CPU 缓存**：三个池共享 CPU 缓冲缓存，节省内存

### 批处理优化

- **绘制合并**：共享几何处理器的绘制合并到单个 Draw 对象
- **状态排序**：按状态分组减少状态切换
- **令牌系统**：精确控制资源生命周期，减少同步开销

### 缓存友好性

- **线性遍历**：使用迭代器线性遍历绘制列表，提高缓存命中率
- **连续存储**：`SkArenaAllocList` 在 arena 中连续分配节点

### 减少虚函数调用

虽然继承两个接口，但通过内联和 final 关键字，编译器可以去虚化（devirtualize）大部分调用。

### 延迟上传优化

- **ASAP 上传**：预先上传纹理，避免在绘制期间等待
- **内联上传**：只在需要时才上传，避免不必要的传输
- **批量上传**：多个上传可以合并执行

### 引用计数管理

`Draw` 析构函数正确管理几何处理器代理的引用计数：

```cpp
GrOpFlushState::Draw::~Draw() {
    for (int i = 0; i < fGeometryProcessor->numTextureSamplers(); ++i) {
        SkASSERT(fGeomProcProxies && fGeomProcProxies[i]);
        fGeomProcProxies[i]->unref();
    }
}
```

确保代理在 Draw 对象销毁时正确释放。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 基类接口 | 网格绘制目标接口 |
| `src/gpu/ganesh/GrDeferredUpload.h` | 基类接口 | 延迟上传目标接口 |
| `src/gpu/ganesh/GrOpsTask.h/cpp` | 使用者 | 创建和使用 flush state |
| `src/gpu/ganesh/GrOp.h` | 协作 | Op 使用 flush state 执行 |
| `src/gpu/ganesh/GrBufferAllocPool.h/cpp` | 依赖 | 缓冲区池实现 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 依赖 | 渲染通道接口 |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 资源提供者 |
| `src/gpu/ganesh/GrSimpleMesh.h` | 数据结构 | 网格数据 |
| `src/gpu/ganesh/GrProgramInfo.h` | 配置 | 程序信息 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 着色器 | 几何处理器 |
| `src/gpu/ganesh/GrPipeline.h` | 状态 | 渲染管线 |
| `src/base/SkArenaAlloc.h` | 工具 | Arena 分配器 |
