# SkDeque - 双端队列容器
> 源文件: `src/base/SkDeque.cpp`（头文件在 include/private/base/SkDeque.h）

## 概述
SkDeque 是 Skia 实现的双端队列（Deque）容器，支持在头部和尾部高效地插入和删除元素。与 std::deque 不同，SkDeque 使用块链表（block list）的内存分配策略，允许用户提供初始存储空间，并支持自定义元素大小。该容器在路径构建、命令缓冲、以及需要频繁双端操作的场景中被广泛使用。

## 架构位置
SkDeque 位于 Skia 基础容器模块（src/base）中，属于底层数据结构层。它为路径构建、画布命令记录、GPU 命令缓冲、以及其他需要动态增长且支持双端访问的数据结构提供支持。

## 主要类与结构体

### SkDeque::Block（内部结构体）
内存块的内部表示，用于构建块链表。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fNext | Block* | 指向下一个块 |
| fPrev | Block* | 指向前一个块 |
| fBegin | char* | 当前块的已用区域起始地址 |
| fEnd | char* | 当前块的已用区域结束地址 |
| fStop | char* | 当前块的分配内存结束地址 |

**内存布局**:
```
+-------------+------------------+
| Block 头部  |   实际数据区域    |
+-------------+------------------+
^             ^                  ^
Block*        start()            fStop
```

### SkDeque
双端队列容器主类。

**继承关系**: 无

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fElemSize | size_t | 单个元素的大小（字节） |
| fInitialStorage | void* | 用户提供的初始存储（可为 nullptr） |
| fCount | int | 当前元素总数 |
| fAllocCount | int | 每次分配的元素数量 |
| fFrontBlock | Block* | 头部块指针 |
| fBackBlock | Block* | 尾部块指针 |
| fFront | void* | 头部元素指针 |
| fBack | void* | 尾部元素指针 |

## 公共 API 函数

### 构造与析构

#### `SkDeque(size_t elemSize, int allocCount)`
- **功能**: 构造 deque，不提供初始存储
- **参数**:
  - elemSize: 单个元素大小
  - allocCount: 每个块容纳的元素数量（≥1）

#### `SkDeque(size_t elemSize, void* storage, size_t storageSize, int allocCount)`
- **功能**: 构造 deque，使用用户提供的初始存储
- **参数**:
  - storage: 初始存储空间指针
  - storageSize: 初始存储大小（至少需要 sizeof(Block) + elemSize）
- **优化**: 避免第一次分配

#### `~SkDeque()`
- **功能**: 析构函数，释放所有动态分配的块
- **行为**: 保留用户提供的初始存储（fInitialStorage）

### 插入操作

#### `void* push_front()`
- **功能**: 在头部插入一个元素，返回元素指针
- **返回值**: 指向新插入元素的指针（未初始化）
- **复杂度**: 通常 O(1)，偶尔需要分配新块
- **副作用**: fCount 递增

#### `void* push_back()`
- **功能**: 在尾部插入一个元素，返回元素指针
- **返回值**: 指向新插入元素的指针（未初始化）
- **复杂度**: 通常 O(1)，偶尔需要分配新块
- **副作用**: fCount 递增

### 删除操作

#### `void pop_front()`
- **功能**: 删除头部元素
- **前提**: fCount > 0（否则断言失败）
- **复杂度**: 通常 O(1)，偶尔释放空块
- **副作用**: fCount 递减

#### `void pop_back()`
- **功能**: 删除尾部元素
- **前提**: fCount > 0
- **复杂度**: 通常 O(1)，偶尔释放空块
- **副作用**: fCount 递减

### 查询操作

#### `int count() const`
- **功能**: 返回当前元素总数
- **复杂度**: O(1)

#### `bool empty() const`
- **功能**: 检查 deque 是否为空
- **实现**: `fCount == 0`

#### `const void* front() const` / `void* front()`
- **功能**: 返回头部元素指针
- **前提**: deque 非空

#### `const void* back() const` / `void* back()`
- **功能**: 返回尾部元素指针
- **前提**: deque 非空

### 调试辅助

#### `int numBlocksAllocated() const`
- **功能**: 返回当前分配的块数量
- **用途**: 内存使用分析和调试
- **复杂度**: O(n)，n 为块数量

## SkDeque::Iter 迭代器类

### 构造

#### `Iter(const SkDeque& d, IterStart startLoc)`
- **功能**: 构造迭代器
- **参数**:
  - d: 目标 deque
  - startLoc: kFront_IterStart（从头开始）或 kBack_IterStart（从尾开始）

### 迭代

#### `void* next()`
- **功能**: 返回当前元素并前进到下一个元素
- **返回值**: 当前元素指针，无元素时返回 nullptr
- **方向**: 从前向后

#### `void* prev()`
- **功能**: 返回当前元素并后退到前一个元素
- **返回值**: 当前元素指针，无元素时返回 nullptr
- **方向**: 从后向前

#### `void reset(const SkDeque& d, IterStart startLoc)`
- **功能**: 重置迭代器到新位置

## 内部实现细节

### 块链表结构
SkDeque 使用双向链表连接内存块：
```
+-------+     +-------+     +-------+
| Block | <-> | Block | <-> | Block |
+-------+     +-------+     +-------+
    ^                           ^
fFrontBlock                 fBackBlock
```

每个块内存布局：
```
+--------+---+---+---+---+
| Header | E | E | E | E |  E = Element
+--------+---+---+---+---+
          ^           ^
       fBegin       fEnd
```

### push_front 实现逻辑
```cpp
void* SkDeque::push_front() {
    1. 增加计数
    2. 如果没有块，分配第一个块
    3. 如果当前块未初始化（fBegin == nullptr）：
       - 从块尾部向前放置元素
    4. 否则，从 fBegin 向前放置元素
    5. 如果空间不足，分配新块并链接到头部
    6. 更新 fFront 指针
}
```

**从尾部向前的原因**: 在 push_back 也使用相同块时，避免冲突。

### push_back 实现逻辑
```cpp
void* SkDeque::push_back() {
    1. 增加计数
    2. 如果没有块，分配第一个块
    3. 如果当前块未初始化（fBegin == nullptr）：
       - 从块起始位置向后放置元素
    4. 否则，从 fEnd 向后放置元素
    5. 如果空间不足，分配新块并链接到尾部
    6. 更新 fBack 指针
}
```

### 块回收策略
当块变空时（fBegin == nullptr）：
- pop_front: 如果头部块为空且有后续块，释放头部块
- pop_back: 如果尾部块为空且有前驱块，释放尾部块
- **标记为空**: 设置 fBegin 和 fEnd 为 nullptr

### goto 的使用
代码中使用 `goto INIT_CHUNK`：
```cpp
INIT_CHUNK:
    first->fEnd = first->fStop;
    begin = first->fStop - fElemSize;
```

**原因**: 避免代码重复，在两个分支（初始化和空间不足）中共享初始化逻辑。

### 初始存储的处理
```cpp
if (storageSize >= sizeof(Block) + elemSize) {
    fFrontBlock = (Block*)storage;
    fFrontBlock->init(storageSize);
}
```
- 检查初始存储是否足够大
- 必须容纳至少一个 Block 头部和一个元素
- 不足时回退到动态分配

### 块分配
```cpp
Block* SkDeque::allocateBlock(int allocCount) {
    Block* newBlock = (Block*)sk_malloc_throw(sizeof(Block) + allocCount * fElemSize);
    newBlock->init(sizeof(Block) + allocCount * fElemSize);
    return newBlock;
}
```
- 分配连续内存：头部 + 数据区
- 使用 sk_malloc_throw 确保分配失败时抛异常

### 迭代器的跳过空块逻辑
```cpp
while (fCurBlock && nullptr == fCurBlock->fBegin) {
    fCurBlock = fCurBlock->fNext;
}
```
- 跳过已标记为空的块（fBegin == nullptr）
- 找到第一个非空块
- 如果所有块都为空，fCurBlock 和 fPos 都为 nullptr

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAssert.h | 断言检查 |
| include/private/base/SkMalloc.h | sk_malloc_throw 和 sk_free |
| <cstddef> | size_t, nullptr |

### 被依赖的模块
- 路径构建（SkPath 内部使用）
- 画布命令记录
- GPU 命令缓冲
- 字体缓存管理
- 动画系统
- 任何需要双端队列的场景

## 设计模式与设计决策

### 用户可提供存储
允许用户提供初始存储空间：
- **优点**:
  - 避免第一次堆分配
  - 栈分配小 deque（性能优化）
  - 自定义内存池
- **示例**:
  ```cpp
  char storage[1024];
  SkDeque deque(sizeof(MyType), storage, 1024, 10);
  ```

### 块大小可配置
通过 `allocCount` 参数控制块大小：
- 小 allocCount：内存节省，更多块分配
- 大 allocCount：减少分配次数，更多内存浪费
- 根据使用模式调整

### 不存储元素类型
SkDeque 只知道元素大小，不知道类型：
- **优点**: 通用性，任意类型
- **缺点**: 不调用构造/析构函数
- **适用**: POD 类型或手动管理生命周期

### 块标记为空而非立即释放
使用 fBegin/fEnd == nullptr 标记空块：
- 延迟释放，减少分配/释放循环
- 块可能被重用
- 最终在析构或下次 pop 时释放

### 双向链表
使用双向链表连接块：
- 支持双向迭代
- 双端操作都是 O(1)
- 简化块的插入和删除

## 性能考量

### 时间复杂度
| 操作 | 平均 | 最坏 | 说明 |
|------|------|------|------|
| push_front/push_back | O(1) | O(n) | n = allocCount，偶尔需要分配块 |
| pop_front/pop_back | O(1) | O(1) | 即使释放块也是常数时间 |
| front/back | O(1) | O(1) | 直接访问指针 |

### 空间开销
- **每块开销**: sizeof(Block) ≈ 40 字节（5 个指针）
- **碎片**: 每块最多浪费 (allocCount - 1) × elemSize 字节
- **最佳情况**: 元素填满所有块
- **最坏情况**: 每块只有一个元素

### 缓存局部性
- **优点**: 同块内的元素连续存储，缓存友好
- **缺点**: 跨块访问可能缓存不命中
- **权衡**: allocCount 越大，局部性越好，但浪费越多

### 初始存储优化
提供栈上初始存储可以：
- 避免首次堆分配（可能节省数百纳秒）
- 适用于大多数 deque 很小的场景
- 类似于 SSO（Small String Optimization）

### 与 std::deque 比较
**SkDeque 优势**:
- 支持自定义初始存储
- 更简单的实现（可预测性能）
- 更小的头部开销（如果块大）

**std::deque 优势**:
- 支持随机访问（operator[]）
- 调用构造/析构函数
- 标准库，更广泛支持

## 相关文件
| 文件 | 关系 |
|------|------|
| include/private/base/SkDeque.h | 类声明和内联方法 |
| include/private/base/SkMalloc.h | 内存分配函数 |
| src/core/SkPath.cpp | 使用 SkDeque 构建路径 |
| src/core/SkCanvas.cpp | 画布命令记录 |
| src/gpu/ganesh/GrGpuCommandBuffer.cpp | GPU 命令缓冲 |
| tests/DequeTest.cpp | 单元测试 |

## 使用示例

### 基本用法
```cpp
SkDeque deque(sizeof(int), 10);  // 每块 10 个 int
*(int*)deque.push_back() = 42;   // 尾部插入
*(int*)deque.push_front() = 7;   // 头部插入
int first = *(int*)deque.front(); // 读取头部
deque.pop_front();                // 删除头部
```

### 使用初始存储
```cpp
char storage[256];
SkDeque deque(sizeof(MyStruct), storage, 256, 5);
// 如果元素数量 ≤ 5，不会有堆分配
```

### 迭代
```cpp
SkDeque::Iter iter(deque, SkDeque::Iter::kFront_IterStart);
while (void* ptr = iter.next()) {
    MyType* elem = (MyType*)ptr;
    // 处理元素
}
```

### 反向迭代
```cpp
SkDeque::Iter iter(deque, SkDeque::Iter::kBack_IterStart);
while (void* ptr = iter.prev()) {
    MyType* elem = (MyType*)ptr;
    // 从后向前处理
}
```
