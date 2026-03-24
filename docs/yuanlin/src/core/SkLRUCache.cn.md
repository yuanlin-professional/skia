# SkLRUCache

> 源文件
> - src/core/SkLRUCache.h

## 概述

`SkLRUCache` 是 Skia 中实现的泛型 LRU(Least Recently Used,最近最少使用)缓存类模板。它提供了一个高效的缓存容器,自动管理容量并在达到上限时淘汰最久未使用的条目。该类广泛用于 Skia 内部的各种缓存场景,如字体缓存、图像滤镜缓存、着色器缓存等。

该实现使用哈希表和双向链表的组合,提供 O(1) 的查找、插入和删除操作,同时维护访问顺序以支持 LRU 淘汰策略。

## 架构位置

`SkLRUCache` 在 Skia 缓存系统中的位置:

```
应用层 (字体、图像、着色器等)
    ↓
SkLRUCache<K, V> (泛型 LRU 缓存)
    ↓
SkTHashTable (哈希表) + SkTInternalLList (双向链表)
```

它是 Skia 内部缓存机制的核心组件。

## 主要类与结构体

### SkNoOpPurge

**默认清理回调:**

```cpp
struct SkNoOpPurge {
    template <typename K, typename V>
    void operator()(void* /* context */, const K& /* k */, const V* /* v */) const {}
};
```

**用途:** 当不需要特殊清理逻辑时使用的空操作回调。

### SkLRUCache

**模板参数:**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| K | 键类型 | - |
| V | 值类型 | - |
| HashK | 哈希函数对象 | SkGoodHash |
| PurgeCB | 淘汰回调函数对象 | SkNoOpPurge |

**关键嵌套类型:**

#### Entry

```cpp
struct Entry {
    template<typename K1, typename V1>
    Entry(K1&& key, V1&& value)
        : fKey(std::forward<K1>(key))
        , fValue(std::forward<V1>(value)) {}

    const K fKey;
    V fValue;

    SK_DECLARE_INTERNAL_LLIST_INTERFACE(Entry);
};
```

**特点:**
- fKey 是 const,插入后不可修改
- 包含双向链表节点接口(通过宏声明)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMaxCount | int | 最大缓存条目数 |
| fMap | THashTable&lt;Entry*, K, Traits&gt; | 哈希表,用于快速查找 |
| fLRU | SkTInternalLList&lt;Entry&gt; | 双向链表,维护访问顺序 |
| fContext | void* | 传递给 PurgeCB 的上下文指针 |

## 公共 API 函数

### 构造函数

```cpp
explicit SkLRUCache(int maxCount, void* context = nullptr);
```

**参数:**
- `maxCount`: 最大缓存条目数(必须 > 0)
- `context`: 传递给淘汰回调的上下文指针

**限制:** 不允许默认构造,必须指定 maxCount。

### 析构函数

```cpp
~SkLRUCache();
```

**行为:** 删除所有缓存的 Entry 对象(调用 PurgeCB)。

### find

```cpp
V* find(const K& key);
```

**功能:** 查找键对应的值。

**行为:**
1. 在哈希表中查找 Entry
2. 如果找到且不在链表头部,移动到头部(更新访问时间)
3. 返回值的指针

**返回值:**
- 找到: 返回值的指针
- 未找到: 返回 nullptr

**时间复杂度:** O(1)

### insert

```cpp
template<typename K1, typename V1>
V* insert(K1&& key, V1&& value);

V* insert(Entry* entry);
```

**功能:** 插入新键值对。

**行为:**
1. 创建新 Entry(或使用提供的 Entry)
2. 插入到哈希表和链表头部
3. 如果超过 maxCount,淘汰链表尾部的条目

**返回值:** 指向新插入值的指针。

**注意:**
- 不检查键是否已存在(调用者需确保)
- 使用完美转发避免不必要的拷贝

**时间复杂度:** O(1) (均摊)

### insert_or_update

```cpp
template<typename K1, typename V1>
V* insert_or_update(K1&& key, V1&& value);
```

**功能:** 插入或更新键值对。

**行为:**
1. 调用 find() 查找键
2. 如果找到,更新值
3. 如果未找到,调用 insert() 插入

**返回值:** 指向值的指针(新插入或更新后的)。

**时间复杂度:** O(1)

### remove

```cpp
void remove(const K& key);
```

**功能:** 移除指定键的条目。

**行为:**
1. 在哈希表中查找 Entry
2. 调用 PurgeCB 回调
3. 从哈希表和链表中移除
4. 删除 Entry 对象

**时间复杂度:** O(1)

### count

```cpp
int count() const;
```

**功能:** 返回当前缓存的条目数。

**实现:**
```cpp
return fMap.count();
```

### foreach

```cpp
template <typename Fn>  // f(const K*, V*)
void foreach(Fn&& fn);
```

**功能:** 遍历所有缓存条目(从最近访问到最久未访问)。

**参数:** 可调用对象,接受 `(const K*, V*)` 参数。

**用途:** 调试、统计、批量操作等。

### reset

```cpp
void reset();
```

**功能:** 清空缓存,删除所有条目。

**行为:**
1. 清空哈希表
2. 遍历链表,删除所有 Entry
3. 清空链表

## 内部实现细节

### 数据结构组合

`SkLRUCache` 使用两种数据结构:

1. **哈希表(fMap):** O(1) 查找
2. **双向链表(fLRU):** 维护访问顺序

**关系:**
- 哈希表存储 `Entry*`
- 链表存储同样的 `Entry*`
- Entry 对象在两个结构中共享

### Traits 结构体

```cpp
struct Traits {
    static const K& GetKey(Entry* e) {
        return e->fKey;
    }

    static uint32_t Hash(const K& k) {
        return HashK()(k);
    }
};
```

**用途:** 适配 SkTHashTable,使其可以使用 Entry* 作为存储类型,同时使用 K 作为查找键。

### find 实现

```cpp
V* find(const K& key) {
    Entry** value = fMap.find(key);
    if (!value) {
        return nullptr;
    }
    Entry* entry = *value;
    if (entry != fLRU.head()) {
        fLRU.remove(entry);
        fLRU.addToHead(entry);
    }
    return &entry->fValue;
}
```

**关键点:**
- 如果 entry 已经在头部,不移动(优化)
- 否则,先移除再添加到头部

### insert 实现

```cpp
V* insert(Entry* entry) {
    fMap.set(entry);
    fLRU.addToHead(entry);
    while (fMap.count() > fMaxCount) {
        this->remove(fLRU.tail()->fKey);
    }
    return &entry->fValue;
}
```

**淘汰策略:**
- 使用 while 循环确保不超过 maxCount
- 淘汰链表尾部(最久未使用)

### remove 实现

```cpp
void remove(const K& key) {
    Entry** value = fMap.find(key);
    SkASSERT(value);
    Entry* entry = *value;
    SkASSERT(key == entry->fKey);
    PurgeCB()(fContext, key, &entry->fValue);  // 调用回调
    fMap.remove(key);
    fLRU.remove(entry);
    delete entry;
}
```

**关键:** 在删除前调用 PurgeCB,允许用户清理资源。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkTInternalLList | 双向链表 |
| SkChecksum | 哈希函数 |
| SkTHash | 哈希表 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkGlyphCache | 字形缓存 |
| SkResourceCache | 资源缓存 |
| SkImageFilter | 滤镜缓存 |
| SkRuntimeEffect | 着色器缓存 |

## 设计模式与设计决策

### 策略模式

通过模板参数注入策略:
- **HashK:** 自定义哈希函数
- **PurgeCB:** 自定义淘汰回调

**示例:**
```cpp
struct CustomHash {
    uint32_t operator()(const MyKey& k) const { /* ... */ }
};

struct CustomPurge {
    void operator()(void* ctx, const MyKey& k, const MyValue* v) const {
        // 清理资源
    }
};

SkLRUCache<MyKey, MyValue, CustomHash, CustomPurge> cache(100, myContext);
```

### 不可拷贝设计

```cpp
SkLRUCache(const SkLRUCache&) = delete;
SkLRUCache& operator=(const SkLRUCache&) = delete;
```

**原因:**
- LRU 缓存包含复杂的内部状态
- 拷贝语义不明确(深拷贝还是浅拷贝?)
- 通过指针或引用传递更合适

### 完美转发

insert 方法使用完美转发:
```cpp
template<typename K1, typename V1>
V* insert(K1&& key, V1&& value) {
    return this->insert(new Entry(std::forward<K1>(key), std::forward<V1>(value)));
}
```

**优势:**
- 避免不必要的拷贝
- 支持只移动类型(move-only types)
- 保持值类别(lvalue/rvalue)

### const K 设计

Entry 的 fKey 是 const:
```cpp
const K fKey;
```

**原因:**
- 键不应该在插入后修改(会破坏哈希表一致性)
- 编译时保证不可变性

## 性能考量

### O(1) 操作

所有主要操作都是 O(1):
- **find:** 哈希表查找 + 可选的链表移动
- **insert:** 哈希表插入 + 链表头部插入
- **remove:** 哈希表删除 + 链表删除

**原因:** 双向链表的节点移动是常数时间。

### 缓存局部性

虽然使用链表,但访问模式对缓存友好:
- **find:** 通常访问热点数据(在链表头部附近)
- **Entry 对象:** 键和值在同一内存块

### 内存开销

每个 Entry 的开销:
```
sizeof(Entry) = sizeof(K) + sizeof(V) + 2 * sizeof(void*)  // 链表指针
```

加上哈希表的开销(指针数组 + 负载因子)。

### 淘汰策略效率

淘汰最久未使用的条目只需要:
```cpp
this->remove(fLRU.tail()->fKey);
```

链表尾部访问是 O(1)。

### 优化技巧

**头部检查优化:**
```cpp
if (entry != fLRU.head()) {
    fLRU.remove(entry);
    fLRU.addToHead(entry);
}
```

避免对已在头部的条目进行不必要的链表操作。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/base/SkTInternalLList.h | 依赖 | 双向链表实现 |
| src/core/SkChecksum.h | 依赖 | 哈希函数 |
| src/core/SkTHash.h | 依赖 | 哈希表实现 |
| src/core/SkGlyphCache.h | 使用者 | 字形缓存 |
| src/core/SkResourceCache.h | 使用者 | 资源缓存 |
