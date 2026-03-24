# MacWindowInfo - macOS 窗口信息结构体

> 源文件: `tools/window/mac/MacWindowInfo.h`

## 概述

此头文件定义了 macOS 平台上的窗口信息结构体 `MacWindowInfo` 和一个获取 Retina 缩放因子的工具函数 `GetBackingScaleFactor`。这些是 macOS 窗口上下文工厂函数的基础参数类型，用于在窗口创建时传递必要的 NSView 信息。

## 架构位置

- 位于 `skwindow` 命名空间
- 被 macOS 平台的各窗口上下文工厂函数使用
- 包含编译时平台检查（排除 iOS）

## 主要类与结构体

### `MacWindowInfo`
- `fMainView` (`NSView*`) - macOS 主视图指针

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GetBackingScaleFactor(NSView*)` | 获取 Retina 显示屏的缩放因子 |

## 内部实现细节

### 平台保护
使用 `#if defined(SK_BUILD_FOR_IOS)` + `#error` 确保此头文件不会在 iOS 上使用。

### 缩放因子获取
`GetBackingScaleFactor` 通过以下优先级获取缩放因子：
1. 优先使用视图所在窗口的屏幕 (`view.window.screen`)
2. 回退到主屏幕 (`[NSScreen mainScreen]`)
3. 返回 `backingScaleFactor` 属性（Retina 屏幕通常为 2.0）

## 依赖关系

- `include/core/SkTypes.h` - 基础类型
- `<Cocoa/Cocoa.h>` - NSView, NSScreen

## 设计模式与设计决策

- **简单数据传输**: 使用 POD 结构体传递窗口信息
- **优雅回退**: 缩放因子获取使用空合运算符 (`?:`) 处理窗口不可用的情况
- **编译时安全**: 通过 `#error` 防止跨平台误用

## 性能考量

静态内联函数，开销可忽略。缩放因子查询涉及 Objective-C 消息传递但不涉及昂贵操作。

## 相关文件

- `tools/window/mac/MacWindowGLUtils.h` - macOS GL 工具
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 版本（使用 `IOSWindowInfo`）
