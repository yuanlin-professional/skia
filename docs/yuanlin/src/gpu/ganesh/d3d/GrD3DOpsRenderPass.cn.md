# GrD3DOpsRenderPass

> 源文件
> - src/gpu/ganesh/d3d/GrD3DOpsRenderPass.h
> - src/gpu/ganesh/d3d/GrD3DOpsRenderPass.cpp

## 概述

`GrD3DOpsRenderPass` 是 Skia 图形库中 Ganesh D3D 后端的渲染通道类,继承自 `GrOpsRenderPass`,负责记录和执行绘制操作。该类封装了 D3D12 的渲染命令记录,将 Skia 的高级绘制操作转换为 D3D12 命令列表调用。它管理渲染目标的设置、视口裁剪、管线状态绑定、顶点缓冲区绑定和绘制命令的发出。

该类是 Ganesh 渲染管线的核心组件,作为绘制操作与 D3D12 命令列表之间的桥梁。通过缓存渲染状态、批处理绘制调用和优化资源绑定,该类实现了高效的 GPU 渲染。

## 架构位置

```
Skia
└── src/gpu/ganesh
    ├── GrOpsRenderPass (抽象渲染通道基类)
    │   └── GrD3DOpsRenderPass (D3D12 实现) ← 核心类
    │       └── GrD3DDirectCommandList (命令列表)
    └── d3d
        ├── GrD3DGpu (持有渲染通道)
        ├── GrD3DPipelineState (管线状态)
        └── GrD3DRenderTarget (渲染目标)
```

## 主要类与结构体

### GrD3DOpsRenderPass

**继承关系**:
- 继承自: `GrOpsRenderPass`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrD3DGpu*` | GPU 设备指针 |
| `fCommandList` | `GrD3DDirectCommandList*` | 当前命令列表 |
| `fRenderTarget` | `GrD3DRenderTarget*` | 当前渲染目标 |
| `fOrigin` | `GrSurfaceOrigin` | 表面原点(左上/左下) |
| `fBounds` | `SkIRect` | 渲染边界 |
| `fColorLoadOp` | `LoadOp` | 颜色缓冲加载操作 |
| `fPipelineState` | `GrD3DPipelineState*` | 当前管线状态 |

## 公共 API 函数

### 渲染通道生命周期

```cpp
// 设置渲染通道参数
bool set(GrD3DRenderTarget* rt, GrSurfaceOrigin origin, const SkIRect& bounds,
         const LoadAndStoreInfo& colorInfo,
         const StencilLoadAndStoreInfo& stencilInfo,
         const TArray<GrSurfaceProxy*>& sampledProxies);

// 提交渲染通道
void submit();
```

### 绘制命令

```cpp
// 绘制实例化几何体
void onDraw(int vertexCount, int baseVertex);
void onDrawIndexed(int indexCount, int baseIndex, uint16_t minIndexValue,
                  uint16_t maxIndexValue, int baseVertex);
void onDrawInstanced(int instanceCount, int baseInstance,
                    int vertexCount, int baseVertex);
void onDrawIndexedInstanced(int indexCount, int baseIndex,
                           int instanceCount, int baseInstance,
                           int baseVertex);

// 间接绘制
void onDrawIndirect(const GrBuffer* drawIndirectBuffer, size_t offset,
                   int drawCount);
void onDrawIndexedIndirect(const GrBuffer* drawIndirectBuffer, size_t offset,
                          int drawCount);
```

### 清除操作

```cpp
// 清除渲染目标
void onClear(const GrScissorState& scissor, std::array<float, 4> color);

// 清除模板缓冲
void onClearStencilClip(const GrScissorState& scissor, bool insideStencilMask);
```

## 内部实现细节

### 渲染通道初始化

`set` 方法配置渲染通道:

```cpp
bool set(GrD3DRenderTarget* rt, GrSurfaceOrigin origin, const SkIRect& bounds,
         const LoadAndStoreInfo& colorInfo, ...) {
    fRenderTarget = rt;
    fOrigin = origin;
    fBounds = bounds;
    fColorLoadOp = colorInfo.fLoadOp;

    // 设置渲染目标
    fCommandList->setRenderTarget(rt);

    // 处理加载操作
    if (fColorLoadOp == LoadOp::kClear) {
        fCommandList->clearRenderTargetView(rt, colorInfo.fClearColor, nullptr);
    }

    return true;
}
```

### 绘制调用

`onDraw` 实现基本绘制:

```cpp
void onDraw(int vertexCount, int baseVertex) {
    SkASSERT(fPipelineState);
    fCommandList->drawInstanced(vertexCount, 1, baseVertex, 0);
}
```

### 管线状态绑定

绑定操作通过 `onBindPipeline` 执行:

```cpp
void onBindPipeline(const GrProgramInfo& programInfo, const SkRect& drawBounds) {
    fPipelineState = fGpu->resourceProvider().findOrCreateCompatiblePipelineState(
        fRenderTarget, programInfo);
    fPipelineState->setData(fRenderTarget, programInfo);
    fCommandList->setPipelineState(fPipelineState->pipeline());
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrOpsRenderPass` | 抽象基类 |
| `GrD3DGpu` | GPU 设备 |
| `GrD3DCommandList` | 命令记录 |
| `GrD3DPipelineState` | 管线状态 |
| `GrD3DRenderTarget` | 渲染目标 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DGpu` | 创建和管理渲染通道 |
| `GrOpsTask` | 提交绘制操作 |

## 设计模式与设计决策

### 命令记录模式

延迟执行绘制命令:
- 批处理优化
- 状态排序
- 减少驱动开销

### 状态缓存

缓存当前管线状态:
- 避免冗余绑定
- 减少 API 调用
- 优化 CPU 开销

## 性能考量

### 批处理绘制

合并多个绘制调用:
- 减少驱动调用次数
- 提高 GPU 利用率
- 降低 CPU 开销

### 状态最小化

只设置改变的状态:
- 减少状态切换
- 优化驱动处理
- 提高帧率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrOpsRenderPass.h` | 基类 | 抽象渲染通道 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | GPU 设备 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 依赖 | 命令记录 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 依赖 | 管线状态 |
