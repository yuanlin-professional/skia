# GrDeferredDisplayList

> 源文件
> - src/gpu/ganesh/GrDeferredDisplayList.cpp

## 概述

`GrDeferredDisplayList`（DDL，延迟显示列表）是 Skia Ganesh 渲染引擎中实现跨线程渲染的核心类。它是一个不可变的、预录制的渲染命令集合，可以在一个上下文中录制，然后在另一个上下文中回放。这是 Chromium 浏览器实现 GPU 线程渲染的关键技术。

DDL 包含录制时生成的所有渲染任务、目标代理信息、延迟代理数据和着色器程序数据。它确保录制的命令序列可以安全地在不同线程间传递，并在回放时准确地重现录制时的渲染效果。

## 架构位置

`GrDeferredDisplayList` 位于 Skia DDL 系统的中心：

```
Skia Deferred Display List System
├── Recording Phase (录制阶段)
│   ├── GrDeferredDisplayListRecorder (录制器)
│   ├── GrSurfaceCharacterization (表面特征)
│   └── SkCanvas (绘制画布)
├── DDL Container (DDL容器)
│   ├── GrDeferredDisplayList ← 当前模块
│   ├── fRenderTasks (渲染任务列表)
│   ├── fTargetProxy (目标代理)
│   ├── fLazyProxyData (延迟代理数据)
│   └── fProgramData (程序数据)
└── Replay Phase (回放阶段)
    ├── GrDirectContext (直接上下文)
    ├── GrDDLTask (DDL任务)
    └── SkSurface (目标表面)
```

该模块在架构中的职责：
- 存储录制的渲染任务
- 管理目标代理和延迟代理数据
- 提供程序数据用于预编译
- 支持DDL回放到兼容表面
- 确保线程安全的数据传递

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDeferredDisplayList` | 无 | DDL容器，存储预录制的渲染命令 |
| `ProgramIterator` | 无 | 程序迭代器，用于预编译着色器 |
| `LazyProxyData` | 无 | 延迟代理数据，连接录制和回放 |

### GrDeferredDisplayList 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCharacterization` | `GrSurfaceCharacterization` | 目标表面特征 |
| `fArenas` | `SkArenaAllocWithReset` | Arena内存分配器 |
| `fTargetProxy` | `sk_sp<GrRenderTargetProxy>` | 目标渲染代理 |
| `fLazyProxyData` | `sk_sp<LazyProxyData>` | 延迟代理数据 |
| `fRenderTasks` | `skia_private::TArray<sk_sp<GrRenderTask>>` | 渲染任务列表 |

### LazyProxyData 结构

```cpp
struct LazyProxyData {
    sk_sp<GrRenderTargetProxy> fReplayDest;  // 回放目标代理
};
```

用于在回放时将录制的延迟代理连接到实际的目标表面。

### ProgramIterator

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fDContext` | `GrDirectContext*` | 直接上下文 |
| `fProgramData` | `const TArray<ProgramData>&` | 程序数据引用 |
| `fIndex` | `int` | 当前迭代索引 |

## 公共 API 函数

### 构造函数
```cpp
GrDeferredDisplayList(const GrSurfaceCharacterization& characterization,
                      sk_sp<GrRenderTargetProxy> targetProxy,
                      sk_sp<LazyProxyData> lazyProxyData);
```
创建DDL实例（私有，通过录制器创建）。

**参数说明：**
- `characterization`: 目标表面特征
- `targetProxy`: 目标渲染代理（DDL目标）
- `lazyProxyData`: 延迟代理数据

**断言检查：**
```cpp
SkASSERT(fTargetProxy->isDDLTarget());
```

### 析构函数
```cpp
~GrDeferredDisplayList();
```
清理DDL资源。

**调试检查：**
```cpp
#if defined(SK_DEBUG)
    for (auto& renderTask : fRenderTasks) {
        SkASSERT(renderTask->unique());  // 确保任务唯一所有权
    }
#endif
```

### ProgramIterator 方法

#### 构造函数
```cpp
ProgramIterator(GrDirectContext* dContext, GrDeferredDisplayList* ddl);
```
创建程序迭代器。

#### compile
```cpp
bool compile();
```
编译当前程序。

**返回值：** 编译是否成功

**实现：**
```cpp
bool compile() {
    if (!fDContext || fIndex < 0 || fIndex >= (int)fProgramData.size()) {
        return false;
    }
    return fDContext->priv().compile(fProgramData[fIndex].desc(),
                                     fProgramData[fIndex].info());
}
```

#### done
```cpp
bool done() const;
```
检查是否已遍历所有程序。

#### next
```cpp
void next();
```
移动到下一个程序。

### 回放函数

#### DrawDDL (SkSurface版本)
```cpp
namespace skgpu::ganesh {
    bool DrawDDL(SkSurface* surface, sk_sp<const GrDeferredDisplayList> ddl);
}
```
将DDL回放到指定表面。

**参数说明：**
- `surface`: 目标表面
- `ddl`: 要回放的DDL

**返回值：** 回放是否成功

**检查：**
- 表面和DDL非空
- 表面是Ganesh支持的
- 调用 `SkSurface_Ganesh::draw(ddl)`

#### DrawDDL (sk_sp版本)
```cpp
bool DrawDDL(sk_sp<SkSurface> surface, sk_sp<const GrDeferredDisplayList> ddl);
```
智能指针版本，内部调用指针版本。

## 内部实现细节

### DDL构造逻辑

```cpp
GrDeferredDisplayList::GrDeferredDisplayList(const GrSurfaceCharacterization& characterization,
                                             sk_sp<GrRenderTargetProxy> targetProxy,
                                             sk_sp<LazyProxyData> lazyProxyData)
        : fCharacterization(characterization)
        , fArenas(true)  // 允许重置
        , fTargetProxy(std::move(targetProxy))
        , fLazyProxyData(std::move(lazyProxyData)) {
    SkASSERT(fTargetProxy->isDDLTarget());
}
```

**关键点：**
- 保存表面特征用于兼容性检查
- 创建arena分配器，生命周期与DDL相同
- 目标代理必须标记为DDL目标
- 延迟代理数据用于回放时连接

### 程序迭代器实现

```cpp
GrDeferredDisplayList::ProgramIterator::ProgramIterator(GrDirectContext* dContext,
                                                        GrDeferredDisplayList* ddl)
    : fDContext(dContext)
    , fProgramData(ddl->programData())
    , fIndex(0) {
}

bool ProgramIterator::compile() {
    if (!fDContext || fIndex < 0 || fIndex >= (int)fProgramData.size()) {
        return false;
    }
    return fDContext->priv().compile(fProgramData[fIndex].desc(),
                                     fProgramData[fIndex].info());
}

bool ProgramIterator::done() const {
    return fIndex >= (int)fProgramData.size();
}

void ProgramIterator::next() {
    ++fIndex;
}
```

**使用场景：**
```cpp
// 预编译DDL中的所有着色器
GrDeferredDisplayList::ProgramIterator iter(dContext, ddl.get());
while (!iter.done()) {
    if (!iter.compile()) {
        // 处理编译失败
    }
    iter.next();
}
```

### DDL回放实现

```cpp
namespace skgpu::ganesh {

bool DrawDDL(SkSurface* surface, sk_sp<const GrDeferredDisplayList> ddl) {
    if (!surface || !ddl) {
        return false;
    }
    auto sb = asSB(surface);  // 获取SkSurface_Base
    if (!sb->isGaneshBacked()) {
        return false;
    }
    auto gs = static_cast<SkSurface_Ganesh*>(surface);
    return gs->draw(ddl);
}

bool DrawDDL(sk_sp<SkSurface> surface, sk_sp<const GrDeferredDisplayList> ddl) {
    return DrawDDL(surface.get(), ddl);
}

}
```

**回放流程：**
1. 检查表面和DDL有效性
2. 确认表面是Ganesh后端
3. 调用 `SkSurface_Ganesh::draw(ddl)`
4. 创建 `GrDDLTask` 并添加到绘制管理器
5. 执行DDL中的所有渲染任务

### 延迟代理机制

录制时：
```cpp
// 在录制器中创建延迟代理
fTargetProxy = createLazyRenderTargetProxy(
    [lazyProxyData = fLazyProxyData](...) {
        return lazyProxyData->fReplayDest->peekSurface();
    },
    ...
);
```

回放时：
```cpp
// 在SkSurface_Ganesh::draw中
ddl->fLazyProxyData->fReplayDest = fTarget;  // 设置实际目标
// 执行DDL任务，延迟代理回调触发，获取实际表面
```

### 唯一所有权检查

```cpp
GrDeferredDisplayList::~GrDeferredDisplayList() {
#if defined(SK_DEBUG)
    for (auto& renderTask : fRenderTasks) {
        SkASSERT(renderTask->unique());
    }
#endif
}
```

确保渲染任务没有被外部持有，防止生命周期问题。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrSurfaceCharacterization` | 表面特征描述 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrRenderTask` | 渲染任务 |
| `SkArenaAllocWithReset` | Arena内存分配 |
| `GrDirectContext` | 回放上下文 |
| `GrDirectContextPriv` | 编译程序 |
| `SkSurface_Ganesh` | Ganesh表面 |
| `GrRecordingContext::ProgramData` | 程序数据 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrDeferredDisplayListRecorder` | 创建DDL |
| `GrDDLTask` | 回放DDL |
| `SkSurface_Ganesh` | 绘制DDL到表面 |
| Chromium渲染器 | 跨线程渲染 |
| 着色器预编译系统 | 使用ProgramIterator |

## 设计模式与设计决策

### 不可变对象模式（Immutable Object Pattern）

DDL创建后不可修改：
- 所有成员都是const或私有
- 没有公共setter方法
- 确保线程安全传递

### 迭代器模式（Iterator Pattern）

`ProgramIterator` 提供标准迭代接口：
```cpp
ProgramIterator iter(context, ddl);
while (!iter.done()) {
    iter.compile();
    iter.next();
}
```

### 延迟绑定（Lazy Binding）

使用延迟代理实现录制和回放的解耦：
- 录制时创建延迟代理
- 回放时绑定实际表面

### 资源所有权

使用智能指针清晰管理资源：
- `sk_sp<GrRenderTask>`: 渲染任务所有权
- `sk_sp<GrRenderTargetProxy>`: 目标代理所有权
- `sk_sp<LazyProxyData>`: 延迟数据所有权

### 命名空间封装

回放函数放在 `skgpu::ganesh` 命名空间：
```cpp
namespace skgpu::ganesh {
    bool DrawDDL(SkSurface*, sk_sp<const GrDeferredDisplayList>);
}
```

### 设计决策

1. **不可变性**：确保线程安全和可预测行为
2. **延迟代理**：实现录制和回放的完全解耦
3. **程序预编译**：通过迭代器支持着色器预热
4. **表面特征**：基于特征而非实际表面，提高灵活性
5. **唯一所有权**：渲染任务唯一归DDL所有，简化生命周期管理

## 性能考量

### Arena分配

使用arena分配器优化内存管理：
```cpp
fArenas(true)  // 允许重置，可重用
```

**优点：**
- 快速批量分配
- 一次性释放
- 减少内存碎片
- 提高缓存局部性

### 程序预编译

通过 `ProgramIterator` 支持预编译：
```cpp
// 在后台线程预编译
ProgramIterator iter(context, ddl.get());
while (!iter.done()) {
    iter.compile();  // 异步编译着色器
    iter.next();
}
```

避免回放时的编译停顿。

### 延迟代理开销

延迟代理有一定开销：
- 回调函数调用
- 运行时绑定

但相比跨线程渲染的收益，这是可接受的。

### 移动语义

构造函数使用移动语义避免拷贝：
```cpp
GrDeferredDisplayList(...,
                      sk_sp<GrRenderTargetProxy> targetProxy,
                      sk_sp<LazyProxyData> lazyProxyData)
    : ...
    , fTargetProxy(std::move(targetProxy))
    , fLazyProxyData(std::move(lazyProxyData)) {
}
```

### 唯一所有权检查

仅在调试构建中检查：
```cpp
#if defined(SK_DEBUG)
    SkASSERT(renderTask->unique());
#endif
```

发布版本无开销。

### 迭代器效率

迭代器使用索引而非指针：
```cpp
fIndex < (int)fProgramData.size()
```

避免迭代器失效问题。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/chromium/GrDeferredDisplayList.h` | 头文件 | 公共接口定义 |
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | 创建 | DDL录制器 |
| `include/private/chromium/GrSurfaceCharacterization.h` | 依赖 | 表面特征 |
| `src/gpu/ganesh/GrDeferredDisplayListPriv.h` | 特权访问 | 内部数据访问 |
| `src/gpu/ganesh/GrDDLTask.h` | 使用 | DDL回放任务 |
| `src/gpu/ganesh/GrRenderTask.h` | 依赖 | 渲染任务 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 依赖 | 渲染目标代理 |
| `src/gpu/ganesh/surface/SkSurface_Ganesh.h` | 使用 | Ganesh表面实现 |
| `src/gpu/ganesh/GrDirectContextPriv.h` | 使用 | 直接上下文特权访问 |
| `src/base/SkArenaAlloc.h` | 依赖 | Arena内存分配 |
