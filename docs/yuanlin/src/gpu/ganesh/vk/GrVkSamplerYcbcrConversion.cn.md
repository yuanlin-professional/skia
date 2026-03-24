# GrVkSamplerYcbcrConversion

> 源文件
> - `src/gpu/ganesh/vk/GrVkSamplerYcbcrConversion.h`
> - `src/gpu/ganesh/vk/GrVkSamplerYcbcrConversion.cpp`

## 概述

`GrVkSamplerYcbcrConversion` 封装 Vulkan YCbCr 采样器颜色空间转换对象（`VkSamplerYcbcrConversion`），用于从 YUV 格式纹理（如视频帧）正确采样并转换到 RGB 颜色空间。该类支持标准 YCbCr 格式和 Android 外部格式，处理色度子采样、颜色模型转换、分量swizzle 等复杂配置。通过 `GrVkResourceProvider` 缓存复用，避免重复创建相同配置的转换对象。

## 架构位置

```
GrVkManagedResource
    └── GrVkSamplerYcbcrConversion (YCbCr 转换封装)
```

与 `GrVkSampler` 配合使用，由 `GrVkResourceProvider` 缓存管理。

## 主要类与结构体

### GrVkSamplerYcbcrConversion 类

**核心成员**：
```cpp
VkSamplerYcbcrConversion fYcbcrConversion;  // Vulkan YCbCr 转换对象
std::optional<VkFilter> fRequiredFilter;    // 必需的过滤模式（某些格式限制）
Key fKey;                                    // 缓存键
```

### Key 结构体

```cpp
struct Key {
    VkFormat fVkFormat = VK_FORMAT_UNDEFINED;  // Vulkan 格式（标准 YCbCr 格式）
    uint64_t fExternalFormat = 0;               // 外部格式（Android 专用）
    uint32_t fConversionKey = 0;                // 转换参数打包键
};
```

转换参数打包到 32 位整数：
- 位 0-2: 颜色模型（YCbCr 模型）
- 位 3: 颜色范围（narrow/full）
- 位 4-5: 色度偏移（X、Y 方向）
- 位 6: 色度过滤模式
- 位 7: 强制显式重建
- 位 8-19: 分量 swizzle（R/G/B/A 各 3 位）

## 公共 API 函数

**Create** (静态工厂方法)
```cpp
static GrVkSamplerYcbcrConversion* Create(
    GrVkGpu* gpu,
    const skgpu::VulkanYcbcrConversionInfo& info);
```
创建 YCbCr 转换对象。Android 上支持外部格式，其他平台只支持标准 Vulkan 格式。

**ycbcrConversion**
```cpp
VkSamplerYcbcrConversion ycbcrConversion() const;
```
返回 Vulkan 转换对象，用于创建采样器。

**requiredFilter**
```cpp
std::optional<VkFilter> requiredFilter() const;
```
返回必需的过滤模式。某些格式不支持独立设置 min/mag 过滤器，必须与 chroma filter 匹配。

**GenerateKey** (静态)
```cpp
static Key GenerateKey(const skgpu::VulkanYcbcrConversionInfo& ycbcrInfo);
```
生成缓存键，将所有转换参数打包成紧凑的键结构。

**Hash** (静态)
```cpp
static uint32_t Hash(const Key& key);
```
计算键的哈希值。

## 内部实现细节

### 外部格式支持（Android）

```cpp
#ifdef SK_BUILD_FOR_ANDROID
VkExternalFormatANDROID externalFormat;
if (info.hasExternalFormat()) {
    SkASSERT(info.format() == VK_FORMAT_UNDEFINED);  // 外部格式不指定 VkFormat
    externalFormat.externalFormat = info.externalFormat();
    ycbcrCreateInfo.pNext = &externalFormat;
}
#else
SkASSERT(!info.hasExternalFormat());  // 非 Android 平台不支持
#endif
```

Android 外部格式用于 AHardwareBuffer 等系统缓冲区，格式由系统定义，Skia 通过 64 位外部格式 ID 引用。

### 键生成算法

```cpp
uint32_t ycbcrKey = static_cast<uint32_t>(ycbcrInfo.model());           // 位 0-2
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.range()) << 3);            // 位 3
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.xChromaOffset()) << 4);    // 位 4
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.yChromaOffset()) << 5);    // 位 5
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.chromaFilter()) << 6);     // 位 6
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.forceExplicitReconstruction()) << 7); // 位 7
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.components().r) << 8);     // 位 8-10
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.components().g) << 11);    // 位 11-13
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.components().b) << 14);    // 位 14-16
ycbcrKey |= (static_cast<uint32_t>(ycbcrInfo.components().a) << 17);    // 位 17-19
```

紧凑打包所有参数，每个参数占用所需最小位数。

### 资源释放

```cpp
void freeGPUData() const {
    GR_VK_CALL(..., DestroySamplerYcbcrConversion(..., fYcbcrConversion, nullptr));
}
```

销毁 Vulkan 转换对象。

## 依赖关系

- `GrVkGpu`: GPU 接口
- `GrVkResourceProvider`: 资源提供器（缓存管理）
- `GrVkCaps`: Vulkan 能力查询（YCbCr 转换支持）
- `GrVkSampler`: 采样器（持有转换对象）
- `GrVkManagedResource`: 托管资源基类
- `skgpu::VulkanYcbcrConversionInfo`: YCbCr 转换配置信息

## 设计模式与设计决策

### 不可变对象

转换对象创建后不可修改，确保缓存安全。

### 紧凑键设计

将多个参数打包成 32 位整数，结合 VkFormat 和外部格式构成紧凑的缓存键，减少内存占用。

### 平台条件编译

Android 外部格式支持通过条件编译实现，非 Android 平台代码更简洁。

### 必需过滤器处理

某些格式（如特定 YCbCr 格式）对过滤器有限制，通过 `fRequiredFilter` 传递给采样器，确保符合 Vulkan 规范。

## 性能考量

### 转换对象复用

通过 `GrVkResourceProvider` 缓存，视频播放等场景中相同格式的帧复用同一转换对象，避免重复创建。

### 键生成优化

所有转换参数打包成整数，键生成和哈希计算非常快速。

### 外部格式支持

Android 外部格式允许 Skia 直接使用系统提供的 YUV 缓冲区（如相机、视频解码器输出），无需 CPU 转换。

## 相关文件

- `src/gpu/ganesh/vk/GrVkGpu.h/cpp`: GPU 接口
- `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp`: 资源提供器
- `src/gpu/ganesh/vk/GrVkSampler.h/cpp`: 采样器
- `src/gpu/ganesh/vk/GrVkCaps.h/cpp`: Vulkan 能力查询
- `src/gpu/ganesh/vk/GrVkManagedResource.h`: 托管资源基类
- `include/gpu/vk/VulkanTypes.h`: Vulkan 类型定义
- `src/gpu/vk/VulkanUtilsPriv.h`: Vulkan 工具函数
