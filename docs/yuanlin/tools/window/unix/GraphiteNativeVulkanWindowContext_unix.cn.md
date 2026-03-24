# GraphiteNativeVulkanWindowContext_unix

> 源文件
> - tools/window/unix/GraphiteNativeVulkanWindowContext_unix.h
> - tools/window/unix/GraphiteNativeVulkanWindowContext_unix.cpp

## 概述

`GraphiteNativeVulkanWindowContext_unix` 是 Skia 在 Unix/Linux 平台上使用 Graphite 渲染引擎和原生 Vulkan API 的窗口上下文实现。Graphite 是 Skia 的下一代 GPU 渲染引擎，专为现代图形 API 设计，提供更好的多线程支持和更低的 CPU 开销。该模块通过 XCB（X C Binding）接口与 X Window System 交互，为 Graphite 提供 Vulkan 渲染表面。

相比 Ganesh + Vulkan 的实现，Graphite + Vulkan 组合代表了 Skia 的未来方向，提供更现代化的渲染架构和更好的性能特性。该实现主要用于测试 Graphite 在 Linux 平台上的功能和性能。

## 架构位置

该模块位于 Skia 工具层的 Unix 平台窗口实现中：

```
skia/
├── tools/
│   └── window/
│       ├── GraphiteNativeVulkanWindowContext.h       # Graphite Vulkan 基类
│       └── unix/
│           ├── GraphiteNativeVulkanWindowContext_unix.h   # 本模块头文件
│           ├── GraphiteNativeVulkanWindowContext_unix.cpp # 本模块实现
│           ├── GaneshVulkanWindowContext_unix.cpp         # Ganesh Vulkan 实现
│           └── XlibWindowInfo.h                      # Xlib 窗口信息
├── include/
│   └── gpu/
│       └── graphite/                                # Graphite 公共接口
│           ├── Context.h
│           └── vk/
│               └── VulkanTypes.h
└── src/
    └── gpu/
        └── graphite/
            └── vk/                                  # Graphite Vulkan 后端
```

该模块的架构层次：
- **应用层**：测试工具、示例程序
- **窗口抽象层**：本模块（平台适配）
- **渲染引擎层**：Graphite（新架构）
- **图形 API 层**：Vulkan（原生）

## 主要类与结构体

### XlibWindowInfo

定义在 `XlibWindowInfo.h` 中：
- `Display* fDisplay`：X11 显示连接
- `Window fWindow`：X Window 窗口句柄
- `int fWidth`、`int fHeight`：窗口尺寸

### DisplayParams

显示参数配置：
- 颜色空间
- MSAA 设置
- 其他渲染选项

## 公共 API 函数

### MakeGraphiteNativeVulkanForXlib

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGraphiteNativeVulkanForXlib(
    const XlibWindowInfo& info,
    std::unique_ptr<const DisplayParams> displayParams);
}
```

**功能：** 创建 Unix/Linux 平台的 Graphite 原生 Vulkan 窗口上下文。

**参数：**
- `info`：包含 X Window 信息的结构体
- `displayParams`：显示参数配置

**返回值：** 成功返回 `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景：**
- Graphite 测试和开发
- 高性能图形应用
- Linux 平台的现代化渲染路径

## 内部实现细节

### Vulkan 库加载

```cpp
PFN_vkGetInstanceProcAddr instProc;
if (!sk_gpu_test::LoadVkLibraryAndGetProcAddrFuncs(&instProc)) {
    SkDebugf("Could not load vulkan library\n");
    return nullptr;
}
```

动态加载 Vulkan 共享库（`libvulkan.so`），获取函数加载器。

### XCB 表面创建

`createVkSurface` Lambda 函数创建 Vulkan 表面：

```cpp
auto createVkSurface = [&info, instProc](VkInstance instance) -> VkSurfaceKHR {
    // 1. 加载 XCB 表面创建函数
    static PFN_vkCreateXcbSurfaceKHR createXcbSurfaceKHR = nullptr;
    if (!createXcbSurfaceKHR) {
        createXcbSurfaceKHR =
                (PFN_vkCreateXcbSurfaceKHR)instProc(instance, "vkCreateXcbSurfaceKHR");
    }

    // 2. 配置表面创建信息
    VkXcbSurfaceCreateInfoKHR surfaceCreateInfo;
    memset(&surfaceCreateInfo, 0, sizeof(VkXcbSurfaceCreateInfoKHR));
    surfaceCreateInfo.sType = VK_STRUCTURE_TYPE_XCB_SURFACE_CREATE_INFO_KHR;
    surfaceCreateInfo.pNext = nullptr;
    surfaceCreateInfo.flags = 0;
    surfaceCreateInfo.connection = XGetXCBConnection(info.fDisplay);
    surfaceCreateInfo.window = info.fWindow;

    // 3. 创建表面
    VkSurfaceKHR surface;
    VkResult res = createXcbSurfaceKHR(instance, &surfaceCreateInfo, nullptr, &surface);
    if (res != VK_SUCCESS) {
        return VK_NULL_HANDLE;
    }

    return surface;
};
```

**关键点：**
- 使用 XCB 而非 Xlib 创建表面（更现代化）
- 从 Xlib Display 获取 XCB 连接
- 静态缓存函数指针避免重复加载

### 呈现支持查询

`canPresent` Lambda 函数检查呈现支持：

```cpp
auto canPresent = [&info, instProc](VkInstance instance,
                                    VkPhysicalDevice physDev,
                                    uint32_t queueFamilyIndex) {
    // 加载查询函数
    static PFN_vkGetPhysicalDeviceXcbPresentationSupportKHR
            getPhysicalDeviceXcbPresentationSupportKHR = nullptr;
    if (!getPhysicalDeviceXcbPresentationSupportKHR) {
        getPhysicalDeviceXcbPresentationSupportKHR =
                (PFN_vkGetPhysicalDeviceXcbPresentationSupportKHR)instProc(
                        instance, "vkGetPhysicalDeviceXcbPresentationSupportKHR");
    }

    // 获取 Visual ID
    Display* display = info.fDisplay;
    VisualID visualID = XVisualIDFromVisual(
            DefaultVisual(info.fDisplay, DefaultScreen(info.fDisplay)));

    // 查询呈现支持
    VkBool32 check = getPhysicalDeviceXcbPresentationSupportKHR(
            physDev, queueFamilyIndex, XGetXCBConnection(display), visualID);
    return (check != VK_FALSE);
};
```

确保选择的 GPU 队列族支持向 X Window 呈现。

### 上下文创建

```cpp
std::unique_ptr<WindowContext> ctx(new internal::GraphiteVulkanWindowContext(
        std::move(displayParams), createVkSurface, canPresent, instProc));
if (!ctx->isValid()) {
    return nullptr;
}
return ctx;
```

创建 `GraphiteVulkanWindowContext` 对象，传递平台特定的回调函数。

## 依赖关系

### 外部依赖

**Skia Graphite 组件：**
- `GraphiteNativeVulkanWindowContext`：Graphite Vulkan 基类
- `skgpu::graphite::Context`：Graphite 上下文
- `skgpu::graphite::Recorder`：命令记录器

**Vulkan 组件：**
- `VkInstance`：Vulkan 实例
- `VkPhysicalDevice`：物理设备
- `VkSurfaceKHR`：渲染表面
- `VK_KHR_xcb_surface`：XCB 表面扩展

**系统库：**
- `X11`：X Window System
- `xcb`：X C Binding
- `vulkan`：Vulkan 库
- `VkTestUtils`：Vulkan 测试工具

### 被依赖关系

该模块被以下组件使用：
- Graphite 测试工具
- DM 测试框架（Graphite 路径）
- 性能基准测试

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeGraphiteNativeVulkanForXlib()` 创建实例
   - 隐藏实现细节

2. **策略模式**
   - Lambda 函数传递平台策略
   - `createVkSurface` 和 `canPresent` 作为策略

3. **回调模式**
   - 基类通过回调获取平台功能
   - 解耦平台代码和通用代码

### 设计决策

1. **选择 XCB 接口**
   - 更现代的 X11 绑定
   - 更好的性能和线程安全
   - Vulkan 官方推荐

2. **Lambda 函数作为回调**
   - 捕获上下文信息
   - 代码简洁
   - 避免额外类定义

3. **静态函数指针缓存**
   - 避免重复加载
   - 提高性能

4. **与 Ganesh 实现代码相似**
   - 共享平台层逻辑
   - 仅渲染引擎不同（Graphite vs Ganesh）
   - 降低维护成本

## 性能考量

### 优势

1. **Graphite 架构优势**
   - 更好的多线程支持
   - 更低的 CPU 开销
   - 现代化的资源管理

2. **Vulkan 低开销**
   - 显式资源控制
   - 细粒度同步
   - 更少的驱动干预

3. **XCB 性能**
   - 比 Xlib 更快
   - 异步通信
   - 更小内存占用

### 潜在瓶颈

1. **动态库加载**
   - 首次加载开销
   - 可通过缓存优化

2. **X11 通信**
   - 网络 X11 场景延迟高
   - 本地 Unix socket 性能好

3. **队列选择**
   - 可能不是最优队列
   - 需要查询所有队列族

### 优化建议

- 使用专用传输队列
- 启用 mailbox 呈现模式
- 预分配命令缓冲区
- 利用 Graphite 的批处理优化

## 相关文件

**同平台其他实现：**
- `tools/window/unix/GaneshVulkanWindowContext_unix.cpp`：Ganesh Vulkan 实现
- `tools/window/unix/GaneshGLWindowContext_unix.cpp`：Ganesh OpenGL 实现
- `tools/window/unix/GraphiteDawnXlibWindowContext_unix.cpp`：Graphite Dawn 实现
- `tools/window/unix/RasterWindowContext_unix.cpp`：软件光栅化

**基类和工具：**
- `tools/window/GraphiteNativeVulkanWindowContext.h`：Graphite Vulkan 基类
- `tools/window/WindowContext.h`：窗口上下文抽象
- `tools/window/unix/XlibWindowInfo.h`：Xlib 窗口信息
- `tools/gpu/vk/VkTestUtils.h`：Vulkan 测试工具

**Graphite Vulkan 后端：**
- `src/gpu/graphite/vk/VulkanGraphiteUtils.h`：Vulkan 工具函数
- `include/gpu/graphite/vk/VulkanTypes.h`：Vulkan 类型定义
- `src/gpu/graphite/vk/VulkanContext.h`：Vulkan 上下文

**应用示例：**
- `tools/viewer/Viewer.cpp`：可视化测试工具
- `dm/DM.cpp`：测试框架
- `tools/graphite/vk/GraphiteVulkanTestContext.h`：测试上下文
