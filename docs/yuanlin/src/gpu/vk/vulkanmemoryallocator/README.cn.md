# vulkanmemoryallocator - AMD Vulkan Memory Allocator 集成

## 概述

`src/gpu/vk/vulkanmemoryallocator` 目录包含 Skia 对 AMD 开源 Vulkan Memory Allocator (VMA) 库的集成代码。VMA 是一个广泛使用的 Vulkan GPU 内存管理库,提供了内存池化、子分配和碎片管理等高级功能。Skia 通过 `VulkanAMDMemoryAllocator` 类将 VMA 封装为 `VulkanMemoryAllocator` 接口的具体实现。

Vulkan 将内存管理的责任完全交给应用程序。应用需要查询内存类型、选择合适的内存堆、处理对齐要求,并自行管理内存的生命周期。这对于像 Skia 这样的图形库来说是一个沉重的负担。VMA 库通过自动化这些决策来简化内存管理,同时保持接近最优的性能。

Skia 的 VMA 集成具有以下关键特性:首先,它锁定 Vulkan API 版本为 1.1(`VMA_VULKAN_VERSION 1001000`),与 Skia 的最低 Vulkan 要求保持一致。其次,它使用自定义函数指针(`VMA_STATIC_VULKAN_FUNCTIONS 0`, `VMA_DYNAMIC_VULKAN_FUNCTIONS 0`),而非让 VMA 自行加载 Vulkan 函数,确保与 Skia 的 `VulkanInterface` 系统一致。默认块大小设置为 4MB,这是根据 Android 应用内存使用模式和 DM 测试工具运行结果选定的平衡值。

该集成还提供了 `VulkanMemoryAllocators::Make()` 工厂函数,可以直接从 `VulkanBackendContext` 创建完整的内存分配器实例,简化了 Ganesh 和 Graphite 的初始化流程。线程安全性可以在创建时配置,通过 `VMA_ALLOCATOR_CREATE_EXTERNALLY_SYNCHRONIZED_BIT` 标志控制。

值得注意的是,构建系统将 VMA 的可见性限制在 Skia 内部(`tools` 和 `src/gpu/vk` 包),不作为公共模块暴露。这是因为 VMA 的编译期配置(如函数指针模式)可能与客户端自己的 VMA 实例产生 ODR (One Definition Rule) 冲突。如果客户端需要使用自己的 VMA 实例,应该将其封装为 `VulkanMemoryAllocator` 接口的实现传入 Skia。

## 架构图

```
+--------------------------------------------------+
|              Skia GPU 后端 (Ganesh/Graphite)      |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|       VulkanMemoryAllocator (抽象接口)            |
|       include/gpu/vk/VulkanMemoryAllocator.h      |
|                                                   |
|   allocateImageMemory()  allocateBufferMemory()   |
|   freeMemory()  mapMemory()  unmapMemory()        |
|   flushMemory()  invalidateMemory()               |
|   getAllocInfo()  totalAllocatedAndUsedMemory()    |
+---------------------------+-----------------------+
                            |
           +----------------+----------------+
           |                                 |
+----------v-----------+   +-----------------v---------+
| VulkanAMDMemory      |   |  客户端自定义实现          |
| Allocator            |   |  (如果需要)               |
| (VMA封装)            |   |                           |
|                      |   +---------------------------+
| +-----------------+  |
| | VmaAllocator    |  |
| | (AMD VMA库实例) |  |
| +-----------------+  |
+----------+-----------+
           |
+----------v-----------+
| VulkanMemoryAllocator|
| Wrapper.h            |
| (VMA头文件安全引入)  |
|                      |
| +------------------+ |
| | vk_mem_alloc.h   | |
| | (AMD VMA实现)    | |
| +------------------+ |
+-----------+----------+
            |
+-----------v----------+
|   Vulkan 驱动层      |
| VkDeviceMemory       |
| vkAllocateMemory()   |
| vkFreeMemory()       |
+----------------------+
```

## 目录结构

```
src/gpu/vk/vulkanmemoryallocator/
|-- BUILD.bazel                          # Bazel 构建配置
|-- BUILD.gn                             # GN 构建配置
|-- VulkanAMDMemoryAllocator.h           # VMA 封装类头文件
|-- VulkanAMDMemoryAllocator.cpp         # VMA 封装类实现 (~315行)
|-- VulkanMemoryAllocatorPriv.h          # 私有工厂函数头文件
|-- VulkanMemoryAllocatorWrapper.h       # VMA 头文件安全引入包装
|-- VulkanMemoryAllocatorWrapper.cpp     # VMA 实现编译单元
```

## 关键类与函数

### `VulkanAMDMemoryAllocator` (VulkanAMDMemoryAllocator.h)

AMD VMA 库的 Skia 封装,实现 `VulkanMemoryAllocator` 接口:

```cpp
class VulkanAMDMemoryAllocator : public VulkanMemoryAllocator {
public:
    // 工厂方法: 创建VMA封装的内存分配器
    static sk_sp<VulkanMemoryAllocator> Make(
        VkInstance instance,
        VkPhysicalDevice physicalDevice,
        VkDevice device,
        uint32_t physicalDeviceVersion,
        const VulkanExtensions* extensions,
        const VulkanInterface* interface,
        ThreadSafe);

    // 图像内存分配
    VkResult allocateImageMemory(VkImage image,
                                 uint32_t allocationPropertyFlags,
                                 skgpu::VulkanBackendMemory*) override;

    // 缓冲区内存分配
    VkResult allocateBufferMemory(VkBuffer buffer,
                                  BufferUsage usage,
                                  uint32_t allocationPropertyFlags,
                                  skgpu::VulkanBackendMemory*) override;

    // 获取总分配量和使用量
    std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const override;

private:
    VmaAllocator fAllocator;  // AMD VMA 分配器实例
};
```

### Make() 工厂方法详细分析

```cpp
// 关键初始化参数:
VmaAllocatorCreateInfo info;
info.flags = VMA_ALLOCATOR_CREATE_KHR_DEDICATED_ALLOCATION_BIT;
// 如果 ThreadSafe::kNo:
info.flags |= VMA_ALLOCATOR_CREATE_EXTERNALLY_SYNCHRONIZED_BIT;

// 默认块大小: 4MB
constexpr size_t kBlockSize = 4 * 1024 * 1024;
info.preferredLargeHeapBlockSize = kBlockSize;

// 锁定 API 版本为 1.1
info.vulkanApiVersion = VK_API_VERSION_1_1;
```

函数指针通过 `SKGPU_COPY_FUNCTION` 和 `SKGPU_COPY_FUNCTION_KHR` 宏从 `VulkanInterface` 复制到 `VmaVulkanFunctions`:

```cpp
SKGPU_COPY_FUNCTION(AllocateMemory);         // fAllocateMemory
SKGPU_COPY_FUNCTION(FreeMemory);             // fFreeMemory
SKGPU_COPY_FUNCTION(MapMemory);              // fMapMemory
SKGPU_COPY_FUNCTION(CreateBuffer);           // fCreateBuffer
SKGPU_COPY_FUNCTION_KHR(GetBufferMemoryRequirements2);  // fGetBufferMemoryRequirements2KHR
SKGPU_COPY_FUNCTION_KHR(BindBufferMemory2);  // fBindBufferMemory2KHR
// ... 共约 20 个函数
```

### 缓冲区内存分配策略 (BufferUsage)

| BufferUsage | requiredFlags | preferredFlags | 说明 |
|-------------|---------------|----------------|------|
| `kGpuOnly` | `DEVICE_LOCAL` | 无 | GPU 专用内存 |
| `kCpuWritesGpuReads` | `HOST_VISIBLE + HOST_COHERENT` | `DEVICE_LOCAL` | CPU 写 GPU 读(一致性) |
| `kTransfersFromCpuToGpu` | `HOST_VISIBLE + HOST_COHERENT` | 无 | CPU 到 GPU 传输 |
| `kTransfersFromGpuToCpu` | `HOST_VISIBLE` | `HOST_CACHED` | GPU 到 CPU 回读 |

### `VulkanMemoryAllocators::Make()` (VulkanMemoryAllocatorPriv.h)

便捷工厂函数,直接从 `VulkanBackendContext` 创建分配器:

```cpp
namespace VulkanMemoryAllocators {
sk_sp<VulkanMemoryAllocator> Make(const skgpu::VulkanBackendContext&,
                                  ThreadSafe);
}
```

该函数内部会创建临时的 `VulkanInterface` 并调用 `VulkanAMDMemoryAllocator::Make()`。

### `VulkanMemoryAllocatorWrapper.h`

VMA 头文件的安全引入包装器,解决以下问题:

1. **Vulkan 头文件兼容**: 某些构建环境只有 `vulkan_core.h` 而无完整 `vulkan.h`。通过在引入前检查 `VULKAN_CORE_H_` 并伪定义 `VULKAN_H_` 来绕过 VMA 的头文件检查。

2. **API 版本锁定**: 定义 `VMA_VULKAN_VERSION 1001000` 将 VMA 限制在 Vulkan 1.1 API。

3. **编译警告抑制**: 通过 Clang diagnostic pragma 抑制 VMA 中的 `-Wc++98-compat-extra-semi` 警告。

4. **ODR 安全**: 定义 `VMA_STATIC_VULKAN_FUNCTIONS 0` 和 `VMA_DYNAMIC_VULKAN_FUNCTIONS 0` 确保 VMA 不会自行加载函数,避免与外部 VMA 实例冲突。

### `VulkanMemoryAllocatorWrapper.cpp`

VMA 的实现编译单元。通过定义 `VMA_IMPLEMENTATION` 宏并包含 `VulkanMemoryAllocatorWrapper.h` 来编译 VMA 的实现代码。还定义了 `VMA_NULLABLE` 和 `VMA_NOT_NULL` 为空来禁用 VMA 不完整的空值标注。

## 依赖关系

```
vulkanmemoryallocator/ 依赖:
  +-- @vulkanmemoryallocator//:hdrs (AMD VMA 库头文件: vk_mem_alloc.h)
  +-- include/gpu/vk/VulkanMemoryAllocator.h (Skia 内存分配器接口)
  +-- include/gpu/vk/VulkanTypes.h (Vulkan 类型定义)
  +-- include/gpu/vk/VulkanBackendContext.h (后端上下文)
  +-- include/gpu/vk/VulkanExtensions.h (扩展管理)
  +-- src/gpu/vk/VulkanInterface.h (函数指针接口)
  +-- src/gpu/vk/VulkanUtilsPriv.h (工具函数: MakeInterface)
  +-- include/third_party/vulkan/ (Vulkan 头文件)

被以下模块使用:
  +-- src/gpu/ganesh/vk/ (Ganesh Vulkan 后端)
  +-- src/gpu/graphite/vk/ (Graphite Vulkan 后端, 间接)
  +-- src/gpu/android/ (Android Vulkan 内存分配器)
  +-- tools/ (Skia 测试工具)
```

## 设计模式分析

### 1. 适配器模式 (Adapter Pattern)

`VulkanAMDMemoryAllocator` 将 AMD VMA 库的 C API (`vmaAllocateMemoryForImage`, `vmaAllocateMemoryForBuffer` 等) 适配为 Skia 的 `VulkanMemoryAllocator` C++ 接口。这使得 VMA 可以被透明替换为其他内存管理实现。

### 2. 抽象工厂 (Abstract Factory)

`VulkanMemoryAllocators::Make()` 作为抽象工厂方法,根据 `VulkanBackendContext` 创建合适的内存分配器实例。客户端无需了解具体使用的是 VMA 还是其他实现。

### 3. 编译防火墙 (Compilation Firewall)

`VulkanMemoryAllocatorWrapper.h` 和 `.cpp` 文件将 VMA 的编译隔离在单独的编译单元中。VMA 头文件中的大量模板和内联代码不会泄露到 Skia 的其他编译单元,避免编译时间膨胀和潜在的符号冲突。

### 4. 构建可见性控制

通过 Bazel 的 `visibility` 属性严格控制 VMA 的使用范围:

```python
visibility = [
    "//tools:__subpackages__",    # 仅测试工具
    "//src/gpu/vk:__pkg__",       # 仅 Vulkan 共享层
]
```

这确保了 VMA 不会被意外引入到不需要它的模块中。

## 数据流

```
1. 初始化流:
   VulkanBackendContext (VkInstance + VkDevice + VkPhysicalDevice + getProc)
        |
   VulkanMemoryAllocators::Make()
        |-- 创建临时 VulkanInterface (加载函数指针)
        |-- VulkanAMDMemoryAllocator::Make()
              |-- 复制 ~20个 Vulkan 函数指针到 VmaVulkanFunctions
              |-- 设置创建参数 (块大小=4MB, API=1.1, 线程安全)
              |-- vmaCreateAllocator() 创建 VMA 实例
              |
        返回 sk_sp<VulkanMemoryAllocator>

2. 图像内存分配流:
   allocateImageMemory(VkImage, allocationPropertyFlags)
        |-- 构建 VmaAllocationCreateInfo:
        |     requiredFlags = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT
        |     + 可选: DEDICATED / LAZILY_ALLOCATED / PROTECTED
        |-- vmaAllocateMemoryForImage(fAllocator, image, &info, &allocation)
        |-- 返回 VulkanBackendMemory 句柄

3. 缓冲区内存分配流:
   allocateBufferMemory(VkBuffer, BufferUsage, flags)
        |-- 根据 BufferUsage 选择内存属性组合
        |-- 可选: DEDICATED / LAZILY_ALLOCATED / PERSISTENTLY_MAPPED / PROTECTED
        |-- vmaAllocateMemoryForBuffer(fAllocator, buffer, &info, &allocation)
        |-- 返回 VulkanBackendMemory 句柄

4. 内存信息查询:
   getAllocInfo(VulkanBackendMemory) -> VulkanAlloc
        |-- vmaGetAllocationInfo() 获取偏移量/大小/设备内存
        |-- vmaGetMemoryTypeProperties() 获取内存属性标志
        |     HOST_VISIBLE -> kMappable_Flag
        |     !HOST_COHERENT -> kNoncoherent_Flag
        |     LAZILY_ALLOCATED -> kLazilyAllocated_Flag
        |-- 组装 VulkanAlloc 结构体

5. 统计信息:
   totalAllocatedAndUsedMemory()
        |-- vmaCalculateStatistics() 获取全局统计
        |-- 返回 {blockBytes, allocationBytes}

6. 清理流:
   ~VulkanAMDMemoryAllocator()
        |-- vmaDestroyAllocator(fAllocator) 销毁 VMA 实例
```

## 相关文档与参考

- **AMD Vulkan Memory Allocator**: https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator
- **VMA 文档**: https://gpuopen-librariesandsdks.github.io/VulkanMemoryAllocator/html/
- **Vulkan 内存管理最佳实践**: https://developer.nvidia.com/blog/vulkan-memory-management/
- **VMA ODR 问题 (b/306154574)**: Skia 内部 bug 追踪,关于 VMA 头文件的 ODR 违反问题
- **VMA GitHub Issues**: #298 (未使用变量), #299 (隐式穿透), #312 (cstdio 依赖)
- **Skia VulkanMemoryAllocator 接口**: `include/gpu/vk/VulkanMemoryAllocator.h`
- **父目录 Vulkan 工具层**: `src/gpu/vk/` - 共享 Vulkan 基础设施
- **Android VMA 集成**: `src/gpu/android/AndroidVulkanMemoryAllocator.cpp`
