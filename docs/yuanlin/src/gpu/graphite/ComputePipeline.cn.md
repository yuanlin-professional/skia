# ComputePipeline (计算管线)

> 源文件：[src/gpu/graphite/ComputePipeline.h](../../../../src/gpu/graphite/ComputePipeline.h)、[src/gpu/graphite/ComputePipeline.cpp](../../../../src/gpu/graphite/ComputePipeline.cpp)

## 概述

`ComputePipeline` 是 Graphite 中 GPU 计算管线资源的抽象基类。它对应后端特定的计算管线对象：Metal 的 `MTLComputePipelineState`、Dawn 的 `CreateComputePipeline`、D3D12 的 `CreateComputePipelineState` 或 Vulkan 的 `VkComputePipelineCreateInfo`。

作为 `Resource` 的子类，`ComputePipeline` 纳入 Graphite 的资源缓存和生命周期管理系统。计算管线主要用于 GPU 路径光栅化（Vello）和其他计算着色器工作负载。

## 架构位置

`ComputePipeline` 位于计算着色器执行管线中：

- **上游**：`ResourceProvider::findOrCreateComputePipeline()` 创建或查找缓存的计算管线。
- **下游**：`CommandBuffer::addComputePass()` 在计算调度中绑定计算管线。
- **后端子类**：`MtlComputePipeline`、`VulkanComputePipeline`、`DawnComputePipeline` 封装各自 API 的管线对象。

## 主要类与结构体

### `ComputePipeline` (继承自 Resource)
抽象基类，定义计算管线的资源接口。

**关键特性：**
- GPU 内存大小为 0（管线对象通常不占用显著的 GPU 内存）。
- 资源类型标识为 `"Compute Pipeline"`。
- 所有权为 `Ownership::kOwned`。

## 公共 API 函数

### `getResourceType() -> const char*`
返回 `"Compute Pipeline"`，用于调试和内存统计。

## 内部实现细节

`ComputePipeline` 的构造函数将 GPU 内存大小设为 0 传递给 `Resource` 基类。这意味着计算管线：
- 不计入 GPU 内存预算。
- 在 `ResourceCache` 中不会因为预算超支而被清除（使用 `kMaxUseToken`）。
- 可以长期保留在缓存中以避免重复编译。

未来计划支持返回有效的本地工作组大小，特别是当着色器中通过特化常量静态指定工作组大小时。

## 依赖关系

### 上游依赖
- `Resource`：GPU 资源基类，提供缓存和引用计数管理。
- `SharedContext`：共享上下文。

### 下游使用者
- 后端子类：`MtlComputePipeline`、`VulkanComputePipeline`、`DawnComputePipeline`。
- `ResourceProvider`：创建和缓存计算管线。
- `DispatchGroup`：计算调度中绑定管线。
- `CommandBuffer`：执行计算通道。

## 设计模式与设计决策

1. **零内存预算**：与采样器类似，管线对象不占用显著 GPU 内存，零大小确保不被 LRU 清除策略误删。缓存对性能至关重要，因为管线编译通常非常昂贵。

2. **轻量基类**：基类仅定义资源接口，所有实质性的管线配置和编译由后端子类负责。

3. **缓存友好**：计算管线通过 `ComputePipelineDesc` 生成唯一键，相同配置的管线可以跨 Recording 和 Recorder 复用。

## 性能考量

- 计算管线编译在 GPU API 层面通常非常昂贵（涉及着色器编译和优化），缓存是关键优化。
- 零内存大小确保管线不会被缓存清除策略删除。
- 管线在全局级别缓存（通过 `GlobalCache` 或 Context 级别的 `ResourceCache`），支持跨 Recorder 共享。

## 相关文件

- `src/gpu/graphite/Resource.h/.cpp`：资源基类。
- `src/gpu/graphite/ResourceProvider.h/.cpp`：计算管线创建和缓存。
- `src/gpu/graphite/ComputePipelineDesc.h`：计算管线描述。
- `src/gpu/graphite/compute/DispatchGroup.h/.cpp`：计算调度组。
- `src/gpu/graphite/mtl/MtlComputePipeline.h/.mm`：Metal 计算管线实现。
- `src/gpu/graphite/vk/VulkanComputePipeline.h/.cpp`：Vulkan 计算管线实现。
- `src/gpu/graphite/dawn/DawnComputePipeline.h/.cpp`：Dawn 计算管线实现。
