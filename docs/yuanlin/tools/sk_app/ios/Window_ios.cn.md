# Window_ios - iOS 平台窗口实现

> 源文件:
> - [tools/sk_app/ios/Window_ios.h](../../../../tools/sk_app/ios/Window_ios.h)
> - [tools/sk_app/ios/Window_ios.mm](../../../../tools/sk_app/ios/Window_ios.mm)

## 概述

Window_ios 是 sk_app::Window 在 iOS 平台的实现，封装了 UIKit 窗口管理和触摸手势输入处理。使用单窗口模式（全局唯一实例），支持 Metal、OpenGL 和光栅渲染后端。通过 Objective-C 的 UIGestureRecognizer 系统处理拖拽、点击、缩放和滑动手势。

## 架构位置

位于 `tools/sk_app/ios/` 目录下，是 sk_app 跨平台窗口抽象在 iOS 上的具体实现。通过 `Windows::CreateNativeWindow()` 工厂方法创建。

## 主要类与结构体

### `Window_ios`
继承 `sk_app::Window`，管理 UIWindow 生命周期。
- `fWindow` - UIWindow 实例
- `gWindow` - 全局唯一窗口指针（静态）

### `MainView`（Objective-C）
UIView 子类，处理手势识别并转发到 Window_ios。
- 支持 Pan（拖拽）、Tap（点击）、Pinch（缩放）、Swipe（左右滑动）手势

### `WindowViewController`（Objective-C）
UIViewController 子类，跟踪视图控制器事件。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `initWindow()` | 初始化 UIWindow 和视图控制器 |
| `attach(BackendType)` | 绑定渲染后端（Metal/GL/Raster） |
| `PaintWindow()` | 静态方法，触发主窗口重绘 |
| `MainWindow()` | 获取全局唯一窗口 |

## 内部实现细节

- **单窗口模式**：iOS 使用静态 `gWindow` 指针确保只有一个窗口实例。
- **手势优先级**：Pan 手势要求 Swipe 手势失败后才识别（`requireGestureRecognizerToFail`）。
- **后端绑定**：通过 `IOSWindowInfo` 结构传递窗口和视图控制器信息给窗口上下文工厂。
- **非 ARC**：显式标记 `#error` 禁止 ARC 编译，手动管理 Objective-C 对象生命周期。

## 依赖关系

- **UIKit**：UIWindow、UIView、UIGestureRecognizer 系列
- **sk_app**：Window 基类
- **窗口上下文**：WindowContextFactory_ios（Metal/GL/Raster 工厂）

## 设计模式与设计决策

- **全局单例**：iOS 应用通常只有一个主窗口。
- **手势委托**：通过 Objective-C 手势识别器自然映射到 Skia 的输入事件模型。

## 性能考量

- 手势识别器由系统优化管理。
- 渲染通过 `onPaint()` 统一调度。

## 相关文件

- `tools/sk_app/Window.h` - 窗口抽象基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 窗口上下文工厂
