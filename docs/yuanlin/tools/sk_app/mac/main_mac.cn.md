# main_mac.mm

> 源文件: tools/sk_app/mac/main_mac.mm

## 概述

`main_mac.mm` 是 Skia 应用程序框架在 macOS 平台上的主入口点实现文件。该文件使用 Objective-C++ 语言编写，负责初始化 macOS 应用程序环境、创建应用程序菜单、管理事件循环，并与 Skia 的跨平台应用程序框架进行集成。这是一个典型的 macOS 原生应用程序启动器，它桥接了 Cocoa 框架和 Skia 的应用程序抽象层。

该文件的核心职责包括：
- 初始化 NSApplication 实例并配置应用程序生命周期
- 创建基本的应用程序菜单栏（包含退出功能）
- 实现自定义的事件循环，将 macOS 事件与 Skia 的窗口系统集成
- 管理应用程序的空闲处理和窗口重绘机制
- 处理应用程序的启动和终止流程

## 架构位置

在 Skia 的整体架构中，`main_mac.mm` 位于平台抽象层的最顶层：

```
tools/
  └── sk_app/                    # Skia 应用程序框架
      ├── Application.h          # 跨平台应用程序抽象接口
      ├── mac/
      │   ├── main_mac.mm       # macOS 平台入口点（本文件）
      │   └── Window_mac.h       # macOS 窗口实现
      ├── unix/
      │   └── main_unix.cpp      # Unix/Linux 平台入口点
      ├── win/
      │   └── main_win.cpp       # Windows 平台入口点
      └── android/
          └── main_android.cpp   # Android 平台入口点
```

该文件是平台相关代码的入口，负责将 macOS 的原生事件循环与 Skia 的跨平台 `Application` 类连接起来。它依赖于 Cocoa 框架的 NSApplication、NSMenu 等类，同时使用 Skia 的 `sk_app::Application` 和 `sk_app::Window_mac` 类。

## 主要类与结构体

### AppDelegate

```objective-c
@interface AppDelegate : NSObject<NSApplicationDelegate, NSWindowDelegate>
@property (nonatomic, assign) BOOL done;
@end
```

**作用**：AppDelegate 是一个 Objective-C 类，实现了 NSApplicationDelegate 协议，用于处理应用程序生命周期事件。

**主要成员**：
- `done`：BOOL 类型的属性，标记应用程序是否应该退出

**关键方法**：
- `init`：初始化方法，将 done 标志设置为 FALSE
- `applicationShouldTerminate:`：当用户尝试退出应用程序时被调用，设置 done 标志为 TRUE 并返回 NSTerminateCancel（阻止立即终止）
- `applicationDidFinishLaunching:`：应用程序启动完成后调用，执行 `[NSApp stop:nil]` 停止默认的运行循环

该设计允许应用程序接管事件循环的控制权，而不是使用 Cocoa 的默认运行循环。

## 公共 API 函数

### main

```cpp
int main(int argc, char * argv[])
```

**功能**：程序的主入口点，负责初始化 macOS 应用程序环境并运行主事件循环。

**参数**：
- `argc`：命令行参数数量
- `argv`：命令行参数数组

**返回值**：
- `EXIT_SUCCESS`：正常退出
- `EXIT_FAILURE`：在不支持的 macOS 版本上退出

**执行流程**：

1. **版本检查**：检查 macOS 版本是否支持 Core Profile 3.2（OS X 10.7+）
2. **自动释放池初始化**：创建 NSAutoreleasePool 管理内存
3. **NSApplication 初始化**：创建共享的 NSApplication 实例
4. **应用程序策略设置**：设置为 NSApplicationActivationPolicyRegular（显示在 Dock 中）
5. **菜单栏创建**：
   - 创建主菜单栏
   - 添加 "Apple" 菜单
   - 添加 "Quit" 菜单项（快捷键 Cmd+Q）
6. **委托设置**：创建并设置 AppDelegate 实例
7. **Skia 应用程序创建**：调用 `Application::Create()` 创建跨平台应用程序对象
8. **初始启动循环**：调用 `[NSApp run]` 直到启动完成
9. **主事件循环**：
   - 从 NSApp 获取并处理所有待处理事件
   - 周期性刷新自动释放池
   - 调用 `Window_mac::PaintWindows()` 处理窗口重绘
   - 调用 `app->onIdle()` 处理空闲任务
10. **清理**：释放所有 Objective-C 对象并删除应用程序实例

## 内部实现细节

### 事件循环机制

该文件实现了一个自定义的事件循环，而不是使用 Cocoa 的标准 `[NSApp run]`：

```objective-c
while (![appDelegate done]) {
    NSEvent* event;
    do {
        event = [NSApp nextEventMatchingMask:NSEventMaskAny
                                   untilDate:[NSDate distantPast]
                                      inMode:NSDefaultRunLoopMode
                                     dequeue:YES];
        [NSApp sendEvent:event];
    } while (event != nil);

    // 处理窗口重绘和空闲任务
    Window_mac::PaintWindows();
    app->onIdle();
}
```

**关键设计点**：
- 使用 `[NSDate distantPast]` 作为超时时间，确保不阻塞等待事件
- 内部 do-while 循环处理所有待处理事件
- 每次事件批次处理完成后，显式调用窗口绘制和空闲处理
- 自动释放池在每次迭代后刷新，避免内存累积

### 窗口重绘策略

```objective-c
// Rather than depending on a Mac event to drive this, we treat our window
// invalidation flag as a separate event stream. Window::onPaint() will clear
// the invalidation flag, effectively removing it from the stream.
Window_mac::PaintWindows();
```

Skia 的窗口失效（invalidation）被视为独立的事件流，不依赖于 macOS 的标准重绘事件。这允许应用程序更灵活地控制渲染时机。

### 应用程序终止处理

```objective-c
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    _done = TRUE;
    return NSTerminateCancel;
}
```

当用户尝试退出时，设置 `done` 标志但返回 `NSTerminateCancel`，防止 Cocoa 立即终止应用程序。这允许主循环正常退出并执行清理操作。

### 内存管理

文件使用手动引用计数（MRC）而非 ARC：
- 显式调用 `alloc`、`init`、`release`
- 在事件循环中周期性刷新自动释放池
- 退出前释放所有创建的对象

## 依赖关系

**Cocoa 框架依赖**：
- `Cocoa/Cocoa.h`：macOS 应用程序框架
  - NSApplication：应用程序主类
  - NSMenu、NSMenuItem：菜单系统
  - NSEvent：事件处理
  - NSAutoreleasePool：内存管理

**Skia 内部依赖**：
- `tools/sk_app/Application.h`：跨平台应用程序抽象类
- `tools/sk_app/mac/Window_mac.h`：macOS 窗口实现

**依赖图**：
```
main_mac.mm
  ├── Cocoa 框架（macOS 系统框架）
  ├── Application（Skia 应用程序抽象）
  └── Window_mac（Skia macOS 窗口实现）
```

## 设计模式与设计决策

### 委托模式（Delegate Pattern）

使用 `AppDelegate` 类实现 `NSApplicationDelegate` 协议，将应用程序生命周期事件的处理权委托给自定义对象。

### 自定义事件循环

**决策理由**：
- Skia 需要精确控制渲染时机
- 需要集成自己的窗口失效机制
- 支持跨平台的一致事件处理模型

**实现方式**：
- 使用 `[NSApp run]` 仅用于初始启动
- 调用 `[NSApp stop:nil]` 后接管控制权
- 手动从事件队列中提取和分发事件

### 平台抽象层桥接

将 macOS 特定的 Cocoa API 与 Skia 的跨平台 `Application` 接口桥接：
```cpp
Application* app = Application::Create(argc, argv, nullptr);
```

这允许上层代码使用统一的接口，而不需要关心底层平台细节。

### 最小化菜单设计

仅创建最基本的菜单（Apple 菜单 + Quit 项），将更多的 UI 控制权留给 Skia 应用程序层。

## 性能考量

### 事件循环效率

```objective-c
event = [NSApp nextEventMatchingMask:NSEventMaskAny
                           untilDate:[NSDate distantPast]
                              inMode:NSDefaultRunLoopMode
                             dequeue:YES];
```

使用 `[NSDate distantPast]` 确保非阻塞轮询，避免在无事件时浪费 CPU 时间。但这也意味着主循环会持续运行，需要在 `app->onIdle()` 中实现适当的节流。

### 自动释放池管理

```objective-c
[pool drain];
pool = [[NSAutoreleasePool alloc] init];
```

在每次事件循环迭代后刷新自动释放池，防止临时对象累积导致内存压力。这对于长时间运行的图形应用程序尤其重要。

### 窗口重绘优化

`Window_mac::PaintWindows()` 使用失效标志机制，仅重绘需要更新的窗口，避免不必要的渲染开销。

### 版本兼容性检查

```cpp
#if MAC_OS_X_VERSION_MAX_ALLOWED < 1070
    return EXIT_FAILURE;
#endif
```

在编译时和运行时检查 macOS 版本，确保只在支持现代 OpenGL 的系统上运行。

## 相关文件

- `tools/sk_app/Application.h`：跨平台应用程序接口定义
- `tools/sk_app/mac/Window_mac.h`：macOS 窗口实现
- `tools/sk_app/unix/main_unix.cpp`：Unix/Linux 平台的对应实现
- `tools/sk_app/win/main_win.cpp`：Windows 平台的对应实现
- `tools/sk_app/android/main_android.cpp`：Android 平台的对应实现

这些文件共同构成了 Skia 应用程序框架的平台抽象层，允许相同的上层代码在不同操作系统上运行。
