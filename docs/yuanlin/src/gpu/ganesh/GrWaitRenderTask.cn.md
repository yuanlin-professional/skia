# GrWaitRenderTask

> 源文件: src/gpu/ganesh/GrWaitRenderTask.h, src/gpu/ganesh/GrWaitRenderTask.cpp

## 概述

`GrWaitRenderTask` 是 Skia Ganesh GPU 后端中用于同步的渲染任务,专门负责在 GPU 端等待外部信号量(semaphore)完成。它是实现跨 API 同步、多队列协调和外部资源共享的关键机制。

该类继承自 `GrRenderTask`,融入 Ganesh 的渲染任务 DAG,但不实际渲染内容,仅执行同步操作。它持有一组信号量,在执行时通知 GPU 等待这些信号量,确保在继续后续操作前特定的外部工作已完成。

## 架构位置

`GrWaitRenderTask` 在 Ganesh 渲染系统中的位置:

- **上层**: 通常由外部 API 集成代码创建(如 Vulkan/Metal 互操作)
- **同层**: 与其他 `GrRenderTask` 子类并列,插入渲染任务图
- **下层**: 依赖 `GrGpu` 提交信号量等待指令到 GPU

该任务作为同步点,连接 Skia 的渲染管线与外部 GPU 工作流。

## 主要类与结构体

### GrWaitRenderTask 类

**继承关系**:
- 继承自 `GrRenderTask`
- 标记为 `final`,禁止进一步派生

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSemaphores` | `std::unique_ptr<std::unique_ptr<GrSemaphore>[]>` | 信号量指针数组 |
| `fNumSemaphores` | `int` | 信号量数量 |
| `fWaitedOn` | `GrSurfaceProxyView` | 等待关联的表面视图 |

**特殊设计**:
- 双层 `unique_ptr` 确保信号量和数组的独立生命周期管理
- `fWaitedOn` 不参与常规的目标追踪机制

## 公共 API 函数

### 构造函数

```cpp
GrWaitRenderTask(GrSurfaceProxyView surfaceView,
                 std::unique_ptr<std::unique_ptr<GrSemaphore>[]> semaphores,
                 int numSemaphores)
```

**功能**: 创建等待任务。

**参数**:
- `surfaceView`: 关联的表面视图(用于依赖追踪)
- `semaphores`: 要等待的信号量数组
- `numSemaphores`: 信号量数量

**特点**:
- 构造函数为公开,不使用工厂模式
- 使用初始化列表直接转移所有权

## 内部实现细节

### onIsUsed

```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override
```

**功能**: 检查任务是否使用特定代理。

**实现**:
```cpp
return proxy == fWaitedOn.proxy();
```

**意义**: 只关联 `fWaitedOn` 代理,不使用其他资源。

### gatherProxyIntervals

```cpp
void gatherProxyIntervals(GrResourceAllocator* alloc) const override
```

**功能**: 注册代理的资源使用区间。

**关键实现**:
```cpp
SkASSERT(0 == this->numTargets());  // 不使用常规目标机制
auto fakeOp = alloc->curOp();
alloc->addInterval(fWaitedOn.proxy(), fakeOp, fakeOp,
                   GrResourceAllocator::ActualUse::kYes,
                   GrResourceAllocator::AllowRecycling::kYes);
alloc->incOps();
```

**设计理由**:
- 该任务没有"普通"操作,但仍需注册操作索引以保持同步
- 使用"假操作号"捕获对代理的操作事实
- 确保 `fEndOfOpsTaskOpIndices` 保持一致

### onMakeClosed

```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect*) override
```

**功能**: 标记任务已关闭。

**返回值**: `ExpectedOutcome::kTargetUnchanged`

**含义**: 该任务不修改任何表面内容,仅执行同步。

### onExecute

```cpp
bool onExecute(GrOpFlushState* flushState) override
```

**功能**: 执行信号量等待操作。

**实现逻辑**:
```cpp
for (int i = 0; i < fNumSemaphores; ++i) {
    if (fSemaphores[i]) {
        flushState->gpu()->waitSemaphore(fSemaphores[i].get());
    }
}
return true;
```

**错误处理**:
- 如果信号量为空,跳过等待(包装失败的情况)
- 客户端提供的无效信号量被视为可忽略的错误
- 始终返回 `true`(等待操作本身不会失败)

**宽容策略**: 即使部分信号量无效,也继续执行,避免因外部错误导致渲染管线中断。

### fWaitedOn 字段的特殊性

注释明确说明:

> This field is separate from the main "targets" field on GrRenderTask because this task does not actually write to the surface and so should not participate in the normal lastRenderTask tracking that written-to targets do.

**设计决策**:
- 不使用 `GrRenderTask::targets`,避免触发写入追踪
- 单独维护 `fWaitedOn`,仅用于依赖分析
- 防止错误的渲染任务排序

### Debug 支持

```cpp
#if defined(GPU_TEST_UTILS)
    const char* name() const final { return "Wait"; }
#endif
```

用于测试时识别任务类型。

### visitProxies_debugOnly

```cpp
#ifdef SK_DEBUG
    void visitProxies_debugOnly(const GrVisitProxyFunc&) const override {}
#endif
```

空实现,因为没有非目标代理需要访问(注释: "No non-dst proxies")。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTask` | 基类,提供任务框架 |
| `GrSemaphore` | 跨 API 的信号量抽象 |
| `GrSurfaceProxyView` | 表面视图,用于依赖追踪 |
| `GrGpu` | 执行底层 GPU 等待指令 |
| `GrOpFlushState` | 提供执行时的上下文 |
| `GrResourceAllocator` | 管理资源分配和依赖 |

### 被依赖的模块

该任务在以下场景中使用:
- **跨 API 互操作**: Vulkan/Metal/D3D12 与其他图形 API 共享资源
- **多队列同步**: 计算队列和图形队列之间的同步
- **外部纹理导入**: 等待外部渲染完成后使用纹理
- **视频解码集成**: 等待视频帧准备就绪

## 设计模式与设计决策

### 单一职责原则

任务只做一件事:等待信号量。

**优点**:
- 代码简洁易懂
- 职责明确
- 易于测试和调试

### 资源所有权管理

使用 `std::unique_ptr` 的双层包装:

```cpp
std::unique_ptr<std::unique_ptr<GrSemaphore>[]>
```

**原因**:
- 外层管理数组生命周期
- 内层允许单个信号量为空(包装失败)
- 自动释放资源,避免泄漏

### 宽松的错误处理

空信号量不导致任务失败:

**理由**:
- 信号量包装可能因客户端错误失败
- 渲染不应因外部同步错误而完全中断
- 最坏情况是同步失效,而非崩溃

### 分离的代理追踪

`fWaitedOn` 不使用常规目标机制:

**设计考量**:
- 等待操作不修改表面
- 不应影响 `lastRenderTask` 追踪
- 但需要参与依赖分析(确保表面可用)

### Lightweight 设计

成员变量最少化:
- 只存储必要的信号量和代理
- 不持有其他资源
- 内存占用小

## 性能考量

### 异步执行

信号量等待在 GPU 端异步进行:
- CPU 提交等待指令后立即返回
- GPU 在后台等待,不阻塞 CPU
- 允许 CPU 继续准备后续工作

### 批量等待

支持一次等待多个信号量:
- 减少 API 调用次数
- 利用 GPU 的多信号量等待能力

### 无数据传输

该任务不涉及 CPU-GPU 数据传输:
- 开销极低
- 不占用带宽
- 纯粹的同步操作

### 早期跳过

检查信号量有效性并跳过空指针:

```cpp
if (fSemaphores[i]) {
    // 只处理有效信号量
}
```

避免无效操作。

### 资源回收

允许回收 (`AllowRecycling::kYes`):
- 表面可在等待后被重用
- 提高内存效率

### 零拷贝

使用移动语义转移所有权:
- 构造时直接移动 `unique_ptr`
- 避免拷贝开销

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类定义 |
| `src/gpu/ganesh/GrSemaphore.h` | 信号量抽象 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 表面视图定义 |
| `src/gpu/ganesh/GrGpu.h` | GPU 接口,执行等待 |
| `src/gpu/ganesh/GrOpFlushState.h` | 执行状态管理 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 资源分配协调 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | GPU 私有类型定义 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 表面代理基类 |
