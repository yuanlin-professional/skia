# GrDeferredDisplayList

> 源文件: `include/private/chromium/GrDeferredDisplayList.h`

## 概述

GrDeferredDisplayList (DDL) 是 Skia Ganesh 渲染引擎中的延迟显示列表类，封装了预处理的 GPU 操作。它允许在一个线程上录制绘制命令，然后在另一个线程或稍后的时间点将这些命令回放到 SkSurface 上，是 Chromium 实现跨线程渲染的核心组件。

## 架构位置

本类位于 Skia 的 Ganesh GPU 后端子系统，专为 Chromium 的多线程渲染架构设计。它在 GrDeferredDisplayListRecorder（录制器）和 SkSurface（回放目标）之间起桥梁作用，属于 DDL 系统的核心数据结构。

## 主要类与结构体

### GrDeferredDisplayList

延迟显示列表主类，继承自 SkNVRefCnt，支持引用计数管理。

**继承关系**: SkNVRefCnt&lt;GrDeferredDisplayList&gt; → GrDeferredDisplayList

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCharacterization | const GrSurfaceCharacterization | 表面特性描述（不可变） |
| fArenas | GrRecordingContext::OwnedArenas | 内存池和分配器 |
| fRenderTasks | skia_private::TArray&lt;sk_sp&lt;GrRenderTask&gt;&gt; | 渲染任务列表 |
| fProgramData | skia_private::TArray&lt;GrRecordingContext::ProgramData&gt; | 程序数据数组 |
| fTargetProxy | sk_sp&lt;GrRenderTargetProxy&gt; | 目标渲染代理 |
| fLazyProxyData | sk_sp&lt;LazyProxyData&gt; | 延迟代理数据 |

### GrDeferredDisplayList::LazyProxyData

延迟代理数据类，继承自 SkRefCnt，用于在回放时提供 DDL 的后备纹理。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fReplayDest | GrRenderTargetProxy* | 回放目标代理（可能成为悬空指针） |

**生命周期**: 该对象需要单独引用计数，因为延迟代理可能比 DDL 本身存活更久。

### GrDeferredDisplayList::ProgramIterator

程序迭代器类，用于遍历和编译 DDL 所需的着色器程序。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDContext | GrDirectContext* | 直接上下文指针 |
| fProgramData | const TArray&lt;ProgramData&gt;& | 程序数据引用 |
| fIndex | int | 当前迭代索引 |

**主要方法**:
- `compile()`: 编译当前程序，返回是否有实际工作（缓存命中不算）
- `done()`: 检查是否遍历完成
- `next()`: 移动到下一个程序

## 公共 API 函数

### `characterization()`

```cpp
const GrSurfaceCharacterization& characterization() const
```

- **功能**: 获取 DDL 关联的表面特性描述
- **返回值**: 表面特性的常量引用
- **用途**: 在回放前验证目标表面是否兼容

### `ProgramIterator` 构造函数

```cpp
ProgramIterator(GrDirectContext*, GrDeferredDisplayList*)
```

- **功能**: 创建程序迭代器
- **参数**:
  - `GrDirectContext*`: 用于编译的直接上下文
  - `GrDeferredDisplayList*`: 待处理的 DDL
- **用途**: 在回放前预编译着色器程序

### `ProgramIterator::compile()`

```cpp
bool compile()
```

- **功能**: 编译当前程序
- **返回值**: 如果有实际编译工作（非缓存命中）返回 true
- **用途**: 驱动着色器编译，减少回放时的卡顿

### `ProgramIterator::done()`

```cpp
bool done() const
```

- **功能**: 检查是否已遍历完所有程序
- **返回值**: 完成返回 true

### `ProgramIterator::next()`

```cpp
void next()
```

- **功能**: 移动到下一个程序
- **前置条件**: `done()` 返回 false

### `priv()`

```cpp
GrDeferredDisplayListPriv priv()
const GrDeferredDisplayListPriv priv() const
```

- **功能**: 访问非公开 API
- **返回值**: 私有接口访问器
- **用途**: 提供给内部实现使用的额外功能

## 全局函数

### `skgpu::ganesh::DrawDDL()`

```cpp
bool DrawDDL(SkSurface*, sk_sp<const GrDeferredDisplayList> ddl)
bool DrawDDL(sk_sp<SkSurface>, sk_sp<const GrDeferredDisplayList> ddl)
```

- **功能**: 将 DDL 绘制到指定表面
- **参数**:
  - `SkSurface*` 或 `sk_sp<SkSurface>`: 目标表面（不能为空）
  - `ddl`: 延迟显示列表（不能为空）
- **返回值**: 如果 DDL 不兼容表面返回 false，否则返回 true
- **实验性参数**: xOffset 和 yOffset（当前未实现，非零会被忽略）
- **示例**: https://fiddle.skia.org/c/@Surface_draw_2

## 内部实现细节

### 成员销毁顺序

成员变量的声明顺序经过精心设计，确保析构函数按正确的顺序清理资源：

1. `fRenderTasks` 首先销毁（可能引用 arena 和内存池）
2. `fArenas` 随后销毁（包含内存池）

这避免了悬空指针问题。

### 延迟代理机制

`LazyProxyData` 充当 DDL 和实际渲染目标之间的桥梁：

- **录制时**: `fReplayDest` 为 nullptr
- **回放时**: GrDrawingManager 填充 `fReplayDest` 指向目标表面的代理
- **风险**: `fReplayDest` 不增加引用计数，可能成为悬空指针
- **约束**: 拥有目标表面的 SkSurface 必须在 DDL 刷新完成前保持有效

### 程序数据

`fProgramData` 存储了 DDL 所需的所有着色器程序信息，`ProgramIterator` 可以在回放前预编译这些程序，避免首次使用时的编译延迟。

### 私有构造函数

```cpp
GrDeferredDisplayList(const GrSurfaceCharacterization& characterization,
                     sk_sp<GrRenderTargetProxy> fTargetProxy,
                     sk_sp<LazyProxyData>)
```

只有友元类（如 GrDeferredDisplayListRecorder）可以创建 DDL 实例，确保对象总是从有效的录制过程中产生。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt | 引用计数基类 |
| SkNVRefCnt | 非虚拟引用计数 |
| GrRecordingContext | 录制上下文 |
| GrSurfaceCharacterization | 表面特性描述 |
| GrRenderTargetProxy | 渲染目标代理 |
| GrRenderTask | 渲染任务 |
| SkTArray | 动态数组容器 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| GrDeferredDisplayListRecorder | 创建 DDL 实例 |
| GrDrawingManager | 回放 DDL 到渲染目标 |
| SkSurface | 接收 DDL 绘制 |
| GrDirectContext | 编译 DDL 程序 |

## 设计模式与设计决策

### 延迟执行模式

DDL 实现了命令模式的延迟变体，将绘制命令的录制和执行分离，支持：
- 多线程并行录制
- 命令重用和缓存
- 异步渲染

### 引用计数共享

使用 `SkNVRefCnt` 实现非虚拟引用计数，减少虚函数开销，同时支持智能指针管理。

### Pimpl 变体

通过友元类和私有访问器（`priv()`）提供扩展接口，既保持了公共 API 的简洁，又允许内部组件访问额外功能。

### 不可变特性

`fCharacterization` 声明为 const，确保 DDL 的目标特性在创建后不可更改，保证了回放的安全性。

### 资源所有权

DDL 拥有 `fArenas` 和 `fRenderTasks`，但 `fReplayDest` 是借用指针，这种混合所有权模型需要用户小心管理生命周期。

## 性能考量

### 预编译优化

`ProgramIterator` 允许在回放前编译所有着色器，避免了渲染时的编译卡顿：

```cpp
GrDeferredDisplayList::ProgramIterator iter(dContext, ddl.get());
while (!iter.done()) {
    iter.compile();
    iter.next();
}
```

### 内存池复用

`fArenas` 包含内存池，DDL 录制的所有临时对象都从这些池中分配，减少了堆分配开销。

### 任务批处理

`fRenderTasks` 将多个绘制操作组织成任务，支持批量提交和优化。

### 零拷贝回放

DDL 直接包含渲染任务，回放时无需重新解析命令，只需执行任务列表。

### xOffset/yOffset 预留

虽然当前未实现，API 预留了偏移参数，为将来支持部分区域回放做准备。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | DDL 录制器 |
| `include/private/chromium/GrSurfaceCharacterization.h` | 表面特性描述 |
| `include/core/SkSurface.h` | DDL 回放目标 |
| `include/gpu/ganesh/GrRecordingContext.h` | 录制上下文 |
| `include/gpu/ganesh/GrDirectContext.h` | 直接上下文 |
| `src/gpu/ganesh/GrRenderTask.h` | 渲染任务实现 |
| `src/gpu/ganesh/GrDrawingManager.h` | 绘制管理器 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 渲染目标代理 |
