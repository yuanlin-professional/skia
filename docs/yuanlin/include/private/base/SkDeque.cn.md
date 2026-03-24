# SkDeque

> 源文件: `include/private/base/SkDeque.h`

## 概述
SkDeque 是一个双端队列(double-ended queue)容器类,支持在队列两端高效地进行插入和删除操作。它采用分块链表实现,将固定大小的元素存储在多个连续内存块中,每个块可容纳多个元素。

## 架构位置
该类位于 Skia 基础容器库中,属于私有实现层。它为 Skia 内部提供高效的双端队列数据结构,常用于需要频繁在两端进行操作的场景,如命令队列、缓冲区管理等。

## 主要类与结构体

### SkDeque
双端队列的主容器类,管理元素的存储和访问。

**继承关系**: 无基类 → SkDeque

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFront | void* | 指向队列首部元素的指针 |
| fBack | void* | 指向队列尾部元素的指针 |
| fFrontBlock | Block* | 指向首部数据块的指针 |
| fBackBlock | Block* | 指向尾部数据块的指针 |
| fElemSize | size_t | 单个元素的字节大小 |
| fInitialStorage | void* | 初始化时提供的外部存储(可选) |
| fCount | int | 队列中元素的总数 |
| fAllocCount | int | 每个数据块分配的元素数量 |

### Block (私有内部结构体)
用于存储实际数据的内存块,通过双向链表连接。具体定义未在头文件中公开。

### Iter
双向迭代器类,支持前向和后向遍历队列。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fCurBlock | SkDeque::Block* | 当前遍历到的数据块 |
| fPos | char* | 当前元素在块内的位置指针 |
| fElemSize | size_t | 元素大小,用于指针移动计算 |

### F2BIter
单向迭代器类,仅支持从前到后遍历,通过私有继承 Iter 实现。

## 公共 API 函数

### 构造函数
```cpp
explicit SkDeque(size_t elemSize, int allocCount = 1)
```
- **功能**: 创建一个空的双端队列
- **参数**:
  - `elemSize` - 单个元素的字节大小
  - `allocCount` - 每个数据块包含的元素数量(默认为1)

```cpp
SkDeque(size_t elemSize, void* storage, size_t storageSize, int allocCount = 1)
```
- **功能**: 使用预分配的存储空间创建队列
- **参数**:
  - `storage` - 外部提供的存储空间指针
  - `storageSize` - 存储空间的字节大小

### 查询方法

#### `bool empty() const`
- **功能**: 检查队列是否为空
- **返回值**: 队列为空返回 true

#### `int count() const`
- **功能**: 获取队列中元素的数量
- **返回值**: 元素总数

#### `size_t elemSize() const`
- **功能**: 获取单个元素的大小
- **返回值**: 元素字节大小

### 访问方法

#### `void* front()` / `const void* front() const`
- **功能**: 获取队列首部元素的指针
- **返回值**: 指向首部元素的指针,队列为空时行为未定义

#### `void* back()` / `const void* back() const`
- **功能**: 获取队列尾部元素的指针
- **返回值**: 指向尾部元素的指针,队列为空时行为未定义

### 修改方法

#### `void* push_front()`
- **功能**: 在队列首部分配一个新元素的空间
- **返回值**: 指向新元素的指针,调用者负责在该位置构造对象
- **说明**: 不调用构造函数,仅分配内存

#### `void* push_back()`
- **功能**: 在队列尾部分配一个新元素的空间
- **返回值**: 指向新元素的指针,调用者负责在该位置构造对象

#### `void pop_front()`
- **功能**: 移除队列首部元素
- **说明**: 不调用析构函数,调用者负责对象清理

#### `void pop_back()`
- **功能**: 移除队列尾部元素
- **说明**: 不调用析构函数,调用者负责对象清理

## Iter 迭代器 API

### 枚举类型
```cpp
enum IterStart {
    kFront_IterStart,  // 从队列首部开始
    kBack_IterStart,   // 从队列尾部开始
};
```

### 构造和重置

#### `Iter()`
- **功能**: 创建一个未初始化的迭代器,必须调用 reset 后才能使用

#### `Iter(const SkDeque& d, IterStart startLoc)`
- **功能**: 创建并初始化迭代器
- **参数**:
  - `d` - 要遍历的队列
  - `startLoc` - 起始位置(首部或尾部)

#### `void reset(const SkDeque& d, IterStart startLoc)`
- **功能**: 重置迭代器到新的起始位置

### 遍历方法

#### `void* next()`
- **功能**: 移动到下一个元素
- **返回值**: 指向下一个元素的指针,到达末尾时返回 nullptr

#### `void* prev()`
- **功能**: 移动到上一个元素
- **返回值**: 指向上一个元素的指针,到达起始时返回 nullptr

## F2BIter 迭代器 API

### `F2BIter(const SkDeque& d)`
- **功能**: 创建一个从前到后的单向迭代器
- **说明**: 通过私有继承 Iter,仅暴露 next() 方法,隐藏 prev() 方法

### `void reset(const SkDeque& d)`
- **功能**: 重置迭代器到队列首部

## 内部实现细节

### 分块链表结构
队列采用分块(chunked)链表实现:
- 每个 Block 可以存储多个固定大小的元素
- Block 通过双向链表连接
- 优势: 减少内存分配次数,提高缓存局部性

### 延迟回收策略
```cpp
// One behavior to be aware of is that the pops do not immediately remove an
// empty block from the beginning/end of the list
```
当 pop 操作导致块为空时,不会立即释放该块:
- 避免频繁的分配/释放操作
- 适合 push/pop 配对频繁的场景
- 可能导致首/尾元素不在首/尾块中

### 类型无关设计
队列以字节(void*)为单位操作,不使用模板:
- 通过 elemSize 参数确定元素大小
- 调用者负责类型转换和对象生命周期管理
- 减少代码膨胀,编译速度更快

### 外部存储支持
支持使用用户提供的初始存储空间:
- 避免小队列的动态内存分配
- 适合栈上分配场景
- 当容量超出时自动切换到堆分配

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/private/base/SkAPI.h | SK_API 宏,用于符号导出 |
| <cstddef> | size_t 类型定义 |

### 被依赖的模块
- 路径操作模块(存储路径动词和坐标)
- 图形命令队列
- 文本布局引擎(字形缓冲)
- 任何需要双端队列的内部实现

## 设计模式与设计决策

### RAII 边界模式
push 方法返回原始指针,调用者负责对象构造:
```cpp
void* ptr = deque.push_back();
new (ptr) MyType(args);  // placement new
```
这种设计分离了内存管理和对象生命周期,提供最大灵活性。

### 迭代器继承层次
- `Iter`: 完整的双向迭代器
- `F2BIter`: 通过私有继承限制接口,仅提供单向遍历
- 体现了接口隔离原则

### 不可拷贝
```cpp
SkDeque(const SkDeque&) = delete;
SkDeque& operator=(const SkDeque&) = delete;
```
禁止拷贝避免:
- 深拷贝的高昂代价
- 不明确的语义(浅拷贝还是深拷贝?)
- 需要移动语义时应显式实现

## 性能考量

### 内存分配优化
- **批量分配**: 每个 Block 包含多个元素,减少分配次数
- **allocCount 参数**: 允许根据使用模式调优块大小
- **外部存储**: 小队列可以完全避免堆分配

### 缓存友好性
- 连续存储同一 Block 中的元素
- 提高空间局部性
- 适合顺序访问模式

### 延迟回收
- 减少 push/pop 边界的抖动
- 避免频繁的分配/释放
- 适合栈式使用模式

### 迭代器开销
- 迭代器存储当前块和位置
- 跨块遍历时需要链表跳转
- 相比 std::deque 的索引访问略慢,但插入/删除更快

## 使用场景

### 命令队列
```cpp
SkDeque cmdQueue(sizeof(Command), 32);  // 每块32个命令
void* ptr = cmdQueue.push_back();
new (ptr) DrawRectCommand(rect);
```

### 路径数据存储
```cpp
SkDeque pathPoints(sizeof(SkPoint), 16);
pathPoints.push_back();  // 添加点
```

### 临时缓冲区
```cpp
SkAlignedSTStorage<1024, char> storage;
SkDeque buffer(1, storage.get(), 1024, 1024);
// 使用栈上的初始存储,避免小缓冲的堆分配
```

## 相关文件
| 文件 | 关系 |
|------|------|
| src/core/SkDeque.cpp | 实现文件 |
| include/private/base/SkAPI.h | 提供 API 导出宏 |
| tests/DequeTest.cpp | 单元测试 |
| src/core/SkPath.cpp | 使用 SkDeque 存储路径数据 |

## 注意事项

### 内存管理
- push 方法不调用构造函数,必须使用 placement new
- pop 方法不调用析构函数,必须手动调用
- 析构函数不会自动清理元素,需要手动遍历销毁

### 迭代器失效
- push/pop 操作可能导致迭代器失效
- 不支持在迭代过程中修改队列结构

### 线程安全
- 该类不是线程安全的
- 多线程环境需要外部同步机制
