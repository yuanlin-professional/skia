# SkTInternalLList

> 源文件: src/base/SkTInternalLList.h

## 概述

`SkTInternalLList` 是 Skia 中实现侵入式双向链表(Intrusive Doubly Linked List)的模板类。与标准的链表实现不同,侵入式链表将链表节点的指针直接嵌入到元素对象本身,而不是将元素包装在独立的节点结构中。这种设计消除了额外的内存分配,提供了更高的性能和更好的缓存局部性。

该模块提供了双向链表的所有基本操作,包括头尾插入、任意位置插入、删除、合并等功能,并在 Debug 模式下提供完整的链表完整性验证机制。

## 架构位置

```
src/base/
├── SkTInternalLList.h   // 侵入式双向链表实现
└── (其他基础容器)
    ↓
src/gpu/
├── GrResourceCache.cpp  // GPU 资源缓存管理
└── (GPU 对象池管理)
    ↓
src/core/
└── (需要高效链表的模块)
```

该模块是基础容器层的重要组件,特别适合需要频繁插入删除且对性能敏感的场景,如资源缓存、对象池和LRU缓存。

## 主要类与结构体

### SkTInternalLList<T>

侵入式双向链表容器类。

**继承关系:**
- 无继承关系(独立模板类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fHead | T* | 指向链表头节点的指针 |
| fTail | T* | 指向链表尾节点的指针 |

### 嵌入式节点字段

元素类型 T 必须包含以下字段(通过宏定义):

| 字段 | 类型 | 说明 |
|------|------|------|
| fPrev | ClassName* | 指向前一个节点 |
| fNext | ClassName* | 指向下一个节点 |
| fList | SkTInternalLList<ClassName>* | (Debug) 指向所属链表 |

### SkTInternalLList<T>::Iter

链表迭代器类,支持前向和后向遍历。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fCurr | T* | 当前迭代位置 |

## 公共 API 函数

### 基本操作

| 方法 | 功能说明 |
|------|---------|
| `SkTInternalLList()` | 构造空链表 |
| `void reset()` | 清空链表(不释放元素) |
| `bool isEmpty() const` | 检查链表是否为空 |
| `T* head() const` | 获取头节点 |
| `T* tail() const` | 获取尾节点 |

### 插入操作

| 方法 | 功能说明 |
|------|---------|
| `void addToHead(T* entry)` | 在链表头部插入元素 |
| `void addToTail(T* entry)` | 在链表尾部插入元素 |
| `void addBefore(T* newEntry, T* existingEntry)` | 在指定元素之前插入 |
| `void addAfter(T* newEntry, T* existingEntry)` | 在指定元素之后插入 |

### 删除操作

| 方法 | 功能说明 |
|------|---------|
| `void remove(T* entry)` | 从链表中删除指定元素 |

### 合并操作

| 方法 | 功能说明 |
|------|---------|
| `void concat(SkTInternalLList&& list)` | 将另一个链表连接到当前链表末尾 |

### 调试功能

| 方法 | 功能说明 |
|------|---------|
| `void validate() const` | 验证链表完整性(Debug 模式) |
| `bool isInList(const T* entry) const` | 检查元素是否在链表中(Debug) |
| `int countEntries() const` | 计算链表元素数量(Debug) |

### 迭代器操作

| 方法 | 功能说明 |
|------|---------|
| `Iter begin() const` | 获取指向头部的迭代器 |
| `Iter end() const` | 获取结束迭代器 |
| `T* Iter::init(const SkTInternalLList& list, IterStart startLoc)` | 初始化迭代器 |
| `T* Iter::get()` | 获取当前元素 |
| `T* Iter::next()` | 移动到下一个元素 |
| `T* Iter::prev()` | 移动到上一个元素 |

## 内部实现细节

### 侵入式设计

元素类必须使用宏声明链表接口:
```cpp
class MyObject {
private:
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(MyObject);
    // 展开为:
    // friend class SkTInternalLList<MyObject>;
    // SkDEBUGCODE(SkTInternalLList<MyObject>* fList = nullptr;)
    // MyObject* fPrev = nullptr;
    // MyObject* fNext = nullptr;
};
```

这种设计使链表指针直接嵌入对象,而不需要额外的节点结构。

### 插入操作实现

**头部插入**:
```cpp
void addToHead(T* entry) {
    SkASSERT(nullptr == entry->fPrev && nullptr == entry->fNext);
    entry->fPrev = nullptr;
    entry->fNext = fHead;
    if (fHead) {
        fHead->fPrev = entry;
    }
    fHead = entry;
    if (nullptr == fTail) {
        fTail = entry;
    }
    entry->fList = this;  // Debug 模式
}
```

**关键步骤**:
1. 断言检查元素未在其他链表中
2. 设置新元素的前后指针
3. 更新原头节点的 prev 指针
4. 更新链表的 head 指针
5. 如果链表原本为空,更新 tail 指针

### 删除操作实现

```cpp
void remove(T* entry) {
    SkASSERT(fHead && fTail);
    SkASSERT(this->isInList(entry));

    T* prev = entry->fPrev;
    T* next = entry->fNext;

    if (prev) {
        prev->fNext = next;
    } else {
        fHead = next;  // 删除的是头节点
    }

    if (next) {
        next->fPrev = prev;
    } else {
        fTail = prev;  // 删除的是尾节点
    }

    entry->fPrev = nullptr;
    entry->fNext = nullptr;
    entry->fList = nullptr;  // Debug
}
```

### 合并操作实现

```cpp
void concat(SkTInternalLList&& list) {
    if (list.isEmpty()) {
        return;
    }

    list.fHead->fPrev = fTail;
    if (!fHead) {
        fHead = list.fHead;
    } else {
        fTail->fNext = list.fHead;
    }
    fTail = list.fTail;

#ifdef SK_DEBUG
    for (T* node = list.fHead; node; node = node->fNext) {
        node->fList = this;  // 更新所有权
    }
#endif

    list.fHead = list.fTail = nullptr;
}
```

### 迭代器实现

迭代器支持 C++11 range-for 循环:
```cpp
class Iter {
    bool operator!=(const Iter& that) const {
        return fCurr != that.fCurr;
    }
    T* operator*() { return this->get(); }
    void operator++() { this->next(); }
};

// 使用示例
for (T* item : list) {
    // 处理 item
}
```

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkDebug.h | 调试宏 |
| include/private/base/SkTo.h | SkToBool 工具 |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/gpu/GrResourceCache.cpp | GPU 资源的 LRU 缓存 |
| src/gpu/GrGpuResource.cpp | GPU 对象链表管理 |
| src/core/SkGlyphRunPainter.cpp | 字形运行链表 |

## 设计模式与设计决策

### 侵入式设计

**优点**:
- 零额外内存分配(节点指针嵌入对象)
- 更好的缓存局部性(数据和指针在一起)
- 删除操作只需 O(1) 时间(无需查找节点)
- 避免内存碎片化

**缺点**:
- 侵入性(元素类必须包含链表字段)
- 元素只能属于一个链表(除非多组指针)
- 需要宏辅助声明

### 友元模式

使用 `friend class` 允许链表访问元素的私有字段:
```cpp
class MyObject {
private:
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(MyObject);
    // friend 允许 SkTInternalLList 访问 fPrev/fNext
};
```

### Debug 所有权跟踪

Debug 模式下,每个元素存储所属链表指针:
- 检测元素是否已在其他链表中
- 验证 remove 操作的合法性
- 帮助调试悬垂指针问题

### RAII 资源管理

虽然链表不拥有元素,但通过移动语义支持链表转移:
```cpp
SkTInternalLList<T> list2 = std::move(list1);  // 不支持
// 但 concat 使用右值引用实现高效合并
list1.concat(std::move(list2));
```

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| addToHead() | O(1) | 常量时间插入 |
| addToTail() | O(1) | 常量时间插入 |
| addBefore() | O(1) | 需要已知位置 |
| addAfter() | O(1) | 需要已知位置 |
| remove() | O(1) | 需要元素指针 |
| concat() | O(1) 或 O(n) | Release O(1), Debug O(n)(更新所有权) |
| isEmpty() | O(1) | 检查头指针 |
| head() / tail() | O(1) | 直接访问 |

### 空间复杂度

- **元素开销**: 2 个指针(16 或 32 字节),Debug 模式下额外 1 个指针
- **链表开销**: 2 个指针(head 和 tail)
- **无额外节点**: 相比标准链表节省内存

### 性能优势

1. **无内存分配**: 插入删除不需要 malloc/free
2. **缓存友好**: 元素和链表指针在同一缓存行
3. **O(1) 删除**: 已知元素指针时无需查找
4. **O(1) 合并**: 链表拼接只需指针操作

### 性能陷阱

1. **随机访问**: 不支持 O(1) 的索引访问,需要 O(n) 遍历
2. **查找操作**: 需要 O(n) 线性查找
3. **内存占用**: 每个元素都有链表开销,即使不在链表中

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkDebug.h | 调试宏 |
| include/private/base/SkTo.h | 类型转换工具 |
| src/gpu/GrResourceCache.h | 使用链表管理缓存 |

## 使用示例

```cpp
// 示例 1: 定义可链表化的类
class Task {
public:
    Task(int priority) : fPriority(priority) {}
    int getPriority() const { return fPriority; }

private:
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(Task);
    int fPriority;
};

// 示例 2: 创建和使用链表
SkTInternalLList<Task> taskList;

Task* task1 = new Task(1);
Task* task2 = new Task(2);
Task* task3 = new Task(3);

taskList.addToHead(task1);
taskList.addToTail(task3);
taskList.addAfter(task2, task1);

// 示例 3: 遍历链表
for (Task* task = taskList.head(); task; task = task->fNext) {
    printf("Task priority: %d\n", task->getPriority());
}

// 示例 4: 使用迭代器
SkTInternalLList<Task>::Iter iter;
for (Task* task = iter.init(taskList, Iter::kHead_IterStart);
     task; task = iter.next()) {
    processTask(task);
}

// 示例 5: 使用 range-for
for (Task* task : taskList) {
    task->execute();
}

// 示例 6: 删除元素
if (!taskList.isEmpty()) {
    Task* first = taskList.head();
    taskList.remove(first);
    delete first;
}

// 示例 7: 在指定位置插入
Task* newTask = new Task(0);
Task* current = taskList.head();
while (current && current->getPriority() < newTask->getPriority()) {
    current = current->fNext;
}
if (current) {
    taskList.addBefore(newTask, current);
} else {
    taskList.addToTail(newTask);
}

// 示例 8: 合并两个链表
SkTInternalLList<Task> list1, list2;
// ... 填充链表
list1.concat(std::move(list2));  // list2 变为空

// 示例 9: 清空链表并释放内存
while (!taskList.isEmpty()) {
    Task* task = taskList.head();
    taskList.remove(task);
    delete task;
}

// 示例 10: LRU 缓存实现
class CacheEntry {
public:
    CacheEntry(int key, int value) : fKey(key), fValue(value) {}
    int key() const { return fKey; }
    int value() const { return fValue; }

private:
    SK_DECLARE_INTERNAL_LLIST_INTERFACE(CacheEntry);
    int fKey;
    int fValue;
};

class LRUCache {
public:
    void access(CacheEntry* entry) {
        if (entry->fList == &fList) {
            fList.remove(entry);
        }
        fList.addToHead(entry);  // 最近使用的放到头部
    }

    CacheEntry* evict() {
        if (fList.isEmpty()) return nullptr;
        CacheEntry* lru = fList.tail();  // 尾部是最久未使用的
        fList.remove(lru);
        return lru;
    }

private:
    SkTInternalLList<CacheEntry> fList;
};

// 示例 11: 双向遍历
SkTInternalLList<Task>::Iter iter;
for (Task* task = iter.init(taskList, Iter::kTail_IterStart);
     task; task = iter.prev()) {
    // 从尾到头遍历
}
```

## 注意事项

1. **元素所有权**: 链表不拥有元素,需要手动管理内存
2. **单一所属**: 元素同时只能属于一个链表
3. **指针有效性**: 删除元素后必须确保没有悬垂指针
4. **线程安全**: 非线程安全,需要外部同步
5. **宏使用**: 必须在类的 private 部分使用宏
6. **Debug 检查**: Debug 模式下会进行大量检查,影响性能
7. **移动语义**: 不支持标准的移动构造/赋值,使用 concat 替代
8. **迭代器失效**: 删除元素会使指向该元素的迭代器失效

## 与标准容器对比

| 特性 | SkTInternalLList | std::list |
|------|-----------------|-----------|
| 内存分配 | 零额外分配 | 每个元素分配节点 |
| 删除复杂度 | O(1)(已知指针) | O(1)(已知迭代器) |
| 元素所有权 | 不拥有 | 拥有(值语义) |
| 侵入性 | 侵入式 | 非侵入式 |
| 元素可重用性 | 一个链表 | 可在多个容器 |
| 标准库 | 否 | 是 |
| 迭代器稳定性 | 删除失效 | 删除失效 |

## 最佳实践

1. **适用场景**: LRU 缓存、对象池、频繁插入删除的场景
2. **内存管理**: 使用智能指针或明确的所有权策略
3. **初始化**: 确保元素的 fPrev/fNext 初始化为 nullptr
4. **验证**: Debug 模式下定期调用 validate()
5. **迭代器安全**: 不要在遍历过程中删除当前元素(使用 next/prev 提前保存)
6. **性能测试**: 对比标准容器,确认性能提升
7. **文档化**: 明确标注类使用了侵入式链表

## 扩展阅读

- 侵入式容器设计原理
- Boost.Intrusive 库
- 内核链表(Linux kernel list.h)
- LRU 缓存实现技术
- 缓存友好的数据结构设计
