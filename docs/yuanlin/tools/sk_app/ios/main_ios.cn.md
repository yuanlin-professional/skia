# main_ios - iOS 平台应用程序入口

> 源文件: `tools/sk_app/ios/main_ios.mm`

## 概述

main_ios.mm 是 Skia sk_app 框架在 iOS 平台上的应用程序入口点实现。它通过 Objective-C 的 `UIApplicationDelegate` 模式管理应用生命周期，使用 `CADisplayLink` 驱动渲染帧更新，并将事件分发到 sk_app 的 Application 和 Window 抽象层。

## 架构位置

位于 `tools/sk_app/ios/` 目录，属于 sk_app 框架的 iOS 平台适配层。该文件是 iOS 上所有 sk_app 应用程序的启动代码。

## 主要类与结构体

### `AppDelegate`
- 继承自 `UIResponder<UIApplicationDelegate>`
- 持有 `CADisplayLink` 和 `sk_app::Application` 实例
- 管理应用的激活/挂起/终止事件

## 公共 API 函数

### `main(int argc, char** argv)`
标准 C 入口，将参数保存到全局变量后调用 `UIApplicationMain`。

### AppDelegate 生命周期方法
- `applicationWillResignActive:` - 通知主窗口变为非活跃
- `applicationDidBecomeActive:` - 通知主窗口变为活跃
- `applicationWillTerminate:` - 清理 DisplayLink 和 Application
- `application:didFinishLaunchingWithOptions:` - 创建 Application 和 DisplayLink
- `displayLinkFired` - DisplayLink 回调，驱动窗口绘制和空闲处理

## 内部实现细节

- 使用全局变量 `gArgc/gArgv` 在 `main` 和 `AppDelegate` 之间传递命令行参数
- 文件明确禁用 ARC（`#if __has_feature(objc_arc) #error`），手动管理对象生命周期
- `CADisplayLink` 以 `NSRunLoopCommonModes` 注册，确保在滚动等模式切换时仍能触发
- 每帧先调用 `Window_ios::PaintWindow()` 再调用 `app->onIdle()`

## 依赖关系

- `QuartzCore/QuartzCore.h` - CADisplayLink
- `UIKit/UIKit.h` - iOS UI 框架
- `tools/sk_app/Application.h` - Application 基类
- `tools/sk_app/ios/Window_ios.h` - iOS 窗口实现

## 设计模式与设计决策

- **委托模式**: 遵循 iOS `UIApplicationDelegate` 标准模式管理生命周期
- **DisplayLink 驱动**: 使用 `CADisplayLink` 实现与屏幕刷新率同步的渲染循环
- **禁用 ARC**: 可能因为需要与 C++ 的 `std::unique_ptr` 精确控制生命周期

## 性能考量

- `CADisplayLink` 与硬件 VSync 同步，避免不必要的 CPU 使用
- TODO 注释提到需要更好的事件循环集成（如 `CAMetalLayer` 的绘制事件循环）

## 相关文件

- `tools/sk_app/Application.h` - Application 基类
- `tools/sk_app/ios/Window_ios.h` - iOS 窗口实现
