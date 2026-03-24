# GrMockRenderTask

> 源文件
> - src/gpu/ganesh/mock/GrMockRenderTask.h

## 概述

`GrMockRenderTask` 是 Skia 图形库中 Mock 后端的渲染任务实现,继承自 `GrRenderTask`。该类提供了一个空操作的渲染任务,用于测试渲染任务依赖图的构建和调度逻辑,而无需真正执行 GPU 命令。它支持手动添加目标、依赖和使用的代理,用于单元测试中验证任务图的正确性。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/
    ├── GrRenderTask          (渲染任务基类)
    └── mock/
        └── GrMockRenderTask  (Mock渲染任务) ← 当前类
```

## 主要类与结构体

### GrMockRenderTask

Mock 渲染任务,用于测试任务依赖图管理。

**继承关系:**
- 基类: `GrRenderTask`(final 类,无派生类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTargets` | `TArray<sk_sp<GrSurfaceProxy>>` | 渲染目标代理列表 |
| `fDependencies` | `TArray<GrRenderTask*>` | 依赖的其他任务 |
| `fUsed` | `TArray<sk_sp<GrSurfaceProxy>>` | 使用的表面代理列表 |

**关键标志:**
- 构造时自动设置 `kDisowned_Flag`,表示不被 DrawManager 拥有

## 公共 API 函数

### 构造函数

```cpp
GrMockRenderTask();
```
创建 Mock 渲染任务,自动标记为"已解除所有权"状态。

### 任务配置方法

```cpp
void addTarget(sk_sp<GrSurfaceProxy> proxy);
void addDependency(GrRenderTask* dep);
void addUsed(sk_sp<GrSurfaceProxy> proxy);
```
手动添加渲染目标、依赖任务和使用的表面,用于构建测试场景。

## 内部实现细节

### 重写的基类方法

#### visitProxies_debugOnly
```cpp
#ifdef SK_DEBUG
void visitProxies_debugOnly(const GrVisitProxyFunc&) const override {
    return;  // 调试模式下不遍历代理
}
#endif
```

#### gatherProxyIntervals
```cpp
void gatherProxyIntervals(GrResourceAllocator*) const override {}
```
空实现,不参与资源分配器的代理间隔收集。

#### onMakeClosed
```cpp
ExpectedOutcome onMakeClosed(GrRecordingContext*, SkIRect*) override {
    SkUNREACHABLE;  // 不应被调用
}
```
标记为不可达,Mock 任务不需要关闭操作。

#### onIsUsed
```cpp
bool onIsUsed(GrSurfaceProxy* proxy) const override {
    for (const auto& entry : fUsed) {
        if (entry.get() == proxy) {
            return true;
        }
    }
    return false;
}
```
检查指定代理是否在使用列表中。

#### onExecute
```cpp
bool onExecute(GrOpFlushState*) override {
    return true;  // 假装执行成功
}
```
空操作执行,始终返回成功。

#### name (仅测试模式)
```cpp
#if defined(GPU_TEST_UTILS)
const char* name() const final {
    return "Mock";
}
#endif
```
返回任务名称用于调试输出。

### 所有权管理

构造函数中设置特殊标志:
```cpp
GrMockRenderTask() : GrRenderTask() {
    // Mock 任务永不被 DrawManager "拥有"
    this->setFlag(kDisowned_Flag);
}
```

这使得任务可以:
- 独立于 DrawManager 存在
- 手动管理生命周期
- 避免自动调度逻辑干扰测试

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrRenderTask` | 基类,提供任务接口 |
| `GrSurfaceProxy` | 表面代理 |
| `GrResourceAllocator` | 资源分配器(空实现) |
| `GrOpFlushState` | 刷新状态(空实现) |
| `GrRecordingContext` | 录制上下文 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| 单元测试 | 构建和验证任务依赖图 |
| `GrMockSurfaceProxy` | 与 Mock 代理配合使用 |
| DAG 测试 | 测试有向无环图逻辑 |

## 设计模式与设计决策

### 空对象模式
提供符合 `GrRenderTask` 接口的空实现,用于测试任务管理逻辑。

### 构建器模式
通过 `addTarget`/`addDependency`/`addUsed` 方法逐步构建任务配置,便于测试设置。

### 最小接口实现
仅实现必要的纯虚函数,其他方法提供空操作或返回安全默认值。

### 显式所有权标记
通过 `kDisowned_Flag` 明确表达任务的特殊生命周期,避免与正常渲染流程冲突。

## 性能考量

### 零执行开销
`onExecute` 立即返回 true,无实际命令编码或提交。

### 最小内存占用
仅存储代理和任务指针,无复杂状态或缓冲区。

### 快速查找
`onIsUsed` 使用线性查找,适合测试中的小规模代理集合(通常 < 10 个)。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTask.h` | 基类 | 渲染任务抽象 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 协作 | 表面代理 |
| `src/gpu/ganesh/mock/GrMockSurfaceProxy.h` | 协作 | Mock 表面代理 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 接口 | 资源分配器 |
| `src/gpu/ganesh/GrOpFlushState.h` | 接口 | 刷新状态 |
| `src/gpu/ganesh/GrRecordingContext.h` | 上下文 | 录制上下文 |
