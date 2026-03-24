# SkTHash

> 源文件: src/core/SkTHash.h

## 概述

`SkTHash` 是 Skia 中的现代化哈希表实现,提供了三个主要容器:`THashTable` (底层哈希表)、`THashMap` (键值映射) 和 `THashSet` (集合)。该实现采用开放寻址法 (线性探测) 解决冲突,支持自动扩容和缩容,并提供了完整的迭代器接口。相比旧版 `SkTDynamicHash`,`THashMap` 和 `THashSet` 提供了更安全的 API,防止意外修改键导致哈希表损坏。所有容器支持移动语义、初始化列表构造和范围 for 循环。

## 架构位置

`SkTHash` 位于 Skia 核心数据结构层:
- **位置**: `src/core/` - Skia 核心实现目录
- **命名空间**: `skia_private`
- **层次**: 基础容器,被 Skia 各模块广泛使用
- **用途**: 提供高性能哈希表、映射和集合实现

## 主要类与结构体

### THashTable<T, K, Traits>

底层哈希表实现,使用开放寻址法。

**模板参数**:
- `T`: 存储的元素类型
- `K`: 键类型
- `Traits`: 特性类,提供键提取和哈希函数

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCount` | `int` | 当前元素数量 |
| `fCapacity` | `int` | 哈希表容量 (2 的幂) |
| `fSlots` | `std::unique_ptr<Slot[]>` | 槽位数组 |

**Traits 要求**:
- `static K GetKey(T)`: 从元素提取键
- `static uint32_t Hash(K)`: 计算哈希值
- 可选: `static bool ShouldGrow(int count, int capacity)`
- 可选: `static bool ShouldShrink(int count, int capacity)`

### THashMap<K, V, HashK>

键值映射容器,封装 `THashTable`。

**模板参数**:
- `K`: 键类型
- `V`: 值类型
- `HashK`: 键的哈希函数对象 (默认 `SkGoodHash`)

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `THashTable<Pair, K>` | 底层哈希表 |

**内部类型 Pair**:
- 继承自 `std::pair<K, V>`
- 提供 `GetKey()` 和 `Hash()` 静态方法

### THashSet<T, HashT>

集合容器,存储唯一值。

**模板参数**:
- `T`: 元素类型
- `HashT`: 哈希函数对象 (默认 `SkGoodHash`)

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `THashTable<T, T, Traits>` | 底层哈希表 |

### THashTable::Iter<SlotVal>

迭代器类,支持范围 for 循环。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `const TTable*` | 指向哈希表 |
| `fSlot` | `int` | 当前槽位索引 |

### Slot (THashTable 内部类)

哈希槽位,使用联合体优化未初始化状态。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHash` | `uint32_t` | 哈希值 (0 表示空槽) |
| `fVal` | `union { T fStorage; }` | 值存储 |

## 公共 API 函数

### THashTable 核心接口

```cpp
T* set(T val)
```
插入或更新元素,返回表中元素的指针 (在下次 `set()` 前有效)。

```cpp
T* find(const K& key) const
```
查找键对应的元素,返回指针或 `nullptr`。

```cpp
T findOrNull(const K& key) const
```
查找并返回元素 (仅适用于指针类型 `T`)。

```cpp
bool removeIfExists(const K& key)
```
如果键存在则删除,返回是否成功删除。

```cpp
void remove(const K& key)
```
删除键,键必须存在 (否则断言)。

```cpp
void resize(int capacity)
```
手动调整容量 (必须是 2 的幂)。

```cpp
void reserve(int n)
```
预留容量,自动调整为合适的 2 的幂。

```cpp
template <typename Fn>
void foreach(Fn&& fn)
```
遍历所有元素,`fn(T*)` 或 `fn(const T&)`。

### THashMap 接口

```cpp
V* set(K key, V val)
```
设置键值对,返回值的指针。

```cpp
V* find(const K& key) const
```
查找键对应的值指针。

```cpp
V& operator[](const K& key)
```
索引操作,键不存在时插入默认值。

```cpp
void remove(const K& key)
void removeIfExists(const K& key)
```
删除操作。

```cpp
template <typename Fn>
void foreach(Fn&& fn)
```
遍历,支持 `fn(K, V*)`, `fn(const K&, V)`, `fn(Pair)` 等多种形式。

```cpp
Iter begin() const
Iter end() const
```
迭代器接口,支持范围 for 循环。

### THashSet 接口

```cpp
void add(T item)
```
添加元素。

```cpp
bool contains(const T& item) const
```
检查元素是否存在。

```cpp
const T* find(const T& item) const
```
查找元素指针。

```cpp
void remove(const T& item)
```
删除元素。

```cpp
template <typename Fn>
void foreach(Fn&& fn) const
```
遍历所有元素。

```cpp
Iter begin() const
Iter end() const
```
迭代器接口。

## 内部实现细节

### 开放寻址法 (线性探测)

使用反向线性探测 (向前探测) 解决冲突:
```cpp
int next(int index) const {
    index--;
    if (index < 0) { index += fCapacity; }
    return index;
}
```
初始位置: `index = hash & (fCapacity - 1)`

### 哈希值处理

```cpp
static uint32_t Hash(const K& key) {
    uint32_t hash = Traits::Hash(key) & 0xffffffff;
    return hash ? hash : 1;  // 保留 0 作为空标记
}
```
确保哈希值非零,使用 0 标记空槽。

### 动态扩容和缩容

**默认策略**:
- **扩容**: 当 `4 * count >= 3 * capacity` 时 (75% 负载因子)
- **缩容**: 当 `4 * count <= capacity` 时 (25% 负载因子,最小容量 4)
- **容量翻倍**: 扩容时容量 * 2,缩容时容量 / 2

**自定义策略**:
通过 `Traits::ShouldGrow()` 和 `Traits::ShouldShrink()` 自定义。

### 槽位管理

`Slot` 类使用联合体优化:
```cpp
union Storage {
    T fStorage;
    Storage() {}   // 不初始化
    ~Storage() {}  // 不析构
} fVal;
```
仅在 `fHash != 0` 时 `fStorage` 才有效,手动管理生命周期。

### 删除操作的重排

删除元素后需要重新排列后续元素以维护探测链:
```cpp
void removeSlot(int index) {
    fCount--;
    for (;;) {
        // 查找可以移动到空槽的元素
        index = this->next(index);
        Slot& s = fSlots[index];
        if (s.empty()) {
            emptySlot.reset();
            return;
        }
        // 判断是否可以移动
        originalIndex = s.fHash & (fCapacity - 1);
        if (/* 复杂条件判断 */) {
            emptySlot = std::move(moveFrom);
        }
    }
}
```

### 迭代器实现

迭代器跳过空槽:
```cpp
int nextPopulatedSlot(int currentSlot) const {
    for (int i = currentSlot + 1; i < fCapacity; i++) {
        if (fSlots[i].has_value()) {
            return i;
        }
    }
    return fCapacity;  // end() 位置
}
```

### THashMap 初始化列表

支持初始化列表构造:
```cpp
THashMap<int, std::string> map = {
    {1, "one"},
    {2, "two"},
    {3, "three"}
};
```
自动计算初始容量: `SkNextPow2(pairs.size() * 4 / 3)`。

### constexpr 检测 Traits

使用 SFINAE 检测 `Traits` 是否提供自定义负载因子方法:
```cpp
template <typename U, typename = void>
struct HasShouldGrow : std::false_type {};

template <typename U>
struct HasShouldGrow<U, std::void_t<decltype(U::ShouldGrow(...))>>
    : std::true_type {};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/base/SkMathPriv.h` | `SkNextPow2()` 计算 2 的幂 |
| `src/core/SkChecksum.h` | `SkGoodHash` 哈希函数 |
| `include/core/SkTypes.h` | 基础类型定义 |
| `<memory>`, `<utility>` | 智能指针和移动语义 |
| `<type_traits>` | SFINAE 和类型特性 |

### 被依赖的模块

`SkTHash` 在 Skia 中被广泛使用:
- 资源缓存 (`SkResourceCache`)
- 字体管理 (`SkFontMgr`)
- GPU 资源追踪
- 编译器内部数据结构
- 测试框架

## 设计模式与设计决策

### 1. 开放寻址 vs 链表法
选择开放寻址提高缓存局部性,减少内存碎片。

### 2. 反向线性探测
使用 `index--` 而非 `index++`,可能有助于某些硬件的预取优化。

### 3. 2 的幂容量
使用 `hash & (capacity - 1)` 而非 `hash % capacity`,提高取模性能。

### 4. 0 作为空标记
避免额外的布尔标志,节省内存。

### 5. 封装层次
`THashTable` 提供底层能力,`THashMap` 和 `THashSet` 提供安全的高层接口。

### 6. 类型安全
`THashMap` 分离键和值,防止修改键破坏哈希表。

### 7. 移动语义优化
充分利用 C++11 移动语义减少拷贝。

### 8. Placement New
槽位使用 placement new 构造,精确控制对象生命周期。

## 性能考量

### 1. 缓存友好
开放寻址法将数据紧密存储,提高缓存命中率。

### 2. 负载因子
默认 75% 负载因子平衡内存使用和查找性能。

### 3. 容量预留
`reserve()` 方法减少批量插入时的重新分配次数。

### 4. 初始容量优化
初始化列表构造自动计算合适容量,避免初始扩容。

### 5. 哈希质量
使用 `SkGoodHash` 提供高质量哈希,减少冲突。

### 6. 迭代器开销
迭代器需要跳过空槽,满表时最优,稀疏表时较慢。

### 7. 删除成本
删除操作需要重排元素,最坏情况 O(n)。

### 8. 编译时检测
使用 `constexpr if` 和 SFINAE 避免运行时开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkTHash.h` | 声明与实现 | 完整模板定义 |
| `src/core/SkTDynamicHash.h` | 旧版实现 | 已废弃,现为 `THashTable` 的封装 |
| `src/core/SkChecksum.h` | 依赖 | 提供 `SkGoodHash` |
| `src/base/SkMathPriv.h` | 依赖 | 提供 `SkNextPow2` |

## 使用示例

### THashMap 示例

```cpp
// 初始化列表构造
THashMap<int, std::string> ages = {
    {1, "Alice"},
    {2, "Bob"},
    {3, "Carol"}
};

// 插入
ages.set(4, "David");

// 查找
if (std::string* name = ages.find(2)) {
    std::cout << *name << std::endl;  // "Bob"
}

// 索引操作
ages[5] = "Eve";  // 插入新键

// 遍历
ages.foreach([](int id, const std::string& name) {
    std::cout << id << ": " << name << std::endl;
});

// 范围 for 循环
for (const auto& [id, name] : ages) {
    std::cout << id << ": " << name << std::endl;
}

// 删除
ages.remove(3);
```

### THashSet 示例

```cpp
// 初始化列表
THashSet<int> primes = {2, 3, 5, 7, 11};

// 添加元素
primes.add(13);

// 检查存在
if (primes.contains(7)) {
    std::cout << "7 is prime" << std::endl;
}

// 遍历
primes.foreach([](int n) {
    std::cout << n << " ";
});

// 范围 for
for (int n : primes) {
    std::cout << n << " ";
}
```

### 自定义哈希

```cpp
struct Point {
    int x, y;
    bool operator==(const Point& p) const {
        return x == p.x && y == p.y;
    }
};

struct PointHash {
    uint32_t operator()(const Point& p) const {
        return SkChecksum::Mix(p.x) ^ SkChecksum::Mix(p.y);
    }
};

THashSet<Point, PointHash> points;
points.add({10, 20});
```
