# VulkanAMDMemoryAllocator - 基于 VMA 的 Vulkan 内存分配器

> 源文件: `src/gpu/vk/vulkanmemoryallocator/VulkanAMDMemoryAllocator.h`, `src/gpu/vk/vulkanmemoryallocator/VulkanAMDMemoryAllocator.cpp`

## 概述

`VulkanAMDMemoryAllocator` 是 Skia 对 AMD 开源的 Vulkan Memory Allocator (VMA) 库的封装实现。它实现了 `VulkanMemoryAllocator` 抽象接口，为 Skia 的 Vulkan 后端提供高效的 GPU 内存管理。VMA 通过子分配（suballocation）策略将多个小的 Vulkan 资源打包到更大的内存块中，减少了驱动级内存分配的次数和碎片。

## 架构位置

```
Skia 渲染层 (Ganesh / Graphite)
      |
VulkanMemory (策略层)
      |
VulkanMemoryAllocator (抽象接口)
      |
VulkanAMDMemoryAllocator (本文件 - VMA 实现)
      |
VMA (vk_mem_alloc.h - 第三方库)
      |
Vulkan 驱动
```

该类是 Skia 默认使用的 Vulkan 内存分配器实现。客户端也可以提供自定义的 `VulkanMemoryAllocator` 实现来替代它。

## 主要类与结构体

### `VulkanAMDMemoryAllocator`

继承自 `VulkanMemoryAllocator`（引用计数接口），封装了一个 `VmaAllocator` 句柄。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fAllocator` | `VmaAllocator` | VMA 分配器句柄 |

### `VulkanMemoryAllocators` 命名空间

提供便捷的工厂函数 `Make()`，根据 `VulkanBackendContext` 自动创建完整的分配器实例。

## 公共 API 函数

### `Make()` 工厂方法

```cpp
static sk_sp<VulkanMemoryAllocator> Make(VkInstance instance,
                                          VkPhysicalDevice physicalDevice,
                                          VkDevice device,
                                          uint32_t physicalDeviceVersion,
                                          const VulkanExtensions* extensions,
                                          const VulkanInterface* interface,
                                          ThreadSafe);
```

创建 VMA 分配器实例：
1. 从 `VulkanInterface` 拷贝所需的 Vulkan 函数指针到 `VmaVulkanFunctions`。
2. 配置 VMA：4MB 首选块大小、支持 KHR 专用分配、可选外部同步。
3. 将 API 版本限制到 Vulkan 1.1。

### `allocateImageMemory()`

```cpp
VkResult allocateImageMemory(VkImage image, uint32_t allocationPropertyFlags,
                              VulkanBackendMemory*) override;
```

为图像分配设备本地内存。支持专用分配、延迟分配和受保护内存标志。

### `allocateBufferMemory()`

```cpp
VkResult allocateBufferMemory(VkBuffer buffer, BufferUsage usage,
                               uint32_t allocationPropertyFlags,
                               VulkanBackendMemory*) override;
```

根据 `BufferUsage` 选择内存属性：

| BufferUsage | 必需属性 | 首选属性 |
|-------------|----------|----------|
| `kGpuOnly` | DEVICE_LOCAL | - |
| `kCpuWritesGpuReads` | HOST_VISIBLE + HOST_COHERENT | DEVICE_LOCAL |
| `kTransfersFromCpuToGpu` | HOST_VISIBLE + HOST_COHERENT | - |
| `kTransfersFromGpuToCpu` | HOST_VISIBLE | HOST_CACHED |

### `freeMemory()`

释放 VMA 分配。将 `VulkanBackendMemory` 转换回 `VmaAllocation` 后调用 `vmaFreeMemory`。

### `getAllocInfo()`

```cpp
void getAllocInfo(const VulkanBackendMemory&, VulkanAlloc*) const override;
```

查询分配信息（设备内存、偏移、大小）并推断标志（可映射、非一致性、延迟分配）。

### `mapMemory()` / `unmapMemory()`

映射/取消映射内存区域。直接委托给 VMA 的 `vmaMapMemory`/`vmaUnmapMemory`。

### `flushMemory()` / `invalidateMemory()`

刷新/失效 VMA 分配的内存范围。

### `totalAllocatedAndUsedMemory()`

```cpp
std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const override;
```

返回 `{blockBytes, allocationBytes}`，即总分配块大小和实际使用的分配大小。

## 内部实现细节

### 函数指针拷贝

使用宏从 `VulkanInterface` 拷贝函数指针到 VMA 所需的格式：

```cpp
#define SKGPU_COPY_FUNCTION(NAME) functions.vk##NAME = interface->fFunctions.f##NAME
#define SKGPU_COPY_FUNCTION_KHR(NAME) functions.vk##NAME##KHR = interface->fFunctions.f##NAME
```

特别注意 KHR 后缀的处理：Skia 内部统一使用无后缀名称（因为 Vulkan 1.1 已提升这些函数），而 VMA 仍期望 KHR 后缀。

### 块大小策略

```cpp
constexpr size_t kBlockSize = 4 * 1024 * 1024;  // 4MB
```

通过分析 Android 应用和 DM 测试的内存使用模式确定。VMA 会从 1/8 块大小开始，按需增长到此上限。

### 线程安全

通过 `VMA_ALLOCATOR_CREATE_EXTERNALLY_SYNCHRONIZED_BIT` 标志控制。当 `ThreadSafe::kNo` 时设置此标志，告诉 VMA 外部已保证同步，可跳过内部锁。

### `VulkanMemoryAllocators::Make()` 便捷工厂

此函数封装了创建 `VulkanInterface` 和 `VulkanAMDMemoryAllocator` 的完整流程。注释指出为此会临时创建一个 `VulkanInterface` 实例，存在轻微的冗余（Ganesh/Graphite 稍后会创建自己的），但初始化仅执行一次，影响可忽略。

## 依赖关系

- **上游依赖**: `VulkanMemoryAllocator`（抽象接口）、`VulkanInterface`（函数指针源）、`VulkanExtensions`、`VulkanMemoryAllocatorWrapper.h`（VMA 头文件包装）。
- **第三方依赖**: `vk_mem_alloc.h` (AMD VMA 库)。
- **被依赖**: `VulkanMemory`、Ganesh/Graphite Vulkan GPU 实现。

## 设计模式与设计决策

1. **适配器模式**: 将 VMA 的 C 接口适配为 Skia 的 `VulkanMemoryAllocator` C++ 接口。
2. **句柄转换**: `VulkanBackendMemory`（`intptr_t`）与 `VmaAllocation` 之间通过 C 风格强制转换进行互转，实现类型擦除。
3. **子分配策略**: 利用 VMA 的子分配机制，在大内存块内分配多个小资源，减少 `vkAllocateMemory` 调用次数（Vulkan 限制同时分配数）。
4. **API 版本限制**: 当前固定到 Vulkan 1.1，注释说明待 Skia 接口和头文件更新后可提升到 1.3。

## 性能考量

- **TRACE_EVENT 追踪**: 关键分配和释放操作都有 `TRACE_EVENT0` 埋点（图像分配使用 `TRACE_EVENT0_ALWAYS` 确保始终记录）。
- **4MB 块大小**: 在减少碎片与避免浪费之间取得平衡，VMA 渐进式增长策略进一步优化了小场景的内存使用。
- **持久映射**: 对于 CPU 写入的缓冲区，通过 `VMA_ALLOCATION_CREATE_MAPPED_BIT` 支持创建时即映射，避免后续 map/unmap 开销。
- **缓冲区内存选择**: `kCpuWritesGpuReads` 倾向使用一致性内存（coherent），避免显式刷新操作，但首选设备本地以获得更好的 GPU 读取性能。

## 相关文件

- `include/gpu/vk/VulkanMemoryAllocator.h` - 内存分配器抽象接口
- `src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorWrapper.h` - VMA 头文件包装
- `src/gpu/vk/vulkanmemoryallocator/VulkanMemoryAllocatorPriv.h` - 私有辅助
- `src/gpu/vk/VulkanMemory.h` - 内存操作工具函数
- `src/gpu/vk/VulkanInterface.h` - Vulkan 函数指针接口
- `src/gpu/vk/VulkanUtilsPriv.h` - `MakeInterface()` 工厂函数
