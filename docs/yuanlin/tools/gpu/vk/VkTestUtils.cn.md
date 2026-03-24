# VkTestUtils

> 源文件
> - tools/gpu/vk/VkTestUtils.h
> - tools/gpu/vk/VkTestUtils.cpp

## 概述

`VkTestUtils` 是 Skia GPU 工具集中用于初始化和配置 Vulkan 测试环境的核心工具模块。Vulkan 是一个低级图形 API，初始化过程涉及加载动态库、选择物理设备、创建逻辑设备、设置验证层、配置扩展等众多步骤。该模块封装了这些复杂的初始化逻辑，为测试代码提供简洁的 Vulkan 上下文创建接口。

核心功能包括：动态加载 Vulkan 库并获取函数指针、创建配置完整的 `VulkanBackendContext`、支持验证层和调试消息回调、选择合适的物理设备和队列族、配置设备特性和扩展、支持受保护内存和呈现队列。该模块是 Skia Vulkan 测试基础设施的基础，被所有需要 Vulkan 上下文的测试和工具使用。

## 架构位置

`VkTestUtils` 位于 `tools/gpu/vk/` 目录下，是 Vulkan 测试工具层的基础设施组件。在 Skia 架构中：

1. **Vulkan 初始化层**：封装 Vulkan 实例、设备和上下文的创建流程
2. **测试环境配置层**：为测试提供标准化的 Vulkan 环境
3. **平台适配层**：处理不同平台（Windows、macOS、Linux）的库加载差异

依赖关系：
- **上游依赖**：Vulkan SDK（头文件和库）、`VulkanBackendContext`、`VulkanExtensions`
- **下游使用**：`GrContextFactory`、Vulkan 测试用例、`VkTestHelper`
- **集成组件**：验证层、调试工具、内存分配器

该模块是测试代码和 Vulkan API 之间的主要桥梁，隐藏了平台和驱动差异。

## 主要类与结构体

### TestVkFeatures 结构体

封装 Vulkan 设备特性的配置。

**成员变量：**
- `VkPhysicalDeviceFeatures2 deviceFeatures`：Vulkan 1.1+ 的特性结构（可链接扩展特性）
- `skgpu::VulkanPreferredFeatures skiaFeatures`：Skia 偏好的 Vulkan 特性
- `VkPhysicalDeviceProtectedMemoryFeatures protectedMemoryFeatures`：受保护内存特性

**生命周期关联：** 扩展特性通过 `pNext` 链接到 `deviceFeatures`，因此必须共享相同的生命周期。

### CanPresentFn 函数对象

```cpp
using CanPresentFn = std::function<bool(VkInstance, VkPhysicalDevice, uint32_t queueFamilyIndex)>;
```

用户提供的回调函数，判断指定队列族是否支持呈现（用于窗口系统集成）。

**参数：**
- `VkInstance`：Vulkan 实例
- `VkPhysicalDevice`：物理设备
- `queueFamilyIndex`：队列族索引

**返回值：** `true` 表示支持呈现

## 公共 API 函数

### LoadVkLibraryAndGetProcAddrFuncs

```cpp
bool LoadVkLibraryAndGetProcAddrFuncs(PFN_vkGetInstanceProcAddr* instProc);
```

动态加载 Vulkan 库并获取 `vkGetInstanceProcAddr` 函数指针。

**平台特定库名：**
- **Windows**：`vulkan-1.dll`
- **macOS**：`libvk_swiftshader.dylib`（默认使用 SwiftShader 软件渲染器）
- **Linux**：`libvulkan.so` 或 `libvulkan.so.1`（备用）

**返回值：** 成功返回 `true`，失败返回 `false`

**实现细节：**
- 使用静态变量缓存库句柄和函数指针（只加载一次）
- 支持备用库名（Linux 上的 `.so.1` 后缀）
- 使用 Skia 的跨平台动态库加载工具

### CreateVkBackendContext

```cpp
bool CreateVkBackendContext(
    PFN_vkGetInstanceProcAddr getInstProc,
    skgpu::VulkanBackendContext* ctx,
    skgpu::VulkanExtensions* extensions,
    TestVkFeatures* features,
    VkDebugUtilsMessengerEXT* debugMessenger,
    uint32_t* presentQueueIndexPtr = nullptr,
    const CanPresentFn& canPresent = CanPresentFn(),
    bool isProtected = false);
```

创建完整配置的 Vulkan 后端上下文。

**参数：**
- `getInstProc`：`vkGetInstanceProcAddr` 函数指针
- `ctx`：输出的后端上下文结构
- `extensions`：输出的 Vulkan 扩展信息
- `features`：输出的设备特性信息
- `debugMessenger`：输出的调试消息回调句柄（可选）
- `presentQueueIndexPtr`：输出的呈现队列索引（可选）
- `canPresent`：呈现能力查询回调（可选）
- `isProtected`：是否需要受保护内存

**返回值：** 成功返回 `true`

**创建流程：**
1. 创建 Vulkan 实例（启用验证层和扩展）
2. 枚举物理设备并选择合适的 GPU
3. 选择支持图形操作的队列族（如果需要呈现，还要支持呈现）
4. 创建逻辑设备并启用所需特性
5. 创建内存分配器（`VkTestMemoryAllocator`）
6. 构建 `VulkanBackendContext` 结构
7. 设置调试消息回调（如果启用了验证层）

## 内部实现细节

### 平台库加载策略

使用条件编译定义平台特定的库名：

```cpp
#if defined _WIN32
    #define SK_GPU_TOOLS_VK_LIBRARY_NAME vulkan-1.dll
#elif defined SK_BUILD_FOR_MAC
    #define SK_GPU_TOOLS_VK_LIBRARY_NAME libvk_swiftshader.dylib
#else
    #define SK_GPU_TOOLS_VK_LIBRARY_NAME libvulkan.so
    #define SK_GPU_TOOLS_VK_LIBRARY_NAME_BACKUP libvulkan.so.1
#endif
```

macOS 默认使用 SwiftShader（软件渲染器），因为 macOS 本身不直接支持 Vulkan（通过 MoltenVK 运行）。

### 验证层支持

在 `SK_ENABLE_VK_LAYERS` 定义时启用验证层：

**支持的层：**
- `VK_LAYER_KHRONOS_validation`：Khronos 官方验证层（合并了旧的多个独立层）

**版本兼容性检查：**
```cpp
if (version <= remove_patch_version(layers[i].specVersion)) {
    return i;  // 层版本足够新，可以使用
}
```

确保验证层支持使用的 Vulkan API 版本。

### 调试消息回调

```cpp
VKAPI_ATTR VkBool32 VKAPI_CALL DebugUtilsMessenger(...) {
    // 过滤已知的无关紧要消息
    // 根据严重程度分类（错误、警告、信息）
    // 打印消息和调用栈
    // 错误时触发调试断点
}
```

**特性：**
- 过滤白名单中的消息（减少噪音）
- 根据严重程度着色输出
- 错误时打印调用栈（仅 glibc 平台）
- 错误时触发 `SkDEBUGFAIL`（中断调试器）

### 物理设备选择策略

选择第一个支持图形操作和指定特性的物理设备：

**选择标准：**
1. 队列族支持图形操作（`VK_QUEUE_GRAPHICS_BIT`）
2. 如果需要呈现，队列族必须支持呈现（通过 `canPresent` 检查）
3. 设备支持所需的扩展（如 `VK_KHR_swapchain`）
4. 如果需要受保护内存，设备必须支持（`protectedMemory` 特性）

**优先级：** 独立 GPU > 集成 GPU > 软件渲染器（但代码中未明确实现优先级）

### 队列族选择

优先选择同时支持图形和呈现的队列族（避免跨队列同步开销）。如果不存在，选择单独的队列族。

**队列索引：**
- 图形队列索引存储在 `ctx->fQueueIndex`
- 呈现队列索引（如果不同）存储在 `*presentQueueIndexPtr`

### 扩展管理

支持的实例扩展：
- `VK_EXT_debug_utils`：调试工具
- `VK_KHR_surface`：窗口系统集成
- `VK_KHR_*_surface`：平台特定的表面扩展（Win32、XCB、Wayland、Android 等）

支持的设备扩展：
- `VK_KHR_swapchain`：交换链（呈现）
- `VK_EXT_device_fault`：设备故障诊断

扩展根据平台和编译配置动态选择。

### 内存分配器集成

创建 `VkTestMemoryAllocator` 并设置到 `VulkanBackendContext`：

```cpp
ctx->fMemoryAllocator = VkTestMemoryAllocator::Make(...);
```

这确保所有 GPU 内存分配都通过 VMA 库管理，提供高效的内存管理。

### 受保护内存支持

当 `isProtected = true` 时：
- 启用 `protectedMemory` 设备特性
- 选择支持受保护内存的队列族
- 创建受保护的逻辑设备

受保护内存用于 DRM（数字版权管理）内容，防止未授权的读取。

### 错误处理

使用 Vulkan 结果代码检查每个 API 调用：
```cpp
VkResult result = vkCreateInstance(...);
if (result != VK_SUCCESS) {
    return false;
}
```

失败时清理已创建的资源并返回 `false`。

## 依赖关系

### 核心依赖

- **Vulkan SDK**：Vulkan 头文件（`vulkan/vulkan.h`）和库
- **VulkanBackendContext.h**：Skia 的 Vulkan 上下文结构
- **VulkanExtensions.h**：Vulkan 扩展管理
- **VulkanPreferredFeatures.h**：Skia 偏好的 Vulkan 特性

### 工具依赖

- **VkTestMemoryAllocator.h**：VMA 集成的内存分配器
- **LoadDynamicLibrary.h**：跨平台动态库加载

### 被依赖

- **GrContextFactory**：Ganesh 上下文工厂（创建 GrDirectContext）
- **GraphiteContextFactory**：Graphite 上下文工厂
- **Vulkan 测试用例**：所有 Vulkan 后端测试
- **VkTestHelper**：Vulkan 测试辅助类

### 系统依赖

- **平台库**：Windows 的 `vulkan-1.dll`、Linux 的 `libvulkan.so`
- **验证层**：Vulkan SDK 的验证层库
- **调试工具**：glibc 的 `backtrace` 函数（可选）

## 设计模式与设计决策

### 工厂模式

`CreateVkBackendContext` 作为工厂函数，封装复杂的创建逻辑，返回完全初始化的上下文。

### 延迟加载

Vulkan 库延迟加载（首次调用时），并缓存函数指针，避免重复加载开销。

### 回调模式

通过 `CanPresentFn` 回调将呈现能力查询委托给用户代码，支持不同的窗口系统。

### 平台抽象

使用条件编译和动态库加载抽象平台差异，保持核心逻辑跨平台。

### 可选功能配置

验证层、调试消息、呈现支持、受保护内存都是可选的，通过参数或编译标志控制。

### 错误处理策略

简单的布尔返回值，失败时返回 `false`，成功时填充输出参数。适合测试场景（不需要详细的错误代码）。

### 测试优先设计

代码针对测试场景优化：
- 默认启用验证层（调试模式）
- 详细的错误消息和调用栈
- 严格的错误检查（验证层错误触发断点）

### 资源管理

通过 RAII（在 `VulkanBackendContext` 中）和智能指针（内存分配器）管理资源，避免泄漏。

## 性能考量

### 库加载开销

首次调用 `LoadVkLibraryAndGetProcAddrFuncs` 会加载动态库（数毫秒），但结果被缓存，后续调用立即返回。

### 验证层开销

验证层会显著降低性能（10-100 倍），因为每个 Vulkan 调用都被拦截和验证。仅在调试模式启用。

### 设备选择

代码选择第一个满足条件的设备，而非最佳设备。对于测试足够，但生产代码可能需要更智能的选择策略。

### 队列族选择

优先选择统一队列（图形+呈现），避免跨队列同步开销。但如果硬件不支持，会使用独立队列（可能有性能影响）。

### 调试消息过滤

过滤机制避免被无关紧要的消息淹没，但过滤本身有轻微开销（字符串匹配）。

### 适用场景

该模块设计用于测试环境：
- 初始化开销不是瓶颈（只执行一次）
- 调试和验证优先于性能
- 不适合需要极致启动速度的生产应用

## 相关文件

### 核心依赖

- `include/gpu/vk/VulkanBackendContext.h` - Vulkan 后端上下文结构
- `include/gpu/vk/VulkanExtensions.h` - 扩展管理
- `include/gpu/vk/VulkanPreferredFeatures.h` - 偏好特性

### 工具依赖

- `tools/gpu/vk/VkTestMemoryAllocator.h` - 内存分配器
- `tools/library/LoadDynamicLibrary.h` - 动态库加载

### 后端集成

- `src/gpu/vk/VulkanInterface.h` - Vulkan 函数指针表
- `src/gpu/ganesh/vk/GrVkGpu.h` - Ganesh Vulkan GPU 实现
- `src/gpu/graphite/vk/VulkanGraphiteUtils.h` - Graphite Vulkan 工具

### 使用场景

- `tools/gpu/GrContextFactory.cpp` - 上下文工厂
- `tools/gpu/vk/VkTestHelper.cpp` - Vulkan 测试辅助
- `tests/` - Vulkan 单元测试
- `gm/` - Vulkan GM 测试

### 相关工具类

- `tools/gpu/vk/VkYcbcrSamplerHelper.h` - YCbCr 采样器
- `tools/gpu/vk/VkTestHelper.h` - Vulkan 测试辅助类
