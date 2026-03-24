# SkTaskGroup

> 源文件: src/core/SkTaskGroup.h, src/core/SkTaskGroup.cpp

## 概述

`SkTaskGroup` 是 Skia 中用于任务并行化的核心组件,提供了一个高层次的接口来管理和执行异步任务。它封装了任务提交、执行追踪和同步等待的功能,支持在多线程环境中有效地分配和执行工作负载。该类使用 `SkExecutor` 作为底层执行引擎,通过引用计数跟踪待处理任务,并提供了非阻塞的完成状态查询和阻塞式等待机制。

## 架构位置

`SkTaskGroup` 位于 Skia 核心层的并发控制模块中,是任务调度系统的高级封装:
- **位置**: `src/core/` - Skia 核心实现目录
- **层次**: 应用层并发工具,构建在 `SkExecutor` 之上
- **用途**: 为图形处理、批量操作等并行化场景提供任务组管理

## 主要类与结构体

### SkTaskGroup

任务组管理类,负责任务的添加、执行追踪和同步。

**继承关系**:
- 继承自 `SkNoncopyable` - 禁止拷贝,确保任务组的唯一性

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPending` | `std::atomic<int32_t>` | 原子计数器,追踪待处理任务数量 |
| `fExecutor` | `SkExecutor&` | 执行器引用,负责实际任务调度 |

### SkTaskGroup::Enabler

测试辅助类,用于创建和配置线程池执行器。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fThreadPool` | `std::unique_ptr<SkExecutor>` | 线程池执行器实例 |

## 公共 API 函数

### 构造与析构

```cpp
explicit SkTaskGroup(SkExecutor& executor = SkExecutor::GetDefault())
```
创建任务组,可指定执行器或使用默认执行器。

```cpp
~SkTaskGroup()
```
析构函数,自动调用 `wait()` 等待所有任务完成。

### 任务添加

```cpp
void add(std::function<void(void)> fn)
void add(std::function<void(void)> fn, int workList)
```
添加单个任务到任务组。第二个重载允许指定工作列表编号用于任务分组。

```cpp
void batch(int N, std::function<void(int)> fn)
```
批量添加 N 个任务,每个任务接收不同的索引参数 (0 到 N-1)。

### 任务控制

```cpp
void discardAllPendingWork()
```
丢弃所有待处理的任务,减少待处理计数。

```cpp
bool done() const
```
检查所有任务是否已完成,非阻塞操作。

```cpp
void wait()
```
阻塞等待所有任务完成,期间会主动协助执行器处理任务。

## 内部实现细节

### 原子计数管理

`SkTaskGroup` 使用 `std::atomic<int32_t>` 实现无锁的任务计数:
- `add()` 操作使用 `fetch_add(+1, std::memory_order_relaxed)` 增加计数
- 任务完成时使用 `fetch_add(-1, std::memory_order_release)` 减少计数
- `done()` 检查使用 `load(std::memory_order_acquire)` 读取计数,确保内存可见性

### 工作窃取机制

`wait()` 实现采用主动协助策略而非被动等待:
```cpp
while (!this->done()) {
    fExecutor.borrow();
}
```
调用线程会从执行器中"借用"任务来执行,避免死锁并提高 CPU 利用率。这允许 `SkTaskGroup` 任意深度嵌套在单个 `SkExecutor` 上。

### Lambda 捕获优化

添加任务时,使用 move 语义减少拷贝:
```cpp
fExecutor.add([this, fn{std::move(fn)}] {
    fn();
    fPending.fetch_add(-1, std::memory_order_release);
}, workList);
```

### 批量任务实现

`batch()` 通过循环创建任务:
```cpp
fPending.fetch_add(+N, std::memory_order_relaxed);
for (int i = 0; i < N; i++) {
    fExecutor.add([fn, i, this] {
        fn(i);
        fPending.fetch_add(-1, std::memory_order_release);
    });
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkExecutor.h` | 底层任务执行引擎 |
| `include/core/SkTypes.h` | 基础类型定义 |
| `include/private/base/SkNoncopyable.h` | 不可拷贝基类 |
| `<atomic>` | 原子操作支持 |
| `<functional>` | std::function 支持 |

### 被依赖的模块

`SkTaskGroup` 在 Skia 中被广泛用于:
- 图像解码和编码的并行处理
- 批量图形对象生成
- 测试框架中的并发测试执行

## 设计模式与设计决策

### 1. RAII 模式
析构函数自动调用 `wait()`,确保任务组销毁前所有任务完成,防止悬空引用。

### 2. 引用语义
持有 `SkExecutor&` 而非拥有执行器,允许多个任务组共享同一个执行器,提高资源利用率。

### 3. 工作窃取 (Work Stealing)
`wait()` 中的 `fExecutor.borrow()` 实现了工作窃取机制,避免线程空闲等待,同时支持嵌套任务组。

### 4. 内存顺序优化
- 任务添加使用 `relaxed`,因为只需保证原子性
- 任务完成使用 `release`,确保任务内存操作对后续可见
- 状态检查使用 `acquire`,确保看到最新的完成状态

## 性能考量

### 1. 低开销计数
使用原子变量而非互斥锁,减少同步开销。

### 2. 批量优化机会
`batch()` API 提示实现可以进行批量优化,虽然当前实现较简单(注释提到可能有更聪明的分块逻辑)。

### 3. 避免过度创建线程
通过 `SkExecutor` 复用线程池,避免每个任务组都创建新线程。

### 4. 主动执行策略
`wait()` 中主动执行任务而非被动等待,提高 CPU 利用率,特别是在嵌套任务场景中。

### 5. Move 语义
充分利用 move 语义传递 lambda,减少不必要的拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkExecutor.h` | 依赖 | 定义底层执行器接口 |
| `include/private/base/SkNoncopyable.h` | 继承 | 提供不可拷贝语义 |
| `src/core/SkTaskGroup.h` | 声明 | 类声明和公共接口 |
| `src/core/SkTaskGroup.cpp` | 实现 | 成员函数实现 |

## 使用示例

```cpp
// 创建任务组
SkTaskGroup tasks;

// 添加单个任务
tasks.add([]() { /* 执行某些工作 */ });

// 批量添加并行任务
tasks.batch(100, [](int i) {
    // 处理第 i 个元素
});

// 等待所有任务完成
tasks.wait();
```

测试环境配置:
```cpp
SkTaskGroup::Enabler enabler(4);  // 创建 4 线程的线程池
// 此时 SkExecutor::GetDefault() 返回该线程池
```
