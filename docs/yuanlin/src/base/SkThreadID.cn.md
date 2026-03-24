# SkThreadID

> 源文件: `src/base/SkThreadID.cpp`

## 概述

`SkThreadID.cpp` 实现了 Skia 图形库中获取当前线程标识符的跨平台函数 `SkGetThreadID()`。该文件的实现极为简洁，仅有一个函数，但它在 Skia 的线程安全基础设施中扮演着关键角色，主要用于调试模式下的互斥锁所有权验证。

线程 ID 是一个 `int64_t` 类型的值（类型别名为 `SkThreadID`），在 Windows 平台上通过 Win32 API `GetCurrentThreadId()` 获取，在 POSIX 平台（Linux、macOS、Android 等）上通过 `pthread_self()` 获取。

## 架构位置

该文件位于 `src/base/` 目录下，属于 Skia 的 **基础平台抽象层（Base Layer）**。这是 Skia 中最底层的代码，不依赖于任何 Skia 核心或图形相关的功能。

```
Skia 应用层
  -> 核心层（SkCanvas、SkSurface 等）
       -> 并发原语（SkMutex、SkSpinlock 等）
            -> 平台抽象基础层
                 -> SkGetThreadID()   <-- 本文件
                      -> OS 线程 API（pthread / Win32）
```

在典型的调用路径中，`SkMutex` 在 debug 模式下使用 `SkGetThreadID()` 来验证锁的获取和释放操作是否由同一线程执行，从而检测潜在的线程安全错误。

## 主要类与结构体

### 类型定义（在头文件 `include/private/base/SkThreadID.h` 中）

```cpp
typedef int64_t SkThreadID;
```

线程标识符类型，统一使用 64 位有符号整数表示，以适配不同平台的线程 ID 类型。

### 常量

```cpp
const SkThreadID kIllegalThreadID = 0;
```

非法线程 ID 值，用作未初始化或无效状态的哨兵值。值为 0 是安全的，因为主流操作系统不会为真实线程分配 ID 为 0 的标识符。

## 公共 API 函数

### `SkGetThreadID()`

```cpp
SkThreadID SkGetThreadID();
```

获取当前执行线程的唯一标识符。

**返回值**: 当前线程的 `SkThreadID`，保证在同一进程内不同线程间具有唯一性。

**平台实现**:

| 平台 | 底层 API | 说明 |
|------|---------|------|
| Windows (`SK_BUILD_FOR_WIN`) | `GetCurrentThreadId()` | 返回 DWORD 类型的线程 ID，隐式转换为 int64_t |
| POSIX（Linux/macOS/Android 等） | `pthread_self()` | 返回 `pthread_t` 类型，强制转换为 int64_t |

**可见性**: 该函数使用条件编译宏 `SkDEBUGCODE(SK_SPI)` 声明，意味着：
- 在 **debug 构建** 中：函数使用 `SK_SPI`（Skia Public/Private Interface）导出，可被外部代码调用
- 在 **release 构建** 中：函数可能不被导出，甚至可能被完全优化掉（如果没有被引用）

## 内部实现细节

### 平台分支

文件使用简单的预处理器条件编译实现跨平台：

```cpp
#ifdef SK_BUILD_FOR_WIN
    #include "src/base/SkLeanWindows.h"
    SkThreadID SkGetThreadID() { return GetCurrentThreadId(); }
#else
    #include <pthread.h>
    SkThreadID SkGetThreadID() { return (int64_t)pthread_self(); }
#endif
```

- **Windows 分支**: 包含精简版 Windows 头文件（`SkLeanWindows.h` 封装了 `<windows.h>` 并定义了精简宏以减少编译开销），使用 `GetCurrentThreadId()` 返回的 `DWORD` 值
- **POSIX 分支**: 包含 `<pthread.h>`，对 `pthread_self()` 返回的 `pthread_t` 进行 C 风格强制转换为 `int64_t`

### pthread_t 到 int64_t 的转换

`pthread_self()` 返回的 `pthread_t` 在不同平台上类型不同（Linux 上通常是 `unsigned long`，macOS 上是指针类型）。将其强制转换为 `int64_t` 是安全的，因为该值仅用于相等性比较，不需要保留其语义含义。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `include/private/base/SkThreadID.h` | 类型定义 `SkThreadID` 和函数声明 |
| `src/base/SkLeanWindows.h` | Windows 平台精简头文件（仅 Windows 分支） |
| `<pthread.h>` | POSIX 线程库头文件（仅 POSIX 分支） |

## 设计模式与设计决策

### 最小化平台抽象

该文件是 Skia 中 **最小化平台抽象** 设计理念的典型体现：用最少的代码量封装平台差异，提供统一的接口。整个实现仅有效代码 6 行。

### Debug-Only 导出

通过 `SkDEBUGCODE(SK_SPI)` 的条件导出机制，确保线程 ID 功能仅在调试构建中对外可见。这体现了 Skia 的设计哲学：调试辅助功能不应增加 release 构建的 ABI 表面积。

### SkLeanWindows.h 的使用

使用 Skia 自己的 `SkLeanWindows.h` 而非直接包含 `<windows.h>`，是为了避免 Windows 头文件引入大量宏和符号污染编译环境，并缩短编译时间。

### int64_t 统一类型

选择 `int64_t` 作为跨平台的统一线程 ID 类型，足够宽以容纳所有平台的线程标识符（Windows 的 `DWORD` 是 32 位，POSIX 的 `pthread_t` 最多 64 位）。

## 性能考量

- **极低开销**: `GetCurrentThreadId()` 和 `pthread_self()` 都是极快的系统调用，通常不会进入内核态（在 Linux 上通过 TLS 直接读取，在 Windows 上从 TEB 结构读取）
- **Debug-Only 使用**: 该函数主要在 debug 构建的互斥锁断言中使用，在 release 构建中不会产生运行时开销
- **无缓存**: 函数每次调用都直接查询操作系统，未做线程局部缓存（因为调用开销已经足够低）

## 相关文件

- `include/private/base/SkThreadID.h` - 类型定义和函数声明
- `include/private/base/SkMutex.h` - 互斥锁实现，debug 模式下使用 `SkGetThreadID()` 验证锁所有权
- `src/base/SkLeanWindows.h` - Windows 平台精简头文件封装
- `src/base/SkSpinlock.h` - 自旋锁实现，可能间接使用线程 ID 进行调试
- `include/private/base/SkDebug.h` - 定义 `SkDEBUGCODE` 宏
