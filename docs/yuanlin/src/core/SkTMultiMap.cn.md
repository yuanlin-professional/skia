# SkTMultiMap

> 源文件: src/core/SkTMultiMap.h

## 概述

`SkTMultiMap` 是 Skia 中的模板化多值映射容器,允许单个键关联多个值。它基于 `SkTDynamicHash` 实现,使用链表存储相同键的多个值。该容器支持高效的插入、查找、删除操作,并提供自定义查找谓词的灵活接口。每个键对应的值列表通过单向链表组织,支持在多个相同值的场景下正确处理。`SkTMultiMap` 主要用于需要一对多映射关系的场景,如图形对象管理、资源索引等。

## 架构位置

`SkTMultiMap` 位于 Skia 核心数据结构层:
- **位置**: `src/core/` - Skia 核心实现目录
- **层次**: 基础容器,构建在 `SkTDynamicHash` 之上
- **用途**: 提供一键多值的映射能力,支持资源管理和对象索引

## 主要类与结构体

### SkTMultiMap

多值映射模板类。

**模板参数**:
- `T`: 值类型 (指针)
- `Key`: 键类型
- `HashTraits`: 哈希特性类 (默认为 `T`)

**继承关系**:
- 无继承

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHash` | `SkTDynamicHash<ValueList, Key>` | 底层哈希表,存储值列表 |
| `fCount` | `int` | 总值数量计数 |

### ValueList (内部结构)

值列表节点,用于链式存储同键的多个值。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fValue` | `T*` | 存储的值指针 |
| `fNext` | `ValueList*` | 指向下一个节点 |
| `fCount` | `uint32_t` | 链表中元素计数 (仅头节点维护) |

**静态方法**:
```cpp
static const Key& GetKey(const ValueList& e)
static uint32_t Hash(const Key& key)
```

## 公共 API 函数

### 构造与析构

```cpp
SkTMultiMap()
```
默认构造,初始化空映射。

```cpp
~SkTMultiMap()
```
析构,调用 `reset()` 清理所有资源。

### 容器管理

```cpp
void reset()
```
清空所有条目,对每个值调用 `HashTraits::OnFree()`,释放所有 `ValueList` 节点。

```cpp
int count() const
```
返回总值数量 (所有键的值总和)。

### 插入操作

```cpp
void insert(const Key& key, T* value)
```
插入键值对:
- 如果键已存在,新值插入到链表第二位,原头部值移到新节点
- 如果键不存在,创建新的 `ValueList` 并添加到哈希表
- 更新计数器

### 删除操作

```cpp
void remove(const Key& key, const T* value)
```
删除指定键值对:
- 在链表中查找匹配的值
- 调用 `internalRemove()` 处理删除逻辑
- 当前实现在找不到值时不会崩溃 (处理 crbug.com/877915)

### 查找操作

```cpp
T* find(const Key& key) const
```
查找键对应的第一个值,如果键不存在返回 `nullptr`。

```cpp
template<class FindPredicate>
T* find(const Key& key, const FindPredicate f)
```
使用谓词查找满足条件的第一个值:
```cpp
auto value = map.find(key, [](T* v) { return v->someCondition(); });
```

```cpp
template<class FindPredicate>
T* findAndRemove(const Key& key, const FindPredicate f)
```
查找并删除满足谓词的第一个值,返回该值的指针。

### 调试接口 (SK_DEBUG)

```cpp
template <typename Fn>
void foreach(Fn&& fn) const
```
遍历所有值,对每个值调用 `fn(*value)`。

```cpp
bool has(const T* value, const Key& key) const
```
检查指定值是否存在于键的值列表中。

```cpp
int countForKey(const Key& key) const
```
返回键对应的值数量。

## 内部实现细节

### 值列表插入策略

插入新值时采用特殊策略:
```cpp
ValueList* newEntry = new ValueList(list->fValue);  // 新节点存储旧头部值
newEntry->fNext = list->fNext;                      // 链接到旧链表
list->fNext = newEntry;                             // 旧头部链接新节点
list->fValue = value;                               // 旧头部存储新值
list->fCount++;
```
这种设计保持哈希表条目不变,仅修改链表结构。

### 删除节点处理

`internalRemove()` 处理三种情况:
1. **删除中间/尾部节点**: 将下一个节点的值复制到当前节点,删除下一个节点
2. **删除非头部节点**: 断开链接,删除节点
3. **删除头部节点**: 从哈希表移除,删除节点

```cpp
if (elem->fNext) {
    // 情况 1: 拷贝下一个节点的值,删除下一个节点
    ValueList* next = elem->fNext;
    elem->fValue = next->fValue;
    elem->fNext = next->fNext;
    delete next;
} else if (prev) {
    // 情况 2: 非头部,断开链接
    prev->fNext = nullptr;
    delete elem;
} else {
    // 情况 3: 头部节点,从哈希表移除
    fHash.remove(key);
    delete elem;
}
```

### 计数维护

- `fCount`: 全局值计数,每次插入 `++`,每次删除 `--`
- `ValueList::fCount`: 链表元素计数,仅在头节点维护,用于调试

### 哈希特性要求

`HashTraits` 必须提供:
- `static const Key& GetKey(const T&)`: 从值提取键
- `static uint32_t Hash(const Key&)`: 计算键的哈希值
- `static void OnFree(T*)`: 值释放时的清理回调

### 安全性处理

为处理 crbug.com/877915,`remove()` 实现了容错:
- 理想情况下应断言值存在 (`#if 0` 部分)
- 实际实现允许删除不存在的值,仅在 Debug 模式断言

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `src/core/SkTDynamicHash.h` | 底层动态哈希表 |
| C++ 标准库 | 指针、模板支持 |

### 被依赖的模块

`SkTMultiMap` 在 Skia 中用于:
- 图形资源管理 (多个对象共享同一标识符)
- 缓存系统 (一键多值的缓存条目)
- 渲染管线中的对象索引

## 设计模式与设计决策

### 1. 侵入式链表
使用自定义 `ValueList` 节点而非标准容器,减少内存分配次数。

### 2. 特殊插入顺序
新值插入到链表第二位而非头部,保持哈希表条目稳定性,避免修改哈希表的键值映射。

### 3. 延迟删除
删除节点时通过值拷贝减少指针修改,保持链表完整性。

### 4. 类型特性 (Traits)
通过 `HashTraits` 模板参数解耦键提取和哈希计算逻辑,提高灵活性。

### 5. 指针语义
存储 `T*` 而非 `T`,适用于大对象或多态场景,调用者负责内存管理。

### 6. 计数冗余
维护全局 `fCount` 和链表头 `fCount`,后者仅用于调试,便于 LLDB 查看。

## 性能考量

### 1. 哈希表查找
第一次查找通过哈希表,时间复杂度 O(1) 平均情况。

### 2. 链表遍历
同键多值通过链表存储,查找特定值需要 O(n) 时间,n 为该键的值数量。

### 3. 内存开销
每个值需要额外的 `ValueList` 节点 (16-24 字节),包含指针和计数器。

### 4. 插入优化
新值插入为 O(1),无需遍历链表。

### 5. 删除优化
删除中间节点通过值拷贝避免链表重连,但对于大对象可能有拷贝开销。

### 6. 缓存局部性
链表节点分散分配,可能降低缓存命中率。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkTMultiMap.h` | 声明与实现 | 模板类完整定义 |
| `src/core/SkTDynamicHash.h` | 依赖 | 底层哈希表实现 |
| `src/core/SkTHash.h` | 相关 | 另一个哈希表实现 |

## 使用示例

```cpp
// 定义值类型和哈希特性
struct MyValue {
    int key;
    std::string data;

    static int GetKey(const MyValue& v) { return v.key; }
    static uint32_t Hash(int k) { return SkChecksum::Mix(k); }
    static void OnFree(MyValue* v) { delete v; }
};

// 创建多值映射
SkTMultiMap<MyValue, int, MyValue> multiMap;

// 插入多个同键值
multiMap.insert(1, new MyValue{1, "first"});
multiMap.insert(1, new MyValue{1, "second"});
multiMap.insert(2, new MyValue{2, "third"});

// 查找
MyValue* v1 = multiMap.find(1);  // 返回最后插入的 "second"

// 条件查找
MyValue* v2 = multiMap.find(1, [](MyValue* v) {
    return v->data == "first";
});

// 删除特定值
multiMap.remove(1, v2);

// 清理
multiMap.reset();  // 触发所有 OnFree 回调
```
