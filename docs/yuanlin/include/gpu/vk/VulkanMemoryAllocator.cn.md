# VulkanMemoryAllocator

> 源文件: `include/gpu/vk/VulkanMemoryAllocator.h`

## 概述
VulkanMemoryAllocator 定义了 Skia Vulkan 后端的内存分配器抽象接口。该接口要求客户端提供自定义的 Vulkan 内存管理实现,用于分配图像和缓冲区的设备内存,支持映射、刷新、失效等操作,是 Skia GPU 资源管理的核心组件。

## 架构位置
该文件位于 Skia 的 GPU 公共接口层,属于 `skgpu` 命名空间。作为纯虚接口类,它定义了 Vulkan 内存管理的契约,由客户端代码实现(通常基于 Vulkan Memory Allocator 库),并在创建 Skia Vulkan 上下文时提供。

## 主要类与结构体

### VulkanMemoryAllocator
内存分配器的抽象基类,继承自 `SkRefCnt` 以支持智能指针管理。

**继承关系**: `SkRefCnt` → `VulkanMemoryAllocator`

**设计特点**:
- 纯虚接口,所有核心方法必须由派生类实现
- 使用引用计数管理生命周期
- 支持图像和缓冲区的差异化分配策略
- 提供细粒度的内存控制 (映射、刷新、统计)

### AllocationPropertyFlags
内存分配属性标志位枚举。

**枚举值**:
| 标志 | 值 | 说明 |
|------|-----|------|
| kNone_AllocationPropertyFlag | 0b0000 | 无特殊属性 |
| kDedicatedAllocation_AllocationPropertyFlag | 0b0001 | 独立 VkDeviceMemory,不进行子分配 |
| kLazyAllocation_AllocationPropertyFlag | 0b0010 | 延迟分配,仅设备可访问 |
| kPersistentlyMapped_AllocationPropertyFlag | 0b0100 | 持久映射,保持映射直到销毁 |
| kProtected_AllocationPropertyFlag | 0b1000 | 受保护内存,仅受保护上下文可访问 |

**使用规则**:
- 可通过位或操作组合多个标志
- `kLazyAllocation` 不能用于主机可见的缓冲区
- `kPersistentlyMapped` 要求缓冲区用途不是 `kGpuOnly`
- `kProtected` 需要设备支持受保护内存特性

### BufferUsage
缓冲区使用模式枚举,决定内存分配策略。

**枚举值**:
| 用途 | 内存特性 | 典型场景 |
|------|----------|----------|
| kGpuOnly | 设备本地内存 | 大型常量缓冲区、纹理数据 |
| kCpuWritesGpuReads | 可映射、一致性、倾向设备本地 | 顶点/索引/Uniform 缓冲区 |
| kTransfersFromCpuToGpu | 可映射、一致性 | Staging 缓冲区 (CPU → GPU) |
| kTransfersFromGpuToCpu | 可映射、倾向缓存 | Readback 缓冲区 (GPU → CPU) |

**内存选择策略**:
- `kGpuOnly`: 优先 `DEVICE_LOCAL_BIT`
- `kCpuWritesGpuReads`: `HOST_VISIBLE_BIT | HOST_COHERENT_BIT`,倾向 `DEVICE_LOCAL_BIT`
- `kTransfersFromCpuToGpu`: `HOST_VISIBLE_BIT | HOST_COHERENT_BIT`
- `kTransfersFromGpuToCpu`: `HOST_VISIBLE_BIT | HOST_CACHED_BIT`

## 公共 API 函数

### 图像内存分配
```cpp
virtual VkResult allocateImageMemory(
    VkImage image,
    uint32_t allocationPropertyFlags,
    skgpu::VulkanBackendMemory* memory) = 0;
```
- **功能**: 为已创建的 VkImage 分配设备内存
- **参数**:
  - `image`: 需要绑定内存的图像对象
  - `allocationPropertyFlags`: 分配属性的位掩码
  - `memory`: 输出参数,返回不透明的内存句柄
- **返回值**: Vulkan 结果码,成功时为 `VK_SUCCESS`
- **职责**: 实现需要调用 `vkGetImageMemoryRequirements` 查询需求并分配合适的内存

### 缓冲区内存分配
```cpp
virtual VkResult allocateBufferMemory(
    VkBuffer buffer,
    BufferUsage usage,
    uint32_t allocationPropertyFlags,
    skgpu::VulkanBackendMemory* memory) = 0;
```
- **功能**: 为已创建的 VkBuffer 分配设备内存
- **参数**:
  - `buffer`: 需要绑定内存的缓冲区对象
  - `usage`: 缓冲区使用模式,影响内存类型选择
  - `allocationPropertyFlags`: 分配属性标志
  - `memory`: 输出内存句柄
- **返回值**: Vulkan 结果码
- **实现要点**: 根据 `usage` 选择合适的内存堆和属性

### 获取分配信息
```cpp
virtual void getAllocInfo(
    const skgpu::VulkanBackendMemory& memory,
    skgpu::VulkanAlloc* alloc) const = 0;
```
- **功能**: 将不透明的内存句柄转换为详细的 VulkanAlloc 结构
- **参数**:
  - `memory`: 内存句柄
  - `alloc`: 输出参数,填充 VkDeviceMemory、偏移量、大小等信息
- **用途**: 用于绑定内存到图像/缓冲区或传递给外部 API

### 内存映射
```cpp
virtual void* mapMemory(const skgpu::VulkanBackendMemory& memory);
virtual VkResult mapMemory(const skgpu::VulkanBackendMemory& memory, void** data);
```
- **功能**: 将分配的内存映射到主机地址空间
- **返回值**:
  - 旧版本返回指针,失败返回 nullptr
  - 新版本返回 VkResult,通过 `data` 输出指针
- **要点**:
  - 返回的指针指向分配的起始位置
  - 实现可能映射更大的范围,但必须保证指针正确对齐
  - 仅适用于 `HOST_VISIBLE` 内存

### 取消映射
```cpp
virtual void unmapMemory(const skgpu::VulkanBackendMemory& memory) = 0;
```
- **功能**: 取消内存映射,使主机指针失效
- **参数**: `memory` - 之前映射的内存句柄
- **注意**: 持久映射的内存在释放前不应调用此方法

### 刷新映射内存
```cpp
virtual void flushMappedMemory(
    const skgpu::VulkanBackendMemory& memory,
    VkDeviceSize offset,
    VkDeviceSize size);
virtual VkResult flushMemory(
    const skgpu::VulkanBackendMemory& memory,
    VkDeviceSize offset,
    VkDeviceSize size);
```
- **功能**: 将主机写入的数据刷新到设备可见
- **参数**:
  - `memory`: 内存句柄
  - `offset`: 相对于分配起始的偏移量 (非 VkDeviceMemory 偏移)
  - `size`: 刷新的字节数
- **用途**: 用于非一致性内存 (`NON_COHERENT` 标志)
- **实现职责**: 处理 `VkDeviceSize` 的对齐要求

### 失效映射内存
```cpp
virtual void invalidateMappedMemory(
    const skgpu::VulkanBackendMemory& memory,
    VkDeviceSize offset,
    VkDeviceSize size);
virtual VkResult invalidateMemory(
    const skgpu::VulkanBackendMemory& memory,
    VkDeviceSize offset,
    VkDeviceSize size);
```
- **功能**: 使主机缓存失效,确保读取到设备最新写入的数据
- **参数**: 与 `flushMemory` 相同
- **用途**: 读取 GPU 写入的数据前调用 (如 readback)
- **对齐要求**: 实现需要确保偏移和大小满足 `nonCoherentAtomSize` 对齐

### 释放内存
```cpp
virtual void freeMemory(const skgpu::VulkanBackendMemory& memory) = 0;
```
- **功能**: 释放之前分配的内存
- **参数**: `memory` - 要释放的内存句柄
- **要点**:
  - 调用前确保所有使用该内存的命令已完成
  - 如果内存已映射,实现应先取消映射

### 内存统计
```cpp
virtual std::pair<uint64_t, uint64_t> totalAllocatedAndUsedMemory() const = 0;
```
- **功能**: 查询分配器的内存使用统计
- **返回值**: `{总分配内存, 总使用内存}` (单位:字节)
- **用途**: 性能监控、内存预算管理、调试

## 内部实现细节

### 兼容性双接口设计
文件中多处存在新旧接口共存:
```cpp
// 旧接口 (返回指针)
virtual void* mapMemory(const VulkanBackendMemory&) { return nullptr; }

// 新接口 (返回 VkResult)
virtual VkResult mapMemory(const VulkanBackendMemory& memory, void** data) {
    *data = this->mapMemory(memory);
    return *data ? VK_SUCCESS : VK_ERROR_INITIALIZATION_FAILED;
}
```
**设计原因**: 保持向后兼容性,新代码应实现返回 VkResult 的版本以提供更好的错误处理。

### 偏移量语义
所有接口中的 `offset` 和 `size` 参数相对于**分配的起始位置**,而非底层 `VkDeviceMemory` 的起始:
```cpp
// VulkanAlloc 结构:
// fMemory: VkDeviceMemory (可能包含多个子分配)
// fOffset: 在 fMemory 中的偏移量 (如 256 字节)
// fSize: 分配大小 (如 1024 字节)

// 调用 flushMemory 时:
flushMemory(memory, 100, 200);
// 实际刷新范围是 VkDeviceMemory 的 [256+100, 256+100+200) 字节
```

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkRefCnt.h | 引用计数基类 |
| include/gpu/vk/VulkanTypes.h | VulkanBackendMemory 和 VulkanAlloc 类型 |
| include/private/gpu/vk/SkiaVulkan.h | Vulkan API 头文件 |

### 被依赖的模块
- `VulkanBackendContext`: 在上下文初始化时需要提供分配器实例
- Vulkan GPU 资源类: 纹理、缓冲区等资源创建时调用分配接口
- Vulkan 后端实现: 内存管理、资源绑定、数据传输

## 设计模式与设计决策

### 策略模式 (Strategy Pattern)
`VulkanMemoryAllocator` 使用策略模式实现可插拔的内存管理:
- **接口**: `VulkanMemoryAllocator` 定义内存管理操作
- **具体策略**: 客户端提供实现 (VMA、自定义分配器)
- **上下文**: `VulkanBackendContext` 持有分配器引用

**优势**:
- Skia 核心不依赖特定分配器实现
- 客户端可根据需求优化内存策略
- 支持不同平台的最佳实践

### 模板方法模式
`BufferUsage` 枚举为不同使用场景定义了内存分配的模板策略,实现类遵循这些模板选择内存类型。

### 契约式设计 (Design by Contract)
接口文档明确前置条件和后置条件:
- `flushMemory/invalidateMemory`: 要求偏移+大小不超过分配大小
- `freeMemory`: 要求所有使用该内存的操作已完成
- `mapMemory`: 要求内存具有 `HOST_VISIBLE` 属性

## 性能考量

### 子分配策略
`kDedicatedAllocation_AllocationPropertyFlag` 的使用:
- **默认行为**: 小对象从大内存块中子分配,减少 VkDeviceMemory 数量
- **独立分配**: 大对象或有特殊要求的资源使用独立内存
- **性能影响**: 减少内存碎片,提高分配效率

### 持久映射优化
`kPersistentlyMapped_AllocationPropertyFlag`:
- **传统方式**: 每次使用前 map,使用后 unmap (开销大)
- **持久映射**: 映射一次,持续使用 (适合频繁更新的缓冲区)
- **应用场景**: Uniform 缓冲区、动态顶点缓冲区

### 内存一致性权衡
- **一致性内存** (`HOST_COHERENT`): 自动同步,无需刷新,但可能较慢
- **非一致性内存** (`NON_COHERENT`): 需手动刷新/失效,但读写性能更好
- **建议**: 频繁写入选择一致性,大块传输选择非一致性

### 惰性分配
`kLazyAllocation_AllocationPropertyFlag`:
- **使用场景**: 瞬态附件 (Transient Attachments)
- **优势**: 延迟物理内存分配,节省内存
- **限制**: 仅适用于 GPU 独占资源

## 平台相关说明

### Android 优化
- 优先使用 `HOST_COHERENT` 内存简化同步
- 受保护内存用于 DRM 内容
- 考虑使用 `AHardwareBuffer` 的外部内存

### 桌面平台 (Windows/Linux/macOS)
- Windows: 可利用 `DEVICE_LOCAL | HOST_VISIBLE` 的 256MB BAR 内存
- Linux: 注意 DRM 驱动的内存限制
- macOS (MoltenVK): 内存类型选择受 Metal 限制

### 移动平台
- 统一内存架构 (UMA): `DEVICE_LOCAL` 和 `HOST_VISIBLE` 通常重叠
- 内存预算: 使用 `VK_EXT_memory_budget` 扩展监控

## 典型实现示例

### 使用 Vulkan Memory Allocator (VMA)
```cpp
class VmaAllocator : public skgpu::VulkanMemoryAllocator {
public:
    VkResult allocateImageMemory(VkImage image,
                                  uint32_t flags,
                                  VulkanBackendMemory* memory) override {
        VmaAllocationCreateInfo allocInfo = {};
        allocInfo.usage = VMA_MEMORY_USAGE_AUTO;
        if (flags & kDedicatedAllocation_AllocationPropertyFlag) {
            allocInfo.flags |= VMA_ALLOCATION_CREATE_DEDICATED_MEMORY_BIT;
        }
        if (flags & kPersistentlyMapped_AllocationPropertyFlag) {
            allocInfo.flags |= VMA_ALLOCATION_CREATE_MAPPED_BIT;
        }

        VmaAllocation allocation;
        VkResult result = vmaAllocateMemoryForImage(fAllocator, image,
                                                     &allocInfo, &allocation, nullptr);
        *memory = reinterpret_cast<VulkanBackendMemory>(allocation);
        return result;
    }
    // ... 其他方法实现
};
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/vk/VulkanBackendContext.h | 使用此接口创建 Skia 上下文 |
| include/gpu/vk/VulkanTypes.h | 定义 VulkanAlloc 和 VulkanBackendMemory 类型 |
| src/gpu/vk/VulkanMemory.h | Skia 内部的内存管理封装 |
| third_party/externals/vma/ | 推荐的 VMA 库实现 |

## 常见问题与解决方案

### 问题 1: 内存泄漏
**症状**: `totalAllocatedAndUsedMemory()` 显示分配不断增长
**原因**: 资源未正确释放或分配器实现有误
**解决**: 使用验证层追踪对象生命周期,确保 `freeMemory` 调用匹配

### 问题 2: 映射失败
**症状**: `mapMemory` 返回 nullptr 或 `VK_ERROR_MEMORY_MAP_FAILED`
**原因**: 内存类型不支持 `HOST_VISIBLE` 或已映射次数超限
**解决**: 检查内存属性标志,避免多次映射同一内存

### 问题 3: 数据未同步
**症状**: GPU 读取的数据是旧值
**原因**: 非一致性内存未刷新
**解决**: 在 CPU 写入后调用 `flushMemory`,GPU 写入后读取前调用 `invalidateMemory`

### 问题 4: 对齐错误
**症状**: 验证层报告 `nonCoherentAtomSize` 对齐错误
**原因**: 刷新/失效的偏移或大小未对齐
**解决**: 实现中向下对齐偏移,向上对齐大小:
```cpp
VkDeviceSize atomSize = physicalDeviceProperties.limits.nonCoherentAtomSize;
VkDeviceSize alignedOffset = (offset / atomSize) * atomSize;
VkDeviceSize alignedSize = ((offset + size + atomSize - 1) / atomSize) * atomSize - alignedOffset;
```
