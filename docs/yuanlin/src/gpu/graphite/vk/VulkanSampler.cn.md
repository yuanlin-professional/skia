# VulkanSampler

> 源文件: `src/gpu/graphite/vk/VulkanSampler.h`, `src/gpu/graphite/vk/VulkanSampler.cpp`

## 概述

`VulkanSampler` 是 Skia Graphite Vulkan 后端中对 `VkSampler` 的封装，继承自通用的 `Sampler` 基类。它将 Skia 的采样选项（过滤模式、平铺模式、mipmap 模式）转换为 Vulkan 采样器参数，并支持可选的 YCbCr 颜色空间转换。

## 架构位置

- **上层**: 由 `VulkanResourceProvider::createSampler()` 创建
- **基类**: 继承自 `Sampler`，参与资源缓存
- **使用者**: 被 `VulkanCommandBuffer` 用于纹理采样描述符集的绑定

## 主要类与结构体

### `VulkanSampler` 类

**私有成员**:
- `fDesc` — 采样器描述（`SamplerDesc`），用于创建描述符时快速访问
- `fSampler` — `VkSampler` 句柄
- `fYcbcrConversion` — 可选的 YCbCr 转换对象

## 公共 API 函数

- **`Make(VulkanSharedContext*, SamplerDesc, sk_sp<VulkanYcbcrConversion>)`** — 静态工厂方法
- **`vkSampler()`** — 返回原始 VkSampler 句柄
- **`ycbcrConversion()`** — 返回 YCbCr 转换对象指针
- **`samplerDesc()`** — 返回采样器描述引用
- **`constVkSamplerPtr()`** — 返回 VkSampler 的常量指针（用于不可变采样器）

## 内部实现细节

### 过滤模式映射

| Skia 过滤模式 | Vulkan 过滤模式 |
|-------------|--------------|
| `kNearest` | `VK_FILTER_NEAREST` |
| `kLinear` | `VK_FILTER_LINEAR` |

YCbCr 转换可能覆盖过滤模式（通过 `requiredFilter()`）。

### 平铺模式映射

| Skia 平铺模式 | Vulkan 寻址模式 |
|-------------|--------------|
| `kClamp` | `CLAMP_TO_EDGE` |
| `kRepeat` | `REPEAT` |
| `kMirror` | `MIRRORED_REPEAT` |
| `kDecal` | `CLAMP_TO_BORDER`（透明黑色边界） |

W 轴始终使用 `CLAMP_TO_EDGE`。

### Mipmap 处理

| Skia Mipmap 模式 | Vulkan Mipmap 模式 | maxLod |
|----------------|-----------------|--------|
| `kNone` | `LINEAR` | 0.0（禁用 mipmap） |
| `kNearest` | `NEAREST` | `VK_LOD_CLAMP_NONE` |
| `kLinear` | `LINEAR` | `VK_LOD_CLAMP_NONE` |

通过设置 `maxLod = 0.0` 而非 "NONE" 模式来禁用 mipmap，因为 Vulkan 没有直接的禁用选项。`minLod` 始终为 0。

### YCbCr 转换

如果提供了 `VulkanYcbcrConversion`，则通过 `VkSamplerYcbcrConversionInfo` 链接到采样器创建信息的 `pNext` 链中。

### 其他设置

- 各向异性过滤：当前禁用（`anisotropyEnable = VK_FALSE`）
- 比较操作：禁用（`compareEnable = VK_FALSE`）
- 非归一化坐标：禁用
- 边界颜色：透明黑色（用于 Decal 平铺模式）

## 依赖关系

- `Sampler` — 基类
- `VulkanSharedContext` — Vulkan 设备
- `VulkanYcbcrConversion` — YCbCr 转换
- `VulkanCaps` — 能力查询
- `SamplerDesc` — 采样器描述

## 设计模式与设计决策

### 描述保留

保留 `SamplerDesc` 成员以便在创建描述符时快速访问数值采样器表示，避免从 VkSampler 反向推导参数。

### Mipmap 禁用策略

使用 `minLod = maxLod = 0` 而非不存在的 "NONE" 模式来禁用 mipmap。选择 `LINEAR` 而非 `NEAREST` 作为禁用时的模式，因为 Chrome 像素测试依赖于此行为。

## 性能考量

- **轻量封装**: 仅包含一个 VkSampler 句柄和描述数据
- **不可变采样器支持**: `constVkSamplerPtr()` 用于描述符集布局中的不可变采样器优化
- **资源缓存**: 通过基类 Sampler 参与全局资源缓存

## 相关文件

- `src/gpu/graphite/Sampler.h` — 基类
- `src/gpu/graphite/vk/VulkanYcbcrConversion.h` — YCbCr 转换
- `src/gpu/graphite/vk/VulkanResourceProvider.cpp` — 创建采样器
- `src/gpu/graphite/vk/VulkanCaps.h` — Vulkan 能力
