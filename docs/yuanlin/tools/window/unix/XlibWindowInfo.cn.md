# XlibWindowInfo - X11/Xlib 窗口信息结构体

> 源文件: `tools/window/unix/XlibWindowInfo.h`

## 概述

此头文件定义了 Linux/Unix 平台上基于 X11 窗口系统的窗口信息结构体 `XlibWindowInfo`。它封装了创建图形渲染上下文所需的所有 X11 和 GLX 相关信息，包括 Display 连接、窗口句柄、帧缓冲配置和可视化信息。

## 架构位置

- 位于 `skwindow` 命名空间
- 被 Unix 平台的各窗口上下文工厂函数使用
- 桥接 X11 窗口系统和 Skia 渲染上下文

## 主要类与结构体

### `XlibWindowInfo`
| 成员 | 类型 | 说明 |
|------|------|------|
| `fDisplay` | `Display*` | X11 显示连接 |
| `fWindow` | `XWindow` | X11 窗口句柄 |
| `fFBConfig` | `GLXFBConfig*` | GLX 帧缓冲配置指针 |
| `fVisualInfo` | `XVisualInfo*` | X11 可视化信息 |
| `fWidth` | `int` | 窗口宽度 |
| `fHeight` | `int` | 窗口高度 |

## 公共 API 函数

无公共函数，仅包含数据结构定义和类型别名。

## 内部实现细节

### 类型别名
- `GLXFBConfig` - 定义为 `__GLXFBConfigRec*` 的别名，通过前置声明避免引入 GLX 头文件
- `XWindow` - 定义为 `Window` 的别名，避免与可能的命名冲突

### 头文件依赖
仅包含最小的 X11 头文件：
- `X11/X.h` - 提供 `Window` 类型（通常为 `unsigned long`）
- `X11/Xutil.h` - 提供 `XVisualInfo` 结构体

## 依赖关系

- `<X11/X.h>` - X11 基础类型
- `<X11/Xutil.h>` - X 工具类型
- GLX（通过前置声明）

## 设计模式与设计决策

- **最小依赖**: 通过前置声明 `__GLXFBConfigRec` 避免引入完整的 GLX 头文件
- **类型别名**: `XWindow` 别名避免了 `Window` 这个过于通用的类型名称在 C++ 中的潜在冲突
- **POD 结构体**: 简单的数据传输对象，不包含逻辑

## 性能考量

纯数据结构定义，不涉及运行时性能问题。

## 相关文件

- `tools/window/mac/MacWindowInfo.h` - macOS 对应结构体
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 对应的 `IOSWindowInfo`
- `tools/window/unix/GLWindowContext_unix.cpp` - 使用此结构体的 Unix GL 实现
