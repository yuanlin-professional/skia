# VulkanWindowContext

> 源文件: `tools/window/VulkanWindowContext.h`, `tools/window/VulkanWindowContext.cpp`

## 概述

VulkanWindowContext 是 Skia 窗口系统中基于 Ganesh 后端的 Vulkan 窗口渲染上下文实现。它管理 Vulkan 设备、交换链和 GrDirectContext，为窗口应用提供基于 Vulkan 的 Ganesh GPU 加速渲染能力。与 GraphiteVulkanWindowContext 不同，此类使用传统的 Ganesh 渲染管线而非 Graphite。

该类封装了完整的 Vulkan 窗口表面生命周期，包括实例初始化、WSI 函数加载、交换链管理、GrDirectContext 创建，以及通过 GrBackendTexture/GrBackendRenderTarget 将交换链图像包装为 SkSurface 的过程。

## 架构位置

```
WindowContext (基类)
  +-- VulkanWindowContext          (Ganesh + Vulkan) <-- 本文件
  +-- GraphiteVulkanWindowContext  (Graphite + Vulkan)
  +-- MetalWindowContext           (Ganesh + Metal)
  +-- GLWindowContext              (Ganesh + OpenGL)
  ...
```

VulkanWindowContext 是 Ganesh 渲染路径中 Vulkan 后端的窗口上下文实现，平台特定子类通过回调函数提供 VkSurface 创建逻辑。

## 主要类与结构体

### `VulkanWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `WindowContext`
- **用途**: 基于 Ganesh/Vulkan 的窗口渲染上下文

### `SwapchainImage`（内部结构体）
与 GraphiteVulkanWindowContext 中的结构体基本相同，包含 VkImage、图像布局、渲染完成信号量和 SkSurface。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `VulkanWindowContext(params, createVkSurface, canPresent, instProc)` | 构造函数 |
| `~VulkanWindowContext()` | 析构函数 |
| `getBackbufferSurface()` | 获取后缓冲 SkSurface，通过信号量等待图像可用 |
| `isValid()` | 检查设备有效性 |
| `resize(w, h)` | 通过重建交换链调整大小 |
| `setDisplayParams(params)` | 更新显示参数并重新初始化 |

## 内部实现细节

### 与 GraphiteVulkanWindowContext 的关键差异

1. **上下文创建**: 使用 `GrDirectContexts::MakeVulkan` 创建 Ganesh GrDirectContext，而非 Graphite Context
2. **内存分配器**: 通过 `VulkanMemoryAllocators::Make` 配置内存分配器
3. **Surface 包装**: 根据图像的采样能力选择不同的包装方式：
   - 可采样时：使用 `SkSurfaces::WrapBackendTexture` 包装为 GrBackendTexture
   - 不可采样时：使用 `SkSurfaces::WrapBackendRenderTarget` 包装为 GrBackendRenderTarget
4. **颜色类型映射**: 显式将 VkFormat 映射为 SkColorType（RGBA_8888 / BGRA_8888）
5. **GPU 提交**: 使用 Ganesh 的 `dContext->flush()` + `dContext->submit()` 而非 Graphite Recording
6. **信号量处理**: 在 `getBackbufferSurface` 中通过 `surface->wait()` 等待获取信号量

### 交换链图像填充（populateSwapchainImages）
- 查询交换链图像并创建 GrVkImageInfo
- 根据 usageFlags 中是否包含 `VK_IMAGE_USAGE_SAMPLED_BIT` 选择 BackendTexture 或 BackendRenderTarget
- MSAA > 1 时要求图像可采样

### 销毁流程
- 等待呈现队列和设备空闲
- 销毁交换链和表面
- 调用 `fContext->abandonContext()` 确保 Ganesh 上下文安全释放
- 按 Device -> DebugMessenger -> Instance 顺序销毁 Vulkan 对象

## 依赖关系

- **Ganesh 后端**: `GrDirectContext`, `GrBackendSurface`, `GrVkBackendSemaphore`, `GrVkBackendSurface`, `GrVkTypes`
- **Vulkan 通用**: `VulkanInterface`, `VulkanExtensions`, `VulkanMutableTextureState`, `VulkanMemoryAllocatorPriv`
- **Skia 核心**: `SkSurface`, `SkAutoMalloc`
- **工具**: `WindowContext`, `VkTestUtils`

## 设计模式与设计决策

1. **平台回调抽象**: 与 GraphiteVulkanWindowContext 相同的 `CreateVkSurfaceFn` / `CanPresentFn` 回调模式
2. **双路 Surface 创建**: 根据图像使用标志选择 BackendTexture 或 BackendRenderTarget 路径，确保兼容不同硬件能力
3. **Ganesh Flush 语义**: 使用 `GrFlushInfo` 配置信号量，通过 `MutableTextureState` 管理图像布局转换
4. **MSAA 支持差异**: 不可采样图像不支持 MSAA（直接返回 false），这是 Ganesh 后端的限制

## 性能考量

- 交换链创建策略与 Graphite 版本一致（Mailbox > FIFO，可选 Immediate）
- 使用 `GR_VK_CALL` 宏统一 Vulkan 调用，减少冗余的返回值检查代码
- 通过 `VulkanMemoryAllocators::Make` 使用优化的 Vulkan 内存分配器（非线程安全模式，因为窗口上下文是单线程使用的）

## 相关文件

- `tools/window/GraphiteNativeVulkanWindowContext.h/.cpp` - Graphite 版本对照
- `tools/window/WindowContext.h` - 基类定义
- `include/gpu/ganesh/vk/GrVkDirectContext.h` - Ganesh Vulkan 上下文创建
- `include/gpu/ganesh/GrBackendSurface.h` - 后端表面类型
- `src/gpu/vk/VulkanInterface.h` - Vulkan 接口封装
