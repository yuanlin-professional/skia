# SkArenaAllocList

> 源文件: `src/base/SkArenaAllocList.h`

## 概述

SkArenaAllocList 是存储在 SkArenaAlloc 中的单向链表模板容器。元素由竞技场分配器拥有,而非链表本身,支持前向迭代和范围 for 循环。该数据结构专为高性能临时对象集合设计,避免单独的内存分配开销。

## 架构位置

- **所属子系统**: 基础设施层 (Base Infrastructure)
- **层级**: 数据结构 - 容器
- **作用域**: 为需要临时对象集合的 Skia 模块提供高效链表

## 主要类与结构体

### SkArenaAllocList<T>

基于竞技场分配器的单向链表容器。

**继承关系**: 无

**模板参数**:
- `T`: 元素类型

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fHead | Node* | 链表头指针 |
| fTail | Node* | 链表尾指针 |

### Node (私有)

链表节点结构,存储元素和下一节点指针。

**关键成员**:
| 成员 | 类型 | 说明 |
|------|------|------|
| fT | T | 元素对象 |
| fNext | Node* | 下一节点指针 |

**构造函数**:
```cpp
template <typename... Args>
Node(Args... args) : fT(std::forward<Args>(args)...) {}
```

### Iter

前向迭代器类,符合标准迭代器要求。

**关键成员**:
| 成员 | 类型 | 说明 |
|------|------|------|
| fCurr | Node* | 当前节点指针 |

## 公共 API 函数

### `SkArenaAllocList()`
- **功能**: 默认构造函数,创建空链表
- **返回值**: 无
- **初始状态**: fHead 和 fTail 均为 nullptr

### `void reset()`
- **功能**: 重置链表为空
- **返回值**: 无
- **副作用**: fHead 和 fTail 设为 nullptr
- **注意**: 不释放节点内存(由 SkArenaAlloc 管理)

### `template <typename... Args> T& append(SkArenaAlloc* arena, Args... args)`
- **功能**: 在链表尾部追加新元素
- **参数**:
  - `arena`: 竞技场分配器指针
  - `args`: 转发给 T 构造函数的参数
- **返回值**: 新元素的引用
- **复杂度**: O(1)
- **实现**:
  ```cpp
  auto* n = arena->make<Node>(std::forward<Args>(args)...);
  if (!fTail) {
      fHead = fTail = n;
  } else {
      fTail = fTail->fNext = n;
  }
  return fTail->fT;
  ```

### `Iter begin()`
- **功能**: 返回指向第一个元素的迭代器
- **返回值**: Iter 对象
- **空链表**: 返回的迭代器等于 end()

### `Iter end()`
- **功能**: 返回尾后迭代器
- **返回值**: Iter(nullptr)
- **用途**: 迭代终止条件

### `Iter tail()`
- **功能**: 返回指向最后一个元素的迭代器
- **返回值**: Iter(fTail)
- **用途**: 访问尾部元素

## 迭代器接口

### `Iter& operator++()`
- **功能**: 前进到下一个元素(前置递增)
- **返回值**: 自身引用
- **实现**: `fCurr = fCurr->fNext;`

### `T& operator*() const`
- **功能**: 解引用,访问当前元素
- **返回值**: 元素引用
- **实现**: `return fCurr->fT;`

### `T* operator->() const`
- **功能**: 成员访问操作符
- **返回值**: 元素指针
- **实现**: `return &fCurr->fT;`

### `bool operator==(const Iter&) const`
- **功能**: 比较两个迭代器是否相等
- **返回值**: 相等返回 true
- **实现**: `return fCurr == that.fCurr;`

### `bool operator!=(const Iter&) const`
- **功能**: 比较两个迭代器是否不等
- **返回值**: 不等返回 true
- **实现**: `return !(*this == that);`

## 内部实现细节

### append 实现

```cpp
template <typename T>
template <typename... Args>
T& SkArenaAllocList<T>::append(SkArenaAlloc* arena, Args... args) {
    SkASSERT(!fHead == !fTail);  // 一致性检查
    auto* n = arena->make<Node>(std::forward<Args>(args)...);
    if (!fTail) {
        fHead = fTail = n;
    } else {
        fTail = fTail->fNext = n;
    }
    return fTail->fT;
}
```

**步骤**:
1. 使用竞技场分配器创建新节点
2. 如果链表空,同时设置头尾
3. 否则,链接到当前尾部并更新 fTail
4. 返回新元素的引用

### 迭代器递增

```cpp
template <typename T>
typename SkArenaAllocList<T>::Iter& SkArenaAllocList<T>::Iter::operator++() {
    fCurr = fCurr->fNext;
    return *this;
}
```

简单的指针跳转,O(1) 时间复杂度。

### 范围 for 循环支持

```cpp
for (const auto& element : list) {
    // 使用 element
}
```

**展开为**:
```cpp
auto it = list.begin();
auto end_it = list.end();
for (; it != end_it; ++it) {
    const auto& element = *it;
    // 使用 element
}
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkArenaAlloc.h | 节点内存分配 |
| SkAssert.h | 一致性检查 |
| std::forward | 完美转发 |

### 被依赖的模块
- **SkRasterPipeline**: 管道阶段链表
- **SkPath 构建器**: 临时路径操作列表
- **图形效果**: 效果参数链表

## 设计模式与设计决策

### 设计模式
1. **迭代器模式**: 提供标准迭代器接口
2. **组合模式**: 节点包含元素和指针
3. **RAII 模式**: 内存由竞技场分配器管理

### 设计决策

**为什么使用单向链表而不是双向?**
- 前向遍历已满足大多数需求
- 节省每节点 8 字节(无 prev 指针)
- 追加操作仍为 O(1)(保持尾指针)

**为什么元素由竞技场拥有?**
- 避免单独的 new/delete 开销
- 批量释放,析构时零开销
- 内存布局紧凑,缓存友好

**为什么不提供 size() 方法?**
- 需要额外存储或 O(n) 计算
- 大多数用例不需要大小
- 保持结构最小化(仅 16 字节)

**为什么 reset() 不释放内存?**
- 内存由 SkArenaAlloc 统一管理
- 允许快速重用链表结构
- 符合竞技场分配器的批量释放语义

**为什么返回元素引用而不是指针?**
- 元素总是有效的
- 更自然的语法
- 避免 nullptr 检查

## 性能考量

### 时间复杂度
- `append()`: O(1) - 常量时间追加
- `begin()`, `end()`, `tail()`: O(1) - 指针访问
- `reset()`: O(1) - 仅重置指针
- 迭代: O(n) - 遍历所有节点
- 析构: O(1) - 无析构逻辑(竞技场处理)

### 空间复杂度
- **链表开销**: 16 字节(fHead + fTail)
- **每节点开销**: sizeof(T) + sizeof(void*) + 竞技场对齐
- **典型**: sizeof(T) + 8-16 字节

### 性能优势
1. **零分配开销**: 使用竞技场分配器
2. **零析构开销**: 批量释放
3. **缓存友好**: 节点连续分配(竞技场)
4. **尾部追加**: O(1) 无需遍历

### 性能对比
| 操作 | SkArenaAllocList | std::list | std::vector |
|------|------------------|-----------|-------------|
| append | O(1), 零堆分配 | O(1), 每次堆分配 | O(1) 均摊 |
| 迭代 | O(n) | O(n) | O(n) |
| 析构 | O(1) | O(n) | O(n) |
| 内存布局 | 紧凑(竞技场) | 分散(堆) | 连续 |

## 相关文件
| 文件 | 关系 |
|------|------|
| src/base/SkArenaAlloc.h | 内存分配器 |
| include/private/base/SkAssert.h | 断言工具 |

## 使用示例

### 示例 1: 基本追加和迭代
```cpp
SkArenaAlloc alloc(1024);
SkArenaAllocList<int> list;

list.append(&alloc, 10);
list.append(&alloc, 20);
list.append(&alloc, 30);

for (int value : list) {
    SkDebugf("%d\n", value);  // 输出 10, 20, 30
}
```

### 示例 2: 复杂对象
```cpp
struct Point {
    float x, y;
    Point(float x_, float y_) : x(x_), y(y_) {}
};

SkArenaAlloc alloc(1024);
SkArenaAllocList<Point> points;

points.append(&alloc, 1.0f, 2.0f);
points.append(&alloc, 3.0f, 4.0f);

for (const Point& pt : points) {
    SkDebugf("(%f, %f)\n", pt.x, pt.y);
}
```

### 示例 3: 使用迭代器
```cpp
SkArenaAllocList<std::string> list;
list.append(&alloc, "hello");
list.append(&alloc, "world");

for (auto it = list.begin(); it != list.end(); ++it) {
    SkDebugf("%s\n", it->c_str());
}
```

### 示例 4: 访问尾部元素
```cpp
SkArenaAllocList<int> list;
list.append(&alloc, 1);
list.append(&alloc, 2);

int& lastValue = *list.tail();  // 2
lastValue = 42;
```

### 示例 5: 重用链表
```cpp
SkSTArenaAllocWithReset<1024> alloc;
SkArenaAllocList<int> list;

for (int frame = 0; frame < 100; ++frame) {
    list.reset();  // 清空链表
    for (int i = 0; i < 10; ++i) {
        list.append(&alloc, i);
    }
    // 处理链表...
    alloc.reset();  // 释放所有内存
}
```

### 示例 6: 完美转发
```cpp
struct Widget {
    Widget(int a, double b, std::string c) { /* ... */ }
};

SkArenaAllocList<Widget> widgets;
widgets.append(&alloc, 42, 3.14, "test");
// 直接转发参数给 Widget 构造函数
```

## 注意事项

1. **竞技场生命周期**: 链表元素依赖竞技场,竞技场销毁后访问未定义
2. **迭代器失效**: 竞技场 reset() 后所有迭代器失效
3. **非拥有性**: 链表不拥有元素,reset() 不调用析构函数
4. **单向性**: 不支持反向迭代
5. **无删除**: 不支持删除单个元素(不是设计目标)
6. **线程安全**: 不是线程安全的
7. **元素稳定性**: 元素地址稳定,直到竞技场销毁
8. **移动语义**: 链表本身可移动,但通常无需要

## 最佳实践

### 何时使用 SkArenaAllocList
- 需要临时对象集合
- 元素仅追加,不删除
- 生命周期与竞技场一致
- 对性能要求高

### 何时使用其他容器
- **std::vector**: 需要随机访问或大小查询
- **std::list**: 需要双向迭代或中间插入
- **std::deque**: 需要两端追加

### 性能提示
1. 预估竞技场大小避免重新分配
2. 重用链表和竞技场(WithReset)
3. 批量追加减少调用开销
4. 避免复制元素,使用引用或指针迭代

### 典型用例
```cpp
// 路径操作列表
SkArenaAllocList<PathOp> operations;

// 管道阶段链表
SkArenaAllocList<PipelineStage> stages;

// 临时对象集合
SkArenaAllocList<TempObject> temps;
```

## 限制和权衡

### 限制
1. **仅前向迭代**: 不支持反向遍历
2. **无 size()**: 获取大小需要遍历
3. **无随机访问**: 访问第 n 个元素需要 O(n)
4. **无删除**: 不能移除单个元素
5. **依赖竞技场**: 必须提供有效的 SkArenaAlloc

### 权衡
- **内存效率 vs. 功能**: 牺牲部分功能换取最小开销
- **性能 vs. 灵活性**: 专为追加和迭代优化
- **简单性 vs. 通用性**: 适合特定用例,不是通用容器
