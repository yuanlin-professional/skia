# tools/sk_app/unix/ - Linux/X11 平台应用实现

## 概述

`tools/sk_app/unix/` 目录实现了 Skia 应用框架在 Linux 平台上的适配层，基于 X Window System (X11) 和 GLX。`Window_unix` 类封装了 X11 的 `XWindow` 句柄，通过 `SkTDynamicHash` 维护窗口 ID 到实例的映射，支持多窗口管理。

该实现的一个显著特点是它的惰性更新机制：`markPendingPaint()` 和 `markPendingResize()` 方法标记窗口需要重绘或调整大小，而实际操作延迟到 `finishPaint()` 和 `finishResize()` 中执行。这种设计避免了 X11 事件洪水中的冗余操作，如在连续的 `ConfigureNotify` 事件中只响应最后一次 resize。

Linux 是 Skia 唯一实现了系统剪贴板访问的平台（通过 `getClipboardText()` 和 `setClipboardText()`），使用 X11 的选择协议（Selection Protocol）和 `XA_CLIPBOARD` 原子。此外，`keysym2ucs.c` 文件提供了 X11 KeySym 到 Unicode 码点的转换功能，基于 Markus Kuhn 的开源实现。

入口文件 `main_unix.cpp` 实现了标准的 X11 事件循环，使用 `XNextEvent` 获取事件，通过 `XPending` 检查是否有待处理事件，在空闲时调用 `app->onIdle()`。

## 架构图

```
+----------------------------------------------------------+
|                 Linux/X11 应用流程                          |
|                                                           |
|  main() (main_unix.cpp)                                   |
|    |                                                      |
|    v                                                      |
|  XOpenDisplay(nullptr)  <-- 连接 X11 服务器               |
|    |                                                      |
|    v                                                      |
|  Application::Create(argc, argv, display)                 |
|    |                                                      |
|    v                                                      |
|  主事件循环:                                               |
|  while (true) {                                           |
|    while (XPending(display)) {                            |
|      XNextEvent(display, &event);                         |
|      Window_unix* win = gWindowMap.find(event.xany.window)|
|      win->handleEvent(event);                             |
|    }                                                      |
|    for (each window) {                                    |
|      win->finishResize();  // 执行待定的 resize            |
|      win->finishPaint();   // 执行待定的 paint             |
|    }                                                      |
|    app->onIdle();  // 空闲回调                             |
|  }                                                        |
|                                                           |
|  handleEvent(XEvent):                                     |
|    Expose       --> markPendingPaint()                    |
|    ConfigureNotify --> markPendingResize(w, h)            |
|    KeyPress     --> onKey(key, kDown, mods) + onChar(c)   |
|    KeyRelease   --> onKey(key, kUp, mods)                 |
|    ButtonPress  --> onMouse(x, y, kDown, mods)            |
|    ButtonRelease--> onMouse(x, y, kUp, mods)              |
|    MotionNotify --> onMouse(x, y, kMove, mods)            |
|    ClientMessage (WM_DELETE_WINDOW) --> 关闭窗口          |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/unix/
|-- BUILD.bazel          # Bazel 构建定义
|-- main_unix.cpp        # X11 入口点（XNextEvent 事件循环）
|-- Window_unix.h        # X11 窗口类声明
|-- Window_unix.cpp      # X11 窗口类实现
|-- keysym2ucs.h         # X11 KeySym 到 Unicode 转换头文件
+-- keysym2ucs.c         # 转换实现（基于 Unicode 标准映射表）
```

## 关键类与函数

### Window_unix 类

```cpp
// tools/sk_app/unix/Window_unix.h
namespace sk_app {
class Window_unix : public Window {
public:
    bool initWindow(Display* display);    // 创建 X11 窗口 (XCreateWindow)
    void setTitle(const char*) override;  // XStoreName
    void show() override;                 // XMapWindow
    bool attach(BackendType) override;    // 附着渲染后端
    void onInval() override;              // 发送 Expose 事件

    // 系统剪贴板（唯一实现此功能的平台）
    const char* getClipboardText() override;
    void setClipboardText(const char*) override;

    // X11 事件处理
    bool handleEvent(const XEvent& event);

    // 惰性更新机制
    void markPendingPaint();                      // 标记需要重绘
    void finishPaint();                           // 执行待定重绘
    void markPendingResize(int width, int height); // 标记需要调整大小
    void finishResize();                          // 执行待定 resize

    // 支持运行时切换后端
    void setRequestedDisplayParams(...) override;

    // 全局窗口映射表
    static SkTDynamicHash<Window_unix, XWindow> gWindowMap;

private:
    Display*     fDisplay;           // X11 显示连接
    XWindow      fWindow;            // X11 窗口 ID
    GC           fGC;                // X11 图形上下文
    GLXFBConfig* fFBConfig;          // GLX 帧缓冲配置
    XVisualInfo* fVisualInfo;        // X11 视觉信息
    int          fMSAASampleCount;   // MSAA 采样数
    Atom         fWmDeleteMessage;   // WM_DELETE_WINDOW 原子
    BackendType  fBackend;           // 当前后端类型
    std::string  fClipboardText;     // 剪贴板文本缓存
    bool         fPendingPaint;      // 是否有待定重绘
    bool         fPendingResize;     // 是否有待定 resize
    int          fPendingWidth, fPendingHeight;  // 待定尺寸
};
}
```

### keysym2ucs 转换

```c
// tools/sk_app/unix/keysym2ucs.h
// 将 X11 KeySym 转换为 Unicode 码点
// 基于 Markus Kuhn 的开源实现
long keysym2ucs(unsigned int keysym);
```

## 依赖关系

```
Window_unix
    |
    +---> X11 / Xlib
    |       +---> XOpenDisplay, XCreateWindow, XMapWindow
    |       +---> XNextEvent, XPending, XSendEvent
    |       +---> XStoreName, XInternAtom
    |       +---> XSetSelectionOwner, XConvertSelection (剪贴板)
    |
    +---> GLX
    |       +---> glXChooseFBConfig, glXGetVisualFromFBConfig
    |
    +---> sk_app::Window (基类)
    +---> SkTDynamicHash, SkChecksum
    |
    +---> tools/window/unix/
    |       +---> GaneshGLWindowContext_unix
    |       +---> GaneshVulkanWindowContext_unix
    |       +---> GraphiteDawnXlibWindowContext_unix
    |       +---> GraphiteNativeVulkanWindowContext_unix
    |       +---> RasterWindowContext_unix
    |
    +---> tools/skui/
            +---> skui::Key, InputState, ModifierKey
```

## 设计模式分析

### 事件聚合与防抖 (Debounce)

Linux 实现最独特的设计是惰性更新机制。X11 在窗口调整大小时会发送大量 `ConfigureNotify` 事件，直接响应每个事件会导致频繁的 resize 和重绘。`markPendingResize()` 只记录最新的目标尺寸，`finishResize()` 在事件循环空闲时执行一次操作，实现了高效的事件聚合。

### 注册表模式

静态 `gWindowMap` 将 X11 窗口 ID 映射到 `Window_unix` 实例，使得事件循环可以快速将 XEvent 路由到正确的窗口对象。

### X11 Selection Protocol（剪贴板）

剪贴板实现使用 X11 的选择协议，这是一个异步的请求-响应机制。设置剪贴板调用 `XSetSelectionOwner`，获取剪贴板需要 `XConvertSelection` + 等待 `SelectionNotify` 事件。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **Linux 窗口上下文**: `tools/window/unix/README.md`
- **X11 编程手册**: https://www.x.org/releases/current/doc/
- **GLX 规范**: https://www.khronos.org/registry/OpenGL/specs/gl/glxencode.html
- **keysym2ucs 来源**: Markus Kuhn 的 X11 KeySym 映射
