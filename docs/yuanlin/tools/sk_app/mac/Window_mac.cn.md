# Window_mac - macOS 平台窗口实现

> 源文件:
> - [tools/sk_app/mac/Window_mac.h](../../../../tools/sk_app/mac/Window_mac.h)
> - [tools/sk_app/mac/Window_mac.mm](../../../../tools/sk_app/mac/Window_mac.mm)

## 概述

Window_mac 是 sk_app::Window 在 macOS 平台的实现，封装了 Cocoa NSWindow 管理和事件处理。支持多窗口（通过 `gWindowMap` 哈希表管理）、HiDPI 缩放、完整的键盘/鼠标/滚轮输入处理。支持 ANGLE、OpenGL、Metal、Graphite Metal、Graphite Dawn 等多种渲染后端。

## 架构位置

位于 `tools/sk_app/mac/` 目录下，是 sk_app 跨平台窗口抽象在 macOS 上的具体实现。是 Skia Viewer 等 macOS 桌面工具的窗口基础。

## 主要类与结构体

### `Window_mac`
继承 `sk_app::Window`，管理 NSWindow 生命周期。
- `fWindow` - NSWindow 实例
- `fWindowNumber` - 窗口编号，用作哈希表键
- `gWindowMap` - 全局窗口哈希表（SkTDynamicHash）

### `WindowDelegate`（Objective-C）
NSWindowDelegate 实现，处理窗口大小变化、屏幕切换和关闭事件。

### `MainView`（Objective-C）
NSView 子类，处理键盘、鼠标、滚轮事件。
- `fTrackingArea` - NSTrackingArea 限制事件捕获范围
- `fLastModifiers` - 修饰键状态追踪

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `initWindow()` | 创建 1280x960 的 Cocoa 窗口 |
| `setTitle(title)` | 设置窗口标题 |
| `show()` | 显示窗口并激活应用 |
| `attach(BackendType)` | 绑定渲染后端 |
| `scaleFactor()` | 获取 HiDPI 缩放因子 |
| `PaintWindows()` | 重绘所有需要更新的窗口 |
| `closeWindow()` | 关闭窗口，最后一个窗口关闭时终止应用 |

## 内部实现细节

- **键码映射**：`get_key()` 使用 Carbon Virtual Key 到 skui::Key 的查找表。
- **修饰键追踪**：`updateModifierKeys` 跟踪修饰键变化并合成按下/释放事件。
- **Key Equivalent 处理**：`performKeyEquivalent` 返回 NO 让系统转发为 keyDown，并延迟 0.1 秒合成 keyUp。
- **坐标转换**：鼠标事件将 NSWindow 坐标（左下角原点）转换为 Skia 坐标（左上角原点），并应用 Retina 缩放。
- **多窗口管理**：使用 `SkTDynamicHash` 按窗口编号索引。

## 依赖关系

- **Cocoa/AppKit**：NSWindow、NSView、NSEvent、NSTrackingArea
- **Carbon**：Virtual Key 码常量
- **sk_app**：Window 基类
- **窗口上下文**：各后端 WindowContext 工厂

## 设计模式与设计决策

- **多窗口支持**：通过哈希表管理多个窗口实例。
- **修饰键合成**：独立追踪修饰键状态，合成按下/释放事件。
- **HiDPI 感知**：所有坐标乘以 `backingScaleFactor`。

## 性能考量

- `PaintWindows()` 仅重绘内容失效的窗口。
- NSTrackingArea 限制鼠标事件捕获范围，减少不必要的事件处理。

## 相关文件

- `tools/sk_app/Window.h` - 窗口抽象基类
- `tools/window/mac/` - macOS 窗口上下文工厂
- `tools/skui/ModifierKey.h` - 修饰键定义
