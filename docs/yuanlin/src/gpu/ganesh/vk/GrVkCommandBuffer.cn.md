# GrVkCommandBuffer - Vulkan 命令缓冲区

> 源文件: `src/gpu/ganesh/vk/GrVkCommandBuffer.h`, `src/gpu/ganesh/vk/GrVkCommandBuffer.cpp`

## 概述

`GrVkCommandBuffer` 是 Ganesh Vulkan 后端中命令缓冲区的封装层，提供了对 Vulkan 命令缓冲区的类型安全的 C++ 接口。它分为基类 `GrVkCommandBuffer` 和两个具体子类 `GrVkPrimaryCommandBuffer`（主命令缓冲区）和 `GrVkSecondaryCommandBuffer`（次级命令缓冲区），分别对应 Vulkan 的主次级命令缓冲区概念。

## 架构位置

```
GrVkGpu
    |
GrVkCommandPool -> GrVkPrimaryCommandBuffer
                        |
                  GrVkSecondaryCommandBuffer (嵌套执行)
                        |
                  VkCommandBuffer (Vulkan API)
```

命令缓冲区是 Vulkan 渲染管线中记录和提交 GPU 命令的核心组件。

## 主要类与结构体

### `GrVkCommandBuffer` (基类)

| 成员 | 类型 | 说明 |
|------|------|------|
| `fCmdBuffer` | `VkCommandBuffer` | Vulkan 命令缓冲区句柄 |
| `fIsActive` | `bool` | 是否处于 begin/end 之间 |
| `fHasWork` | `bool` | 是否记录了任何命令 |
| `fActiveRenderPass` | `const GrVkRenderPass*` | 当前活跃的渲染通道 |
| `fTrackedResources` | `TrackedResourceArray` | 引用的受管资源列表 |
| `fTrackedRecycledResources` | `TrackedResourceArray` | 可回收资源列表 |
| `fTrackedGpuBuffers` | `STArray` | 引用的 GPU 缓冲区 |
| `fTrackedGpuSurfaces` | `STArray` | 引用的 GPU 表面 |
| 缓存状态 | 各类 | 视口、裁剪、混合常量等动态状态缓存 |
| 屏障批次 | `STArray` | 缓冲区和图像内存屏障的批处理缓冲区 |

### `GrVkPrimaryCommandBuffer`

继承自 `GrVkCommandBuffer`，负责完整的命令提交生命周期。

| 额外成员 | 类型 | 说明 |
|----------|------|------|
| `fSecondaryCommandBuffers` | `TArray<unique_ptr<Secondary>>` | 已执行的次级缓冲区 |
| `fSubmitFence` | `VkFence` | 提交完成栅栏 |
| `fFinishedProcs` | `TArray<sk_sp<RefCntedCallback>>` | 完成回调 |

### `GrVkSecondaryCommandBuffer`

继承自 `GrVkCommandBuffer`，用于渲染通道内的命令记录或包装外部次级命令缓冲区。

## 公共 API 函数

### 基类命令（渲染通道内外均可用）

| 方法 | 说明 |
|------|------|
| `pipelineBarrier()` | 管线屏障（批量收集后提交） |
| `bindInputBuffer()` / `bindIndexBuffer()` | 绑定输入/索引缓冲区 |
| `bindPipeline()` | 绑定图形管线 |
| `bindDescriptorSets()` | 绑定描述符集 |
| `pushConstants()` | 推送常量 |
| `setViewport()` / `setScissor()` / `setBlendConstants()` | 设置动态状态 |

### 渲染通道内命令

| 方法 | 说明 |
|------|------|
| `draw()` / `drawIndexed()` | 直接绘制 |
| `drawIndirect()` / `drawIndexedIndirect()` | 间接绘制 |
| `clearAttachments()` | 清除附件 |

### 主命令缓冲区特有

| 方法 | 说明 |
|------|------|
| `begin()` / `end()` | 开始/结束命令记录 |
| `beginRenderPass()` / `endRenderPass()` | 渲染通道管理 |
| `executeCommands()` | 执行次级命令缓冲区 |
| `copyImage()` / `blitImage()` / `resolveImage()` | 图像操作 |
| `copyBufferToImage()` / `copyImageToBuffer()` | 缓冲区-图像传输 |
| `fillBuffer()` / `copyBuffer()` / `updateBuffer()` | 缓冲区操作 |
| `submitToQueue()` | 提交到 GPU 队列 |
| `forceSync()` | 强制同步（等待栅栏） |
| `finished()` | 检查是否完成 |

### 资源管理

```cpp
void addResource(sk_sp<const GrManagedResource>);
void addRecycledResource(gr_rp<const GrRecycledResource>);
void addGrBuffer(sk_sp<const GrBuffer>);
void addGrSurface(sk_sp<const GrSurface>);
void releaseResources();
```

命令缓冲区持有所有引用资源的智能指针，确保在 GPU 执行期间资源不被释放。执行完成后统一释放。

## 内部实现细节

### 屏障批处理

管线屏障不立即提交，而是缓存在 `fBufferBarriers` 和 `fImageBarriers` 中。通过 `submitPipelineBarriers` 统一提交，减少 Vulkan 调用次数并允许驱动更好地优化。

### 状态缓存

动态状态（视口、裁剪、混合常量）被缓存，避免重复设置相同状态。

### 资源追踪

使用 `STArray<32, ...>` 预分配数组减少堆分配。区分普通资源和可回收资源，后者在释放时通知池可以复用。

### 栅栏同步

`submitToQueue` 关联 `VkFence`，`finished()` 检查栅栏状态，`forceSync()` 阻塞等待栅栏完成。

## 依赖关系

- **上游依赖**: `GrVkGpu`（创建和提交）、`GrVkCommandPool`（分配）。
- **核心依赖**: Vulkan API、`GrManagedResource`、`GrVkRenderPass`、`GrVkPipeline`。
- **被依赖**: `GrVkOpsRenderPass`（通过次级命令缓冲区记录绘制命令）。

## 设计模式与设计决策

1. **主/次级分离**: 主缓冲区管理整体生命周期和非渲染通道命令，次级缓冲区专注于渲染通道内的绘制。
2. **资源生命周期绑定**: 所有引用资源的生命周期与命令缓冲区绑定，保证执行期间的有效性。
3. **屏障延迟提交**: 收集多个屏障后批量提交，减少 Vulkan 调用开销。
4. **包装外部缓冲区**: 支持包装外部提供的 `VkCommandBuffer`（如 Android Vulkan 集成）。

## 性能考量

- `STArray` 初始大小 32 避免大多数场景下的堆分配。
- 屏障批处理减少了 `vkCmdPipelineBarrier` 的调用次数。
- 动态状态缓存避免冗余的 Vulkan 状态设置调用。
- 次级命令缓冲区可被回收复用，减少 Vulkan 命令缓冲区分配开销。

## 相关文件

- `src/gpu/ganesh/vk/GrVkCommandPool.h` - 命令池管理
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU 实现
- `src/gpu/ganesh/vk/GrVkRenderPass.h` - 渲染通道
- `src/gpu/ganesh/vk/GrVkPipeline.h` - 图形管线
- `src/gpu/ganesh/GrManagedResource.h` - 受管资源基类
