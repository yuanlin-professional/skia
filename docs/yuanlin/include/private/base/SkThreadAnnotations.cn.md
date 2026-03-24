# SkThreadAnnotations

> 源文件: `include/private/base/SkThreadAnnotations.h`

## 概述

SkThreadAnnotations 提供了一套线程安全性注解宏，用于在编译时通过 Clang 的线程安全分析（Thread Safety Analysis）检测潜在的并发问题。这些宏基于 Clang 的属性系统，允许开发者为锁、受保护的数据和函数标注语义信息，编译器可以静态分析代码是否遵循了正确的锁定协议。

## 架构位置

本模块位于 Skia 的私有基础设施层，属于编译期工具支持。它不影响运行时行为，仅在编译期间为 Clang 编译器提供额外的分析信息。该模块被 Skia 的所有需要线程同步的组件广泛使用。

## 主要宏定义

### 基础宏

#### `SK_THREAD_ANNOTATION_ATTRIBUTE(x)`

```cpp
#if defined(__clang__) && (!defined(SWIG))
#define SK_THREAD_ANNOTATION_ATTRIBUTE(x)   __attribute__((x))
#else
#define SK_THREAD_ANNOTATION_ATTRIBUTE(x)   // no-op
#endif
```

- **功能**: 所有线程注解的基础宏，将参数转换为 Clang 属性
- **平台**: 仅在 Clang 编译器且非 SWIG 环境下启用
- **其他编译器**: 展开为空，不影响代码

### 锁能力注解

#### `SK_CAPABILITY(x)`

```cpp
#define SK_CAPABILITY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(capability(x))
```

- **功能**: 标注一个类型表示锁能力（capability）
- **用途**: 用于定义锁类型（如 SkMutex）
- **示例**: `class SK_CAPABILITY("mutex") SkMutex { ... };`

#### `SK_SCOPED_CAPABILITY`

```cpp
#define SK_SCOPED_CAPABILITY SK_THREAD_ANNOTATION_ATTRIBUTE(scoped_lockable)
```

- **功能**: 标注一个 RAII 风格的作用域锁类型
- **用途**: 用于自动锁管理类（如 SkAutoMutexExclusive）
- **示例**: `class SK_SCOPED_CAPABILITY SkAutoMutexExclusive { ... };`

### 数据保护注解

#### `SK_GUARDED_BY(x)`

```cpp
#define SK_GUARDED_BY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(guarded_by(x))
```

- **功能**: 标注变量受指定锁保护
- **用途**: 标记成员变量
- **示例**: `int data SK_GUARDED_BY(mutex);`
- **语义**: 访问 `data` 前必须持有 `mutex`

#### `SK_PT_GUARDED_BY(x)`

```cpp
#define SK_PT_GUARDED_BY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(pt_guarded_by(x))
```

- **功能**: 标注指针指向的内容受指定锁保护（pointer-target guarded by）
- **用途**: 标记指针成员
- **示例**: `Data* ptr SK_PT_GUARDED_BY(mutex);`
- **语义**: 访问 `*ptr` 前必须持有 `mutex`，但访问 `ptr` 本身不需要

### 锁顺序注解

#### `SK_ACQUIRED_BEFORE(...)`

```cpp
#define SK_ACQUIRED_BEFORE(...) SK_THREAD_ANNOTATION_ATTRIBUTE(acquired_before(__VA_ARGS__))
```

- **功能**: 标注锁的获取顺序，此锁应在参数中的锁之前获取
- **用途**: 防止死锁
- **示例**: `SkMutex mutex1 SK_ACQUIRED_BEFORE(mutex2);`

#### `SK_ACQUIRED_AFTER(...)`

```cpp
#define SK_ACQUIRED_AFTER(...) SK_THREAD_ANNOTATION_ATTRIBUTE(acquired_after(__VA_ARGS__))
```

- **功能**: 标注锁的获取顺序，此锁应在参数中的锁之后获取
- **用途**: 防止死锁
- **示例**: `SkMutex mutex2 SK_ACQUIRED_AFTER(mutex1);`

### 函数需求注解

#### `SK_REQUIRES(...)`

```cpp
#define SK_REQUIRES(...) SK_THREAD_ANNOTATION_ATTRIBUTE(requires_capability(__VA_ARGS__))
```

- **功能**: 标注函数调用时必须持有指定锁
- **用途**: 标记需要在锁保护下调用的函数
- **示例**: `void foo() SK_REQUIRES(mutex);`

#### `SK_REQUIRES_SHARED(...)`

```cpp
#define SK_REQUIRES_SHARED(...) SK_THREAD_ANNOTATION_ATTRIBUTE(requires_shared_capability(__VA_ARGS__))
```

- **功能**: 标注函数调用时必须持有指定锁的共享（读）访问权
- **用途**: 用于读写锁的读端
- **示例**: `void read() SK_REQUIRES_SHARED(rwlock);`

### 锁获取注解

#### `SK_ACQUIRE(...)`

```cpp
#define SK_ACQUIRE(...) SK_THREAD_ANNOTATION_ATTRIBUTE(acquire_capability(__VA_ARGS__))
```

- **功能**: 标注函数获取指定锁
- **用途**: 标记锁的 lock 方法
- **示例**: `void lock() SK_ACQUIRE(this);`

#### `SK_ACQUIRE_SHARED(...)`

```cpp
#define SK_ACQUIRE_SHARED(...) SK_THREAD_ANNOTATION_ATTRIBUTE(acquire_shared_capability(__VA_ARGS__))
```

- **功能**: 标注函数获取指定锁的共享访问权
- **用途**: 标记读写锁的 lock_shared 方法
- **示例**: `void lock_shared() SK_ACQUIRE_SHARED(this);`

### 锁释放注解

#### `SK_RELEASE_CAPABILITY(...)`

```cpp
#define SK_RELEASE_CAPABILITY(...) SK_THREAD_ANNOTATION_ATTRIBUTE(release_capability(__VA_ARGS__))
```

- **功能**: 标注函数释放指定锁
- **用途**: 标记锁的 unlock 方法
- **注意**: 不叫 `SK_RELEASE` 是因为该宏名已被用于调试模式（SK_DEBUG vs. SK_RELEASE）
- **示例**: `void unlock() SK_RELEASE_CAPABILITY(this);`

#### `SK_RELEASE_SHARED_CAPABILITY(...)`

```cpp
#define SK_RELEASE_SHARED_CAPABILITY(...) SK_THREAD_ANNOTATION_ATTRIBUTE(release_shared_capability(__VA_ARGS__))
```

- **功能**: 标注函数释放指定锁的共享访问权
- **用途**: 标记读写锁的 unlock_shared 方法
- **示例**: `void unlock_shared() SK_RELEASE_SHARED_CAPABILITY(this);`

### 条件获取注解

#### `SK_TRY_ACQUIRE(...)`

```cpp
#define SK_TRY_ACQUIRE(...) SK_THREAD_ANNOTATION_ATTRIBUTE(try_acquire_capability(__VA_ARGS__))
```

- **功能**: 标注函数尝试获取指定锁，可能失败
- **参数**: 第一个参数通常是表示成功的返回值（如 true）
- **示例**: `bool try_lock() SK_TRY_ACQUIRE(true, this);`

#### `SK_TRY_ACQUIRE_SHARED(...)`

```cpp
#define SK_TRY_ACQUIRE_SHARED(...) SK_THREAD_ANNOTATION_ATTRIBUTE(try_acquire_shared_capability(__VA_ARGS__))
```

- **功能**: 标注函数尝试获取指定锁的共享访问权
- **示例**: `bool try_lock_shared() SK_TRY_ACQUIRE_SHARED(true, this);`

### 排斥注解

#### `SK_EXCLUDES(...)`

```cpp
#define SK_EXCLUDES(...) SK_THREAD_ANNOTATION_ATTRIBUTE(locks_excluded(__VA_ARGS__))
```

- **功能**: 标注函数调用时不能持有指定锁
- **用途**: 防止死锁，标记会获取锁的函数
- **示例**: `void foo() SK_EXCLUDES(mutex);`

### 断言注解

#### `SK_ASSERT_CAPABILITY(x)`

```cpp
#define SK_ASSERT_CAPABILITY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(assert_capability(x))
```

- **功能**: 标注函数断言持有指定锁（不实际获取）
- **用途**: 用于断言函数，告知分析器假设已持有锁
- **示例**: `void assertHeld() SK_ASSERT_CAPABILITY(this);`

#### `SK_ASSERT_SHARED_CAPABILITY(x)`

```cpp
#define SK_ASSERT_SHARED_CAPABILITY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(assert_shared_capability(x))
```

- **功能**: 标注函数断言持有指定锁的共享访问权
- **示例**: `void assertHeldShared() SK_ASSERT_SHARED_CAPABILITY(this);`

### 返回值注解

#### `SK_RETURN_CAPABILITY(x)`

```cpp
#define SK_RETURN_CAPABILITY(x) SK_THREAD_ANNOTATION_ATTRIBUTE(lock_returned(x))
```

- **功能**: 标注函数返回指定的锁能力
- **用途**: 用于返回锁对象的函数
- **示例**: `SkMutex* getLock() SK_RETURN_CAPABILITY(mutex);`

### 分析禁用注解

#### `SK_NO_THREAD_SAFETY_ANALYSIS`

```cpp
#define SK_NO_THREAD_SAFETY_ANALYSIS SK_THREAD_ANNOTATION_ATTRIBUTE(no_thread_safety_analysis)
```

- **功能**: 禁用指定函数的线程安全分析
- **用途**: 用于复杂的锁定逻辑，分析器无法理解的情况
- **警告**: 应谨慎使用，可能隐藏真实问题
- **示例**: `void complexLocking() SK_NO_THREAD_SAFETY_ANALYSIS;`

## Google3 特殊支持

### 潜在阻塞区域宏

```cpp
#if defined(SK_BUILD_FOR_GOOGLE3) && !defined(SK_BUILD_FOR_WASM_IN_GOOGLE3) \
    && !defined(SK_BUILD_FOR_WIN)
    extern "C" {
        void __google_cxa_guard_acquire_begin(void) __attribute__((weak));
        void __google_cxa_guard_acquire_end  (void) __attribute__((weak));
    }
    static inline void sk_potentially_blocking_region_begin() {
        if (&__google_cxa_guard_acquire_begin) {
            __google_cxa_guard_acquire_begin();
        }
    }
    static inline void sk_potentially_blocking_region_end() {
        if (&__google_cxa_guard_acquire_end) {
            __google_cxa_guard_acquire_end();
        }
    }
    #define SK_POTENTIALLY_BLOCKING_REGION_BEGIN sk_potentially_blocking_region_begin()
    #define SK_POTENTIALLY_BLOCKING_REGION_END   sk_potentially_blocking_region_end()
#else
    #define SK_POTENTIALLY_BLOCKING_REGION_BEGIN
    #define SK_POTENTIALLY_BLOCKING_REGION_END
#endif
```

- **功能**: 标记可能阻塞的代码区域（Google3 专用）
- **用途**: 帮助 Google 内部工具检测潜在的性能问题
- **平台**: 仅在 Google3 构建环境（非 WASM、非 Windows）下启用
- **其他平台**: 展开为空

## 内部实现细节

### 条件编译

所有注解都通过条件编译实现：
- Clang 编译器：展开为 `__attribute__((...))`
- 其他编译器：展开为空注释

这确保了跨编译器兼容性，不影响代码的可移植性。

### 弱符号链接

Google3 的阻塞区域函数使用 `__attribute__((weak))`，允许符号在运行时不存在：

```cpp
if (&__google_cxa_guard_acquire_begin) {
    __google_cxa_guard_acquire_begin();
}
```

这种设计使代码在不同环境下都能编译和运行。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkFeatures.h | 平台特性检测 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkMutex.h | 使用 SK_CAPABILITY 标注锁类型 |
| SkSpinlock.h | 使用锁注解 |
| SkRWLock.h | 使用共享锁注解 |
| 所有多线程代码 | 使用 SK_GUARDED_BY 等保护数据 |

## 设计模式与设计决策

### 零开销抽象

注解在非 Clang 编译器下完全消失，不产生任何运行时开销。

### 防御性编程

通过编译期检查，在开发阶段就发现潜在的并发问题，而不是等到运行时。

### 渐进式采用

可以逐步为代码添加注解，不需要一次性全部完成。

### 命名约定

所有宏以 `SK_` 为前缀，避免与其他库冲突。

## 性能考量

### 编译期检查

所有分析在编译期完成，不影响运行时性能。

### 无运行时开销

注解不生成任何机器码，发布版本的二进制文件与未标注的代码完全相同。

### 编译时间

启用线程安全分析可能略微增加编译时间，但通常可以忽略不计。

## 平台相关说明

### Clang 专用

线程安全分析是 Clang 的特性，GCC 和 MSVC 不支持。

### SWIG 排除

SWIG（Simplified Wrapper and Interface Generator）在生成语言绑定时会忽略这些注解。

### Google3 集成

在 Google 的内部构建系统中，额外提供了阻塞区域检测功能。

## 使用示例

```cpp
// 定义一个锁类型
class SK_CAPABILITY("mutex") SkMutex {
public:
    void lock() SK_ACQUIRE();
    void unlock() SK_RELEASE_CAPABILITY();
};

// 定义受保护的数据
class DataStructure {
    SkMutex mutex;
    int data SK_GUARDED_BY(mutex);

    void updateData() {
        mutex.lock();
        data = 42;  // OK：持有锁
        mutex.unlock();
    }

    int getData() SK_REQUIRES(mutex) {
        return data;  // OK：调用者必须持有锁
    }
};

// RAII 锁
class SK_SCOPED_CAPABILITY AutoLock {
    SkMutex& mutex;
public:
    AutoLock(SkMutex& m) SK_ACQUIRE(m) : mutex(m) { mutex.lock(); }
    ~AutoLock() SK_RELEASE_CAPABILITY() { mutex.unlock(); }
};
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkFeatures.h` | 平台特性定义 |
| `include/private/base/SkMutex.h` | 互斥锁实现 |
| `include/private/base/SkSpinlock.h` | 自旋锁实现 |
| `include/private/base/SkSemaphore.h` | 信号量实现 |
| Clang 文档 | 线程安全分析官方文档 |
