# SkSharedMutex

> 源文件: src/base/SkSharedMutex.h, src/base/SkSharedMutex.cpp

## 概述

`SkSharedMutex` 是 Skia 中实现的读写锁（reader-writer lock）机制，类似于 POSIX 的 `pthread_rwlock`。它允许多个线程同时持有共享锁（读锁），但独占锁（写锁）只能由单个线程持有。该实现提供了高性能和调试两个版本，采用信号量机制实现线程同步，不依赖 C++ 标准库的互斥锁，确保跨平台兼容性。

该锁不保证严格的队列顺序，而是在读者和写者之间交替调度。这种设计权衡了公平性以获得更好的性能特征。

## 架构位置

`SkSharedMutex` 位于 Skia 基础设施层的并发控制模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 图形库提供跨平台的读写锁同步原语
- **依赖**: 基于 `SkSemaphore` 实现线程等待和唤醒机制

在 Skia 架构中，它是底层同步原语，被各种需要细粒度并发控制的组件使用，特别是在需要高读取并发性的场景（如缓存、资源池等）。

## 主要类与结构体

### SkSharedMutex

读写锁的核心实现类。

**继承关系**:
- 无继承关系，独立实现

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fQueueCounts` (Release) | `std::atomic<int32_t>` | 原子计数器，打包存储三个计数：共享锁持有数、等待独占锁数、等待共享锁数 |
| `fSharedQueue` (Release) | `SkSemaphore` | 共享锁等待队列的信号量 |
| `fExclusiveQueue` (Release) | `SkSemaphore` | 独占锁等待队列的信号量 |
| `fCurrentShared` (Debug) | `std::unique_ptr<ThreadIDSet>` | 当前持有共享锁的线程集合 |
| `fWaitingExclusive` (Debug) | `std::unique_ptr<ThreadIDSet>` | 等待独占锁的线程集合 |
| `fWaitingShared` (Debug) | `std::unique_ptr<ThreadIDSet>` | 等待共享锁的线程集合 |
| `fSharedQueue[2]` (Debug) | `SkSemaphore[2]` | 双队列设计，用于分离写锁前后的读锁请求 |
| `fMu` (Debug) | `SkMutex` | 调试模式下保护内部状态的互斥锁 |

### SkAutoSharedMutexExclusive

独占锁的 RAII 包装类。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLock` | `SkSharedMutex&` | 引用被管理的共享互斥锁 |

### SkAutoSharedMutexShared

共享锁的 RAII 包装类。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLock` | `SkSharedMutex&` | 引用被管理的共享互斥锁 |

### ThreadIDSet (Debug Only)

调试模式下用于跟踪线程 ID 的辅助类。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fThreadIDs` | `SkTDArray<SkThreadID>` | 存储线程 ID 的动态数组 |

## 公共 API 函数

### SkSharedMutex 核心 API

```cpp
// 构造与析构
SkSharedMutex();
~SkSharedMutex();

// 独占锁操作
void acquire();                    // 获取独占锁（写锁）
void release();                    // 释放独占锁
void assertHeld() const;          // 断言当前线程持有独占锁

// 共享锁操作
void acquireShared();             // 获取共享锁（读锁）
void releaseShared();             // 释放共享锁
void assertHeldShared() const;    // 断言当前线程持有共享锁
```

### RAII 辅助类

```cpp
// 独占锁自动管理
SkAutoSharedMutexExclusive(SkSharedMutex& lock);  // 构造时获取独占锁
~SkAutoSharedMutexExclusive();                    // 析构时释放独占锁

// 共享锁自动管理
SkAutoSharedMutexShared(SkSharedMutex& lock);     // 构造时获取共享锁
~SkAutoSharedMutexShared();                       // 析构时释放共享锁
```

## 内部实现细节

### Release 模式实现（高性能）

Release 模式采用无锁算法和原子操作实现高性能：

1. **位域打包计数器**: `fQueueCounts` 使用 32 位整数的三个 10 位字段存储：
   - Bits 0-9: 共享锁持有数（最多 1024）
   - Bits 10-19: 等待独占锁的线程数
   - Bits 20-29: 等待共享锁的线程数

2. **独占锁获取流程**:
   - 原子递增等待独占锁计数
   - 如果有其他等待者或共享锁持有者，则在 `fExclusiveQueue` 上等待
   - 否则立即获取锁

3. **独占锁释放流程**:
   - 原子更新计数器：递减等待独占锁计数
   - 将等待共享锁计数移动到共享锁持有计数
   - 唤醒所有等待的共享锁线程，或单个等待的独占锁线程

4. **共享锁获取流程**:
   - 检查是否有等待的独占锁
   - 有则递增等待共享锁计数并阻塞
   - 无则递增共享锁持有计数并立即返回

5. **共享锁释放流程**:
   - 原子递减共享锁持有计数
   - 如果计数归零且有等待的独占锁，则唤醒一个独占锁线程

### Debug 模式实现（可调试）

Debug 模式提供详细的线程跟踪和错误检测：

1. **线程 ID 跟踪**: 使用 `ThreadIDSet` 记录所有持有锁和等待锁的线程
2. **死锁检测**: 检测重复获取锁、释放未持有的锁等错误
3. **双队列设计**: 使用两个共享锁队列，区分写锁前后的读锁请求，确保公平性
4. **断言验证**: `assertHeld` 和 `assertHeldShared` 在 Release 模式下是空操作，在 Debug 模式下进行严格检查

### Thread Sanitizer 集成

代码集成了 Thread Sanitizer (TSan) 注解：
- `ANNOTATE_RWLOCK_CREATE`: 通知 TSan 锁的创建
- `ANNOTATE_RWLOCK_ACQUIRED`: 通知 TSan 锁的获取
- `ANNOTATE_RWLOCK_RELEASED`: 通知 TSan 锁的释放
- `ANNOTATE_RWLOCK_DESTROY`: 通知 TSan 锁的销毁

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkSemaphore` | 提供跨平台的信号量实现，用于线程阻塞和唤醒 |
| `SkMutex` | Debug 模式下保护内部数据结构 |
| `SkThreadID` | Debug 模式下跟踪线程身份 |
| `SkTDArray` | Debug 模式下存储线程 ID 集合 |
| `SkThreadAnnotations` | 提供编译器线程安全注解支持 |
| `<atomic>` | 提供原子操作支持 |

### 被依赖的模块

`SkSharedMutex` 作为底层同步原语，被以下类型的模块使用：

| 使用场景 | 说明 |
|---------|------|
| 资源缓存 | 保护共享的缓存数据结构，允许多读单写 |
| 字体管理 | 字体查找表等需要高读取并发性的场景 |
| 图像解码器 | 保护共享的解码器状态 |
| 配置管理 | 保护只读配置数据，偶尔需要更新 |

## 设计模式与设计决策

### 设计模式

1. **RAII 模式**: `SkAutoSharedMutexExclusive` 和 `SkAutoSharedMutexShared` 确保异常安全的锁管理

2. **条件编译策略**: 使用 `#ifdef SK_DEBUG` 在调试和发布版本间切换实现：
   - Debug: 牺牲性能换取可调试性
   - Release: 最大化性能，最小化内存占用

3. **原子操作与无锁编程**: Release 版本使用 CAS（Compare-And-Swap）循环避免显式互斥锁

### 设计决策

1. **不保证公平性**:
   - 锁在读者和写者之间交替，不按 FIFO 顺序
   - 优点: 简化实现，提高性能
   - 缺点: 可能导致写者饥饿

2. **三合一计数器**:
   - 将三个计数打包到单个原子变量中
   - 优点: 单次 CAS 操作更新所有计数，提高原子性
   - 限制: 每个计数最多 1024（10 位）

3. **信号量而非条件变量**:
   - 使用 `SkSemaphore` 而非标准库条件变量
   - 原因: 避免 C++ 标准库依赖，确保跨平台一致性

4. **ThreadIDSet 实现**:
   - Debug 模式使用简单的动态数组而非哈希集合
   - 原因: Debug 模式重调试性而非性能，简单实现易于维护

5. **双队列 Debug 实现**:
   - 使用两个共享队列交替，区分写锁前后的读请求
   - 原因: 防止新的读锁请求无限期阻塞等待的写锁

## 性能考量

### 优化策略

1. **快速路径优化**: 无竞争情况下，锁操作仅涉及单次原子操作
2. **批量唤醒**: 释放写锁时一次性唤醒所有等待的读锁线程
3. **内存序优化**:
   - 获取锁使用 `memory_order_acquire`
   - 释放锁使用 `memory_order_release`
   - 最小化同步开销

### 性能特征

- **读-读并发**: 优秀，多个读者可完全并行
- **读-写竞争**: 读者优先于后来的写者
- **写-写竞争**: 严格串行化
- **内存占用**:
  - Release: 16 字节（1 个原子变量 + 2 个信号量）
  - Debug: 约 100+ 字节（包含线程集合和额外调试数据）

### 使用建议

1. **适用场景**:
   - 读多写少的场景
   - 临界区较短的情况
   - 需要高读取并发性的数据结构

2. **不适用场景**:
   - 写密集型场景（考虑使用普通互斥锁）
   - 需要严格公平性的场景
   - 嵌套锁场景（当前实现不支持重入）

3. **最佳实践**:
   - 始终使用 RAII 包装类管理锁的生命周期
   - 尽量缩短临界区长度
   - 避免在持有锁时执行可能阻塞的操作

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkSemaphore.h` | 信号量头文件，提供跨平台信号量接口 |
| `include/private/base/SkMutex.h` | 互斥锁头文件，Debug 模式使用 |
| `include/private/base/SkThreadAnnotations.h` | 线程安全注解，支持静态分析工具 |
| `include/private/base/SkThreadID.h` | 线程 ID 获取功能 |
| `include/private/base/SkTDArray.h` | 动态数组模板，Debug 模式使用 |
| `include/private/base/SkDebug.h` | 调试断言宏定义 |
