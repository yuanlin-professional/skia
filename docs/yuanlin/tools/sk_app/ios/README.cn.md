# tools/sk_app/ios/ - iOS 平台应用实现

## 概述

`tools/sk_app/ios/` 目录实现了 Skia 应用框架在 iOS 平台上的适配层。该实现基于 UIKit 框架，使用 UIWindow 和自定义的 `MainView`（继承 UIView）来管理窗口和触摸事件。由于 iOS 的单窗口特性，`Window_ios` 采用了全局单例模式（`gWindow` 静态指针），通过 `MainWindow()` 方法访问唯一的窗口实例。

iOS 实现的特点是简洁而受限。受平台限制，`setTitle()` 和 `show()` 方法为空实现（iOS 应用没有传统意义上的窗口标题栏，也不需要显式显示窗口）。`PaintWindow()` 静态方法触发唯一窗口的重绘。入口文件 `main_ios.mm` 使用 Objective-C++ 编写，通过 `UIApplicationMain` 启动 iOS 应用生命周期。

`MainView` 是一个自定义的 UIView 子类（在 Window_ios.h 中声明），负责将 iOS 触摸事件（`touchesBegan`、`touchesMoved`、`touchesEnded`）转换为 Skia 的统一输入事件。iOS 原生支持多点触控，因此 `MainView` 需要正确处理多个触摸点的追踪。

iOS 平台支持 Metal 和 OpenGL ES 两种 GPU 后端，其中 Metal 是推荐的现代 GPU 后端。Graphite+Metal 也在 iOS 上可用。

## 架构图

```
+----------------------------------------------------------+
|                 iOS 应用流程                                |
|                                                           |
|  main() (main_ios.mm)                                     |
|    |                                                      |
|    v                                                      |
|  UIApplicationMain(argc, argv, nil, @"AppDelegate")       |
|    |                                                      |
|    v                                                      |
|  AppDelegate                                              |
|    |                                                      |
|    +-- application:didFinishLaunching:                     |
|    |     Application::Create(argc, argv, nil)             |
|    |     Window_ios::initWindow()                         |
|    |     创建 UIWindow + MainView                         |
|    |                                                      |
|    +-- applicationWillTerminate:                           |
|          delete application                               |
|                                                           |
|  UIWindow + MainView (自定义 UIView)                       |
|    |                                                      |
|    +-- touchesBegan:withEvent:                            |
|    |     --> window->onTouch(owner, kDown, x, y)          |
|    |                                                      |
|    +-- touchesMoved:withEvent:                            |
|    |     --> window->onTouch(owner, kMove, x, y)          |
|    |                                                      |
|    +-- touchesEnded:withEvent:                            |
|    |     --> window->onTouch(owner, kUp, x, y)            |
|    |                                                      |
|    +-- drawRect: (CADisplayLink 驱动)                     |
|          --> Window_ios::PaintWindow()                     |
|          --> window->onPaint()                             |
|                                                           |
|  gWindow: 全局唯一 Window_ios 实例                         |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/ios/
|-- BUILD.bazel        # Bazel 构建定义
|-- main_ios.mm        # iOS 入口点（UIApplicationMain、AppDelegate）
|-- Window_ios.h       # iOS 窗口类 + MainView 声明
+-- Window_ios.mm      # iOS 窗口类实现（UIWindow 管理、触摸事件转换）
```

## 关键类与函数

### Window_ios 类

```cpp
// tools/sk_app/ios/Window_ios.h
namespace sk_app {
class Window_ios : public Window {
public:
    Window_ios() : Window(), fWindow(nil) {}
    ~Window_ios() override { this->closeWindow(); }

    bool initWindow();                    // 创建 UIWindow 和 MainView
    void setTitle(const char*) override {} // iOS 无窗口标题（空实现）
    void show() override {}                // iOS 无需显式 show（空实现）
    bool attach(BackendType) override;    // 附着 Metal/GL/Raster 后端
    void onInval() override;              // setNeedsDisplay 触发重绘

    static void PaintWindow();            // 重绘全局唯一窗口
    UIWindow* uiWindow() { return fWindow; }
    static Window_ios* MainWindow() { return gWindow; }

private:
    void closeWindow();
    UIWindow*  fWindow;                   // UIKit 窗口对象
    static Window_ios* gWindow;           // 全局唯一实例
};
}

// MainView - 自定义 UIView 子类
@interface MainView : UIView
- (MainView*)initWithWindow:(sk_app::Window_ios*)initWindow;
@end
```

### MainView 触摸事件处理

```
MainView 将 UITouch 事件转换为 sk_app 事件：
- touchesBegan:    每个触摸点 --> onTouch(owner, kDown, x, y)
- touchesMoved:    每个触摸点 --> onTouch(owner, kMove, x, y)
- touchesEnded:    每个触摸点 --> onTouch(owner, kUp, x, y)
- touchesCancelled: 每个触摸点 --> onTouch(owner, kUp, x, y)

其中 owner 参数使用 UITouch 指针的 intptr_t 值作为触摸点标识，
支持多点触控（如双指缩放）的追踪。
```

## 依赖关系

```
Window_ios
    |
    +---> UIKit 框架
    |       +---> UIWindow, UIView, UITouch, UIEvent
    |       +---> UIApplication, UIApplicationDelegate
    |       +---> CADisplayLink (帧驱动)
    |
    +---> sk_app::Window (基类)
    |
    +---> tools/window/ios/
    |       +---> MakeGLForIOS(UIView*, DisplayParams*)
    |       +---> MakeMetalForIOS(UIView*, DisplayParams*)
    |       +---> MakeGraphiteMetalForIOS(UIView*, DisplayParams*)
    |       +---> MakeRasterForIOS(UIView*, DisplayParams*)
    |
    +---> SkTDynamicHash, SkChecksum (头文件引入)
```

## 设计模式分析

### 单例模式 (Singleton)

`Window_ios` 使用静态指针 `gWindow` 管理唯一的窗口实例。`MainWindow()` 提供全局访问点。这符合 iOS 应用通常只有一个主窗口的设计约定。

### 适配器模式 (Adapter)

`MainView` 将 UIKit 的触摸事件协议适配为 sk_app 的通用输入事件接口。每个 UITouch 对象被适配为一个 `onTouch()` 调用，UITouch 指针值用作触摸点的唯一标识符。

### 空对象模式 (Null Object)

`setTitle()` 和 `show()` 的空实现体现了空对象模式。iOS 平台不支持这些操作，但保持接口一致性使得上层代码无需进行平台判断。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **iOS 窗口上下文**: `tools/window/ios/README.md`
- **Apple UIKit 文档**: https://developer.apple.com/documentation/uikit
- **UIView 事件处理**: https://developer.apple.com/documentation/uikit/uiresponder
- **CADisplayLink**: https://developer.apple.com/documentation/quartzcore/cadisplaylink
