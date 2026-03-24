# SkMutex 互斥锁模块

> 源文件: `include/private/base/SkMutex.h`

## 概述
SkMutex 是 Skia 的自定义互斥锁实现,提供线程安全的同步原语。该模块避免依赖 C++ 标准库的 `std::mutex`,以满足某些受限环境的需求,同时提供 RAII 风格的自动锁管理。

## 架构位置
位于 Skia 基础设施层 (private/base),为多线程环境下的资源访问同步提供底层支持。被资源缓存、线程池、图像解码器等模块使用。

## 主要类与结构体

### SkMutex

**继承关系**: 无基类,独立实现

**职责**: 提供互斥锁功能,保护共享资源免受并发访问

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fSemaphore` | SkSemaphore | 底层同步原语,初始计数为 1 |
| `fOwner` | SkThreadID | (Debug 模式) 当前持有锁的线程 ID |

**线程注解**:
- 类声明使用 `SK_CAPABILITY("mutex")` 标记为互斥能力
- 支持 Clang 线程安全分析工具

### SkAutoMutexExclusive

**继承关系**: 无基类

**职责**: RAII 风格的互斥锁管理器,构造时获取锁,析构时释放锁

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fMutex` | SkMutex& | 被管理的互斥锁的引用 |

**设计特点**:
- 不可拷贝 (deleted copy constructor/assignment)
- 不可移动 (deleted move constructor/assignment)
- 使用 `SK_SCOPED_CAPABILITY` 标注作用域能力

## 公共 API 函数

### SkMutex 方法

#### `acquire`
```cpp
void acquire() SK_ACQUIRE()
```
- **功能**: 获取互斥锁,如果锁已被占用则阻塞等待
- **实现**: 调用 `fSemaphore.wait()` 获取信号量
- **Debug 行为**: 记录当前线程 ID 到 `fOwner`
- **线程注解**: `SK_ACQUIRE()` 标记获取锁能力

#### `release`
```cpp
void release() SK_RELEASE_CAPABILITY()
```
- **功能**: 释放互斥锁,唤醒一个等待线程
- **前置条件**: 必须由持有锁的线程调用
- **实现**:
  1. 调用 `assertHeld()` 验证当前线程持有锁
  2. 重置 `fOwner` 为 `kIllegalThreadID`
  3. 调用 `fSemaphore.signal()` 释放信号量

#### `assertHeld`
```cpp
void assertHeld() SK_ASSERT_CAPABILITY(this)
```
- **功能**: 断言当前线程持有此锁
- **用途**: 在需要持有锁的函数中进行前置条件检查
- **实现**: 检查 `fOwner == SkGetThreadID()`
- **Release 模式**: 宏展开为空操作

#### `assertNotHeld`
```cpp
void assertNotHeld()
```
- **功能**: 断言当前没有线程持有此锁
- **用途**: 在析构函数中验证锁已正确释放
- **实现**: 检查 `fOwner == kIllegalThreadID`

### SkAutoMutexExclusive 方法

#### 构造函数
```cpp
SkAutoMutexExclusive(SkMutex& mutex) SK_ACQUIRE(mutex)
```
- **功能**: 构造时自动获取互斥锁
- **参数**: `mutex` - 要管理的互斥锁引用
- **实现**: 调用 `mutex.acquire()`

#### 析构函数
```cpp
~SkAutoMutexExclusive() SK_RELEASE_CAPABILITY()
```
- **功能**: 析构时自动释放互斥锁
- **实现**: 调用 `fMutex.release()`
- **保证**: 异常安全,即使发生异常也会释放锁

## 内部实现细节

### 基于信号量的实现
SkMutex 通过 `SkSemaphore` 实现:
```cpp
SkSemaphore fSemaphore{1};  // 初始计数为 1
```
- 信号量初始值为 1,表示锁未被占用
- `wait()` 减少计数 (获取锁)
- `signal()` 增加计数 (释放锁)

### Debug 模式的所有权追踪
```cpp
SkDEBUGCODE(SkThreadID fOwner{kIllegalThreadID};)
```
- 仅在 Debug 构建中编译
- 用于检测错误使用 (如重复获取、跨线程释放)
- `kIllegalThreadID` 表示无线程持有锁

### 线程注解系统
使用 Clang 的线程安全分析属性:
- `SK_CAPABILITY("mutex")`: 声明类型为互斥能力
- `SK_ACQUIRE()`: 标记获取锁的函数
- `SK_RELEASE_CAPABILITY()`: 标记释放锁的函数
- `SK_ASSERT_CAPABILITY(this)`: 断言持有锁
- `SK_SCOPED_CAPABILITY`: 标记 RAII 锁管理器

编译器可静态分析锁的使用,检测:
- 忘记释放锁
- 未持有锁就访问受保护数据
- 死锁风险

### 不可拷贝/移动语义
```cpp
SkAutoMutexExclusive(const SkAutoMutexExclusive&) = delete;
SkAutoMutexExclusive(SkAutoMutexExclusive&&) = delete;
SkAutoMutexExclusive& operator=(const SkAutoMutexExclusive&) = delete;
SkAutoMutexExclusive& operator=(SkAutoMutexExclusive&&) = delete;
```
防止意外复制导致的双重释放或所有权混乱。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| `SkAssert.h` | 提供 SkASSERT 断言宏 |
| `SkDebug.h` | Debug 模式支持 |
| `SkSemaphore.h` | 底层信号量实现 |
| `SkThreadAnnotations.h` | 线程安全分析注解 |
| `SkThreadID.h` | 线程 ID 获取 |

### 被依赖的模块
- `SkResourceCache` - 缓存访问同步
- `SkTaskGroup` - 任务队列保护
- `SkFontMgr` - 字体资源管理
- 图像解码器 - 并发解码保护

## 设计模式与设计决策

### 避免标准库依赖
**决策**: 实现自定义 mutex 而非使用 `std::mutex`
**原因**:
- Google 内部代码规范限制 (go/cstyle#Disallowed_Stdlib)
- 某些嵌入式环境不支持完整 C++ 标准库
- 更精确控制行为和性能特征

### RAII 模式
`SkAutoMutexExclusive` 采用 RAII (Resource Acquisition Is Initialization):
- 构造即获取资源
- 析构自动释放资源
- 异常安全保证

### 编译期 Debug 检查
使用 `SkDEBUGCODE` 宏使 Debug 检查在 Release 构建中零开销:
```cpp
SkDEBUGCODE(fOwner = SkGetThreadID();)
```
Release 构建中此行完全消失。

### 静态线程安全分析
通过 Clang 属性在编译期检测线程安全问题,避免运行时错误。

## 性能考量

### 轻量级实现
基于 `SkSemaphore`,通常映射到操作系统原生同步原语:
- POSIX: `sem_t`
- Windows: `HANDLE` (Semaphore 对象)
- 最小化开销

### Debug 开销
所有权追踪仅在 Debug 构建中存在,Release 构建无额外成本。

### 内联优化
小函数设计为可内联,减少函数调用开销。

### 无条件变量
设计为简单的互斥锁,不支持条件变量。如需条件等待,需组合其他原语。

## 使用示例

### 基本互斥锁使用
```cpp
SkMutex gCacheMutex;
std::vector<CacheEntry> gCache;

void AddToCache(const CacheEntry& entry) {
    SkAutoMutexExclusive lock(gCacheMutex);
    gCache.push_back(entry);
    // 锁在函数结束时自动释放
}
```

### 手动锁管理 (不推荐)
```cpp
SkMutex mutex;
mutex.acquire();
try {
    // 临界区代码
    ProcessData();
} catch (...) {
    mutex.release();
    throw;
}
mutex.release();
```

### 条件性锁定
```cpp
void ConditionalUpdate(bool needLock) {
    std::unique_ptr<SkAutoMutexExclusive> lock;
    if (needLock) {
        lock = std::make_unique<SkAutoMutexExclusive>(gMutex);
    }
    // 执行操作
}
```

### 断言锁持有
```cpp
class ThreadSafeCache {
    SkMutex fMutex;

    void InternalAdd(Entry e) {
        fMutex.assertHeld();  // 确保调用者持有锁
        // ...
    }

public:
    void Add(Entry e) {
        SkAutoMutexExclusive lock(fMutex);
        InternalAdd(e);
    }
};
```

## 局限性与注意事项

### 不支持递归锁
SkMutex 不是递归互斥锁,同一线程再次 `acquire()` 会导致死锁。

### 无超时机制
不支持 `try_lock` 或带超时的 `acquire`,只能无限等待。

### 无优先级继承
简单实现,不解决优先级反转问题。

### 跨平台行为差异
底层 `SkSemaphore` 的实现可能因平台而异,但接口保持一致。

## 相关文件
| 文件 | 关系 |
|------|------|
| `SkSemaphore.h` | 提供底层信号量实现 |
| `SkThreadID.h` | 线程 ID 获取 |
| `SkThreadAnnotations.h` | 线程安全分析宏 |
| `SkSpinlock.h` | 轻量级自旋锁替代方案 |
| `SkOnce.h` | 单次初始化原语 |

## 历史与演进
- 2015 年引入,取代之前的互斥锁实现
- 基于信号量提供跨平台统一接口
- 集成 Clang 线程安全分析支持
