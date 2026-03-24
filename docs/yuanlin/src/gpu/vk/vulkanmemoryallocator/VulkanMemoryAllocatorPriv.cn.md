# VulkanMemoryAllocatorPriv

> 源文件:
> - `src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorPriv.h`

## 概述

`VulkanMemoryAllocatorPriv.h` 定义了 Vulkan 内存分配器的内部工厂接口。它提供了一个函数用于创建 `VulkanMemoryAllocator` 的具体实现。由于内存分配器的某些配置是编译期决定的，该接口不直接暴露给客户端，仅供 Skia 内部使用。

## 架构位置

```
Skia GPU 层
  └── Vulkan 后端
        └── VulkanMemoryAllocators 命名空间
              └── Make() (工厂函数，创建具体的内存分配器实现)
```

## 主要类与结构体

### `skgpu::VulkanMemoryAllocators` 命名空间
包含内存分配器的工厂函数。实际实现通常基于 VMA（Vulkan Memory Allocator）库。

## 公共 API 函数

- **`Make(const skgpu::VulkanBackendContext&, ThreadSafe) -> sk_sp<VulkanMemoryAllocator>`**：创建 Vulkan 内存分配器的具体实现。
  - `VulkanBackendContext` 提供 Vulkan 实例、设备、物理设备等信息。
  - `ThreadSafe` 枚举参数指定分配器是否需要线程安全（`true` 表示内部加锁保护，`false` 表示调用者负责同步）。

## 内部实现细节

该头文件仅声明接口。具体实现位于同目录下的 `.cpp` 文件中，通常使用 AMD 的 VMA (Vulkan Memory Allocator) 库来管理 GPU 内存的分配、子分配和回收。编译期配置（如 VMA 版本和编译选项）使得此接口无法以有意义的方式暴露给客户端。

## 依赖关系

- **Skia 核心**: `SkRefCnt`（`sk_sp`）
- **Vulkan 后端**: `VulkanBackendContext`、`VulkanMemoryAllocator`、`SkiaVulkan.h`

## 设计模式与设计决策

1. **工厂模式**：通过工厂函数隐藏具体实现类型，客户端只需通过 `VulkanMemoryAllocator` 抽象接口使用。
2. **线程安全可配置**：通过 `ThreadSafe` 参数让调用者根据使用场景选择是否需要线程安全，避免不必要的同步开销。
3. **内部 API 隔离**：编译期配置的存在使此接口必须保持内部可见性。

## 性能考量

- `ThreadSafe` 参数允许在单线程场景下避免互斥锁开销。
- 底层 VMA 库提供高效的子分配和内存池管理。

## 相关文件

- `include/gpu/vk/VulkanMemoryAllocator.h` - 内存分配器抽象接口
- `include/private/gpu/vk/SkiaVulkan.h` - Vulkan 类型定义
- `src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorPriv.cpp` - 具体实现
