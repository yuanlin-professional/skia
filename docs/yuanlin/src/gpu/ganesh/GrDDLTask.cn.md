# GrDDLTask

> 源文件
> - src/gpu/ganesh/GrDDLTask.h
> - src/gpu/ganesh/GrDDLTask.cpp

## 概述

`GrDDLTask` 是 Skia Ganesh 渲染引擎中用于执行延迟显示列表（Deferred Display List，DDL）的渲染任务。它继承自 `GrRenderTask`，作为DDL内部渲染任务与主渲染任务图（DAG）之间的隔离层。

DDL是一种预录制的渲染命令序列，可以在一个上下文中录制，然后在另一个上下文中回放。`GrDDLTask` 确保DDL内部的所有渲染任务作为一个原子块执行，不会被DAG的拓扑排序重新排序，保持了DDL录制时的执行顺序。

## 架构位置

`GrDDLTask` 位于 Skia GPU 渲染任务管理架构中：

```
Skia GPU Rendering Task System
├── GrDrawingManager (绘制管理器)
│   └── Render Task DAG (渲染任务有向无环图)
│       ├── GrOpsTask (操作任务)
│       ├── GrCopyRenderTask (拷贝任务)
│       ├── GrDDLTask ← 当前模块
│       └── 其他 GrRenderTask
├── GrDeferredDisplayList (DDL容器)
│   └── fRenderTasks (DDL内部任务列表)
└── GrOpFlushState (刷新状态)
```

该模块在架构中的职责：
- 将DDL中的渲染任务集成到主渲染DAG中
- 隔离DDL内部任务，防止被重新排序
- 转发准备、执行和清理操作到DDL内部任务
- 管理DDL目标代理的依赖关系

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDDLTask` | `GrRenderTask` | DDL渲染任务封装器 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDDL` | `sk_sp<const GrDeferredDisplayList>` | 持有的延迟显示列表 |
| `fDDLTarget` | `sk_sp<GrRenderTargetProxy>` | DDL的目标渲染表面代理 |

## 公共 API 函数

### 构造函数
```cpp
GrDDLTask(GrDrawingManager* drawingMgr,
          sk_sp<GrRenderTargetProxy> ddlTarget,
          sk_sp<const GrDeferredDisplayList> ddl);
```
创建DDL任务实例。

**参数说明：**
- `drawingMgr`: 绘制管理器，用于更新任务依赖关系
- `ddlTarget`: DDL的目标渲染表面
- `ddl`: 要执行的延迟显示列表

**构造逻辑：**
1. 遍历DDL中的所有渲染任务
2. 为每个任务的目标代理设置最后的渲染任务指针
3. 立即关闭任务（设置 `kClosed_Flag`），不接受额外任务

### 析构函数
```cpp
~GrDDLTask() override;
```
默认析构函数，智能指针自动管理生命周期。

### 刷新和清理

#### requiresExplicitCleanup
```cpp
bool requiresExplicitCleanup() const override { return true; }
```
返回 `true`，表示DDL内部任务需要显式清理通知，因为它们不在主DAG中。

#### endFlush
```cpp
void endFlush(GrDrawingManager* drawingManager) override;
```
刷新结束时调用，转发到DDL内部的所有渲染任务。

#### disown
```cpp
void disown(GrDrawingManager* drawingManager) override;
```
放弃任务所有权时调用，转发到DDL内部的所有渲染任务。

### 任务查询

#### onIsUsed
```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override;
```
检查指定的表面代理是否被此任务使用。

**逻辑：**
1. 检查是否是DDL目标代理
2. 遍历DDL内部任务，检查它们是否使用该代理

### 资源分配

#### gatherProxyIntervals
```cpp
void gatherProxyIntervals(GrResourceAllocator* alloc) const override;
```
收集代理使用区间，用于资源分配。

**实现细节：**
- 调用 `alloc->incOps()` 占用一个操作索引（即使没有代理）
- 转发到DDL内部所有任务的 `gatherProxyIntervals`

### 任务执行

#### onMakeClosed
```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect* targetUpdateBounds) override;
```
任务关闭时调用，但DDL任务在构造时已关闭，此方法不应被调用。

#### onPrePrepare
```cpp
void onPrePrepare(GrRecordingContext*) override;
```
预准备阶段调用，但DDL任务不应递归出现在DDL中，此方法不应被调用。

#### onPrepare
```cpp
void onPrepare(GrOpFlushState* flushState) override;
```
准备阶段，转发到DDL内部所有任务的 `prepare` 方法。

#### onExecute
```cpp
bool onExecute(GrOpFlushState* flushState) override;
```
执行阶段，遍历DDL内部所有任务并执行。

**返回值：** 如果任何内部任务发出了GPU命令，返回 `true`。

### 调试支持（GPU_TEST_UTILS）

#### dump
```cpp
void dump(const SkString& label,
          SkString indent,
          bool printDependencies,
          bool close) const final;
```
输出任务的调试信息，包括DDL目标和所有子任务的详细信息。

#### name
```cpp
const char* name() const final { return "DDL"; }
```
返回任务类型名称 "DDL"。

#### visitProxies_debugOnly
```cpp
void visitProxies_debugOnly(const GrVisitProxyFunc&) const override {}
```
空实现，因为DDL任务的代理访问通过内部任务处理。

## 内部实现细节

### 构造时的依赖关系设置

```cpp
GrDDLTask::GrDDLTask(GrDrawingManager* drawingMgr,
                     sk_sp<GrRenderTargetProxy> ddlTarget,
                     sk_sp<const GrDeferredDisplayList> ddl)
        : fDDL(std::move(ddl))
        , fDDLTarget(std::move(ddlTarget)) {

    for (auto& task : fDDL->priv().renderTasks()) {
        SkASSERT(task->isClosed());

        for (int i = 0; i < task->numTargets(); ++i) {
            drawingMgr->setLastRenderTask(task->target(i), task.get());
        }
    }

    // DDL任务不接受额外任务
    this->setFlag(kClosed_Flag);
}
```

**关键点：**
1. 所有DDL内部任务必须已关闭
2. 更新绘制管理器中每个目标代理的最后渲染任务指针
3. 立即标记为关闭状态

### 代理使用检查

```cpp
bool GrDDLTask::onIsUsed(GrSurfaceProxy* proxy) const {
    if (proxy == fDDLTarget.get()) {
        return true;
    }

    for (auto& task : fDDL->priv().renderTasks()) {
        if (task->isUsed(proxy)) {
            return true;
        }
    }

    return false;
}
```

先快速检查DDL目标，然后递归检查内部任务。

### 执行流程

```cpp
bool GrDDLTask::onExecute(GrOpFlushState* flushState) {
    bool anyCommandsIssued = false;
    for (auto& task : fDDL->priv().renderTasks()) {
        if (task->execute(flushState)) {
            anyCommandsIssued = true;
        }
    }
    return anyCommandsIssued;
}
```

按顺序执行所有内部任务，跟踪是否有GPU命令发出。

### 调试输出格式

```cpp
void GrDDLTask::dump(...) const {
    INHERITED::dump(label, indent, printDependencies, false);

    SkDebugf("%sDDL Target: ", indent.c_str());
    if (fDDLTarget) {
        SkString proxyStr = fDDLTarget->dump();
        SkDebugf("%s", proxyStr.c_str());
    }
    SkDebugf("\n");

    SkDebugf("%s%d sub-tasks\n", indent.c_str(), fDDL->priv().numRenderTasks());

    SkString subIndent(indent);
    subIndent.append("    ");

    int index = 0;
    for (auto& task : fDDL->priv().renderTasks()) {
        SkString subLabel;
        subLabel.printf("sub-task %d/%d", index++, fDDL->priv().numRenderTasks());
        task->dump(subLabel, subIndent, printDependencies, true);
    }
    ...
}
```

提供层次化的调试输出，显示DDL及其所有子任务。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrRenderTask` | 基类 |
| `GrDeferredDisplayList` | DDL容器 |
| `GrDeferredDisplayListPriv` | 访问DDL内部任务 |
| `GrDrawingManager` | 绘制管理器 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrResourceAllocator` | 资源分配器 |
| `GrOpFlushState` | 刷新状态 |
| `GrSurfaceProxy` | 表面代理 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrDrawingManager` | 创建并管理DDL任务 |
| `GrDirectContextPriv` | 通过 `createDDLTask` 创建DDL任务 |
| DDL回放系统 | 执行预录制的渲染命令 |

## 设计模式与设计决策

### 代理模式（Proxy Pattern）

`GrDDLTask` 作为DDL内部任务的代理，转发所有操作：
```cpp
void GrDDLTask::onPrepare(GrOpFlushState* flushState) {
    for (auto& task : fDDL->priv().renderTasks()) {
        task->prepare(flushState);
    }
}
```

**优点：**
- 统一接口
- 隔离内部实现
- 控制访问

### 组合模式（Composite Pattern）

`GrDDLTask` 包含多个子任务，但对外表现为单个任务：
```cpp
bool onExecute(GrOpFlushState* flushState) override {
    bool anyCommandsIssued = false;
    for (auto& task : fDDL->priv().renderTasks()) {
        if (task->execute(flushState)) {
            anyCommandsIssued = true;
        }
    }
    return anyCommandsIssued;
}
```

### 不变性保证

DDL任务创建后立即标记为关闭：
```cpp
this->setFlag(kClosed_Flag);
```

保证DDL内容不被修改，维护录制时的语义。

### 延迟执行

DDL支持录制与执行分离：
1. **录制阶段**：在 `GrDeferredDisplayListRecorder` 中录制命令
2. **传输阶段**：DDL可以跨线程传递
3. **回放阶段**：在 `GrDirectContext` 中通过 `GrDDLTask` 执行

### 显式清理

重写 `requiresExplicitCleanup()` 返回 `true`，因为DDL内部任务不在主DAG中，需要显式通知：
```cpp
bool requiresExplicitCleanup() const override { return true; }
```

### 设计决策

1. **原子执行**：DDL内部任务不参与DAG排序，确保按录制顺序执行
2. **封装隔离**：通过 `GrDeferredDisplayListPriv` 访问内部任务，保持封装性
3. **所有权管理**：使用智能指针管理DDL和目标代理的生命周期
4. **前置条件检查**：构造时断言所有内部任务已关闭

## 性能考量

### 批量操作

通过单个 `GrDDLTask` 批量执行多个内部任务，减少调度开销。

### 避免重新排序

保持DDL录制时的任务顺序，避免拓扑排序的计算成本。

### 资源分配优化

`gatherProxyIntervals` 统一处理所有内部任务的资源需求，优化内存分配。

### 早期关闭

构造时立即关闭任务，避免后续的状态检查开销。

### 智能指针开销

使用 `sk_sp` 管理DDL和代理的生命周期，自动引用计数有一定开销，但简化了内存管理。

### 调试代码隔离

调试功能使用条件编译，不影响发布版本性能：
```cpp
#if defined(GPU_TEST_UTILS)
    void dump(...) const final;
#endif
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类 | 渲染任务抽象基类 |
| `include/private/chromium/GrDeferredDisplayList.h` | 使用 | DDL容器 |
| `src/gpu/ganesh/GrDeferredDisplayListPriv.h` | 使用 | DDL特权访问 |
| `src/gpu/ganesh/GrDrawingManager.h` | 使用 | 绘制管理器 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 使用 | 渲染目标代理 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 使用 | 资源分配器 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | 刷新状态 |
| `src/gpu/ganesh/GrDirectContextPriv.cpp` | 被使用 | 创建DDL任务 |
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | 关联 | DDL录制器 |
