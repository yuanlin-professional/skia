# tools/window/ - Skia 窗口渲染上下文管理

## 概述

`tools/window/` 目录实现了 Skia 工具链中的窗口渲染上下文（WindowContext）系统。该系统为 Skia 应用（如 Viewer）提供了与具体图形 API（OpenGL、Vulkan、Metal、Dawn/WebGPU、Direct3D、ANGLE）和操作系统（Windows、macOS、Linux、Android、iOS）的集成层。其核心职责是管理渲染目标（backbuffer）的创建、呈现（swap）和 GPU 上下文的生命周期。

架构上，`tools/window/` 与 `tools/sk_app/` 形成了清晰的职责分离：`sk_app` 负责应用逻辑和平台事件循环，`window` 负责图形 API 的初始化和帧缓冲管理。两者通过 `WindowContext` 抽象接口解耦。`sk_app::Window` 持有一个 `skwindow::WindowContext` 智能指针，通过它获取绘制表面、提交 GPU 工作和交换缓冲区。

根目录文件定义了核心抽象和通用实现：
- `WindowContext.h/cpp` 定义了所有窗口上下文的基类
- `DisplayParams.h` 定义了渲染参数（颜色类型、色彩空间、MSAA 采样数、VSync 控制等）及其 Builder
- 各种 `*WindowContext.h/cpp` 文件提供了特定图形 API 的通用实现（如 `GLWindowContext` 处理 OpenGL 通用逻辑，`VulkanWindowContext` 管理 Vulkan Swapchain）

平台子目录（`win/`、`mac/`、`unix/`、`android/`、`ios/`）则包含平台特定的 WindowContext 工厂函数和初始化代码。例如，`mac/GaneshGLWindowContext_mac.mm` 实现了在 macOS 上创建 NSOpenGLContext 的具体逻辑。

该系统支持 Skia 的两套 GPU 渲染后端：传统的 Ganesh 后端和新的 Graphite 后端。通过条件编译（`SK_GANESH`、`SK_GRAPHITE`），WindowContext 可以持有 `GrDirectContext`（Ganesh）或 `graphite::Context` + `graphite::Recorder`（Graphite）。

## 架构图

```
+------------------------------------------------------------------+
|                  WindowContext 体系                                |
|                                                                   |
|  +----------------------------+                                   |
|  |    WindowContext (基类)     |  namespace skwindow               |
|  |  + getBackbufferSurface()  |  核心接口：获取绘制表面             |
|  |  + swapBuffers()           |  交换前后缓冲                     |
|  |  + resize(w, h)            |  窗口大小变更                     |
|  |  + submitToGpu(cb)         |  提交 GPU 工作                    |
|  |  + setDisplayParams()      |  更新渲染参数                     |
|  |  + directContext()         |  获取 Ganesh 上下文               |
|  |  + graphiteContext()       |  获取 Graphite 上下文             |
|  |  + graphiteRecorder()      |  获取 Graphite 记录器             |
|  +----------------------------+                                   |
|       ^      ^       ^      ^      ^       ^                      |
|       |      |       |      |      |       |                      |
|  +----+--+---+---+---+--+---+--+---+---+---+---+                 |
|  | GL    | Vulkan | Metal| Dawn   | ANGLE | Raster|               |
|  | Window| Window | Window| Window| Window| Window|               |
|  | Context Context Context Context Context Context|               |
|  +-------+-------+------+-------+-------+--------+               |
|       |              |       |              |                      |
|       v              v       v              v                      |
|  Ganesh           Ganesh  Graphite       Ganesh                   |
|  GrDirectContext  GrDC    Context+       GrDC                     |
|                           Recorder                                |
|                                                                   |
|  +----------------------------+                                   |
|  |   DisplayParams            |  渲染参数配置                      |
|  |  + colorType()             |  kN32_SkColorType 默认             |
|  |  + colorSpace()            |  色彩空间                          |
|  |  + msaaSampleCount()       |  MSAA 采样数                       |
|  |  + disableVsync()          |  VSync 控制                        |
|  |  + surfaceProps()          |  表面属性                          |
|  |  + grContextOptions()      |  Ganesh 上下文选项                  |
|  +----------------------------+                                   |
|                                                                   |
|  +----------------------------+                                   |
|  |   DisplayParamsBuilder     |  Builder 模式构建 DisplayParams     |
|  |  .colorType(...)           |                                   |
|  |  .msaaSampleCount(...)     |                                   |
|  |  .disableVsync(true)       |                                   |
|  |  .detach()                 |  --> unique_ptr<DisplayParams>     |
|  +----------------------------+                                   |
|                                                                   |
|  平台子目录:                                                       |
|  +------+------+------+---------+------+                          |
|  | win/ | mac/ | unix/| android/| ios/ |                          |
|  |      |      |      |         |      |                          |
|  | GL   | GL   | GL   | GL      | GL   |                          |
|  | Vk   | Metal| Vk   | Vk      | Metal|                          |
|  | ANGLE| Dawn | Dawn | Dawn    |      |                          |
|  | D3D12|Graphi| Graphi| Graphi |Graphi|                          |
|  | Dawn | te   | te   | te      | te   |                          |
|  |Raster|Raster|Raster|Raster   |Raster|                          |
|  +------+------+------+---------+------+                          |
+------------------------------------------------------------------+
```

## 目录结构

```
tools/window/
|-- WindowContext.h           # 窗口渲染上下文抽象基类
|-- WindowContext.cpp         # 基类实现（submitToGpu、supportsGpuTimer）
|-- DisplayParams.h           # 显示参数类 + DisplayParamsBuilder
|-- GraphiteDisplayParams.h   # Graphite 扩展显示参数
|-- BUILD.bazel               # Bazel 构建定义
|-- BUILD.gn                  # GN 构建定义
|
|-- # 图形 API 通用实现
|-- GLWindowContext.h/cpp                # OpenGL 通用窗口上下文
|-- VulkanWindowContext.h/cpp            # Vulkan 通用窗口上下文（含 Swapchain）
|-- MetalWindowContext.h/mm              # Metal 通用窗口上下文
|-- ANGLEWindowContext.h/cpp             # ANGLE (OpenGL ES on non-GL) 窗口上下文
|-- GraphiteDawnWindowContext.h/cpp      # Graphite + Dawn 窗口上下文
|-- GraphiteNativeMetalWindowContext.h/mm # Graphite 原生 Metal 窗口上下文
|-- GraphiteNativeVulkanWindowContext.h/cpp # Graphite 原生 Vulkan 窗口上下文
|-- RasterWindowContext.h                # 软件光栅化窗口上下文接口
|
|-- android/                  # Android 平台窗口上下文
|   |-- WindowContextFactory_android.h  # Android 工厂函数声明
|   |-- GLWindowContext_android.cpp
|   |-- VulkanWindowContext_android.cpp
|   |-- GraphiteDawnWindowContext_android.cpp
|   |-- GraphiteVulkanWindowContext_android.cpp
|   +-- RasterWindowContext_android.cpp
|
|-- ios/                      # iOS 平台窗口上下文
|   |-- WindowContextFactory_ios.h
|   |-- GLWindowContext_ios.mm
|   |-- MetalWindowContext_ios.mm
|   |-- GraphiteMetalWindowContext_ios.mm
|   +-- RasterWindowContext_ios.mm
|
|-- mac/                      # macOS 平台窗口上下文
|   |-- MacWindowInfo.h               # macOS 窗口信息结构体
|   |-- MacWindowGLUtils.h            # macOS GL 辅助工具
|   |-- GaneshANGLEWindowContext_mac.h/mm
|   |-- GaneshGLWindowContext_mac.h/mm
|   |-- GaneshMetalWindowContext_mac.h/mm
|   |-- GraphiteDawnMetalWindowContext_mac.h/mm
|   |-- GraphiteNativeMetalWindowContext_mac.h/mm
|   +-- RasterWindowContext_mac.h/mm
|
|-- unix/                     # Linux/X11 平台窗口上下文
|   |-- XlibWindowInfo.h               # X11 窗口信息结构体
|   |-- GaneshGLWindowContext_unix.h/cpp
|   |-- GaneshVulkanWindowContext_unix.h/cpp
|   |-- GraphiteDawnXlibWindowContext_unix.h/cpp
|   |-- GraphiteNativeVulkanWindowContext_unix.h/cpp
|   +-- RasterWindowContext_unix.h/cpp
|
+-- win/                      # Windows 平台窗口上下文
    |-- WindowContextFactory_win.h     # Windows 工厂函数声明
    |-- GLWindowContext_win.cpp
    |-- VulkanWindowContext_win.cpp
    |-- ANGLEWindowContext_win.cpp
    |-- D3D12WindowContext_win.cpp
    |-- GraphiteDawnWindowContext_win.cpp
    |-- GraphiteVulkanWindowContext_win.cpp
    +-- RasterWindowContext_win.cpp
```

## 关键类与函数

### WindowContext 基类

```cpp
// tools/window/WindowContext.h
namespace skwindow {
class WindowContext {
public:
    WindowContext(std::unique_ptr<const DisplayParams>);
    virtual ~WindowContext();

    // 核心接口
    virtual sk_sp<SkSurface> getBackbufferSurface() = 0;  // 获取绘制表面
    void swapBuffers();           // 交换前后缓冲
    virtual bool isValid() = 0;   // 上下文是否有效
    virtual void resize(int w, int h) = 0;  // 窗口大小变更
    virtual void activate(bool isActive) {}  // 窗口激活/非激活
    virtual void setDisplayParams(std::unique_ptr<const DisplayParams>) = 0;

    // GPU 上下文访问
    GrDirectContext* directContext() const;        // Ganesh
    graphite::Context* graphiteContext() const;     // Graphite
    graphite::Recorder* graphiteRecorder() const;   // Graphite

    // GPU 计时与提交
    void submitToGpu(GpuTimerCallback = {});
    bool supportsGpuTimer() const;

    // 尺寸与属性
    int width() const;
    int height() const;
    int sampleCount() const;
    int stencilBits() const;

protected:
    virtual bool isGpuContext() { return true; }
    virtual void onSwapBuffers() = 0;  // 平台特定的缓冲区交换

    sk_sp<GrDirectContext> fContext;              // Ganesh 上下文
    std::unique_ptr<graphite::Context> fGraphiteContext;   // Graphite 上下文
    std::unique_ptr<graphite::Recorder> fGraphiteRecorder; // Graphite 记录器
    int fWidth, fHeight;
    std::unique_ptr<const DisplayParams> fDisplayParams;
    int fSampleCount = 1;
    int fStencilBits = 0;
};
}
```

### VulkanWindowContext（最复杂的实现）

```cpp
// tools/window/VulkanWindowContext.h
namespace skwindow::internal {
class VulkanWindowContext : public WindowContext {
public:
    using CreateVkSurfaceFn = std::function<VkSurfaceKHR(VkInstance)>;
    using CanPresentFn = sk_gpu_test::CanPresentFn;

    VulkanWindowContext(std::unique_ptr<const DisplayParams>,
                        CreateVkSurfaceFn, CanPresentFn, PFN_vkGetInstanceProcAddr);

    sk_sp<SkSurface> getBackbufferSurface() override;
    void resize(int w, int h) override;

private:
    bool createSwapchain(int width, int height);  // 创建/重建 Swapchain
    void submitToGpu();                            // 提交渲染命令
    void onSwapBuffers() override;                 // 呈现图像

    struct SwapchainImage {
        VkImage fVkImage;
        VkImageLayout fImageLayout;
        VkSemaphore fRenderCompletionSemaphore;
        sk_sp<SkSurface> fSurface;
    };

    // Vulkan 对象
    VkInstance fInstance;
    VkDevice fDevice;
    VkSwapchainKHR fSwapchain;
    AutoTArray<SwapchainImage> fImages;
    uint32_t fCurrentImageIndex;
    // ... WSI 函数指针
};
}
```

### DisplayParams 与 Builder

```cpp
// tools/window/DisplayParams.h
namespace skwindow {
class DisplayParams {
public:
    SkColorType colorType() const;           // 默认 kN32_SkColorType
    sk_sp<SkColorSpace> colorSpace() const;  // 默认 nullptr
    int msaaSampleCount() const;             // 默认 1
    const GrContextOptions& grContextOptions() const;  // Ganesh 选项
    const SkSurfaceProps& surfaceProps() const;
    bool disableVsync() const;
    bool createProtectedNativeBackend() const;
    virtual std::unique_ptr<DisplayParams> clone() const;
};

class DisplayParamsBuilder {
public:
    DisplayParamsBuilder& colorType(SkColorType);
    DisplayParamsBuilder& colorSpace(const sk_sp<SkColorSpace>&);
    DisplayParamsBuilder& msaaSampleCount(int);
    DisplayParamsBuilder& disableVsync(bool);
    DisplayParamsBuilder& surfaceProps(const SkSurfaceProps&);
    DisplayParamsBuilder& grContextOptions(const GrContextOptions&);
    std::unique_ptr<DisplayParams> detach();  // 生成不可变对象
};
}
```

## 依赖关系

```
skwindow::WindowContext
    |
    +---> DisplayParams (渲染参数)
    +---> SkSurface (backbuffer 绘制表面)
    |
    +---> Ganesh (SK_GANESH)
    |       +---> GrDirectContext
    |       +---> GrContextOptions
    |       +---> GrGLInterface (GL 后端)
    |
    +---> Graphite (SK_GRAPHITE)
    |       +---> graphite::Context
    |       +---> graphite::Recorder
    |
    +---> Vulkan SDK (VulkanWindowContext)
    |       +---> VkInstance, VkDevice, VkSwapchainKHR
    |       +---> VulkanBackendContext, VulkanInterface
    |       +---> sk_gpu_test::VkTestUtils
    |
    +---> Metal Framework (MetalWindowContext)
    |       +---> MTLDevice, CAMetalLayer
    |
    +---> Dawn/WebGPU (GraphiteDawnWindowContext)
    |       +---> dawn::native 或 wgpu API
    |
    +---> ANGLE (ANGLEWindowContext)
    |       +---> EGL/GLES 接口
    |
    +---> 平台 SDK
            +---> Win32 (HWND, HDC)
            +---> Cocoa (NSView, CALayer)
            +---> X11 (Display, Window)
            +---> Android NDK (ANativeWindow)
            +---> UIKit (UIView, CAEAGLLayer)
```

## 设计模式分析

### 1. 抽象工厂 + 策略模式

每个平台子目录提供一组工厂函数（如 `MakeGLForWin`、`MakeVulkanForWin`），`sk_app::Window` 的 `attach(BackendType)` 方法根据 BackendType 枚举选择对应的工厂来创建 WindowContext。这结合了抽象工厂（按平台分组）和策略（按后端类型选择）两种模式。

### 2. 模板方法模式

`GLWindowContext` 和 `VulkanWindowContext` 等中间基类定义了初始化和销毁的通用流程，平台特定的子类只需实现 `onInitializeContext()` 和 `onDestroyContext()` 这两个钩子方法。

### 3. 建造者模式 (Builder)

`DisplayParamsBuilder` 使用流式接口构建不可变的 `DisplayParams` 对象。`detach()` 方法转移所有权，确保构建完成后参数不可修改。

### 4. 不可变对象模式 (Immutable Object)

`DisplayParams` 被设计为一旦创建即不可修改。所有字段通过 `DisplayParamsBuilder` 设置，外部只能通过 const getter 访问。修改参数需要通过 `clone()` + Builder 创建新实例。

### 5. Swapchain 模式 (Vulkan 特有)

`VulkanWindowContext` 实现了完整的 Vulkan Swapchain 管理：图像获取（Acquire）-> 渲染 -> 信号量同步 -> 呈现（Present）。`SwapchainImage` 结构体封装了每个 Swapchain 图像的所有关联资源。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md` - WindowContext 的主要使用者
- **GPU 测试工具**: `tools/gpu/README.md` - Vulkan 工具被 VulkanWindowContext 使用
- **Vulkan 规范**: https://www.khronos.org/registry/vulkan/
- **Metal 框架**: https://developer.apple.com/metal/
- **Dawn WebGPU**: https://dawn.googlesource.com/dawn
- **ANGLE 项目**: https://chromium.googlesource.com/angle/angle
- **Skia GPU 后端**: `include/gpu/ganesh/` 和 `include/gpu/graphite/`
