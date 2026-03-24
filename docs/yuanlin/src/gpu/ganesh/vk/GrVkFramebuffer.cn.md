# GrVkFramebuffer

> 源文件: `src/gpu/ganesh/vk/GrVkFramebuffer.h`, `src/gpu/ganesh/vk/GrVkFramebuffer.cpp`

## 概述

`GrVkFramebuffer` 是 Skia Ganesh Vulkan 后端中对 `VkFramebuffer` 的封装类。它管理 Vulkan 帧缓冲对象的创建、持有和销毁，同时持有关联的颜色附件、解析附件和模板附件的引用。该类还支持外部二级命令缓冲区的封装场景，用于在客户端管理的渲染流程中进行绘图操作。

## 架构位置

该类位于 Ganesh GPU 渲染引擎的 Vulkan 后端中，继承自 `GrVkManagedResource`，后者提供了 GPU 资源的引用计数和生命周期管理功能。它在渲染管线中处于渲染通道（RenderPass）与渲染目标（RenderTarget）之间，负责将图像附件绑定到渲染通道以便进行实际的渲染操作。

## 主要类与结构体

### `GrVkFramebuffer`
- 继承自 `GrVkManagedResource`，提供 Vulkan GPU 资源的托管生命周期
- 封装 `VkFramebuffer` 句柄
- 持有颜色附件（`fColorAttachment`）、解析附件（`fResolveAttachment`）、模板附件（`fStencilAttachment`）的 `sk_sp<GrVkImage>` 引用
- 持有兼容渲染通道（`fCompatibleRenderPass`）的引用
- 支持外部渲染通道和外部命令缓冲区（用于包装外部二级命令缓冲区的场景）

## 公共 API 函数

### `Make()`
```cpp
static sk_sp<const GrVkFramebuffer> Make(GrVkGpu* gpu, SkISize dimensions,
    sk_sp<const GrVkRenderPass> compatibleRenderPass,
    GrVkImage* colorAttachment, GrVkImage* resolveAttachment,
    GrVkImage* stencilAttachment, GrVkResourceProvider::CompatibleRPHandle);
```
工厂方法，创建标准帧缓冲对象。收集所有附件的 `VkImageView`，填充 `VkFramebufferCreateInfo`，然后调用 `vkCreateFramebuffer` 创建 Vulkan 帧缓冲。至少需要一个渲染通道和一个颜色附件。

### 构造函数（外部二级命令缓冲区）
```cpp
GrVkFramebuffer(const GrVkGpu* gpu, sk_sp<GrVkImage> colorAttachment,
    sk_sp<const GrVkRenderPass> renderPass,
    std::unique_ptr<GrVkSecondaryCommandBuffer>);
```
用于包装外部二级命令缓冲区的构造函数。此时 `VkFramebuffer` 句柄保持为 `VK_NULL_HANDLE`。

### `framebuffer()`
返回底层 `VkFramebuffer` 句柄。仅对非外部帧缓冲有效。

### `isExternal()`
判断是否为外部帧缓冲（即包装了外部二级命令缓冲区）。

### `externalCommandBuffer()` / `returnExternalGrSecondaryCommandBuffer()`
管理外部二级命令缓冲区的取出与归还，用于控制 `GrManagedResources` 的生命周期。

### `compatibleRenderPass()` / `compatibleRenderPassHandle()`
访问兼容的渲染通道及其句柄。

### `colorAttachment()` / `resolveAttachment()` / `stencilAttachment()`
访问各附件的 `GrVkImage` 指针。

## 内部实现细节

- `Make()` 方法最多支持 3 个附件（颜色、解析、模板），按顺序填入 `VkImageView` 数组
- 帧缓冲的 layers 固定为 1
- `freeGPUData()` 方法在非外部模式下调用 `vkDestroyFramebuffer`，然后调用 `releaseResources()` 释放外部命令缓冲区资源
- `freeGPUData()` 使用 `const_cast` 来绕过 `GrManagedResource` 中 `freeGPUData` 为 const 的限制（代码中有 TODO 注明此设计应当改进）

## 依赖关系

- **GrVkManagedResource**: 基类，提供 GPU 资源引用计数管理
- **GrVkImage**: 封装 Vulkan 图像，作为帧缓冲的附件
- **GrVkRenderPass**: 帧缓冲关联的兼容渲染通道
- **GrVkSecondaryCommandBuffer**: 外部二级命令缓冲区
- **GrVkImageView**: 用于获取附件的 `VkImageView`
- **GrVkGpu**: 提供 Vulkan 设备和接口访问
- **GrVkResourceProvider**: 提供 `CompatibleRPHandle` 类型

## 设计模式与设计决策

1. **工厂方法模式**: 使用 `Make()` 静态工厂方法创建对象，在创建失败时返回 `nullptr`
2. **RAII 资源管理**: 通过 `sk_sp` 智能指针自动管理附件和渲染通道的生命周期
3. **双用途设计**: 同一个类既支持标准 Vulkan 帧缓冲，也支持外部二级命令缓冲区的包装，通过 `isExternal()` 区分
4. **资源追踪**: 在 `SK_TRACE_MANAGED_RESOURCES` 模式下提供 `dumpInfo()` 方法用于调试

## 性能考量

- 帧缓冲创建是一次性操作，通常在渲染目标初始化时进行
- 通过持有附件的 `sk_sp` 引用确保附件在帧缓冲存活期间不被销毁，避免悬空引用
- 外部命令缓冲区的生命周期由 `GrVkSecondaryCBDrawContext` 控制，确保 GPU 完成工作后才释放资源

## 使用示例

### 标准帧缓冲创建流程
```cpp
// 通过 Make 工厂方法创建帧缓冲
auto framebuffer = GrVkFramebuffer::Make(
    gpu, dimensions, compatibleRenderPass,
    colorAttachment, resolveAttachment, stencilAttachment,
    compatibleRPHandle);
// Make 内部收集 VkImageView 并调用 vkCreateFramebuffer
```

### 外部帧缓冲（包装二级命令缓冲区）
```cpp
// 用于 GrVkSecondaryCBDrawContext 场景
GrVkFramebuffer externalFB(gpu, colorAttachment, renderPass, std::move(cmdBuffer));
// VkFramebuffer 句柄保持为 VK_NULL_HANDLE
// 通过 isExternal() 判断帧缓冲类型
```

### 资源生命周期管理
外部帧缓冲的命令缓冲区生命周期由 `GrVkSecondaryCBDrawContext` 控制：
1. 客户端通过 `externalCommandBuffer()` 取出命令缓冲区进行录制
2. 录制完成后通过 `returnExternalGrSecondaryCommandBuffer()` 归还
3. 客户端调用 `releaseResources()` 时才释放命令缓冲区持有的 `GrManagedResources`

## 线程安全性

`GrVkFramebuffer` 本身不是线程安全的。它依赖于 Ganesh 的单线程 GPU 访问模型。外部帧缓冲的命令缓冲区生命周期由客户端负责，客户端必须确保 GPU 完成所有工作后才调用 `releaseResources()`。

## 已知限制

- `freeGPUData()` 为 const 方法但需要修改内部状态，通过 `const_cast` 解决，代码中标注了 TODO
- 帧缓冲的 layers 固定为 1，不支持多层渲染（如立方体贴图或纹理数组）
- 外部帧缓冲不持有实际的 `VkFramebuffer` 句柄，不能直接用于标准渲染通道

## 相关文件

- `src/gpu/ganesh/vk/GrVkRenderPass.h` - 渲染通道定义
- `src/gpu/ganesh/vk/GrVkImage.h` - Vulkan 图像封装
- `src/gpu/ganesh/vk/GrVkImageView.h` - 图像视图，提供 `VkImageView` 给帧缓冲
- `src/gpu/ganesh/vk/GrVkRenderTarget.h` - 渲染目标，持有帧缓冲
- `src/gpu/ganesh/vk/GrVkCommandBuffer.h` - 命令缓冲区（含二级命令缓冲区）
- `src/gpu/ganesh/vk/GrVkResourceProvider.h` - 资源提供者，管理帧缓冲的缓存
- `src/gpu/ganesh/vk/GrVkGpu.h` - Vulkan GPU，提供设备和接口
- `src/gpu/ganesh/GrManagedResource.h` - 托管资源基类
- `src/gpu/ganesh/vk/GrVkManagedResource.h` - Vulkan 托管资源基类
- `src/gpu/ganesh/vk/GrVkUtil.h` - Vulkan 工具宏（GR_VK_CALL_RESULT 等）
