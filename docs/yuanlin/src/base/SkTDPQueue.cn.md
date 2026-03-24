# SkTDPQueue

> 源文件: src/base/SkTDPQueue.h

## 概述

`SkTDPQueue` 是 Skia 中实现优先级队列(Priority Queue)的模板类,基于二叉堆(binary heap)数据结构实现。它提供了高效的插入、删除和访问最高优先级元素的操作,支持自定义比较函数来定义优先级顺序。该类还可选地支持随机删除和优先级动态调整功能。

优先级队列是许多算法的核心数据结构,如 Dijkstra 最短路径算法、A* 寻路、任务调度和事件驱动系统。`SkTDPQueue` 为 Skia 内部的图形算法提供了高效的优先级管理能力。

## 架构位置

```
src/base/
├── SkTDPQueue.h         // 优先级队列实现
├── SkTSort.h            // 排序算法(用于 sort 方法)
└── (其他基础容器)
    ↓
src/gpu/
├── GrPathRendering.cpp  // 路径渲染调度
└── (GPU 资源管理)       // 使用优先级队列管理资源
```

该模块是基础容器层的重要组件,为上层算法提供优先级管理能力,特别是在需要按优先级处理任务的场景中。

## 主要类与结构体

### SkTDPQueue<T, LESS, INDEX>

基于二叉堆的优先级队列模板类。

**模板参数:**

| 参数 | 说明 |
|------|------|
| T | 元素类型 |
| LESS | 比较函数:`bool (*)(const T&, const T&)`,返回 true 表示第一个参数优先级更高 |
| INDEX | 索引函数:`int* (*)(const T&)`,返回元素的索引指针,用于支持随机删除和优先级调整 |

**继承关系:**
- 无继承关系(独立模板类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fArray | SkTDArray<T> | 存储堆元素的动态数组 |

## 公共 API 函数

### 构造与容量管理

| 方法 | 功能说明 |
|------|---------|
| `SkTDPQueue()` | 默认构造空队列 |
| `SkTDPQueue(int reserve)` | 预留指定容量的队列 |
| `int count() const` | 获取队列中的元素数量 |

### 优先级操作

| 方法 | 功能说明 |
|------|---------|
| `const T& peek() const` / `T& peek()` | 获取最高优先级元素(不移除) |
| `void pop()` | 移除最高优先级元素 |
| `void insert(T entry)` | 插入新元素到队列 |

### 高级操作(需要 INDEX 函数)

| 方法 | 功能说明 |
|------|---------|
| `void remove(T entry)` | 随机删除指定元素 |
| `void priorityDidChange(T entry)` | 通知队列某元素的优先级已改变 |

### 辅助操作

| 方法 | 功能说明 |
|------|---------|
| `T at(int i) const` | 获取索引 i 处的元素(非优先级顺序) |
| `void sort()` | 将队列排序为优先级顺序 |

## 内部实现细节

### 二叉堆结构

队列使用一维数组表示完全二叉树,索引映射关系:
```cpp
LeftOf(int x)   { return 2 * x + 1; }  // 左子节点
RightOf(int x)  { return 2 * x + 2; }  // 右子节点(隐式)
ParentOf(int x) { return (x - 1) >> 1; }  // 父节点
```

**堆性质**: 父节点的优先级总是高于或等于子节点(`LESS(parent, child)` 为 false)。

### 插入操作(上浮)

```cpp
void insert(T entry) {
    int index = fArray.size();
    *fArray.append() = entry;
    this->setIndex(fArray.size() - 1);
    this->percolateUpIfNecessary(index);  // 上浮调整
}
```

**上浮过程**:
1. 将新元素添加到数组末尾
2. 与父节点比较,如果优先级更高则交换
3. 重复直到满足堆性质或到达根节点

### 删除操作(下沉)

```cpp
void pop() {
    fArray[0] = fArray[fArray.size() - 1];  // 用最后元素替换根
    fArray.pop_back();
    this->percolateDownIfNecessary(0);  // 下沉调整
}
```

**下沉过程**:
1. 将根节点与最后一个元素交换
2. 删除最后一个元素
3. 新根节点与较高优先级的子节点比较并交换
4. 重复直到满足堆性质或到达叶节点

### 索引跟踪机制

当提供 `INDEX` 函数时,队列会维护元素的索引:
```cpp
void setIndex(int index) {
    if (SkToBool(INDEX)) {
        *INDEX(fArray[index]) = index;  // 更新元素的索引
    }
}
```

这使得随机删除和优先级调整的时间复杂度为 O(log n)。

### 优先级调整

```cpp
void priorityDidChange(T entry) {
    int index = *INDEX(entry);
    this->percolateUpOrDown(index);  // 可能上浮或下沉
}
```

首先尝试上浮,如果不需要上浮则尝试下沉。

### 随机删除

```cpp
void remove(T entry) {
    int index = *INDEX(entry);
    fArray[index] = fArray[fArray.size() - 1];
    fArray.pop_back();
    this->setIndex(index);
    this->percolateUpOrDown(index);  // 调整堆
}
```

类似于 `pop`,但删除的是中间元素。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| include/private/base/SkTDArray.h | 动态数组存储 |
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkDebug.h | 调试宏 |
| include/private/base/SkTo.h | 类型转换工具 |
| src/base/SkTSort.h | 排序算法 |
| utility | std::swap |

**被依赖的模块:**

| 模块 | 使用场景 |
|------|---------|
| src/gpu/ganesh/ | GPU 资源调度 |
| src/pathops/ | 路径操作算法 |
| src/core/ | 核心图形算法 |

## 设计模式与设计决策

### 模板策略模式

通过模板参数 `LESS` 注入比较策略:
```cpp
template <typename T, bool (*LESS)(const T&, const T&)>
class SkTDPQueue { ... };
```

这使得队列可以支持任意类型和任意优先级定义,而无需运行时多态开销。

### 可选功能设计

`INDEX` 参数是可选的:
- **nullptr**: 仅支持基本的 peek/pop/insert 操作
- **非 nullptr**: 支持 remove 和 priorityDidChange

这种设计避免了不必要的内存和计算开销。

### 索引维护模式

要求元素自己存储索引:
```cpp
struct Task {
    int priority;
    int heapIndex;  // 由队列维护
};

int* getIndex(const Task& t) { return &t.heapIndex; }
```

这是一种侵入式设计,但避免了额外的索引映射表。

### 验证机制

Debug 模式下提供堆性质验证:
```cpp
void validate(int excludedIndex = -1) const {
#ifdef SK_DEBUG
    for (int i = 1; i < fArray.size(); ++i) {
        int p = ParentOf(i);
        SkASSERT(!(LESS(fArray[i], fArray[p])));
    }
#endif
}
```

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| peek() | O(1) | 直接访问数组首元素 |
| pop() | O(log n) | 下沉操作最多 log n 次比较 |
| insert() | O(log n) | 上浮操作最多 log n 次比较 |
| remove() | O(log n) | 需要 INDEX,删除后调整堆 |
| priorityDidChange() | O(log n) | 需要 INDEX,重新调整位置 |
| at() | O(1) | 直接数组访问 |
| sort() | O(n log n) | 使用快速排序 |

### 空间复杂度

- **基本版本**: O(n),仅存储元素
- **带 INDEX 版本**: O(n),元素自身存储索引,无额外开销

### 性能优化技术

1. **位运算**: 使用移位代替乘除法
   ```cpp
   LeftOf(x)   = 2 * x + 1  =>  (x << 1) + 1
   ParentOf(x) = (x - 1) / 2  =>  (x - 1) >> 1
   ```

2. **原地调整**: 上浮和下沉都在原数组中进行,无额外分配

3. **预留容量**: 构造函数支持预留容量,减少动态扩容

4. **索引缓存**: 避免重复调用 INDEX 函数

5. **短路优化**: 上浮/下沉过程中尽早退出

### 性能陷阱

1. **频繁 priorityDidChange**: 如果优先级频繁变化,考虑重新设计数据结构
2. **大量随机删除**: 可能导致堆频繁重构,考虑标记删除
3. **排序后操作**: `sort()` 后的队列在下次操作时可能失去排序状态

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/private/base/SkTDArray.h | 底层存储容器 |
| src/base/SkTSort.h | 提供排序功能 |
| include/private/base/SkAssert.h | 断言宏 |
| include/private/base/SkTo.h | 类型转换工具 |

## 使用示例

```cpp
// 示例 1: 基本优先级队列(无索引跟踪)
struct Task {
    int priority;
    const char* name;
};

bool taskLess(const Task& a, const Task& b) {
    return a.priority < b.priority;  // 数字越小优先级越高
}

SkTDPQueue<Task, taskLess> queue;
queue.insert({10, "Low priority"});
queue.insert({1, "High priority"});
queue.insert({5, "Medium priority"});

while (queue.count() > 0) {
    Task t = queue.peek();
    printf("Processing: %s\n", t.name);  // High -> Medium -> Low
    queue.pop();
}

// 示例 2: 支持随机删除的队列
struct Event {
    int time;
    int eventId;
    int heapIndex;  // 由队列维护
};

bool eventLess(const Event& a, const Event& b) {
    return a.time < b.time;
}

int* getEventIndex(const Event& e) {
    return const_cast<int*>(&e.heapIndex);
}

SkTDPQueue<Event, eventLess, getEventIndex> eventQueue;

Event e1 = {100, 1, -1};
Event e2 = {50, 2, -1};
Event e3 = {75, 3, -1};

eventQueue.insert(e1);
eventQueue.insert(e2);
eventQueue.insert(e3);

// 随机删除事件 2
eventQueue.remove(e2);

// 示例 3: 优先级动态调整
struct Process {
    int priority;
    int processIndex;
};

bool processLess(const Process& a, const Process& b) {
    return a.priority > b.priority;  // 数字越大优先级越高
}

int* getProcessIndex(const Process& p) {
    return const_cast<int*>(&p.processIndex);
}

SkTDPQueue<Process, processLess, getProcessIndex> scheduler(10);

Process p1 = {5, -1};
scheduler.insert(p1);

// 提升优先级
p1.priority = 10;
scheduler.priorityDidChange(p1);

// 示例 4: 预留容量
SkTDPQueue<Task, taskLess> bigQueue(1000);  // 预留 1000 个元素空间

// 示例 5: 排序队列
SkTDPQueue<int, [](int a, int b) { return a < b; }> numbers;
numbers.insert(5);
numbers.insert(2);
numbers.insert(8);
numbers.insert(1);

numbers.sort();  // 排序为 [1, 2, 5, 8]
for (int i = 0; i < numbers.count(); ++i) {
    printf("%d ", numbers.at(i));
}

// 示例 6: 指针类型元素
struct Node { int value; int heapIdx; };

bool nodePtrLess(Node* const& a, Node* const& b) {
    return a->value < b->value;
}

int* getNodeIndex(Node* const& n) {
    return &n->heapIdx;
}

SkTDPQueue<Node*, nodePtrLess, getNodeIndex> ptrQueue;
Node n1 = {10, -1}, n2 = {5, -1};
ptrQueue.insert(&n1);
ptrQueue.insert(&n2);
```

## 注意事项

1. **比较函数语义**: `LESS(a, b)` 返回 true 表示 a 优先级更高(会先出队)
2. **索引初始化**: 使用 INDEX 功能时,元素的索引字段应初始化为 -1
3. **索引有效性**: 调用 remove 或 priorityDidChange 前必须已 insert
4. **元素生命周期**: 队列不拥有元素,指针类型需外部管理生命周期
5. **移动语义**: 不支持移动构造和移动赋值(声明为 default)
6. **复制禁止**: 复制构造和复制赋值被删除
7. **线程安全**: 非线程安全,需要外部同步
8. **堆性质**: 除了 at(0),其他 at(i) 访问的元素不保证优先级顺序

## 最佳实践

1. **选择合适的容器**: 如果不需要随机删除,考虑使用 std::priority_queue
2. **预留容量**: 已知大小时使用构造函数预留,避免动态扩容
3. **索引管理**: 使用侵入式索引避免额外查找开销
4. **批量操作**: 尽量批量插入后再排序,而非逐个调整优先级
5. **验证比较函数**: 确保 LESS 函数定义了严格弱序关系
6. **Debug 验证**: 利用 validate() 方法检查堆完整性

## 与 std::priority_queue 对比

| 特性 | SkTDPQueue | std::priority_queue |
|------|-----------|---------------------|
| 随机删除 | 支持(需 INDEX) | 不支持 |
| 优先级调整 | 支持(需 INDEX) | 不支持 |
| 索引跟踪 | 内置支持 | 需外部实现 |
| 排序 | 支持 sort() | 不支持 |
| 直接访问 | 支持 at(i) | 仅 top() |
| 标准库 | 否 | 是 |
| 容器适配 | 固定使用 SkTDArray | 可定制底层容器 |

## 算法应用场景

1. **Dijkstra 算法**: 按距离优先级处理节点
2. **A* 寻路**: 按启发式估值排序
3. **任务调度**: 按优先级或时间调度任务
4. **事件驱动系统**: 按时间戳排序事件
5. **资源管理**: 按使用频率或重要性管理资源
6. **路径渲染**: 按深度或覆盖顺序渲染

## 扩展阅读

- 二叉堆数据结构原理
- 斐波那契堆(更优的 decrease-key 操作)
- 配对堆(实现简单,性能优异)
- 优先级队列的应用算法
