# DawnAsyncWait

> 源文件
> - src/gpu/graphite/dawn/DawnAsyncWait.h
> - src/gpu/graphite/dawn/DawnAsyncWait.cpp

## 概述

`DawnAsyncWait` 是 Skia Graphite 中专门为 Dawn/WebGPU 后端设计的异步操作同步工具类。该类提供了一种轻量级的同步机制,用于等待 Dawn 异步操作(如缓冲区映射、着色器编译、命令提交等)完成。它封装了不同平台下的事件循环交互逻辑,支持非阻塞检查和忙等待两种模式。

核心功能包括:信号量式的等待机制、与 Dawn 事件循环的协作、支持可选的忙等待、原子操作保证线程安全。`DawnAsyncWait` 还配套提供了 `DawnAsyncResult<T>` 模板类,用于封装异步操作的返回值,提供类型安全的结果访问接口。

## 架构位置

`DawnAsyncWait` 位于 Skia Graphite 的 Dawn 后端基础设施层,在架构中的位置如下:

```
skgpu::graphite::dawn
├── DawnSharedContext (上下文管理)
├── DawnAsyncWait (异步等待工具)
├── DawnBuffer (使用 DawnAsyncWait)
├── DawnGraphicsPipeline (使用 DawnAsyncWait)
└── DawnResourceProvider (使用 DawnAsyncWait)
```

该类是 Dawn 后端中所有异步操作的同步基础,被缓冲区映射、管线创建、查询结果读取等多个模块使用。它与 `DawnSharedContext` 紧密协作,通过上下文的 `tick()` 方法驱动 Dawn 事件循环,实现异步操作的完成通知。

## 主要类与结构体

### DawnAsyncWait 类

```cpp
class DawnAsyncWait {
public:
    // 构造函数,关联到 DawnSharedContext
    DawnAsyncWait(const DawnSharedContext*);

    // 非阻塞检查:尝试让出执行权给事件循环,检查是否已信号
    bool yieldAndCheck() const;

    // 查询是否允许忙等待
    bool mayBusyWait() const;

    // 阻塞等待:忙等待直到信号触发(仅在允许时可调用)
    void busyWait() const;

    // 标记为已完成(设置信号)
    void signal() { fSignaled = true; }

    // 重置为未信号状态
    void reset() { fSignaled = false; }

private:
    const DawnSharedContext* fSharedContext; // 关联的上下文
    std::atomic_bool fSignaled;              // 原子信号标志
};
```

### DawnAsyncResult<T> 模板类

```cpp
template <typename T>
class DawnAsyncResult {
public:
    // 构造函数,创建关联的异步等待对象
    DawnAsyncResult(const DawnSharedContext* sharedContext);

    // 析构函数,自动等待结果完成
    ~DawnAsyncResult();

    // 设置结果并触发信号
    void set(const T& result);

    // 非阻塞获取:若已就绪返回结果指针,否则返回 nullptr
    const T* getIfReady() const;

    // 阻塞等待并获取结果
    const T& waitAndGet() const;

private:
    DawnAsyncWait fSync; // 内部同步对象
    T fResult;           // 存储的结果
};
```

## 公共 API 函数

### yieldAndCheck()

```cpp
bool DawnAsyncWait::yieldAndCheck() const
```
非阻塞检查异步操作是否完成。如果上下文支持 tick(事件循环驱动),则调用 `tick()` 让出执行权给 Dawn 处理异步回调,然后检查信号状态。该方法是性能敏感的热路径,使用 `memory_order_acquire` 确保内存可见性。

### mayBusyWait()

```cpp
bool DawnAsyncWait::mayBusyWait() const
```
查询当前环境是否允许忙等待。通过检查 `Caps::allowCpuSync()` 判断,通常在支持 tick 的环境下返回 true。该方法防止在不支持忙等待的环境(如 Emscripten 的某些模式)中误用 `busyWait()`。

### busyWait()

```cpp
void DawnAsyncWait::busyWait() const
```
阻塞等待异步操作完成。内部循环调用 `yieldAndCheck()`,不断驱动事件循环直到信号触发。注意:仅在 `mayBusyWait()` 返回 true 时可调用,否则会触发断言失败。

### signal() / reset()

```cpp
void signal()  // 标记为已完成
void reset()   // 重置为未完成状态
```
信号控制方法。`signal()` 由异步操作的回调函数调用,标记操作完成;`reset()` 用于对象复用场景,重置为初始状态。

### DawnAsyncResult::set() / getIfReady() / waitAndGet()

```cpp
void set(const T& result)           // 设置结果并触发信号
const T* getIfReady() const         // 非阻塞获取结果
const T& waitAndGet() const         // 阻塞等待并获取结果
```
`DawnAsyncResult` 的结果访问接口。`set()` 通常由异步回调调用;`getIfReady()` 用于轮询模式;`waitAndGet()` 用于必须等待结果的场景。析构函数会自动调用 `busyWait()` 确保结果就绪,防止资源泄漏。

## 内部实现细节

### 原子信号机制

`fSignaled` 使用 `std::atomic_bool` 实现线程安全:
```cpp
std::atomic_bool fSignaled;
```

访问时使用 `memory_order_acquire` 确保之前的写操作可见:
```cpp
fSignaled.load(std::memory_order_acquire)
```

设置时直接赋值(隐式使用 `memory_order_seq_cst`):
```cpp
fSignaled = true;
```

这种内存序选择平衡了性能和正确性:acquire 语义确保信号触发后的读操作能看到之前的所有写操作,而设置信号时的顺序一致性保证跨线程可见性。

### 事件循环驱动

`yieldAndCheck()` 的核心逻辑:
```cpp
bool DawnAsyncWait::yieldAndCheck() const {
    if (fSharedContext->hasTick()) {
        if (fSignaled.load(std::memory_order_acquire)) {
            return true;  // 已信号,提前返回
        }
        fSharedContext->tick();  // 驱动事件循环
    }
    return fSignaled.load(std::memory_order_acquire);
}
```

该实现的关键点:
1. **提前检查优化**: 若已信号,避免不必要的 `tick()` 调用
2. **有条件驱动**: 仅在支持 tick 时调用,适配不同平台
3. **双重检查**: tick 后再次检查信号,因为回调可能在 tick 中触发

### 忙等待实现

```cpp
void DawnAsyncWait::busyWait() const {
    SkASSERT(fSharedContext->hasTick());
    while (!this->yieldAndCheck()) {}
}
```

这是一个简单的自旋循环,但通过 `yieldAndCheck()` 调用 `tick()`,实际上将 CPU 时间让给 Dawn 处理异步任务,不是纯粹的忙等待。这种设计在单线程 JavaScript 环境(如 Emscripten)中尤为重要,因为异步回调需要事件循环才能执行。

### DawnAsyncResult 的 RAII 语义

```cpp
~DawnAsyncResult() {
    if (fSync.mayBusyWait()) {
        fSync.busyWait();
    }
    SkASSERT(fSync.yieldAndCheck());
}
```

析构函数确保结果就绪:
- 若支持忙等待,则阻塞等待完成
- 断言检查结果已就绪,捕获逻辑错误
- 防止未完成的异步操作导致资源泄漏或悬空引用

## 依赖关系

### 对外依赖

| 依赖类/模块 | 用途 | 依赖类型 |
|------------|------|---------|
| `DawnSharedContext` | 获取上下文信息和 tick 能力 | 强依赖 |
| `Caps` | 查询是否允许 CPU 同步 | 间接依赖 |
| `std::atomic_bool` | 线程安全的信号标志 | 标准库 |
| `SkASSERT` | 调试断言 | 辅助 |

### 被依赖关系

- **DawnBuffer**: 缓冲区映射操作的等待
- **DawnGraphicsPipeline**: 异步着色器编译的等待
- **DawnResourceProvider**: 资源创建异步操作的同步
- **DawnCommandBuffer**: 命令提交和查询结果的等待

## 设计模式与设计决策

### 信号量模式

`DawnAsyncWait` 实现了简化版的信号量(semaphore)模式:
- `signal()` 相当于 V 操作(增加信号)
- `busyWait()` 相当于 P 操作(等待信号)
- 不支持计数,仅支持二元状态(已信号/未信号)

### RAII 资源管理

`DawnAsyncResult` 使用 RAII 模式管理异步结果的生命周期:
- 构造时初始化同步对象
- 析构时自动等待完成
- 确保资源不泄漏,简化调用者代码

### 协作式并发

通过 `tick()` 机制实现协作式并发:
- 不使用操作系统线程或条件变量
- 通过事件循环调度异步任务
- 适配 JavaScript 的单线程事件驱动模型

这种设计使得代码可在多线程原生环境和单线程 Web 环境下统一工作。

### 模板泛型编程

`DawnAsyncResult<T>` 使用模板提供类型安全的异步结果封装:
```cpp
template <typename T> class DawnAsyncResult { ... }
```
支持任意类型的异步结果,避免类型擦除和 void* 指针的使用。

## 性能考量

### 原子操作开销最小化

使用 `memory_order_acquire` 而非 `memory_order_seq_cst`:
```cpp
fSignaled.load(std::memory_order_acquire)
```
在 x86 架构上,acquire 是零开销的编译器屏障,而 seq_cst 可能引入额外的内存屏障指令。

### 提前返回优化

`yieldAndCheck()` 在调用 `tick()` 前先检查信号:
```cpp
if (fSignaled.load(std::memory_order_acquire)) {
    return true;
}
```
避免不必要的事件循环驱动,减少函数调用开销。

### 避免条件变量

不使用 `std::condition_variable`,原因:
1. 不适用于 Emscripten 的异步模型
2. 避免线程上下文切换开销
3. 通过 tick 机制实现更轻量的协作式调度

### 忙等待的权衡

`busyWait()` 是一个忙循环,会消耗 CPU:
- **优点**: 响应延迟低,适合短时间异步操作
- **缺点**: 高 CPU 占用,不适合长时间等待
- **场景**: 主要用于测试或必须同步的场景,生产代码更多使用异步回调

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/dawn/DawnSharedContext.h` | 协作类 | 提供 tick 和 Caps 接口 |
| `src/gpu/graphite/Caps.h` | 间接依赖 | 提供 allowCpuSync() 查询 |
| `src/gpu/graphite/dawn/DawnBuffer.h` | 使用者 | 缓冲区映射等待 |
| `src/gpu/graphite/dawn/DawnGraphicsPipeline.h` | 使用者 | 管线编译等待 |
| `include/core/SkTypes.h` | 基础类型 | 提供 SkASSERT 等宏 |
| `<atomic>` | 标准库 | 提供原子操作支持 |
| `<functional>` | 标准库 | 函数对象支持 |
| `webgpu/webgpu_cpp.h` | 外部依赖 | WebGPU C++ API 头文件 |
