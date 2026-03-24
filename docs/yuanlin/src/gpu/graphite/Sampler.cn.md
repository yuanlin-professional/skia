# Sampler (采样器)

> 源文件：[src/gpu/graphite/Sampler.h](../../../../src/gpu/graphite/Sampler.h)、[src/gpu/graphite/Sampler.cpp](../../../../src/gpu/graphite/Sampler.cpp)

## 概述

`Sampler` 是 Graphite 中 GPU 采样器资源的抽象基类。采样器定义了纹理采样时的过滤模式、寻址模式和其他采样参数。`Sampler` 继承自 `Resource`，因此纳入 Graphite 的资源缓存和生命周期管理系统。

作为基类，`Sampler` 本身仅提供最基本的框架。具体的采样器功能由后端子类（Metal、Vulkan、Dawn）实现，它们封装各自 API 的采样器对象。

## 架构位置

`Sampler` 位于资源抽象层：

- **上游**：`ResourceProvider` 创建和缓存 `Sampler` 实例。
- **下游**：`DrawPass` 在绑定纹理时关联对应的采样器。
- **后端子类**：`MtlSampler`、`VulkanSampler`、`DawnSampler` 封装各自 API 的采样器对象。

## 主要类与结构体

### `Sampler` (继承自 Resource)
抽象基类，定义采样器的资源接口。

**关键特性：**
- GPU 内存大小为 0（采样器通常不占用显著的 GPU 内存）。
- 资源类型标识为 `"Sampler"`。
- 所有权为 `Ownership::kOwned`。

## 公共 API 函数

### `getResourceType() -> const char*`
返回 `"Sampler"`，用于调试和内存统计。

## 内部实现细节

`Sampler` 的构造函数将 GPU 内存大小设为 0 传递给 `Resource` 基类。这意味着采样器：
- 不计入 GPU 内存预算。
- 在 `ResourceCache` 中不会因为预算超支而被清除（使用 `kMaxUseToken`）。
- 可以长期保留在缓存中以最大化复用。

## 依赖关系

### 上游依赖
- `Resource`：GPU 资源基类，提供缓存和引用计数管理。
- `SharedContext`：共享上下文。

### 下游使用者
- 后端子类：`MtlSampler`、`VulkanSampler`、`DawnSampler`。
- `ResourceProvider`：创建和缓存采样器。
- `DrawPass`：绑定采样器到绘制命令。

## 设计模式与设计决策

1. **零内存预算**：采样器不占用显著 GPU 内存，设为零大小可避免不必要的缓存清除，同时保留在缓存中以减少创建开销。

2. **轻量基类**：基类仅定义资源接口，所有实质性的采样器配置由后端子类负责。

## 性能考量

- 采样器创建在 GPU API 层面相对昂贵，缓存对性能至关重要。
- 零内存大小确保采样器不会被 LRU 清除策略误删。

## 相关文件

- `src/gpu/graphite/Resource.h/.cpp`：资源基类。
- `src/gpu/graphite/ResourceProvider.h/.cpp`：采样器创建和缓存。
- `src/gpu/graphite/mtl/MtlSampler.h/.mm`：Metal 采样器实现。
- `src/gpu/graphite/vk/VulkanSampler.h/.cpp`：Vulkan 采样器实现。
- `src/gpu/graphite/dawn/DawnSampler.h/.cpp`：Dawn 采样器实现。
