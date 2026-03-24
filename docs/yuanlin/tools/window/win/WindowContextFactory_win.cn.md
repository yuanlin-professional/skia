# WindowContextFactory_win - Windows 窗口上下文工厂声明

> 源文件: `tools/window/win/WindowContextFactory_win.h`

## 概述

此头文件声明了 Windows 平台上所有可用渲染后端的窗口上下文工厂函数。它作为 Windows 窗口上下文创建的统一入口点，通过条件编译宏（如 `SK_VULKAN`、`SK_GL`、`SK_ANGLE`、`SK_DIRECT3D`、`SK_DAWN`）控制各后端的可用性。所有工厂函数接受 `HWND` 窗口句柄和 `DisplayParams` 显示参数。

## 架构位置

- 属于 `skwindow` 命名空间
- 位于 Windows 平台窗口工具层的顶层接口
- 被 `sk_app::Window_win` 等窗口管理类调用
- 各工厂函数的实现分散在对应的 `.cpp` 文件中

## 主要类与结构体

无新类定义，仅包含前置声明：
- `WindowContext` - 所有窗口上下文的基类
- `DisplayParams` - 显示参数配置

## 公共 API 函数

| 函数 | 条件 | 说明 |
|------|------|------|
| `MakeVulkanForWin` | `SK_VULKAN` | 创建 Ganesh Vulkan 窗口上下文 |
| `MakeGraphiteVulkanForWin` | `SK_VULKAN && SK_GRAPHITE` | 创建 Graphite Vulkan 窗口上下文 |
| `MakeGLForWin` | `SK_GL` | 创建 OpenGL 窗口上下文 |
| `MakeANGLEForWin` | `SK_ANGLE` | 创建 ANGLE (OpenGL ES via D3D) 窗口上下文 |
| `MakeD3D12ForWin` | `SK_DIRECT3D` | 创建 Direct3D 12 窗口上下文 |
| `MakeGraphiteDawnForWin` | `SK_DAWN && SK_GRAPHITE` | 创建 Graphite Dawn 窗口上下文 |
| `MakeRasterForWin` | 始终可用 | 创建 CPU 光栅化窗口上下文 |

## 内部实现细节

- `MakeGraphiteDawnForWin` 额外接受 `BackendType` 参数，支持在 Dawn D3D11 和 D3D12 后端之间选择
- `MakeRasterForWin` 不受条件编译保护，始终可用作为后备选项
- 所有函数签名统一：接受 `HWND` 和 `unique_ptr<const DisplayParams>`，返回 `unique_ptr<WindowContext>`

## 依赖关系

- `tools/sk_app/Window.h` - `BackendType` 枚举
- `<Windows.h>` - HWND 类型
- `<memory>` - `std::unique_ptr`

## 设计模式与设计决策

- **抽象工厂模式**: 统一的工厂接口创建不同后端的窗口上下文
- **条件编译策略**: 仅在对应 GPU 后端启用时才声明工厂函数
- **统一接口**: 所有工厂函数接受相同的参数类型，便于在运行时切换后端
- **光栅化保底**: `MakeRasterForWin` 无条件可用，确保始终有可用的渲染路径

## 性能考量

此文件仅包含声明，不涉及运行时性能。后端选择在应用启动时一次性决定。

## 相关文件

- `tools/window/win/GLWindowContext_win.cpp` - OpenGL 实现
- `tools/window/win/VulkanWindowContext_win.cpp` - Vulkan 实现
- `tools/window/win/D3D12WindowContext_win.cpp` - D3D12 实现
- `tools/window/win/ANGLEWindowContext_win.cpp` - ANGLE 实现
- `tools/window/win/GraphiteDawnWindowContext_win.cpp` - Dawn 实现
- `tools/window/win/RasterWindowContext_win.cpp` - 光栅化实现
