# SkSpinlock

> 源文件: src/base/SkSpinlock.h, src/base/SkSpinlock.cpp

## 概述

`SkSpinlock` 是 Skia 中实现的轻量级自旋锁（spinlock）同步原语。它使用原子操作和忙等待（busy-waiting）机制实现互斥访问，适用于临界区极短的场景。相比传统的互斥锁，自旋锁在无竞争情况下开销极小，但在高竞争场景下会消耗 CPU 资源。

自旋锁的核心思想是通过不断检查锁状态而非阻塞线程来等待锁释放，因此只适用于持锁时间非常短的情况。

## 架构位置

`SkSpinlock` 位于 Skia 基础设施层的并发控制模块中：

- **层级**: src/base（基础工具层）
- **用途**: 为 Skia 提供轻量级互斥锁原语
- **应用场景**: 短临界区的快速同步、内存分配器、计数器更新

在 Skia 架构中，它是最底层的同步原语之一，被各种需要极低开销互斥的场景使用。

## 主要类与结构体

### SkSpinlock

自旋锁的核心实现类。

**继承关系**:
- 无继承关系

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLocked` | `std::atomic<bool>` | 原子布尔值，表示锁的状态（false=未锁定，true=已锁定） |

### SkAutoSpinlock

自旋锁的 RAII 包装类。

**继承关系**:
- 无继承关系

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSpinlock` | `SkSpinlock&` | 引用被管理的自旋锁 |

## 公共 API 函数

### SkSpinlock 核心 API

```cpp
// 构造函数
constexpr SkSpinlock() = default;  // fLocked 初始化为 false

// 获取锁
void acquire();                    // 阻塞直到获取锁

// 尝试获取锁
bool tryAcquire();                 // 尝试获取锁，立即返回成功/失败

// 释放锁
void release();                    // 释放锁
```

### SkAutoSpinlock RAII 类

```cpp
// 构造时获取锁
explicit SkAutoSpinlock(SkSpinlock& mutex);

// 析构时释放锁
~SkAutoSpinlock();
```

## 内部实现细节

### acquire - 获取锁

```cpp
void acquire() {
    if (fLocked.exchange(true, std::memory_order_acquire)) {
        // 锁被竞争，进入慢速路径
        this->contendedAcquire();
    }
}
```

**快速路径**:
- 使用 `exchange` 原子操作尝试将 `fLocked` 从 `false` 设为 `true`
- 若原值为 `false`（未锁定），则立即成功获取锁
- `memory_order_acquire` 确保后续读写操作不会重排到获取锁之前

**慢速路径**:
- 若原值为 `true`（已被其他线程持有），则调用 `contendedAcquire()`

### contendedAcquire - 竞争获取锁

```cpp
void SkSpinlock::contendedAcquire() {
    SK_POTENTIALLY_BLOCKING_REGION_BEGIN;
    while (fLocked.exchange(true, std::memory_order_acquire)) {
        do_pause();
    }
    SK_POTENTIALLY_BLOCKING_REGION_END;
}
```

**实现要点**:
1. **自旋循环**: 不断尝试 `exchange` 操作直到成功
2. **CPU 暂停指令**: 每次失败后调用 `do_pause()` 避免过度占用 CPU
3. **阻塞区域标记**: 使用 `SK_POTENTIALLY_BLOCKING_REGION` 宏通知性能分析工具

### do_pause - CPU 暂停指令

```cpp
#if SK_CPU_SSE_LEVEL >= SK_CPU_SSE_LEVEL_SSE2
    #include <emmintrin.h>
    static void do_pause() { _mm_pause(); }
#else
    static void do_pause() { /*spin*/ }
#endif
```

- **SSE2 平台**: 使用 `_mm_pause()` 指令（x86 的 `PAUSE`）
  - 向 CPU 提示正在自旋等待
  - 减少功耗
  - 避免流水线冲突
  - 提高超线程效率

- **其他平台**: 空操作（纯自旋）

### tryAcquire - 尝试获取锁

```cpp
bool tryAcquire() {
    if (fLocked.exchange(true, std::memory_order_acquire)) {
        // 锁已被持有
        return false;
    }
    return true;
}
```

- 只尝试一次，不进入自旋循环
- 立即返回成功或失败
- 用于避免阻塞的场景

### release - 释放锁

```cpp
void release() {
    fLocked.store(false, std::memory_order_release);
}
```

- 简单地将 `fLocked` 设为 `false`
- `memory_order_release` 确保临界区内的写操作对后续获取锁的线程可见

### SkAutoSpinlock - RAII 包装

```cpp
explicit SkAutoSpinlock(SkSpinlock& mutex) : fSpinlock(mutex) {
    fSpinlock.acquire();
}

~SkAutoSpinlock() {
    fSpinlock.release();
}
```

- 遵循 RAII 原则，自动管理锁的生命周期
- 保证异常安全（即使发生异常也会释放锁）

### debug_trace - 调试跟踪（默认禁用）

代码中包含被注释掉的调试功能：

```cpp
#if 0
    static void debug_trace() {
        // 使用 backtrace 打印调用栈
        // 用于调试锁竞争问题
    }
#endif
```

- 默认禁用，可手动启用用于调试锁竞争
- 使用互斥锁保护打印操作，避免递归使用自旋锁

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<atomic>` | 提供原子操作支持 |
| `SkThreadAnnotations.h` | 提供线程安全注解，支持静态分析工具 |
| `SkAPI.h` | API 导出宏定义 |
| `SkFeatures.h` | 平台特性检测 |
| `<emmintrin.h>` | x86 SSE2 指令（仅 SSE2+ 平台） |

### 被依赖的模块

`SkSpinlock` 作为底层同步原语，被以下场景使用：

| 使用场景 | 说明 |
|---------|------|
| 内存分配器 | 保护分配器内部的小型数据结构 |
| 计数器 | 保护共享计数器的原子更新 |
| 缓存管理 | 保护缓存查找表的短暂更新 |
| 对象池 | 保护对象分配/回收的快速路径 |

## 设计模式与设计决策

### 设计模式

1. **RAII 模式**: `SkAutoSpinlock` 确保锁的自动释放，防止死锁

2. **快速路径优化**: 无竞争情况下只需一次原子操作

3. **两阶段锁获取**: 分离快速路径和慢速路径，优化常见情况

### 设计决策

1. **自旋而非阻塞**:
   - 优点: 无竞争时开销极小（约 1-2 纳秒）
   - 缺点: 竞争时浪费 CPU 周期
   - 适用: 临界区极短（< 100 纳秒）的场景

2. **单个原子布尔值**:
   - 相比复杂的队列锁，实现极简
   - 内存占用仅 1 字节
   - 不保证公平性（可能导致某些线程饥饿）

3. **不使用操作系统锁原语**:
   - 避免系统调用开销
   - 避免线程上下文切换
   - 代价是竞争时消耗 CPU

4. **constexpr 构造函数**:
   - 允许编译时初始化
   - 静态全局锁零开销初始化

5. **提供 tryAcquire**:
   - 允许调用者实现非阻塞算法
   - 支持超时机制（外部实现）

6. **内联实现**:
   - 核心方法在头文件中内联
   - `contendedAcquire` 标记为 `SK_API`（不内联）
   - 原因: 慢速路径不内联可减小代码体积，快速路径内联可提高性能

7. **平台相关优化**:
   - x86 使用 `PAUSE` 指令
   - ARM 可扩展为 `WFE`/`SEV` 指令
   - 其他平台使用纯自旋

## 性能考量

### 性能特征

**无竞争情况**:
- 获取锁: 约 1-2 纳秒（单次原子操作）
- 释放锁: 约 1 纳秒（单次原子写）

**低竞争情况**:
- 自旋几次即可获取锁
- 总延迟: 10-100 纳秒

**高竞争情况**:
- 持续自旋直到锁释放
- CPU 占用率 100%
- 不适合长时间持锁

### 与其他锁的比较

| 锁类型 | 无竞争开销 | 竞争开销 | 适用场景 |
|--------|-----------|---------|---------|
| `SkSpinlock` | 极低（1-2 ns） | 高（100% CPU） | 极短临界区 |
| `SkMutex` | 低（10-20 ns） | 中（线程休眠） | 短临界区 |
| `SkSharedMutex` | 中（20-30 ns） | 中（信号量） | 读多写少 |
| `std::mutex` | 中（20-50 ns） | 低（内核调度） | 长临界区 |

### 优化策略

1. **尽量避免竞争**:
   - 减少锁的持有时间
   - 使用局部副本减少访问次数
   - 考虑无锁数据结构

2. **选择合适的锁**:
   - 临界区 < 100 ns → `SkSpinlock`
   - 临界区 < 10 μs → `SkMutex`
   - 临界区 > 10 μs → 考虑条件变量

3. **使用 tryAcquire 实现回退**:
   ```cpp
   if (!lock.tryAcquire()) {
       // 执行其他工作或使用更重的锁
   }
   ```

### 使用建议

**适用场景**:
- 更新简单计数器
- 分配器的快速路径
- 极短的读-修改-写操作
- 内存屏障配合

**不适用场景**:
- 包含 I/O 操作的临界区
- 可能睡眠的临界区
- 包含内存分配的临界区
- 临界区执行时间 > 1 微秒

**最佳实践**:
1. 始终使用 `SkAutoSpinlock` 管理生命周期
2. 临界区内避免函数调用（除非确定极快）
3. 避免在持锁时访问可能缺页的内存
4. 考虑使用原子操作代替自旋锁（如可能）

**调试建议**:
- 启用 `debug_trace()` 排查竞争问题
- 使用性能分析工具（Perf、VTune）检测自旋热点
- 监控 CPU 占用率识别过度自旋

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkMutex.h` | 标准互斥锁实现，适用于更长的临界区 |
| `include/private/base/SkThreadAnnotations.h` | 线程安全注解，支持 Clang Thread Safety Analysis |
| `include/private/base/SkFeatures.h` | 平台特性检测宏 |
| `src/core/SkResourceCache.cpp` | 使用 SkSpinlock 保护缓存统计计数 |
| `src/core/SkArenaAlloc.cpp` | 可能使用自旋锁保护分配器 |
