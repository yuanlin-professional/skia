# VulkanYcbcrConversion

> 源文件
> - src/gpu/graphite/vk/VulkanYcbcrConversion.h
> - src/gpu/graphite/vk/VulkanYcbcrConversion.cpp

## 概述

`VulkanYcbcrConversion` 是 Skia Graphite Vulkan 后端中用于处理 YCbCr 色彩空间转换的 GPU 资源类。YCbCr（也称为 YUV）是视频和图像处理中常用的色彩空间，将亮度（Y）与色度（Cb、Cr）分离，与常见的 RGB 色彩空间不同。该类封装了 Vulkan 的 `VkSamplerYcbcrConversion` 对象，用于在 GPU 采样纹理时自动执行色彩空间转换。

主要功能包括：
- 创建和管理 Vulkan YCbCr 采样器转换对象
- 支持 Android 平台的外部格式（如相机输出的硬件缓冲区）
- 处理色度采样滤波器的特殊要求
- 在紧凑的整数表示（`ImmutableSamplerInfo`）与完整的转换信息结构之间转换

该类主要用于视频纹理采样、相机预览帧处理、以及需要 YCbCr 格式图像的多媒体应用场景。

## 架构位置

`VulkanYcbcrConversion` 位于 Skia Graphite 渲染引擎的 Vulkan 后端资源管理层：

```
skgpu::graphite (Graphite 渲染引擎)
  ├── Resource (GPU 资源基类)
  └── vk (Vulkan 后端)
      ├── VulkanSharedContext (Vulkan 上下文)
      ├── VulkanCaps (能力查询)
      ├── VulkanTexture (纹理资源)
      ├── VulkanSampler (采样器)
      └── VulkanYcbcrConversion (YCbCr 转换 - 本类)
```

在采样管线中的位置：
```
纹理数据 (YCbCr 格式)
  → VulkanTexture (纹理对象)
  → VulkanYcbcrConversion (色彩空间转换)
  → VulkanSampler (采样器，带不可变采样器)
  → 着色器 (接收 RGB 格式数据)
```

## 主要类与结构体

### VulkanYcbcrConversion

继承自 `Resource`，表示一个 YCbCr 色彩空间转换的 GPU 资源。

**关键成员：**
- `VkSamplerYcbcrConversion fYcbcrConversion` - Vulkan YCbCr 转换对象句柄
- `std::optional<VkFilter> fRequiredFilter` - 可选的必需滤波器类型

**主要方法：**
- `static sk_sp<VulkanYcbcrConversion> Make(...)` - 创建转换对象
- `const VkSamplerYcbcrConversion& ycbcrConversion()` - 获取 Vulkan 句柄
- `std::optional<VkFilter> requiredFilter()` - 获取必需的滤波器设置
- `static ImmutableSamplerInfo ToImmutableSamplerInfo(...)` - 转换为紧凑表示
- `static VulkanYcbcrConversionInfo FromImmutableSamplerInfo(...)` - 从紧凑表示还原

### 相关结构体

**VulkanYcbcrConversionInfo** （定义在其他头文件）
包含创建 YCbCr 转换所需的所有参数：
- 格式信息（VkFormat 或外部格式）
- 色彩模型（YCbCr 模型类型）
- 色彩范围（窄范围或全范围）
- 色度采样偏移
- 色度滤波器
- 组件映射
- 各种标志位

**ImmutableSamplerInfo**
紧凑的位域表示，用于高效存储和比较：
- `uint32_t fNonFormatYcbcrConversionInfo` - 除格式外的所有信息打包为 32 位整数
- `uint64_t fFormat` - 格式或外部格式 ID

## 公共 API 函数

### Make

```cpp
static sk_sp<VulkanYcbcrConversion> Make(
    const VulkanSharedContext* context,
    const VulkanYcbcrConversionInfo& conversionInfo)
```

**功能：** 创建 YCbCr 转换资源的工厂方法。

**参数：**
- `context` - Vulkan 共享上下文，提供设备和接口访问
- `conversionInfo` - YCbCr 转换的配置信息

**返回值：** 智能指针包装的 `VulkanYcbcrConversion` 对象，失败时返回 nullptr

**实现细节：**
1. 检查设备是否支持 YCbCr 转换（通过 `VulkanCaps`）
2. 将 `VulkanYcbcrConversionInfo` 转换为 Vulkan API 的创建信息结构
3. 在 Android 平台上，处理外部格式的特殊情况（将外部格式信息追加到 `pNext` 链）
4. 调用 `vkCreateSamplerYcbcrConversion` 创建 Vulkan 对象
5. 封装为 `VulkanYcbcrConversion` 资源对象

**平台差异：**
- Android：支持外部格式（如 `AHardwareBuffer` 的格式）
- 其他平台：仅支持标准 Vulkan 格式

### ycbcrConversion

```cpp
const VkSamplerYcbcrConversion& ycbcrConversion() const
```

**功能：** 获取底层 Vulkan YCbCr 转换对象句柄。

**返回值：** Vulkan 句柄的常量引用

**用途：** 创建不可变采样器（Immutable Sampler）时需要此句柄。

### requiredFilter

```cpp
std::optional<VkFilter> requiredFilter() const
```

**功能：** 获取采样器必须使用的滤波器类型。

**返回值：** 可选的 `VkFilter` 值，如果未设置则为 `std::nullopt`

**含义：**
- 如果返回值有效，采样器的 `minFilter` 和 `magFilter` 必须与此值匹配
- 这是 Vulkan 规范的要求，当格式不支持 `VK_FORMAT_FEATURE_SAMPLED_IMAGE_YCBCR_CONVERSION_SEPARATE_RECONSTRUCTION_FILTER_BIT` 特性时生效
- 如果返回 `nullopt`，采样器的滤波器可以独立设置

### ToImmutableSamplerInfo

```cpp
static ImmutableSamplerInfo ToImmutableSamplerInfo(
    const VulkanYcbcrConversionInfo& conversionInfo)
```

**功能：** 将完整的 YCbCr 转换信息打包为紧凑的不可变采样器信息。

**参数：** `conversionInfo` - 完整的 YCbCr 转换配置

**返回值：** 紧凑表示的 `ImmutableSamplerInfo` 结构

**实现细节：**
- 使用位操作将多个字段打包到 32 位整数中
- 每个字段占用固定的位数（1-3 位不等）
- 包含完整性检查，确保所有值都在合法范围内
- 格式/外部格式单独存储为 64 位整数

**位域分配：**
```
位 0: 是否使用外部格式
位 1-3: YCbCr 模型
位 4: YCbCr 范围
位 5: X 色度偏移
位 6: Y 色度偏移
位 7: 色度滤波器
位 8: 强制显式重建
位 9-11: 组件 R 映射
位 12-14: 组件 G 映射
位 15-17: 组件 B 映射
位 18-20: 组件 A 映射
位 21: 色度滤波器必须匹配
位 22: 支持线性滤波
```

### FromImmutableSamplerInfo

```cpp
static VulkanYcbcrConversionInfo FromImmutableSamplerInfo(
    ImmutableSamplerInfo info)
```

**功能：** 从紧凑表示还原为完整的 YCbCr 转换信息。

**参数：** `info` - 紧凑的不可变采样器信息

**返回值：** 完整的 `VulkanYcbcrConversionInfo` 结构

**实现细节：**
- 使用位掩码和位移操作从打包的整数中提取各个字段
- 根据"是否使用外部格式"标志位正确解释格式字段
- 将提取的原始值转换为对应的 Vulkan 枚举类型

## 内部实现细节

### 构造函数

```cpp
VulkanYcbcrConversion(const VulkanSharedContext* context,
                      VkSamplerYcbcrConversion ycbcrConversion,
                      std::optional<VkFilter> requiredFilter)
```

**参数说明：**
- `context` - 共享上下文
- `ycbcrConversion` - 已创建的 Vulkan 转换对象
- `requiredFilter` - 可选的必需滤波器

**初始化列表：**
- 调用基类 `Resource` 构造函数，设置所有权为 `kOwned`
- GPU 内存大小设为 0（转换对象本身不占用显存）
- 不支持可重用性（`reusableRequiresPurgeable=false`）

### freeGpuData

```cpp
void freeGpuData() override
```

**功能：** 释放 GPU 资源的虚函数实现。

**实现：**
1. 向下转型获取 `VulkanSharedContext`
2. 断言确保句柄有效
3. 调用 `vkDestroySamplerYcbcrConversion` 销毁 Vulkan 对象

**生命周期：** 当资源对象析构时，基类会自动调用此方法。

### 位域打包策略

代码使用匿名命名空间定义了完整的位域布局：

**设计考量：**
1. **紧凑性：** 将 10+ 个字段打包到 32 位，节省内存和传输开销
2. **确定性：** 每个字段有固定的位位置，便于调试和验证
3. **可扩展性：** 静态断言确保总位数不超过 32 位
4. **类型安全：** 使用常量定义而非魔法数字，易于维护

**位域验证：**
```cpp
static_assert(kSupportsLinearFilterShift + kSupportsLinearFilterBits <= 32);
```

确保在编译时检测位域溢出。

### Android 外部格式支持

在 Android 平台上，可以使用外部格式（通过 `VkExternalFormatANDROID`）：

```cpp
#ifdef SK_BUILD_FOR_ANDROID
    VkExternalFormatANDROID externalFormat;
    if (conversionInfo.hasExternalFormat()) {
        externalFormat.sType = VK_STRUCTURE_TYPE_EXTERNAL_FORMAT_ANDROID;
        externalFormat.externalFormat = conversionInfo.externalFormat();
        ycbcrCreateInfo.pNext = &externalFormat;
    }
#endif
```

**特点：**
- 外部格式时，`VkFormat` 必须为 `VK_FORMAT_UNDEFINED`
- 外部格式 ID 通常来自 `AHardwareBuffer_describe()`
- 只在 Android 平台编译时启用

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `src/gpu/graphite/Resource.h` | 基类定义 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型和宏定义 |
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | Vulkan Graphite 公共类型 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
| `src/gpu/graphite/vk/VulkanCaps.h` | 能力查询 |
| `src/core/SkChecksum.h` | 校验和工具（未直接使用） |
| `<cinttypes>` | 整数类型定义 |
| `<optional>` | 可选值类型 |

### 被依赖关系

该类被以下组件使用：
- **VulkanSampler** - 创建带不可变采样器的采样器对象
- **VulkanTexture** - YCbCr 格式纹理需要关联转换对象
- **VulkanDescriptorSet** - 绑定带 YCbCr 转换的纹理采样器
- **VulkanResourceProvider** - 资源缓存和创建

### 与其他系统的交互

```
VulkanYcbcrConversionInfo (用户提供)
    ↓
VulkanYcbcrConversion::Make() (创建资源)
    ↓
VulkanYcbcrConversion (资源对象)
    ↓
VulkanSampler (创建不可变采样器)
    ↓
VulkanDescriptorSet (绑定到描述符集)
    ↓
着色器采样 (自动进行色彩空间转换)
```

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法而非公共构造函数：
- 可以在创建失败时返回 `nullptr`（构造函数无法返回失败）
- 集中处理 Vulkan API 调用和错误检查
- 隐藏构造细节，降低使用者的复杂度

### 资源管理模式

继承自 `Resource` 基类：
- 统一的 GPU 资源生命周期管理
- 自动集成到资源追踪和回收系统
- 支持资源监控和调试工具

### 不可变对象模式

创建后对象状态不可变：
- 构造时设置所有字段，之后只读
- 线程安全，无需加锁
- 便于缓存和共享

### 位域打包模式

使用位操作打包多个字段：
- **优点：** 内存紧凑，适合作为哈希键或缓存键
- **缺点：** 代码复杂度较高，位操作容易出错
- **权衡：** 通过常量定义和静态断言降低出错风险

### 平台抽象

使用条件编译处理平台差异：
```cpp
#ifdef SK_BUILD_FOR_ANDROID
    // Android 特有代码
#else
    // 非 Android 平台
#endif
```

- 在不影响代码可读性的前提下支持平台特性
- 通过断言确保不在错误平台上调用特定代码

### 可选值模式

使用 `std::optional<VkFilter>` 表示可选的必需滤波器：
- 明确区分"未设置"与"设置为某值"
- 比使用哨兵值（如 -1）更安全和清晰
- 符合现代 C++ 最佳实践

## 性能考量

### 内存效率

1. **位域打包**
   - 将 10+ 个字段打包到 32 位整数
   - `ImmutableSamplerInfo` 总共只占用 12 字节（4 + 8）
   - 适合作为缓存键，减少哈希表内存开销

2. **零拷贝设计**
   - 返回引用而非拷贝 Vulkan 句柄
   - 使用智能指针管理对象生命周期，避免手动引用计数

### 创建性能

1. **延迟创建**
   - 只在首次需要时创建转换对象
   - 通过资源缓存避免重复创建

2. **设备能力检查**
   - 在 `Make` 中首先检查是否支持 YCbCr 转换
   - 快速失败，避免无效的 Vulkan API 调用

### 运行时性能

1. **GPU 硬件加速**
   - YCbCr 转换由 GPU 硬件执行，无 CPU 开销
   - 在纹理采样时自动完成，无额外着色器指令

2. **缓存友好**
   - 对象很小（只有两个成员变量）
   - 适合存储在紧凑的数据结构中

### 最佳实践

1. **复用转换对象**
   - 相同配置的转换对象应该共享
   - 使用资源缓存机制避免重复创建

2. **避免动态转换**
   - 转换对象是不可变采样器的一部分
   - 无法在运行时切换，应在创建纹理时确定

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/graphite/Resource.h` | 基类 | GPU 资源基类，提供生命周期管理 |
| `include/gpu/graphite/vk/VulkanGraphiteTypes.h` | 类型定义 | 定义 `VulkanYcbcrConversionInfo` 等公共类型 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | 上下文 | Vulkan 共享上下文，提供设备和接口访问 |
| `src/gpu/graphite/vk/VulkanCaps.h` | 能力查询 | 查询设备是否支持 YCbCr 转换 |
| `src/gpu/graphite/vk/VulkanSampler.h` | 使用者 | 创建带不可变采样器的采样器对象 |
| `src/gpu/graphite/vk/VulkanTexture.h` | 关联类 | YCbCr 格式纹理关联转换对象 |
| `src/gpu/graphite/vk/VulkanGraphiteUtils.h` | 工具函数 | Vulkan 相关的辅助函数 |
| `src/gpu/graphite/vk/VulkanDescriptorSet.h` | 使用者 | 描述符集绑定 YCbCr 采样器 |
