# GrCopyRenderTask

> 源文件
> - src/gpu/ganesh/GrCopyRenderTask.h
> - src/gpu/ganesh/GrCopyRenderTask.cpp

## 概述

`GrCopyRenderTask` 是 Ganesh GPU 后端中负责表面间像素拷贝操作的渲染任务类。它继承自 `GrRenderTask`，提供了在两个 GPU 表面之间高效拷贝像素的功能。该类支持从源矩形区域拷贝到目标矩形区域，可以处理不同尺寸的拷贝（如果 GPU 支持缩放和过滤），并且在拷贝过程中可以应用采样滤镜。

该类的主要职责是封装表面拷贝操作的所有参数和执行逻辑，将其整合到 Skia 的渲染任务调度系统中。通过将拷贝操作表示为独立的渲染任务，可以实现更好的资源管理、依赖追踪和执行优化。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrCopyRenderTask` 位于渲染任务层次结构中：

```
GrRecordingContext (录制上下文)
    └── GrDrawingManager (绘制管理器)
        └── GrRenderTask (抽象渲染任务)
            └── GrCopyRenderTask (拷贝渲染任务)
```

该类与其他渲染任务一起由 `GrDrawingManager` 管理，参与渲染任务的调度、依赖解析和资源分配。它通过 `GrResourceAllocator` 进行资源分配协调，并在执行阶段通过 `GrOpFlushState` 提交实际的 GPU 命令。

## 主要类与结构体

### GrCopyRenderTask

该类是拷贝渲染任务的核心实现，继承自 `GrRenderTask`。

**继承关系：**
```
GrRenderTask (基类)
    └── GrCopyRenderTask (派生类)
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSrc` | `sk_sp<GrSurfaceProxy>` | 源表面代理，指向要拷贝的源表面 |
| `fSrcRect` | `SkIRect` | 源矩形区域，定义从源表面拷贝的像素范围 |
| `fDstRect` | `SkIRect` | 目标矩形区域，定义拷贝到目标表面的像素范围 |
| `fFilter` | `GrSamplerState::Filter` | 采样滤镜，用于缩放拷贝时的像素插值 |
| `fOrigin` | `GrSurfaceOrigin` | 表面原点，定义坐标系统（顶部或底部原点） |

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<GrRenderTask> Make(GrDrawingManager* drawingMgr,
                                sk_sp<GrSurfaceProxy> dst,
                                SkIRect dstRect,
                                sk_sp<GrSurfaceProxy> src,
                                SkIRect srcRect,
                                GrSamplerState::Filter filter,
                                GrSurfaceOrigin origin);
```

**功能：** 创建一个新的拷贝渲染任务实例。

**参数说明：**
- `drawingMgr`: 绘制管理器，用于注册渲染任务
- `dst`: 目标表面代理
- `dstRect`: 目标矩形区域
- `src`: 源表面代理
- `srcRect`: 源矩形区域
- `filter`: 采样滤镜（Nearest 或 Linear）
- `origin`: 表面原点方向

**前置条件：**
- 源和目标表面必须有效
- 矩形区域必须在各自表面的尺寸范围内

该方法执行断言检查，确保所有矩形区域都包含在对应表面的维度内。这些检查基于调用者应该已经通过 `canCopySurface()` 验证拷贝操作可行的假设。

## 内部实现细节

### 构造函数

私有构造函数初始化所有成员变量，并通过 `addTarget()` 方法将目标表面注册到渲染任务系统中。这确保了依赖追踪和资源分配能够正确处理目标表面。

### 资源分配

`gatherProxyIntervals()` 方法在资源分配阶段被调用，用于声明对源和目标表面的访问时间窗口：

```cpp
void gatherProxyIntervals(GrResourceAllocator* alloc) const override;
```

该方法为源表面和目标表面各创建一个资源访问区间，标记为实际使用（`ActualUse::kYes`）并允许回收（`AllowRecycling::kYes`）。如果任务已被标记为可跳过（`fSrc` 为空），则只增加操作计数而不添加资源区间。

### 任务闭合

`onMakeClosed()` 方法在任务闭合时计算目标表面的更新边界：

```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect* targetUpdateBounds) override;
```

该方法使用 `GrNativeRect::MakeIRectRelativeTo()` 将目标矩形转换为相对于表面原点的坐标，并返回 `ExpectedOutcome::kTargetDirty` 表明目标表面将被修改。

### 执行阶段

`onExecute()` 方法实现实际的拷贝操作：

```cpp
bool onExecute(GrOpFlushState* flushState) override;
```

执行流程：
1. 检查源表面是否存在（如果任务被标记为跳过则直接返回成功）
2. 验证源和目标表面是否已实例化
3. 获取实际的表面指针
4. 将源和目标矩形转换为本地坐标系（考虑表面原点）
5. 调用 `GrGpu::copySurface()` 执行实际的 GPU 拷贝操作

### 可跳过性

`onMakeSkippable()` 方法通过重置源表面引用来标记任务为可跳过：

```cpp
void onMakeSkippable() override { fSrc.reset(); }
```

这允许渲染系统在某些优化场景下跳过不必要的拷贝操作。

### 使用检查

`onIsUsed()` 方法用于依赖追踪：

```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override {
    return proxy == fSrc.get();
}
```

该方法返回给定代理是否是该任务所使用的源表面。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTask` | 基类，提供渲染任务基础设施 |
| `GrSurfaceProxy` | 表面代理系统，用于延迟资源分配 |
| `GrResourceAllocator` | 资源分配器，管理 GPU 资源生命周期 |
| `GrOpFlushState` | 刷新状态，提供执行时的 GPU 访问 |
| `GrGpu` | GPU 接口，执行实际的拷贝命令 |
| `GrSurface` | 具体的 GPU 表面实例 |
| `GrNativeRect` | 坐标转换工具，处理不同原点系统 |
| `GrDrawingManager` | 绘制管理器，管理渲染任务 |
| `SkIRect` | Skia 整数矩形结构 |
| `GrSamplerState` | 采样器状态，定义滤镜类型 |

### 被依赖的模块

`GrCopyRenderTask` 被以下组件使用：

| 模块 | 使用方式 |
|------|---------|
| `GrDrawingManager` | 创建和调度拷贝任务 |
| `GrRenderTaskCluster` | 在渲染任务图中组织拷贝操作 |
| GPU 后端实现 | 通过渲染任务接口执行拷贝 |

## 设计模式与设计决策

### 工厂方法模式

该类使用静态 `Make()` 方法而非公共构造函数，这是典型的工厂方法模式。这种设计的优点：
- 在构造过程中进行参数验证
- 返回智能指针，明确所有权语义
- 允许构造失败时返回 null
- 可以根据参数选择不同的实现（虽然此处未使用）

### 延迟执行

拷贝任务采用延迟执行策略：
- 创建时只记录拷贝参数，不执行实际操作
- 通过代理（Proxy）引用表面，支持延迟资源分配
- 实际执行推迟到刷新阶段

这种设计允许渲染系统进行全局优化，例如重排任务、合并操作或消除冗余拷贝。

### 表面原点处理

该类显式处理表面原点（顶部或底部原点），通过 `GrNativeRect::MakeIRectRelativeTo()` 进行坐标转换。这确保了拷贝操作在不同坐标系统之间正确工作，特别是在与 OpenGL（底部原点）和其他图形 API（顶部原点）交互时。

### 资源生命周期管理

通过 `gatherProxyIntervals()` 方法，该类向资源分配器声明其对表面的使用：
- 明确标记源表面为只读
- 明确标记目标表面为写入
- 允许分配器进行资源复用和内存优化

### 调试支持

代码包含多个调试功能：
- `GPU_TEST_UTILS` 宏保护的任务名称
- `SK_DEBUG` 宏保护的代理访问追踪
- 多个断言确保前置条件

## 性能考量

### 最小化状态改变

拷贝任务通过单一的 GPU 命令完成，避免了复杂的渲染管线设置。这比使用绘制操作模拟拷贝更高效。

### 资源复用

通过向资源分配器标记允许回收，该类支持表面资源的复用。分配器可以在拷贝完成后立即复用源表面的内存。

### 跳过优化

`onMakeSkippable()` 机制允许渲染系统在检测到拷贝结果未被使用时跳过执行，节省 GPU 时间。

### 直接 GPU 拷贝

该类使用 GPU 的原生拷贝功能（如 `glBlitFramebuffer` 或类似命令），这通常比 CPU 拷贝或通过着色器拷贝更快，特别是对于大型表面。

### 坐标转换缓存

虽然每次执行都会转换坐标，但转换逻辑简单且在栈上完成，开销可忽略不计。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类 | 定义渲染任务接口 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 依赖 | 表面代理系统 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 依赖 | 资源分配系统 |
| `src/gpu/ganesh/GrOpFlushState.h` | 依赖 | 刷新状态接口 |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | GPU 抽象接口 |
| `src/gpu/ganesh/GrDrawingManager.h` | 使用者 | 创建和管理任务 |
| `src/gpu/ganesh/GrNativeRect.h` | 依赖 | 坐标转换工具 |
| `src/gpu/ganesh/GrSurface.h` | 依赖 | 具体表面类型 |
| `src/gpu/ganesh/GrSamplerState.h` | 依赖 | 采样器状态定义 |
