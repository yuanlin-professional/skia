# Window_unix - X11/Linux 平台窗口实现

> 源文件:
> - [tools/sk_app/unix/Window_unix.h](../../../../tools/sk_app/unix/Window_unix.h)
> - [tools/sk_app/unix/Window_unix.cpp](../../../../tools/sk_app/unix/Window_unix.cpp)

## 概述

Window_unix 是 sk_app::Window 在 Linux/X11 平台的实现，封装了 Xlib 窗口管理、GLX 视觉配置选择、X11 事件处理和剪贴板交互。支持 OpenGL（通过 GLX）、Vulkan、Graphite Vulkan、Graphite Dawn 和光栅后端。提供完整的键盘、鼠标、滚轮输入处理和剪贴板读写。

## 架构位置

位于 `tools/sk_app/unix/` 目录下，是 sk_app 在 Linux 平台的具体实现。是 Skia Viewer 在 Linux 上的窗口基础。

## 主要类与结构体

### `Window_unix`
继承 `sk_app::Window`，管理 X11 窗口和 GLX 配置。
- `fDisplay` - X11 Display 连接
- `fWindow` - X11 Window（XWindow）
- `fGC` - 图形上下文
- `fFBConfig` / `fVisualInfo` - GLX 帧缓冲配置和视觉信息
- `fMSAASampleCount` - MSAA 采样数
- `gWindowMap` - 全局窗口哈希表

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `initWindow(Display*)` | 初始化 X11 窗口，选择 GLX 视觉配置 |
| `setTitle(title)` | 设置窗口标题（XSetWMName） |
| `show()` | 映射显示窗口（XMapWindow） |
| `attach(BackendType)` | 绑定渲染后端 |
| `handleEvent(XEvent)` | 处理 X11 事件 |
| `getClipboardText()` / `setClipboardText()` | 剪贴板读写 |
| `onInval()` | 发送 Expose 事件触发重绘 |
| `markPendingPaint/Resize()` / `finishPaint/Resize()` | 延迟绘制/调整大小 |

## 内部实现细节

- **GLX 配置选择**：优先使用 `glXChooseFBConfig`，回退到 `glXChooseVisual`。支持 MSAA 配置。
- **键盘映射**：使用 `XkbKeycodeToKeysym` 和 `keysym2ucs`（外部 C 函数）将 KeySym 转换为 Unicode。
- **剪贴板协议**：实现完整的 X11 Selection 协议（SelectionRequest/SelectionClear/SelectionNotify），支持 UTF8_STRING 格式。
- **Vulkan 重建**：Vulkan 后端在参数变化时需要完全重建窗口上下文（detach + attach），因为直接重初始化会崩溃。
- **WM_DELETE_WINDOW**：注册删除消息原子以处理窗口关闭。
- **延迟绘制**：通过 `fPendingPaint` / `fPendingResize` 标志在事件循环中批量处理。

## 依赖关系

- **X11**：Xlib、XKBlib、X11/Xutil、X11/Xatom
- **GLX**：GL/glx.h（GL 视觉配置）
- **sk_app**：Window 基类
- **窗口上下文**：各后端 WindowContext 工厂
- **skui**：ModifierKey、InputState

## 设计模式与设计决策

- **回退式初始化**：GLX 配置选择从最佳到最基本逐步回退。
- **延迟事件处理**：Expose 和 ConfigureNotify 事件标记为 pending，在主循环统一处理。
- **X11 Selection 协议**：完整实现剪贴板所有者/请求者两端。

## 性能考量

- `handleEvent` 在事件循环中高频调用，使用简单的 switch 分发。
- 延迟绘制避免短时间内多次重绘。
- MSAA 配置变更需要重新创建窗口。
- 剪贴板操作使用同步 `XSync`/`XNextEvent`，可能阻塞。

## 相关文件

- `tools/sk_app/Window.h` - 窗口抽象基类
- `tools/window/unix/` - Linux 窗口上下文工厂
- `tools/sk_app/unix/keysym2ucs.h` - KeySym 到 Unicode 转换
