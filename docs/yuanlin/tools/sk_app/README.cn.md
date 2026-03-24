# tools/sk_app/ - Skia 跨平台应用框架

## 概述

`tools/sk_app/` 目录实现了 Skia 的跨平台应用程序框架，为 Skia 工具（特别是 Viewer）提供了统一的应用生命周期管理、窗口抽象和事件处理机制。该框架的核心设计目标是在六个目标平台（Windows、macOS、Linux/X11、Android、iOS、WebAssembly）上提供一致的编程接口，同时允许每个平台利用其原生窗口系统和事件循环。

框架围绕三个核心抽象构建：`Application` 类定义了应用程序的生命周期接口（创建和空闲回调）；`Window` 类提供了跨平台的窗口管理，包括标题设置、显示、GPU 后端附着，以及基于 Layer 的事件处理栈；`CommandSet` 类实现了快捷键命令的注册、管理和帮助信息显示。

`Window` 类的 Layer 系统是该框架最精巧的设计之一。通过维护一个 Layer 栈，Window 将事件分发给多个处理器（如 ImGuiLayer、StatsLayer、Viewer 自身），支持事件消费（signalLayers）和广播（visitLayers）两种分发策略。这种设计使得 UI 组件可以灵活组合而不产生紧耦合。

每个平台子目录（`win/`、`mac/`、`unix/`、`ios/`、`android/`、`wasm/`）包含两部分代码：`main_*` 文件实现平台特定的入口点和事件循环；`Window_*` 文件继承 `Window` 基类，实现平台原生窗口的创建、事件转换和 GPU 后端附着。平台实现通过调用 `tools/window/` 中的 `WindowContext` 工厂方法来创建具体的渲染上下文。

框架与 Skia 窗口系统（`tools/window/`）之间的职责划分非常清晰：`sk_app` 负责应用逻辑和平台事件循环，`window` 负责图形 API 的初始化和缓冲区管理。两者通过 `WindowContext` 接口解耦，使得同一个应用可以在不同的图形后端之间切换。

## 架构图

```
+----------------------------------------------------------------+
|                    sk_app 应用框架                                |
|                                                                  |
|  +---------------------------+                                   |
|  |     Application           |   静态工厂方法                     |
|  |  + Create(argc, argv, pd) |----> 各平台 main_* 调用            |
|  |  + onIdle()  [纯虚]       |                                   |
|  +---------------------------+                                   |
|              ^                                                   |
|              | 继承                                               |
|              |                                                   |
|  +---------------------------+                                   |
|  |        Viewer 等          |   具体应用                         |
|  +---------------------------+                                   |
|                                                                  |
|  +---------------------------+                                   |
|  |         Window            |   窗口抽象                         |
|  |  + setTitle()             |                                   |
|  |  + show()                 |                                   |
|  |  + attach(BackendType)    |----> WindowContext 创建             |
|  |  + detach()               |                                   |
|  |  + pushLayer(Layer*)      |                                   |
|  |  + onPaint()              |----> 遍历 Layer 栈                 |
|  |  + inval()                |----> 触发重绘                      |
|  |                           |                                   |
|  |  Layer 栈:                |                                   |
|  |  [StatsLayer]             |   <-- 最后添加，最先处理输入        |
|  |  [ImGuiLayer]             |                                   |
|  |  [Viewer]                 |   <-- 最先添加，最先绘制            |
|  +---------------------------+                                   |
|       ^     ^     ^     ^     ^     ^                             |
|       |     |     |     |     |     |                             |
|  +----+-+--+-+---+-+--+-+---+-+---+-+                            |
|  | win | mac | unix| ios| and| wasm |  平台实现                   |
|  +-----+-----+-----+-----+-----+----+                            |
|                                                                  |
|  +---------------------------+                                   |
|  |      CommandSet           |   快捷键管理                       |
|  |  + attach(Window*)        |                                   |
|  |  + addCommand(key, ...)   |                                   |
|  |  + onKey() / onChar()     |                                   |
|  |  + drawHelp(canvas)       |                                   |
|  +---------------------------+                                   |
+----------------------------------------------------------------+

事件处理流程:
  平台事件循环 --> Window_xxx --> Window::onKey/onMouse/...
                                    |
                            signalLayers() (后进先出)
                                    |
                    +-------+-------+-------+
                    |       |       |       |
                [Layer3] [Layer2] [Layer1]
                 Stats    ImGui    Viewer
                 (消费则停止向下传播)
```

## 目录结构

```
tools/sk_app/
|-- Application.h          # 应用程序抽象基类（4 行核心接口）
|-- Window.h               # 窗口抽象基类（~185 行，含 Layer 内部类）
|-- Window.cpp             # 窗口基类实现（事件分发、绘制循环、GPU 上下文访问）
|-- CommandSet.h           # 快捷键命令集头文件
|-- CommandSet.cpp         # 快捷键命令集实现（命令注册、帮助绘制）
|-- BUILD.bazel            # Bazel 构建定义
|
|-- android/               # Android 平台实现
|   |-- main_android.cpp   # Android 入口（JNI 回调驱动）
|   |-- Window_android.h   # Android 窗口类
|   |-- Window_android.cpp # Android 窗口实现
|   |-- surface_glue_android.h   # JNI 粘合层头文件
|   +-- surface_glue_android.cpp # JNI 粘合层实现
|
|-- ios/                   # iOS 平台实现
|   |-- BUILD.bazel        # iOS Bazel 构建
|   |-- main_ios.mm        # iOS 入口（UIApplicationMain）
|   |-- Window_ios.h       # iOS 窗口类（含 MainView）
|   +-- Window_ios.mm      # iOS 窗口实现
|
|-- mac/                   # macOS 平台实现
|   |-- BUILD.bazel        # macOS Bazel 构建
|   |-- main_mac.mm        # macOS 入口（NSApplicationMain 风格）
|   |-- Window_mac.h       # macOS 窗口类（NSWindow 封装）
|   +-- Window_mac.mm      # macOS 窗口实现
|
|-- unix/                  # Linux/X11 平台实现
|   |-- BUILD.bazel        # Unix Bazel 构建
|   |-- main_unix.cpp      # X11 入口（XNextEvent 事件循环）
|   |-- Window_unix.h      # X11 窗口类（XWindow 封装）
|   |-- Window_unix.cpp    # X11 窗口实现
|   |-- keysym2ucs.h       # X11 键盘符号到 Unicode 转换
|   +-- keysym2ucs.c       # 转换实现
|
|-- wasm/                  # WebAssembly 平台实现
|   +-- main_wasm.cpp      # WASM 入口（Emscripten 主循环）
|
+-- win/                   # Windows 平台实现
    |-- main_win.cpp       # Windows 入口（WinMain + 消息循环）
    |-- Window_win.h       # Windows 窗口类（HWND 封装）
    +-- Window_win.cpp     # Windows 窗口实现
```

## 关键类与函数

### Application 抽象基类

```cpp
// tools/sk_app/Application.h - 极简接口
namespace sk_app {
class Application {
public:
    // 平台特定的工厂方法，由各平台 main_* 调用
    static Application* Create(int argc, char** argv, void* platformData);

    virtual ~Application() {}

    // 每次事件循环空闲时调用，用于动画更新和重绘触发
    virtual void onIdle() = 0;
};
}
```

### Window 类核心接口

```cpp
// tools/sk_app/Window.h
namespace sk_app {
class Window {
public:
    // 窗口操作
    virtual void setTitle(const char*) = 0;
    virtual void show() = 0;
    void inval();  // 请求重绘

    // 渲染后端
    enum class BackendType {
        kNativeGL, kANGLE, kVulkan, kGraphiteVulkan,
        kMetal, kGraphiteMetal, kGraphiteDawnD3D11,
        kGraphiteDawnD3D12, kGraphiteDawnMetal,
        kGraphiteDawnOpenGLES, kGraphiteDawnVulkan,
        kDirect3D, kRaster
    };
    virtual bool attach(BackendType) = 0;
    void detach();

    // Layer 管理
    void pushLayer(Layer* layer);

    // GPU 上下文访问
    GrDirectContext* directContext() const;
    skgpu::graphite::Context* graphiteContext() const;
    skgpu::graphite::Recorder* graphiteRecorder() const;

    // GPU 计时与提交
    bool supportsGpuTimer() const;
    void submitToGpu(GpuTimerCallback = {});

    // 显示参数
    void setRequestedDisplayParams(std::unique_ptr<const DisplayParams>, bool allowReattach);

    // Layer 内部类
    class Layer {
    public:
        virtual void onBackendCreated() {}
        virtual void onAttach(Window*) {}
        virtual void onPrePaint() {}
        virtual void onPaint(SkSurface*) {}
        virtual void onResize(int w, int h) {}
        virtual bool onChar(SkUnichar, skui::ModifierKey) { return false; }
        virtual bool onKey(skui::Key, skui::InputState, skui::ModifierKey) { return false; }
        virtual bool onMouse(int x, int y, skui::InputState, skui::ModifierKey) { return false; }
        virtual bool onMouseWheel(float delta, int x, int y, skui::ModifierKey) { return false; }
        virtual bool onTouch(intptr_t owner, skui::InputState, float x, float y) { return false; }
        virtual bool onFling(skui::InputState) { return false; }
        virtual bool onPinch(skui::InputState, float scale, float x, float y) { return false; }
    };

protected:
    SkTDArray<Layer*> fLayers;
    std::unique_ptr<skwindow::WindowContext> fWindowContext;
    std::unique_ptr<const skwindow::DisplayParams> fRequestedDisplayParams;
};

namespace Windows {
    Window* CreateNativeWindow(void* platformData);  // 平台工厂
}
}
```

### CommandSet 命令管理

```cpp
// tools/sk_app/CommandSet.h
namespace sk_app {
class CommandSet {
public:
    void attach(Window* window);

    // 注册字符命令和键盘命令
    void addCommand(SkUnichar c, const char* group, const char* description,
                    std::function<void()> function);
    void addCommand(skui::Key k, const char* keyName, const char* group,
                    const char* description, std::function<void()> function);

    // 事件处理
    bool onKey(skui::Key key, skui::InputState state, skui::ModifierKey modifiers);
    bool onChar(SkUnichar, skui::ModifierKey modifiers);

    // UI
    void drawHelp(SkCanvas* canvas);
    std::vector<SkString> getCommandsAsSoftkeys() const;  // Android 软键支持

private:
    enum HelpMode { kNone_HelpMode, kGrouped_HelpMode, kAlphabetical_HelpMode };
};
}
```

## 依赖关系

```
sk_app::Application
    |
    +---> 由各平台 main_*.cpp 调用 Create()
    |
    v
sk_app::Window
    |
    +---> skwindow::WindowContext (tools/window/)
    |       +---> skwindow::DisplayParams
    |       +---> SkSurface (backbuffer)
    |
    +---> sk_app::Window::Layer 栈
    |       +---> 各种 Layer 实现 (Viewer, ImGuiLayer, StatsLayer)
    |
    +---> skui 命名空间 (tools/skui/)
    |       +---> InputState, Key, ModifierKey
    |
    +---> Skia Core
            +---> GrDirectContext (SK_GANESH)
            +---> graphite::Context / Recorder (SK_GRAPHITE)

sk_app::CommandSet
    |
    +---> sk_app::Window (用于注册为 softkey)
    +---> skui::Key, skui::InputState, skui::ModifierKey

平台实现:
    Window_win   ---> HWND, Win32 API
    Window_mac   ---> NSWindow, Cocoa
    Window_unix  ---> XWindow, X11/GLX
    Window_ios   ---> UIWindow, UIKit
    Window_android --> ANativeWindow, Android NDK
    main_wasm    ---> Emscripten API
```

## 设计模式分析

### 1. 模板方法模式 (Template Method)

`Window` 基类定义了绘制算法的骨架（`onPaint()`），包括获取 backbuffer Surface、遍历 Layer 栈调用 `onPrePaint()` 和 `onPaint(SkSurface*)`、刷新 GPU 并交换缓冲区。子类只需实现 `onInval()` 来触发平台特定的重绘请求。

### 2. 抽象工厂模式 (Abstract Factory)

`Application::Create()` 和 `Windows::CreateNativeWindow()` 作为工厂方法，在编译时通过链接不同的平台实现文件来确定具体创建哪种平台窗口。

### 3. 责任链模式 (Chain of Responsibility)

Layer 栈实现了经典的责任链：输入事件从栈顶向栈底传播，任何一层返回 `true` 即终止传播。绘制事件则广播给所有活跃层。

### 4. 命令模式 (Command Pattern)

`CommandSet` 将键盘快捷键映射为 `Command` 对象，每个 Command 包含类型（字符或按键）、分组、描述和回调函数。支持运行时注册和帮助文档自动生成。

### 5. 桥接模式 (Bridge)

`Window` 通过持有 `WindowContext` 指针将窗口抽象与渲染实现分离。`Window` 的平台子类（如 `Window_mac`）处理系统窗口操作，而 `WindowContext` 的子类（如 `GLWindowContext`）处理图形 API 操作。两者可以独立变化。

## 相关文档与参考

- **Viewer 文档**: `tools/viewer/README.md` - Viewer 是 sk_app 框架的主要用户
- **窗口管理**: `tools/window/README.md` - WindowContext 和 DisplayParams
- **输入系统**: `tools/skui/` - InputState、Key、ModifierKey 定义
- **平台子目录文档**:
  - `tools/sk_app/win/README.md` - Windows 平台实现
  - `tools/sk_app/mac/README.md` - macOS 平台实现
  - `tools/sk_app/unix/README.md` - Linux/X11 平台实现
  - `tools/sk_app/ios/README.md` - iOS 平台实现
  - `tools/sk_app/android/README.md` - Android 平台实现
  - `tools/sk_app/wasm/README.md` - WebAssembly 平台实现
