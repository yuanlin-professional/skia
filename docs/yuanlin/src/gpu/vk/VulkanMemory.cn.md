# VulkanMemory - Vulkan 内存操作工具函数

> 源文件: `src/gpu/vk/VulkanMemory.h`, `src/gpu/vk/VulkanMemory.cpp`

## 概述

`VulkanMemory` 是一个命名空间，提供了一组用于 Vulkan GPU 内存分配、释放、映射和同步的工具函数。它在 `VulkanMemoryAllocator` 抽象接口之上封装了更高级的策略逻辑，例如根据缓冲区用途自动决定内存属性标志，以及处理非一致性（non-coherent）内存的对齐和刷新。

## 架构位置

`VulkanMemory` 位于 Skia GPU 后端的 Vulkan 公共层（`src/gpu/vk/`），是 Ganesh 和 Graphite 共享的内存管理中间层：

```
应用层 / Skia 内部
      |
VulkanMemory (策略层 - 本文件)
      |
VulkanMemoryAllocator (抽象接口)
      |
VulkanAMDMemoryAllocator (VMA 实现)
      |
Vulkan 驱动
```

## 主要类与结构体

### 命名空间 `skgpu::VulkanMemory`

该命名空间不包含类定义，仅包含自由函数。

### 类型别名

```cpp
using CheckResult = bool(VkResult);
```

回调函数类型，用于检查 Vulkan 操作结果。调用者通过此回调实现自定义的错误处理策略。

## 公共 API 函数

### `AllocBufferMemory()`

```cpp
bool AllocBufferMemory(VulkanMemoryAllocator*, VkBuffer buffer,
                       Protected isProtected, BufferUsage,
                       bool shouldPersistentlyMapCpuToGpu,
                       const std::function<CheckResult>&, VulkanAlloc* alloc);
```

为 Vulkan 缓冲区分配内存。根据 `BufferUsage` 和 `shouldPersistentlyMapCpuToGpu` 参数自动决定内存属性：
- CPU 到 GPU 传输缓冲区或需要持久映射的 CPU 写入缓冲区：设置 `kPersistentlyMapped` 标志。
- 受保护内存：追加 `kProtected` 标志。

### `FreeBufferMemory()`

释放缓冲区内存。内部通过 `allocator->freeMemory()` 委托给具体分配器。

### `AllocImageMemory()`

```cpp
bool AllocImageMemory(VulkanMemoryAllocator*, VkImage image,
                      Protected isProtected, bool forceDedicatedMemory,
                      bool useLazyAllocation,
                      const std::function<CheckResult>&, VulkanAlloc* alloc);
```

为 Vulkan 图像分配内存。支持以下策略：
- **专用分配** (`forceDedicatedMemory`): 强制使用 `kDedicatedAllocation` 标志。
- **延迟分配** (`useLazyAllocation`): 设置 `kLazyAllocation` 标志（用于移动端 tile-based GPU）。
- **受保护内存**: 设置 `kProtected` 标志。

### `FreeImageMemory()`

释放图像内存。

### `MapAlloc()` / `UnmapAlloc()`

```cpp
void* MapAlloc(VulkanMemoryAllocator*, const VulkanAlloc&,
               const std::function<CheckResult>&);
void UnmapAlloc(VulkanMemoryAllocator*, const VulkanAlloc&);
```

映射/取消映射整个 `VulkanAlloc` 块。返回的指针指向分配块的起始位置。

### `FlushMappedAlloc()` / `InvalidateMappedAlloc()`

```cpp
void FlushMappedAlloc(VulkanMemoryAllocator*, const VulkanAlloc&,
                      VkDeviceSize offset, VkDeviceSize size,
                      const std::function<CheckResult>&);
void InvalidateMappedAlloc(VulkanMemoryAllocator*, const VulkanAlloc&,
                           VkDeviceSize offset, VkDeviceSize size,
                           const std::function<CheckResult>&);
```

仅当内存标记为 `kNoncoherent_Flag` 时执行刷新/失效操作。`offset` 相对于 `VulkanAlloc` 的起始位置（通常为 0）。

### `GetNonCoherentMappedMemoryRange()`

```cpp
void GetNonCoherentMappedMemoryRange(const VulkanAlloc&,
                                     VkDeviceSize offset, VkDeviceSize size,
                                     VkDeviceSize alignment,
                                     VkMappedMemoryRange*);
```

计算对齐后的 `VkMappedMemoryRange`，用于非一致性内存的刷新/失效。对齐逻辑：
- 向下对齐 `offset`（减去偏移余量）。
- 向上对齐 `size`（按 `nonCoherentAtomSize` 边界对齐）。

## 内部实现细节

### 内存属性标志决策

`AllocBufferMemory` 中的属性标志逻辑：

```cpp
if (usage == BufferUsage::kTransfersFromCpuToGpu ||
    (usage == BufferUsage::kCpuWritesGpuReads && shouldPersistentlyMapCpuToGpu)) {
    propFlags = kPersistentlyMapped_AllocationPropertyFlag;
}
```

对于 CPU 写入 GPU 读取的场景，持久映射通常是更好的选择，因为它避免了反复的 map/unmap 开销。

### 对齐计算

`GetNonCoherentMappedMemoryRange` 使用位运算进行高效对齐：
```cpp
VkDeviceSize offsetDiff = offset & (alignment - 1);  // 计算偏移余量
offset = offset - offsetDiff;                          // 向下对齐
size = (size + alignment - 1) & ~(alignment - 1);    // 向上对齐
```

## 依赖关系

- **上游依赖**: `VulkanMemoryAllocator`（抽象分配器接口）、`VulkanTypes.h`（`VulkanAlloc` 结构体）、`GpuTypes.h`（`Protected` 枚举）。
- **被依赖**: Ganesh 和 Graphite 的 Vulkan GPU 实现层，用于所有资源（缓冲区、纹理）的内存管理。

## 设计模式与设计决策

1. **策略封装**: 将内存分配策略（如属性标志选择）从具体分配器中解耦，使 `VulkanMemoryAllocator` 的实现保持简洁。
2. **回调式错误处理**: 使用 `std::function<CheckResult>` 让调用者自定义错误检查行为，支持 Ganesh 和 Graphite 各自不同的错误处理策略。
3. **透明的一致性处理**: Flush/Invalidate 函数内部检查 `kNoncoherent_Flag`，使调用者无需关心内存类型细节。

## 性能考量

- 持久映射策略（`kPersistentlyMapped`）减少了频繁 map/unmap 的系统调用开销。
- 延迟分配（`kLazyAllocation`）在移动 GPU 上避免为仅 GPU 使用的资源实际分配物理内存。
- 对齐计算使用位运算，无分支和除法，性能开销极低。
- 一致性内存（coherent）的 Flush/Invalidate 操作被短路跳过（检查标志后直接返回）。

## 相关文件

- `include/gpu/vk/VulkanMemoryAllocator.h` - 内存分配器抽象接口
- `include/gpu/vk/VulkanTypes.h` - `VulkanAlloc`、`VulkanBackendMemory` 等类型定义
- `src/gpu/vk/vulkanmemoryallocator/VulkanAMDMemoryAllocator.h` - VMA 实现
- `src/gpu/vk/VulkanInterface.h` - Vulkan 函数指针接口
