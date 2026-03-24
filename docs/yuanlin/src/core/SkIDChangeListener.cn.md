# SkIDChangeListener

> 源文件
> - src/core/SkIDChangeListener.cpp
> - include/private/SkIDChangeListener.h (需参考)

## 概述

`SkIDChangeListener` 是 Skia 的缓存失效通知机制,用于在对象的生成 ID(generation ID)或唯一 ID 失效时,主动通知相关的缓存条目提前清理。该机制防止缓存无限增长,特别是当缓存项在 ID 失效前就被删除的场景下,可以标记监听器为"应注销"状态,避免监听器泄漏。

核心包括两个类:
- **`SkIDChangeListener`**: 抽象基类,定义失效回调接口
- **`SkIDChangeListener::List`**: 监听器列表,管理多个监听器的生命周期和通知

## 架构位置

`SkIDChangeListener` 位于 Skia 缓存管理架构的通知层:

- **观察对象**: 拥有生成 ID 的对象(如 `SkPixelRef`、`SkImage`、`SkTypeface`)
- **观察者**: 缓存条目,监听对象 ID 变化
- **触发时机**: 对象销毁或内容修改导致 ID 失效
- **应用场景**:
  - 图像缓存失效(像素数据变化)
  - 字体缓存失效(字体文件卸载)
  - 纹理缓存失效(GPU 资源释放)

## 主要类与结构体

### SkIDChangeListener

**继承关系**: 继承自 `SkRefCnt`(引用计数管理)

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fShouldDeregister | bool | 是否应该注销(缓存项已删除) |

### SkIDChangeListener::List

监听器列表,管理一组监听器。

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fListeners | skia_private::TArray&lt;sk_sp&lt;SkIDChangeListener&gt;&gt; | 监听器数组 |
| fMutex | mutable SkMutex | 保护列表的互斥锁 |

## 公共 API 函数

### SkIDChangeListener

```cpp
// 构造与析构
SkIDChangeListener();
virtual ~SkIDChangeListener();

// 核心回调(子类必须实现)
virtual void changed() = 0;

// 标记管理
void markShouldDeregister() { fShouldDeregister = true; }
bool shouldDeregister() const { return fShouldDeregister; }
```

### SkIDChangeListener::List

```cpp
// 构造与析构
List();
~List();  // 销毁时通知所有未注销的监听器

// 监听器管理
void add(sk_sp<SkIDChangeListener> listener);
int count() const;

// 通知与清理
void changed();  // 通知所有监听器并清空列表
void reset();    // 清空列表(不通知)
```

## 内部实现细节

### 添加监听器

```cpp
void List::add(sk_sp<SkIDChangeListener> listener) {
    if (!listener) {
        return;
    }
    SkASSERT(!listener->shouldDeregister());

    SkAutoMutexExclusive lock(fMutex);

    // 清理已标记为注销的监听器(垃圾回收)
    for (int i = 0; i < fListeners.size(); ++i) {
        if (fListeners[i]->shouldDeregister()) {
            fListeners.removeShuffle(i--);  // 无需保持顺序,使用 shuffle 移除
        }
    }

    fListeners.push_back(std::move(listener));
}
```

关键设计:
- **增量垃圾回收**: 每次添加时清理旧监听器,避免集中清理的峰值开销
- **无序移除**: `removeShuffle()` 将最后一个元素交换到被删除位置,O(1) 复杂度
- **空指针检查**: 允许传入 null 监听器(静默忽略)

### 通知失效

```cpp
void List::changed() {
    SkAutoMutexExclusive lock(fMutex);
    for (auto& listener : fListeners) {
        if (!listener->shouldDeregister()) {
            listener->changed();  // 触发回调
        }
    }
    fListeners.clear();  // 通知后立即清空
}
```

语义:
- **一次性通知**: 失效通知后,所有监听器自动移除
- **跳过已注销**: 不通知标记为 `shouldDeregister` 的监听器
- **自动清理**: 避免监听器累积

### 析构行为

```cpp
List::~List() {
    // 不需要互斥锁(析构时不应有其他线程访问)
    for (auto& listener : fListeners) {
        if (!listener->shouldDeregister()) {
            listener->changed();  // 通知未注销的监听器
        }
    }
}
```

保证对象销毁时,所有活跃的缓存项都能收到通知。

### 线程安全设计

所有公开方法都通过 `SkAutoMutexExclusive` 保护:
```cpp
SkAutoMutexExclusive lock(fMutex);
```

支持场景:
- 多线程并发添加监听器
- 一个线程触发失效,其他线程同时查询
- 析构与添加的竞争(虽然应避免)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRefCnt | 监听器的引用计数管理 |
| SkMutex | 线程安全保护 |
| skia_private::TArray | 动态数组存储监听器 |
| SkAssert | 断言验证 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkPixelRef | 像素数据变化时通知缓存 |
| SkImage | 图像失效通知 |
| SkTypeface | 字体卸载通知 |
| SkResourceCache | 缓存条目实现监听器 |
| GrGpuResource | GPU 资源失效通知 |

## 设计模式与设计决策

### 观察者模式(Observer Pattern)

标准的观察者模式实现:
- **主题(Subject)**: 拥有 `SkIDChangeListener::List` 的对象
- **观察者(Observer)**: `SkIDChangeListener` 子类
- **通知机制**: `changed()` 方法

### 引用计数生命周期管理

使用 `sk_sp<SkIDChangeListener>` 管理生命周期:
- 避免悬挂指针
- 自动释放未使用的监听器
- 支持监听器共享(如果需要)

### 延迟删除标记

`shouldDeregister()` 标记实现延迟删除:
- **问题**: 缓存项删除但对象未失效时,监听器泄漏
- **解决**: 标记监听器,下次 `add()` 或 `changed()` 时清理
- **优点**: 避免实时查找和删除,分摊开销

### 设计决策: 一次性通知

为什么 `changed()` 后清空列表:
- 生成 ID 失效意味着对象内容变化或销毁
- 旧的缓存条目不再有效,无需保留监听器
- 如果对象继续存活(如 `notifyPixelsChanged()`),会生成新 ID 和新监听器

### 设计决策: removeShuffle vs removeAt

使用 `removeShuffle()` 而非 `removeAt()`:
- 监听器顺序不重要
- O(1) 删除 vs O(n) 移动
- 适合频繁删除场景

### 设计决策: 析构时通知

为什么析构时调用 `changed()`:
- 保证对象生命周期结束时,所有缓存项都收到通知
- 避免缓存项持有失效对象的引用
- 实现缓存的一致性保证

## 性能考量

### 增量垃圾回收

```cpp
// 每次 add() 时清理,而非集中清理
for (int i = 0; i < fListeners.size(); ++i) {
    if (fListeners[i]->shouldDeregister()) {
        fListeners.removeShuffle(i--);
    }
}
```

优点:
- 分摊清理开销,避免峰值延迟
- 及时释放内存
- 适合高频添加/删除场景

### 无序移除优化

`removeShuffle()` 实现:
```cpp
// 伪代码
void removeShuffle(int index) {
    fArray[index] = std::move(fArray.back());
    fArray.pop_back();
}
```

时间复杂度 O(1),避免数组元素移动。

### 锁粒度

每个操作独立加锁,粒度较细:
- 减少锁持有时间
- 提高并发性
- 避免在持锁期间调用回调(可能死锁)

注意: `changed()` 在持锁时调用回调,要求回调实现不能尝试重新获取相同锁。

### 引用计数开销

使用 `sk_sp` 的开销:
- 每次添加/删除: 原子增减引用计数
- 通常可接受,因为监听器数量不多
- 避免手动内存管理的复杂性

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/private/SkIDChangeListener.h | 头文件 | 类定义 |
| include/core/SkPixelRef.h | 使用者 | 像素数据失效通知 |
| include/core/SkImage.h | 使用者 | 图像失效通知 |
| src/core/SkResourceCache.h | 观察者 | 缓存条目实现监听器 |
| include/core/SkRefCnt.h | 基类 | 引用计数管理 |
| include/private/base/SkMutex.h | 工具 | 线程同步 |
| include/private/base/SkTArray.h | 工具 | 动态数组 |
