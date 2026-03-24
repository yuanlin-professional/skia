# GLWindowContext_win - Windows OpenGL 窗口上下文

> 源文件: `tools/window/win/GLWindowContext_win.cpp`

## 概述

`GLWindowContext_win` 实现了 Windows 平台上的 OpenGL（通过 WGL）窗口上下文。它使用 Windows 特有的 WGL（Windows GL）扩展来创建和管理 OpenGL 渲染上下文，支持 MSAA 多重采样、VSync 控制和 RenderDoc 兼容性检测。注意该实现在 ARM64 架构上被禁用。

## 架构位置

- 继承自 `skwindow::internal::GLWindowContext`
- 由工厂函数 `MakeGLForWin` 创建
- 使用 Skia 自定义的 WGL 封装（`SkWGL.h`）
- 在 ARM64 架构上返回空实现

## 主要类与结构体

### `GLWindowContext_win`（匿名命名空间）
- 继承自 `GLWindowContext`
- 成员变量：
  - `fHWND` (`HWND`) - 窗口句柄
  - `fHGLRC` (`HGLRC`) - OpenGL 渲染上下文句柄

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGLForWin(HWND, unique_ptr<const DisplayParams>)` | 工厂函数 |

## 内部实现细节

### ARM64 处理
在 `_M_ARM64` 定义时，`MakeGLForWin` 直接返回 `nullptr` 并记录错误日志，因为 Windows ARM64 不支持 OpenGL。

### 上下文初始化 (`onInitializeContext`)
1. 使用 `SkCreateWGLContext` 创建兼容性 profile 的 WGL 上下文
2. 检查 `WGL_EXT_swap_control` 扩展，根据 `disableVsync` 参数设置交换间隔
3. **RenderDoc 检测**: 如果检测到 `GL_EXT_debug_tool` 扩展（RenderDoc 注入），则重新创建 Core Profile 上下文以兼容 RenderDoc
4. 设置初始 GL 状态（清除模板缓冲区和颜色缓冲区）
5. 从 `DescribePixelFormat` 获取实际的模板位数
6. 从 `WGL_ARB_multisample` 扩展查询实际的 MSAA 采样数
7. 返回 `GrGLMakeNativeInterface()` 提供 GL 接口

### 帧交换
`onSwapBuffers()` 通过标准的 `SwapBuffers(dc)` 完成双缓冲交换。

### 资源清理
`onDestroyContext()` 调用 `wglDeleteContext` 销毁 GL 上下文。

## 依赖关系

- `include/gpu/ganesh/gl/GrGLInterface.h` - Ganesh GL 接口
- `tools/ganesh/gl/win/SkWGL.h` - Skia WGL 封装
- `tools/window/GLWindowContext.h` - GL 窗口上下文基类
- `<Windows.h>`, `<GL/gl.h>` - Win32 和 OpenGL API

## 设计模式与设计决策

- **条件编译**: ARM64 上完全禁用 OpenGL 支持
- **RenderDoc 兼容性**: 自动检测 RenderDoc 并切换到 Core Profile，提升调试体验
- **VSync 控制**: 支持通过显示参数禁用垂直同步
- **优雅降级**: 创建失败时记录详细错误信息

## 性能考量

- MSAA 采样数从 WGL 扩展查询，确保使用硬件实际支持的值
- VSync 可通过参数禁用以获得更高帧率（测试用途）
- RenderDoc 检测会导致额外一次上下文创建/销毁，仅在调试工具附加时发生
- `SwapBuffers` 的行为取决于驱动程序和 VSync 设置

## 相关文件

- `tools/window/GLWindowContext.h` - 跨平台 GL 基类
- `tools/ganesh/gl/win/SkWGL.h` - WGL 封装
- `tools/window/win/ANGLEWindowContext_win.cpp` - ANGLE 替代方案
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
