# ANGLEWindowContext_win - Windows ANGLE 窗口上下文

> 源文件: `tools/window/win/ANGLEWindowContext_win.cpp`

## 概述

`ANGLEWindowContext_win` 实现了 Windows 平台上通过 ANGLE（Almost Native Graphics Layer Engine）库使用 OpenGL ES 的窗口上下文。ANGLE 将 OpenGL ES API 调用转译为 Direct3D 11 调用，使得 Skia 能够在 Windows 上通过 D3D11 后端使用 OpenGL ES。该实现继承自跨平台的 `ANGLEWindowContext` 基类。

## 架构位置

- 继承自 `skwindow::internal::ANGLEWindowContext`
- 由工厂函数 `MakeANGLEForWin` 创建
- 位于匿名命名空间中，作为内部实现
- 是 ANGLE 的 Windows 平台特化

## 主要类与结构体

### `ANGLEWindowContext_win`（匿名命名空间）
- 继承自 `ANGLEWindowContext`
- 成员变量：
  - `fHWND` (`HWND`) - Windows 窗口句柄
  - `fHDC` (`HDC`) - 设备上下文句柄

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeANGLEForWin(HWND, unique_ptr<const DisplayParams>)` | 工厂函数 |

## 内部实现细节

### EGL 显示获取
- `onGetEGLDisplay()` 使用 `EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE` 属性创建 ANGLE 平台显示
- 通过 `eglGetPlatformDisplayEXT` 获取基于 D3D11 的 EGL 显示

### 窗口信息获取
- `onGetNativeWindow()` 返回 HWND
- `onGetSize()` 通过 `GetClientRect` 获取客户区尺寸
- `onGetStencilBits()` 使用 `DescribePixelFormat` 获取模板缓冲区位数

### 初始化流程
构造函数中获取 HDC 后调用基类的 `initializeContext()` 完成 EGL 初始化。

## 依赖关系

- `tools/window/ANGLEWindowContext.h` - ANGLE 基类
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
- Windows API: `GetDC`, `GetClientRect`, `DescribePixelFormat`, `GetPixelFormat`

## 设计模式与设计决策

- **模板方法模式**: 基类定义初始化框架，子类实现平台特定的回调方法
- **硬编码 D3D11**: 当前仅支持 D3D11 后端 ANGLE（`EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE`）
- **工厂模式**: 统一的创建接口，验证后返回

## 性能考量

- ANGLE 的 D3D11 转译层会引入一定的性能开销，但通常比纯软件渲染更快
- EGL 初始化是一次性开销
- 适合需要 OpenGL ES 兼容性测试的场景

## 相关文件

- `tools/window/ANGLEWindowContext.h` - 跨平台 ANGLE 基类
- `tools/window/win/GLWindowContext_win.cpp` - 原生 OpenGL 实现
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
