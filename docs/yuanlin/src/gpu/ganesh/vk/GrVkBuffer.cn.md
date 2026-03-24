# GrVkBuffer

> 源文件
> - `src/gpu/ganesh/vk/GrVkBuffer.h`
> - `src/gpu/ganesh/vk/GrVkBuffer.cpp`

## 概述

`GrVkBuffer` 是 Ganesh Vulkan 后端中的核心缓冲区管理类,封装了 Vulkan 的 `VkBuffer` 对象及其相关内存管理功能。该类继承自 `GrGpuBuffer`,为 GPU 提供顶点缓冲区、索引缓冲区、Uniform 缓冲区、间接绘制缓冲区以及数据传输缓冲区等多种类型的缓冲区支持。它负责处理 Vulkan 缓冲区的创建、内存分配、映射/解映射、数据更新、内存屏障管理以及资源释放等完整生命周期。

## 架构位置

`GrVkBuffer` 位于 Skia 的 GPU Ganesh Vulkan 后端架构中:

```
Skia 渲染架构
├── Ganesh GPU 后端
│   ├── 通用 GPU 抽象层
│   │   └── GrGpuBuffer (基类)
│   └── Vulkan 后端实现
│       ├── GrVkGpu (Vulkan GPU 主控制器)
│       ├── GrVkBuffer (Vulkan 缓冲区封装) ← 当前类
│       ├── GrVkDescriptorSet (描述符集管理)
│       ├── GrVkResourceProvider (资源提供者)
│       └── VulkanMemoryAllocator (内存分配器)
```

该类是 Vulkan 后端资源管理的基础组件,为上层渲染操作提供高效的缓冲区抽象。

## 主要类与结构体

### 继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `GrGpuBuffer` | 父类 | 通用 GPU 缓冲区抽象基类 |
| `GrVkBuffer` | 当前类 | Vulkan 缓冲区具体实现 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBuffer` | `VkBuffer` | Vulkan 缓冲区句柄 |
| `fAlloc` | `skgpu::VulkanAlloc` | Vulkan 内存分配信息(包含内存句柄、偏移、大小、标志位) |
| `fUniformDescriptorSet` | `const GrVkDescriptorSet*` | Uniform 缓冲区的描述符集(仅 Uniform 类型) |
| `fMapPtr` | `void*` (继承自基类) | CPU 映射的内存指针 |

## 公共 API 函数

### 核心创建函数

```cpp
static sk_sp<GrVkBuffer> Make(GrVkGpu* gpu,
                               size_t size,
                               GrGpuBufferType bufferType,
                               GrAccessPattern accessPattern);
```
静态工厂函数,根据指定类型和访问模式创建 Vulkan 缓冲区。

**缓冲区类型支持:**
- `kVertex`: 顶点缓冲区 (`VK_BUFFER_USAGE_VERTEX_BUFFER_BIT`)
- `kIndex`: 索引缓冲区 (`VK_BUFFER_USAGE_INDEX_BUFFER_BIT`)
- `kDrawIndirect`: 间接绘制缓冲区 (`VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT`)
- `kUniform`: Uniform 缓冲区 (`VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT`)
- `kXferCpuToGpu`: CPU 到 GPU 传输缓冲区 (`VK_BUFFER_USAGE_TRANSFER_SRC_BIT`)
- `kXferGpuToCpu`: GPU 到 CPU 传输缓冲区 (`VK_BUFFER_USAGE_TRANSFER_DST_BIT`)

### 访问器函数

```cpp
VkBuffer vkBuffer() const;
```
返回底层 Vulkan 缓冲区句柄。

```cpp
const VkDescriptorSet* uniformDescriptorSet() const;
```
获取 Uniform 缓冲区的描述符集(仅对 Uniform 类型有效)。

### 同步函数

```cpp
void addMemoryBarrier(VkAccessFlags srcAccessMask,
                      VkAccessFlags dstAccesMask,
                      VkPipelineStageFlags srcStageMask,
                      VkPipelineStageFlags dstStageMask,
                      bool byRegion) const;
```
添加缓冲区内存屏障,用于管道同步和内存可见性控制。

## 内部实现细节

### 缓冲区创建流程

1. **内存类型决策**:
   - **Protected 内存**: 对于 static 访问模式的非顶点/索引/间接绘制缓冲区,在保护上下文中使用
   - **可映射内存**: Dynamic/Stream 访问模式或不支持 GPU-only 高性能模式时必须可映射
   - **GPU-only 内存**: Static 访问模式且硬件支持时使用,性能更高

2. **内存分配策略**:
   ```cpp
   BufferUsage allocUsage;
   if (bufferType == GrGpuBufferType::kXferCpuToGpu) {
       allocUsage = BufferUsage::kTransfersFromCpuToGpu;
   } else if (bufferType == GrGpuBufferType::kXferGpuToCpu) {
       allocUsage = BufferUsage::kTransfersFromGpuToCpu;
   } else {
       allocUsage = requiresMappable ? BufferUsage::kCpuWritesGpuReads
                                     : BufferUsage::kGpuOnly;
   }
   ```

3. **描述符集初始化**: Uniform 缓冲区需要创建并绑定描述符集,使用 `VkWriteDescriptorSet` 更新描述符。

### 数据更新机制

**映射更新** (可映射缓冲区):
```cpp
bool onUpdateData(const void* src, size_t offset, size_t size, bool preserve) {
    if (this->isVkMappable()) {
        this->vkMap(0, 0);  // 不读取现有数据
        memcpy(SkTAddOffset<void>(fMapPtr, offset), src, size);
        this->vkUnmap(offset, size);  // 仅刷新更新区域
    } else {
        this->copyCpuDataToGpuBuffer(src, offset, size);
    }
}
```

**命令缓冲区更新** (不可映射缓冲区):
- 小数据 (≤65536 字节且 4 字节对齐): 使用 `vkCmdUpdateBuffer`
- 大数据: 创建临时传输缓冲区,通过 `vkCmdCopyBuffer` 复制

### 内存同步

**映射时的 Invalidate**:
确保 GPU 写入的数据对 CPU 可见(用于读操作)。

**解映射时的 Flush**:
确保 CPU 写入的数据对 GPU 可见(用于写操作)。

### 资源释放

```cpp
void vkRelease() {
    if (fMapPtr) {
        this->vkUnmap(0, this->size());
    }
    if (fUniformDescriptorSet) {
        fUniformDescriptorSet->recycle();  // 回收描述符集
    }
    VK_CALL(gpu, DestroyBuffer(device, fBuffer, nullptr));
    skgpu::VulkanMemory::FreeBufferMemory(allocator, fAlloc);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrVkGpu` | 强依赖 | 提供 Vulkan 设备、接口和上下文 |
| `skgpu::VulkanMemoryAllocator` | 强依赖 | 内存分配和管理 |
| `GrVkDescriptorSet` | 条件依赖 | Uniform 缓冲区需要描述符集 |
| `GrVkResourceProvider` | 强依赖 | 提供描述符集等资源 |
| `GrVkCaps` | 强依赖 | 查询硬件能力和配置 |
| `skgpu::VulkanMemory` | 强依赖 | 底层内存操作(映射、刷新、释放) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GrVkOpsRenderPass` | 绑定顶点/索引/间接绘制缓冲区 |
| `GrVkPipelineState` | 绑定 Uniform 缓冲区描述符集 |
| `GrVkGpu` | 执行缓冲区传输和更新操作 |
| `GrResourceProvider` | 创建和管理缓冲区生命周期 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 函数而非公共构造函数,确保缓冲区创建的完整性和错误处理:
- 分配失败时自动清理
- Uniform 缓冲区描述符集创建失败时回滚
- 返回智能指针管理生命周期

### 策略模式

根据访问模式和缓冲区类型选择不同的内存分配和更新策略:
- Dynamic/Stream → 始终可映射
- Static + GPU-only 支持 → 不可映射高性能内存
- Protected 上下文 → Protected 内存

### 延迟映射

仅在真正需要访问时才映射内存,避免不必要的 CPU-GPU 同步开销。

### 描述符集复用

Uniform 缓冲区的描述符集通过 `GrVkResourceProvider` 获取,支持回收和复用,减少描述符集创建开销。

## 性能考量

### 内存映射优化

1. **持久映射**: 对于频繁更新的 CPU-to-GPU 缓冲区,`shouldPersistentlyMapCpuToGpuBuffers` 控制是否启用持久映射
2. **部分刷新**: `vkUnmap` 仅刷新实际修改的区域,避免全缓冲区刷新
3. **Invalidate 优化**: 读取前仅 Invalidate 需要读取的区域

### 数据传输优化

1. **小数据路径**: ≤65536 字节使用 `vkCmdUpdateBuffer`,避免额外缓冲区分配
2. **对齐检查**: 利用 `vkCmdUpdateBuffer` 的 4 字节对齐要求加速小数据更新
3. **临时缓冲区**: 大数据或不对齐数据使用动态传输缓冲区

### 硬件适配

```cpp
bool gpuOnlyBuffersMorePerformant = gpu->vkCaps().gpuOnlyBuffersMorePerformant();
```
查询硬件特性,在支持的设备上使用 GPU-only 内存获得更好的读取性能。

### 内存屏障精细化

支持指定访问掩码和管道阶段,避免过度同步:
```cpp
bufferMemoryBarrier.srcAccessMask = srcAccessMask;
bufferMemoryBarrier.dstAccessMask = dstAccesMask;
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuBuffer.h` | 父类 | 通用 GPU 缓冲区接口定义 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 协作 | Vulkan GPU 主控制器 |
| `src/gpu/ganesh/vk/GrVkDescriptorSet.h` | 协作 | Uniform 描述符集管理 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h` | 协作 | 资源提供和管理 |
| `src/gpu/ganesh/vk/GrVkCaps.h` | 协作 | 硬件能力查询 |
| `src/gpu/vk/VulkanMemory.h` | 依赖 | 底层内存操作 |
| `include/gpu/vk/VulkanMemoryAllocator.h` | 依赖 | 内存分配器接口 |
| `src/gpu/ganesh/vk/GrVkUtil.h` | 工具 | Vulkan 工具函数 |
| `src/gpu/ganesh/vk/GrVkUniformHandler.h` | 协作 | Uniform 绑定信息 |
