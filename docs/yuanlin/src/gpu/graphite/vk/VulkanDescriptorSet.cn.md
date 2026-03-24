# VulkanDescriptorSet -- Vulkan 描述符集封装

> 源文件:
> - `src/gpu/graphite/vk/VulkanDescriptorSet.h`
> - `src/gpu/graphite/vk/VulkanDescriptorSet.cpp`

## 概述

VulkanDescriptorSet 是对 `VkDescriptorSet` 的 RAII 封装类,继承自 Graphite 的 `Resource` 基类。它通过引用计数管理其关联的 `VulkanDescriptorPool` 的生命周期,确保描述符池在所有从其分配的描述符集被释放后才会被销毁。

## 架构位置

```
Resource (Graphite 资源基类)
  -> VulkanDescriptorSet  <-- 本模块
       -> VulkanDescriptorPool (描述符池)
```

描述符集是 Vulkan 管线绑定资源（纹理、缓冲区等）的核心机制,被 `VulkanCommandBuffer` 在绘制和计算调度时使用。

## 主要类与结构体

### VulkanDescriptorSet

```cpp
class VulkanDescriptorSet : public Resource {
    VkDescriptorSet             fDescSet;
    sk_sp<VulkanDescriptorPool> fPool;
};
```

| 成员 | 用途 |
|------|------|
| `fDescSet` | 底层 Vulkan 描述符集句柄 |
| `fPool` | 指向分配该描述符集的描述符池的引用计数指针 |

## 公共 API 函数

### Make -- 静态工厂方法

```cpp
static sk_sp<VulkanDescriptorSet> Make(const VulkanSharedContext*,
                                       const sk_sp<VulkanDescriptorPool>&);
```
从给定的描述符池中分配一个 `VkDescriptorSet`。使用 `VkDescriptorSetAllocateInfo` 指定池句柄和布局,失败时返回 nullptr。

### descriptorSet -- 获取底层句柄

```cpp
const VkDescriptorSet* descriptorSet();
```
返回底层 `VkDescriptorSet` 的指针,供 Vulkan API 调用使用。

## 内部实现细节

### 构造函数

```cpp
VulkanDescriptorSet(const VulkanSharedContext*, VkDescriptorSet, sk_sp<VulkanDescriptorPool>);
```
构造时显式设置 `reusableRequiresPurgeable=true`,因为该对象可能在 Skia API 调用期间被 `VulkanCommandBuffer` 立即修改,不在命令缓冲区执行流程内。构造时额外调用 `fPool->ref()` 增加池的引用计数。

### freeGpuData

```cpp
void freeGpuData() override;
```
释放时调用 `fPool->unref()` 减少描述符池的引用计数。注意:不需要显式释放 `VkDescriptorSet`,因为当所有引用的描述符集释放后,池本身会被销毁,Vulkan 会自动回收池中的所有描述符集。

## 依赖关系

- `Resource` -- Graphite 资源基类,提供引用计数和资源管理
- `VulkanDescriptorPool` -- 描述符池,提供分配和布局信息
- `VulkanSharedContext` -- 设备访问
- `VulkanGraphiteUtils.h` -- Vulkan 调用宏

## 设计模式与设计决策

1. **隐式池生命周期管理**: 通过在描述符集中持有对池的引用,当池的引用计数归零时(即所有描述符集都已释放),池可以安全销毁。这避免了显式跟踪池中活跃描述符集的复杂性。

2. **资源系统集成**: 继承 `Resource` 基类使描述符集可以参与 Graphite 的资源缓存和回收机制。`reusableRequiresPurgeable=true` 确保在复用时遵循正确的清除语义。

3. **零 GPU 内存报告**: 构造时 `gpuMemorySize=0`,因为描述符集的实际内存由描述符池管理。

## 性能考量

- 描述符集分配是轻量操作,Vulkan 从预分配的池中快速分配。
- 引用计数管理确保池的延迟销毁,避免在描述符集仍在使用时意外释放池。
- `getResourceType()` 返回硬编码字符串,用于调试和资源追踪。

## 相关文件

- `src/gpu/graphite/vk/VulkanDescriptorPool.h` -- 描述符池管理
- `src/gpu/graphite/Resource.h` -- Graphite 资源基类
- `src/gpu/graphite/vk/VulkanCommandBuffer.h` -- 使用描述符集的命令缓冲区
- `src/gpu/graphite/DescriptorData.h` -- 描述符数据定义
