# GraphiteVulkanWindowContext_android

> 源文件: tools/window/android/GraphiteVulkanWindowContext_android.cpp

## 概述

`GraphiteVulkanWindowContext_android` 是 Skia Graphite 渲染引擎在 Android 平台上使用原生 Vulkan API 的窗口上下文实现。该文件提供了一个工厂函数 `MakeGraphiteVulkanForAndroid`，用于创建基于 Vulkan 的 Graphite 窗口上下文。

与 Dawn 封装版本不同，这是直接使用 Vulkan API 的原生实现，通过 Android 的 `vkCreateAndroidSurfaceKHR` 扩展创建窗口 Surface。该实现适用于需要直接控制 Vulkan 行为或最大化性能的场景。

## 架构位置

该文件位于 Skia 工具层的 Android 平台窗口实现中：

```
skia/
  tools/
    window/
      android/                                    # Android 平台特定实现
        GraphiteVulkanWindowContext_android.cpp  # 本文件
        WindowContextFactory_android.h            # Android 窗口工厂
      GraphiteNativeVulkanWindowContext.h         # Graphite 原生 Vulkan 基类
      DisplayParams.h                             # 显示参数配置
    gpu/
      vk/
        VkTestUtils.h                             # Vulkan 测试工具
  src/
    gpu/graphite/                                 # Graphite 渲染引擎核心
```

在 Skia 架构层次：
- **平台层**: 与 Android NDK 的 ANativeWindow 和 Vulkan 扩展交互
- **窗口系统层**: 实现跨平台窗口上下文接口
- **渲染后端层**: 直接使用 Vulkan API，为 Graphite 提供底层支持

## 主要类与结构体

该文件不定义新类，而是使用 `internal::GraphiteVulkanWindowContext` 基类，通过工厂函数和 Lambda 表达式实现平台特定逻辑。

### Lambda 闭包

**createVkSurface**:
```cpp
auto createVkSurface = [window, instProc] (VkInstance instance) -> VkSurfaceKHR
```
- **捕获**: `window` (ANativeWindow 指针), `instProc` (Vulkan 函数指针)
- **功能**: 创建 Android Vulkan Surface
- **返回**: VkSurfaceKHR 句柄，失败返回 VK_NULL_HANDLE

**canPresent**:
```cpp
auto canPresent = [](VkInstance, VkPhysicalDevice, uint32_t) { return true; }
```
- **功能**: 检查物理设备是否支持呈现
- **实现**: Android 上始终返回 true（假定所有队列族都支持呈现）

## 公共 API 函数

### MakeGraphiteVulkanForAndroid

```cpp
std::unique_ptr<WindowContext> MakeGraphiteVulkanForAndroid(
    ANativeWindow* window,
    std::unique_ptr<const DisplayParams> params)
```

**功能**: 创建 Android 平台的 Graphite Vulkan 窗口上下文。

**参数**:
- `window`: Android 原生窗口指针（由 Android 系统提供）
- `params`: 显示参数配置（包含 MSAA、VSync、色彩空间等设置）

**返回值**:
- 成功: 有效的 `WindowContext` 智能指针
- 失败: `nullptr`（Vulkan 库加载失败或上下文无效）

**使用场景**:
- Android NDK 应用中创建 Skia Graphite 渲染上下文
- 需要原生 Vulkan 性能和控制力的高性能图形应用

## 内部实现细节

### Vulkan 库加载

```cpp
PFN_vkGetInstanceProcAddr instProc;
if (!sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs(&instProc)) {
    return nullptr;
}
```

使用 Skia 的 Vulkan 测试工具加载 Vulkan 动态库并获取 `vkGetInstanceProcAddr` 函数指针。这是访问所有其他 Vulkan 函数的入口点。

### Surface 创建流程

1. **获取创建函数**:
   ```cpp
   PFN_vkCreateAndroidSurfaceKHR createAndroidSurfaceKHR =
       (PFN_vkCreateAndroidSurfaceKHR) instProc(instance, "vkCreateAndroidSurfaceKHR");
   ```
   从 Vulkan 实例动态加载 Android Surface 创建扩展函数。

2. **配置 Surface 创建信息**:
   ```cpp
   VkAndroidSurfaceCreateInfoKHR surfaceCreateInfo;
   memset(&surfaceCreateInfo, 0, sizeof(VkAndroidSurfaceCreateInfoKHR));
   surfaceCreateInfo.sType = VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR;
   surfaceCreateInfo.pNext = nullptr;
   surfaceCreateInfo.flags = 0;
   surfaceCreateInfo.window = window;
   ```

3. **创建 Surface**:
   ```cpp
   VkResult res = createAndroidSurfaceKHR(instance, &surfaceCreateInfo,
                                          nullptr, &surface);
   return (VK_SUCCESS == res) ? surface : VK_NULL_HANDLE;
   ```

### 呈现能力检查

`canPresent` Lambda 在 Android 上始终返回 `true`，这是基于 Android 平台的特性：
- Android 的 Vulkan 实现保证所有图形队列族都支持呈现到 ANativeWindow
- 简化了队列族选择逻辑

### 上下文构造

```cpp
std::unique_ptr<WindowContext> ctx(new internal::GraphiteVulkanWindowContext(
    std::move(params), createVkSurface, canPresent, instProc));
```

使用基类 `GraphiteVulkanWindowContext` 的构造函数，传入：
- 显示参数
- Surface 创建闭包
- 呈现能力检查闭包
- Vulkan 函数加载器

### 验证与返回

```cpp
if (!ctx->isValid()) {
    return nullptr;
}
return ctx;
```

检查上下文是否成功初始化，失败则返回空指针。

## 依赖关系

**直接依赖**:
- `tools/window/android/WindowContextFactory_android.h`: 工厂函数声明
- `tools/gpu/vk/VkTestUtils.h`: Vulkan 库加载工具
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/window/GraphiteNativeVulkanWindowContext.h`: Graphite Vulkan 基类
- Android NDK: `ANativeWindow` 和 Vulkan 扩展

**间接依赖**:
- Vulkan SDK: Vulkan API 头文件和类型定义
- `src/gpu/graphite/`: Graphite 渲染引擎核心
- Android Vulkan 驱动: 系统层 Vulkan 实现

**依赖图**:
```
Android App
    ↓
MakeGraphiteVulkanForAndroid
    ↓
LoadVkLibraryAndGetProcAddrFuncs → Vulkan 动态库
    ↓
GraphiteVulkanWindowContext (基类)
    ↓
vkCreateAndroidSurfaceKHR → ANativeWindow
    ↓
Vulkan 驱动 → GPU 硬件
```

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `MakeGraphiteVulkanForAndroid` 封装复杂的创建逻辑
2. **策略模式**: 通过 Lambda 闭包注入平台特定的 Surface 创建和呈现检查策略
3. **依赖注入**: 将 `createVkSurface` 和 `canPresent` 注入基类，实现平台解耦

### 设计决策

**1. Lambda 闭包而非子类**:
- 避免定义专门的 Android 子类
- 减少代码重复
- 平台特定逻辑局部化在工厂函数中

**2. 动态加载 Vulkan**:
- 支持在不支持 Vulkan 的设备上优雅降级
- 避免编译时硬链接 Vulkan 库
- 提高应用兼容性

**3. 简化呈现检查**:
- Android 平台特性决定可以安全返回 true
- 避免不必要的队列族查询开销

**4. 基类重用**:
- `GraphiteVulkanWindowContext` 处理所有复杂的 Vulkan 初始化
- Android 实现仅关注 Surface 创建
- 代码重用率高

**5. 错误处理策略**:
- 失败时返回 nullptr，由调用者处理
- 不抛出异常，符合 Skia 的设计哲学

### 与其他平台的对比

| 平台 | Surface 创建扩展 | 呈现检查逻辑 |
|------|-----------------|-------------|
| Android | `vkCreateAndroidSurfaceKHR` | 始终返回 true |
| Windows | `vkCreateWin32SurfaceKHR` | 检查队列族支持 |
| Linux | `vkCreateXcbSurfaceKHR` | 检查队列族支持 |
| macOS | MoltenVK 封装 | 检查队列族支持 |

## 性能考量

### 优化特性

1. **零拷贝初始化**: 使用 `std::move` 转移 `DisplayParams` 所有权
2. **延迟加载**: Vulkan 库仅在需要时加载
3. **轻量闭包**: Lambda 仅捕获必要的指针，无额外开销
4. **直接 API**: 相比 Dawn 封装，减少中间层开销

### 性能特征

- **初始化时间**: 中等（需加载 Vulkan 库和创建实例）
- **运行时开销**: 最小（直接 Vulkan 调用）
- **内存占用**: 低（仅函数指针和窗口句柄）
- **帧率性能**: 接近理论最大值

### 性能对比

| 实现方式 | 初始化 | 运行时开销 | 灵活性 |
|---------|--------|-----------|--------|
| 原生 Vulkan | 中 | 最低 | 最高 |
| Dawn Vulkan | 高 | 低 | 中等 |
| OpenGL ES | 低 | 中等 | 低 |

### 潜在瓶颈

- 首次 Vulkan 驱动加载可能有明显延迟
- 某些低端 Android 设备 Vulkan 驱动不稳定
- ANativeWindow 的生命周期管理需要应用层正确处理

## 相关文件

### 同目录文件
- `tools/window/android/GraphiteDawnWindowContext_android.cpp`: Dawn 封装版本
- `tools/window/android/VulkanWindowContext_android.cpp`: Ganesh Vulkan 实现
- `tools/window/android/GLWindowContext_android.cpp`: OpenGL ES 实现
- `tools/window/android/RasterWindowContext_android.cpp`: 软件光栅化实现
- `tools/window/android/WindowContextFactory_android.h`: Android 窗口工厂

### 基类与工具
- `tools/window/GraphiteNativeVulkanWindowContext.h`: Graphite Vulkan 基类
- `tools/gpu/vk/VkTestUtils.h`: Vulkan 测试工具
- `tools/window/DisplayParams.h`: 显示参数
- `tools/window/WindowContext.h`: 窗口上下文接口

### 其他平台实现
- `tools/window/win/GraphiteVulkanWindowContext_win.cpp`: Windows 实现
- `tools/window/unix/GraphiteVulkanWindowContext_unix.cpp`: Linux 实现

### Vulkan 相关
- Vulkan SDK 头文件（系统或 NDK 提供）
- `include/third_party/vulkan/`: Skia 包含的 Vulkan 头文件
