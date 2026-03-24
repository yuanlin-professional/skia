# tools/sk_app/win/ - Windows 平台应用实现

## 概述

`tools/sk_app/win/` 目录实现了 Skia 应用框架在 Windows 平台上的适配层。该实现基于 Win32 API，通过 `WinMain` 入口点和标准 Windows 消息循环来驱动 Skia 应用的运行。`Window_win` 类继承自 `sk_app::Window`，封装了 HWND 窗口句柄的创建与管理，将 Win32 消息（如 `WM_PAINT`、`WM_SIZE`、`WM_KEYDOWN`、`WM_MOUSEMOVE` 等）转换为 Skia 的统一输入事件。

Windows 实现的一个特殊之处在于它覆盖了 `setRequestedDisplayParams()` 方法，支持在显示参数变更时重新附着渲染后端（`allowReattach` 参数）。这使得用户可以在运行时动态切换图形后端类型（如从 OpenGL 切换到 Vulkan 或 Direct3D），无需重启应用。

该目录还与 `tools/window/win/` 中的窗口上下文工厂协作，后者提供了 `MakeGLForWin`、`MakeVulkanForWin`、`MakeANGLEForWin`、`MakeD3D12ForWin`、`MakeRasterForWin` 等工厂函数来创建具体的渲染上下文。Windows 是 Skia 支持图形后端最多的平台，包含 OpenGL、Vulkan、ANGLE、Direct3D 12、Graphite+Dawn（D3D11/D3D12/Vulkan/OpenGLES）等多种选择。

## 架构图

```
+----------------------------------------------------------+
|                 Windows 应用流程                           |
|                                                           |
|  WinMain()                                                |
|    |                                                      |
|    v                                                      |
|  RegisterClassEx()  <-- 注册 WNDCLASSEX, 设置 WndProc     |
|    |                                                      |
|    v                                                      |
|  Application::Create()  <-- 创建 Viewer 等应用实例         |
|    |                                                      |
|    v                                                      |
|  主消息循环:                                               |
|  while (true) {                                           |
|    if (PeekMessage(&msg, ...)) {                          |
|      TranslateMessage(&msg);                              |
|      DispatchMessage(&msg);  --> WndProc                  |
|    } else {                                               |
|      app->onIdle();  --> 触发动画更新和重绘                 |
|    }                                                      |
|  }                                                        |
|                                                           |
|  WndProc(hwnd, msg, wParam, lParam):                      |
|    WM_PAINT    --> window->onPaint()                      |
|    WM_SIZE     --> window->onResize(w, h)                 |
|    WM_KEYDOWN  --> window->onKey(key, kDown, mods)        |
|    WM_KEYUP    --> window->onKey(key, kUp, mods)          |
|    WM_CHAR     --> window->onChar(c, mods)                |
|    WM_LBUTTONDOWN --> window->onMouse(x, y, kDown, mods)  |
|    WM_MOUSEMOVE   --> window->onMouse(x, y, kMove, mods)  |
|    WM_MOUSEWHEEL  --> window->onMouseWheel(delta, ...)    |
|    WM_CLOSE    --> DestroyWindow                          |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/win/
|-- main_win.cpp        # Windows 入口点 (WinMain)，消息循环，WndProc
|-- Window_win.h        # Windows 窗口类声明
+-- Window_win.cpp      # Windows 窗口类实现（窗口创建、后端附着、事件处理）
```

## 关键类与函数

### Window_win 类

```cpp
// tools/sk_app/win/Window_win.h
namespace sk_app {
class Window_win : public Window {
public:
    Window_win() : Window() {}
    ~Window_win() override;

    bool init(HINSTANCE instance);            // 创建 Win32 窗口 (CreateWindowEx)
    void setTitle(const char*) override;      // SetWindowTextA
    void show() override;                     // ShowWindow + UpdateWindow
    bool attach(BackendType) override;        // 根据 BackendType 调用窗口上下文工厂
    void onInval() override;                  // InvalidateRect 触发 WM_PAINT

    // 支持运行时重新附着渲染后端
    void setRequestedDisplayParams(
        std::unique_ptr<const skwindow::DisplayParams>,
        bool allowReattach) override;

private:
    void closeWindow();                       // 销毁窗口资源

    HINSTANCE   fHInstance;                   // 应用程序实例句柄
    HWND        fHWnd;                        // 窗口句柄
    BackendType fBackend;                     // 当前附着的渲染后端类型
    bool        fInitializedBackend = false;  // 渲染后端是否已初始化
};
}
```

### main_win.cpp 入口逻辑

```
1. 注册 WNDCLASSEX 窗口类
   - 设置 WndProc 回调函数
   - 设置图标和光标

2. 调用 Application::Create(argc, argv, hInstance)
   - 由 Viewer 等应用提供具体实现

3. 进入消息循环
   - 使用 PeekMessage (非阻塞) 检查消息
   - 有消息时：TranslateMessage + DispatchMessage
   - 无消息时：调用 app->onIdle()

4. WndProc 函数
   - 从 GWLP_USERDATA 获取 Window_win 指针
   - 将 Win32 消息转换为 sk_app 事件方法调用
   - 处理键盘修饰键状态 (Shift/Ctrl/Alt)
   - 将 VK_* 虚拟键码映射为 skui::Key 枚举
```

## 依赖关系

```
Window_win
    |
    +---> Win32 API
    |       +---> windows.h (HWND, HINSTANCE, WNDCLASSEX, MSG)
    |       +---> CreateWindowExA, ShowWindow, UpdateWindow
    |       +---> PeekMessage, TranslateMessage, DispatchMessage
    |       +---> InvalidateRect, SetWindowTextA
    |       +---> GetWindowLongPtr / SetWindowLongPtr (GWLP_USERDATA)
    |
    +---> sk_app::Window (基类)
    |       +---> Layer 栈事件分发
    |       +---> WindowContext 管理
    |
    +---> tools/window/win/WindowContextFactory_win.h
    |       +---> MakeGLForWin(HWND, DisplayParams*)
    |       +---> MakeVulkanForWin(HWND, DisplayParams*)
    |       +---> MakeANGLEForWin(HWND, DisplayParams*)
    |       +---> MakeD3D12ForWin(HWND, DisplayParams*)
    |       +---> MakeGraphiteDawnD3D11ForWin(HWND, DisplayParams*)
    |       +---> MakeGraphiteDawnD3D12ForWin(HWND, DisplayParams*)
    |       +---> MakeRasterForWin(HWND, DisplayParams*)
    |
    +---> tools/skui/
            +---> skui::Key (键码枚举)
            +---> skui::InputState (输入状态枚举)
            +---> skui::ModifierKey (修饰键枚举)
```

## 设计模式分析

### 适配器模式 (Adapter)

Windows 实现的核心是将 Win32 的过程式消息机制（WndProc 回调 + WPARAM/LPARAM 消息参数）适配为 sk_app 的面向对象事件接口。WndProc 函数作为适配器，通过窗口的 `GWLP_USERDATA` 用户数据指针获取 `Window_win` 实例，然后解析消息参数并调用相应的虚函数。

### 后端动态切换

`Window_win` 是少数覆盖 `setRequestedDisplayParams()` 的平台实现之一。当 `allowReattach` 为 `true` 时，它会销毁当前的 WindowContext 并使用新的 DisplayParams 和可能不同的 BackendType 重新创建。这使得 Viewer 可以在运行时切换渲染后端。

### 非阻塞消息泵

`main_win.cpp` 使用 `PeekMessage` 而非 `GetMessage` 实现消息循环。`GetMessage` 在没有消息时会阻塞线程，而 `PeekMessage` 立即返回，允许在无消息时调用 `app->onIdle()` 进行动画更新和帧渲染。这是实时图形应用的标准做法。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **Windows 窗口上下文**: `tools/window/win/README.md`
- **Win32 API 文档**: https://learn.microsoft.com/en-us/windows/win32/
- **Win32 消息循环**: https://learn.microsoft.com/en-us/windows/win32/winmsg/about-messages-and-message-queues
