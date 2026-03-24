# Application - sk_app 应用程序基类

> 源文件: `tools/sk_app/Application.h`

## 概述

Application 是 Skia 示例应用程序框架 `sk_app` 的核心抽象基类。它定义了一个极简的应用程序生命周期接口，由各平台的 `main` 入口点创建和驱动。所有 sk_app 应用程序（如 Viewer）都通过继承此类来实现具体功能。

## 架构位置

该文件位于 `tools/sk_app/` 目录，是 sk_app 框架的顶层抽象。平台相关的 `main` 实现（如 `main_win.cpp`、`main_ios.mm`）负责创建 Application 实例并驱动其事件循环。

## 主要类与结构体

### `sk_app::Application`
- **静态工厂方法**: `Create(int argc, char** argv, void* platformData)` - 由具体应用实现，创建 Application 实例
- **虚析构函数**: 确保正确的多态析构
- **纯虚函数**: `onIdle()` - 空闲时回调，子类必须实现

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `static Create(argc, argv, platformData)` | 工厂方法，创建平台相关的应用实例 |
| `virtual ~Application()` | 虚析构函数 |
| `virtual void onIdle() = 0` | 每帧空闲回调，驱动渲染和动画 |

## 内部实现细节

头文件仅包含接口声明，不含实现。`Create` 方法是由下游应用程序（如 Viewer）提供的链接时多态实现。`platformData` 参数在不同平台上含义不同（如 Windows 下为 HINSTANCE，iOS 下为 nullptr）。

## 依赖关系

无直接依赖。该头文件是纯接口定义。

## 设计模式与设计决策

- **抽象工厂模式**: `Create` 静态方法作为工厂，将对象创建延迟到具体应用
- **极简接口**: 仅暴露 `onIdle` 一个纯虚函数，保持框架轻量

## 性能考量

作为纯接口类，无性能开销。实际性能取决于子类 `onIdle()` 的实现。

## 相关文件

- `tools/sk_app/win/main_win.cpp` - Windows 平台入口
- `tools/sk_app/ios/main_ios.mm` - iOS 平台入口
- `tools/sk_app/wasm/main_wasm.cpp` - WebAssembly 平台入口
