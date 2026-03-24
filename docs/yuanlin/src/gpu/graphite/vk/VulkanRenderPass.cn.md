# VulkanRenderPass

> 源文件: `src/gpu/graphite/vk/VulkanRenderPass.h`, `src/gpu/graphite/vk/VulkanRenderPass.cpp`

## 概述

`VulkanRenderPass` 是 Skia Graphite Vulkan 后端中对 `VkRenderPass` 的封装，继承自 `Resource` 基类以支持资源缓存和生命周期管理。渲染通道定义了颜色、深度/模板和解析附件的格式、采样数和加载/存储操作，是 Vulkan 帧缓冲区和图形管线创建的基础。

该类还提供了紧凑的键编码方案，将渲染通道的全部描述信息压缩到单个 `uint32_t` 中，用于快速的缓存查找和管线兼容性检查。

## 架构位置

- **上层**: 由 `VulkanResourceProvider::findOrCreateRenderPass()` 创建和缓存
- **基类**: 继承自 `Resource`，参与资源缓存管理
- **使用者**: `VulkanCommandBuffer`（开始渲染通道）、`VulkanFramebuffer`（创建帧缓冲区）、`VulkanGraphicsPipeline`（创建管线）

## 主要类与结构体

### `VulkanRenderPass` 类

**公共成员**:
- `fRenderPass` — 底层 `VkRenderPass` 句柄
- `fGranularity` — 渲染区域粒度

## 公共 API 函数

- **`renderPass()`** — 返回原始 VkRenderPass 句柄
- **`granularity()`** — 返回渲染区域粒度
- **`GetRenderPassKey(RenderPassDesc, bool compatibleForPipelineKey)`** — 静态方法，将渲染通道描述编码为 uint32 键
- **`ExtractRenderPassDesc(uint32_t key, Swizzle, DstReadStrategy, RenderPassDesc*)`** — 静态方法，从键反向解码为渲染通道描述
- **`Make(VulkanSharedContext*, RenderPassDesc)`** — 静态工厂方法

## 内部实现细节

### 键编码方案

渲染通道键为 32 位，布局如下：

```
LSB                                                         MSB
+----+-----+---+---+---+------------+------------+--------+---+
| CF | DSF | M | L | S | L(resolve) | S(resolve) | MSRTSS | 0 |
+----+-----+---+---+---+------------+------------+--------+---+
  8     8    3   2   1       2            1           1     6
```

- **CF** (8 bits): 颜色格式
- **DSF** (8 bits): 深度/模板格式
- **M** (3 bits): 采样数
- **L** (2 bits): 颜色加载操作
- **S** (1 bit): 颜色存储操作
- **L(resolve)** (2 bits): 解析附件加载操作
- **S(resolve)** (1 bit): 解析附件存储操作
- **MSRTSS** (1 bit): 是否多采样渲染到单采样

### 兼容性与完整键

- **兼容键**（`compatibleForPipelineKey = true`）: 排除加载/存储操作，仅保留格式和采样信息，用于管线创建
- **完整键**（`compatibleForPipelineKey = false`）: 包含所有信息，用于开始渲染通道

### VkRenderPass 创建

`Make()` 方法创建 Vulkan 渲染通道，处理以下场景：
- 单子通道（无 MSAA 从解析加载）
- 双子通道（首个子通道从解析附件加载 MSAA 数据）
- 颜色附件使用 `VK_IMAGE_LAYOUT_GENERAL` 以支持作为输入附件读取
- 子通道自依赖用于支持运行时 dst 读取混合

### 附件描述

`setup_vk_attachment_description()` 模板函数将 Graphite 的 `AttachmentDesc` 转换为 Vulkan 的附件描述，利用 `LoadOp` 和 `StoreOp` 与 Vulkan 枚举值的对齐（`static_assert` 验证）。

### 子通道依赖

对于需要 dst 读取的场景，添加颜色附件的子通道自依赖：
- `VK_DEPENDENCY_BY_REGION_BIT` 标志
- 源和目标均为 `COLOR_ATTACHMENT_OUTPUT` 阶段
- 如果不支持 `rasterizationOrderColorAttachmentAccess` 扩展或使用非一致高级混合，则需要此依赖

## 依赖关系

- `Resource` — 基类，提供资源缓存集成
- `VulkanSharedContext` — Vulkan 设备和能力
- `RenderPassDesc` — 渲染通道描述
- `VulkanGraphiteUtils.h` — Vulkan 调用宏

## 设计模式与设计决策

### 紧凑键

将所有渲染通道信息压缩到 32 位键中，使得缓存查找非常高效。这依赖于几个简化假设（深度/模板始终 Clear/Discard、解析附件格式与颜色相同等）。

### 兼容性分层

区分"兼容"和"完整"渲染通道。兼容渲染通道用于管线和帧缓冲区创建（只需格式和采样数匹配），完整渲染通道用于实际的渲染通道开始。

### GENERAL 布局

颜色附件在子通道中使用 `VK_IMAGE_LAYOUT_GENERAL` 而非 `COLOR_ATTACHMENT_OPTIMAL`，以支持作为输入附件读取（dst 读取混合）。大多数 GPU 识别此模式并保持最优内部布局。

## 性能考量

- **缓存友好**: 32 位键使得哈希查找极快
- **资源共享**: 通过 `Shareable::kYes` 允许多个帧缓冲区/管线共享同一个渲染通道
- **布局优化**: 初始/最终布局使用 OPTIMAL 变体，仅子通道引用使用 GENERAL

## 相关文件

- `src/gpu/graphite/RenderPassDesc.h` — 渲染通道描述
- `src/gpu/graphite/vk/VulkanResourceProvider.h` — 资源提供者
- `src/gpu/graphite/vk/VulkanCommandBuffer.h` — 命令缓冲区
- `src/gpu/graphite/vk/VulkanFramebuffer.h` — 帧缓冲区
