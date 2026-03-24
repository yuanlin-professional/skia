# SkSemaphore

> 源文件: src/base/SkSemaphore.cpp

## 概述

`SkSemaphore` 是 Skia 中实现的跨平台信号量（semaphore）同步原语。它提供了对底层操作系统信号量的统一封装，支持 macOS/iOS（使用 GCD dispatch_semaphore）、Windows（使用 Win32 Semaphore API）和 POSIX 系统（使用 sem_t）。信号量是一种计数器，用于控制多个线程对共享资源的访问。

该实现采用混合模式：在无竞争时使用原子操作快速路径，在竞争时才创建和使用操作系统信号量，实现了性能和功能的平衡。

## 架构位置

`SkSemaphore` 位于 Skia 基础设施层的并发控制模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 提供跨平台的信号量同步原语
- **应用场景**: 线程池、任务队列、资源限制、读写锁实现

在 Skia 架构中，它是底层同步原语，被 `SkSharedMutex`、线程池、并行任务调度等模块使用。

## 主要类与结构体

### SkSemaphore

信号量的公共接口类（定义在 `include/private/base/SkSemaphore.h` 中）。

**继承关系**:
- 无继承关系

**关键成员变量**（推测，基于实现）:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCount` | `std::atomic<int>` | 原子计数器，表示可用资源数（快速路径） |
| `fOSSemaphore` | `OSSemaphore*` | 操作系统信号量（慢速路径，延迟创建） |
| `fOSSemaphoreOnce` | `SkOnce` | 确保 OS 信号量只创建一次 |

### SkSemaphore::OSSemaphore

操作系统相关的信号量封装（平台相关实现）。

#### macOS/iOS 实现

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSemaphore` | `dispatch_semaphore_t` | GCD 信号量句柄 |

#### Windows 实现

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSemaphore` | `HANDLE` | Win32 信号量句柄 |

#### POSIX 实现

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSemaphore` | `sem_t` | POSIX 信号量对象 |

## 公共 API 函数

### 核心 API（推测）

```cpp
// 构造与析构
SkSemaphore(int count = 0);      // count: 初始计数
~SkSemaphore();

// 等待信号量
void wait();                      // 减少计数，若为 0 则阻塞

// 尝试等待（非阻塞）
bool try_wait();                  // 若计数 > 0 则减少并返回 true

// 发信号
void signal(int n = 1);           // 增加计数 n 次
```

## 内部实现细节

### 平台相关实现

#### macOS/iOS - GCD Dispatch Semaphore

```cpp
struct SkSemaphore::OSSemaphore {
    dispatch_semaphore_t fSemaphore;

    OSSemaphore() {
        fSemaphore = dispatch_semaphore_create(0);  // 初始计数 0
    }

    ~OSSemaphore() {
        dispatch_release(fSemaphore);
    }

    void signal(int n) {
        while (n --> 0) {
            dispatch_semaphore_signal(fSemaphore);  // 逐个发信号
        }
    }

    void wait() {
        dispatch_semaphore_wait(fSemaphore, DISPATCH_TIME_FOREVER);
    }
};
```

**特点**:
- 使用 GCD（Grand Central Dispatch）的信号量
- `dispatch_semaphore_create(0)` 创建初始计数为 0 的信号量
- `DISPATCH_TIME_FOREVER` 表示无限等待

#### Windows - Win32 Semaphore

```cpp
struct SkSemaphore::OSSemaphore {
    HANDLE fSemaphore;

    OSSemaphore() {
        fSemaphore = CreateSemaphore(
            nullptr,    // 安全属性
            0,          // 初始计数
            MAXLONG,    // 最大计数
            nullptr     // 名称
        );
    }

    ~OSSemaphore() {
        CloseHandle(fSemaphore);
    }

    void signal(int n) {
        ReleaseSemaphore(fSemaphore, n, nullptr);  // 批量释放
    }

    void wait() {
        WaitForSingleObject(fSemaphore, INFINITE);  // 无限等待
    }
};
```

**特点**:
- 使用 Win32 API 的命名信号量
- `MAXLONG` 作为最大计数（约 21 亿）
- 支持批量 `signal(n)`

#### POSIX - sem_t

```cpp
struct SkSemaphore::OSSemaphore {
    sem_t fSemaphore;

    OSSemaphore() {
        sem_init(&fSemaphore, 0, 0);  // pshared=0, count=0
    }

    ~OSSemaphore() {
        sem_destroy(&fSemaphore);
    }

    void signal(int n) {
        while (n --> 0) {
            sem_post(&fSemaphore);  // 逐个发信号
        }
    }

    void wait() {
        // 处理信号中断
        while (sem_wait(&fSemaphore) == -1 && errno == EINTR);
    }
};
```

**特点**:
- 使用 POSIX 标准的 `sem_t`
- `pshared = 0` 表示仅在进程内共享
- `wait()` 循环处理 `EINTR`（信号中断）

### 混合实现策略

`SkSemaphore` 采用混合实现：

1. **快速路径**（无竞争）:
   - 使用原子计数器 `fCount`
   - `signal` 和 `wait` 直接操作原子变量
   - 无需系统调用

2. **慢速路径**（有竞争）:
   - 延迟创建 `OSSemaphore`（通过 `fOSSemaphoreOnce`）
   - 调用操作系统信号量进行线程阻塞

### 关键函数实现

#### osSignal - 操作系统信号

```cpp
void SkSemaphore::osSignal(int n) {
    fOSSemaphoreOnce([this] { fOSSemaphore = new OSSemaphore; });
    fOSSemaphore->signal(n);
}
```

- 使用 `SkOnce` 确保信号量只创建一次（线程安全）
- 调用平台相关的 `signal` 方法

#### osWait - 操作系统等待

```cpp
void SkSemaphore::osWait() {
    fOSSemaphoreOnce([this] { fOSSemaphore = new OSSemaphore; });
    fOSSemaphore->wait();
}
```

- 同样延迟创建信号量
- 调用平台相关的 `wait` 方法

#### try_wait - 尝试等待

```cpp
bool SkSemaphore::try_wait() {
    int count = fCount.load(std::memory_order_relaxed);
    if (count > 0) {
        return fCount.compare_exchange_weak(count, count - 1,
                                             std::memory_order_acquire);
    }
    return false;
}
```

- 使用 CAS（Compare-And-Swap）尝试减少计数
- `memory_order_relaxed` 读取（快速）
- `memory_order_acquire` 交换（确保同步）
- 失败时立即返回 `false`，不阻塞

#### 析构函数

```cpp
SkSemaphore::~SkSemaphore() {
    delete fOSSemaphore;
}
```

- 删除可能创建的操作系统信号量
- 若从未竞争，`fOSSemaphore` 为 `nullptr`，删除是安全的

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 平台 |
|------|------|------|
| `<dispatch/dispatch.h>` | GCD 信号量 API | macOS/iOS |
| `src/base/SkLeanWindows.h` | 精简 Windows 头文件 | Windows |
| `<semaphore.h>` | POSIX 信号量 API | Linux/Unix |
| `<errno.h>` | 错误码（EINTR） | POSIX |
| `SkFeatures.h` | 平台检测宏 | 所有平台 |

### 被依赖的模块

`SkSemaphore` 作为底层同步原语，被以下模块使用：

| 使用场景 | 说明 |
|---------|------|
| `SkSharedMutex` | 实现读写锁的等待队列 |
| `SkTaskGroup` | 线程池中的任务计数和等待 |
| `SkExecutor` | 并行任务调度器 |
| 资源池 | 限制并发访问资源的数量 |

## 设计模式与设计决策

### 设计模式

1. **延迟初始化模式**:
   - 操作系统信号量仅在首次竞争时创建
   - 使用 `SkOnce` 确保线程安全的单次初始化

2. **适配器模式**:
   - `OSSemaphore` 封装不同平台的信号量 API
   - 提供统一的 `signal/wait` 接口

3. **两阶段构造**:
   - `SkSemaphore` 构造函数轻量（可能只初始化原子计数）
   - `OSSemaphore` 在需要时才构造

### 设计决策

1. **混合实现策略**:
   - 快速路径使用原子操作
   - 慢速路径使用操作系统信号量
   - 优点: 无竞争时零系统调用开销

2. **延迟创建 OS 信号量**:
   - 若从未竞争，`OSSemaphore` 永不分配
   - 优点: 节省内存和初始化开销
   - 代价: 首次竞争时需额外分配

3. **平台相关条件编译**:
   - 使用 `#if defined(...)` 选择实现
   - 优先级: macOS/iOS → Windows → POSIX
   - 原因: macOS 必须使用 GCD（POSIX 信号量在 Mach 上不可靠）

4. **初始计数为 0**:
   - 所有平台的 `OSSemaphore` 都使用初始计数 0
   - 原因: 配合快速路径的原子计数器

5. **循环处理 EINTR**:
   - POSIX 实现中 `wait()` 循环重试
   - 原因: 信号可能中断 `sem_wait`，需要区分真正的错误

6. **批量 signal 的差异**:
   - Windows: `ReleaseSemaphore(n)` 原生支持批量
   - macOS/POSIX: 循环调用 `signal()` 模拟批量
   - 原因: API 差异，Windows 提供更高效的批量接口

7. **try_wait 使用 weak CAS**:
   - `compare_exchange_weak` 可能虚假失败
   - 优点: 比 `strong` 更快（在某些架构上）
   - 调用者负责循环重试（若需要）

## 性能考量

### 性能特征

**无竞争情况**:
- `signal`: 约 2-5 纳秒（原子操作）
- `wait`: 约 2-5 纳秒（原子操作）
- `try_wait`: 约 5-10 纳秒（CAS 操作）

**首次竞争**:
- 额外开销: 创建 OS 信号量（约 1-10 微秒）
- 仅发生一次

**竞争情况**:
- `signal`: 约 100-500 纳秒（系统调用）
- `wait`: 阻塞直到被唤醒（无 CPU 占用）

### 平台性能差异

| 平台 | signal 延迟 | wait 延迟 | 特点 |
|------|------------|----------|------|
| macOS/iOS | 中等 | 中等 | GCD 优化良好 |
| Windows | 快 | 快 | 内核对象开销低 |
| Linux | 快 | 快 | futex 底层实现 |

### 优化策略

1. **延迟初始化**: 避免不必要的 OS 资源分配
2. **原子快速路径**: 无竞争时避免系统调用
3. **批量 signal**: Windows 平台利用原生批量 API

### 使用建议

1. **适用场景**:
   - 生产者-消费者队列
   - 线程池任务计数
   - 资源限制（如连接池）
   - 实现更复杂的同步原语（如读写锁）

2. **不适用场景**:
   - 简单的互斥（用 `SkMutex`）
   - 计数器更新（用原子变量）
   - 短临界区（用 `SkSpinlock`）

3. **最佳实践**:
   - 配合条件使用 `try_wait` 实现非阻塞逻辑
   - 批量 `signal(n)` 比循环 `signal()` 更高效
   - 初始计数设为资源的可用数量

4. **陷阱避免**:
   - 确保每个 `signal` 对应一个 `wait`（平衡计数）
   - 避免信号量计数溢出（虽然上限很高）
   - 不要依赖 `try_wait` 的公平性

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkSemaphore.h` | 信号量公共接口定义 |
| `src/base/SkSharedMutex.cpp` | 使用 SkSemaphore 实现读写锁 |
| `include/private/base/SkOnce.h` | 单次初始化工具 |
| `src/base/SkLeanWindows.h` | 精简的 Windows 头文件 |
| `include/private/base/SkFeatures.h` | 平台检测宏 |
| `src/core/SkTaskGroup.cpp` | 线程池使用信号量 |
