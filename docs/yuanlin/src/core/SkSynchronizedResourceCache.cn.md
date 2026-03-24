# SkSynchronizedResourceCache

> 源文件: src/core/SkSynchronizedResourceCache.h, src/core/SkSynchronizedResourceCache.cpp

## 概述

`SkSynchronizedResourceCache` 是 Skia 图形库中的线程安全资源缓存实现类。它继承自 `SkResourceCache` 基类,通过添加互斥锁机制,为所有缓存操作提供线程同步保护,确保在多线程环境下安全地访问和管理缓存资源。该类主要用于在并发场景中缓存图形资源,如位图、纹理等,避免重复计算和加载,提高渲染性能。

## 架构位置

`SkSynchronizedResourceCache` 位于 Skia 核心层的资源管理模块中。它是资源缓存系统的一个关键组件,为上层渲染模块提供线程安全的缓存服务。该类通过继承 `SkResourceCache` 基类,在保持基类缓存逻辑不变的前提下,添加了多线程安全保护。

```
Skia 架构层次:
  应用层
    ↓
  渲染层 (使用缓存)
    ↓
  资源管理层
    ├─ SkResourceCache (基类)
    └─ SkSynchronizedResourceCache (线程安全版本)
```

## 主要类与结构体

### SkSynchronizedResourceCache

**继承关系:**
- 继承自: `SkResourceCache` (基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMutex` | `mutable SkMutex` | 互斥锁,用于保护所有缓存操作的线程安全 |

该类的设计核心是通过 `fMutex` 互斥锁,在每个公共方法中使用 `SkAutoMutexExclusive` 自动锁,确保所有对基类方法的调用都在锁的保护下进行。

## 公共 API 函数

### 构造和析构

| 函数签名 | 功能说明 |
|---------|---------|
| `SkSynchronizedResourceCache(DiscardableFactory)` | 使用可丢弃内存工厂构造缓存 |
| `SkSynchronizedResourceCache(size_t byteLimit)` | 使用字节限制构造缓存 |
| `~SkSynchronizedResourceCache()` | 析构函数,默认实现 |

### 查找和添加操作

| 函数签名 | 功能说明 |
|---------|---------|
| `bool find(const Key& key, FindVisitor, void* context)` | 查找缓存项,线程安全 |
| `void add(Rec*, void* payload = nullptr)` | 添加缓存项,线程安全 |
| `void visitAll(Visitor, void* context)` | 遍历所有缓存项,线程安全 |

### 容量管理

| 函数签名 | 功能说明 |
|---------|---------|
| `size_t getTotalBytesUsed() const` | 获取当前使用的字节数 |
| `size_t getTotalByteLimit() const` | 获取总字节限制 |
| `size_t setTotalByteLimit(size_t newLimit)` | 设置新的字节限制 |
| `size_t setSingleAllocationByteLimit(size_t)` | 设置单个分配的字节限制 |
| `size_t getSingleAllocationByteLimit() const` | 获取单个分配的字节限制 |
| `size_t getEffectiveSingleAllocationByteLimit() const` | 获取有效的单个分配字节限制 |

### 其他操作

| 函数签名 | 功能说明 |
|---------|---------|
| `void purgeAll()` | 清除所有缓存项 |
| `DiscardableFactory discardableFactory() const` | 获取可丢弃内存工厂 |
| `SkCachedData* newCachedData(size_t bytes)` | 创建新的缓存数据 |
| `void dump() const` | 转储缓存信息用于调试 |

## 内部实现细节

### 线程同步机制

所有公共方法的实现都遵循相同的模式:
1. 通过 `SkAutoMutexExclusive am(fMutex)` 获取互斥锁
2. 调用基类 `SkResourceCache` 的对应方法
3. 锁在作用域结束时自动释放

示例实现:
```cpp
bool SkSynchronizedResourceCache::find(const Key& key, FindVisitor visitor, void* context) {
    SkAutoMutexExclusive am(fMutex);
    return SkResourceCache::find(key, visitor, context);
}
```

### Wrapper 模式

该类采用了经典的 Wrapper (包装器) 模式,它不改变基类的任何逻辑,只是为每个方法添加了线程安全保护层。这种设计使得:
- 基类可以继续维护缓存的核心逻辑
- 派生类专注于提供线程安全保证
- 代码职责分离清晰

### 互斥锁的使用

- `fMutex` 被声明为 `mutable`,允许在 `const` 方法中也能加锁
- 使用 `SkAutoMutexExclusive` RAII 机制,确保异常安全
- 所有方法都是排他性锁,保证同一时刻只有一个线程访问缓存

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkResourceCache` | 基类,提供缓存的核心功能 |
| `SkMutex` | 提供互斥锁机制 |
| `SkDebug` | 提供调试断言功能 |
| `SkCachedData` | 缓存数据的表示 |

### 被依赖的模块

该类被 Skia 中需要线程安全缓存的模块使用,包括:
- 多线程渲染管线
- 图像解码器的缓存层
- GPU 资源管理器
- 全局资源缓存实例

## 设计模式与设计决策

### 设计模式

1. **继承与多态**: 通过继承 `SkResourceCache` 实现接口复用
2. **Wrapper 模式**: 包装基类方法,添加线程同步功能
3. **RAII 模式**: 使用 `SkAutoMutexExclusive` 自动管理锁的生命周期

### 设计决策

1. **为何使用继承而非组合?**
   - 需要保持与基类相同的接口契约
   - 多态性使得可以在需要 `SkResourceCache*` 的地方使用此类

2. **为何每个方法都加锁?**
   - 简单直接的线程安全策略
   - 避免细粒度锁带来的复杂性和死锁风险
   - 对于缓存操作,粗粒度锁的性能开销是可接受的

3. **为何使用 mutable 互斥锁?**
   - 允许在 `const` 方法中加锁
   - 锁本身不是对象逻辑状态的一部分
   - 符合逻辑常量性的设计原则

## 性能考量

### 性能特点

1. **线程安全保证**: 所有操作都是线程安全的,但存在锁竞争开销
2. **锁粒度**: 使用粗粒度锁(整个缓存级别),简单但可能成为并发瓶颈
3. **适用场景**: 适合读写操作不是极端频繁的场景

### 性能优化建议

1. 如果应用场景读多写少,可以考虑使用读写锁替代互斥锁
2. 对于高并发场景,可以考虑使用分片锁或无锁数据结构
3. 批量操作时,考虑在应用层减少锁的获取次数

### 性能权衡

- **优势**: 实现简单,正确性容易保证,维护成本低
- **劣势**: 在高并发场景下,可能成为性能瓶颈
- **适用性**: 对于大多数图形应用,缓存访问不是最热路径,当前设计已足够

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkResourceCache.h` | 基类头文件,定义缓存核心接口 |
| `src/core/SkResourceCache.cpp` | 基类实现,包含缓存逻辑 |
| `include/private/base/SkMutex.h` | 互斥锁定义 |
| `include/private/base/SkDebug.h` | 调试工具 |
| `src/core/SkCachedData.h` | 缓存数据结构定义 |
