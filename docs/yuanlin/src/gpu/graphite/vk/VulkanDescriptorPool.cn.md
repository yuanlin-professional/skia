# VulkanDescriptorPool

> 源文件
> - `src/gpu/graphite/vk/VulkanDescriptorPool.h`
> - `src/gpu/graphite/vk/VulkanDescriptorPool.cpp`

## 概述

`VulkanDescriptorPool` 是 Skia Graphite 的 Vulkan 后端中用于管理描述符池和描述符集布局的包装类。它封装了 `VkDescriptorPool` 和 `VkDescriptorSetLayout` 对象，负责根据指定的描述符类型和数量创建描述符池，并管理这些资源的生命周期。描述符池是 Vulkan 中分配描述符集的内存池，用于高效地批量分配和释放描述符集，这些描述符集绑定着色器访问的资源（纹理、缓冲区、采样器等）。

## 架构位置

`VulkanDescriptorPool` 位于 Vulkan 描述符管理层：

```
skgpu::graphite 描述符管理架构
    ├── VulkanDescriptorPool (描述符池管理)
    │    ├── 封装 VkDescriptorPool
    │    ├── 持有 VkDescriptorSetLayout
    │    └── 支持批量分配描述符集
    ├── VulkanDescriptorSet (描述符集)
    │    └── 从 VulkanDescriptorPool 分配
    └── VulkanCommandBuffer 使用描述符集
         └── 绑定资源到着色器管线
```

它为渲染和计算管线提供资源绑定的基础设施。

## 主要类与结构体

### VulkanDescriptorPool

```cpp
class VulkanDescriptorPool : public SkRefCnt
```

**核心成员变量：**
- `VkDescriptorPool fDescPool` - Vulkan 描述符池句柄
- `VkDescriptorSetLayout fDescSetLayout` - 描述符集布局（池拥有所有权）
- `const VulkanSharedContext* fSharedContext` - Vulkan 共享上下文
- `static constexpr int kMaxNumDescriptors = 1024` - 单个描述符类型的最大数量限制

**核心方法：**
- `static sk_sp<VulkanDescriptorPool> Make()` - 创建描述符池
- `VkDescriptorPool descPool()` - 获取描述符池句柄
- `const VkDescriptorSetLayout* descSetLayout()` - 获取描述符集布局

## 公共 API 函数

### 描述符池创建

```cpp
static sk_sp<VulkanDescriptorPool> Make(
    const VulkanSharedContext* context,
    SkSpan<DescriptorData> requestedDescCounts,
    VkDescriptorSetLayout layout,
    uint32_t numSets
)
```

创建描述符池，能够容纳指定类型和数量的描述符。

**参数：**
- `context` - Vulkan 共享上下文
- `requestedDescCounts` - 描述符类型和数量数组（每个 `DescriptorData` 包含类型和数量）
- `layout` - 描述符集布局（池获得所有权）
- `numSets` - 池中可分配的最大描述符集数量

**返回值：**
智能指针指向新创建的 `VulkanDescriptorPool`，失败返回 nullptr。

**实现流程：**
1. 验证输入参数（描述符数组非空，每个数量 > 0）
2. 为每个描述符类型创建 `VkDescriptorPoolSize` 结构
3. 计算总描述符数量：`descriptorCount = fCount * numSets`
4. 检查描述符数量是否超过 `kMaxNumDescriptors` 限制
5. 调用 `vkCreateDescriptorPool` 创建池
6. 创建失败时销毁传入的布局对象
7. 返回包装后的 `VulkanDescriptorPool` 对象

### 描述符池访问

```cpp
VkDescriptorPool descPool()
```

返回底层的 `VkDescriptorPool` 句柄，用于分配描述符集。

### 描述符集布局访问

```cpp
const VkDescriptorSetLayout* descSetLayout()
```

返回描述符集布局的指针，用于分配描述符集时指定布局。

**断言检查：** 布局必须有效（非 `VK_NULL_HANDLE`）。

## 内部实现细节

### 构造函数

```cpp
VulkanDescriptorPool::VulkanDescriptorPool(
    const VulkanSharedContext* context,
    VkDescriptorPool pool,
    VkDescriptorSetLayout layout
)
    : fSharedContext(context)
    , fDescPool(pool)
    , fDescSetLayout(layout)
```

私有构造函数，仅通过 `Make()` 工厂方法调用，确保对象创建的一致性。

### 析构函数

```cpp
~VulkanDescriptorPool() override {
    // 销毁描述符池（自动释放所有分配的描述符集）
    VULKAN_CALL(fSharedContext->interface(),
                DestroyDescriptorPool(fSharedContext->device(), fDescPool, nullptr));

    // 销毁描述符集布局
    if (fDescSetLayout != VK_NULL_HANDLE) {
        VULKAN_CALL(fSharedContext->interface(),
                    DestroyDescriptorSetLayout(fSharedContext->device(), fDescSetLayout, nullptr));
        fDescSetLayout = VK_NULL_HANDLE;
    }
}
```

**关键特性：**
- **自动释放描述符集**：销毁 `VkDescriptorPool` 会自动释放从中分配的所有 `VkDescriptorSet`
- **布局所有权**：`VulkanDescriptorPool` 拥有并管理 `VkDescriptorSetLayout` 的生命周期

### 描述符池大小计算

```cpp
for (size_t i = 0; i < requestedDescCounts.size(); i++) {
    VkDescriptorPoolSize& poolSize = poolSizes.push_back();
    poolSize.type = DsTypeEnumToVkDs(requestedDescCounts[i].fType);
    poolSize.descriptorCount = requestedDescCounts[i].fCount * numSets;
}
```

**计算逻辑：**
- 每个描述符类型的池大小 = 单个描述符集中的数量 × 最大描述符集数量
- 例如：如果每个集合需要 5 个采样器，最多分配 10 个集合，则池需要 50 个采样器描述符

### 描述符类型映射

```cpp
poolSize.type = DsTypeEnumToVkDs(requestedDescCounts[i].fType);
```

将 Graphite 的 `DescriptorType` 枚举映射到 Vulkan 的 `VkDescriptorType`，例如：
- `DescriptorType::kUniformBuffer` → `VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER`
- `DescriptorType::kCombinedImageSampler` → `VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER`

### 错误处理

```cpp
if (requestedDescCounts[i].fCount > kMaxNumDescriptors) {
    SkDebugf("The number of descriptors requested, %u, exceeds the maximum allowed (%d).\n",
             requestedDescCounts[i].fCount, kMaxNumDescriptors);
    return nullptr;
}
```

对单个描述符类型的数量进行限制，防止过度分配。

### 失败清理

```cpp
if (result != VK_SUCCESS) {
    VULKAN_CALL(context->interface(),
                DestroyDescriptorSetLayout(context->device(), layout, nullptr));
    return nullptr;
}
```

创建池失败时，销毁传入的布局对象，避免资源泄漏。

## 依赖关系

**直接依赖：**
- `SkRefCnt` - 引用计数基类
- `VulkanSharedContext` - Vulkan 共享上下文
- `DescriptorData` - 描述符类型和数量数据结构
- `VkDescriptorPool` / `VkDescriptorSetLayout` - Vulkan 描述符类型

**被依赖者：**
- `VulkanDescriptorSet` - 从池中分配描述符集
- `VulkanResourceProvider` - 创建和管理描述符池
- `VulkanCommandBuffer` - 使用描述符集绑定资源

## 设计模式与设计决策

### RAII 资源管理
通过智能指针和析构函数自动管理 Vulkan 对象生命周期，确保无资源泄漏。

### 工厂模式
`Make()` 静态方法封装 Vulkan API 调用和对象构造，提供统一的创建接口。

### 所有权转移
池获得 `VkDescriptorSetLayout` 的所有权，简化生命周期管理（布局与池同生共死）。

### 批量分配优化
通过指定 `numSets` 参数，创建能够容纳多个描述符集的池，减少池创建次数。

### 类型安全的描述符映射
使用 `DescriptorData` 和 `DsTypeEnumToVkDs()` 映射函数，避免直接使用 Vulkan 枚举，增强可移植性。

### 防御性限制
`kMaxNumDescriptors` 限制防止异常大的分配请求，保护驱动稳定性。

### 自动描述符集清理
Vulkan 规范保证销毁池时自动释放所有描述符集，因此不需要显式释放每个集合。

## 性能考量

1. **批量分配效率**
   描述符池支持快速的批量分配，比逐个创建描述符集高效得多。

2. **内存局部性**
   从同一池分配的描述符集在内存中相邻，提高缓存命中率。

3. **重置而非销毁**
   虽然当前实现未使用，但 `VkDescriptorPool` 支持重置操作（`vkResetDescriptorPool`），可一次性释放所有描述符集而不销毁池。

4. **引用计数开销**
   继承自 `SkRefCnt`，使用原子引用计数，线程安全但有轻微性能开销。

5. **限制过度分配**
   `kMaxNumDescriptors = 1024` 限制防止过大的池创建，避免浪费驱动内存。

6. **失败快速返回**
   参数验证在 Vulkan API 调用前进行，失败快速返回，减少无效 API 调用。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
| `src/gpu/graphite/DescriptorData.h` | 描述符数据结构定义 |
| `src/gpu/graphite/vk/VulkanDescriptorSet.h` | 描述符集类 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | Vulkan 工具函数（包含类型映射） |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkSpan.h` | 数组视图类 |
| `include/gpu/vk/VulkanTypes.h` | Vulkan 类型定义 |
