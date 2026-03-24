# GrVkCommandPool - Vulkan 命令池

> 源文件: `src/gpu/ganesh/vk/GrVkCommandPool.h`, `src/gpu/ganesh/vk/GrVkCommandPool.cpp`

## 概述

`GrVkCommandPool` 封装了 Vulkan 的 `VkCommandPool`，管理从中分配的主命令缓冲区和次级命令缓冲区。它继承自 `GrVkManagedResource`，通过 Ganesh 的资源管理系统追踪生命周期。每个命令池拥有一个主命令缓冲区和一个可回收的次级命令缓冲区池。

## 架构位置

```
GrVkGpu
    |
GrVkCommandPool (本文件)
    |
    +-- GrVkPrimaryCommandBuffer (1个，拥有)
    +-- GrVkSecondaryCommandBuffer (多个，池化)
    |
VkCommandPool (Vulkan API)
```

命令池是 Vulkan 资源管理的基本单位，所有命令缓冲区的分配和释放都通过命令池进行。

## 主要类与结构体

### `GrVkCommandPool`

继承自 `GrVkManagedResource`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fOpen` | `bool` | 池是否处于开放状态 |
| `fCommandPool` | `VkCommandPool` | Vulkan 命令池句柄 |
| `fPrimaryCommandBuffer` | `unique_ptr<GrVkPrimaryCommandBuffer>` | 主命令缓冲区 |
| `fAvailableSecondaryBuffers` | `STArray<4, unique_ptr<Secondary>>` | 可用的次级命令缓冲区 |
| `fMaxCachedSecondaryCommandBuffers` | `int` | 最大缓存次级缓冲区数 |

## 公共 API 函数

### `Create()`

```cpp
static GrVkCommandPool* Create(GrVkGpu* gpu);
```

创建命令池并分配主命令缓冲区。

### `reset()`

```cpp
void reset(GrVkGpu* gpu);
```

重置命令池，回收所有命令缓冲区的资源。调用 `vkResetCommandPool`。

### `getPrimaryCommandBuffer()`

```cpp
GrVkPrimaryCommandBuffer* getPrimaryCommandBuffer();
```

返回此池的主命令缓冲区。

### `findOrCreateSecondaryCommandBuffer()`

```cpp
std::unique_ptr<GrVkSecondaryCommandBuffer> findOrCreateSecondaryCommandBuffer(GrVkGpu* gpu);
```

从可用池中获取或新建次级命令缓冲区。

### `recycleSecondaryCommandBuffer()`

```cpp
void recycleSecondaryCommandBuffer(GrVkSecondaryCommandBuffer* buffer);
```

将用完的次级缓冲区回收到可用池中（受 `fMaxCachedSecondaryCommandBuffers` 限制）。

### `close()` / `isOpen()`

标记命令池为关闭状态，防止继续创建或写入命令缓冲区。

## 内部实现细节

### 命令池生命周期

1. `Create`: 创建 VkCommandPool + 分配主 VkCommandBuffer。
2. 使用期间：通过 `findOrCreateSecondaryCommandBuffer` 按需分配次级缓冲区。
3. `close`: 标记关闭，不再接受新的命令。
4. `reset`: 重置整个池，命令缓冲区状态回到初始。
5. `freeGPUData` (析构): 销毁 VkCommandPool 及其所有缓冲区。

### 次级缓冲区池化

`fAvailableSecondaryBuffers` 维护一个小型的次级命令缓冲区池（预分配 4 个），避免频繁的 `vkAllocateCommandBuffers` 调用。超出 `fMaxCachedSecondaryCommandBuffers` 限制的缓冲区不会被缓存。

### 资源追踪

继承 `GrVkManagedResource` 支持 `SK_TRACE_MANAGED_RESOURCES` 模式下的资源调试追踪。

## 依赖关系

- **上游依赖**: `GrVkGpu`（创建和管理命令池）。
- **核心依赖**: `GrVkPrimaryCommandBuffer`、`GrVkSecondaryCommandBuffer`。
- **资源管理**: `GrVkManagedResource` / `GrManagedResource`。
- **被依赖**: `GrVkGpu` 通过命令池管理所有命令提交。

## 设计模式与设计决策

1. **池化模式**: 次级命令缓冲区回收复用，减少 Vulkan 分配调用。
2. **一池一主**: 每个命令池固定关联一个主命令缓冲区，简化管理。
3. **开放/关闭状态**: 明确的生命周期阶段，防止在已提交的命令池上误写入。
4. **受管资源**: 通过 `GrVkManagedResource` 集成到 Ganesh 资源跟踪系统。

## 性能考量

- `vkResetCommandPool` 批量重置比逐个重置命令缓冲区更高效。
- 次级缓冲区的池化避免了频繁的分配/释放开销。
- `STArray<4>` 预分配避免小场景下的堆分配。
- `fMaxCachedSecondaryCommandBuffers` 限制内存使用，防止缓存过多闲置缓冲区。

## 相关文件

- `src/gpu/ganesh/vk/GrVkCommandBuffer.h` - 命令缓冲区定义
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现
- `src/gpu/ganesh/vk/GrVkManagedResource.h` - Vulkan 受管资源基类
- `src/gpu/ganesh/GrManagedResource.h` - 通用受管资源基类
