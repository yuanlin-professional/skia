# tools/sk_app/mac/ - macOS 平台应用实现

## 概述

`tools/sk_app/mac/` 目录实现了 Skia 应用框架在 macOS 平台上的适配层。该实现基于 Cocoa 框架，使用 NSWindow 和 NSView 来管理窗口和事件。`Window_mac` 类封装了 NSWindow 实例，并通过 `SkTDynamicHash` 维护窗口号（NSInteger）到 `Window_mac` 实例的映射表 (`gWindowMap`)，支持多窗口场景。

macOS 实现的一个关键特性是对 Retina（高 DPI）显示的支持。`scaleFactor()` 方法返回 NSWindow 的 `backingScaleFactor`，使得 Skia 能够正确地在高分辨率屏幕上渲染。`PaintWindows()` 静态方法遍历所有注册的窗口并触发重绘，适配 macOS 的 Core Animation 刷新机制。

入口文件 `main_mac.mm` 使用 Objective-C++ 编写，通过 NSApplication 的 run loop 驱动应用执行，同时集成了 Skia 的 `Application::Create()` 工厂方法和空闲回调机制。macOS 是 Skia 开发团队的主要开发平台之一，因此该实现经过了充分的测试和优化。

## 架构图

```
+----------------------------------------------------------+
|                 macOS 应用流程                              |
|                                                           |
|  main() (main_mac.mm)                                     |
|    |                                                      |
|    v                                                      |
|  [NSApplication sharedApplication]                        |
|    |                                                      |
|    v                                                      |
|  AppDelegate (Objective-C 委托对象)                        |
|    |                                                      |
|    +-- applicationDidFinishLaunching:                      |
|    |     Application::Create(argc, argv, nil)             |
|    |     Window_mac::initWindow()                         |
|    |                                                      |
|    +-- applicationShouldTerminate:                         |
|          delete application                               |
|                                                           |
|  NSWindow (Cocoa 窗口)                                     |
|    |                                                      |
|    +-- SkNSWindowDelegate                                 |
|    |     windowDidResize: --> window->onResize()          |
|    |     windowShouldClose: --> closeWindow()             |
|    |                                                      |
|    +-- SkNSView (自定义 NSView)                           |
|          mouseDown:     --> window->onMouse()             |
|          mouseDragged:  --> window->onMouse()             |
|          mouseUp:       --> window->onMouse()             |
|          scrollWheel:   --> window->onMouseWheel()        |
|          keyDown:       --> window->onKey() + onChar()    |
|          keyUp:         --> window->onKey()               |
|          flagsChanged:  --> 修饰键状态更新                 |
|          drawRect:      --> window->onPaint()             |
|                                                           |
|  gWindowMap: SkTDynamicHash<Window_mac, NSInteger>        |
|    窗口编号 --> Window_mac 实例的全局映射                    |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/mac/
|-- BUILD.bazel        # Bazel 构建定义
|-- main_mac.mm        # macOS 入口点（NSApplication 事件循环、AppDelegate）
|-- Window_mac.h       # macOS 窗口类声明
+-- Window_mac.mm      # macOS 窗口类实现（NSWindow 管理、事件转换）
```

## 关键类与函数

### Window_mac 类

```cpp
// tools/sk_app/mac/Window_mac.h
namespace sk_app {
class Window_mac : public Window {
public:
    Window_mac() : Window(), fWindow(nil) {}
    ~Window_mac() override { this->closeWindow(); }

    bool initWindow();                    // 创建 NSWindow 和 SkNSView
    void setTitle(const char*) override;  // [fWindow setTitle:@"..."]
    void show() override;                 // [fWindow makeKeyAndOrderFront:nil]
    bool attach(BackendType) override;    // 通过 window/mac/ 工厂创建上下文
    void onInval() override {}            // macOS 使用 CVDisplayLink/Timer 驱动
    float scaleFactor() const override;   // [fWindow backingScaleFactor]

    static void PaintWindows();           // 遍历 gWindowMap，重绘所有窗口
    NSWindow* window() { return fWindow; }
    void closeWindow();                   // 释放 NSWindow

    // SkTDynamicHash 所需的键和哈希函数
    static const NSInteger& GetKey(const Window_mac& w) { return w.fWindowNumber; }
    static uint32_t Hash(const NSInteger& windowNumber) { return windowNumber; }

private:
    NSWindow*  fWindow;          // Cocoa 窗口对象
    NSInteger  fWindowNumber;    // 窗口编号，作为哈希表键

    // 全局窗口映射表（静态成员）
    static SkTDynamicHash<Window_mac, NSInteger> gWindowMap;
};
}
```

### Objective-C 辅助类 (main_mac.mm 中定义)

```
SkNSView       - 自定义 NSView 子类
                 处理鼠标事件、键盘事件和绘制
                 持有 Window_mac 指针用于事件转发

SkNSWindowDlg  - NSWindow 委托
                 处理窗口大小变化和关闭事件

AppDelegate    - NSApplication 委托
                 在 applicationDidFinishLaunching 中创建应用
                 在 applicationShouldTerminate 中清理资源
```

## 依赖关系

```
Window_mac
    |
    +---> Cocoa 框架
    |       +---> NSWindow, NSView, NSEvent
    |       +---> NSApplication, NSApplicationDelegate
    |       +---> NSOpenGLContext (GL 后端)
    |
    +---> sk_app::Window (基类)
    |
    +---> SkTDynamicHash (Skia 哈希表)
    |       +---> 使用 NSInteger 作为键
    |
    +---> tools/window/mac/
    |       +---> GaneshGLWindowContext_mac
    |       +---> GaneshMetalWindowContext_mac
    |       +---> GaneshANGLEWindowContext_mac
    |       +---> GraphiteDawnMetalWindowContext_mac
    |       +---> GraphiteNativeMetalWindowContext_mac
    |       +---> RasterWindowContext_mac
    |
    +---> tools/skui/
            +---> skui::Key, InputState, ModifierKey
```

## 设计模式分析

### 适配器模式 (Adapter)

macOS 实现将 Cocoa 的委托/Target-Action 机制适配为 sk_app 的统一事件接口。NSView 的 `mouseDown:`、`keyDown:` 等 Objective-C 选择器被转换为 `Window::onMouse()`、`Window::onKey()` 等 C++ 虚函数调用。

### 注册表模式 (Registry)

静态 `gWindowMap` 哈希表实现窗口编号到实例的映射。当 Cocoa 框架通过窗口编号路由事件时，该映射表用于快速查找对应的 `Window_mac` 实例。

### Retina 高 DPI 支持

`scaleFactor()` 返回 NSWindow 的 `backingScaleFactor`（Retina 屏为 2.0）。Viewer 使用此值调整渲染分辨率和 UI 元素大小，确保在高 DPI 屏幕上获得清晰的渲染效果。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **macOS 窗口上下文**: `tools/window/mac/README.md`
- **Apple Cocoa 文档**: https://developer.apple.com/documentation/appkit
- **NSWindow 文档**: https://developer.apple.com/documentation/appkit/nswindow
- **NSView 事件处理**: https://developer.apple.com/documentation/appkit/nsresponder
