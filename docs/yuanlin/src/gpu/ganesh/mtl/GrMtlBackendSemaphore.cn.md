# GrMtlBackendSemaphore

> 源文件
> - include/gpu/ganesh/mtl/GrMtlBackendSemaphore.h
> - src/gpu/ganesh/mtl/GrMtlBackendSemaphore.mm

## 概述

`GrMtlBackendSemaphore` 模块为 Ganesh 渲染引擎提供 Metal 后端信号量（Semaphore）的封装和管理功能。Metal 使用 `MTLEvent` 和关联的值来实现信号量语义，该模块将 Metal 的事件对象包装为 Skia 的 `GrBackendSemaphore` 抽象接口，支持跨队列同步和多帧资源管理。

Metal 事件采用时间线信号量模型，每个事件有一个 64 位整数值，支持比传统二进制信号量更灵活的同步机制。

## 架构位置

该模块位于 Ganesh Metal 后端的同步原语层：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── Synchronization Abstraction
    │   └── GrBackendSemaphore        ← 抽象接口
    └── Backend Implementations
        └── Metal Backend
            ├── GrMtlBackendSemaphore  ← 当前模块（Metal 实现）
            ├── GrMtlGpu               ← GPU 实现
            └── GrMtlCommandBuffer     ← 命令缓冲区
```

## 主要类与结构体

### GrMtlBackendSemaphoreData

Metal 后端信号量数据类，封装 Metal 事件和值。

**继承关系**: `GrMtlBackendSemaphoreData` → `GrBackendSemaphoreData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fEvent` | `GrMTLHandle` | Metal 事件对象句柄（实际为 `id<MTLEvent>`） |
| `fValue` | `uint64_t` | 信号量的值（时间线信号量语义） |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `event()` | 返回 Metal 事件句柄 |
| `value()` | 返回信号量值 |
| `copyTo(AnySemaphoreData&)` | 将数据复制到类型擦除容器 |
| `type()` | 返回后端 API 类型（调试模式） |

**构造函数**
```cpp
GrMtlBackendSemaphoreData(GrMTLHandle event, uint64_t value)
```

## 公共 API 函数

### GrBackendSemaphores 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendSemaphore MakeMtl(GrMTLHandle event, uint64_t value)` | 创建包装了 Metal 事件的 `GrBackendSemaphore` 对象 |
| `GrMTLHandle GetMtlHandle(const GrBackendSemaphore&)` | 从信号量对象中提取 Metal 事件句柄 |
| `uint64_t GetMtlValue(const GrBackendSemaphore&)` | 从信号量对象中提取信号量值 |

### 使用示例

```cpp
// 创建 Metal 事件（Objective-C 代码）
id<MTLEvent> mtlEvent = [device newEvent];

// 包装为 Skia 信号量
GrBackendSemaphore skSem = GrBackendSemaphores::MakeMtl((__bridge GrMTLHandle)mtlEvent, 1);

// 稍后提取 Metal 事件和值
GrMTLHandle extractedEvent = GrBackendSemaphores::GetMtlHandle(skSem);
uint64_t value = GrBackendSemaphores::GetMtlValue(skSem);
```

### 引用管理要求

**重要**: 创建信号量时的引用管理责任：

```cpp
// 创建者必须使用 __bridge_retained 增加引用计数
id<MTLEvent> event = [device newEvent];
GrBackendSemaphore sem = GrBackendSemaphores::MakeMtl(
    (__bridge_retained GrMTLHandle)event, 1);

// 接收者使用 __bridge_transfer 接管引用
id<MTLEvent> receivedEvent = (__bridge_transfer id<MTLEvent>)GetMtlHandle(sem);
```

## 内部实现细节

### ARC 编译要求

文件使用 Objective-C++ 和 ARC（Automatic Reference Counting）：

```cpp
#if !__has_feature(objc_arc)
#error This file must be compiled with Arc. Use -fobjc-arc flag
#endif
```

ARC 自动管理 Objective-C 对象的引用计数。

### 类型安全的转换

使用辅助函数 `get_and_cast_data()` 确保类型安全：

```cpp
static const GrMtlBackendSemaphoreData* get_and_cast_data(const GrBackendSemaphore& sem) {
    auto data = GrBackendSemaphorePriv::GetBackendData(sem);
    SkASSERT(!data || data->type() == GrBackendApi::kMetal);
    return static_cast<const GrMtlBackendSemaphoreData*>(data);
}
```

### 信号量创建流程

`MakeMtl()` 函数的实现：

```cpp
GrBackendSemaphore MakeMtl(GrMTLHandle event, uint64_t value) {
    GrMtlBackendSemaphoreData data(event, value);
    return GrBackendSemaphorePriv::MakeGrBackendSemaphore(GrBackendApi::kMetal, data);
}
```

**流程**:
1. 创建 `GrMtlBackendSemaphoreData` 临时对象，存储事件句柄和值
2. 调用私有构造函数创建 `GrBackendSemaphore` 对象
3. 返回包装后的信号量对象

### 事件句柄提取

`GetMtlHandle()` 函数的实现：

```cpp
GrMTLHandle GetMtlHandle(const GrBackendSemaphore& sem) {
    SkASSERT(sem.backend() == GrBackendApi::kMetal);
    const GrMtlBackendSemaphoreData* data = get_and_cast_data(sem);
    SkASSERT(data);
    return data->event();
}
```

**安全检查**:
1. 断言信号量后端类型为 Metal
2. 获取并转换为 Metal 数据对象
3. 断言数据对象有效
4. 返回事件句柄

### 信号量值提取

`GetMtlValue()` 函数的实现类似，提取 64 位值。

### 时间线信号量语义

Metal 事件采用时间线信号量模型：

- **值单调递增**: 每次信号操作使用递增的值
- **等待特定值**: 可以等待事件达到或超过特定值
- **多次信号**: 同一事件可以多次信号不同的值
- **灵活同步**: 支持比二进制信号量更复杂的同步模式

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrBackendSemaphore` | 提供信号量抽象接口 |
| `GrBackendSemaphorePriv` | 访问信号量的私有构造函数 |
| `GrMtlTypes` | 定义 `GrMTLHandle` 类型 |
| `GrTypes` | 提供 Ganesh 基础类型 |
| `SkAssert` | 提供断言宏 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrMtlGpu` | 创建和使用 Metal 事件进行同步 |
| `GrMtlCommandBuffer` | 在命令缓冲区中编码信号和等待操作 |
| `GrContext` | 跨队列操作时使用信号量 |
| 互操作代码 | 与外部 Metal 资源交互时传递信号量 |

## 设计模式与设计决策

### 1. 适配器模式

将 Metal 的 `MTLEvent` 适配为 Skia 的 `GrBackendSemaphore` 接口。

### 2. 工厂函数模式

使用命名空间函数 `MakeMtl()` 作为工厂函数，提供清晰的创建接口。

### 3. 类型擦除（Type Erasure）

使用 `AnySemaphoreData` 容器存储不同后端的信号量数据。

### 4. 时间线信号量模型

采用值语义的时间线信号量，比传统二进制信号量更灵活。

### 5. 命名空间作用域

使用 `GrBackendSemaphores` 命名空间而非类静态方法，减少头文件依赖。

### 6. 显式引用管理

文档明确说明引用管理责任，避免内存泄漏。

### 7. 句柄传递语义

信号量使用 Metal 事件句柄表示，引用计数由 ARC 管理。

## 性能考量

### 1. 零开销抽象

信号量对象仅存储一个 Metal 事件句柄和一个 64 位整数，内存开销极小。

### 2. ARC 优化

ARC 的引用计数操作由编译器优化，通常比手动管理更高效。

### 3. 内联函数

`event()` 和 `value()` 等访问器函数可以被编译器内联。

### 4. 时间线信号量优势

单个 Metal 事件可以表示多个同步点，减少事件对象的创建和销毁。

### 5. 编译期类型检查

使用断言在调试模式下检查类型，发布版本不产生额外开销。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/GrBackendSemaphore.h` | 后端信号量抽象接口 |
| `src/gpu/ganesh/GrBackendSemaphorePriv.h` | 信号量私有构造函数 |
| `include/gpu/ganesh/mtl/GrMtlTypes.h` | Metal 类型定义 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 基础类型 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | Metal GPU 实现 |
| `src/gpu/ganesh/mtl/GrMtlCommandBuffer.h` | Metal 命令缓冲区 |
