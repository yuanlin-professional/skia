# BackendSemaphore

> 源文件
> - include/gpu/graphite/BackendSemaphore.h
> - src/gpu/graphite/BackendSemaphore.cpp

## 概述

`BackendSemaphore` 是 Skia Graphite 渲染系统中用于跨 GPU 队列或跨进程同步的信号量抽象类。它封装了不同图形 API（Vulkan、Metal）的原生信号量对象，提供统一的接口用于 GPU 工作的同步控制。

信号量是 GPU 编程中的关键同步原语，用于：
- 协调多个命令队列之间的执行顺序
- 实现跨进程的 GPU 资源共享
- 控制渲染管线的依赖关系

Graphite 的 `BackendSemaphore` 使用类型擦除技术（`SkAnySubclass`）存储后端特定的信号量数据，避免暴露底层 API 细节。

## 架构位置

`BackendSemaphore` 位于 Graphite 的跨平台抽象层：

- **上层**：被 Recording 和 Context 使用，控制命令提交的同步
- **同层**：与 `BackendTexture` 等其他后端对象抽象并列
- **下层**：封装后端特定的信号量实现（VkSemaphore、MTLSharedEvent 等）
- **所属模块**：`gpu/graphite` - 跨平台 GPU 抽象

这是一个轻量级的值类型对象，支持复制和赋值。

## 主要类与结构体

### BackendSemaphore 类

**继承关系**：
- 无继承，独立实现
- 可复制、可移动

**关键成员变量**：
| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fBackend` | `BackendApi` | 后端类型（Vulkan/Metal/Dawn） |
| `fSemaphoreData` | `AnyBackendSemaphoreData` | 类型擦除的信号量数据容器 |
| `fIsValid` | `bool` | 标记信号量是否有效 |

**类型定义**：
```cpp
inline constexpr static size_t kMaxSubclassSize = 24;
using AnyBackendSemaphoreData = SkAnySubclass<BackendSemaphoreData, kMaxSubclassSize>;
```

### BackendSemaphoreData 抽象基类

后端特定信号量数据的基类，定义了虚析构函数和 `copyTo` 方法。

**子类实现**：
- `VkBackendSemaphoreData`：封装 VkSemaphore
- `MtlBackendSemaphoreData`：封装 MTLSharedEvent

## 公共 API 函数

### 构造与析构

```cpp
BackendSemaphore()
```
默认构造函数，创建无效的信号量对象。

```cpp
BackendSemaphore(const BackendSemaphore&)
```
拷贝构造函数，执行深拷贝。

```cpp
~BackendSemaphore()
```
析构函数，释放内部数据。

### 赋值运算符

```cpp
BackendSemaphore& operator=(const BackendSemaphore& that)
```

**实现逻辑**：
1. 检查源对象是否有效，无效则标记当前对象为无效
2. 断言后端类型一致（不允许跨后端赋值）
3. 复制后端类型和有效性标记
4. 根据后端类型使用 `copyTo` 复制数据

**特殊处理**：
- Dawn 后端当前不支持（调用 `SK_ABORT`）
- Metal 和 Vulkan 支持完整复制

### 查询函数

```cpp
bool isValid() const
```
返回信号量是否有效。

```cpp
BackendApi backend() const
```
返回后端 API 类型（Vulkan、Metal、Dawn）。

## 内部实现细节

### 类型擦除技术

使用 `SkAnySubclass` 实现类型擦除：
- 避免模板代码膨胀
- 在栈上存储小对象（≤24 字节）
- 支持多态行为而不使用虚函数表

**存储布局**：
```cpp
template <typename SomeBackendSemaphoreData>
BackendSemaphore(BackendApi backend, const SomeBackendSemaphoreData& data)
        : fBackend(backend), fIsValid(true) {
    fSemaphoreData.emplace<SomeBackendSemaphoreData>(data);
}
```

### 后端特定实现

#### Vulkan 实现

封装 `VkSemaphore` 句柄：
- 用于 `vkQueueSubmit` 的等待/信号操作
- 支持时间线信号量（Timeline Semaphore）
- 可用于跨队列同步

#### Metal 实现

封装 `MTLSharedEvent`：
- 支持 CPU-GPU 同步
- 可在多个命令缓冲区间共享
- 支持设置信号值进行细粒度控制

#### Dawn 实现

当前未实现（调用时会中止），预留接口。

### 复制语义

赋值运算符实现深拷贝：
- 调用 `fSemaphoreData.reset()` 清空当前数据
- 使用 `that.fSemaphoreData->copyTo(fSemaphoreData)` 复制数据
- 确保每个 `BackendSemaphore` 独立管理其生命周期

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `BackendApi` | 枚举后端类型 |
| `SkAnySubclass` | 类型擦除容器 |
| `BackendSemaphoreData` | 后端数据基类 |
| `BackendSemaphorePriv` | 内部访问接口 |

### 被依赖的模块

- **InsertRecordingInfo**：提交 Recording 时指定等待的信号量
- **QueueManager**：使用信号量控制命令队列同步
- **Context**：管理跨提交的同步依赖

## 设计模式与设计决策

### 值语义设计

`BackendSemaphore` 是值类型而非引用类型：
- 支持拷贝和赋值
- 使用栈分配，避免堆内存管理
- 生命周期由持有者控制

这与 Vulkan/Metal 的信号量模型一致，信号量本身是轻量级句柄。

### 类型擦除而非虚函数

使用 `SkAnySubclass` 而非继承和虚函数：
- 避免虚函数表开销
- 保持对象大小可预测（24 字节内）
- 编译期确定类型，优化性能

### 不可变性

一旦创建，`fBackend` 不可变：
- 简化同步逻辑
- 避免后端类型不匹配错误
- 通过断言在开发期检测错误

### 显式有效性标记

使用 `fIsValid` 标记而非依赖空指针：
- 值类型不能为 null
- 显式标记更清晰
- 支持默认构造的无效状态

## 性能考量

### 内存布局

- 固定大小（约 32 字节：8 字节对齐 + 24 字节数据 + 标志位）
- 栈分配，无堆内存开销
- 缓存友好的紧凑布局

### 复制开销

- 拷贝操作涉及后端数据的深拷贝
- Vulkan：仅复制句柄（4-8 字节）
- Metal：可能复制对象引用
- 建议按引用传递以避免不必要的复制

### 同步开销

信号量本身的性能取决于后端实现：
- Vulkan：内核级同步原语，开销较低
- Metal：共享事件机制，支持细粒度同步
- 正确使用可显著减少 CPU-GPU 同步等待

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/GpuTypes.h` | 定义 BackendApi 枚举 |
| `include/private/base/SkAnySubclass.h` | 类型擦除容器实现 |
| `src/gpu/graphite/BackendSemaphorePriv.h` | 内部访问接口 |
| `src/gpu/graphite/vk/VkSemaphore.h` | Vulkan 信号量封装 |
| `src/gpu/graphite/mtl/MtlSemaphore.h` | Metal 共享事件封装 |
| `include/gpu/graphite/GraphiteTypes.h` | Graphite 类型定义 |
