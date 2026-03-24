# VulkanMutableTextureStatePriv

> 源文件:
> - `src/gpu/vk/VulkanMutableTextureStatePriv.h`

## 概述

`VulkanMutableTextureStatePriv.h` 定义了用于修改 Vulkan 纹理可变状态的内部私有 API。该头文件暴露了两个函数，允许 Skia 内部代码直接修改 `MutableTextureState` 对象中的 Vulkan 图像布局（`VkImageLayout`）和队列族索引（Queue Family Index）。这些函数不属于公开 API，仅供 Skia 内部使用。

## 架构位置

```
Skia GPU 层
  └── Vulkan 后端
        └── MutableTextureState (公开类)
              └── MutableTextureStates (私有辅助命名空间)
                    ├── SetVkImageLayout()
                    └── SetVkQueueFamilyIndex()
```

## 主要类与结构体

### `skgpu::MutableTextureStates` 命名空间
提供两个静态函数用于修改 `MutableTextureState` 的 Vulkan 特定字段。这些函数是对公开只读接口的内部补充。

## 公共 API 函数

- **`SetVkImageLayout(MutableTextureState* state, VkImageLayout layout)`**：设置纹理的 Vulkan 图像布局。图像布局决定了纹理在 GPU 内存中的排列方式，如 `VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL`、`VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL` 等。
- **`SetVkQueueFamilyIndex(MutableTextureState* state, uint32_t queueFamilyIndex)`**：设置纹理当前所属的 Vulkan 队列族索引。在跨队列族操作（如从图形队列转移到计算队列）时需要更新此值。

## 内部实现细节

这两个函数直接修改 `MutableTextureState` 对象的内部状态，绕过公开 API 的只读限制。这是 Skia 内部在提交命令缓冲区、执行布局转换或队列族所有权转移时必需的操作。

## 依赖关系

- **Vulkan API**: `VkImageLayout` 来自 `SkiaVulkan.h`
- **Skia GPU**: `skgpu::MutableTextureState`

## 设计模式与设计决策

1. **Priv 模式**：遵循 Skia 的 "Priv" 头文件惯例，将内部修改接口与公开只读接口分离，防止外部代码意外修改纹理状态。
2. **命名空间函数**：使用命名空间中的自由函数而非成员函数，保持 `MutableTextureState` 公开接口的简洁性。

## 性能考量

- 直接指针修改，无额外开销。这些函数在渲染循环的关键路径上被高频调用（每次布局转换时）。

## 相关文件

- `include/gpu/MutableTextureState.h` - 公开的可变纹理状态类
- `include/private/gpu/vk/SkiaVulkan.h` - Vulkan 类型定义
