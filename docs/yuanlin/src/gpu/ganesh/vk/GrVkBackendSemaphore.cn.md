# GrVkBackendSemaphore

> 源文件
> - include/gpu/ganesh/vk/GrVkBackendSemaphore.h
> - src/gpu/ganesh/vk/GrVkBackendSemaphore.cpp

## 概述

`GrVkBackendSemaphore` 模块为 Ganesh 渲染引擎提供 Vulkan 后端信号量（Semaphore）的封装和管理功能。信号量是 Vulkan 中用于同步 GPU 操作的重要机制，该模块将 Vulkan 原生的 `VkSemaphore` 对象包装为 Skia 的 `GrBackendSemaphore` 抽象接口，使上层代码能够以统一的方式处理跨后端的同步操作。

该模块主要用于跨队列同步、与外部图形 API 互操作（如 Vulkan 与 OpenGL 之间）以及多帧资源管理等场景。

## 架构位置

该模块位于 Ganesh Vulkan 后端的同步原语层：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── Synchronization Abstraction
    │   └── GrBackendSemaphore       ← 抽象接口
    └── Backend Implementations
        └── Vulkan Backend
            ├── GrVkBackendSemaphore  ← 当前模块（Vulkan 实现）
            ├── GrVkGpu               ← GPU 实现
            └── GrVkSemaphore         ← 内部信号量管理
```

## 主要类与结构体

### GrVkBackendSemaphoreData

Vulkan 后端信号量数据类，封装 Vulkan 信号量句柄。

**继承关系**: `GrVkBackendSemaphoreData` → `GrBackendSemaphoreData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSemaphore` | `VkSemaphore` | Vulkan 信号量句柄 |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `semaphore()` | 返回 Vulkan 信号量句柄 |
| `copyTo(AnySemaphoreData&)` | 将数据复制到类型擦除容器 |
| `type()` | 返回后端 API 类型（调试模式） |

**构造函数**
```cpp
GrVkBackendSemaphoreData(VkSemaphore semaphore)
```
接受 Vulkan 信号量句柄作为参数。

## 公共 API 函数

### GrBackendSemaphores 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendSemaphore MakeVk(VkSemaphore semaphore)` | 创建包装了 Vulkan 信号量的 `GrBackendSemaphore` 对象 |
| `VkSemaphore GetVkSemaphore(const GrBackendSemaphore&)` | 从 `GrBackendSemaphore` 对象中提取 Vulkan 信号量句柄 |

### 使用示例

```cpp
// 创建 Vulkan 信号量
VkSemaphore vkSem = ...; // 通过 vkCreateSemaphore 创建

// 包装为 Skia 信号量
GrBackendSemaphore skSem = GrBackendSemaphores::MakeVk(vkSem);

// 稍后提取 Vulkan 信号量
VkSemaphore extractedSem = GrBackendSemaphores::GetVkSemaphore(skSem);
```

## 内部实现细节

### 类型安全的转换

使用辅助函数 `get_and_cast_data()` 确保类型安全：

```cpp
static const GrVkBackendSemaphoreData* get_and_cast_data(const GrBackendSemaphore& sem) {
    auto data = GrBackendSemaphorePriv::GetBackendData(sem);
    SkASSERT(!data || data->type() == GrBackendApi::kVulkan);
    return static_cast<const GrVkBackendSemaphoreData*>(data);
}
```

该函数：
1. 从 `GrBackendSemaphore` 中获取后端数据
2. 断言数据类型为 Vulkan
3. 安全地转换为 `GrVkBackendSemaphoreData*`

### 信号量创建流程

`MakeVk()` 函数的实现：

```cpp
GrBackendSemaphore MakeVk(VkSemaphore semaphore) {
    GrVkBackendSemaphoreData data(semaphore);
    return GrBackendSemaphorePriv::MakeGrBackendSemaphore(GrBackendApi::kVulkan, data);
}
```

流程：
1. 创建 `GrVkBackendSemaphoreData` 临时对象，存储 Vulkan 信号量句柄
2. 调用私有构造函数创建 `GrBackendSemaphore` 对象
3. 返回包装后的信号量对象

### 信号量提取流程

`GetVkSemaphore()` 函数的实现：

```cpp
VkSemaphore GetVkSemaphore(const GrBackendSemaphore& sem) {
    SkASSERT(sem.backend() == GrBackendApi::kVulkan);
    const GrVkBackendSemaphoreData* data = get_and_cast_data(sem);
    SkASSERT(data);
    return data->semaphore();
}
```

流程：
1. 断言信号量后端类型为 Vulkan
2. 获取并转换为 Vulkan 数据对象
3. 断言数据对象有效
4. 返回 Vulkan 信号量句柄

### 数据复制机制

`copyTo()` 方法使用类型擦除容器存储数据：

```cpp
void copyTo(AnySemaphoreData& data) const override {
    data.emplace<GrVkBackendSemaphoreData>(fSemaphore);
}
```

使用 `std::variant` 风格的容器，支持不同后端的信号量数据类型。

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrBackendSemaphore` | 提供信号量抽象接口 |
| `GrBackendSemaphorePriv` | 访问信号量的私有构造函数 |
| `SkiaVulkan.h` | 包含 Vulkan 类型定义 |
| `GrTypes` | 提供 Ganesh 基础类型 |
| `SkAssert` | 提供断言宏 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrVkGpu` | 创建和使用 Vulkan 信号量进行同步 |
| `GrContext` | 跨队列操作时使用信号量 |
| `GrSurface` | 表面间数据传输时使用信号量 |
| 互操作代码 | 与其他图形 API 交互时传递信号量 |

## 设计模式与设计决策

### 1. 适配器模式

将 Vulkan 的 `VkSemaphore` 适配为 Skia 的 `GrBackendSemaphore` 接口，使上层代码无需了解 Vulkan 细节。

### 2. 工厂函数模式

使用命名空间函数 `MakeVk()` 作为工厂函数，提供清晰的创建接口。

### 3. 类型擦除（Type Erasure）

使用 `AnySemaphoreData` 容器存储不同后端的信号量数据，避免虚函数调用开销。

### 4. PIMPL 轻量级变体

`GrBackendSemaphore` 持有指向 `GrVkBackendSemaphoreData` 的指针，实现接口和实现分离。

### 5. 命名空间作用域

使用 `GrBackendSemaphores` 命名空间而非类静态方法，减少头文件依赖。

### 6. 句柄传递语义

信号量使用 Vulkan 句柄（整数或指针）表示，不拥有资源所有权，由外部管理生命周期。

## 性能考量

### 1. 零开销抽象

信号量对象仅存储一个 Vulkan 句柄（通常是 64 位整数），没有额外内存开销。

### 2. 内联函数

`semaphore()` 等访问器函数可以被编译器内联，消除函数调用开销。

### 3. 编译期类型检查

使用断言在调试模式下检查类型，发布版本不产生额外开销。

### 4. 值复制优化

`copyTo()` 方法仅复制一个句柄，是非常轻量的操作。

### 5. 无虚函数调用（部分场景）

在已知后端类型的情况下，编译器可以优化掉虚函数调用。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/GrBackendSemaphore.h` | 后端信号量抽象接口 |
| `src/gpu/ganesh/GrBackendSemaphorePriv.h` | 信号量私有构造函数 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型定义 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 基础类型 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | Vulkan GPU 实现 |
| `src/gpu/ganesh/vk/GrVkSemaphore.h` | Vulkan 内部信号量管理 |
| `include/gpu/ganesh/vk/GrVkTypes.h` | Vulkan 类型定义 |
