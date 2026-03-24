# SkThreadID

> 源文件: `include/private/base/SkThreadID.h`

## 概述

SkThreadID 提供了跨平台的线程标识符类型定义和获取功能。它使用 int64_t 作为统一的线程 ID 类型，并提供 SkGetThreadID() 函数在运行时获取当前线程的唯一标识符，是 Skia 多线程代码中用于线程识别和调试的基础设施。

## 架构位置

本模块位于 Skia 的私有基础设施层，属于平台抽象层。它为 Skia 的所有需要线程识别的代码（如锁的持有者检查、线程本地存储等）提供统一的接口。

## 主要定义

### SkThreadID 类型

```cpp
typedef int64_t SkThreadID;
```

- **功能**: 定义线程标识符类型为 64 位有符号整数
- **选择原因**:
  - 64 位足以容纳所有平台的线程 ID
  - 有符号类型允许使用 -1 等特殊值
  - 跨平台一致性

### SkGetThreadID() 函数

```cpp
SkDEBUGCODE(SK_SPI) SkThreadID SkGetThreadID();
```

- **功能**: 获取当前线程的唯一标识符
- **返回值**: 当前线程的 SkThreadID
- **属性**: SK_SPI（Skia Private Interface）- 标记为私有接口
- **调试特性**: `SkDEBUGCODE()` 宏包裹，表明此函数主要用于调试
- **注释说明**: SkMutex.h 在调试代码中使用此函数

### kIllegalThreadID 常量

```cpp
const SkThreadID kIllegalThreadID = 0;
```

- **功能**: 定义非法或未初始化的线程 ID 值
- **用途**:
  - 表示"无线程"状态
  - 作为哨兵值检测未初始化的线程 ID
  - 在断言中验证线程 ID 的有效性

## 内部实现细节

### 平台实现

虽然头文件未包含实现，但 SkGetThreadID() 的实现在不同平台上有所不同：

**POSIX 系统（Linux、macOS、iOS 等）**：
```cpp
SkThreadID SkGetThreadID() {
    return (int64_t)pthread_self();
}
```

**Windows**：
```cpp
SkThreadID SkGetThreadID() {
    return (int64_t)GetCurrentThreadId();
}
```

### 调试专用

`SkDEBUGCODE()` 宏的使用暗示：
- 发布版本可能不包含此函数
- 或者函数存在但不被调用
- 主要用于调试断言和日志

### 唯一性保证

SkGetThreadID() 保证：
- 同一时刻，不同线程返回不同的 ID
- 同一线程多次调用返回相同的 ID
- 线程结束后，其 ID 可能被重用（平台相关）

## 典型应用场景

### 锁持有者检查

```cpp
class SkMutex {
    SkThreadID fOwner;
public:
    void lock() {
        // ...
        SkDEBUGCODE(fOwner = SkGetThreadID();)
    }

    void assertHeld() const {
        SkASSERT(fOwner == SkGetThreadID());
    }
};
```

### 线程本地存储验证

```cpp
class ThreadLocalCache {
    SkThreadID fThreadID;
public:
    void* get() {
        SkASSERT(fThreadID == SkGetThreadID());
        return fData;
    }
};
```

### 死锁检测

```cpp
void checkForDeadlock(SkThreadID waiting, SkThreadID holding) {
    if (waiting == holding) {
        SkASSERT(!"Same thread trying to lock twice");
    }
}
```

### 调试日志

```cpp
void logOperation(const char* op) {
    SkDebugf("[Thread %lld] %s\n", SkGetThreadID(), op);
}
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkAPI.h | SK_SPI 宏定义 |
| SkDebug.h | SkDEBUGCODE 宏定义 |
| &lt;cstdint&gt; | int64_t 类型定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkMutex.h | 锁持有者检查（调试） |
| SkSpinlock.h | 自旋锁调试 |
| SkOnce.h | 一次性初始化调试 |
| SkThreadLocalStorage.h | 线程本地存储验证 |

## 设计模式与设计决策

### 类型别名而非类

使用 typedef 定义 SkThreadID，而非定义一个类，这是因为：
- 线程 ID 是简单的数值
- 无需封装额外行为
- 便于直接比较和赋值
- 减少开销

### 调试专用设计

通过 `SkDEBUGCODE()` 包裹，确保：
- 发布版本不承担线程 ID 查询的开销
- 调试版本可以进行详细的线程安全检查
- 保持 API 简洁

### 统一类型选择

使用 int64_t 而非平台相关类型（如 pthread_t）：
- 跨平台一致性
- 易于序列化和打印
- 支持比较操作

### 哨兵值约定

定义 kIllegalThreadID = 0：
- 与大多数平台的线程 ID 范围不冲突
- 便于初始化检查
- 符合"零值无效"的常见约定

## 性能考量

### 轻量级类型

SkThreadID 只是一个 int64_t，占用 8 字节，传递和存储都非常高效。

### 系统调用开销

SkGetThreadID() 通常涉及系统调用或 TLS 访问：
- POSIX: pthread_self() 通常很快（可能只是读取 TLS）
- Windows: GetCurrentThreadId() 是快速内联函数
- 但仍比普通变量访问慢

### 调试模式限制

通过限制在调试模式，避免了发布版本的性能影响。

### 缓存策略

如果需要频繁访问当前线程 ID，可以缓存：

```cpp
thread_local SkThreadID gCachedThreadID = 0;

SkThreadID GetCachedThreadID() {
    if (gCachedThreadID == kIllegalThreadID) {
        gCachedThreadID = SkGetThreadID();
    }
    return gCachedThreadID;
}
```

## 平台相关说明

### POSIX 系统

- 使用 pthread_self() 获取线程 ID
- 返回 pthread_t 类型，可能是指针或整数
- 需要转换为 int64_t

### Windows

- 使用 GetCurrentThreadId() 获取线程 ID
- 返回 DWORD (uint32_t)
- 直接适合 int64_t

### 线程 ID 重用

- 线程结束后，其 ID 可能被新线程重用
- 不应长期存储线程 ID 并假设其指向原线程
- 仅在线程生命周期内或持有线程引用时使用

### 跨进程

- 线程 ID 仅在单个进程内唯一
- 不同进程中的线程可能有相同的 ID 值

## 使用注意事项

### 仅用于调试

由于 `SkDEBUGCODE()` 包裹，不应在发布代码逻辑中依赖 SkGetThreadID()。

### 不可序列化

线程 ID 仅在当前进程的当前运行时有意义，不应序列化到文件或网络。

### 不可跨线程比较生命周期

不能假设 ID 较小的线程先创建或先结束。

### 比较操作

仅 `==` 和 `!=` 有意义，`<` 或 `>` 比较无实际意义。

## 使用示例

### 简单断言

```cpp
class ObjectWithAffinity {
    SkThreadID fCreatorThread;
public:
    ObjectWithAffinity() : fCreatorThread(SkGetThreadID()) {}

    void useObject() {
        SkASSERT(fCreatorThread == SkGetThreadID());
        // ...
    }
};
```

### 锁调试

```cpp
#ifdef SK_DEBUG
void SkMutex::assertHeld() const {
    SkASSERT(fOwner != kIllegalThreadID);
    SkASSERT(fOwner == SkGetThreadID());
}
#endif
```

### 日志输出

```cpp
void SkDebugTrace(const char* message) {
#ifdef SK_DEBUG
    fprintf(stderr, "[TID %lld] %s\n", SkGetThreadID(), message);
#endif
}
```

## 替代方案

### std::this_thread::get_id()

C++11 提供了标准的线程 ID 获取：

```cpp
std::this_thread::get_id()
```

但 SkThreadID 仍然有价值：
- 返回简单的整数类型，易于打印和比较
- 在 Skia 的旧代码中广泛使用
- 提供统一的平台抽象

### thread_local 变量

对于线程亲和性检查，有时可以用 thread_local 变量替代：

```cpp
thread_local bool gInitializedOnThisThread = false;
```

但这不能提供线程的唯一标识符。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkAPI.h` | SK_SPI 宏定义 |
| `include/private/base/SkDebug.h` | SkDEBUGCODE 宏 |
| `include/private/base/SkMutex.h` | 使用 SkThreadID 进行锁调试 |
| `include/private/base/SkSpinlock.h` | 自旋锁调试 |
| `src/core/SkThreadID.cpp` | 平台相关实现 |
