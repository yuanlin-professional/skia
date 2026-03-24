# VulkanTypes

> 源文件: `include/gpu/vk/VulkanTypes.h`

## 概述
VulkanTypes.h 定义了 Skia 与 Vulkan 图形 API 交互所需的核心类型、结构体和函数指针类型。该文件是 Skia GPU 后端中 Vulkan 实现的基础类型层,提供了内存分配、YCbCr 颜色转换、设备丢失处理等关键功能的类型定义。

## 架构位置
该文件位于 Skia 的 GPU 抽象层中,属于 `skgpu` 命名空间,专门服务于 Vulkan 后端实现。它是 Ganesh (传统 GPU 后端) 和 Graphite (新一代 GPU 后端) 共享的基础类型定义层,为上层的资源管理和渲染管线提供类型支持。

## 主要类型与结构体

### VulkanGetProc
**定义**: `using VulkanGetProc = std::function<PFN_vkVoidFunction(const char*, VkInstance, VkDevice)>`

函数类型别名,用于动态获取 Vulkan 函数指针。这是 Skia 与 Vulkan 驱动交互的核心机制。

**参数说明**:
- `const char*`: Vulkan 函数名称
- `VkInstance`: Vulkan 实例句柄或 VK_NULL_HANDLE
- `VkDevice`: Vulkan 设备句柄或 VK_NULL_HANDLE

### VulkanBackendMemory
**定义**: `typedef intptr_t VulkanBackendMemory`

不透明的内存句柄类型,用于标识通过 `VulkanMemoryAllocator` 分配的后端内存。使用整型指针确保跨平台兼容性。

### VulkanAlloc
Vulkan 内存分配的完整描述结构体,封装了 VkDeviceMemory 及其属性。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fMemory | VkDeviceMemory | Vulkan 设备内存句柄,借用的 RT 可为 VK_NULL_HANDLE |
| fOffset | VkDeviceSize | 内存偏移量 |
| fSize | VkDeviceSize | 分配大小,借用纹理可为不确定值 |
| fFlags | uint32_t | 内存属性标志位 (非相干、可映射、惰性分配) |
| fBackendMemory | VulkanBackendMemory | 后端内存分配器的句柄 |
| fUsesSystemHeap | bool | 是否使用系统堆 (私有成员) |

**标志位枚举**:
- `kNoncoherent_Flag (0x1)`: 映射后需刷新到设备
- `kMappable_Flag (0x2)`: 内存可被映射
- `kLazilyAllocated_Flag (0x4)`: 使用惰性分配创建

**操作符重载**:
实现了 `operator==` 用于比较两个分配是否引用相同的内存资源。

### VulkanYcbcrConversionInfo
封装 YCbCr (亮度-色度) 颜色空间转换的配置信息,主要用于 Android 硬件缓冲区的外部格式图像。

**核心成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFormat | VkFormat | 图像格式,外部图像必须为 VK_FORMAT_UNDEFINED |
| fExternalFormat | uint64_t | Android 外部格式标识符,非零表示外部图像 |
| fYcbcrModel | VkSamplerYcbcrModelConversion | YCbCr 颜色模型 (RGB/Rec601/Rec709等) |
| fYcbcrRange | VkSamplerYcbcrRange | 值范围 (ITU_FULL/ITU_NARROW) |
| fXChromaOffset | VkChromaLocation | 水平色度采样偏移 |
| fYChromaOffset | VkChromaLocation | 垂直色度采样偏移 |
| fChromaFilter | VkFilter | 色度通道插值滤波器 |
| fForceExplicitReconstruction | VkBool32 | 强制显式色度重建 |
| fComponents | VkComponentMapping | 颜色分量重映射 |
| fSamplerFilterMustMatchChromaFilter | bool | 采样器滤波器是否必须匹配色度滤波器 |
| fSupportsLinearFilter | bool | 是否支持线性滤波 |

## 公共 API 函数

### VulkanYcbcrConversionInfo 构造函数

#### 外部格式构造函数
```cpp
VulkanYcbcrConversionInfo(uint64_t externalFormat,
                          VkSamplerYcbcrModelConversion ycbcrModel,
                          VkSamplerYcbcrRange ycbcrRange,
                          VkChromaLocation xChromaOffset,
                          VkChromaLocation yChromaOffset,
                          VkFilter chromaFilter,
                          VkBool32 forceExplicitReconstruction,
                          VkComponentMapping components,
                          VkFormatFeatureFlags formatFeatures)
```
- **功能**: 为 Android 硬件缓冲区的外部格式创建转换信息
- **参数**:
  - `externalFormat`: Android 外部格式 ID
  - `formatFeatures`: 通过 `vkAndroidHardwareBufferFormatPropertiesANDROID` 查询得到的格式特性
- **用途**: 主要用于 Android 平台的相机/视频输出处理

#### 标准格式构造函数
```cpp
VulkanYcbcrConversionInfo(VkFormat format,
                          VkSamplerYcbcrModelConversion ycbcrModel,
                          ...)
```
- **功能**: 为标准 Vulkan 格式创建转换信息
- **参数**: `format` 为标准的 VkFormat 枚举值
- **用途**: 用于标准 YCbCr 格式的纹理采样

### `isValid()`
- **功能**: 检查转换信息是否有效配置
- **返回值**: 如果颜色模型非 RGB_IDENTITY 或存在外部格式则返回 true

### `toVkSamplerYcbcrConversionCreateInfo()`
```cpp
void toVkSamplerYcbcrConversionCreateInfo(
    VkSamplerYcbcrConversionCreateInfo* outInfo,
    std::optional<VkFilter>* requiredSamplerFilter) const
```
- **功能**: 将封装的信息转换为 Vulkan 原生的创建结构体
- **参数**:
  - `outInfo`: 输出的 Vulkan 创建信息
  - `requiredSamplerFilter`: 如果平台要求特定滤波器则返回该值
- **用途**: 创建 VkSamplerYcbcrConversion 对象前的准备步骤

### 设备丢失回调类型
```cpp
typedef void (*VulkanDeviceLostProc)(
    VulkanDeviceLostContext faultContext,
    const std::string& description,
    const std::vector<VkDeviceFaultAddressInfoEXT>& addressInfos,
    const std::vector<VkDeviceFaultVendorInfoEXT>& vendorInfos,
    const std::vector<std::byte>& vendorBinaryData)
```
- **功能**: 当接收到 `VK_ERROR_DEVICE_LOST` 错误时的回调函数类型
- **参数**:
  - `faultContext`: 用户提供的上下文指针
  - `description`: 错误描述字符串
  - `addressInfos`: 地址错误信息 (需 VK_EXT_device_fault 扩展)
  - `vendorInfos`: 厂商特定错误信息
  - `vendorBinaryData`: 厂商二进制调试数据
- **依赖**: 需要启用 `VK_EXT_device_fault` 扩展并在 `VkDeviceCreateInfo` 的 pNext 链中包含 `VkPhysicalDeviceFaultFeaturesEXT`

## 内部实现细节

### YCbCr 转换信息的完整性处理
`VulkanYcbcrConversionInfo` 内部有两个私有构造函数用于不同场景:
1. **公共构造函数**: 接受 `VkFormatFeatureFlags` 并根据特性标志自动设置 `fSamplerFilterMustMatchChromaFilter` 和 `fSupportsLinearFilter`
2. **友元构造函数**: 直接接受布尔标志,用于 `graphite::VulkanYcbcrConversion` 从不可变采样器信息重建对象

### 相等性比较的智能实现
`VulkanYcbcrConversionInfo::operator==` 实现了智能比较逻辑:
- 两个无效对象被认为相等
- 不比较 `fSamplerFilterMustMatchChromaFilter`,因为 Vulkan 规范保证相同外部格式具有相同特性支持
- 完整比较所有四个分量映射 (r, g, b, a)

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkTypes.h | Skia 基础类型定义 |
| include/private/base/SkTo.h | 类型转换工具 |
| include/private/gpu/vk/SkiaVulkan.h | Vulkan 头文件包装 |
| Vulkan SDK (1.1+) | Vulkan API 定义 |

### 被依赖的模块
- `VulkanBackendContext.h`: 使用 VulkanGetProc 和 VulkanAlloc
- `VulkanMemoryAllocator.h`: 使用 VulkanBackendMemory 和 VulkanAlloc
- Graphite Vulkan 后端: 使用 VulkanYcbcrConversionInfo
- Ganesh Vulkan 后端: 所有 Vulkan 资源管理

## 设计模式与设计决策

### 类型安全的不透明句柄
使用 `intptr_t` 作为 `VulkanBackendMemory` 确保:
- 指针大小的整数类型,可在不同架构间安全传递
- 不透明性隐藏分配器内部实现细节
- 可与 C++ 内存分配器 (如 VMA) 的句柄类型兼容

### 值语义结构体设计
`VulkanAlloc` 和 `VulkanYcbcrConversionInfo` 设计为值类型:
- 默认构造函数初始化所有成员为安全默认值
- 拷贝和移动语义自动生成
- 适合存储在标准容器中

### 扩展点设计
`VulkanDeviceLostProc` 回调提供了可选的调试扩展:
- 基础功能不依赖该扩展
- 支持扩展时提供详细的设备丢失诊断信息
- 回调参数使用 STL 容器确保内存安全

## 性能考量

### 内存布局优化
`VulkanAlloc` 结构体按字段大小排列,减少填充:
- 8 字节指针类型在前 (fMemory, fBackendMemory)
- 8 字节大小值 (fOffset, fSize)
- 4 字节标志在后 (fFlags)
- 布尔值在最后 (fUsesSystemHeap)

### 比较操作性能
`VulkanYcbcrConversionInfo::operator==`:
- 优先检查无效状态,快速路径返回
- 按成员声明顺序比较,可能的短路行为
- 跳过运行时可推导的字段 (fSamplerFilterMustMatchChromaFilter)

### 零开销抽象
`VulkanGetProc` 使用 `std::function` 提供灵活性,但在热路径中:
- 函数指针通常在初始化时解析并缓存
- 实际调用路径直接使用原始函数指针

## 平台相关说明

### Android 特定功能
`VulkanYcbcrConversionInfo` 的外部格式支持专为 Android 设计:
- `fExternalFormat` 直接对应 `AHardwareBuffer_Desc::format`
- 与 `VkExternalFormatANDROID` 结构体兼容
- 支持相机和媒体编解码器的零拷贝管线

### Vulkan 版本要求
文件开头明确检查:
```cpp
#ifndef VK_VERSION_1_1
#error Skia requires the use of Vulkan 1.1 headers
#endif
```
确保最低 API 级别,启用以下特性:
- 外部内存扩展 (Promoted to core in 1.1)
- YCbCr 采样 (Promoted to core in 1.1)
- 受保护内存 (Promoted to core in 1.1)

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/vk/VulkanBackendContext.h | 使用 VulkanGetProc 初始化上下文 |
| include/gpu/vk/VulkanMemoryAllocator.h | 实现 VulkanAlloc 的分配和释放 |
| include/gpu/graphite/vk/VulkanGraphiteTypes.h | Graphite 版本的类型定义,复用此文件类型 |
| include/private/gpu/vk/SkiaVulkan.h | Vulkan 头文件的统一包装 |
| src/gpu/vk/ (实现目录) | 各类型的实际使用和实现 |

## 使用示例场景

### 场景 1: 创建 YCbCr 采样器用于 Android 视频
```cpp
// 从 AHardwareBuffer 获取格式信息
VulkanYcbcrConversionInfo conversionInfo(
    externalFormat,                      // 从 AHB 查询
    VK_SAMPLER_YCBCR_MODEL_CONVERSION_YCBCR_709,
    VK_SAMPLER_YCBCR_RANGE_ITU_NARROW,
    VK_CHROMA_LOCATION_MIDPOINT,
    VK_CHROMA_LOCATION_MIDPOINT,
    VK_FILTER_LINEAR,
    VK_FALSE,
    {VK_COMPONENT_SWIZZLE_IDENTITY, ...},
    formatFeatures                       // 从驱动查询
);
```

### 场景 2: 检查内存分配属性
```cpp
VulkanAlloc alloc = /* ... 从分配器获取 */;
if (alloc.fFlags & VulkanAlloc::kMappable_Flag) {
    void* mappedPtr = allocator->mapMemory(alloc.fBackendMemory);
    // 操作映射内存
    if (alloc.fFlags & VulkanAlloc::kNoncoherent_Flag) {
        allocator->flushMemory(alloc.fBackendMemory, 0, alloc.fSize);
    }
    allocator->unmapMemory(alloc.fBackendMemory);
}
```

## 错误处理机制

### 设备丢失处理
通过 `VulkanDeviceLostProc` 回调机制:
1. Skia 检测到 `VK_ERROR_DEVICE_LOST` 返回值
2. 如果启用了 `VK_EXT_device_fault` 扩展,查询故障信息
3. 调用用户注册的回调函数,传递详细诊断数据
4. 回调可记录日志、生成崩溃报告或尝试设备重置

### YCbCr 转换验证
`isValid()` 方法确保配置的合法性:
- RGB_IDENTITY 模型必须配合外部格式使用
- 外部格式和标准格式互斥
- 构造函数内部根据格式特性自动设置滤波器约束
