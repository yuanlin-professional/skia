# VulkanImageView

> 源文件: `src/gpu/graphite/vk/VulkanImageView.h`, `src/gpu/graphite/vk/VulkanImageView.cpp`

## 概述

`VulkanImageView` 是 Skia Graphite Vulkan 后端中对 `VkImageView` 的封装。它不继承自 `Resource` 基类，而是作为 `VulkanTexture` 的子对象存在——其生命周期由所属的 `VulkanTexture` 管理。VulkanTexture 在调用 `freeGpuData()` 时负责销毁其包含的 ImageView 子对象。

## 架构位置

- **上层**: 由 `VulkanTexture` 创建和持有
- **作用**: 提供 Vulkan 图像的视图抽象，用于着色器采样或帧缓冲区附件
- **不直接参与资源缓存**: 生命周期由父 VulkanTexture 管理

## 主要类与结构体

### `VulkanImageView` 类

**Usage 枚举**:
- `kShaderInput` — 用作着色器采样输入
- `kAttachment` — 用作渲染目标附件（颜色、深度、模板）

**私有成员**:
- `fSharedContext` — Vulkan 共享上下文（用于销毁时调用 Vulkan API）
- `fImageView` — 底层 `VkImageView` 句柄
- `fUsage` — 使用类型
- `fYcbcrConversion` — 可选的 YCbCr 颜色空间转换

## 公共 API 函数

- **`Make(VulkanSharedContext*, VkImage, VkFormat, Usage, uint32_t miplevels, sk_sp<VulkanYcbcrConversion>)`** — 静态工厂方法，创建 VkImageView
- **`~VulkanImageView()`** — 销毁底层 VkImageView
- **`imageView()`** — 返回原始 VkImageView 句柄
- **`usage()`** — 返回使用类型

## 内部实现细节

### 创建逻辑

`Make()` 工厂方法根据用途和格式设置 `VkImageViewCreateInfo`：

**Aspect Flags 确定**:
- `kAttachment` 用途根据格式选择：
  - `S8_UINT` → `STENCIL_BIT`
  - `D16_UNORM`, `D32_SFLOAT` → `DEPTH_BIT`
  - `D24_UNORM_S8_UINT`, `D32_SFLOAT_S8_UINT` → `DEPTH_BIT | STENCIL_BIT`
  - 其他 → `COLOR_BIT`
- `kShaderInput` 用途始终使用 `COLOR_BIT`
- 附件用途强制 `miplevels = 1`（附件只能暴露顶层 MIP）

**YCbCr 转换**:
- 如果提供了 `VulkanYcbcrConversion`，通过 `pNext` 链接 `VkSamplerYcbcrConversionInfo`

### 销毁

析构函数直接调用 `vkDestroyImageView`，因为 VulkanImageView 不通过资源缓存管理。

## 依赖关系

- `VulkanSharedContext` — 提供 Vulkan 设备和接口
- `VulkanYcbcrConversion` — 可选的 YCbCr 转换对象
- `VulkanGraphiteUtils.h` — `VULKAN_CALL` 宏

## 设计模式与设计决策

### 非 Resource 设计

与大多数 GPU 对象不同，VulkanImageView 不继承 Resource。这是因为它的生命周期完全由父 VulkanTexture 决定，没有独立的引用计数或缓存需求。这简化了内存管理并避免了循环引用。

### 工厂模式

使用静态 `Make()` 方法而非公开构造函数，确保创建失败时返回 nullptr。

## 性能考量

- **轻量封装**: 仅包含一个 VkImageView 句柄和少量元数据
- **延迟创建**: 按需为每个纹理的不同用途创建视图

## 相关文件

- `src/gpu/graphite/vk/VulkanTexture.h` — 父容器
- `src/gpu/graphite/vk/VulkanSharedContext.h` — Vulkan 共享上下文
- `src/gpu/graphite/vk/VulkanYcbcrConversion.h` — YCbCr 转换
