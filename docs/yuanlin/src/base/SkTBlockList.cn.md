# SkTBlockList

> 源文件: src/base/SkTBlockList.h

## 概述

`SkTBlockList` 是 Skia 中实现的块列表(Block List)容器,是数组和链表的混合体。它以固定大小的内存块为单位分配存储空间,在块内顺序存储元素,块之间通过链表连接。这种设计结合了数组的缓存友好性和链表的动态扩展能力,特别适合需要频繁追加元素且地址稳定性要求高的场景。

该容器保证元素地址在其生命周期内不变(除非调用 concat),支持内联存储优化,并提供了高效的 LIFO(后进先出)操作。模块基于 `SkBlockAllocator` 实现内存管理,自动处理内存分配、释放和对齐。

## 架构位置

```
src/base/
├── SkTBlockList.h       // 块列表容器实现
├── SkBlockAllocator.h   // 底层块分配器
└── (其他基础容器)
    ↓
src/core/
├── SkArenaAlloc.cpp     // 竞技场分配器
└── (需要稳定地址的模块)
    ↓
src/gpu/
└── (GPU 命令缓冲区)     // 使用块列表存储命令
```

该模块是基础容器层的高级组件,为需要高效追加、地址稳定和LIFO操作的场景提供专门的数据结构。

## 主要类与结构体

### SkTBlockList<T, StartingItems>

块列表容器模板类。

**模板参数:**

| 参数 | 说明 |
|------|------|
| T | 元素类型 |
| StartingItems | 内联存储的初始元素数量(默认 1) |

**继承关系:**
- 无继承关系(独立模板类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fAllocator | SkSBlockAllocator<StartingSize> | 块分配器,管理内存块链表 |

### BlockIndexIterator

块列表的迭代器模板,支持前向和反向遍历。

**模板参数包括方向、const性、索引函数等,提供类型安全的迭代。**

## 公共 API 函数

### 构造与配置

| 方法 | 功能说明 |
|------|---------|
| `SkTBlockList()` | 使用默认参数和固定增长策略构造 |
| `explicit SkTBlockList(GrowthPolicy policy)` | 指定增长策略构造 |
| `explicit SkTBlockList(int itemsPerBlock, GrowthPolicy policy)` | 完全自定义构造 |

### 元素操作

| 方法 | 功能说明 |
|------|---------|
| `T& push_back()` | 追加默认构造的元素 |
| `T& push_back(const T& t)` | 追加复制的元素 |
| `T& push_back(T&& t)` | 追加移动的元素 |
| `template <typename... Args> T& emplace_back(Args&&... args)` | 原位构造并追加元素 |
| `void pop_back()` | 移除最后一个元素 |

### 容量管理

| 方法 | 功能说明 |
|------|---------|
| `int count() const` | 获取元素总数 |
| `bool empty() const` | 检查是否为空 |
| `void reserve(int n)` | 预留容量以容纳 n 个额外元素 |
| `void reset()` | 移除所有元素并释放内存 |

### 访问操作

| 方法 | 功能说明 |
|------|---------|
| `T& front()` / `const T& front() const` | 访问第一个元素 |
| `T& back()` / `const T& back() const` | 访问最后一个元素 |
| `T& item(int i)` / `const T& item(int i) const` | 按索引访问元素(非常量时间) |

### 合并操作

| 方法 | 功能说明 |
|------|---------|
| `template <int SI> void concat(SkTBlockList<T, SI>&& other)` | 合并另一个块列表到末尾 |

### 迭代器

| 方法 | 功能说明 |
|------|---------|
| `Iter items()` / `CIter items() const` | 正向迭代(最老到最新) |
| `RIter ritems()` / `CRIter ritems() const` | 反向迭代(最新到最老) |

## 内部实现细节

### 内存布局

**块结构**:
```
Block 1: [metadata | T[0] | T[1] | ... | T[n-1]]
           ↓
Block 2: [metadata | T[n] | T[n+1] | ...]
           ↓
Block 3: ...
```

每个块包含:
- 块元数据(大小、对齐、链表指针)
- 若干个连续存储的 T 类型元素

**内联存储优化**:
```cpp
// StartingItems = 4 时
SkTBlockList<int, 4> list;
// 前 4 个元素存储在对象内部,无堆分配
```

### push_back 实现

```cpp
T& push_back(const T& t) {
    return *new (this->pushItem()) T(t);
}

void* pushItem() {
    auto br = fAllocator->template allocate<alignof(T)>(sizeof(T));
    br.fBlock->setMetadata(br.fAlignedOffset);  // 记录最后元素位置
    fAllocator->setMetadata(fAllocator->metadata() + 1);  // 总数加1
    return br.fBlock->ptr(br.fAlignedOffset);
}
```

**关键步骤**:
1. 从当前块分配 sizeof(T) 字节
2. 如果空间不足,分配新块
3. 在分配的内存上原位构造对象
4. 更新元数据(元素位置和总数)

### pop_back 实现

```cpp
void pop_back() {
    SkBlockAllocator::Block* block = fAllocator->currentBlock();
    int releaseIndex = Last(block);

    GetItem(block, releaseIndex).~T();  // 调用析构函数

    if (releaseIndex == First(block)) {
        fAllocator->releaseBlock(block);  // 块为空,释放整块
    } else {
        block->release(releaseIndex, releaseIndex + sizeof(T));
        block->setMetadata(Decrement(block, releaseIndex));
    }

    fAllocator->setMetadata(fAllocator->metadata() - 1);
}
```

### concat 实现

合并操作分两阶段:
1. **头块元素移动**: 将 other 的头块(内联块)元素移动到当前列表
2. **堆块链接**: 将 other 的堆块链接到当前块链表末尾

```cpp
template <int SI1>
template <int SI2>
void SkTBlockList<T, SI1>::concat(SkTBlockList<T, SI2>&& other) {
    if (other.empty()) return;

    // 处理 other 的头块(内联块)
    SkBlockAllocator::Block* headBlock = other.fAllocator->headBlock();
    if (headBlock->metadata() > 0) {
        // 移动或复制头块的所有元素
        if constexpr (std::is_trivially_copy_constructible<T>::value) {
            // 使用 memcpy 批量复制
        } else {
            // 逐个元素移动构造
        }
    }

    // 链接 other 的堆块
    fAllocator->stealHeapBlocks(other.fAllocator.allocator());
}
```

### item(i) 随机访问

```cpp
T& item(int i) {
    for (auto* b : fAllocator->blocks()) {
        if (b->metadata() == 0) continue;  // 跳过空块

        int start = First(b);
        int end = Last(b) + sizeof(T);
        int index = start + i * sizeof(T);

        if (index < end) {
            return GetItem(b, index);
        } else {
            i -= (end - start) / sizeof(T);  // 减去此块的元素数
        }
    }
    SkUNREACHABLE;
}
```

时间复杂度为 O(块数),因为需要遍历块链表。

### 迭代器实现

迭代器封装了块遍历和块内索引递增的逻辑:
```cpp
Item& operator++() {
    fIndex = Next(block, fIndex);
    if (fIndex > fEndIndex) {
        ++fBlock;  // 移动到下一个块
        this->setIndices();
    }
    return *this;
}
```

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| src/base/SkBlockAllocator.h | 块内存分配器 |
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkDebug.h | 调试宏 |
| include/private/base/SkTo.h | 类型转换工具 |
| src/base/SkTSort.h | (未使用,但包含头文件) |
| type_traits | std::is_trivially_* 类型特征 |
| utility | std::move, std::forward |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/core/SkArenaAlloc.cpp | 竞技场分配器 |
| src/gpu/ops/ | GPU 操作队列 |
| src/core/SkRecorder.cpp | 记录绘制命令 |

## 设计模式与设计决策

### 混合存储策略

结合数组和链表优点:
- **数组特性**: 块内元素连续,缓存友好
- **链表特性**: 块之间链接,动态扩展无需搬移

### 内联存储优化(SSO)

通过模板参数 `StartingItems` 实现小对象优化:
```cpp
SkTBlockList<Command, 16> cmdList;
// 前 16 个命令无堆分配
```

适合大多数情况元素数量较少的场景。

### 地址稳定性保证

一旦元素被添加,其地址不变(除非 concat):
- 不会因为容量扩展而搬移元素
- 可以安全地存储指向元素的指针

### LIFO 优化

push_back 和 pop_back 都是 O(1) 操作:
- 追加总是在当前块末尾
- 删除总是从当前块末尾
- 符合栈(stack)的使用模式

### 类型感知优化

利用类型特征进行优化:
```cpp
if constexpr (std::is_trivially_copy_constructible<T>::value) {
    memcpy(...);  // 平凡类型用 memcpy
} else {
    new (ptr) T(std::move(other));  // 非平凡类型用移动构造
}
```

### 增长策略

支持多种增长策略(通过 SkBlockAllocator::GrowthPolicy):
- `kFixed`: 固定块大小
- `kLinear`: 线性增长
- `kFibonacci`: 斐波那契增长
- `kExponential`: 指数增长

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| push_back() | O(1) 摊销 | 偶尔需要分配新块 |
| pop_back() | O(1) | LIFO 删除 |
| front() | O(1) | 直接访问头块 |
| back() | O(1) | 直接访问尾块 |
| item(i) | O(块数) | 需要遍历块链表 |
| count() | O(1) | 元数据缓存 |
| reset() | O(n) 或 O(块数) | 取决于析构函数 |
| concat() | O(头块元素数) | 堆块链接是 O(1) |
| 迭代 | O(1) per step | 顺序访问每个元素 |

### 空间复杂度

- **元素存储**: n × sizeof(T)
- **块开销**: 块数 × 块元数据大小
- **内联优化**: 首块无额外分配

**内存效率**:
```
块大小 = BlockOverhead + ItemsPerBlock × sizeof(T)
总开销 = 块数 × BlockOverhead
```

### 性能特征

**优势**:
1. **缓存友好**: 块内元素连续存储
2. **无搬移**: 扩容不需要复制现有元素
3. **地址稳定**: 指针保持有效
4. **LIFO 高效**: O(1) push_back 和 pop_back
5. **小对象优化**: 避免小列表的堆分配

**劣势**:
1. **随机访问**: item(i) 是 O(块数)而非 O(1)
2. **内存占用**: 有块元数据开销
3. **插入删除**: 仅支持末尾操作(LIFO)

### 适用场景

- ✅ 频繁追加元素
- ✅ 需要地址稳定性
- ✅ 需要迭代所有元素
- ✅ LIFO(栈)操作模式
- ❌ 频繁随机访问
- ❌ 需要在中间插入删除
- ❌ 需要排序或查找

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| src/base/SkBlockAllocator.h | 底层块分配器 |
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkTo.h | 类型转换 |

## 使用示例

```cpp
// 示例 1: 基本使用
SkTBlockList<int> numbers;
numbers.push_back(1);
numbers.push_back(2);
numbers.push_back(3);

printf("Count: %d\n", numbers.count());  // 3
printf("Back: %d\n", numbers.back());    // 3

// 示例 2: 内联存储优化
SkTBlockList<Point, 8> points;  // 前 8 个点无堆分配
for (int i = 0; i < 8; ++i) {
    points.emplace_back(i, i);
}

// 示例 3: 迭代所有元素
for (const Point& p : points.items()) {
    printf("(%d, %d)\n", p.x, p.y);
}

// 示例 4: 反向迭代
for (Point& p : points.ritems()) {
    p.x *= 2;  // 从最新到最老修改
}

// 示例 5: LIFO 操作(栈行为)
SkTBlockList<Command> commands;
commands.emplace_back(CommandType::Draw, param1);
commands.emplace_back(CommandType::Clear, param2);

while (!commands.empty()) {
    Command& cmd = commands.back();
    executeCommand(cmd);
    commands.pop_back();
}

// 示例 6: 地址稳定性
SkTBlockList<Task> tasks;
Task* task1Ptr = &tasks.emplace_back(Task{1});
tasks.push_back(Task{2});
tasks.push_back(Task{3});
// task1Ptr 仍然有效,地址未改变

// 示例 7: 预留容量
SkTBlockList<int> data;
data.reserve(100);  // 预留空间,减少分配次数
for (int i = 0; i < 100; ++i) {
    data.push_back(i);
}

// 示例 8: 自定义增长策略
SkTBlockList<Record, 4> records(
    32,  // 每块 32 个元素
    SkBlockAllocator::GrowthPolicy::kFibonacci
);

// 示例 9: 合并两个列表
SkTBlockList<int, 4> list1, list2;
list1.push_back(1);
list1.push_back(2);
list2.push_back(3);
list2.push_back(4);

list1.concat(std::move(list2));  // list1: [1,2,3,4], list2: []

// 示例 10: 随机访问(较慢)
for (int i = 0; i < numbers.count(); ++i) {
    printf("%d ", numbers.item(i));  // O(块数) per access
}

// 示例 11: 复杂对象
struct DrawCall {
    SkMatrix matrix;
    SkPaint paint;
    SkPath path;
};

SkTBlockList<DrawCall, 16> drawCalls;
drawCalls.emplace_back(matrix1, paint1, path1);

// 示例 12: 重置和复用
SkTBlockList<TempObject> tempList;
// ... 使用
tempList.reset();  // 清空,内存可复用
// ... 再次使用

// 示例 13: 元素计数验证
SkTBlockList<int> list;
SkASSERT(list.empty());
list.push_back(42);
SkASSERT(!list.empty());
SkASSERT(list.count() == 1);
```

## 注意事项

1. **非随机访问**: item(i) 性能不佳,避免频繁使用
2. **LIFO 限制**: 仅支持末尾操作,不支持中间插入删除
3. **移动语义**: concat 后源列表变为空
4. **地址稳定性**: concat 会移动头块元素,地址可能改变
5. **非线程安全**: 需要外部同步
6. **析构顺序**: reset 按反向顺序(最新到最老)析构元素
7. **类型要求**: T 必须可移动或可复制
8. **块大小**: 过小的块增加开销,过大的块浪费内存

## 与其他容器对比

| 特性 | SkTBlockList | std::vector | std::deque | std::list |
|------|-------------|-------------|------------|-----------|
| 追加 | O(1) 摊销 | O(1) 摊销 | O(1) | O(1) |
| 随机访问 | O(块数) | O(1) | O(1) | O(n) |
| 地址稳定 | ✅ | ❌ | ✅(中间块) | ✅ |
| 缓存友好 | 部分 | ✅ | 部分 | ❌ |
| 内存效率 | 中等 | 高 | 中等 | 低 |
| 中间插入 | ❌ | O(n) | O(n) | O(1) |

## 最佳实践

1. **选择合适的 StartingItems**: 根据常见情况调整,避免频繁堆分配
2. **使用 emplace_back**: 避免不必要的复制或移动
3. **顺序访问**: 优先使用迭代器而非 item(i)
4. **预留容量**: 已知大小时使用 reserve
5. **LIFO 模式**: 利用高效的 push_back/pop_back
6. **避免频繁 concat**: 合并操作有开销,尽量减少
7. **类型选择**: trivially copyable 类型性能更好

## 应用场景

1. **命令缓冲区**: 记录绘制命令序列
2. **事件队列**: LIFO 事件处理
3. **竞技场分配**: 批量分配临时对象
4. **记录回放**: 记录操作历史
5. **构建器模式**: 累积构建数据
6. **日志系统**: 追加日志条目

## 扩展阅读

- 块分配器(Block Allocator)原理
- 小对象优化(Small Object Optimization)
- 内存池技术
- 缓存友好的数据结构设计
- std::deque 实现原理
