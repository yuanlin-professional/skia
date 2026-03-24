# SkExecutor

> 源文件
> - include/core/SkExecutor.h
> - src/core/SkExecutor.cpp

## 概述

`SkExecutor` 是 Skia 中用于管理异步任务执行的抽象基类,提供了统一的线程池和任务调度接口。它支持多种执行策略,包括 FIFO(先进先出)和 LIFO(后进先出)工作队列,以及多优先级工作列表。`SkExecutor` 允许应用程序将计算密集型任务分发到后台线程,从而提高性能和响应性。

该模块提供了默认的简单执行器(`SkTrivialExecutor`,立即执行)和线程池执行器(`SkThreadPool`,多线程并发执行),以及借用(borrowing)机制,允许调用线程参与任务执行。`SkExecutor` 在 Skia 的图像解码、滤镜处理、光栅化等场景中被广泛使用。

## 架构位置

`SkExecutor` 在 Skia 架构中处于基础设施层,为各种计算密集型模块提供并发支持:

```
应用层
    ↓
Skia 渲染模块
    ├── 图像解码
    ├── 图像滤镜
    ├── 光栅化
    └── 其他计算密集型任务
    ↓
SkExecutor (任务调度抽象)
    ├── SkTrivialExecutor (立即执行)
    └── SkThreadPool (线程池)
    ↓
操作系统线程
```

**使用场景**:
- 并行图像解码
- 并行光栅化多个 tile
- 并行执行图像滤镜
- 后台预处理任务

## 主要类与结构体

### SkExecutor (抽象基类)

**继承关系**
```
SkExecutor (抽象基类)
    ├── SkTrivialExecutor (立即执行实现)
    └── SkThreadPool<WorkList> (线程池实现)
```

**关键虚函数**

| 方法 | 说明 |
|-----|------|
| `add(std::function<void(void)>)` | 添加任务到执行器(已弃用,使用双参数版本) |
| `add(std::function<void(void)>, int workList)` | 添加任务到指定工作列表 |
| `discardAllPendingWork()` | 丢弃所有待执行的任务 |
| `borrow()` | 当前线程借用并执行一个任务 |

### SkTrivialExecutor

**功能**: 立即在调用线程执行任务的执行器

**实现**:
```cpp
class SkTrivialExecutor final : public SkExecutor {
public:
    void add(std::function<void(void)> work, int /* workList */) override {
        work();  // 立即执行
    }
    void add(std::function<void(void)> work) override {
        this->add(std::move(work), 0);
    }
    int discardAllPendingWork() override { return 0; }
};
```

**使用场景**:
- 单线程应用
- 调试和测试
- 不需要并发的简单场景

### SkThreadPool

**模板参数**: `WorkList` - 工作队列类型(`std::deque` 或 `TArray`)

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fThreads` | `TArray<std::thread>` | 工作线程数组 |
| `fNumWorkLists` | `const int` | 工作列表数量(至少为 1) |
| `fWorkLists` | `std::unique_ptr<WorkList[]>` | 工作列表数组 |
| `fWorkLock` | `SkMutex` | 保护工作列表的互斥锁 |
| `fWorkAvailable` | `SkSemaphore` | 通知工作可用的信号量 |
| `fAllowBorrowing` | `const bool` | 是否允许借用机制 |

**工作队列类型**:
- **FIFO**: 使用 `std::deque`,从前端取出任务
- **LIFO**: 使用 `TArray`,从后端取出任务

## 公共 API 函数

### 工厂函数

```cpp
static std::unique_ptr<SkExecutor> MakeFIFOThreadPool(int threads = 0,
                                                      bool allowBorrowing = true);
static std::unique_ptr<SkExecutor> MakeLIFOThreadPool(int threads = 0,
                                                      bool allowBorrowing = true);
```
- **功能**: 创建单工作列表的线程池执行器
- **参数**:
  - `threads`: 线程数量,0 表示使用 CPU 核心数
  - `allowBorrowing`: 是否允许调用线程借用任务
- **返回值**: 执行器的 unique_ptr

```cpp
static std::unique_ptr<SkExecutor> MakeMultiListFIFOThreadPool(int numWorkLists,
                                                               int threads = 0,
                                                               bool allowBorrowing = true);
static std::unique_ptr<SkExecutor> MakeMultiListLIFOThreadPool(int numWorkLists,
                                                               int threads = 0,
                                                               bool allowBorrowing = true);
```
- **功能**: 创建多工作列表的线程池执行器
- **参数**:
  - `numWorkLists`: 工作列表数量,列表 0 优先级最高
  - `threads`: 线程数量
  - `allowBorrowing`: 是否允许借用
- **用途**: 实现任务优先级调度

### 默认执行器管理

```cpp
static SkExecutor& GetDefault();
static void SetDefault(SkExecutor*);
```
- **GetDefault**: 获取全局默认执行器(未设置时返回 `SkTrivialExecutor`)
- **SetDefault**: 设置全局默认执行器(不转移所有权,非线程安全)
- **注意**: 必须在单线程环境下调用 `SetDefault`

### 任务提交

```cpp
virtual void add(std::function<void(void)> fn, int workList);
virtual void add(std::function<void(void)> fn) = 0;  // 已弃用
```
- **功能**: 添加任务到执行器
- **参数**:
  - `fn`: 任务函数(无参数无返回值)
  - `workList`: 工作列表索引(0 表示最高优先级)
- **行为**: 任务可能立即执行(TrivialExecutor)或稍后执行(ThreadPool)

### 任务管理

```cpp
virtual int discardAllPendingWork();
```
- **功能**: 丢弃所有待执行的任务
- **返回值**: 丢弃的任务数量
- **注意**: 已开始执行的任务不会被中断

### 借用机制

```cpp
virtual void borrow();
```
- **功能**: 当前线程从工作队列中取出并执行一个任务
- **用途**: 避免线程空闲等待,充分利用 CPU
- **条件**: 仅在 `allowBorrowing = true` 且有待执行任务时有效

## 内部实现细节

### CPU 核心数检测

```cpp
#if defined(SK_BUILD_FOR_WIN)
    static int num_cores() {
        SYSTEM_INFO sysinfo;
        GetNativeSystemInfo(&sysinfo);
        return (int)sysinfo.dwNumberOfProcessors;
    }
#else
    #include <unistd.h>
    static int num_cores() {
        return (int)sysconf(_SC_NPROCESSORS_ONLN);
    }
#endif
```
- Windows: 使用 `GetNativeSystemInfo`
- POSIX: 使用 `sysconf(_SC_NPROCESSORS_ONLN)`

### 线程池工作循环

```cpp
static void Loop(void* ctx) {
    auto pool = (SkThreadPool*)ctx;
    do {
        pool->fWorkAvailable.wait();  // 等待任务可用
    } while (pool->do_work());       // 执行任务,返回 false 时退出
}

bool do_work() {
    std::function<void(void)> work;
    bool workAvailable = false;
    {
        SkAutoMutexExclusive lock(fWorkLock);
        // 从高优先级到低优先级查找任务
        for (int i = 0; i < fNumWorkLists; ++i) {
            if (!fWorkLists[i].empty()) {
                workAvailable = true;
                work = pop(&fWorkLists[i]);
                break;
            }
        }
    }

    if (!workAvailable) {
        return true;  // 可能是 discardAllPendingWork 导致的,继续循环
    }

    if (!work) {
        return false;  // nullptr 表示关闭信号
    }

    work();  // 执行任务
    return true;
}
```

**关键点**:
- 使用信号量同步任务可用状态
- 互斥锁保护工作队列的访问
- 按优先级顺序查找任务
- `nullptr` 任务用作关闭信号

### 工作队列策略

**FIFO(先进先出)**:
```cpp
static inline std::function<void(void)> pop(std::deque<std::function<void(void)>>* list) {
    std::function<void(void)> fn = std::move(list->front());
    list->pop_front();
    return fn;
}
```
- 适用于公平调度
- 保持任务提交顺序

**LIFO(后进先出)**:
```cpp
static inline std::function<void(void)> pop(TArray<std::function<void(void)>>* list) {
    std::function<void(void)> fn = std::move(list->back());
    list->pop_back();
    return fn;
}
```
- 适用于栈式任务分解
- 提高缓存局部性

### 线程池关闭

```cpp
~SkThreadPool() override {
    // 1. 为每个工作线程添加关闭信号(nullptr 任务)
    for (int i = 0; i < fThreads.size(); i++) {
        this->add(nullptr, 0);  // 添加到最高优先级列表
    }
    // 2. 等待所有线程退出
    for (int i = 0; i < fThreads.size(); i++) {
        fThreads[i].join();
    }
}
```

**优雅关闭步骤**:
1. 向最高优先级列表添加 N 个 `nullptr` 任务(N = 线程数)
2. 工作线程检测到 `nullptr` 后退出循环
3. 主线程等待所有工作线程 `join`

### 借用机制实现

```cpp
void borrow() override {
    if (fAllowBorrowing && fWorkAvailable.try_wait()) {
        SkAssertResult(this->do_work());
    }
}
```
- 使用 `try_wait` 非阻塞检查是否有任务
- 成功获取信号量后执行一个任务
- 不允许借用时直接返回

### 多优先级调度

工作线程按优先级顺序查找任务:
```cpp
for (int i = 0; i < fNumWorkLists; ++i) {
    if (!fWorkLists[i].empty()) {
        work = pop(&fWorkLists[i]);
        break;  // 从最低索引(最高优先级)开始
    }
}
```

**添加任务时的优先级钳制**:
```cpp
void add(std::function<void(void)> work, int workList) override {
    workList = SkTPin(workList, 0, fNumWorkLists-1);  // 钳制到有效范围
    // ...
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkMutex` | 保护共享数据结构 |
| `SkSemaphore` | 线程间同步信号 |
| `SkTArray` | 动态数组容器 |
| `SkNoDestructor` | 静态对象的延迟初始化和生命周期管理 |
| `std::thread` | C++ 标准线程库 |
| `std::function` | 函数对象封装 |
| `std::deque` | FIFO 工作队列容器 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| 图像解码器 | 使用 `SkExecutor` 并行解码图像 |
| 图像滤镜 | 使用 `SkExecutor` 并行处理滤镜 |
| 光栅化器 | 使用 `SkExecutor` 并行光栅化 tile |
| Ganesh/Graphite | 使用 `SkExecutor` 进行 GPU 辅助任务 |

## 设计模式与设计决策

### 策略模式

通过抽象基类 `SkExecutor` 定义接口,不同的实现提供不同的执行策略:

```cpp
SkExecutor* executor = SkExecutor::MakeFIFOThreadPool(4).release();
executor->add([](){ /* task */ });  // 多线程执行

SkExecutor* trivial = new SkTrivialExecutor();
trivial->add([](){ /* task */ });   // 立即执行
```

### 单例模式(默认执行器)

```cpp
static SkExecutor* gDefaultExecutor = nullptr;

SkExecutor& SkExecutor::GetDefault() {
    if (gDefaultExecutor) {
        return *gDefaultExecutor;
    }
    return trivial_executor();  // 静态局部变量
}

static SkExecutor& trivial_executor() {
    static SkNoDestructor<SkTrivialExecutor> executor;
    return *executor;
}
```

**设计理由**:
- 提供全局访问点
- 支持用户自定义默认执行器
- 使用 `SkNoDestructor` 避免静态析构顺序问题

### 模板策略

使用模板参数选择工作队列类型:
```cpp
template <typename WorkList>
class SkThreadPool final : public SkExecutor { ... };

// FIFO 实例化
using WorkList = std::deque<std::function<void(void)>>;
return std::make_unique<SkThreadPool<WorkList>>(...);

// LIFO 实例化
using WorkList = TArray<std::function<void(void)>>;
return std::make_unique<SkThreadPool<WorkList>>(...);
```

**优势**:
- 零运行时开销的策略选择
- 代码复用(只有 pop 函数不同)

### 借用机制设计

允许调用线程参与任务执行:
```cpp
// 提交任务后,等待结果的线程可以帮忙执行任务
executor->add(task1);
executor->add(task2);
while (!allTasksComplete) {
    executor->borrow();  // 执行一个任务,避免空闲等待
}
```

**优势**:
- 充分利用 CPU
- 减少线程上下文切换
- 避免死锁(如果任务之间有依赖)

### 设计决策

1. **CPU 核心数默认**: 线程数默认等于 CPU 核心数
   - **原因**: 平衡并行度和线程开销
   - **权衡**: 用户可根据任务特性调整

2. **信号量 + 互斥锁**: 使用信号量通知,互斥锁保护队列
   - **原因**: 避免忙等待,减少 CPU 消耗
   - **性能**: 信号量的系统调用开销小于自旋锁的 CPU 浪费

3. **多优先级支持**: 支持多个工作列表
   - **用途**: 高优先级任务(如用户交互)先执行
   - **实现**: 简单的线性查找(工作列表数量通常很少)

4. **关闭信号**: 使用 `nullptr` 作为关闭信号
   - **原因**: 简单且不需要额外的同步机制
   - **安全性**: 每个线程都会收到一个关闭信号

5. **非拥有默认执行器**: `SetDefault` 不转移所有权
   - **原因**: 避免生命周期管理复杂性
   - **要求**: 调用者负责保证执行器的生命周期

## 性能考量

### 线程开销

1. **默认线程数**: 等于 CPU 核心数
   - 计算密集型任务: 理想配置
   - IO 密集型任务: 可能需要更多线程

2. **线程创建**: 在构造函数中一次性创建
   - 避免动态创建/销毁开销
   - 线程池生命周期内保持活跃

### 同步开销

1. **信号量**: 每个任务一次 `signal` 调用
   - 系统调用开销
   - 相比自旋锁更节能

2. **互斥锁**: 仅保护关键区(访问工作队列)
   - 最小化锁持有时间
   - 避免在锁内执行任务

3. **无锁设计**: 未使用无锁队列
   - **原因**: 实现复杂,收益有限
   - **权衡**: 互斥锁开销可接受

### 任务粒度

**建议**:
- 任务执行时间 >> 调度开销(通常 > 100μs)
- 过小的任务导致调度开销占比过高
- 过大的任务降低并行度

### FIFO vs LIFO 选择

**FIFO 优势**:
- 公平调度,任务按提交顺序执行
- 适合独立任务

**LIFO 优势**:
- 提高缓存局部性(最近的任务数据可能在缓存中)
- 适合递归分解的任务

### 借用机制的权衡

**启用借用**:
- 优势: 充分利用调用线程的 CPU 时间
- 劣势: 可能延迟调用线程的其他工作

**禁用借用**:
- 优势: 调用线程可以立即返回做其他工作
- 劣势: 可能浪费 CPU 周期在等待上

### 内存开销

```cpp
sizeof(SkThreadPool) ≈
    sizeof(TArray<std::thread>)          // N * sizeof(std::thread)
    + sizeof(std::unique_ptr<WorkList[]>) // 指针
    + M * sizeof(WorkList)                // M 个工作列表
    + sizeof(SkMutex)                    // ~64 bytes
    + sizeof(SkSemaphore)                // ~128 bytes
```

**优化**:
- 工作列表按需增长,初始为空
- 线程数量固定,不动态增长

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/base/SkMutex.h` | 依赖 | 互斥锁实现 |
| `include/private/base/SkSemaphore.h` | 依赖 | 信号量实现 |
| `include/private/base/SkTArray.h` | 依赖 | 动态数组容器 |
| `src/base/SkNoDestructor.h` | 依赖 | 静态对象管理 |
| `src/codec/*` | 使用者 | 图像解码器 |
| `src/effects/*` | 使用者 | 图像滤镜 |
| `src/core/SkRasterPipeline*.cpp` | 使用者 | 光栅管线 |
