# RasterWindowContext - 光栅化窗口上下文基类

> 源文件: `tools/window/RasterWindowContext.h`

## 概述

`RasterWindowContext` 是 Skia 窗口工具库中用于纯 CPU 软件光栅化渲染的窗口上下文基类。它继承自 `WindowContext`，为不使用 GPU 加速的平台特定光栅化窗口上下文提供了公共基类。该类位于 `skwindow::internal` 命名空间中，表明它是一个内部实现类，不对外暴露。

## 架构位置

该类位于 Skia 窗口工具层的抽象层级中：
- 继承自 `WindowContext`（所有窗口上下文的基类）
- 作为各平台光栅化窗口上下文的直接父类（如 `RasterWindowContext_win`、`RasterWindowContext_ios` 等）
- 与 GPU 窗口上下文（如 `GLWindowContext`、`VulkanWindowContext`）属于同级关系

## 主要类与结构体

### `RasterWindowContext`
- 继承自 `WindowContext`
- 构造函数接受 `std::unique_ptr<const DisplayParams>` 参数并转发给基类
- 重写 `isGpuContext()` 方法始终返回 `false`，标识此为非 GPU 上下文

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `RasterWindowContext(std::unique_ptr<const DisplayParams>)` | 构造函数，转发显示参数到基类 |
| `isGpuContext()` | 返回 `false`，表示这是 CPU 光栅化上下文 |

## 内部实现细节

该类实现非常简单，仅包含：
1. 一个将参数转发给基类的构造函数
2. 一个覆盖 `isGpuContext()` 返回 `false` 的 protected 方法

实际的光栅化渲染逻辑（如像素缓冲区管理、帧交换等）由各平台特定的子类实现。

## 依赖关系

- `tools/window/WindowContext.h` - 基类定义
- 标准库 `<memory>` - 通过 `std::unique_ptr` 间接使用

## 设计模式与设计决策

- **模板方法模式**: 基类定义接口框架，具体平台实现由子类完成
- **内部命名空间**: 使用 `skwindow::internal` 表明不应被外部直接使用
- **最小化设计**: 基类仅提供共性（非 GPU 标识），将平台差异完全委托给子类
- **不可变显示参数**: 通过 `const DisplayParams` 的 `unique_ptr` 确保参数不被意外修改

## 性能考量

光栅化渲染完全在 CPU 上执行，不涉及 GPU 资源管理开销。适用于不需要 GPU 加速或 GPU 不可用的场景。各平台子类需自行管理像素缓冲区和帧呈现。

## 相关文件

- `tools/window/WindowContext.h` - 基类定义
- `tools/window/win/RasterWindowContext_win.cpp` - Windows 平台实现
- `tools/window/ios/RasterWindowContext_ios.mm` - iOS 平台实现
- `tools/window/DisplayParams.h` - 显示参数定义
