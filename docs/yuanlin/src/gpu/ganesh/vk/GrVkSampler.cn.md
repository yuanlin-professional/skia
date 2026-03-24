# GrVkSampler

> 源文件
> - `src/gpu/ganesh/vk/GrVkSampler.h`
> - `src/gpu/ganesh/vk/GrVkSampler.cpp`

## 概述

`GrVkSampler` 封装 Vulkan 采样器对象（`VkSampler`），负责管理纹理采样参数（过滤模式、寻址模式、各向异性等）和 YCbCr 颜色空间转换。该类继承自 `GrVkManagedResource`，支持引用计数和资源缓存。采样器通过 `GrVkResourceProvider` 缓存和复用，避免重复创建相同配置的采样器。

## 架构位置

```
GrVkManagedResource
    └── GrVkSampler (Vulkan 采样器封装)
```

由 `GrVkResourceProvider` 通过哈希表缓存管理。

## 主要类与结构体

### GrVkSampler 类

**核心成员**：
```cpp
VkSampler fSampler;                             // Vulkan 采样器对象
GrVkSamplerYcbcrConversion* fYcbcrConversion;  // YCbCr 转换（可选）
Key fKey;                                       // 缓存键
uint32_t fUniqueID;                             // 唯一 ID
```

### Key 结构体

```cpp
struct Key {
    GrVkSamplerYcbcrConversion::Key fYcbcrKey;  // YCbCr 转换键
    uint32_t fSamplerKey;                        // 采样器状态键
    uint32_t fPadding = 0;                       // 对齐填充
};
```

采样器的缓存键，包含采样状态和 YCbCr 转换信息。

## 公共 API 函数

**Create** (静态工厂方法)
```cpp
static GrVkSampler* Create(
    GrVkGpu* gpu,
    GrSamplerState samplerState,
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo);
```
创建 Vulkan 采样器，支持标准采样参数和 YCbCr 转换。

**sampler / samplerPtr**
```cpp
VkSampler sampler() const;
const VkSampler* samplerPtr() const;
```
获取 Vulkan 采样器对象或指针。

**GenerateKey** (静态)
```cpp
static Key GenerateKey(
    GrSamplerState samplerState,
    const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo);
```
生成缓存键，用于哈希表查找。

**Hash** (静态)
```cpp
static uint32_t Hash(const Key& key);
```
计算键的哈希值。

**uniqueID**
```cpp
uint32_t uniqueID() const;
```
返回唯一 ID，用于调试和跟踪。

## 内部实现细节

### 采样器创建

**参数映射**：
- **过滤模式**：`kNearest`, `kLinear` 映射到 `VK_FILTER_NEAREST/LINEAR`
- **Mipmap 模式**：`kNone/kNearest/kLinear` 映射到 `VK_SAMPLER_MIPMAP_MODE_*`
- **寻址模式**：`kClamp/kRepeat/kMirrorRepeat/kClampToBorder` 映射到 `VK_SAMPLER_ADDRESS_MODE_*`
- **各向异性**：启用时设置 `maxAnisotropy`，不超过硬件限制

**Mipmap 禁用技巧**：
```cpp
createInfo.minLod = 0.0f;
createInfo.maxLod = !useMipMaps ? 0.0f : 10000.0f;
```
通过设置 `maxLod = 0` 强制只采样 0 级 mipmap，实现禁用 mipmap 效果。

**YCbCr 转换处理**：
```cpp
if (ycbcrInfo.isValid()) {
    ycbcrConversion = gpu->resourceProvider()
        .findOrCreateCompatibleSamplerYcbcrConversion(ycbcrInfo);
    conversionInfo.conversion = ycbcrConversion->ycbcrConversion();
    createInfo.pNext = &conversionInfo;

    // YCbCr 要求特定设置
    createInfo.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    createInfo.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    createInfo.anisotropyEnable = VK_FALSE;
    if (ycbcrConversion->requiredFilter().has_value()) {
        createInfo.magFilter = ycbcrConversion->requiredFilter().value();
        createInfo.minFilter = ycbcrConversion->requiredFilter().value();
    }
}
```

YCbCr 转换对采样器有严格要求：必须 clamp 寻址、禁用各向异性、可能强制特定过滤模式。

### 键生成

```cpp
GrVkSampler::Key GenerateKey(GrSamplerState samplerState,
                             const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo) {
    return {samplerState.asKey(/*anisoIsOrthogonal=*/true),
            GrVkSamplerYcbcrConversion::GenerateKey(ycbcrInfo)};
}
```

Vulkan 中各向异性过滤与其他过滤模式正交（可独立设置），因此 `anisoIsOrthogonal=true`。

### 唯一 ID 生成

```cpp
uint32_t GenID() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID++;
    } while (id == SK_InvalidUniqueID);
    return id;
}
```

使用原子变量生成线程安全的唯一 ID，跳过无效 ID。

### 资源释放

```cpp
void freeGPUData() const {
    GR_VK_CALL(..., DestroySampler(..., fSampler, nullptr));
    if (fYcbcrConversion) {
        fYcbcrConversion->unref();
    }
}
```

销毁采样器并释放关联的 YCbCr 转换对象。

## 依赖关系

- `GrVkGpu`: GPU 接口
- `GrVkResourceProvider`: 资源提供器（缓存和查找）
- `GrVkSamplerYcbcrConversion`: YCbCr 转换对象
- `GrVkManagedResource`: 托管资源基类
- `GrSamplerState`: 采样器状态封装

## 设计模式与设计决策

### 不可变对象

采样器创建后不可修改，确保缓存安全和并发访问安全。

### 键值缓存

通过 `Key` 结构体和哈希函数实现高效缓存查找，`GrVkResourceProvider` 使用 `SkTDynamicHash` 管理。

### YCbCr 转换集成

YCbCr 转换对象独立管理，采样器持有引用。多个采样器可共享同一转换对象。

### 原子 ID 生成

使用 `std::atomic` 确保多线程环境下 ID 生成安全。

## 性能考量

### 采样器复用

通过 `GrVkResourceProvider` 缓存，避免重复创建：
- 采样器创建有一定开销
- 缓存命中率高（有限的采样状态组合）
- 减少驱动层对象管理开销

### 各向异性限制

```cpp
createInfo.maxAnisotropy = std::min(
    static_cast<float>(samplerState.maxAniso()),
    gpu->vkCaps().maxSamplerAnisotropy());
```

限制各向异性级别不超过硬件支持，避免驱动拒绝创建。

### Mipmap 禁用优化

通过 LOD 范围而非 mipmap 模式禁用 mipmap，确保过滤器设置生效（Vulkan 要求指定 mipmap 模式）。

## 相关文件

- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: GPU 接口
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkSamplerYcbcrConversion.h/cpp`: YCbCr 转换
- `src/gpu/ganesh/vk/GrVkManagedResource.h`: 托管资源基类
- `src/gpu/ganesh/GrSamplerState.h`: 采样器状态
