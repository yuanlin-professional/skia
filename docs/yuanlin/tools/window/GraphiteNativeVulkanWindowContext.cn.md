# GraphiteNativeVulkanWindowContext

> 源文件: `tools/window/GraphiteNativeVulkanWindowContext.h`, `tools/window/GraphiteNativeVulkanWindowContext.cpp`

## 概述

GraphiteVulkanWindowContext 是 Skia 窗口系统工具链中用于在 Graphite 后端通过原生 Vulkan API 进行窗口渲染的上下文实现。它负责管理 Vulkan 设备、交换链（swapchain）、信号量同步以及 Graphite 图形上下文，为跨平台窗口应用提供基于 Vulkan 的 GPU 加速渲染能力。

该类封装了完整的 Vulkan 窗口表面生命周期管理，包括：Vulkan 实例与设备初始化、WSI（Window System Integration）扩展函数加载、交换链创建与重建、后缓冲图像获取与呈现、以及 GPU 工作提交与信号量同步。

## 架构位置

GraphiteVulkanWindowContext 位于 Skia 工具层（tools/window），属于窗口上下文（WindowContext）层次结构的具体实现。

```
WindowContext (基类)
  +-- GraphiteVulkanWindowContext  (Graphite + Vulkan)
  +-- VulkanWindowContext          (Ganesh + Vulkan)
  +-- GraphiteMetalWindowContext   (Graphite + Metal)
  +-- GraphiteDawnWindowContext    (Graphite + Dawn)
  ...
```

平台特定的子类（如 Linux/X11/Wayland 版本）通过提供 `CreateVkSurfaceFn` 和 `CanPresentFn` 回调来创建特定平台的 VkSurface。

## 主要类与结构体

### `GraphiteVulkanWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `WindowContext`
- **作用**: 基于 Vulkan 的 Graphite 窗口渲染上下文

### `SwapchainImage`（内部结构体）
- `fVkImage`: 原生 VkImage 句柄
- `fImageLayout`: 非颜色附件使用时的图像布局
- `fRenderCompletionSemaphore`: 渲染完成信号量
- `fSurface`: 客户端渲染的 SkSurface

### 类型别名
- `CreateVkSurfaceFn`: 平台特定的 VkSurfaceKHR 创建函数
- `CanPresentFn`: 平台特定的呈现能力检测函数

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GraphiteVulkanWindowContext(params, createVkSurface, canPresent, instProc)` | 构造函数，接受显示参数、平台回调和 Vulkan 入口点 |
| `~GraphiteVulkanWindowContext()` | 析构函数，销毁所有 Vulkan 资源 |
| `getBackbufferSurface()` | 获取下一个可用的后缓冲 SkSurface |
| `isValid()` | 检查 Vulkan 设备是否有效 |
| `resize(w, h)` | 通过重建交换链处理窗口大小调整 |
| `setDisplayParams(params)` | 更新显示参数，销毁并重新初始化上下文 |

## 内部实现细节

### 初始化流程（initializeContext）
1. 调用 `CreateVkBackendContext` 创建 Vulkan 后端上下文，获取实例、物理设备和逻辑设备
2. 验证 `VK_KHR_surface` 和 `VK_KHR_swapchain` 扩展可用性
3. 通过 `GET_PROC` / `GET_DEV_PROC` 宏动态加载所有 WSI 函数指针
4. 创建 Graphite Context 和 Recorder（启用 `fStoreContextRefInRecorder` 以支持同步 readPixels）
5. 创建平台 VkSurface，验证呈现支持，构建交换链

### 交换链管理（createSwapchain）
- 查询表面能力、格式和呈现模式
- 选择合适的表面格式（排除 sRGB 格式以兼容 Viewer 的颜色管理需求）
- 优先选择 Mailbox 模式（最低延迟无撕裂），可选 Immediate 模式（禁用 VSync 时）
- 支持图形队列与呈现队列分离时的并发共享模式

### GPU 提交与呈现（submitToGpu / onSwapBuffers）
- `submitToGpu` 使用 Graphite Recording 机制提交 GPU 工作
- 配置等待信号量（图像获取）和信号信号量（渲染完成）
- 设置图像布局转换至 `VK_IMAGE_LAYOUT_PRESENT_SRC_KHR`
- 注册完成回调以释放获取信号量
- `onSwapBuffers` 将呈现请求提交到呈现队列

### 后缓冲获取（getBackbufferSurface）
- 创建新的获取信号量
- 通过 `vkAcquireNextImageKHR` 获取下一个可用图像
- 处理 `VK_ERROR_OUT_OF_DATE_KHR`（自动重建交换链）和 `VK_ERROR_SURFACE_LOST_KHR`

## 依赖关系

- **Skia 核心**: `SkSurface`, `SkTypes`, `SkAutoMalloc`
- **Graphite 后端**: `Context`, `Recorder`, `Recording`, `BackendTexture`, `BackendSemaphore`, `TextureInfo`
- **Graphite Vulkan**: `VulkanGraphiteContext`, `VulkanGraphiteTypes`, `VulkanGraphiteUtils`
- **Vulkan 通用**: `VulkanInterface`, `VulkanExtensions`, `VulkanMutableTextureState`, `VulkanAMDMemoryAllocator`
- **工具**: `WindowContext`, `VkTestUtils`, `GraphiteToolUtils`

## 设计模式与设计决策

1. **平台抽象**: 通过 `CreateVkSurfaceFn` 和 `CanPresentFn` 回调将平台特定逻辑与 Vulkan 上下文管理分离，遵循策略模式。

2. **动态函数加载**: 使用 `GET_PROC` / `GET_DEV_PROC` 宏从 Vulkan 后端上下文动态解析函数指针，避免链接时依赖。

3. **信号量生命周期管理**: 获取信号量通过完成回调（`finishedProc`）释放，确保 GPU 完成操作后才销毁；渲染完成信号量随交换链图像生命周期管理。

4. **条件编译**: 整个实现包裹在 `#ifdef SK_VULKAN` 中，`SK_ENABLE_VK_LAYERS` 控制调试层清理。

5. **sRGB 格式排除**: 明确跳过硬件 sRGB 格式，因为 Viewer 需要灵活设置目标色彩空间。

## 性能考量

- **呈现模式选择**: 默认 FIFO（保证无撕裂），优先 Mailbox（最低延迟无撕裂），可选 Immediate（禁用 VSync 时最低延迟但可能撕裂）
- **图像数量**: 请求 `minImageCount + 2` 个交换链图像，减少 CPU 等待 GPU 的阻塞
- **异步提交**: 使用 `SyncToCpu::kNo` 提交 Graphite 工作，避免不必要的 CPU-GPU 同步
- **旧交换链复用**: 创建新交换链时传入旧交换链句柄，允许驱动程序优化资源复用
- **队列分离支持**: 当图形队列和呈现队列不同时使用并发共享模式，避免显式所有权转移开销

## 相关文件

- `tools/window/WindowContext.h` - 窗口上下文基类
- `tools/window/VulkanWindowContext.h/.cpp` - Ganesh 版本的 Vulkan 窗口上下文
- `tools/gpu/vk/VkTestUtils.h` - Vulkan 测试工具函数
- `include/gpu/graphite/vk/VulkanGraphiteContext.h` - Graphite Vulkan 上下文工厂
- `src/gpu/vk/VulkanInterface.h` - Vulkan 接口封装
