# GrRenderTask

> 源文件
> - src/gpu/ganesh/GrRenderTask.h
> - src/gpu/ganesh/GrRenderTask.cpp

## 概述

`GrRenderTask` 是 Ganesh GPU 后端中渲染任务系统的核心抽象基类。它代表了一个针对单个 `GrSurfaceProxy` 的任务,参与 `GrDrawingManager` 的有向无环图(DAG)调度,并通过实现 `onExecute` 方法来修改其目标代理的内容。每个渲染任务可以表示执行命令缓冲区的操作任务(OpsTask)、重新生成 mipmap 的任务等。

该类的主要职责包括:
- 管理渲染任务之间的依赖关系(dependencies 和 dependents)
- 跟踪任务状态(关闭、可跳过、禁用重排序等)
- 提供三阶段执行流程:预准备(prePrepare)、准备(prepare)、执行(execute)
- 管理目标 Surface Proxy 和延迟代理的生命周期
- 支持拓扑排序以优化任务执行顺序

每个渲染任务有一个唯一的 ID,并且维护了它依赖的其他任务列表以及依赖它的任务列表,从而构建出完整的渲染依赖图。

## 架构位置

`GrRenderTask` 位于 Skia GPU 渲染管线的核心层次:

```
GrRecordingContext
    └── GrDrawingManager (管理和调度所有 RenderTask)
        └── GrRenderTask (抽象基类)
            ├── OpsTask (执行绘制操作)
            ├── GrTextureResolveRenderTask (纹理解析任务)
            └── GrDDLTask (延迟显示列表任务)
```

它连接了高层的绘制命令记录与低层的 GPU 命令执行,是 Ganesh 渲染架构中任务调度系统的基础。

## 主要类与结构体

### GrRenderTask 类

**继承关系**:
- 继承自 `SkRefCnt` (引用计数基类)
- 被 `skgpu::ganesh::OpsTask`、`GrTextureResolveRenderTask` 等子类继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fUniqueID | const uint32_t | 任务的唯一标识符 |
| fFlags | uint32_t | 任务状态标志位(已关闭、已分离、可跳过等) |
| fTargets | STArray<1, sk_sp<GrSurfaceProxy>> | 此任务修改的目标表面代理列表 |
| fDeferredProxies | TArray<GrTextureProxy*, true> | 在工作线程上准备内容的纹理代理列表 |
| fDependencies | STArray<1, GrRenderTask*, true> | 此任务依赖的其他任务列表 |
| fDependents | STArray<1, GrRenderTask*, true> | 依赖此任务的其他任务列表 |
| fTextureResolveTask | GrTextureResolveRenderTask* | 关联的纹理解析任务 |

### TopoSortTraits 结构体

提供拓扑排序所需的特性方法,用于任务 DAG 的排序:
- `GetIndex`: 获取任务索引
- `Output`: 标记任务已输出
- `WasOutput`: 检查任务是否已输出
- `SetTempMark/ResetTempMark/IsTempMarked`: 临时标记管理
- `NumDependencies/Dependency`: 依赖关系访问

### Flags 枚举

| 标志位 | 值 | 说明 |
|-------|-----|------|
| kClosed_Flag | 0x01 | 任务已关闭,不能再接受依赖 |
| kDisowned_Flag | 0x02 | 任务已被 DrawingManager 解除所有权 |
| kSkippable_Flag | 0x04 | 任务可以被跳过 |
| kAtlas_Flag | 0x08 | 任务是图集任务 |
| kBlocksReordering_Flag | 0x10 | 不能相对此任务重排序其他任务 |
| kWasOutput_Flag | 0x20 | 拓扑排序标志 |
| kTempMark_Flag | 0x40 | 拓扑排序临时标记 |

## 公共 API 函数

### 生命周期管理

```cpp
GrRenderTask();  // 构造函数,分配唯一ID
void makeClosed(GrRecordingContext*);  // 关闭任务,完成最终准备
void disown(GrDrawingManager*);  // 解除与 DrawingManager 的关联
```

### 执行流程

```cpp
void prePrepare(GrRecordingContext* context);  // 预准备阶段
void prepare(GrOpFlushState* flushState);  // 准备阶段(调度延迟代理上传)
bool execute(GrOpFlushState* flushState);  // 执行阶段
```

### 依赖关系管理

```cpp
void addDependency(GrDrawingManager*, GrSurfaceProxy* dependedOn,
                   skgpu::Mipmapped, GrTextureResolveManager, const GrCaps&);
void addDependenciesFromOtherTask(GrRenderTask* otherTask);
bool dependsOn(const GrRenderTask* dependedOn) const;
void replaceDependency(const GrRenderTask* toReplace, GrRenderTask* replaceWith);
```

### 状态查询

```cpp
bool isClosed() const;  // 是否已关闭
bool isSkippable() const;  // 是否可跳过
bool blocksReordering() const;  // 是否阻止重排序
bool isInstantiated() const;  // 所有目标是否已实例化
uint32_t uniqueID() const;  // 获取唯一ID
int numTargets() const;  // 目标数量
GrSurfaceProxy* target(int i) const;  // 获取指定目标
```

### 特殊功能

```cpp
void makeSkippable();  // 标记为可跳过
virtual skgpu::ganesh::OpsTask* asOpsTask();  // 安全转换为 OpsTask
bool isUsed(GrSurfaceProxy* proxy) const;  // 检查代理是否被使用
```

## 内部实现细节

### 唯一 ID 生成

使用原子操作生成全局唯一的任务 ID:

```cpp
uint32_t GrRenderTask::CreateUniqueID() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == SK_InvalidUniqueID);
    return id;
}
```

### 任务关闭流程

`makeClosed` 执行以下操作:
1. 调用子类的 `onMakeClosed` 获取目标更新边界
2. 如果目标被标记为脏,更新 MSAA 脏区域和 mipmap 状态
3. 如果存在纹理解析任务,添加为依赖并关闭它
4. 设置关闭标志

### 依赖关系处理

从 Surface Proxy 依赖转换为 RenderTask 依赖的复杂逻辑:
- 检测自读情况(dst reads),无需添加依赖
- 处理 MSAA 解析和 mipmap 生成需求
- 创建或重用 `GrTextureResolveRenderTask`
- 避免重复依赖
- 关闭被依赖的任务以确保正确的执行顺序

### 标志位管理

使用位操作高效管理任务状态,并在 fFlags 的高 25 位存储拓扑排序索引:
- 低 7 位:状态标志
- 高 25 位:拓扑排序索引(最多支持 33,554,432 个任务)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrDrawingManager | 任务生命周期管理和调度 |
| GrSurfaceProxy | 目标表面代理 |
| GrTextureProxy | 延迟纹理上传 |
| GrOpFlushState | 准备和执行阶段的状态 |
| GrResourceAllocator | GPU 资源分配 |
| GrTextureResolveRenderTask | 纹理解析任务 |
| GrTextureResolveManager | 解析任务管理 |
| GrCaps | GPU 能力查询 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| skgpu::ganesh::OpsTask | 继承 GrRenderTask,实现绘制操作任务 |
| GrTextureResolveRenderTask | 继承 GrRenderTask,实现 MSAA/mipmap 解析 |
| GrDDLTask | 继承 GrRenderTask,实现延迟显示列表 |
| GrDrawingManager | 管理所有 RenderTask 的调度和执行 |
| GrRenderTaskCluster | 使用内部链表接口进行任务聚类 |

## 设计模式与设计决策

### 模板方法模式

`GrRenderTask` 定义了任务执行的框架流程:
- `prepare()` 调用虚函数 `onPrepare()`
- `execute()` 调用纯虚函数 `onExecute()`
- `makeClosed()` 调用纯虚函数 `onMakeClosed()`

子类通过重写这些虚函数实现具体行为,基类负责通用逻辑。

### 依赖注入

通过 `GrDrawingManager`、`GrTextureResolveManager` 等参数注入依赖,降低耦合度,便于测试。

### 延迟实例化

使用 `fDeferredProxies` 支持纹理的延迟上传,优化资源管理和并发性能。

### 标志位优化

使用单个 `uint32_t` 存储多个布尔状态和索引,减少内存占用。

### 性能优化的纹理解析

每个 RenderTask 重用单个 `fTextureResolveTask`,将多次解析操作批量处理,避免频繁的任务切换开销(见 skbug.com/40040728)。

### DAG 调度

通过依赖关系构建 DAG,支持:
- 并行执行无依赖的任务
- 自动检测循环依赖(调试模式)
- 拓扑排序优化执行顺序

## 性能考量

### 内存布局优化

- 使用 `STArray<1, ...>` 作为容器,优化单目标/单依赖的常见情况
- 避免大多数任务的堆分配

### 减少虚函数调用

- 内联简单的访问函数
- 仅在必要时使用虚函数

### 原子操作优化

使用 `std::memory_order_relaxed` 生成唯一 ID,避免不必要的内存屏障。

### 批量处理

- 纹理解析任务复用减少任务切换
- 延迟代理批量上传

### 跳过优化

支持 `makeSkippable()` 标记可跳过的任务,避免不必要的 GPU 工作。但这是一个优化标志,不是所有任务都会真正跳过执行。

### 避免重复操作

- 检查依赖关系避免重复添加
- 检查已关闭状态避免重复关闭

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrDrawingManager.h/cpp | 管理者 | 管理所有 RenderTask 的调度 |
| src/gpu/ganesh/ops/OpsTask.h/cpp | 子类 | 主要的绘制操作任务实现 |
| src/gpu/ganesh/GrTextureResolveRenderTask.h/cpp | 子类 | MSAA 和 mipmap 解析任务 |
| src/gpu/ganesh/GrSurfaceProxy.h/cpp | 依赖 | 目标表面代理 |
| src/gpu/ganesh/GrRenderTargetProxy.h/cpp | 依赖 | 渲染目标代理 |
| src/gpu/ganesh/GrTextureProxy.h/cpp | 依赖 | 纹理代理 |
| src/gpu/ganesh/GrOpFlushState.h/cpp | 依赖 | 刷新状态管理 |
| src/gpu/ganesh/GrResourceAllocator.h/cpp | 依赖 | 资源分配 |
| include/core/SkRefCnt.h | 基类 | 引用计数基类 |
