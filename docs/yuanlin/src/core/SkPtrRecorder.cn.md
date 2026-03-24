# SkPtrRecorder

> 源文件
> - src/core/SkPtrRecorder.h
> - src/core/SkPtrRecorder.cpp

## 概述

`SkPtrRecorder` 是 Skia 中用于管理指针集合的工具类体系，主要用于序列化和反序列化场景。该模块为每个唯一的指针分配一个 ID（1 到 N），并维护指针与 ID 之间的双向映射关系。重复添加的指针会返回相同的 ID，确保指针的唯一性。

核心功能包括：
- 指针去重和 ID 分配
- 支持引用计数管理（`SkRefCntSet`）
- 工厂函数记录（`SkFactorySet` 和 `SkNamedFactorySet`）
- 支持序列化和反序列化操作

## 架构位置

`SkPtrRecorder` 位于 Skia 核心序列化模块中（`src/core`），是序列化系统的基础组件。

在 Skia 序列化系统中的位置：
```
对象图 → SkPtrRecorder（指针去重） → ID映射 → 序列化流 → 持久化存储
```

主要应用场景：
- **SkPicture 序列化**：记录绘制命令中使用的对象
- **SkFlattenable 序列化**：记录工厂函数以便反序列化
- **资源共享**：避免重复序列化相同对象

## 主要类与结构体

### SkPtrSet

基础的指针集合类，维护指针到 ID 的映射。

**继承关系**
- 继承自 `SkRefCnt`（支持引用计数）

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fList` | `SkTDArray<Pair>` | 存储指针和ID的动态数组（排序） |

**内部结构体 Pair**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fPtr` | `void*` | 指针值（永不为 null） |
| `fIndex` | `uint32_t` | 分配的 ID（1 到 N） |

### SkTPtrSet<T>

模板包装器，提供类型安全的接口。

**继承关系**
- 继承自 `SkPtrSet`

**特点**
- 自动处理类型转换
- 使用模板参数 `T` 提供编译时类型检查

### SkRefCntSet

引用计数管理的指针集合。

**继承关系**
- 继承自 `SkTPtrSet<SkRefCnt*>`

**特点**
- 重写 `incPtr()` 和 `decPtr()` 调用 `ref()` 和 `unref()`
- 自动管理对象生命周期

### SkFactorySet

工厂函数集合，用于记录 `SkFlattenable` 的工厂。

**继承关系**
- 继承自 `SkTPtrSet<SkFlattenable::Factory>`

### SkNamedFactorySet

命名工厂集合，仅支持已注册名称的工厂。

**继承关系**
- 继承自 `SkRefCnt`

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fNextAddedFactory` | `int` | 下一个新增工厂的索引 |
| `fFactorySet` | `SkFactorySet` | 内部工厂集合 |
| `fNames` | `SkTDArray<const char*>` | 工厂名称数组 |

## 公共 API 函数

### SkPtrSet

**查找操作**
```cpp
uint32_t find(void* ptr) const;
```
- 在集合中查找指针
- 返回指针的 ID（1 到 N），未找到或 `nullptr` 返回 0

**添加操作**
```cpp
uint32_t add(void* ptr);
```
- 添加指针到集合
- 重复指针返回已有 ID
- `nullptr` 返回 0

**查询操作**
```cpp
int count() const;
```
- 返回集合中非空指针的数量

**数组导出**
```cpp
void copyToArray(void* array[]) const;
```
- 将指针按 ID 顺序复制到数组
- `array[ptr.ID - 1] = ptr`
- 调用者负责分配内存

**重置操作**
```cpp
void reset();
```
- 对所有指针调用 `decPtr()`
- 清空集合

**迭代器**
```cpp
class Iter {
    Iter(const SkPtrSet& set);
    void* next();
};
```
- 顺序遍历集合中的指针

### SkNamedFactorySet

**查找和添加**
```cpp
uint32_t find(SkFlattenable::Factory factory);
```
- 查找工厂函数
- 如果未在集合中且有注册名称，则添加
- 无注册名称返回 0

**获取新增工厂名**
```cpp
const char* getNextAddedFactoryName();
```
- 返回下一个新增工厂的名称
- 支持增量序列化

## 内部实现细节

### 数据结构

**排序数组**
- `fList` 使用 `SkTDArray` 存储 `Pair` 结构体
- 按指针地址排序（使用 `Less` 比较函数）
- 保持排序状态以支持二分查找

**排序比较器**
```cpp
static bool Less(const Pair& a, const Pair& b) {
    return (char*)a.fPtr < (char*)b.fPtr;
}
```
- 将指针转换为 `char*` 进行比较
- 确保稳定的排序顺序

### 查找算法

使用 `SkTSearch` 进行二分查找：
```cpp
int index = SkTSearch<Pair, Less>(fList.begin(), count, pair, sizeof(pair));
```
- 时间复杂度：O(log n)
- 返回负值表示未找到，`~index` 是插入位置

### 添加算法

1. **查找指针**：使用二分查找定位
2. **已存在**：返回已有的 `fIndex`
3. **不存在**：
   - 调用 `incPtr(ptr)` 增加引用计数
   - 分配新 ID：`count + 1`
   - 在排序位置插入新 `Pair`

### 引用计数管理

**SkRefCntSet 实现**
```cpp
void SkRefCntSet::incPtr(void* ptr) {
    ((SkRefCnt*)ptr)->ref();
}

void SkRefCntSet::decPtr(void* ptr) {
    ((SkRefCnt*)ptr)->unref();
}
```

**生命周期**
- `add()` 时自动 `ref()`
- `reset()` 或析构时自动 `unref()`

### 数组导出逻辑

```cpp
void SkPtrSet::copyToArray(void* array[]) const {
    for (int i = 0; i < count; i++) {
        int index = p[i].fIndex - 1;  // ID 从 1 开始，数组从 0 开始
        array[index] = p[i].fPtr;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数基类 |
| `SkFlattenable` | 可序列化对象和工厂函数 |
| `SkTDArray` | 动态数组容器 |
| `SkTSearch` | 二分查找算法 |
| `SkAssert` | 调试断言 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPicture` | 记录绘制命令中的对象 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化缓冲区 |
| `SkFlattenable` 子类 | 序列化自定义对象 |

## 设计模式与设计决策

### 设计模式

1. **模板方法模式**
   - `SkPtrSet` 定义虚函数 `incPtr()` 和 `decPtr()`
   - 子类（如 `SkRefCntSet`）重写实现具体行为

2. **模板类模式**
   - `SkTPtrSet<T>` 提供类型安全的包装

3. **迭代器模式**
   - `SkPtrSet::Iter` 提供遍历接口

### 设计决策

**为何使用排序数组**
- 支持 O(log n) 查找
- 相比哈希表，内存占用更小
- 支持顺序遍历

**为何 ID 从 1 开始**
- 0 保留为特殊值（未找到或 `nullptr`）
- 与传统数据库主键约定一致

**为何分离 incPtr/decPtr**
- 支持不同的生命周期管理策略
- 基类默认不执行任何操作（仅记录）
- 子类可选择性启用引用计数

**为何禁止 null 指针**
- 简化实现，避免特殊处理
- `nullptr` 在 `find()` 和 `add()` 中统一返回 0

**为何使用指针地址排序**
- 指针地址是唯一标识
- 排序稳定且高效

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `find()` | O(log n) | 二分查找 |
| `add()` | O(n) | 查找 O(log n) + 插入 O(n) |
| `copyToArray()` | O(n) | 线性遍历 |
| `reset()` | O(n) | 调用每个指针的 `decPtr()` |

### 空间复杂度

- 每个指针占用 `sizeof(Pair)` = `sizeof(void*) + sizeof(uint32_t)`
- 排序数组无额外空间开销

### 优化建议

1. **批量添加**
   - 尽量一次性添加所有指针，减少插入开销

2. **避免频繁查找**
   - 缓存已查找的 ID

3. **重用实例**
   - 使用 `reset()` 清空后重用对象

### 性能陷阱

- **插入开销**：每次 `add()` 新指针需要移动数组元素（O(n)）
- **内存分配**：`SkTDArray` 动态扩容可能触发重新分配

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkRefCnt.h` | 依赖 | 引用计数基类 |
| `include/core/SkFlattenable.h` | 依赖 | 工厂函数类型 |
| `include/private/base/SkTDArray.h` | 依赖 | 动态数组容器 |
| `src/base/SkTSearch.h` | 依赖 | 二分查找算法 |
| `src/core/SkReadBuffer.h` | 使用者 | 反序列化时使用 |
| `src/core/SkWriteBuffer.h` | 使用者 | 序列化时使用 |
| `src/core/SkPictureRecord.cpp` | 使用者 | 记录绘制命令 |
