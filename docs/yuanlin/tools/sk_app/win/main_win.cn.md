# main_win - Windows 平台应用程序入口

> 源文件: `tools/sk_app/win/main_win.cpp`

## 概述

main_win.cpp 是 Skia sk_app 框架在 Windows 平台上的应用程序入口点实现。它同时支持 GUI 子系统（通过 `_tWinMain`）和控制台子系统（通过 `main`），负责解析命令行参数、创建 Application 实例，并运行 Windows 消息循环。

## 架构位置

位于 `tools/sk_app/win/` 目录，属于 sk_app 框架的平台适配层。它是 Windows 上所有 sk_app 应用程序的启动代码。

## 主要类与结构体

本文件无类定义，仅包含入口函数和辅助函数。

## 公共 API 函数

### `_tWinMain`
Windows GUI 应用程序入口，将 `lpCmdLine` 转换为 `argc/argv` 格式后调用 `main_common`。

### `main`
Windows 控制台应用程序入口，直接调用 `main_common`。

## 内部实现细节

- **`tchar_to_utf8`**: 辅助函数，将 TCHAR（可能是 Unicode 的 wchar_t）转换为 UTF-8 编码的 char 字符串
- **`main_common`**: 核心逻辑 -- 创建 Application 实例，运行 Windows 消息循环
- **消息循环优化**: 使用 `PeekMessage` 非阻塞消息处理，在无消息时调用 `app->onIdle()`
- **WM_PAINT 特殊处理**: 确保每个 WM_PAINT 消息之前至少调用一次 `onIdle()`，防止鼠标事件淹没消息队列而阻止动画更新

## 依赖关系

- `<windows.h>`, `<tchar.h>` - Windows API
- `include/core/SkTypes.h` - Skia 类型
- `include/private/base/SkMalloc.h` - 内存分配
- `tools/sk_app/Application.h` - Application 基类
- `tools/sk_app/win/Window_win.h` - Windows 窗口实现

## 设计模式与设计决策

- **双入口支持**: 同时定义 `_tWinMain` 和 `main`，支持两种 Windows 子系统类型
- **UTF-8 统一**: 将 Windows 宽字符命令行参数统一转换为 UTF-8，与 Skia 内部编码一致
- **空闲驱动渲染**: 利用消息循环空闲时间驱动帧更新，而非使用定时器

## 性能考量

- `PeekMessage` 的非阻塞方式确保在无用户输入时仍能持续渲染
- `idled` 标志避免在 WM_PAINT 处理期间重复调用 `onIdle()`

## 相关文件

- `tools/sk_app/Application.h` - Application 基类接口
- `tools/sk_app/win/Window_win.h` - Windows 窗口实现
