# SkMetaData

> 源文件：tools/SkMetaData.h, tools/SkMetaData.cpp

## 概述

`SkMetaData` 是 Skia 工具库中实现的一个轻量级键值对容器类，用于存储和管理类型化的元数据。它提供了从 C 字符串键到 POD（Plain Old Data）类型值数组的映射功能，支持四种基本数据类型：`int32_t`、`SkScalar`、`void*` 和 `bool`。该类采用单链表实现，提供简单高效的插入、查询、删除和迭代操作，常用于在 Skia 对象之间传递附加的元数据信息。

## 架构位置

`SkMetaData` 在 Skia 架构中的位置：

- 位于 `tools/` 目录，属于工具辅助类
- 独立的数据结构，无继承关系
- 使用单链表存储键值对记录
- 支持类型安全的数据访问
- 提供迭代器接口遍历所有条目
- 禁用拷贝构造和赋值操作（RAII 风格）

该类主要用于测试工具和示例程序中，为 Skia 对象附加调试信息或配置参数。

## 主要类与结构体

### SkMetaData 类

**核心成员变量**：
```cpp
Rec* fRec = nullptr;  // 记录链表的头节点
```

**公共方法 - 查询**：
```cpp
bool findS32(const char name[], int32_t* value = nullptr) const;
bool findScalar(const char name[], SkScalar* value = nullptr) const;
const SkScalar* findScalars(const char name[], int* count, SkScalar values[] = nullptr) const;
bool findPtr(const char name[], void** value = nullptr) const;
bool findBool(const char name[], bool* value = nullptr) const;

bool hasS32(const char name[], int32_t value) const;
bool hasScalar(const char name[], SkScalar value) const;
bool hasPtr(const char name[], void* value) const;
bool hasBool(const char name[], bool value) const;
```

**公共方法 - 设置**：
```cpp
void setS32(const char name[], int32_t value);
void setScalar(const char name[], SkScalar value);
SkScalar* setScalars(const char name[], int count, const SkScalar values[] = nullptr);
void setPtr(const char name[], void* value);
void setBool(const char name[], bool value);
```

**公共方法 - 删除**：
```cpp
bool removeS32(const char name[]);
bool removeScalar(const char name[]);
bool removePtr(const char name[]);
bool removeBool(const char name[]);
void reset();  // 删除所有条目
```

### Rec 结构体

存储单个键值对的记录：
```cpp
struct Rec {
    Rec* fNext;              // 链表下一节点
    uint16_t fDataCount;     // 元素数量
    uint8_t fDataLen;        // 单个元素字节数
    uint8_t fType;           // 类型标识

    const void* data() const;  // 数据指针
    const char* name() const;  // 键名指针

    static Rec* Alloc(size_t);
    static void Free(Rec*);
};
```

**内存布局**：
```
+--------+----------+---------+
| Rec    | Data     | Name    |
| header | (values) | (string)|
+--------+----------+---------+
```

### Type 枚举

四种支持的数据类型：
```cpp
enum Type {
    kS32_Type,      // int32_t
    kScalar_Type,   // SkScalar (float)
    kPtr_Type,      // void*
    kBool_Type,     // bool
    kTypeCount
};
```

### Iter 迭代器类

遍历所有键值对：
```cpp
class Iter {
public:
    Iter(const SkMetaData&);
    void reset(const SkMetaData&);
    const char* next(Type*, int* count);
};
```

### FindResult 结构体

内部查找结果，包含目标节点和前驱节点：
```cpp
struct FindResult {
    SkMetaData::Rec* rec;   // 找到的记录
    SkMetaData::Rec* prev;  // 前驱记录（用于删除）
};
```

## 公共 API 函数

### 构造与析构

**SkMetaData()**
```cpp
SkMetaData()
```
默认构造，初始化空链表。

**~SkMetaData()**
```cpp
~SkMetaData()
```
析构时自动调用 `reset()` 释放所有记录。

**reset()**
```cpp
void reset()
```
删除所有键值对，释放内存。

### 查询方法

所有 `find` 方法返回 `bool` 表示是否找到，可选的输出参数用于获取值。

**findS32()**
- **功能**：查找 `int32_t` 类型的值
- **返回值**：找到返回 `true`

**findScalar()**
- **功能**：查找单个 `SkScalar` 值
- **返回值**：找到返回 `true`

**findScalars()**
- **功能**：查找 `SkScalar` 数组
- **参数**：
  - `count`: 输出数组长度
  - `values`: 可选的缓冲区，复制数据
- **返回值**：数组指针，未找到返回 `nullptr`

**findPtr()**
- **功能**：查找 `void*` 指针
- **返回值**：找到返回 `true`

**findBool()**
- **功能**：查找 `bool` 值
- **返回值**：找到返回 `true`

### 便捷查询方法

**hasS32() / hasScalar() / hasPtr() / hasBool()**
- **功能**：检查键是否存在且值匹配
- **返回值**：键存在且值相等返回 `true`
- **实现**：内部调用对应的 `find` 方法并比较值

### 设置方法

**setS32() / setScalar() / setPtr() / setBool()**
- **功能**：设置单个值
- **行为**：如果键已存在，更新值；否则创建新条目

**setScalars()**
```cpp
SkScalar* setScalars(const char name[], int count, const SkScalar values[] = nullptr)
```
- **功能**：设置 `SkScalar` 数组
- **参数**：
  - `count`: 数组长度（必须 > 0）
  - `values`: 源数据，可为 `nullptr`（仅分配空间）
- **返回值**：数组的可写指针

### 删除方法

**removeS32() / removeScalar() / removePtr() / removeBool()**
- **功能**：删除指定键的条目
- **返回值**：成功删除返回 `true`，未找到返回 `false`

## 内部实现细节

### 单链表结构

链表存储所有记录，新条目插入头部（O(1) 插入）：
```
fRec -> [Rec 1] -> [Rec 2] -> [Rec 3] -> nullptr
```

### 内存分配策略

**Rec::Alloc()**
```cpp
static Rec* Alloc(size_t size) {
    return (Rec*)sk_malloc_throw(size);
}
```
- 分配连续内存：记录头 + 数据 + 键名
- 使用 Skia 的内存分配器（失败时抛异常）

**内存布局示例**（setS32("width", 100)）：
```
+----------------+-------+----------+
| Rec header     | 100   | "width\0"|
| (8 bytes)      | (4B)  | (6 bytes)|
+----------------+-------+----------+
```

### 查找实现

**findWithPrev()**
```cpp
FindResult findWithPrev(const char name[], Type type) const
```
- 遍历链表查找匹配的键名和类型
- 同时记录前驱节点（用于删除）
- O(n) 时间复杂度

**find()**
```cpp
const Rec* find(const char name[], Type type) const
```
简化版，仅返回记录指针。

### 设置实现

**set()** 方法的复杂逻辑：

```cpp
void* set(const char name[], const void* data, size_t dataSize, Type type, int count)
```

**优化策略 - 重用记录**：
```cpp
bool reuseRec = result.rec &&
                result.rec->fDataLen == dataSize &&
                result.rec->fDataCount == count;
```
如果找到同名同类型的记录，且数据大小相同，则重用记录（避免重新分配）。

**三种情况处理**：
1. **重用**：直接覆写数据
2. **替换**：删除旧记录，插入新记录
3. **新增**：插入到链表头部

**延迟删除**：
```cpp
// Delayed removal since name or data may have been in the result.rec.
this->remove(result);
```
防止在使用参数后才删除旧记录，避免悬空指针。

### 删除实现

**remove(FindResult)**
```cpp
void remove(FindResult result)
```
- 使用前驱节点更新链表指针
- 释放记录内存

**链表删除逻辑**：
```cpp
if (result.prev) {
    result.prev->fNext = result.rec->fNext;  // 中间节点
} else {
    fRec = result.rec->fNext;  // 头节点
}
```

### 迭代器实现

**Iter::next()**
```cpp
const char* next(SkMetaData::Type* t, int* count)
```
- 返回当前节点的键名
- 可选输出类型和元素计数
- 移动到下一节点
- 返回 `nullptr` 表示遍历结束

## 依赖关系

**Skia 核心依赖**：
- `include/core/SkScalar.h` - 浮点数类型定义
- `include/private/base/SkMalloc.h` - 内存分配器
- `include/private/base/SkTo.h` - 类型转换工具

**标准库依赖**：
- `<cstring>` - `strcmp`, `memcpy`, `strlen`

## 设计模式与设计决策

### 类型安全的泛型容器
通过枚举类型和函数重载实现类型安全，避免使用模板。

### RAII 资源管理
析构函数自动清理所有内存，无需手动释放。

### 迭代器模式
提供 `Iter` 类遍历所有条目，隐藏内部链表结构。

### 延迟删除策略
避免在使用参数过程中删除旧记录，防止悬空指针。

### 关键设计决策

**1. 禁用拷贝**
```cpp
SkMetaData(const SkMetaData&) = delete;
SkMetaData& operator=(const SkMetaData&) = delete;
```
防止意外的深拷贝，明确所有权语义。

**2. 支持数组**
`setScalars()` 和 `findScalars()` 支持存储数组，其他类型仅单值。

**3. 空间优化**
使用 `uint16_t` 和 `uint8_t` 减少记录头大小（8 字节）。

**4. 连续内存布局**
记录头、数据和键名连续存储，提高缓存友好性。

**5. 简单的链表**
使用单链表而非哈希表，适合少量条目的场景。

**6. 内联辅助函数**
`name()` 和 `data()` 通过指针算术内联访问数据。

## 性能考量

### 时间复杂度

- **查找**：O(n) - 线性搜索链表
- **插入**：O(n) - 需先查找是否存在
- **删除**：O(n) - 需查找目标节点
- **迭代**：O(n) - 遍历所有节点

### 内存开销

**每个记录**：
- 记录头：8 字节（指针 + 3 个字段）
- 数据：`dataSize × count`
- 键名：`strlen(name) + 1`
- 总计：约 8 + 数据大小 + 键名长度

**示例**：
- `setS32("x", 10)`：8 + 4 + 2 = 14 字节
- `setScalars("points", 10, ...)`：8 + 40 + 7 = 55 字节

### 优化特性

**记录重用**：
```cpp
bool reuseRec = result.rec && ...
```
相同大小的数据更新时重用记录，避免重新分配。

**头部插入**：
新记录插入链表头部，O(1) 操作。

### 性能限制

**不适合大量数据**：
- 线性搜索不适合大量键值对
- 无哈希表的 O(1) 查找优势

**无缓存**：
- 每次查找都遍历链表
- 可考虑缓存最近访问的节点

### 适用场景

**最佳使用场景**：
- 少量元数据（< 10 个键）
- 不频繁访问
- 测试和调试工具

**不适合场景**：
- 大量键值对（考虑 `SkTHashMap`）
- 频繁查询（考虑哈希表）
- 需要排序或范围查询

## 相关文件

**使用示例**：
- `tools/` 目录下的各种测试工具
- 示例程序中附加配置参数

**替代方案**：
- `include/private/base/SkTHashMap.h` - 哈希表容器
- `std::map` - 标准库有序映射
- `std::unordered_map` - 标准库哈希映射

**内存管理**：
- `include/private/base/SkMalloc.h` - Skia 内存分配器
- `include/private/base/SkTo.h` - 安全类型转换

**测试文件**：
- `tests/` 目录下可能存在的元数据测试（需确认）

**历史来源**：
- 版权标注为 2006 年 Android Open Source Project
- 早期用于 Android 框架中的元数据存储
