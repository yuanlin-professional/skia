# VulkanBuffer

> 源文件
> - `src/gpu/graphite/vk/VulkanBuffer.h`
> - `src/gpu/graphite/vk/VulkanBuffer.cpp`

## 概述

`VulkanBuffer` 是 Skia Graphite 的 Vulkan 后端中用于管理 GPU 缓冲区的核心类。它封装了 Vulkan 的 `VkBuffer` 对象及其内存分配，提供了缓冲区创建、映射、访问控制和同步的完整功能。该类继承自 `Buffer` 基类，实现了 Vulkan 特定的缓冲区操作，支持多种缓冲区类型（顶点、索引、统一、存储等），并根据访问模式（CPU 可见、GPU 独占等）优化内存分配策略。

## 架构位置

`VulkanBuffer` 位于 Skia Graphite 的 Vulkan 后端资源管理层：

```
skgpu::graphite
    └── Buffer (基类)
         └── VulkanBuffer
              ├── 使用 VulkanSharedContext (设备和内存管理)
              ├── 使用 VulkanMemoryAllocator (内存分配)
              ├── 与 VulkanCommandBuffer 协作 (访问同步)
              └── 使用 VulkanMemory (底层内存操作)
```

它是 Vulkan 渲染管线中数据传输和存储的基础设施，为顶点数据、索引、统一变量、计算着色器存储等提供内存支持。

## 主要类与结构体

### VulkanBuffer

```cpp
class VulkanBuffer final : public Buffer
```

**核心成员变量：**
- `VkBuffer fBuffer` - Vulkan 缓冲区句柄
- `skgpu::VulkanAlloc fAlloc` - 内存分配信息
- `VkBufferUsageFlags fBufferUsageFlags` - 缓冲区用途标志
- `VkAccessFlags fCurrentAccess` - 当前访问模式（用于同步）
- `bool fBufferUsedForCPURead` - 标记缓冲区是否用于 CPU 读取

**核心方法：**
- `static sk_sp<Buffer> Make()` - 工厂方法，创建缓冲区
- `void setBufferAccess()` - 设置缓冲区访问模式并插入内存屏障
- `void onMap() / onUnmap()` - 映射和取消映射缓冲区内存
- `void freeGpuData()` - 释放 GPU 资源

## 公共 API 函数

### 缓冲区创建

```cpp
static sk_sp<Buffer> Make(
    const VulkanSharedContext* sharedContext,
    size_t size,
    BufferType type,
    AccessPattern accessPattern,
    std::string_view label
)
```

创建 Vulkan 缓冲区，根据类型和访问模式配置内存属性。

**参数：**
- `sharedContext` - Vulkan 共享上下文（设备、内存分配器等）
- `size` - 缓冲区大小（字节）
- `type` - 缓冲区类型（Vertex、Index、Uniform、Storage 等）
- `accessPattern` - 访问模式（HostVisible、GpuOnly、GpuOnlyCopySrc）
- `label` - 调试标签

**关键逻辑：**
1. **保护内存判定**：在保护模式下，仅 GpuOnly 模式的非顶点/索引缓冲区使用保护内存
2. **可映射性要求**：根据访问模式和硬件能力决定是否需要 CPU 可映射内存
3. **用途标志配置**：根据 `BufferType` 设置相应的 `VkBufferUsageFlags`
4. **内存分配策略**：选择合适的 `BufferUsage`（TransfersFromCpuToGpu、GpuOnly 等）

### 访问同步

```cpp
void setBufferAccess(
    VulkanCommandBuffer* cmdBuffer,
    VkAccessFlags dstAccess,
    VkPipelineStageFlags dstStageMask
) const
```

在缓冲区访问模式变化时插入内存屏障，确保 GPU 操作的正确顺序。

**同步规则：**
- 从 Host 访问后不需要屏障（CPU 写入隐式同步）
- 相同类型的只读访问不需要屏障
- 写后读、读后写需要插入 `VkBufferMemoryBarrier`

### GPU 资源释放

```cpp
void freeGpuData() override
```

释放 Vulkan 缓冲区和关联的设备内存。在对象销毁或资源回收时调用。

## 内部实现细节

### 缓冲区类型与用途映射

```cpp
switch (type) {
    case BufferType::kVertex:
        bufInfo.usage = VK_BUFFER_USAGE_VERTEX_BUFFER_BIT |
                        VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        break;
    case BufferType::kIndex:
        bufInfo.usage = VK_BUFFER_USAGE_INDEX_BUFFER_BIT |
                        VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        break;
    case BufferType::kUniform:
        bufInfo.usage = VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT;
        break;
    case BufferType::kStorage:
        bufInfo.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        break;
    case BufferType::kIndirect:
        bufInfo.usage = VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT |
                        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        break;
    // 其他类型...
}
```

顶点和索引缓冲区添加 `TRANSFER_DST_BIT` 以支持 `SkMesh` 缓冲区更新。

### 内存映射机制

```cpp
void internalMap(size_t readOffset, size_t readSize) {
    if (this->isMappable()) {
        fMapPtr = skgpu::VulkanMemory::MapAlloc(allocator, fAlloc, checkResult);
        if (fMapPtr && readSize != 0) {
            // 使设备写入对主机可见（GPU -> CPU 可见性）
            skgpu::VulkanMemory::InvalidateMappedAlloc(
                allocator, fAlloc, readOffset, readSize, checkResult_invalidate);
        }
    }
}

void internalUnmap(size_t flushOffset, size_t flushSize) {
    // 刷新映射内存范围（CPU -> GPU 可见性）
    skgpu::VulkanMemory::FlushMappedAlloc(
        allocator, fAlloc, flushOffset, flushSize, checkResult);
    skgpu::VulkanMemory::UnmapAlloc(allocator, fAlloc);
}
```

**CPU 读取场景**：映射时调用 `InvalidateMappedAlloc` 使 GPU 写入可见
**CPU 写入场景**：取消映射时调用 `FlushMappedAlloc` 使 CPU 写入对 GPU 可见

### 访问屏障优化

```cpp
VkPipelineStageFlags access_to_pipeline_srcStageFlags(VkAccessFlags srcAccess) {
    switch (srcAccess) {
        case VK_ACCESS_TRANSFER_WRITE_BIT:
        case VK_ACCESS_TRANSFER_READ_BIT:
            return VK_PIPELINE_STAGE_TRANSFER_BIT;
        case VK_ACCESS_UNIFORM_READ_BIT:
            return VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT |
                   VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT;
        case VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT:
            return VK_PIPELINE_STAGE_VERTEX_INPUT_BIT;
        // 其他访问类型...
    }
}
```

根据访问类型精确计算管线阶段，最小化同步开销。

### 保护内存限制

```cpp
bool isProtected = sharedContext->isProtected() == Protected::kYes &&
                   (accessPattern == AccessPattern::kGpuOnly ||
                    accessPattern == AccessPattern::kGpuOnlyCopySrc) &&
                   type != BufferType::kVertex &&
                   type != BufferType::kIndex;
```

由于 Vulkan 限制（bug b/374749633），顶点着色器无法使用保护缓冲区，因此顶点和索引缓冲区始终不使用保护内存。

## 依赖关系

**直接依赖：**
- `Buffer` - 基类，提供跨平台缓冲区接口
- `VulkanSharedContext` - 提供设备、队列、内存分配器
- `VulkanMemoryAllocator` - 内存分配接口
- `VulkanCommandBuffer` - 命令缓冲区，用于同步操作
- `VulkanMemory` - 底层内存操作工具

**被依赖者：**
- `VulkanResourceProvider` - 创建和管理缓冲区
- `VulkanCommandBuffer` - 使用缓冲区进行渲染和计算
- Graphite 上层渲染系统 - 通过 `Buffer` 接口使用

## 设计模式与设计决策

### 工厂模式
`Make()` 静态方法封装复杂的创建逻辑，根据参数选择合适的内存类型和用途标志。

### 状态跟踪模式
维护 `fCurrentAccess` 状态，在访问模式变化时自动插入必要的内存屏障，避免显式同步管理的复杂性。

### 资源所有权管理
使用 `sk_sp<Buffer>` 智能指针管理生命周期，在 `freeGpuData()` 中集中释放 Vulkan 资源。

### 内存策略优化
根据硬件能力（`gpuOnlyBuffersMorePerformant()`）动态选择内存类型：
- 高性能设备：优先使用 GPU 独占内存
- 低端设备：使用 CPU-GPU 共享内存减少传输

### 读写分离
通过 `fBufferUsedForCPURead` 标志区分读取和写入场景，在映射/取消映射时使用不同的缓存同步策略（Invalidate vs Flush）。

## 性能考量

1. **持久映射优化**
   根据 `shouldPersistentlyMapCpuToGpuBuffers()` 能力启用持久映射，减少 Map/Unmap 调用开销。

2. **内存类型选择**
   非必要情况下避免 CPU 可映射内存，优先使用设备本地内存以获得更高的 GPU 访问速度。

3. **屏障最小化**
   - 相同只读访问不插入屏障
   - Host 访问后利用隐式同步
   - 精确计算管线阶段，避免过度同步

4. **传输目标标志**
   为顶点/索引缓冲区添加 `TRANSFER_DST_BIT`，支持动态更新（SkMesh）而不需要重建缓冲区。

5. **缓存同步范围**
   `InvalidateMappedAlloc` 和 `FlushMappedAlloc` 仅操作实际使用的偏移和大小，减少缓存刷新开销。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/Buffer.h` | 缓冲区基类定义 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
| `src/gpu/graphite/vk/VulkanCommandBuffer.h` | Vulkan 命令缓冲区 |
| `src/gpu/vk/VulkanMemory.h` | Vulkan 内存分配工具 |
| `include/gpu/vk/VulkanMemoryAllocator.h` | 内存分配器接口 |
| `src/gpu/graphite/vk/VulkanCaps.h` | Vulkan 能力查询 |
| `src/gpu/graphite/vk/VulkanResourceProvider.h` | Vulkan 资源提供者 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | Vulkan 工具函数 |
