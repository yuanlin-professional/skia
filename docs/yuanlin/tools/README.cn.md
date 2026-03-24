# tools/ - Skia 工具集根目录

## 概述

`tools/` 目录是 Skia 图形库中最重要的辅助工具集合，包含了用于开发、测试、调试和性能分析的全部工具代码。该目录中的代码并非 Skia 核心渲染引擎的一部分，而是为开发者和测试基础设施提供支撑的辅助组件。

从功能角度来看，`tools/` 目录涵盖了以下几个核心领域：交互式查看器（Viewer）用于实时预览和调试 Skia 渲染效果；跨平台应用框架（sk_app）和窗口管理（window）提供了在 Windows、macOS、Linux、Android、iOS 以及 WebAssembly 上运行 Skia 应用的基础设施；GPU 测试工具（gpu）为 Ganesh 和 Graphite 两套 GPU 后端提供了纹理管理、上下文创建和 Vulkan 专用工具；命令行标志系统（flags）实现了类似 Google gflags 的参数解析框架。

此外，`tools/` 还包含大量辅助性工具，如编解码器工具（CodecUtils、DecodeUtils、EncodeUtils）、资源管理（Resources）、序列化与反序列化支持（DeserialProcsUtils、SkSharingProc）、字体管理（fonts）、追踪与性能分析（trace、timer）、基础设施脚本（infra）以及各种 Python 自动化脚本。这些工具共同构成了 Skia 项目开发和持续集成流水线的关键基础。

整个 `tools/` 目录的设计理念是高度模块化的。每个子目录都聚焦于特定功能领域，通过清晰的接口相互协作。核心的依赖链是：`viewer` 依赖 `sk_app`，`sk_app` 依赖 `window`，`window` 依赖 `gpu` 和 Skia 核心库。命令行 `flags` 系统则被几乎所有可执行工具所共享。

## 架构图

```
tools/
+-----------------------------------------------------------------------+
|                                                                       |
|  +------------------+     +------------------+    +-----------------+ |
|  |    viewer/       |     |    sk_app/       |    |    window/      | |
|  |  (Skia 查看器)    |---->|  (应用框架)       |--->|  (窗口上下文)    | |
|  |  Viewer, Slide   |     |  Application     |    |  WindowContext  | |
|  |  ImGuiLayer      |     |  Window, Command |    |  DisplayParams  | |
|  +------------------+     +------------------+    +-----------------+ |
|          |                    |  |  |  |  |           |  |  |  |  |  |
|          |               +---+--+--+--+--+---+   +---+--+--+--+--+  |
|          |               |win|mac|unix|ios|and|   |win|mac|unix|ios| |
|          |               |asm|   |    |   |   |   |   |   |    |and| |
|          |               +---+---+----+---+---+   +---+---+----+---+ |
|          |                                                           |
|  +------------------+     +------------------+    +-----------------+ |
|  |    flags/        |     |    gpu/          |    |    gpu/vk/      | |
|  | (命令行标志)      |     | (GPU测试工具)     |    | (Vulkan工具)    | |
|  | CommandLineFlags |     | BackendSurface   |    | VkTestHelper    | |
|  | CommonFlags*     |     | ManagedTexture   |    | VkTestUtils     | |
|  +------------------+     | ContextType      |    | VkYcbcrSampler  | |
|          |                +------------------+    +-----------------+ |
|          |                                                           |
|  +-------------------------------+  +------------------------------+ |
|  |     核心辅助工具                |  |     脚本与自动化               | |
|  | Resources, ToolUtils          |  | git-sync-deps, infra/        | |
|  | CrashHandler, Registry        |  | embed_resources.py           | |
|  | CodecUtils, DecodeUtils       |  | rewrite_includes.py          | |
|  | EncodeUtils, HashAndEncode    |  | build_with_reclient.sh       | |
|  | DeserialProcsUtils            |  | check-headers-self-sufficient| |
|  +-------------------------------+  +------------------------------+ |
|                                                                       |
|  +-------------------------------+  +------------------------------+ |
|  |   图形引擎专用工具              |  |     其他工具                   | |
|  | ganesh/   (Ganesh GPU工具)     |  | debugger/  (调试器)           | |
|  | graphite/ (Graphite GPU工具)   |  | fiddle/    (在线编辑)         | |
|  | skui/     (UI输入状态)         |  | skdiff/    (图片比较)         | |
|  | fonts/    (字体工具)           |  | skqp/      (质量测试)         | |
|  | trace/    (追踪工具)           |  | timer/     (计时工具)         | |
|  +-------------------------------+  +------------------------------+ |
+-----------------------------------------------------------------------+
```

## 目录结构

```
tools/
|-- viewer/               # Skia 交互式查看器应用程序
|   |-- Viewer.h/cpp      # 主查看器类，继承 Application 和 Window::Layer
|   |-- Slide.h           # 幻灯片基类，所有演示效果的抽象接口
|   |-- *Slide.cpp        # 70+ 个具体幻灯片实现
|   |-- ImGuiLayer.h/cpp  # ImGui 集成层，提供调试 UI
|   |-- StatsLayer.h/cpp  # 性能统计显示层
|   +-- TouchGesture.h    # 触摸手势处理
|
|-- sk_app/               # 跨平台应用框架
|   |-- Application.h     # 应用程序抽象基类
|   |-- Window.h/cpp      # 窗口抽象基类，含 Layer 系统
|   |-- CommandSet.h/cpp  # 快捷键命令管理器
|   |-- android/          # Android 平台实现
|   |-- ios/              # iOS 平台实现
|   |-- mac/              # macOS 平台实现
|   |-- unix/             # Linux/X11 平台实现
|   |-- wasm/             # WebAssembly 平台实现
|   +-- win/              # Windows 平台实现
|
|-- window/               # 窗口渲染上下文管理
|   |-- WindowContext.h   # 窗口渲染上下文抽象基类
|   |-- DisplayParams.h   # 显示参数配置（颜色类型、MSAA等）
|   |-- GLWindowContext.h # OpenGL 窗口上下文
|   |-- VulkanWindowContext.h    # Vulkan 窗口上下文
|   |-- MetalWindowContext.h     # Metal 窗口上下文
|   |-- GraphiteDawnWindowContext.h  # Graphite+Dawn 窗口上下文
|   |-- ANGLEWindowContext.h     # ANGLE 窗口上下文
|   |-- RasterWindowContext.h    # 软件光栅化窗口上下文
|   |-- android/          # Android 平台窗口上下文实现
|   |-- ios/              # iOS 平台窗口上下文实现
|   |-- mac/              # macOS 平台窗口上下文实现
|   |-- unix/             # Linux 平台窗口上下文实现
|   +-- win/              # Windows 平台窗口上下文实现
|
|-- gpu/                  # GPU 测试辅助工具
|   |-- BackendSurfaceFactory.h  # 后端 Surface 工厂
|   |-- BackendTextureImageFactory.h  # 后端纹理图像工厂
|   |-- ManagedBackendTexture.h  # 托管后端纹理（自动生命周期管理）
|   |-- ContextType.h     # GPU 上下文类型枚举
|   |-- FlushFinishTracker.h  # 刷新完成追踪器
|   |-- YUVUtils.h        # YUV 图像处理工具
|   +-- vk/               # Vulkan 专用测试工具
|       |-- VkTestHelper.h       # Vulkan 测试辅助器
|       |-- VkTestUtils.h        # Vulkan 后端上下文创建
|       |-- VkTestMemoryAllocator.h  # 测试用 Vulkan 内存分配器
|       +-- VkYcbcrSamplerHelper.h   # YCbCr 采样器辅助器
|
|-- flags/                # 命令行标志解析框架
|   |-- CommandLineFlags.h/cpp  # 核心标志定义与解析
|   |-- CommonFlags.h     # 通用图像路径标志
|   |-- CommonFlagsConfig.h      # 渲染配置标志
|   |-- CommonFlagsGanesh.h      # Ganesh GPU 选项标志
|   +-- CommonFlagsGraphite.h    # Graphite GPU 选项标志
|
|-- ganesh/               # Ganesh (旧 GPU 后端) 专用工具
|-- graphite/             # Graphite (新 GPU 后端) 专用工具
|-- skui/                 # UI 输入状态定义 (Key, InputState, ModifierKey)
|-- fonts/                # 字体管理与测试工具
|-- trace/                # 追踪与事件日志工具
|-- timer/                # 计时器工具
|-- debugger/             # Skia 调试器
|-- fiddle/               # Skia Fiddle 在线编辑工具
|-- skdiff/               # 图片差异比较工具
|-- skqp/                 # Skia Quality Program 测试
|-- infra/                # 基础设施脚本
|
|-- Resources.h/cpp       # 测试资源加载与管理
|-- ToolUtils.h/cpp       # 通用工具函数集
|-- CrashHandler.h/cpp    # 崩溃处理器
|-- Registry.h            # 通用注册表模板
|-- CodecUtils.h          # 编解码器辅助
|-- DecodeUtils.h/cpp     # 解码辅助
|-- EncodeUtils.h/cpp     # 编码辅助
|-- HashAndEncode.h/cpp   # 哈希与编码工具
|-- DeserialProcsUtils.h  # 反序列化回调工具
|-- SkSharingProc.h/cpp   # 共享序列化处理
|-- SkMetaData.h/cpp      # 元数据键值存储
|-- RuntimeBlendUtils.h   # 运行时混合工具
|-- GpuToolUtils.h        # GPU 工具通用函数
+-- BUILD.bazel           # Bazel 构建文件
```

## 关键类与函数

### 核心应用框架类

| 类名 | 文件 | 描述 |
|------|------|------|
| `sk_app::Application` | `sk_app/Application.h` | 应用程序抽象基类，定义 `Create()` 和 `onIdle()` |
| `sk_app::Window` | `sk_app/Window.h` | 窗口抽象基类，管理 Layer 栈和事件分发 |
| `sk_app::Window::Layer` | `sk_app/Window.h` | 窗口图层接口，支持输入和绘制事件 |
| `sk_app::CommandSet` | `sk_app/CommandSet.h` | 快捷键命令管理，支持分组帮助显示 |
| `Viewer` | `viewer/Viewer.h` | Skia 交互式查看器，继承 Application 和 Layer |
| `Slide` | `viewer/Slide.h` | 幻灯片抽象基类，`draw()` 为核心纯虚方法 |

### GPU 与窗口上下文类

| 类名 | 文件 | 描述 |
|------|------|------|
| `skwindow::WindowContext` | `window/WindowContext.h` | 窗口渲染上下文抽象基类 |
| `skwindow::DisplayParams` | `window/DisplayParams.h` | 显示参数（颜色类型、MSAA、VSync等） |
| `skwindow::DisplayParamsBuilder` | `window/DisplayParams.h` | 显示参数构建器（Builder 模式） |
| `skwindow::internal::GLWindowContext` | `window/GLWindowContext.h` | OpenGL 窗口上下文实现 |
| `skwindow::internal::VulkanWindowContext` | `window/VulkanWindowContext.h` | Vulkan 窗口上下文，含 Swapchain 管理 |

### 测试辅助类

| 类名 | 文件 | 描述 |
|------|------|------|
| `sk_gpu_test::ManagedBackendTexture` | `gpu/ManagedBackendTexture.h` | Ganesh 托管后端纹理 |
| `sk_gpu_test::ManagedGraphiteTexture` | `gpu/ManagedBackendTexture.h` | Graphite 托管后端纹理 |
| `sk_gpu_test::FlushFinishTracker` | `gpu/FlushFinishTracker.h` | GPU 刷新完成追踪器 |
| `VkTestHelper` | `gpu/vk/VkTestHelper.h` | Vulkan 测试环境辅助器 |
| `VkYcbcrSamplerHelper` | `gpu/vk/VkYcbcrSamplerHelper.h` | Vulkan YCbCr 采样器辅助器 |
| `CommandLineFlags` | `flags/CommandLineFlags.h` | 命令行标志解析引擎 |

### 关键全局函数与宏

| 函数/宏 | 文件 | 描述 |
|---------|------|------|
| `DEFINE_bool/string/int/double` | `flags/CommandLineFlags.h` | 定义命令行标志的宏 |
| `DECLARE_bool/string/int/double` | `flags/CommandLineFlags.h` | 跨文件声明已有标志 |
| `DEF_SLIDE(code)` | `viewer/Slide.h` | 注册新幻灯片的宏 |
| `sk_gpu_test::MakeBackendTextureSurface()` | `gpu/BackendSurfaceFactory.h` | 创建 GPU 后端纹理 Surface |
| `sk_gpu_test::CreateVkBackendContext()` | `gpu/vk/VkTestUtils.h` | 创建 Vulkan 后端上下文 |
| `CommonFlags::SetCtxOptions()` | `flags/CommonFlagsGanesh.h` | 从命令行标志设置 Ganesh 上下文选项 |

## 依赖关系

```
         Viewer (tools/viewer/)
            |
            v
    sk_app::Application + sk_app::Window (tools/sk_app/)
            |                    |
            |                    v
            |        sk_app::CommandSet (tools/sk_app/)
            |
            v
    skwindow::WindowContext (tools/window/)
            |
            +---> DisplayParams, DisplayParamsBuilder
            |
            +---> GLWindowContext / VulkanWindowContext / MetalWindowContext
            |     GraphiteDawnWindowContext / ANGLEWindowContext / RasterWindowContext
            |
            v
    Skia Core (include/core/, include/gpu/)
            |
            +---> GrDirectContext (SK_GANESH)
            +---> skgpu::graphite::Context + Recorder (SK_GRAPHITE)

    CommandLineFlags (tools/flags/)
            |
            +---> 被 Viewer, DM, nanobench 等所有可执行工具使用
            +---> CommonFlags* 扩展模块提供特定领域标志

    sk_gpu_test (tools/gpu/)
            |
            +---> BackendSurfaceFactory, ManagedBackendTexture
            +---> FlushFinishTracker, YUVUtils
            +---> vk/ (VkTestHelper, VkTestUtils, VkTestMemoryAllocator)
```

### 外部依赖

- **Skia 核心库**: `include/core/`, `include/gpu/`, `src/core/`
- **ImGui**: 用于 Viewer 的调试 UI（`viewer/ImGuiLayer`）
- **Vulkan SDK**: 用于 Vulkan 窗口上下文和测试工具
- **VulkanMemoryAllocator (VMA)**: 用于 `VkTestMemoryAllocator`
- **平台 SDK**: Win32 API、Cocoa/UIKit、X11/GLX、Android NDK、Emscripten

## 设计模式分析

### 1. 分层架构模式 (Layered Architecture)

整个 `tools/` 目录采用清晰的分层设计：
- **应用层** (`viewer/`): 具体的应用逻辑，如幻灯片管理和用户交互
- **框架层** (`sk_app/`): 跨平台应用生命周期和窗口抽象
- **渲染层** (`window/`): 具体的图形 API 窗口上下文实现
- **基础设施层** (`gpu/`, `flags/`): 底层测试工具和配置系统

### 2. 责任链模式 (Chain of Responsibility) - Layer 系统

`sk_app::Window` 使用 Layer 栈来处理事件。事件从栈顶向下传播，每个 Layer 可以选择消费或传递事件。`signalLayers()` 方法从后向前遍历，第一个返回 `true` 的 Layer 终止传播；`visitLayers()` 则广播给所有活跃 Layer。

```cpp
// Window.cpp 中的事件分发
bool Window::signalLayers(const std::function<bool(Layer*)>& visitor) {
    for (int i = fLayers.size() - 1; i >= 0; --i) {
        if (fLayers[i]->fActive && visitor(fLayers[i])) {
            return true;
        }
    }
    return false;
}
```

### 3. 工厂方法模式 (Factory Method)

- `sk_app::Application::Create()` 是静态工厂方法，每个平台提供不同实现
- `sk_app::Windows::CreateNativeWindow()` 创建平台特定的窗口对象
- `sk_gpu_test::MakeBackendTextureSurface()` 根据 GPU 后端创建不同的 Surface

### 4. 建造者模式 (Builder)

`skwindow::DisplayParamsBuilder` 采用流式接口构建不可变的 `DisplayParams` 对象：

```cpp
auto params = DisplayParamsBuilder()
    .colorType(kRGBA_8888_SkColorType)
    .msaaSampleCount(4)
    .disableVsync(true)
    .detach();
```

### 5. 注册表模式 (Registry)

`Slide` 使用 `SlideRegistry`（基于 `sk_tools::Registry` 模板）实现自注册。通过 `DEF_SLIDE` 宏，新幻灯片在静态初始化阶段自动注册，无需修改 Viewer 主代码：

```cpp
DEF_SLIDE(return new MyCustomSlide();)
```

### 6. 策略模式 (Strategy)

`Window::BackendType` 枚举允许在运行时切换渲染后端（OpenGL、Vulkan、Metal、Dawn、Raster 等），每种后端对应一个 `WindowContext` 实现子类。

### 7. 引用计数与 RAII

`ManagedBackendTexture` 和 `ManagedGraphiteTexture` 继承自 `SkNVRefCnt`，通过引用计数自动管理 GPU 纹理的生命周期。`ReleaseProc` 回调确保在最后一个引用释放时正确清理 GPU 资源。

### 8. 单例变体 (Singleton-like) - 命令行标志

`CommandLineFlags` 使用全局链表 (`gHead`) 管理所有标志。`DEFINE_*` 宏在静态初始化时创建 `SkFlagInfo` 节点并链入全局链表，`Parse()` 遍历链表解析命令行参数。

## 相关文档与参考

- **Skia 官方文档**: https://skia.org/docs/
- **Skia Viewer 使用指南**: https://skia.org/docs/dev/tools/viewer/
- **GPU 测试框架**: 参见 `tests/` 目录中对 `sk_gpu_test` 命名空间的使用
- **Ganesh GPU 后端**: `include/gpu/ganesh/` 头文件
- **Graphite GPU 后端**: `include/gpu/graphite/` 头文件
- **Vulkan 集成**: `include/gpu/vk/` 头文件
- **构建系统**: `BUILD.bazel` 和 `BUILD.gn` 文件定义了各工具的构建规则
- **持续集成**: `tools/infra/` 包含 CI/CD 相关脚本
- **gflags 项目**: https://github.com/gflags/gflags （CommandLineFlags 的灵感来源）
