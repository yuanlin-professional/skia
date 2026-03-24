# SkTypefaceCache

> 源文件: src/core/SkTypefaceCache.h, src/core/SkTypefaceCache.cpp

## 概述

`SkTypefaceCache` 是 Skia 字体系统中的核心组件,负责管理字体对象(`SkTypeface`)的缓存。它提供了全局和实例级别的字体缓存机制,通过维护一个字体对象池来避免重复创建相同的字体,从而提高性能并减少内存使用。该类还负责生成全局唯一的 `SkTypefaceID`。

## 架构位置

`SkTypefaceCache` 位于 Skia 核心层 (`src/core`) 的字体管理子系统中,是字体对象生命周期管理的关键部分。它与以下组件协作:

- **上游**: `SkFontMgr`、各种平台特定的字体工厂
- **下游**: `SkTypeface` 及其子类、`SkScalerContext`
- **同级**: `SkTypefaceCache` 与字体序列化、字体描述符等模块交互

## 主要类与结构体

### SkTypefaceCache

**继承关系**:
- 无基类,独立类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTypefaces` | `skia_private::TArray<sk_sp<SkTypeface>>` | 存储缓存字体对象的动态数组 |

## 公共 API 函数

### 实例方法

| 函数签名 | 功能描述 |
|---------|---------|
| `SkTypefaceCache()` | 构造函数,初始化空缓存 |
| `void add(sk_sp<SkTypeface>)` | 向缓存添加字体对象 |
| `sk_sp<SkTypeface> findByProcAndRef(FindProc, void*)` | 使用回调函数查找字体 |
| `void purgeAll()` | 清除所有独占引用的字体 |

### 静态方法

| 函数签名 | 功能描述 |
|---------|---------|
| `static SkTypefaceID NewTypefaceID()` | 生成全局唯一的字体 ID |
| `static void Add(sk_sp<SkTypeface>)` | 向全局缓存添加字体 |
| `static sk_sp<SkTypeface> FindByProcAndRef(FindProc, void*)` | 在全局缓存中查找字体 |
| `static void PurgeAll()` | 清除全局缓存 |
| `static void Dump()` | 调试输出缓存状态 |

### 回调函数类型

```cpp
typedef bool(*FindProc)(SkTypeface*, void* context);
```

## 内部实现细节

### 缓存管理策略

1. **容量限制**: 缓存大小受 `SkGraphics::GetTypefaceCacheCountLimit()` 控制
2. **淘汰策略**: 当缓存满时,通过 `purge()` 方法移除四分之一的容量
3. **淘汰条件**: 仅移除引用计数为 1 的字体对象(缓存独占)
4. **移除算法**: 使用 `removeShuffle()` 进行无序快速移除

### 字体 ID 生成

```cpp
SkTypefaceID SkTypefaceCache::NewTypefaceID() {
    static std::atomic<int32_t> nextID{1};
    return nextID.fetch_add(1, std::memory_order_relaxed);
}
```

- 使用原子操作确保线程安全
- ID 从 1 开始递增
- 使用 `memory_order_relaxed` 以获得最佳性能

### 全局缓存实现

全局缓存使用单例模式和互斥锁保证线程安全:

```cpp
SkTypefaceCache& SkTypefaceCache::Get() {
    static SkTypefaceCache gCache;
    return gCache;
}

static SkMutex& typeface_cache_mutex() {
    static SkMutex& mutex = *(new SkMutex);
    return mutex;
}
```

所有静态方法在访问全局缓存时都会获取锁。

### 查找机制

`findByProcAndRef()` 提供了灵活的查找接口:

```cpp
sk_sp<SkTypeface> SkTypefaceCache::findByProcAndRef(FindProc proc, void* ctx) const {
    for (const sk_sp<SkTypeface>& typeface : fTypefaces) {
        if (proc(typeface.get(), ctx)) {
            return typeface;
        }
    }
    return nullptr;
}
```

- 线性遍历所有缓存的字体
- 使用用户提供的回调函数判断匹配
- 返回的智能指针自动增加引用计数

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkTypeface` | 被缓存的字体对象 |
| `SkGraphics` | 获取缓存大小限制 |
| `SkMutex` | 全局缓存的线程同步 |
| `SkTArray` | 动态数组存储 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkTypeface` 构造函数 | 调用 `NewTypefaceID()` 获取唯一 ID |
| 字体管理器 | 使用静态方法添加和查找字体 |
| 字体工厂 | 在创建字体后添加到缓存 |

## 设计模式与设计决策

### 设计模式

1. **单例模式**: 全局缓存实例
2. **策略模式**: `FindProc` 回调允许自定义查找逻辑
3. **RAII**: 使用智能指针自动管理生命周期

### 设计决策

**为什么使用回调函数查找?**
- 提供最大灵活性,支持按名称、样式等多种条件查找
- 避免为每种查找条件实现专门方法
- 调用者可以传递上下文数据

**为什么不使用哈希表?**
- 字体匹配逻辑复杂,不适合简单的键值查找
- 缓存大小通常较小,线性查找性能可接受
- 简化实现,减少内存开销

**为什么使用 `removeShuffle()` 而不是 `remove()`?**
- 不需要维护顺序,提高移除性能
- 减少数组元素移动操作

**线程安全策略**
- ID 生成使用原子操作,无需锁
- 全局缓存使用粗粒度锁,保证操作原子性
- 实例级缓存不提供线程安全保证,由调用者负责

## 性能考量

### 优化策略

1. **惰性淘汰**: 仅在添加时检查容量,减少不必要的清理
2. **批量淘汰**: 一次移除多个对象,减少频繁清理
3. **原子操作**: ID 生成使用 `relaxed` 内存序,最小化同步开销
4. **智能指针**: 自动引用计数管理,避免手动内存管理错误

### 性能权衡

- **线性查找 vs 哈希查找**: 牺牲查找性能换取实现简单性和灵活性
- **全局锁 vs 细粒度锁**: 使用全局锁简化并发控制,但可能成为瓶颈
- **无序移除**: 使用 `removeShuffle()` 提升移除性能,但丧失插入顺序

### 内存管理

- 缓存仅持有弱引用语义(通过 `unique()` 检查)
- 自动清理不再使用的字体
- 可通过 `SkGraphics` 调整缓存大小限制

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkTypeface.h` | 定义被缓存的字体对象接口 |
| `include/core/SkGraphics.h` | 提供缓存限制配置 |
| `include/core/SkFontStyle.h` | 字体样式定义,用于查找匹配 |
| `include/private/base/SkMutex.h` | 提供线程同步原语 |
| `include/private/base/SkTArray.h` | 动态数组实现 |
| `src/core/SkFontDescriptor.cpp` | 字体序列化相关 |
