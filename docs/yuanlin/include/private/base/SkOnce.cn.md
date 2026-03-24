# SkOnce 单次初始化模块

> 源文件: `include/private/base/SkOnce.h`

## 概述
SkOnce 是 Skia 的单次初始化同步原语,提供类似 C++11 `std::call_once` 的功能,确保某个函数在多线程环境下仅被执行一次。该模块使用原子操作和自旋锁实现,无需依赖标准库。

## 架构位置
位于 Skia 基础设施层 (private/base),为全局资源初始化、单例模式、延迟初始化等场景提供线程安全保证。

## 主要类与结构体

### SkOnce

**继承关系**: 无基类,独立实现

**职责**: 确保初始化函数仅被调用一次,即使多个线程同时尝试初始化

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fState` | std::atomic<uint8_t> | 初始化状态,初始值为 NotStarted |

**内部状态枚举**:
```cpp
enum State : uint8_t {
    NotStarted,  // 尚未开始
    Claimed,     // 已被某线程认领
    Done         // 已完成
};
```

## 公共 API 函数

### `operator()`
```cpp
template <typename Fn, typename... Args>
void operator()(Fn&& fn, Args&&... args)
```
- **功能**: 执行单次初始化,保证 `fn` 仅被调用一次
- **参数**:
  - `fn`: 可调用对象 (函数、lambda、函数对象等)
  - `args`: 转发给 `fn` 的参数
- **线程安全**: 多线程同时调用时,仅一个线程执行 `fn`,其他线程等待
- **异常安全**: 如果 `fn` 抛出异常,状态不会变为 Done,下次调用会重试
- **返回**: 无返回值

## 内部实现细节

### 三阶段状态机

#### 阶段 1: 快速路径 - 已完成检查
```cpp
auto state = fState.load(std::memory_order_acquire);
if (state == Done) {
    return;  // 最常见情况,直接返回
}
```
- **内存序**: `memory_order_acquire` 确保看到初始化的结果
- **无锁**: 已初始化场景下无同步开销

#### 阶段 2: 认领初始化权
```cpp
if (state == NotStarted && fState.compare_exchange_strong(
        state, Claimed,
        std::memory_order_relaxed,
        std::memory_order_relaxed)) {
    // 成功认领,执行初始化
    fn(std::forward<Args>(args)...);
    return fState.store(Done, std::memory_order_release);
}
```
- **CAS 操作**: 原子比较并交换,确保只有一个线程成功
- **失败内存序**: `relaxed` 因为失败时会进入自旋等待
- **完成标记**: `memory_order_release` 发布初始化结果

#### 阶段 3: 自旋等待
```cpp
SK_POTENTIALLY_BLOCKING_REGION_BEGIN;
while (fState.load(std::memory_order_acquire) != Done) { /*spin*/ }
SK_POTENTIALLY_BLOCKING_REGION_END;
```
- **自旋锁**: 持续检查状态直到变为 Done
- **内存序**: `memory_order_acquire` 同步初始化结果
- **线程注解**: 标记潜在阻塞区域,供性能分析工具使用

### 完美转发
```cpp
fn(std::forward<Args>(args)...)
```
使用 C++11 完美转发保留参数的值类别 (左值/右值)。

### 异常安全性
如果 `fn` 抛出异常:
- `fState` 保持为 `Claimed`
- 下次调用会遇到 `state == Claimed`,进入自旋等待
- **结果**: 异常导致永久死锁
- **建议**: 初始化函数应使用 `noexcept` 或确保不抛异常

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkThreadAnnotations.h` | 提供 SK_POTENTIALLY_BLOCKING_REGION 宏 |
| `<atomic>` | std::atomic 原子操作 |
| `<cstdint>` | uint8_t 类型 |
| `<utility>` | std::forward 转发 |

### 被依赖的模块
- 全局单例初始化
- 延迟加载的配置数据
- 线程安全的缓存初始化
- 字体管理器初始化

## 设计模式与设计决策

### 双重检查锁定 (Double-Checked Locking) 模式
```cpp
// 第一次检查 (无锁)
if (state == Done) return;

// 获取锁
if (CAS(NotStarted -> Claimed)) {
    initialize();
}

// 第二次检查 (有锁)
while (state != Done) spin;
```
经典并发模式,优化已初始化场景的性能。

### 自旋锁而非互斥锁
**决策**: 使用自旋等待而非 `SkMutex`
**原因**:
- 初始化通常很快完成
- 避免系统调用开销
- 简化实现,无需条件变量

**权衡**:
- 长时间初始化会浪费 CPU
- 适合短暂初始化场景

### 三状态而非布尔标志
```cpp
enum State { NotStarted, Claimed, Done };
```
**优势**:
- 区分"正在初始化"和"未初始化"
- 其他线程可知道需要等待,而非尝试重新初始化

### constexpr 构造函数
```cpp
constexpr SkOnce() = default;
```
允许 `SkOnce` 作为全局变量使用,无运行时初始化开销。

## 性能考量

### 已初始化场景的零开销
```cpp
if (state == Done) return;  // 单次原子加载
```
- 最常见路径仅一次原子读取
- `memory_order_acquire` 在大多数架构上无额外开销 (x86)
- 分支预测友好 (几乎总是 true)

### 自旋锁的 CPU 使用
自旋等待会占用 CPU 时间片:
- **优点**: 无上下文切换
- **缺点**: 长时间初始化浪费 CPU
- **适用**: 初始化时间 < 100 微秒

### 内存序优化
- 失败的 CAS 使用 `memory_order_relaxed`
- 减少内存屏障开销

### 无虚函数调用
模板实现避免虚函数开销,支持内联优化。

## 使用示例

### 全局资源初始化
```cpp
SkOnce gInitOnce;
std::unique_ptr<GlobalResource> gResource;

GlobalResource* GetResource() {
    gInitOnce([]{
        gResource = std::make_unique<GlobalResource>();
    });
    return gResource.get();
}
```

### 延迟初始化配置
```cpp
class Config {
    SkOnce fLoadOnce;
    Data fData;

public:
    const Data& Get() {
        fLoadOnce([this]{ fData = LoadFromFile(); });
        return fData;
    }
};
```

### 带参数的初始化
```cpp
SkOnce gFontInit;

void InitializeFonts(const char* fontPath, int fontSize) {
    gFontInit([](const char* path, int size) {
        LoadFonts(path, size);
    }, fontPath, fontSize);
}
```

### 成员变量使用
```cpp
class ThreadSafeCache {
    SkOnce fInitOnce;
    std::vector<Entry> fEntries;

public:
    void EnsureInitialized() {
        fInitOnce([this]{
            fEntries = BuildCache();
        });
    }
};
```

### Lambda 捕获
```cpp
SkOnce once;
int value = 42;
once([value]{
    ProcessValue(value);
});
```

## 局限性与注意事项

### 异常不安全
如果初始化函数抛出异常,后续所有调用都会死锁。解决方案:
```cpp
gOnce([]() noexcept {
    try {
        InitializeResource();
    } catch (...) {
        // 使用默认值或记录错误
    }
});
```

### 不支持重新初始化
一旦标记为 Done,无法重置。如需重新初始化,需创建新的 `SkOnce` 对象。

### 自旋锁开销
长时间初始化会浪费 CPU:
```cpp
// 不推荐
gOnce([]{
    SlowNetworkRequest();  // 可能耗时秒级
});

// 推荐
gOnce([]{
    QuickInitialization();  // 微秒级
});
```

### 全局对象的初始化顺序
作为全局变量时,依赖 C++ 的静态初始化:
```cpp
// 安全: constexpr 构造
SkOnce gOnce;

// 危险: 依赖其他全局变量
SkOnce gOnce = GetOnce();  // 初始化顺序未定义
```

## 与标准库的比较

### vs std::call_once
| 特性 | SkOnce | std::call_once |
|------|--------|----------------|
| 依赖 | 无需标准库 mutex | 需要 `<mutex>` |
| 等待方式 | 自旋锁 | 互斥锁 + 条件变量 |
| 适用场景 | 快速初始化 | 任意时长初始化 |
| CPU 使用 | 等待时占用 CPU | 等待时让出 CPU |
| 异常安全 | 否 | 是 |

### vs pthread_once
| 特性 | SkOnce | pthread_once |
|------|--------|--------------|
| 平台依赖 | 跨平台 C++ | POSIX 系统 |
| 参数传递 | 支持任意参数 | 仅无参函数 |
| 类型安全 | 模板类型安全 | void(*)() |

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkMutex.h` | 另一种同步原语 |
| `SkThreadAnnotations.h` | 提供线程分析注解 |
| `SkSpinlock.h` | 类似的自旋锁实现 |
| `SkLazyPtr.h` | 使用 SkOnce 的延迟初始化指针 |

## 历史与演进
- 2013 年引入,取代之前的平台特定实现
- 提供类似 `std::call_once` 的功能,但不依赖标准库
- 使用 C++11 原子操作保证线程安全
- 支持任意可调用对象和完美转发
