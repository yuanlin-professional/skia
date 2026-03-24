# VkTestMemoryAllocator

> 源文件
> - tools/gpu/vk/VkTestMemoryAllocator.h
> - tools/gpu/vk/VkTestMemoryAllocator.cpp

## 概述

`VkTestMemoryAllocator` 是 Skia GPU 工具集中专门用于 Vulkan 后端的内存分配器实现，基于 AMD 的 Vulkan Memory Allocator (VMA) 库。在 Vulkan 中，GPU 内存管理需要手动处理，包括选择合适的内存堆（heap）、内存类型、以及处理分配、映射、同步等复杂操作。该分配器封装了这些复杂性，为 Skia 的 Vulkan 后端提供统一的内存管理接口。

核心功能包括：为 Vulkan 图像和缓冲区分配 GPU 内存、支持多种缓冲区使用模式（GPU 专用、CPU-GPU 共享等）、处理内存映射和取消映射、支持缓存一致性操作（flush 和 invalidate）、提供内存使用统计。该分配器基于 VMA 库，继承了其高效的内存管理策略，如内存池、块分配和去碎片化。

## 架构位置

`VkTestMemoryAllocator` 位于 `tools/gpu/vk/` 目录下，是 Vulkan 测试工具层的核心组件。在 Skia 架构中：

1. **内存管理层**：实现 `skgpu::VulkanMemoryAllocator` 接口，为 Ganesh 和 Graphite 的 Vulkan 后端提供内存分配服务
2. **VMA 集成层**：桥接 Skia 和 VMA 库，转换 API 和数据结构
3. **测试基础设施**：用于测试环境，提供可靠且高效的内存管理

依赖关系：
- **上游依赖**：`VulkanMemoryAllocator`（接口）、VMA 库（`vk_mem_alloc.h`）、`VulkanInterface`（Vulkan 函数指针）
- **后端集成**：Ganesh 和 Graphite 的 Vulkan 后端通过该分配器管理 GPU 内存
- **下游使用**：Vulkan 上下文工厂、Vulkan 测试工具、性能基准测试

该分配器被设计为测试专用，但其实现足够健壮，可以在生产环境中使用（注释提到它基于之前生产环境的 `VulkanAMDMemoryAllocator`）。

## 主要类与结构体

### VkTestMemoryAllocator

继承自 `skgpu::VulkanMemoryAllocator`，实现完整的内存分配器接口。

**关键成员变量：**
- `VmaAllocator fAllocator`：VMA 分配器句柄，所有内存操作都委托给它

**设计特点：**
- 私有构造函数，只能通过 `Make` 工厂方法创建
- RAII 设计，析构函数自动销毁 VMA 分配器
- 无拷贝/移动语义（隐式删除）

### BufferUsage 枚举（继承自基类）

定义缓冲区的使用模式，影响内存类型选择：

- `kGpuOnly`：GPU 独占，设备本地内存（最快）
- `kCpuWritesGpuReads`：CPU 写入，GPU 读取（如顶点/索引缓冲区上传）
- `kTransfersFromCpuToGpu`：CPU 到 GPU 的传输（临时暂存缓冲区）
- `kTransfersFromGpuToCpu`：GPU 到 CPU 的传输（读回结果）

### AllocationPropertyFlags（继承自基类）

内存分配属性标志位：

- `kDedicatedAllocation_AllocationPropertyFlag`：请求专用内存分配（不与其他对象共享）
- `kLazyAllocation_AllocationPropertyFlag`：延迟分配（瓦片渲染优化）
- `kProtected_AllocationPropertyFlag`：受保护内存（DRM 内容）
- `kPersistentlyMapped_AllocationPropertyFlag`：持久映射（创建时即映射）

## 公共 API 函数

### Make（工厂方法）

```cpp
static sk_sp<VulkanMemoryAllocator> Make(
    VkInstance instance,
    VkPhysicalDevice physicalDevice,
    VkDevice device,
    uint32_t physicalDeviceVersion,
    const skgpu::VulkanExtensions* extensions,
    const skgpu::VulkanInterface* interface);
```

创建内存分配器实例。

**参数：**
- `instance`：Vulkan 实例句柄
- `physicalDevice`：物理设备句柄
- `device`：逻辑设备句柄
- `physicalDeviceVersion`：物理设备 Vulkan 版本
- `extensions`：Vulkan 扩展信息
- `interface`：Vulkan 函数指针表

**返回值：** 智能指针包装的分配器对象

**内部流程：**
1. 构建 VMA 需要的 Vulkan 函数指针表
2. 配置 VMA 分配器参数（块大小、API 版本等）
3. 调用 `vmaCreateAllocator` 创建 VMA 分配器
4. 封装为 Skia 分配器对象

### allocateImageMemory

```cpp
VkResult allocateImageMemory(
    VkImage image,
    uint32_t allocationPropertyFlags,
    skgpu::VulkanBackendMemory* backendMemory) override;
```

为 Vulkan 图像分配内存。

**参数：**
- `image`：Vulkan 图像句柄
- `allocationPropertyFlags`：分配属性标志
- `backendMemory`：输出的后端内存句柄

**返回值：** Vulkan 结果代码（`VK_SUCCESS` 表示成功）

**内存特性：**
- 必需：`VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT`（设备本地内存）
- 可选：根据 flags 添加专用分配、延迟分配、受保护标志

### allocateBufferMemory

```cpp
VkResult allocateBufferMemory(
    VkBuffer buffer,
    BufferUsage usage,
    uint32_t allocationPropertyFlags,
    skgpu::VulkanBackendMemory* backendMemory) override;
```

为 Vulkan 缓冲区分配内存。

**参数：**
- `buffer`：Vulkan 缓冲区句柄
- `usage`：缓冲区使用模式
- `allocationPropertyFlags`：分配属性标志
- `backendMemory`：输出的后端内存句柄

**内存选择策略（根据 usage）：**

| Usage | 必需标志 | 首选标志 | 用途 |
|-------|---------|---------|------|
| `kGpuOnly` | `DEVICE_LOCAL` | 无 | 纹理、渲染目标 |
| `kCpuWritesGpuReads` | `HOST_VISIBLE \| HOST_COHERENT` | `DEVICE_LOCAL` | 顶点/索引缓冲区 |
| `kTransfersFromCpuToGpu` | `HOST_VISIBLE \| HOST_COHERENT` | 无 | 暂存缓冲区（上传） |
| `kTransfersFromGpuToCpu` | `HOST_VISIBLE` | `HOST_CACHED` | 回读缓冲区 |

### freeMemory

```cpp
void freeMemory(const skgpu::VulkanBackendMemory& memoryHandle) override;
```

释放分配的内存。

**参数：**
- `memoryHandle`：要释放的内存句柄（VMA allocation）

**注意：** 必须在销毁关联的图像或缓冲区之前调用

### getAllocInfo

```cpp
void getAllocInfo(const skgpu::VulkanBackendMemory& memoryHandle,
                  skgpu::VulkanAlloc* alloc) const override;
```

查询分配的详细信息。

**输出信息包括：**
- `fMemory`：VkDeviceMemory 句柄
- `fOffset`：内存块中的偏移量
- `fSize`：分配大小
- `fFlags`：内存属性标志（可映射、非一致性、延迟分配）

### mapMemory / unmapMemory

```cpp
VkResult mapMemory(const skgpu::VulkanBackendMemory& memoryHandle, void** data) override;
void unmapMemory(const skgpu::VulkanBackendMemory& memoryHandle) override;
```

映射和取消映射内存，允许 CPU 访问 GPU 内存。

**使用限制：**
- 只能映射 `HOST_VISIBLE` 内存
- 映射期间不能释放内存
- 嵌套映射/取消映射必须平衡

### flushMemory / invalidateMemory

```cpp
VkResult flushMemory(const skgpu::VulkanBackendMemory& memoryHandle,
                     VkDeviceSize offset, VkDeviceSize size) override;
VkResult invalidateMemory(const skgpu::VulkanBackendMemory& memoryHandle,
                          VkDeviceSize offset, VkDeviceSize size) override;
```

处理缓存一致性。

**flushMemory**：将 CPU 写入刷新到 GPU 可见内存（用于非一致性内存）
**invalidateMemory**：使 CPU 缓存失效，确保读取到 GPU 最新写入（用于回读）

**注意：** 一致性内存（`HOST_COHERENT`）不需要这些操作

### totalAllocatedAndUsedMemory

```cpp
std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const override;
```

返回内存使用统计。

**返回值：**
- `first`：总分配的内存块大小（包括未使用部分）
- `second`：实际使用的内存大小

**用途：** 监控内存使用、检测泄漏、性能分析

## 内部实现细节

### VMA 集成

VMA（Vulkan Memory Allocator）是 AMD 开源的跨平台 Vulkan 内存分配库，特点：

- **内存池管理**：自动管理大块内存，子分配小对象
- **去碎片化**：智能块分配策略减少碎片
- **性能优化**：减少 Vulkan API 调用次数
- **线程安全**：内部使用互斥锁保护

### 函数指针表构建

`Make` 方法将 Skia 的 `VulkanInterface` 转换为 VMA 的 `VmaVulkanFunctions`：

```cpp
#define SKGPU_COPY_FUNCTION(NAME) functions.vk##NAME = interface->fFunctions.f##NAME
SKGPU_COPY_FUNCTION(AllocateMemory);
SKGPU_COPY_FUNCTION(FreeMemory);
// ... 更多函数
```

这确保 VMA 使用 Skia 加载的 Vulkan 函数，保持版本一致性。

### VMA 分配器配置

关键配置参数：

```cpp
VmaAllocatorCreateInfo info;
info.flags = VMA_ALLOCATOR_CREATE_KHR_DEDICATED_ALLOCATION_BIT;
info.preferredLargeHeapBlockSize = 4 * 1024 * 1024;  // 4MB 块大小
info.vulkanApiVersion = VK_API_VERSION_1_1;  // 最小版本 1.1
```

**4MB 块大小**的选择：
- 基于 Android 应用和 DM 测试的内存使用分析
- 平衡未使用空间浪费和分配次数
- VMA 从 1/8 最大值开始，逐步增长

### 缓冲区内存选择策略

不同使用模式的内存特性权衡：

**kCpuWritesGpuReads（一致性内存）：**
- 选择原因：CPU 顺序写入，GPU 读取，无 CPU 读取
- 权衡：一致性避免 flush，但带宽可能较低
- 未来优化：对于特殊场景可支持缓存一致性内存（`HOST_CACHED | HOST_COHERENT`）

**kTransfersFromGpuToCpu（缓存内存）：**
- 选择原因：GPU 写入后 CPU 读取，需要高带宽
- 缓存加速 CPU 读取，但 GPU 写入会使缓存失效
- 需要 `invalidateMemory` 确保读取最新数据

### 内存句柄转换

Skia 使用 `VulkanBackendMemory`（`void*`）作为不透明句柄，VMA 使用 `VmaAllocation`：

```cpp
*backendMemory = (skgpu::VulkanBackendMemory)allocation;  // 存储时转换
const VmaAllocation allocation = (VmaAllocation)memoryHandle;  // 使用时转换
```

这种转换安全，因为两者都是指针类型，且生命周期由 Skia 控制。

### 追踪事件集成

所有性能关键操作都使用 `TRACE_EVENT`：

```cpp
TRACE_EVENT0_ALWAYS("skia.gpu", TRACE_FUNC);
```

这允许使用 Chrome 的 tracing 工具分析内存分配性能。

### API 版本限制

当前实现限制为 Vulkan 1.1：

```cpp
// TODO: Update our interface and headers to support vulkan 1.3
info.vulkanApiVersion = VK_API_VERSION_1_1;
```

原因：Skia 的最低要求是 Vulkan 1.1，且 1.3 需要额外的函数指针。

## 依赖关系

### 核心依赖

- **VulkanMemoryAllocator.h**：Skia 的内存分配器接口
- **vk_mem_alloc.h**：VMA 库头文件
- **VulkanInterface.h**：Vulkan 函数指针表
- **VulkanExtensions.h**：Vulkan 扩展信息

### 工具依赖

- **SkTraceEvent.h**：性能跟踪系统

### 被依赖

- Ganesh Vulkan 后端（`src/gpu/ganesh/vk/`）
- Graphite Vulkan 后端（`src/gpu/graphite/vk/`）
- Vulkan 上下文工厂（`tools/gpu/vk/GrVkTestUtils.h`）
- Vulkan 测试用例

### 第三方库

- **VMA（Vulkan Memory Allocator）**：AMD 开源库，通过 `vk_mem_alloc.h` 单头文件包含

## 设计模式与设计决策

### 适配器模式

`VkTestMemoryAllocator` 适配 VMA 到 Skia 的内存分配器接口：
- 转换 API 调用（Skia → VMA）
- 转换数据结构（`VulkanBackendMemory` ↔ `VmaAllocation`）
- 统一错误处理和语义

### 工厂方法模式

私有构造函数 + 公共 `Make` 方法：
- 封装复杂的初始化逻辑
- 失败时返回 `nullptr`
- 确保对象始终处于有效状态

### RAII（Resource Acquisition Is Initialization）

析构函数自动销毁 VMA 分配器：
```cpp
~VkTestMemoryAllocator() {
    vmaDestroyAllocator(fAllocator);
    fAllocator = VK_NULL_HANDLE;
}
```

防止资源泄漏，简化生命周期管理。

### 委托模式

所有内存操作委托给 VMA：
- 利用 VMA 的成熟实现
- 避免重复造轮子
- 专注于接口适配而非实现细节

### 缓冲区使用模式驱动设计

通过 `BufferUsage` 枚举驱动内存选择：
- 声明式语义（"我要做什么"而非"我要什么内存"）
- 封装复杂的内存类型选择逻辑
- 适应不同硬件的最佳实践

### 测试与生产的统一

虽然命名为"Test"，但实现质量足以用于生产：
- 基于之前的生产实现（`VulkanAMDMemoryAllocator`）
- 完整的功能支持
- 健壮的错误处理

命名为"Test"主要是位置（`tools/`）而非质量考量。

## 性能考量

### 内存池和块分配

VMA 使用内存池策略：
- 大块分配（4MB），子分配小对象
- 减少 Vulkan API 调用（昂贵操作）
- 降低碎片化

**性能影响：** 小对象分配非常快（O(1) 或 O(log n)），不需要驱动交互。

### 内存类型选择

不同内存类型有不同性能特征：

| 内存类型 | 带宽 | 延迟 | 一致性成本 |
|---------|------|------|-----------|
| `DEVICE_LOCAL`（GPU 专用） | 最高 | 最低 | N/A |
| `HOST_VISIBLE | HOST_COHERENT` | 中等 | 中等 | 无 |
| `HOST_VISIBLE | HOST_CACHED` | 高（读） | 低（读） | 需要 flush/invalidate |

正确选择内存类型对性能至关重要。

### 专用分配的权衡

专用分配（`kDedicatedAllocation`）：
- **优点**：某些驱动对大对象优化专用分配
- **缺点**：浪费空间（整个内存块仅一个对象）、增加分配调用

建议：仅对大型对象（如渲染目标）使用。

### 持久映射

持久映射（`kPersistentlyMapped`）：
- **优点**：避免重复 map/unmap 开销
- **缺点**：占用地址空间、某些驱动可能限制映射数量

适用于频繁更新的小缓冲区（如 uniform 缓冲区）。

### 缓存一致性开销

非一致性内存需要显式 flush/invalidate：
- Flush：可能需要 CPU 缓存写回（数百个周期）
- Invalidate：可能需要缓存行失效

对于大块内存，这些操作成本显著。一致性内存避免此开销，但可能带宽较低。

### 统计查询开销

`totalAllocatedAndUsedMemory` 调用 `vmaCalculateStatistics`：
- 遍历所有内存块和分配
- 非常量时间操作
- 不应在热循环中调用

适用于调试和分析，而非实时监控。

## 相关文件

### 核心依赖

- `include/gpu/vk/VulkanMemoryAllocator.h` - 内存分配器接口
- `src/gpu/vk/VulkanInterface.h` - Vulkan 函数指针表
- `include/gpu/vk/VulkanExtensions.h` - Vulkan 扩展信息

### 第三方库

- `third_party/externals/vulkanmemoryallocator/include/vk_mem_alloc.h` - VMA 库

### Vulkan 后端

- `src/gpu/ganesh/vk/GrVkMemory.h` - Ganesh Vulkan 内存管理
- `src/gpu/graphite/vk/VulkanBuffer.cpp` - Graphite Vulkan 缓冲区
- `src/gpu/graphite/vk/VulkanTexture.cpp` - Graphite Vulkan 纹理

### 测试工具

- `tools/gpu/vk/GrVkTestUtils.h` - Vulkan 测试工具
- `tools/gpu/vk/VkTestHelper.h` - Vulkan 测试辅助类

### 相关文件

- `tools/gpu/vk/VkYcbcrSamplerHelper.h` - YCbCr 采样器（也使用此分配器）
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 通用测试工具
