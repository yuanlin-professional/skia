# GrHashMapWithCache

> 源文件: src/gpu/ganesh/GrHashMapWithCache.h

## 概述

`GrHashMapWithCache` 是 Skia Ganesh GPU 后端中一个带有最近访问缓存的哈希表实现。它在标准哈希表 (`SkHashMap`) 的基础上添加了一级缓存,记住最近一次访问的键值对,从而在连续访问同一键时提供 O(1) 的快速路径,无需进行哈希计算和查找。

该数据结构特别适用于存在访问局部性 (locality of reference) 的场景,例如 GPU 资源的 UniqueID 查找表,其中连续操作经常访问同一个资源。

## 架构位置

`GrHashMapWithCache` 位于 Ganesh 的工具层,作为性能优化的数据结构:

```
SkHashMap (Skia 标准哈希表)
    └── 被 GrHashMapWithCache 包装
            └── 添加一级缓存优化
```

使用场景:
- **UniqueID 到资源的映射**: 频繁查询同一 ID
- **纹理代理缓存**: 连续帧可能重复使用同一纹理
- **任何具有访问局部性的映射**

与其他模块的关系:
- 使用 `skia_private::THashMap` 作为底层存储
- 配合 `GrCheapHash` 用于 UniqueID 的快速哈希
- 要求用户提供 `KeyTraits` 定义无效键

## 主要类与结构体

### 模板参数

```cpp
template <typename K,           // 键类型
          typename V,           // 值类型
          typename KeyTraits,   // 键特性(提供无效键)
          typename HashT = SkGoodHash>  // 哈希函数
class GrHashMapWithCache;
```

### KeyTraits 要求

```cpp
struct KeyTraits {
    static K GetInvalidKey();  // 返回永远不会出现的哨兵键
};
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMap` | `THashMap<K, V, HashT>` | 底层哈希表 |
| `fLastKey` | `mutable K` | 最近访问的键 |
| `fLastValue` | `mutable V*` | 最近访问值的指针 |

### GrCheapHash

```cpp
struct GrCheapHash {
    uint32_t operator()(uint32_t val) {
        return SkChecksum::CheapMix(val);
    }
};
```

- 专门为 UniqueID 设计的快速哈希
- 比 `SkGoodHash` 更快但质量略低
- 适用于已经分布良好的输入

## 公共 API 函数

### 容量查询

```cpp
// 返回键值对数量
int count() const;

// 返回近似内存占用(不包括对象本身)
size_t approxBytesUsed() const;
```

### 查找操作

```cpp
// 查找键对应的值
// 如果找到返回值的指针,否则返回 nullptr
const V* find(const K& key) const;
```

### 插入操作

```cpp
// 设置键值对
// 如果键已存在,替换旧值
// 返回值的指针(指向哈希表中的副本)
const V* set(K key, V val);
```

### 删除操作

```cpp
// 删除指定键的键值对
// 要求键必须存在(调用者应先 find())
void remove(K key);
```

### 清空操作

```cpp
// 清空哈希表和缓存
void reset();
```

## 内部实现细节

### find() 实现

```cpp
const V* find(const K& key) const {
    // 1. 检查缓存命中
    if (key != fLastKey) {
        // 2. 缓存未命中,查询哈希表
        fLastKey = key;
        fLastValue = fMap.find(key);
    }
    // 3. 返回缓存的值(可能是 nullptr)
    return fLastValue;
}
```

关键点:
- `fLastKey` 和 `fLastValue` 是 `mutable`,允许 `const` 方法修改
- 连续访问同一键时,跳过哈希计算和查找
- 缓存未命中时更新缓存

### set() 实现

```cpp
const V* set(K key, V val) {
    // 1. 检查是否更新现有键
    if (fLastValue && key == fLastKey) {
        // 2. 直接更新缓存的值
        *fLastValue = std::move(val);
    } else {
        // 3. 插入或更新哈希表
        fLastKey = key;
        fLastValue = fMap.set(std::move(key), std::move(val));
    }
    return fLastValue;
}
```

优化点:
- 如果更新的是缓存的键,直接修改值,避免哈希表操作
- 使用移动语义减少拷贝
- 更新缓存指向新插入的值

### remove() 实现

```cpp
void remove(K key) {
    // 调用者必须确保键存在
    SkASSERT(fMap.find(key));

    // 1. 更新缓存键
    fLastKey = std::move(key);

    // 2. 清空缓存值
    fLastValue = nullptr;

    // 3. 从哈希表删除
    fMap.remove(fLastKey);
}
```

注意点:
- 要求键必须存在,否则断言失败
- 清空缓存避免悬挂指针
- 使用移动后的 `fLastKey` 进行删除

### reset() 实现

```cpp
void reset() {
    fLastKey = KeyTraits::GetInvalidKey();
    fLastValue = nullptr;
    fMap.reset();
}
```

- 重置缓存为无效状态
- 清空底层哈希表
- 释放所有内存

### count() 和 approxBytesUsed()

```cpp
int count() const {
    return fMap.count();
}

size_t approxBytesUsed() const {
    return fMap.approxBytesUsed();
}
```

- 直接委托给底层哈希表
- 缓存本身占用的内存可忽略

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkTHash.h` | 底层哈希表实现 |
| `SkChecksum.h` | `GrCheapHash` 的混合函数 |
| `SkNoncopyable` | 禁止拷贝的基类 |
| `SkGoodHash` | 默认哈希函数 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| UniqueID 查找表 | 使用 `GrHashMapWithCache` 优化查找 |
| 纹理代理缓存 | 利用访问局部性 |
| 资源管理器 | 快速查找资源 |

## 设计模式与设计决策

### 设计模式

1. **代理模式 (Proxy/Wrapper)**
   - 包装 `THashMap`,添加缓存层
   - 保持接口相似但语义略有不同

2. **缓存模式 (Cache Pattern)**
   - 单条目缓存(最近访问)
   - 利用时间局部性

3. **策略模式 (Strategy Pattern)**
   - 通过模板参数注入哈希策略
   - 支持自定义哈希函数

### 关键设计决策

1. **为何只缓存一条记录?**
   - 简单高效,无需缓存淘汰策略
   - 针对"连续访问同一键"的场景优化
   - 内存开销仅两个成员变量

2. **为何需要无效键 (InvalidKey)?**
   - 初始化缓存状态
   - 避免误判缓存命中
   - 提供明确的"无缓存"状态

3. **mutable 缓存成员的合理性**
   - 缓存是实现细节,不影响逻辑 const
   - 允许 `find()` 更新缓存
   - 符合 const 的逻辑语义

4. **set() 的缓存优化**
   - 连续更新同一键时避免哈希表操作
   - 减少哈希计算和查找开销
   - 特别适合增量更新场景

5. **remove() 的前提条件**
   - 要求键存在,简化实现
   - 调用者通常先 `find()` 再 `remove()`
   - 避免不必要的存在性检查

6. **GrCheapHash 的使用**
   - UniqueID 已经是良好分布的随机数
   - 不需要复杂的哈希函数
   - 简单混合即可达到良好分布

7. **返回指针而非引用**
   - 支持"未找到"的情况(返回 nullptr)
   - 与 `THashMap` 的接口一致
   - 简化错误处理

## 性能考量

### 缓存命中的优势

```cpp
// 缓存命中: O(1) 简单比较
if (key != fLastKey) { /* 跳过 */ }
return fLastValue;

// 缓存未命中: O(1) 哈希 + O(1) 查找
fLastValue = fMap.find(key);
```

- 缓存命中避免哈希计算
- 避免哈希表查找的开销
- 特别适合循环中的重复访问

### set() 的缓存优化

```cpp
// 更新缓存键: 直接修改值
*fLastValue = std::move(val);

// vs. 更新哈希表: 需要哈希 + 查找 + 更新
fMap.set(key, val);
```

- 连续更新同一键时大幅减少开销
- 适合增量更新的场景

### 内存开销

- 缓存仅占用两个成员变量
- `K` 的大小 + 一个指针
- 对于 UniqueID (uint32_t),仅 12 字节(64位系统)

### 局部性利用

- 针对空间局部性和时间局部性优化
- GPU 资源访问通常有很强的局部性
- 连续帧重复使用同一纹理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkTHash.h` | 依赖 | 底层哈希表 |
| `src/core/SkChecksum.h` | 依赖 | 哈希混合函数 |
| `include/private/base/SkNoncopyable.h` | 基类 | 禁止拷贝 |
| GPU 资源管理模块 | 使用 | UniqueID 查找优化 |
