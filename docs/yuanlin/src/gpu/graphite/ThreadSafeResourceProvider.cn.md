# ThreadSafeResourceProvider

> 源文件: src/gpu/graphite/ThreadSafeResourceProvider.h, src/gpu/graphite/ThreadSafeResourceProvider.cpp

## 概述

`ThreadSafeResourceProvider` 是 Skia Graphite 架构中提供线程安全资源访问的包装类。该类封装了后端特定的 `ResourceProvider`，并通过自旋锁（`SkSpinlock`）保护其访问，确保多线程环境下的资源创建和管理的安全性。它公开了最小的 API 表面，主要用于 `SharedContext` 中跨 `Recorder` 的资源共享。

## 架构位置

```
Graphite 资源管理架构：
  ├── SharedContext（共享上下文）
  │   └── ThreadSafeResourceProvider（线程安全资源提供者）★
  │       └── ResourceProvider（后端特定资源提供者，被锁保护）
  └── Recorder（命令录制器）
      └── ResourceProvider（每个 Recorder 独立的资源提供者）
```

## 主要类与结构体

### ThreadSafeResourceProvider 类

```cpp
class ThreadSafeResourceProvider {
public:
    ThreadSafeResourceProvider(std::unique_ptr<ResourceProvider>);

    // 采样器查找/创建
    sk_sp<Sampler> findOrCreateCompatibleSampler(const SamplerDesc&) SK_EXCLUDES(fSpinLock);

    // 调试接口（仅 SK_DEBUG）
    size_t getResourceCacheLimit() const SK_EXCLUDES(fSpinLock);
    size_t getResourceCacheCurrentBudgetedBytes() const SK_EXCLUDES(fSpinLock);
    size_t getResourceCacheCurrentPurgeableBytes() const SK_EXCLUDES(fSpinLock);

    // 资源管理
    void dumpMemoryStatistics(SkTraceMemoryDump*) const SK_EXCLUDES(fSpinLock);
    void freeGpuResources() SK_EXCLUDES(fSpinLock);
    void purgeResourcesNotUsedSince(StdSteadyClock::time_point) SK_EXCLUDES(fSpinLock);
    void forceProcessReturnedResources() SK_EXCLUDES(fSpinLock);

protected:
    mutable SkSpinlock fSpinLock;
    std::unique_ptr<ResourceProvider> fWrappedProvider SK_GUARDED_BY(fSpinLock);
};
```

## 公共 API 函数

### 构造函数

```cpp
ThreadSafeResourceProvider(std::unique_ptr<ResourceProvider> resourceProvider);
```

**功能**: 包装后端特定的 `ResourceProvider`，提供线程安全访问。

### findOrCreateCompatibleSampler

```cpp
sk_sp<Sampler> findOrCreateCompatibleSampler(const SamplerDesc& desc);
```

**功能**: 线程安全地查找或创建兼容的采样器。

**实现**:
```cpp
sk_sp<Sampler> ThreadSafeResourceProvider::findOrCreateCompatibleSampler(const SamplerDesc& desc) {
    SkAutoSpinlock lock{fSpinLock};  // 自动加锁
    sk_sp<Sampler> sampler = fWrappedProvider->findOrCreateCompatibleSampler(desc);
    SkAssertResult(sampler->gpuMemorySize() == 0);  // 采样器应为 0 大小
    return sampler;
}
```

**关键点**: 断言采样器大小为 0，因为线程安全提供者中的资源不计入预算。

### 资源管理方法

```cpp
void dumpMemoryStatistics(SkTraceMemoryDump*) const;
void freeGpuResources();
void purgeResourcesNotUsedSince(StdSteadyClock::time_point purgeTime);
void forceProcessReturnedResources();
```

**功能**: 线程安全地管理资源缓存，所有调用都通过自旋锁保护。

### 调试方法（仅 SK_DEBUG）

```cpp
size_t getResourceCacheLimit() const;
size_t getResourceCacheCurrentBudgetedBytes() const;
size_t getResourceCacheCurrentPurgeableBytes() const;
```

**功能**: 查询资源缓存统计信息，仅在调试构建中可用。

## 内部实现细节

### 线程安全机制

**自旋锁保护**:
```cpp
protected:
    mutable SkSpinlock fSpinLock;
    std::unique_ptr<ResourceProvider> fWrappedProvider SK_GUARDED_BY(fSpinLock);
```

**自动加锁**:
```cpp
void ThreadSafeResourceProvider::freeGpuResources() {
    SkAutoSpinlock lock{fSpinLock};  // RAII 锁，自动释放
    fWrappedProvider->freeGpuResources();
}
```

**SK_EXCLUDES 注解**: 所有公共方法标记 `SK_EXCLUDES(fSpinLock)`，表示调用者不应持有锁。

### 委托模式

所有操作都委托给被包装的 `ResourceProvider`:
```cpp
void ThreadSafeResourceProvider::purgeResourcesNotUsedSince(StdSteadyClock::time_point purgeTime) {
    SkAutoSpinlock lock{fSpinLock};
    fWrappedProvider->purgeResourcesNotUsedSince(purgeTime);
}
```

### 0 大小资源约束

```cpp
SkAssertResult(sampler->gpuMemorySize() == 0);
```

**设计原因**: `ThreadSafeResourceProvider` 中的资源不计入预算，确保轻量级。

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `ResourceProvider` | 被包装的资源提供者 |
| `Sampler` | 采样器资源 |
| `SkSpinlock` | 自旋锁实现 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `SharedContext` | 提供线程安全的资源访问 |
| 多个 `Recorder` | 并发访问共享资源 |

## 设计模式与设计决策

### 装饰器模式

包装 `ResourceProvider` 并添加线程安全层，不改变其接口。

### RAII 锁管理

使用 `SkAutoSpinlock` 确保锁总是被正确释放：
```cpp
{
    SkAutoSpinlock lock{fSpinLock};
    // 临界区代码
}  // 锁自动释放
```

### 最小 API 表面

仅公开必要的方法（采样器创建和资源管理），隐藏其他 `ResourceProvider` 功能。

### 关键设计决策

1. **自旋锁而非互斥锁**: 预期临界区很短，自旋锁开销更低
2. **0 大小资源**: 线程安全提供者中的资源不计入预算，简化内存管理
3. **未来方向**: 注释表明一旦 `ResourceCache` 线程安全，该类可能被移除
4. **委托模式**: 不实现资源逻辑，仅添加线程安全保护

## 性能考量

### 锁开销

1. **自旋锁**: 适用于短临界区（通常仅几个指针操作）
2. **锁粒度**: 每次调用都获取锁，未细化粒度
3. **竞争**: 多 `Recorder` 并发访问时可能有锁竞争

### 内存开销

1. **包装器开销**: 仅一个智能指针和一个自旋锁（约 16 字节）
2. **0 大小资源**: 资源不占用预算，避免预算争用

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/ResourceProvider.h` | 被包装的资源提供者 |
| `src/gpu/graphite/SharedContext.h` | 使用该类的共享上下文 |
| `src/gpu/graphite/Sampler.h` | 采样器资源定义 |
| `src/base/SkSpinlock.h` | 自旋锁实现 |
| `src/gpu/graphite/ResourceCache.h` | 资源缓存（未来可能线程安全） |
