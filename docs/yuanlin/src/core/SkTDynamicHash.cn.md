# SkTDynamicHash

> 源文件: src/core/SkTDynamicHash.h

## 概述

`SkTDynamicHash` 是 Skia 中的遗留哈希表实现,现已成为 `THashTable<T*>` 的简单 API 封装。该类主要为了向后兼容而保留,新代码应直接使用 `SkTHashMap`、`SkTHashSet` 或 `THashTable`。`SkTDynamicHash` 存储指针类型的元素,通过 `Traits` 提取键和计算哈希值。它提供了基本的增删改查接口和遍历功能,但缺少现代哈希表的许多安全特性和便利功能。

## 架构位置

`SkTDynamicHash` 位于 Skia 核心数据结构层:
- **位置**: `src/core/` - Skia 核心实现目录
- **状态**: 遗留代码,已被 `SkTHash` 系列替代
- **层次**: API 封装层,底层使用 `skia_private::THashTable`
- **用途**: 向后兼容,维护旧代码

## 主要类与结构体

### SkTDynamicHash<T, Key, Traits>

动态哈希表封装类,存储 `T*` 类型指针。

**模板参数**:
- `T`: 元素类型 (实际存储 `T*`)
- `Key`: 键类型
- `Traits`: 特性类,提供键提取和哈希函数 (默认为 `T`)

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTable` | `skia_private::THashTable<T*, Key, AdaptedTraits>` | 底层哈希表实现 |

### AdaptedTraits (内部结构)

适配器,将 `Traits` 从 `T` 适配到 `T*`。

**静态方法**:
```cpp
static const Key& GetKey(T* entry)  // 调用 Traits::GetKey(*entry)
static uint32_t Hash(const Key& key)  // 调用 Traits::Hash(key)
```

## 公共 API 函数

### 构造

```cpp
SkTDynamicHash()
```
默认构造函数,创建空哈希表。

### 遍历

```cpp
template <typename Fn>
void foreach(Fn&& fn)
```
遍历所有条目 (可变版本),调用 `fn(T*)` 对每个元素。

```cpp
template <typename Fn>
void foreach(Fn&& fn) const
```
遍历所有条目 (常量版本),调用 `fn(T)` 或 `fn(const T&)` 对每个元素。

### 查询

```cpp
int count() const
```
返回哈希表中的元素数量。

```cpp
size_t approxBytesUsed() const
```
返回哈希表使用的近似内存字节数 (不包括 `sizeof(*this)`)。

```cpp
T* find(const Key& key) const
```
查找键对应的元素指针,如果不存在返回 `nullptr`。

### 修改

```cpp
void add(T* entry)
```
添加元素指针到哈希表。如果键已存在,覆盖旧值。

```cpp
void remove(const Key& key)
```
删除键对应的元素,键必须存在 (否则断言失败)。

### 清空

```cpp
void rewind()
void reset()
```
清空哈希表,两个方法等效,都调用底层 `fTable.reset()`。

## 内部实现细节

### API 封装

`SkTDynamicHash` 是薄封装层,所有操作直接转发给 `THashTable`:
```cpp
void add(T* entry) { fTable.set(entry); }
T* find(const Key& key) const { return fTable.findOrNull(key); }
void remove(const Key& key) { fTable.remove(key); }
```

### Traits 适配

由于底层 `THashTable` 存储 `T*`,而用户提供的 `Traits` 针对 `T`,需要适配器:
```cpp
struct AdaptedTraits {
    static const Key& GetKey(T* entry) {
        return Traits::GetKey(*entry);  // 解引用指针
    }
    static uint32_t Hash(const Key& key) {
        return Traits::Hash(key);  // 直接转发
    }
};
```

### foreach 双重封装

遍历操作需要在 `T*` 和 `T` 之间转换:
```cpp
// 可变版本: fn(T*) -> lambda([&](T** entry) { fn(*entry); })
void foreach(Fn&& fn) {
    fTable.foreach([&](T** entry) { fn(*entry); });
}

// 常量版本: fn(T) -> lambda([&](T* entry) { fn(*entry); })
void foreach(Fn&& fn) const {
    fTable.foreach([&](T* entry) { fn(*entry); });
}
```

### 指针存储

实际存储类型是 `T**`:
- `THashTable` 的槽位存储 `T*`
- `foreach` 回调接收 `T**` 或 `T*`

### Traits 要求

用户必须提供 `Traits` 类,包含:
```cpp
struct MyTraits {
    static const Key& GetKey(const T&);
    static uint32_t Hash(const Key&);
};
```
注意 `GetKey` 接收 `const T&`,而非 `T*`。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/core/SkTHash.h` | 底层 `THashTable` 实现 |
| C++ 标准库 | 模板和类型推导 |

### 被依赖的模块

`SkTDynamicHash` 仍在以下模块中使用 (遗留代码):
- 部分旧的资源管理器
- 旧的字体缓存实现
- 历史测试代码

**注意**: 新代码不应使用 `SkTDynamicHash`,应迁移到 `THashMap` 或 `THashSet`。

## 设计模式与设计决策

### 1. 适配器模式
`AdaptedTraits` 适配用户 `Traits` 到底层 `THashTable` 的要求。

### 2. 薄封装 (Thin Wrapper)
仅提供最小 API 封装,所有实现委托给底层 `THashTable`。

### 3. 向后兼容
保留旧 API 签名,避免破坏现有代码。

### 4. 指针语义
存储指针而非值,调用者负责内存管理。

### 5. 类型擦除
通过模板参数 `Traits` 解耦键提取逻辑。

## 性能考量

### 1. 零开销封装
封装层编译后基本无开销,调用直接内联到 `THashTable`。

### 2. 指针存储
相比直接存储对象,指针存储节省空间 (对于大对象),但增加一次间接访问。

### 3. 底层性能
继承 `THashTable` 的所有性能特性:
- 开放寻址法的缓存友好性
- 自动扩容和缩容
- O(1) 平均查找时间

### 4. 遍历开销
`foreach` 需要 lambda 包装,可能轻微影响内联,但现代编译器通常能优化。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkTDynamicHash.h` | 声明与实现 | 完整模板定义 |
| `src/core/SkTHash.h` | 依赖 | 底层 `THashTable` 实现 |
| `src/core/SkTMultiMap.h` | 相关 | 另一个基于 `SkTDynamicHash` 的容器 |

## 使用示例 (不推荐)

```cpp
// 定义元素类型
struct Entry {
    int key;
    std::string value;

    // Traits 方法
    static const int& GetKey(const Entry& e) { return e.key; }
    static uint32_t Hash(int k) { return SkChecksum::Mix(k); }
};

// 创建哈希表
SkTDynamicHash<Entry, int> hash;

// 添加元素 (调用者管理内存)
Entry* e1 = new Entry{1, "one"};
Entry* e2 = new Entry{2, "two"};
hash.add(e1);
hash.add(e2);

// 查找
Entry* found = hash.find(1);
if (found) {
    std::cout << found->value << std::endl;  // "one"
}

// 遍历
hash.foreach([](Entry* e) {
    std::cout << e->key << ": " << e->value << std::endl;
});

// 删除
hash.remove(1);
delete e1;

// 清空
hash.reset();
delete e2;
```

## 迁移建议

推荐迁移到 `THashMap` 或 `THashSet`:

```cpp
// 旧代码
SkTDynamicHash<Entry, int> hash;
hash.add(entry);

// 新代码 (THashMap)
THashMap<int, Entry> map;
map.set(entry->key, *entry);  // 拷贝值而非存储指针

// 或者使用 THashMap<int, std::unique_ptr<Entry>> 管理指针
```

**迁移优势**:
- 更安全 (防止修改键)
- 自动内存管理 (值语义)
- 更丰富的 API (如 `operator[]`)
- 支持范围 for 循环
- 初始化列表支持
