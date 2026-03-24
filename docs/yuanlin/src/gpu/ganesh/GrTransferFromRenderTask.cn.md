# GrTransferFromRenderTask

> 源文件: src/gpu/ganesh/GrTransferFromRenderTask.h, src/gpu/ganesh/GrTransferFromRenderTask.cpp

## 概述

`GrTransferFromRenderTask` 是 Skia Ganesh GPU 后端中的渲染任务,专门负责将 GPU 纹理表面的数据传输到 CPU 可访问的缓冲区。这是实现 GPU-to-CPU 数据回读、截图、纹理下载等功能的核心机制。

该类继承自 `GrRenderTask`,集成到 Ganesh 的延迟渲染管线中,支持异步数据传输和颜色格式转换。与 `GrWritePixelsRenderTask` 相反,它处理从 GPU 到 CPU 的数据流动。

## 架构位置

`GrTransferFromRenderTask` 在 Ganesh 渲染系统中的位置:

- **上层**: 通常由 `GrSurfaceContext` 或读取像素操作创建
- **同层**: 与其他 `GrRenderTask` 子类并列
- **下层**: 依赖 `GrGpu` 执行底层传输操作

该任务作为 GPU 数据导出管线的一部分,连接 GPU 资源和 CPU 内存。

## 主要类与结构体

### GrTransferFromRenderTask 类

**继承关系**:
- 继承自 `GrRenderTask`
- 标记为 `final`,禁止进一步派生

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSrcProxy` | `sk_sp<GrSurfaceProxy>` | 源表面代理(读取数据的 GPU 纹理) |
| `fSrcRect` | `SkIRect` | 源矩形区域 |
| `fSurfaceColorType` | `GrColorType` | 源表面的颜色格式 |
| `fDstColorType` | `GrColorType` | 目标缓冲区的颜色格式 |
| `fDstBuffer` | `sk_sp<GrGpuBuffer>` | 目标 GPU 缓冲区(CPU 可读) |
| `fDstOffset` | `size_t` | 目标缓冲区内的偏移量 |

**特点**: 所有成员在构造时初始化,不可变。

## 公共 API 函数

### 构造函数

```cpp
GrTransferFromRenderTask(sk_sp<GrSurfaceProxy> srcProxy,
                         const SkIRect& srcRect,
                         GrColorType surfaceColorType,
                         GrColorType dstColorType,
                         sk_sp<GrGpuBuffer> dstBuffer,
                         size_t dstOffset)
```

**功能**: 创建传输任务。

**参数**:
- `srcProxy`: 源表面代理
- `srcRect`: 要读取的矩形区域
- `surfaceColorType`: 源表面的实际颜色格式
- `dstColorType`: 目标缓冲区的期望颜色格式
- `dstBuffer`: 接收数据的 GPU 缓冲区
- `dstOffset`: 写入缓冲区的起始偏移

**特性**: 构造函数为公开,使用初始化列表直接初始化所有成员。

**设计**: 不使用工厂模式,简化创建流程。

## 内部实现细节

### onIsUsed

```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override
```

**功能**: 检查任务是否使用特定代理。

**实现**:
```cpp
SkASSERT(0 == this->numTargets());  // 该任务没有目标
return proxy == fSrcProxy.get();
```

**断言**: 确认任务不使用目标机制(因为是读取而非写入)。

### gatherProxyIntervals

```cpp
void gatherProxyIntervals(GrResourceAllocator* alloc) const override
```

**功能**: 向资源分配器注册源代理的使用区间。

**实现**:
```cpp
alloc->addInterval(fSrcProxy.get(), alloc->curOp(), alloc->curOp(),
                   GrResourceAllocator::ActualUse::kYes,
                   GrResourceAllocator::AllowRecycling::kYes);
alloc->incOps();
```

**设计注释**: 该任务没有"普通"操作,使用假操作号捕获对 `fSrcProxy` 的读取事实。

**目的**:
- 保持 `fEndOfOpsTaskOpIndices` 同步
- 确保源表面在传输时可用

### onMakeClosed

```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect*) override
```

**功能**: 标记任务已关闭。

**返回值**: `ExpectedOutcome::kTargetUnchanged`

**含义**: 该任务不修改任何渲染目标,仅读取数据。

### onExecute

```cpp
bool onExecute(GrOpFlushState* flushState) override
```

**功能**: 执行实际的数据传输操作。

**流程**:
1. 检查源代理是否已实例化
2. 调用 `GrGpu::transferPixelsFrom` 执行传输

**实现**:
```cpp
if (!fSrcProxy->isInstantiated()) {
    return false;
}
return flushState->gpu()->transferPixelsFrom(
    fSrcProxy->peekSurface(),
    fSrcRect,
    fSurfaceColorType,
    fDstColorType,
    fDstBuffer,
    fDstOffset);
```

**返回值**:
- `true`: 传输成功
- `false`: 代理未实例化或传输失败

### Debug 支持

```cpp
#if defined(GPU_TEST_UTILS)
    const char* name() const final { return "TransferFrom"; }
#endif
```

用于测试中识别任务类型。

### visitProxies_debugOnly

```cpp
#ifdef SK_DEBUG
    void visitProxies_debugOnly(const GrVisitProxyFunc& func) const override {
        func(fSrcProxy.get(), skgpu::Mipmapped::kNo);
    }
#endif
```

**功能**: 在调试模式下访问所有代理。

**参数**: 传递 `Mipmapped::kNo`,因为传输操作不使用 mipmap。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTask` | 基类,提供任务框架 |
| `GrSurfaceProxy` | 延迟表面代理 |
| `GrGpuBuffer` | GPU 缓冲区对象 |
| `GrGpu` | 执行底层传输操作 |
| `GrOpFlushState` | 提供执行时的上下文 |
| `GrResourceAllocator` | 管理资源分配和依赖 |
| `SkIRect` | 矩形区域定义 |
| `GrColorType` | 颜色格式枚举 |

### 被依赖的模块

该任务在以下场景中使用:
- **GPU 回读**: 读取渲染结果到 CPU
- **截图功能**: 捕获屏幕内容
- **纹理下载**: 将 GPU 纹理数据导出
- **异步读取**: 通过 GPU 缓冲区实现非阻塞读取
- **数据验证**: 测试中验证渲染输出

## 设计模式与设计决策

### 单向数据流

只支持 GPU → CPU 方向:
- `fSrcProxy` 是输入(只读)
- `fDstBuffer` 是输出(只写)

**优点**: 职责明确,不混淆数据流向。

### 不可变对象

所有成员在构造后不可变:

**好处**:
- 线程安全(一旦创建就只读)
- 简化推理
- 避免状态不一致

### 分离颜色格式

`fSurfaceColorType` 和 `fDstColorType` 分开:

**原因**:
- GPU 表面可能是不同格式
- 目标缓冲区可能需要特定格式
- 允许 GPU 执行格式转换

**示例**: RGBA8888 表面 → BGRA8888 缓冲区。

### GPU 缓冲区作为中介

使用 `GrGpuBuffer` 而非直接 CPU 指针:

**优势**:
- 异步传输: GPU 可在后台写入缓冲区
- DMA 优化: 利用 GPU 的 DMA 引擎
- 映射灵活性: 缓冲区可稍后映射到 CPU

**流程**:
1. 创建任务,指定缓冲区
2. 任务执行时,GPU 写入缓冲区
3. 稍后,CPU 映射缓冲区读取数据

### 无目标机制

不使用 `GrRenderTask::targets`:

**理由**: 该任务是读取操作,不修改表面,不应影响写入追踪。

## 性能考量

### 异步传输

任务在渲染管线中延迟执行:
- CPU 可继续准备其他工作
- GPU 在空闲时执行传输
- 减少 CPU-GPU 同步点

### DMA 加速

`transferPixelsFrom` 通常使用 GPU 的 DMA 引擎:
- 不占用着色器资源
- 高效的内存拷贝
- 并行执行其他渲染任务

### 格式转换开销

`fSurfaceColorType != fDstColorType` 时:
- GPU 执行像素格式转换
- 比 CPU 转换快(并行处理)
- 可能触发额外的传输步骤(某些 GPU)

### 矩形子区域读取

支持只读取 `fSrcRect`:
- 减少传输数据量
- 节省带宽
- 降低延迟

### 缓冲区重用

`fDstOffset` 参数允许写入缓冲区的特定位置:
- 支持缓冲区池化
- 减少分配次数
- 批量读取多个区域

### 早期失败

检查代理实例化失败时立即返回:

```cpp
if (!fSrcProxy->isInstantiated()) {
    return false;  // 快速路径
}
```

避免不必要的 GPU 操作。

### 回收优化

允许回收 (`AllowRecycling::kYes`):
- 源表面可在读取后释放
- 提高内存效率

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类定义 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 表面代理 |
| `src/gpu/ganesh/GrGpuBuffer.h` | GPU 缓冲区定义 |
| `src/gpu/ganesh/GrGpu.h` | GPU 接口,执行传输 |
| `src/gpu/ganesh/GrOpFlushState.h` | 执行状态管理 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 资源分配协调 |
| `include/core/SkRect.h` | 矩形定义 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 颜色类型定义 |
| `include/gpu/GpuTypes.h` | GPU 通用类型 |
