# GrGpu - Ganesh GPU 抽象基类

> 源文件: `src/gpu/ganesh/GrGpu.h`, `src/gpu/ganesh/GrGpu.cpp`

## 概述

`GrGpu` 是 Skia Ganesh GPU 后端的核心抽象基类，定义了所有图形 API 后端（OpenGL、Vulkan、Metal、Dawn、Mock）必须实现的接口。它封装了纹理创建、缓冲区管理、像素读写、表面拷贝、渲染通道管理、信号量同步以及 GPU 提交等基础 GPU 操作。每个具体后端（如 `GrGLGpu`、`GrVkGpu`）都继承并实现此类。

## 架构位置

```
GrDirectContext
    |
GrGpu (本文件 - 抽象 GPU 接口)
    |
    +-- GrGLGpu (OpenGL 实现)
    +-- GrVkGpu (Vulkan 实现)
    +-- GrMtlGpu (Metal 实现)
    +-- GrD3DGpu (Direct3D 实现)
    +-- GrMockGpu (Mock 测试实现)
```

`GrGpu` 位于 Ganesh 渲染管线的最底层，直接与图形 API 驱动交互。上层的 `GrResourceProvider`、`GrOpsRenderPass`、`GrDrawingManager` 通过此接口操作 GPU 资源。

## 主要类与结构体

### `GrGpu`

非引用计数类，由 `GrDirectContext` 拥有（通过 `unique_ptr`）。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCaps` | `sk_sp<const GrCaps>` | GPU 能力对象 |
| `fContext` | `GrDirectContext*` | 所属上下文（非引用计数，避免循环引用） |
| `fResetBits` | `uint32_t` | 脏状态位掩码 |
| `fStats` | `Stats` | GPU 操作统计 |
| `fSubmittedProcs` | `STArray<4, SubmittedProc>` | 提交完成回调 |
| `fOOMed` | `bool` | 内存不足标志 |

### `GrGpu::DisconnectType`

```cpp
enum class DisconnectType { kAbandon, kCleanup };
```
- `kAbandon`: 立即停止所有后端 API 调用。
- `kCleanup`: 释放已分配资源后停止。

### `GrGpu::Stats`

GPU 操作统计类（仅在 `GR_GPU_STATS` 启用时收集数据），追踪纹理创建、上传、绘制调用、渲染通道等计数。

### `GrTimerQuery`

```cpp
struct GrTimerQuery { uint32_t query; };
```

GPU 计时查询句柄，目前仅 GL 实现。

## 公共 API 函数

### 资源创建

| 方法 | 说明 |
|------|------|
| `createTexture()` | 创建 GPU 纹理（含 MipMap 和初始数据支持） |
| `createCompressedTexture()` | 创建压缩纹理 |
| `wrapBackendTexture()` | 包装外部后端纹理 |
| `wrapRenderableBackendTexture()` | 包装可渲染的外部纹理 |
| `wrapBackendRenderTarget()` | 包装外部渲染目标 |
| `wrapVulkanSecondaryCBAsRenderTarget()` | 包装 Vulkan 次级命令缓冲区为渲染目标 |
| `createBuffer()` | 创建 GPU 缓冲区 |
| `createBackendTexture()` | 创建后端 API 原生纹理 |

### 像素操作

| 方法 | 说明 |
|------|------|
| `readPixels()` | 从表面读取像素 |
| `writePixels()` | 写入像素到表面 |
| `transferPixelsTo()` | 从传输缓冲区写入纹理 |
| `transferPixelsFrom()` | 从表面读取到传输缓冲区 |
| `transferFromBufferToBuffer()` | GPU 缓冲区间拷贝 |

### 渲染管理

| 方法 | 说明 |
|------|------|
| `getOpsRenderPass()` | 获取 OpsRenderPass 用于记录绘制命令 |
| `resolveRenderTarget()` | 解析 MSAA 渲染目标 |
| `copySurface()` | 表面间拷贝 |
| `executeFlushInfo()` | 执行 flush 后操作（信号量插入等） |
| `submitToGpu()` | 将命令提交到 GPU |

### 同步操作

| 方法 | 说明 |
|------|------|
| `makeSemaphore()` | 创建 GPU 信号量 |
| `wrapBackendSemaphore()` | 包装后端信号量 |
| `insertSemaphore()` / `waitSemaphore()` | 插入/等待信号量 |
| `addFinishedCallback()` | 添加 GPU 完成回调 |
| `checkFinishedCallbacks()` | 检查完成回调 |
| `finishOutstandingGpuWork()` | 等待所有 GPU 工作完成 |

### 状态管理

| 方法 | 说明 |
|------|------|
| `markContextDirty()` | 标记外部修改了 GPU 状态 |
| `disconnect()` | 断开与后端 API 的连接 |
| `isDeviceLost()` | 检查设备是否丢失 |
| `checkAndResetOOMed()` | 检查并重置 OOM 状态 |
| `handleDirtyContext()` | 在操作前处理脏状态 |

## 内部实现细节

### 模板方法模式

`GrGpu` 广泛使用模板方法模式：公共方法执行通用验证和统计，然后委托给 `on*` 虚方法进行后端特定实现。例如：
- `createTexture()` -> `onCreateTexture()`
- `readPixels()` -> `onReadPixels()`
- `copySurface()` -> `onCopySurface()`

### 状态重置机制

```cpp
void handleDirtyContext() {
    if (fResetBits) { this->resetContext(); }
}
```

当外部代码（如应用程序的自定义 GL 调用）修改了 GPU 状态时，通过 `markContextDirty` 设置脏位，在下次操作前重新同步状态。

### 纹理创建验证

`createTextureCommon` 在调用后端特定实现前执行全面的参数验证（尺寸、格式支持、采样数、MipLevel 一致性等）。

### Vulkan 管线缓存

提供 `canDetectNewVkPipelineCacheData()`、`hasNewVkPipelineCacheData()`、`storeVkPipelineCacheData()` 用于 Vulkan 管线缓存的持久化。

## 依赖关系

- **上游依赖**: `GrDirectContext`（拥有者）、`GrCaps`（能力查询）。
- **核心依赖**: `GrTexture`、`GrRenderTarget`、`GrGpuBuffer`、`GrOpsRenderPass`。
- **被依赖**: `GrResourceProvider`、`GrDrawingManager`、所有后端实现。

## 设计模式与设计决策

1. **模板方法模式**: 公共接口负责验证和统计，虚方法负责后端实现，避免每个后端重复验证逻辑。
2. **非引用计数所有权**: `GrGpu` 被 `GrDirectContext` 唯一拥有，`fContext` 为裸指针避免循环引用。
3. **统计与调试**: `Stats` 类在非调试构建中编译为空操作，零性能开销。
4. **OOM 检测**: 后端通过 `setOOMed()` 报告 OOM，上层通过 `checkAndResetOOMed()` 检查。
5. **测试支持**: `GPU_TEST_UTILS` 宏下提供后端纹理验证、测试渲染目标创建等测试接口。

## 性能考量

- `GR_GPU_STATS` 统计在 Release 构建中编译为空，零成本。
- `handleDirtyContext` 仅在外部状态修改时触发重置，正常使用中不执行。
- 状态标记使用位掩码，支持细粒度的状态重置。
- `submitToGpu` 控制批量提交时机，减少 GPU 命令提交频率。

## 相关文件

- `src/gpu/ganesh/GrCaps.h` - GPU 能力查询
- `src/gpu/ganesh/GrOpsRenderPass.h` - 渲染通道
- `src/gpu/ganesh/GrResourceProvider.h` - 资源提供者
- `src/gpu/ganesh/GrTexture.h` / `GrRenderTarget.h` - GPU 资源
- `src/gpu/ganesh/gl/GrGLGpu.h` - OpenGL 实现
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan 实现
- `src/gpu/ganesh/mock/GrMockGpu.h` - Mock 测试实现
