# SkIDChangeListener

> 源文件: `include/private/SkIDChangeListener.h`

## 概述

SkIDChangeListener 是一个用于监听生成 ID 或唯一 ID 失效事件的通知系统。当缓存对象的 ID 失效时,监听器会收到通知,从而可以抢先清除缓存中已不可达的项。该类支持标记为待注销,防止缓存项在 ID 失效前被移除时监听器无限增长。这是 Skia 资源管理和缓存系统的重要组成部分。

## 架构位置

SkIDChangeListener 位于 Skia 核心资源管理层,作为缓存失效机制的基础设施。它被纹理缓存、图像缓存、路径引用等多个子系统使用,提供了一个通用的失效通知框架。该类定义在 `include/private` 目录,主要供 Skia 内部模块使用。

## 主要类与结构体

### SkIDChangeListener

监听器基类,提供 ID 变化的通知接口。

**继承关系**: `SkRefCnt` → `SkIDChangeListener`

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fShouldDeregister | std::atomic<bool> | 原子标志,指示监听器是否应该被注销 |

**设计特点**:
- 继承自 SkRefCnt,使用引用计数管理生命周期
- 纯虚函数 `changed()` 由派生类实现
- 支持线程安全的注销标记

### SkIDChangeListener::List

监听器列表管理类,维护一组监听器并提供通知和清理功能。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fMutex | mutable SkMutex | 互斥锁,保护监听器列表 |
| fListeners | skia_private::STArray<1, sk_sp<SkIDChangeListener>> | 监听器数组,初始容量 1 |

**设计特点**:
- 使用 STArray,小规模时避免堆分配
- 线程安全,所有操作都受 mutex 保护
- 自动清理已标记为待注销的监听器

## 公共 API 函数

### SkIDChangeListener 类

#### `SkIDChangeListener()`
- **功能**: 构造函数,初始化监听器
- **参数**: 无
- **说明**: fShouldDeregister 初始化为 false

#### `~SkIDChangeListener() override`
- **功能**: 虚析构函数,确保派生类正确清理
- **参数**: 无

#### `virtual void changed() = 0`
- **功能**: 纯虚函数,当 ID 变化时被调用
- **参数**: 无
- **返回值**: 无
- **说明**: 派生类必须实现此方法来响应 ID 失效事件

#### `void markShouldDeregister()`
- **功能**: 标记监听器应该被注销
- **参数**: 无
- **返回值**: 无
- **说明**:
  - 使用 relaxed 内存序存储
  - 标记后不应再调用 changed()
  - 下次列表操作时会被移除

#### `bool shouldDeregister()`
- **功能**: 检查监听器是否已标记为待注销
- **参数**: 无
- **返回值**: true 表示应该注销,false 表示仍然活跃
- **说明**: 使用 acquire 内存序读取

### SkIDChangeListener::List 类

#### `List()`
- **功能**: 构造函数,创建空的监听器列表
- **参数**: 无

#### `~List()`
- **功能**: 析构函数,释放所有监听器
- **参数**: 无

#### `void add(sk_sp<SkIDChangeListener> listener)`
- **功能**: 添加新的监听器到列表
- **参数**: `listener` - 要添加的监听器智能指针
- **返回值**: 无
- **说明**:
  - 监听器必须未被标记为待注销
  - 会自动清理列表中已标记的监听器
  - 线程安全,使用 mutex 保护

#### `int count() const`
- **功能**: 获取列表中监听器的数量
- **参数**: 无
- **返回值**: 监听器数量(包括待注销的)
- **说明**: 线程安全

#### `void changed()`
- **功能**: 通知所有未注销的监听器并重置列表
- **参数**: 无
- **返回值**: 无
- **说明**:
  - 调用每个未注销监听器的 changed() 方法
  - 调用后清空列表
  - 线程安全

#### `void reset()`
- **功能**: 重置列表,不调用监听器的 changed()
- **参数**: 无
- **返回值**: 无
- **说明**:
  - 直接清空列表
  - 不触发通知
  - 线程安全

## 内部实现细节

### 注销机制

监听器的生命周期分为三个阶段:

1. **活跃状态**: 正常监听 ID 变化
2. **标记待注销**: 调用 markShouldDeregister() 后
3. **已移除**: 从列表中清除

标记机制防止两种问题:
- **无限增长**: 缓存项在 ID 失效前被移除,监听器永远不会被触发
- **悬空通知**: ID 失效时通知已不存在的缓存项

### 清理时机

已标记的监听器在以下时机被清理:
1. 调用 `add()` 添加新监听器时
2. 调用 `changed()` 触发通知时
3. 析构 List 时

这种惰性清理策略:
- 避免频繁的列表遍历
- 在有其他操作时顺便清理
- 不影响 changed() 的正确性

### 线程安全设计

两个层次的线程安全:

**监听器级别**:
- fShouldDeregister 使用 atomic<bool>
- markShouldDeregister: relaxed 存储(无需同步)
- shouldDeregister: acquire 读取(确保看到标记)

**列表级别**:
- 所有列表操作都受 fMutex 保护
- 使用 SK_EXCLUDES 宏文档化锁语义
- 避免死锁(从不在持锁时调用外部代码)

### 内存序选择

原子操作的内存序:
- **markShouldDeregister**: relaxed
  - 只需原子性,不需要同步
  - 标记是单向的(false → true)

- **shouldDeregister**: acquire
  - 确保读取到最新的标记
  - 与后续操作建立 happens-before 关系

### changed() 调用时序

List::changed() 的执行流程:
1. 加锁
2. 拷贝监听器列表到临时变量
3. 清空原列表
4. 解锁
5. 遍历临时列表,调用未注销监听器的 changed()

这种设计的优点:
- 持锁时间短,提高并发性
- changed() 回调在无锁状态执行,避免死锁
- 回调期间新添加的监听器不会被立即触发

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/private/base/SkMutex.h` | 互斥锁 |
| `include/private/base/SkTArray.h` | 数组容器 |
| `include/private/base/SkThreadAnnotations.h` | 线程安全注解 |
| `<atomic>` | 原子操作 |

### 被依赖的模块

- **SkPathRef**: 路径引用使用监听器通知路径变化
- **SkPixelRef**: 像素引用使用监听器通知像素数据变化
- **GrGpuResource**: GPU 资源使用监听器管理缓存失效
- **SkResourceCache**: 通用资源缓存使用此机制
- **SkImage**: 图像对象通知缓存失效

## 设计模式与设计决策

### 观察者模式

SkIDChangeListener 是观察者模式的实现:
- **主题(Subject)**: 拥有 ID 的资源对象
- **观察者(Observer)**: 监听器对象
- **通知**: changed() 方法

与经典观察者模式的区别:
- 支持注销标记,避免内存泄漏
- 使用引用计数管理生命周期
- 线程安全的实现

### 延迟清理策略

不立即清理已标记的监听器:
- **减少开销**: 避免频繁的列表操作
- **批量处理**: 在其他操作时顺便清理
- **简化逻辑**: 无需专门的清理机制

### 分离的 List 类

将列表管理独立为内部类:
- **职责分离**: 监听器专注于通知,列表专注于管理
- **灵活性**: 可以为同一个监听器使用多个列表
- **封装性**: 列表的实现细节对外部隐藏

### 小对象优化

使用 STArray<1, ...> 初始容量为 1:
- **常见情况优化**: 大多数对象只有 0-1 个监听器
- **避免堆分配**: 单个监听器时不需要动态内存
- **性能提升**: 减少内存分配和缓存未命中

## 性能考量

### 内存占用

**SkIDChangeListener**:
- SkRefCnt 基类: 8 字节(虚表指针 + 引用计数)
- fShouldDeregister: 4 字节(实际可能 1 字节 + 3 字节填充)
- 总计: 约 16 字节

**List**:
- SkMutex: 平台相关(Linux ~40 字节,Windows ~32 字节)
- STArray<1>: 约 16 字节(包含内联存储)
- 总计: 约 56-64 字节

### 操作复杂度

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| markShouldDeregister | O(1) | 原子写入 |
| shouldDeregister | O(1) | 原子读取 |
| add | O(n) | 可能需要清理已标记的监听器 |
| changed | O(n) | 遍历所有监听器 |
| reset | O(1) | 清空列表 |

n 是监听器数量,通常很小(0-10)。

### 锁竞争

潜在的性能瓶颈:
- 如果多线程频繁 add/changed,mutex 可能成为瓶颈
- 实际中监听器操作频率低,很少出现竞争
- changed() 在无锁状态调用回调,减少持锁时间

### 优化建议

1. **批量操作**: 如果需要添加多个监听器,考虑批量接口
2. **读写锁**: 如果读操作远多于写操作,可以使用 shared_mutex
3. **无锁实现**: 对于极高性能需求,可以考虑无锁队列

## 典型使用场景

### 图像缓存失效

```cpp
class ImageCacheEntry : public SkIDChangeListener {
public:
    ImageCacheEntry(SkPixelRef* pixelRef) : fPixelRef(pixelRef) {
        pixelRef->addIDChangeListener(sk_ref_sp(this));
    }

    void changed() override {
        // 像素数据已变化,从缓存中移除此项
        gImageCache.remove(fKey);
    }

private:
    SkPixelRef* fPixelRef;
    CacheKey fKey;
};
```

### 路径引用监听

```cpp
// SkPath 持有 SkPathRef,当路径修改时通知
class SkPathRef {
    void notifyChanged() {
        fIDChangeListeners.changed();
    }

    SkIDChangeListener::List fIDChangeListeners;
};

// 缓存监听路径变化
cache->addChangeListener(sk_make_sp<PathCacheListener>(pathRef));
```

### 提前移除缓存项

```cpp
void Cache::remove(const Key& key) {
    auto entry = fMap.find(key);
    if (entry) {
        // 标记监听器,避免后续 ID 失效时再次通知
        entry->listener->markShouldDeregister();
        fMap.erase(key);
    }
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/core/SkIDChangeListener.cpp` | 实现文件 |
| `include/private/SkPathRef.h` | 使用监听器通知路径变化 |
| `include/core/SkPixelRef.h` | 使用监听器通知像素变化 |
| `src/core/SkResourceCache.cpp` | 资源缓存使用此机制 |
| `src/gpu/ganesh/GrGpuResource.cpp` | GPU 资源使用监听器 |
| `include/core/SkRefCnt.h` | 基类,提供引用计数 |
