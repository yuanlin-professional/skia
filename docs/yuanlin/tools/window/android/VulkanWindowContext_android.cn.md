# VulkanWindowContext_android

> 源文件: tools/window/android/VulkanWindowContext_android.cpp

## 概述

`VulkanWindowContext_android` 是 Skia Ganesh 渲染引擎在 Android 平台上使用原生 Vulkan API 的窗口上下文实现。该文件提供了一个工厂函数 `MakeVulkanForAndroid`，用于创建基于 Vulkan 的 Ganesh 窗口上下文。

与 Graphite Vulkan 实现类似，这也是直接使用 Vulkan API 的原生实现，通过 Android 的 `vkCreateAndroidSurfaceKHR` 扩展创建窗口 Surface，为 Ganesh 渲染引擎提供高性能的硬件加速支持。

## 架构位置

该文件位于 Skia 工具层的 Android 平台窗口实现中：

```
skia/
  tools/
    window/
      android/
        VulkanWindowContext_android.cpp      # 本文件
        GraphiteVulkanWindowContext_android.cpp  # Graphite 对应实现
        WindowContextFactory_android.h       # Android 窗口工厂
      VulkanWindowContext.h                  # Ganesh Vulkan 基类
      DisplayParams.h                        # 显示参数配置
    gpu/
      vk/
        VkTestUtils.h                        # Vulkan 测试工具
  src/
    gpu/ganesh/                              # Ganesh 渲染引擎核心
```

在 Skia 架构层次：
- **平台层**: 与 Android NDK 的 ANativeWindow 和 Vulkan 扩展交互
- **窗口系统层**: 实现跨平台窗口上下文接口
- **渲染后端层**: 连接 Ganesh 渲染引擎和 Vulkan API

## 主要类与结构体

该文件不定义新类，而是使用 `internal::VulkanWindowContext` 基类，通过工厂函数和 Lambda 表达式实现平台特定逻辑。

### Lambda 闭包

**createVkSurface**:
```cpp
auto createVkSurface = [window, instProc] (VkInstance instance) -> VkSurfaceKHR
```
- **捕获**: `window` (ANativeWindow 指针), `instProc` (Vulkan 函数加载器)
- **功能**: 创建 Android Vulkan Surface
- **返回**: VkSurfaceKHR 句柄，失败返回 VK_NULL_HANDLE

**canPresent**:
```cpp
auto canPresent = [](VkInstance, VkPhysicalDevice, uint32_t) { return true; }
```
- **功能**: 检查物理设备队列族是否支持呈现
- **实现**: 在 Android 上始终返回 true

## 公共 API 函数

### MakeVulkanForAndroid

```cpp
std::unique_ptr<WindowContext> MakeVulkanForAndroid(
    ANativeWindow* window,
    std::unique_ptr<const DisplayParams> params)
```

**功能**: 创建 Android 平台的 Ganesh Vulkan 窗口上下文。

**参数**:
- `window`: Android 原生窗口指针
- `params`: 显示参数配置（MSAA、VSync、色彩空间等）

**返回值**:
- 成功: 有效的 `WindowContext` 智能指针
- 失败: `nullptr`

**使用场景**: 在 Android 应用中创建 Skia Ganesh Vulkan 渲染上下文。

## 内部实现细节

### Vulkan 库加载

```cpp
PFN_vkGetInstanceProcAddr instProc;
if (!sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs(&instProc)) {
    return nullptr;
}
```

使用 Skia 的 Vulkan 测试工具加载 Vulkan 动态库，获取函数加载器入口点。

### Surface 创建流程

1. **动态加载创建函数**:
   ```cpp
   PFN_vkCreateAndroidSurfaceKHR createAndroidSurfaceKHR =
       (PFN_vkCreateAndroidSurfaceKHR) instProc(instance, "vkCreateAndroidSurfaceKHR");
   ```

2. **窗口有效性检查**:
   ```cpp
   if (!window) {
       return VK_NULL_HANDLE;
   }
   ```

3. **配置 Surface 创建信息**:
   ```cpp
   VkAndroidSurfaceCreateInfoKHR surfaceCreateInfo;
   memset(&surfaceCreateInfo, 0, sizeof(VkAndroidSurfaceCreateInfoKHR));
   surfaceCreateInfo.sType = VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR;
   surfaceCreateInfo.pNext = nullptr;
   surfaceCreateInfo.flags = 0;
   surfaceCreateInfo.window = window;
   ```

4. **创建 Surface**:
   ```cpp
   VkResult res = createAndroidSurfaceKHR(instance, &surfaceCreateInfo,
                                          nullptr, &surface);
   return (VK_SUCCESS == res) ? surface : VK_NULL_HANDLE;
   ```

### 上下文构造

```cpp
std::unique_ptr<WindowContext> ctx(new internal::VulkanWindowContext(
    std::move(params), createVkSurface, canPresent, instProc));
```

使用 Ganesh 的 `VulkanWindowContext` 基类，传入平台特定的闭包。

### 验证与返回

```cpp
if (!ctx->isValid()) {
    return nullptr;
}
return ctx;
```

## 依赖关系

**直接依赖**:
- `tools/window/android/WindowContextFactory_android.h`: 工厂声明
- `tools/gpu/vk/VkTestUtils.h`: Vulkan 库加载工具
- `tools/window/DisplayParams.h`: 显示参数
- `tools/window/VulkanWindowContext.h`: Ganesh Vulkan 基类
- Android NDK: `ANativeWindow` 和 Vulkan 扩展

**间接依赖**:
- Vulkan SDK: Vulkan API 头文件
- `src/gpu/ganesh/vk/`: Ganesh Vulkan 后端实现
- Android Vulkan 驱动

**依赖图**:
```
Android App
    ↓
MakeVulkanForAndroid
    ↓
LoadVkLibraryAndGetProcAddrFuncs
    ↓
VulkanWindowContext (基类)
    ↓
vkCreateAndroidSurfaceKHR
    ↓
Vulkan 驱动 → GPU
```

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeVulkanForAndroid` 封装创建逻辑
2. **策略模式**: 通过 Lambda 注入平台特定策略
3. **依赖注入**: 将 Surface 创建和呈现检查注入基类

### 设计决策

**1. Lambda 闭包策略**:
- 避免定义 Android 特定子类
- 平台代码局部化在工厂函数
- 与 Graphite Vulkan 实现几乎相同

**2. 动态库加载**:
- 支持在不支持 Vulkan 的设备上降级
- 避免编译时硬链接

**3. 简化呈现检查**:
- Android 平台保证所有图形队列支持呈现
- 无需复杂的队列族检查

**4. 基类重用**:
- Ganesh 的 `VulkanWindowContext` 处理所有 Vulkan 初始化
- Android 实现仅负责 Surface 创建

**5. 零拷贝初始化**:
- 使用 `std::move` 转移 `DisplayParams` 所有权

### 与 Graphite 实现的对比

| 特性 | Ganesh Vulkan | Graphite Vulkan |
|------|--------------|-----------------|
| 基类 | `VulkanWindowContext` | `GraphiteVulkanWindowContext` |
| Surface 创建 | 相同 | 相同 |
| 渲染引擎 | Ganesh (传统) | Graphite (新) |
| Lambda 策略 | 相同 | 相同 |

## 性能考量

### 优化特性

1. **轻量闭包**: Lambda 仅捕获必要指针
2. **延迟加载**: Vulkan 库按需加载
3. **零拷贝**: 使用移动语义
4. **直接 API**: 无中间层开销

### 性能特征

- **初始化时间**: 中等（加载 Vulkan 库和创建实例）
- **运行时开销**: 最小（直接 Vulkan 调用）
- **内存占用**: 低（仅函数指针和窗口句柄）
- **帧率性能**: 接近理论最大值

### Ganesh vs Graphite

| 渲染引擎 | 初始化 | CPU 开销 | GPU 利用率 |
|---------|--------|---------|-----------|
| Ganesh | 快 | 中等 | 良好 |
| Graphite | 中等 | 低 | 优秀 |

Graphite 使用更现代的多线程架构和更高效的资源管理。

### 潜在瓶颈

- 首次 Vulkan 驱动加载有延迟
- 低端 Android 设备 Vulkan 驱动不稳定
- ANativeWindow 生命周期需正确管理

## 相关文件

### 同目录文件
- `tools/window/android/GraphiteVulkanWindowContext_android.cpp`: Graphite Vulkan 实现
- `tools/window/android/GraphiteDawnWindowContext_android.cpp`: Graphite Dawn 实现
- `tools/window/android/GLWindowContext_android.cpp`: OpenGL ES 实现
- `tools/window/android/RasterWindowContext_android.cpp`: 软件光栅化实现
- `tools/window/android/WindowContextFactory_android.h`: Android 窗口工厂

### 基类与工具
- `tools/window/VulkanWindowContext.h`: Ganesh Vulkan 基类
- `tools/gpu/vk/VkTestUtils.h`: Vulkan 测试工具
- `tools/window/DisplayParams.h`: 显示参数
- `tools/window/WindowContext.h`: 窗口上下文接口

### 其他平台 Vulkan 实现
- `tools/window/win/VulkanWindowContext_win.cpp`: Windows 实现
- `tools/window/unix/VulkanWindowContext_unix.cpp`: Linux 实现

### Ganesh Vulkan 核心
- `src/gpu/ganesh/vk/GrVkGpu.h`: Ganesh Vulkan GPU 实现
- `src/gpu/ganesh/vk/GrVkCaps.h`: Vulkan 能力检测

### Vulkan 相关
- Vulkan SDK 头文件（NDK 或系统提供）
- `include/third_party/vulkan/`: Skia 包含的 Vulkan 头文件
