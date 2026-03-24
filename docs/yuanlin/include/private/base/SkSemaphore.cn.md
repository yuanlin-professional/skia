# SkSemaphore - 轻量级信号量

> 源文件: `include/private/base/SkSemaphore.h`

## 概述

SkSemaphore 是一个轻量级的跨平台信号量实现，结合了用户态原子计数器和操作系统信号量，在不需要阻塞时避免内核调用。该实现基于"部分自旋的轻量级信号量"设计模式，提供高性能的线程同步机制。

## 架构位置

- **所属子系统**: 线程同步工具 (Thread Synchronization)
- **层级**: 私有头文件，位于 `include/private/base/` 目录
- **依赖层次**: 底层同步原语，被线程池和并发算法依赖

## 主要类

### SkSemaphore

跨平台信号量封装类，提供标准的 P/V 操作（wait/signal）。

**继承关系**: 无继承

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCount | std::atomic<int> | 用户态原子计数器，表示可用资源数 |
| fOSSemaphoreOnce | SkOnce | 确保 OS 信号量只初始化一次 |
| fOSSemaphore | OSSemaphore* | 底层操作系统信号量指针 |

## 公共 API 函数

### 构造函数

```cpp
constexpr SkSemaphore(int count = 0)
```

- **功能**: 创建一个信号量，初始计数为 count
- **参数**:
  - `count`: 初始资源数量，默认为0
- **说明**: constexpr 允许编译期构造

### 析构函数

```cpp
SK_SPI ~SkSemaphore()
```

- **功能**: 清理底层操作系统信号量资源
- **说明**: 标记为 SK_SPI（Skia Private Implementation）

### `signal`

```cpp
void signal(int n = 1)
```

- **功能**: 增加计数器 n 次，释放资源
- **参数**:
  - `n`: 增加的数量，默认为1
- **性能建议**: 调用 `signal(n)` 比调用 `signal()` n 次更高效
- **线程安全**: 可从任意线程调用

**实现细节**:
```cpp
int prev = fCount.fetch_add(n, std::memory_order_release);
int toSignal = std::min(-prev, n);
if (toSignal > 0) {
    this->osSignal(toSignal);
}
```

- 使用原子操作增加计数
- 只在计数从负数跨越到非负数时才调用 OS 信号量
- `std::min(-prev, n)` 计算需要唤醒的线程数

### `wait`

```cpp
void wait()
```

- **功能**: 递减计数器，如果计数器 < 0 则阻塞等待
- **阻塞语义**:
  - 如果计数器 >= 0，立即返回
  - 如果计数器 < 0，挂起当前线程直到被 signal 唤醒
- **线程安全**: 可从任意线程调用

**实现细节**:
```cpp
if (fCount.fetch_sub(1, std::memory_order_acquire) <= 0) {
    SK_POTENTIALLY_BLOCKING_REGION_BEGIN;
    this->osWait();
    SK_POTENTIALLY_BLOCKING_REGION_END;
}
```

- 使用原子操作递减计数
- `fetch_sub` 返回递减前的值，<= 0 表示需要阻塞
- 阻塞区域使用宏标记，便于性能分析工具识别

### `try_wait`

```cpp
SK_SPI bool try_wait()
```

- **功能**: 尝试递减计数器，但不阻塞
- **返回值**:
  - `true`: 成功获取资源（计数器 > 0）
  - `false`: 无可用资源（计数器 <= 0）
- **非阻塞**: 总是立即返回

## 内部实现细节

### 混合信号量设计

SkSemaphore 采用两层架构：

**第一层：用户态原子计数器**
- 使用 `std::atomic<int>` 实现
- 处理大多数无竞争的情况
- 避免昂贵的内核调用

**第二层：操作系统信号量**
- 仅在需要阻塞或唤醒线程时使用
- 延迟初始化（通过 SkOnce）
- 平台特定实现（未在头文件中定义）

### OSSemaphore 结构体

```cpp
struct OSSemaphore;
```

- 前向声明，实际定义在平台特定的 .cpp 文件中
- 可能封装 POSIX sem_t、Windows HANDLE 等
- 实现细节对用户隐藏

### 内部辅助函数

```cpp
SK_SPI void osSignal(int n);
SK_SPI void osWait();
```

- 操作系统信号量的具体调用
- 实现在 .cpp 文件中，根据平台不同而异
- 可能使用 sem_post、ReleaseSemaphore 等系统 API

## 算法原理

### 信号量状态机

计数器的语义：
- **count > 0**: 有 count 个可用资源，wait 不阻塞
- **count = 0**: 无可用资源，下一个 wait 会阻塞
- **count < 0**: 有 |count| 个线程正在等待

### signal 的逻辑

```cpp
// 例子1: prev = -3, n = 5
// 有3个线程在等待，现在释放5个资源
// 唤醒 min(3, 5) = 3 个线程
// 最终计数 = -3 + 5 = 2（剩余2个资源）

// 例子2: prev = 2, n = 3
// 无线程等待，直接增加计数
// 不调用 osSignal
// 最终计数 = 2 + 3 = 5
```

关键公式：`toSignal = std::min(-prev, n)`
- 只唤醒确实在等待的线程数量
- 避免虚假唤醒和资源浪费

### wait 的逻辑

```cpp
// fetch_sub(1) 返回递减前的值
// 如果返回值 <= 0，表示原本就没有资源
// 例子1: count = 5 -> fetch_sub -> 4，返回5，不阻塞
// 例子2: count = 0 -> fetch_sub -> -1，返回0，阻塞
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/private/base/SkAPI.h` | 提供 SK_SPI 宏定义 |
| `include/private/base/SkOnce.h` | 确保 OS 信号量单次初始化 |
| `include/private/base/SkThreadAnnotations.h` | 提供线程分析注解 |
| `<atomic>` | 提供原子操作 |
| `<algorithm>` | 提供 std::min |

### 被依赖的模块

此模块被以下场景使用：
- 线程池任务队列同步
- 生产者-消费者模式
- 资源池管理
- 并行算法的屏障同步

## 设计模式与设计决策

### 延迟初始化模式

OS 信号量通过 SkOnce 延迟初始化：
- 如果从不阻塞，永远不分配 OS 资源
- 减少内存占用和初始化开销
- 提高无竞争场景的性能

### 内存顺序选择

```cpp
fCount.fetch_add(n, std::memory_order_release);  // signal
fCount.fetch_sub(1, std::memory_order_acquire);  // wait
```

- **release 语义**: signal 前的所有写操作对后续 wait 可见
- **acquire 语义**: wait 后的所有读操作能看到之前的写操作
- 形成 happens-before 关系，确保数据竞争安全

### 混合信号量的优势

相比纯 OS 信号量：
- 无竞争时零内核调用
- 更快的 signal/wait 操作
- 更好的缓存局部性

相比纯自旋锁：
- 竞争时不浪费 CPU
- 线程调度器友好
- 避免优先级反转

## 性能考量

### 快速路径优化

**无竞争情况**:
- signal: 仅一次原子加法
- wait: 仅一次原子减法
- 无系统调用，性能接近无锁算法

**有竞争情况**:
- signal: 原子加法 + 可能的系统调用
- wait: 原子减法 + 系统调用（阻塞）
- 性能由操作系统调度器决定

### 缓存行影响

```cpp
std::atomic<int> fCount;  // 4字节
SkOnce fOSSemaphoreOnce;  // 平台相关
OSSemaphore* fOSSemaphore;  // 8字节（64位）
```

- 整个对象通常在一个缓存行内
- 减少伪共享（false sharing）的可能性

### 与其他同步原语的比较

| 原语 | 无竞争开销 | 有竞争开销 | 适用场景 |
|------|-----------|-----------|---------|
| SkSemaphore | 极低 | 中等 | 任务队列、资源池 |
| std::mutex | 低 | 高 | 临界区保护 |
| 自旋锁 | 极低 | 极高 | 极短临界区 |
| std::condition_variable | 中 | 中等 | 复杂条件等待 |

## 使用示例

### 生产者-消费者队列

```cpp
class TaskQueue {
    SkSemaphore fSemaphore{0};  // 初始无任务
    std::queue<Task> fQueue;
    std::mutex fMutex;

    void push(Task task) {
        {
            std::lock_guard<std::mutex> lock(fMutex);
            fQueue.push(std::move(task));
        }
        fSemaphore.signal();  // 通知消费者
    }

    Task pop() {
        fSemaphore.wait();  // 等待任务
        std::lock_guard<std::mutex> lock(fMutex);
        Task task = std::move(fQueue.front());
        fQueue.pop();
        return task;
    }
};
```

### 资源池

```cpp
class ResourcePool {
    SkSemaphore fAvailable{10};  // 10个资源

    Resource* acquire() {
        fAvailable.wait();
        return allocateResource();
    }

    void release(Resource* res) {
        freeResource(res);
        fAvailable.signal();
    }
};
```

### 批量操作

```cpp
// 高效释放多个资源
void releaseMultiple(int count) {
    fSemaphore.signal(count);  // 一次调用，比循环 count 次更快
}
```

## 平台相关说明

### POSIX 平台

OSSemaphore 可能封装：
- `sem_t` （POSIX 标准信号量）
- `pthread_mutex_t` + `pthread_cond_t` （条件变量实现）

### Windows 平台

OSSemaphore 可能使用：
- `HANDLE` （通过 CreateSemaphore）
- `CRITICAL_SECTION` + `CONDITION_VARIABLE`

### macOS/iOS 特殊性

- 某些 macOS 版本限制 `sem_t` 的使用
- 可能使用 Grand Central Dispatch (GCD) 的 `dispatch_semaphore_t`

## 线程安全注解

文件包含 `SkThreadAnnotations.h`，支持：
- Clang Thread Safety Analysis
- 潜在阻塞区域标记（`SK_POTENTIALLY_BLOCKING_REGION_BEGIN/END`）
- 帮助静态分析工具检测死锁和竞争条件

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/core/SkSemaphore.cpp` | 平台特定实现 |
| `include/private/base/SkOnce.h` | 提供单次初始化支持 |
| `src/core/SkTaskGroup.h` | 使用信号量进行任务同步 |

## 设计参考

实现基于 Jeff Preshing 的文章：
- **标题**: "A Lightweight Semaphore with Partial Spinning"
- **链接**: http://preshing.com/20150316/semaphores-are-surprisingly-versatile/
- **核心思想**: 混合自旋和阻塞，用户态计数器减少系统调用

## 注意事项

1. **不要过度使用**: 对于简单的互斥，std::mutex 可能更合适
2. **避免死锁**: 确保 signal 和 wait 配对正确
3. **计数器溢出**: 极端情况下 int 可能溢出，但实际很少发生
4. **析构时机**: 确保所有等待线程已退出再析构信号量
5. **跨进程使用**: 此实现不支持跨进程共享，仅限同一进程内的线程

## 性能调优建议

1. **批量 signal**: 使用 `signal(n)` 而非循环 `signal()`
2. **避免虚假唤醒**: 合理设置初始计数
3. **减少竞争**: 考虑使用多个信号量分片
4. **性能分析**: 利用 `SK_POTENTIALLY_BLOCKING_REGION` 宏识别阻塞点
