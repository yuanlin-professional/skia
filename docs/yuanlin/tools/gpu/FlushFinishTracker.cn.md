# FlushFinishTracker

> 源文件
> - tools/gpu/FlushFinishTracker.h
> - tools/gpu/FlushFinishTracker.cpp

## 概述

`FlushFinishTracker` 是 Skia GPU 工具集中用于追踪和同步异步 GPU 操作完成的实用工具类。在 GPU 渲染中，许多操作（如 flush）是异步执行的，即 CPU 提交命令后会立即返回，而实际的 GPU 工作可能还在进行中。该类提供了一种机制来等待这些异步操作真正完成，对于性能测试、时序统计和调试场景至关重要。

核心功能包括：注册 GPU flush 完成回调、轮询检查异步工作完成状态、提供超时保护的阻塞等待接口。该类使用引用计数管理生命周期，支持 Ganesh 和 Graphite 两种 GPU 后端，确保在测量时序或验证结果时能够准确捕获 GPU 工作的实际完成时刻。

## 架构位置

`FlushFinishTracker` 位于 `tools/gpu/` 目录下，属于 GPU 测试工具层。在 Skia 的架构中：

1. **测试框架支持**：主要用于性能基准测试（benchmark）和单元测试，确保测量的时间包含真正的 GPU 执行时间
2. **GPU 同步抽象**：封装了不同 GPU 后端的异步工作检查机制，提供统一的同步接口
3. **回调机制桥接**：作为 CPU 和 GPU 之间的桥梁，将 GPU 完成事件传递回 CPU 代码

该类依赖于：
- Ganesh 的 `GrDirectContext`（传统 GPU 后端）
- Graphite 的 `skgpu::graphite::Context`（新一代 GPU 后端）
- Skia 的引用计数基类 `SkRefCnt`
- 跟踪事件系统 `SkTraceEvent`

它主要被性能基准测试工具、时序验证测试和需要精确 GPU 同步的场景使用。

## 主要类与结构体

### FlushFinishTracker

继承自 `SkRefCnt`，使用引用计数管理生命周期的追踪器类。

**关键成员变量：**
- `GrDirectContext* fContext`：Ganesh GPU 上下文指针（仅在 `SK_GANESH` 定义时存在）
- `skgpu::graphite::Context* fGraphiteContext`：Graphite GPU 上下文指针（仅在 `SK_GRAPHITE` 定义时存在）
- `bool fIsFinished`：标记异步操作是否已完成

**关键设计特点：**
- 使用条件编译支持多后端
- 非原子布尔值（当前单线程使用场景）
- 作为回调上下文传递，在 GPU 完成时自动释放引用

### 静态回调函数

#### FlushFinished
```cpp
static void FlushFinished(void* finishedContext)
```
标准的 flush 完成回调函数，从 `void*` 转换回 `FlushFinishTracker` 指针，设置完成标志并释放引用。

#### FlushFinishedResult
```cpp
static void FlushFinishedResult(void* finishedContext, skgpu::CallbackResult)
```
带结果参数的完成回调，忽略结果直接调用 `FlushFinished`。支持更新的回调接口。

## 公共 API 函数

### 构造函数

```cpp
// Ganesh 版本
explicit FlushFinishTracker(GrDirectContext* context);

// Graphite 版本
explicit FlushFinishTracker(skgpu::graphite::Context* context);
```

根据编译配置选择相应的构造函数，存储 GPU 上下文指针。

**参数：**
- `context`：对应的 GPU 上下文，用于后续轮询异步工作完成状态

### setFinished

```cpp
void setFinished()
```

设置完成标志为 `true`，通常由 GPU 完成回调自动调用。

### waitTillFinished

```cpp
void waitTillFinished(std::function<void()> tick = {})
```

阻塞等待直到 GPU 操作完成或超时。

**参数：**
- `tick`：可选的回调函数，在等待循环的每次迭代中调用，可用于更新 UI 或处理其他事件

**行为：**
- 以 2 秒为超时限制
- 循环调用 GPU 上下文的 `checkAsyncWorkCompletion()` 方法
- 如果超时仍未完成，输出警告信息
- 使用跟踪事件记录等待过程

### 静态回调函数（作为函数指针使用）

```cpp
static void FlushFinished(void* finishedContext);
static void FlushFinishedResult(void* finishedContext, skgpu::CallbackResult);
```

这些静态方法设计为传递给 GPU flush 操作的回调函数指针。

## 内部实现细节

### 引用计数生命周期管理

`FlushFinishTracker` 的生命周期管理遵循特殊模式：

1. **创建时**：用户代码创建追踪器对象，通常使用 `sk_sp<FlushFinishTracker>` 持有引用
2. **注册回调**：将追踪器指针作为 `finishedContext` 传递给 flush 操作，并增加引用计数（通过 `ref()`）
3. **回调触发**：GPU 完成时调用 `FlushFinished()`，该函数内部调用 `unref()` 释放一个引用
4. **用户释放**：`waitTillFinished()` 返回后，用户代码释放其持有的引用

这种设计确保追踪器在 GPU 回调执行前不会被销毁。

### 轮询机制

`waitTillFinished()` 使用主动轮询而非被动等待：

```cpp
while (!fIsFinished && (end - begin) < std::chrono::seconds(2)) {
    if (tick) {
        tick();
    }
    // 调用 checkAsyncWorkCompletion() 轮询 GPU 状态
    fContext->checkAsyncWorkCompletion();  // 或 fGraphiteContext->checkAsyncWorkCompletion()
    end = std::chrono::steady_clock::now();
}
```

**优点：**
- 允许在等待期间执行其他任务（通过 `tick` 回调）
- 不依赖操作系统的同步原语
- 适合单线程事件循环模型

**缺点：**
- 会消耗 CPU 资源进行忙等待
- 不适合需要高效 CPU 利用率的场景

### 超时保护

2 秒的硬编码超时防止无限等待：
- 如果 GPU 挂起或驱动问题导致回调永不触发，超时机制避免程序永久阻塞
- 超时后输出警告但不抛出异常，允许测试继续但提醒结果可能不准确

### 多后端支持策略

使用条件编译和运行时检查组合：

```cpp
#if defined(SK_GANESH)
    if (fContext) {
        fContext->checkAsyncWorkCompletion();
        foundContext = true;
    }
#endif
#if defined(SK_GRAPHITE)
    if (fGraphiteContext) {
        fGraphiteContext->checkAsyncWorkCompletion();
        foundContext = true;
    }
#endif
if (!foundContext) {
    SkDEBUGFAIL("No valid Context");
}
```

这种设计允许在同一个二进制中支持多个后端（如果都启用），并在运行时选择正确的上下文。

### 非原子布尔值的理由

注释明确说明 `fIsFinished` 不是原子类型：

> Currently we don't have the this bool be atomic cause all current uses of this class happen on a single thread.

原因：
- 所有操作（flush、轮询、等待）在同一线程上顺序执行
- GPU 回调在同一线程的事件循环中触发（通过 `checkAsyncWorkCompletion()`）
- 避免原子操作的性能开销

未来扩展：如果需要支持多线程（如在后台线程等待），需要将 `fIsFinished` 改为 `std::atomic<bool>`。

## 依赖关系

### 核心依赖

- **SkRefCnt**：引用计数基类，管理对象生命周期
- **GpuTypes.h**：GPU 类型定义（如 `skgpu::CallbackResult`）
- **SkTraceEvent.h**：性能跟踪事件系统

### GPU 后端依赖

**Ganesh：**
- `GrDirectContext`：提供 `checkAsyncWorkCompletion()` 方法

**Graphite：**
- `skgpu::graphite::Context`：提供 `checkAsyncWorkCompletion()` 方法

### 标准库依赖

- **<functional>**：用于 `std::function<void()>` 回调
- **<chrono>**：用于超时计时

### 被依赖

- 性能基准测试工具（`bench/` 目录）
- GPU 单元测试（`tests/` 目录）
- 时序验证测试
- 需要精确 GPU 同步的工具代码

## 设计模式与设计决策

### 回调模式

使用静态回调函数作为 C 风格函数指针传递：
- `FlushFinished` 符合 GPU flush 回调的签名要求
- 通过 `void*` 上下文指针传递追踪器对象
- 避免闭包或绑定器的复杂性

### 引用计数所有权管理

结合引用计数和回调机制：
- 追踪器对象在注册回调时增加引用
- GPU 完成时自动释放引用
- 防止悬空指针和内存泄漏

### 轮询而非事件驱动

选择主动轮询而非信号量或条件变量：
- 简化实现，不需要线程同步原语
- 符合 Skia 测试框架的单线程模型
- 允许在等待期间执行其他代码（`tick` 回调）

### 超时防御式编程

提供超时和警告而非无限等待或崩溃：
- 避免测试挂起
- 通过警告信息提示问题，但不强制终止
- 适合测试环境的容错性要求

### 条件编译的后端支持

使用 `#if defined(SK_GANESH)` 和 `#if defined(SK_GRAPHITE)`：
- 允许选择性编译后端
- 减少未使用后端的代码体积
- 保持接口统一性

### Tick 回调的可选性

`waitTillFinished()` 的 `tick` 参数默认为空：
- 大多数使用场景不需要 tick
- 但为需要更新 UI 或处理事件的场景提供灵活性
- 不增加简单使用场景的复杂度

## 性能考量

### 忙等待的开销

轮询机制会持续消耗 CPU 资源：
- 在等待期间，CPU 会在循环中不断检查状态
- 对于测试场景可接受，但不适合生产代码
- 如果 GPU 操作时间很短，开销相对较小

### 引用计数的开销

每次增减引用都有原子操作的开销：
- 但这是必要的，确保对象不会提前释放
- 相对于 GPU 操作的时间，开销可以忽略不计

### checkAsyncWorkCompletion 的成本

每次轮询都调用 GPU 上下文的方法：
- 这个方法可能需要与驱动交互，检查 GPU 命令缓冲区
- 频率取决于循环速度，没有显式的睡眠
- 在实践中，GPU 操作通常很快完成，循环次数有限

### 超时机制的必要性

2 秒超时是基于经验的合理值：
- 正常情况下，GPU 操作应在毫秒到数百毫秒内完成
- 2 秒足够覆盖绝大多数合法场景
- 但能捕获 GPU 挂起或驱动问题

### 适用场景

该类设计用于：
- **性能测试**：确保测量的时间包含 GPU 执行
- **正确性验证**：确保在检查结果前 GPU 已完成
- **调试和分析**：精确控制同步点

不适用于：
- 高并发场景（非线程安全）
- 需要高效 CPU 利用率的生产代码
- 需要精确毫秒级控制的实时系统

## 相关文件

### 核心依赖

- `include/core/SkRefCnt.h` - 引用计数基类
- `include/gpu/GpuTypes.h` - GPU 类型定义
- `src/core/SkTraceEvent.h` - 性能跟踪系统

### GPU 后端

- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 上下文
- `include/gpu/graphite/Context.h` - Graphite 上下文

### 使用场景

- `bench/` - 性能基准测试工具
- `tests/` - GPU 相关的单元测试
- `tools/gpu/GrContextFactory.h` - GPU 上下文工厂，常与追踪器配合使用

### 相关工具类

- `tools/gpu/GpuTimer.h` - GPU 时间测量工具
- `tools/Timer.h` - 通用计时器
- `tools/AutoreleasePool.h` - 资源池管理

### 典型使用示例位置

- `bench/BenchGpuClock.cpp` - GPU 时钟基准测试
- `tests/GrContextFactoryTest.cpp` - 上下文工厂测试
