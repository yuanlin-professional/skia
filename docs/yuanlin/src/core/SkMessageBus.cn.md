# SkMessageBus

> 源文件: src/core/SkMessageBus.h

## 概述

`SkMessageBus` 是 Skia 中实现的一个通用消息总线系统，提供线程安全的发布-订阅（Pub-Sub）消息传递机制。它允许组件之间解耦通信，发送者无需知道接收者的具体实例，接收者通过创建 `Inbox` 来订阅特定类型的消息。

该系统支持消息过滤（通过 `SkShouldPostMessageToBus` 特化函数），确保消息只发送给关心它的接收者。消息总线是模板化的，支持任意消息类型和 ID 类型，具有高度的类型安全性和灵活性。`SkMessageBus` 在 Skia 中用于缓存失效、资源通知等场景。

## 架构位置

`SkMessageBus` 是 Skia 核心基础设施的一部分，位于通信和事件系统层：

- **架构层级**：基础工具层，被多个子系统使用
- **典型应用**：缓存管理（如 `SkResourceCache`）、GPU 资源通知、图像更新事件
- **设计特点**：头文件模板实现 + 宏定义单例，避免跨动态库的多实例问题

在 Skia 架构中，`SkMessageBus` 提供了一种轻量级的组件间通信机制，避免了直接依赖和复杂的回调管理。

## 主要类与结构体

### SkMessageBus<Message, IDType, AllowCopyableMessage>

模板参数化的消息总线类：

| **模板参数** | **说明** |
|------------|---------|
| `Message` | 消息类型，需要满足特定约束（见下文） |
| `IDType` | 标识符类型，用于区分不同的消息接收者 |
| `AllowCopyableMessage` | 布尔值，是否允许可拷贝的消息（默认 `true`） |

**继承关系**：

- 继承自 `SkNoncopyable`，禁止拷贝和赋值

**关键成员变量**：

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fInboxes` | `SkTDArray<Inbox*>` | 所有已注册的收件箱指针数组 |
| `fInboxesMutex` | `SkMutex` | 保护收件箱列表的互斥锁 |

### SkMessageBus::Inbox

内嵌类，表示消息接收者的收件箱：

| **特性** | **说明** |
|---------|---------|
| **生命周期** | 构造时自动注册，析构时自动注销 |
| **线程安全** | 所有操作都是线程安全的 |

**关键成员变量**：

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fMessages` | `skia_private::TArray<Message>` | 待处理的消息队列 |
| `fMessagesMutex` | `SkMutex` | 保护消息队列的互斥锁 |
| `fUniqueID` | `const IDType` | 收件箱的唯一标识符，用于消息过滤 |

## 公共 API 函数

### SkMessageBus 接口

#### 发送消息

```cpp
static void Post(Message m);
```

- **功能**：向所有订阅者发送消息
- **线程安全**：是
- **过滤机制**：对每个 `Inbox`，调用 `SkShouldPostMessageToBus(m, inbox->fUniqueID)` 判断是否发送
- **移动语义**：
  - 如果 `AllowCopyableMessage = true`，消息被拷贝到每个符合条件的收件箱
  - 如果 `AllowCopyableMessage = false`，消息通过 `std::move()` 传递给第一个符合条件的收件箱

### Inbox 接口

#### 构造与析构

```cpp
Inbox(IDType uniqueID);
~Inbox();
```

- **构造函数**：自动注册到对应的消息总线
- **析构函数**：自动从消息总线注销

#### 获取 ID

```cpp
IDType uniqueID() const;
```

返回收件箱的唯一标识符。

#### 轮询消息

```cpp
void poll(skia_private::TArray<Message>* out);
```

- **功能**：取出自上次调用以来收到的所有消息
- **行为**：清空内部队列，将消息移动到 `out` 数组
- **线程安全**：是

### 宏定义

#### DECLARE_SKMESSAGEBUS_MESSAGE

```cpp
#define DECLARE_SKMESSAGEBUS_MESSAGE(Message, IDType, AllowCopyableMessage)
```

- **用途**：在单个 `.cpp` 文件中声明消息总线的单例实现
- **必要性**：避免在使用共享库时创建多个消息总线实例
- **使用约束**：每种消息类型只能在一个编译单元中使用该宏

## 内部实现细节

### 消息类型约束

使用 `static_assert` 强制消息类型满足约束：

```cpp
static_assert(AllowCopyableMessage || is_sk_sp<Message>::value ||
              !std::is_copy_constructible<Message>::value,
              "The message type must be sk_sp or non copyable.");
```

- 如果 `AllowCopyableMessage = false`，消息必须是 `sk_sp<T>` 或不可拷贝类型
- 确保消息传递的所有权语义清晰，避免意外的拷贝

### 单例模式实现

通过静态成员函数 `Get()` 实现单例：

```cpp
template <typename Message, typename IDType, bool AllowCopyableMessage>
static SkMessageBus* Get();
```

宏展开后的实现：

```cpp
template <>
SkMessageBus<Message, IDType, AllowCopyableMessage>*
SkMessageBus<Message, IDType, AllowCopyableMessage>::Get() {
    static auto* bus = new SkMessageBus<Message, IDType, AllowCopyableMessage>();
    return bus;
}
```

**特点**：

- 全局唯一实例
- 线程安全（C++11 保证静态局部变量的线程安全初始化）
- 从不销毁（避免静态析构顺序问题）

### Inbox 注册与注销

#### 注册（构造时）

```cpp
SkMessageBus<Message, IDType, AllowCopyableMessage>::Inbox::Inbox(IDType uniqueID)
        : fUniqueID(uniqueID) {
    auto* bus = SkMessageBus<Message, IDType, AllowCopyableMessage>::Get();
    SkAutoMutexExclusive lock(bus->fInboxesMutex);
    bus->fInboxes.push_back(this);
}
```

线程安全地将自己添加到总线的收件箱列表。

#### 注销（析构时）

```cpp
SkMessageBus<Message, IDType, AllowCopyableMessage>::Inbox::~Inbox() {
    auto* bus = SkMessageBus<Message, IDType, AllowCopyableMessage>::Get();
    SkAutoMutexExclusive lock(bus->fInboxesMutex);
    for (int i = 0; i < bus->fInboxes.size(); i++) {
        if (this == bus->fInboxes[i]) {
            bus->fInboxes.removeShuffle(i);  // O(1) 删除，不保证顺序
            break;
        }
    }
}
```

使用 `removeShuffle()` 实现 O(1) 删除，牺牲顺序换取性能。

### 消息发送逻辑

```cpp
template <typename Message, typename IDType, bool AllowCopyableMessage>
/*static*/ void SkMessageBus<Message, IDType, AllowCopyableMessage>::Post(Message m) {
    auto* bus = SkMessageBus<Message, IDType, AllowCopyableMessage>::Get();
    SkAutoMutexExclusive lock(bus->fInboxesMutex);
    for (int i = 0; i < bus->fInboxes.size(); i++) {
        if (SkShouldPostMessageToBus(m, bus->fInboxes[i]->fUniqueID)) {
            if constexpr (AllowCopyableMessage) {
                bus->fInboxes[i]->receive(m);  // 拷贝语义
            } else {
                if constexpr (is_sk_sp<Message>::value) {
                    SkASSERT(m->unique());  // 确保是唯一引用
                }
                bus->fInboxes[i]->receive(std::move(m));  // 移动语义
                break;  // 只发送给第一个匹配的收件箱
            }
        }
    }

    if constexpr (is_sk_sp<Message>::value && !AllowCopyableMessage) {
        SkASSERT(!m);  // 确保消息已被移动
    }
}
```

**关键点**：

- 持有全局锁期间遍历所有收件箱
- 调用用户提供的 `SkShouldPostMessageToBus()` 过滤消息
- 根据 `AllowCopyableMessage` 决定拷贝或移动

### 消息接收逻辑

```cpp
template <typename Message, typename IDType, bool AllowCopyableMessage>
void SkMessageBus<Message, IDType, AllowCopyableMessage>::Inbox::receive(Message m) {
    SkAutoMutexExclusive lock(fMessagesMutex);
    fMessages.push_back(std::move(m));
}
```

线程安全地将消息追加到内部队列。

### 消息轮询逻辑

```cpp
template <typename Message, typename IDType, bool AllowCopyableMessage>
void SkMessageBus<Message, IDType, AllowCopyableMessage>::Inbox::poll(
        skia_private::TArray<Message>* messages) {
    SkASSERT(messages);
    messages->clear();
    SkAutoMutexExclusive lock(fMessagesMutex);
    fMessages.swap(*messages);  // O(1) 交换，避免拷贝
}
```

高效地转移消息所有权，避免逐个拷贝。

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkMutex` | 提供互斥锁，保证线程安全 |
| `SkTArray` | 动态数组，存储消息队列 |
| `SkTDArray` | 动态指针数组，存储收件箱列表 |
| `SkNoncopyable` | 禁止拷贝的基类 |
| `sk_sp` | 智能指针，支持引用计数消息 |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| `SkResourceCache` | 使用消息总线通知缓存失效 |
| GPU 资源管理 | 使用消息总线通知上下文丢失等事件 |
| 图像更新系统 | 通知图像内容变更 |
| 测试框架 | 验证消息传递逻辑 |

## 设计模式与设计决策

### 发布-订阅模式

`SkMessageBus` 是发布-订阅模式的经典实现：

- **解耦**：发送者和接收者互不知晓
- **动态订阅**：收件箱可在运行时动态注册和注销
- **一对多**：一条消息可发送给多个订阅者

### 模板编程

全模板实现提供类型安全和零运行时开销：

- 编译时类型检查
- 无需运行时类型转换
- 每种消息类型独立实例化

### 编译时过滤机制

通过 `SkShouldPostMessageToBus()` 特化函数实现消息过滤：

```cpp
// 用户需要为每种消息类型提供特化
template <>
bool SkShouldPostMessageToBus(const MyMessage& msg, uint32_t targetID) {
    return msg.relevantID == targetID;
}
```

**优势**：

- 灵活的过滤逻辑
- 编译时类型检查
- 无需虚函数开销

### 所有权语义控制

通过 `AllowCopyableMessage` 模板参数控制消息传递语义：

- **可拷贝模式**（默认）：适用于小型消息，广播给所有订阅者
- **移动模式**：适用于大型或唯一所有权的消息，只传递给第一个订阅者

### 线程安全设计

- **粗粒度锁**：使用单一互斥锁保护关键操作，简化实现
- **锁分离**：总线锁和收件箱锁分离，减少竞争
- **原子操作**：`swap()` 用于消息转移，避免持锁时间过长

## 性能考量

### 锁竞争

- **Post 操作**：持有全局锁遍历所有收件箱，可能成为瓶颈
- **优化方向**：可考虑读写锁或细粒度锁

### 内存分配

- **动态数组**：`TArray` 和 `TDArray` 自动扩容，可能引发重分配
- **优化建议**：预留容量（`reserve()`）

### O(1) 删除

使用 `removeShuffle()` 实现 O(1) 收件箱注销：

- 将最后一个元素移动到删除位置
- 不保证收件箱顺序
- 适合不关心顺序的场景

### 消息拷贝开销

- **可拷贝模式**：每个订阅者获得一份拷贝，适合小型消息
- **移动模式**：零拷贝，适合大型消息或唯一资源

### 使用建议

- 消息类型应尽量小且廉价拷贝
- 对于大型数据，考虑传递 `sk_sp` 或移动语义
- 避免在关键渲染路径中频繁发送消息
- 定期调用 `poll()` 清空消息队列，避免无限增长

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkResourceCache.cpp` | 使用消息总线的典型示例 |
| `include/private/base/SkMutex.h` | 互斥锁实现 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/private/base/SkTDArray.h` | 动态指针数组容器 |
| `include/core/SkRefCnt.h` | 智能指针 `sk_sp` 定义 |
| `tests/MessageBusTest.cpp` | 消息总线的单元测试（可能存在） |
