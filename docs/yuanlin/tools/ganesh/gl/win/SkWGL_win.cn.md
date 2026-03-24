# SkWGL_win.cpp - Windows WGL 扩展实现

> 源文件: `tools/ganesh/gl/win/SkWGL_win.cpp`

## 概述

`SkWGL_win.cpp` 提供了 Windows 平台上 WGL (Windows GL) 扩展的完整实现。它封装了 WGL 扩展的函数指针获取、像素格式选择、OpenGL 上下文创建以及 Pbuffer 上下文管理等功能,是 Skia 在 Windows 上创建 OpenGL 渲染上下文的核心基础设施。

## 架构位置

位于 Skia 测试工具链的 Windows GL 平台层。该文件是 `SkWGL.h` 中声明的接口的实现,被 `CreatePlatformGLTestContext_win.cpp` 和其他 Windows OpenGL 组件使用。

## 主要类与结构体

- **`SkWGLExtensions`**: WGL 扩展函数的封装类,管理所有 WGL ARB/EXT 扩展函数指针
- **`PixelFormat`**: 内部结构体,用于像素格式排序和选择
- **`SkWGLPbufferContext`**: Pbuffer 上下文封装,继承自 SkRefCnt

## 公共 API 函数

- **`SkWGLExtensions::hasExtension()`**: 检查指定 WGL 扩展是否可用
- **`SkWGLExtensions::selectFormat()`**: 从候选格式中选择最佳像素格式
- **`SkCreateWGLContext()`**: 创建 WGL 渲染上下文(支持 MSAA、深色、GL ES)
- **`SkWGLPbufferContext::Create()`**: 创建离屏 Pbuffer 渲染上下文

## 内部实现细节

WGL 扩展的初始化需要先创建一个临时 GL 上下文来获取扩展函数指针,这是一个经典的鸡生蛋问题。实现通过 `create_temp_window()` 创建临时窗口和 GL 上下文,用 `SkOnce` 保证函数指针仅初始化一次。像素格式选择使用 `SkTQSort` 和 `SkTSearch` 进行排序和二分查找。

## 依赖关系

- Windows API: `wglGetProcAddress`, `CreateWindow`, `SetPixelFormat` 等
- `SkOnce`: 线程安全的一次性初始化
- `SkTDArray`, `SkTSearch`, `SkTSort`: Skia 内部数据结构和算法

## 设计模式与设计决策

1. **单例缓存**: 函数指针通过 `SkOnce` 缓存为静态变量,整个进程生命周期内复用
2. **优雅降级**: MSAA 格式不可用时自动回退到非 MSAA 格式
3. **上下文类型协商**: 支持 Core Profile、Compatibility Profile 和 GL ES Profile 的优先级选择
4. **Pbuffer 偏好**: 优先使用单缓冲 Pbuffer,在窗口上下文之前尝试

## 性能考量

- 函数指针初始化仅执行一次,后续调用直接使用缓存的指针
- Pbuffer 像素格式缓存避免重复查询
- 临时窗口在初始化完成后立即销毁,不占用持续资源

## 相关文件

- `tools/ganesh/gl/win/SkWGL.h`: 头文件声明
- `tools/ganesh/gl/win/CreatePlatformGLTestContext_win.cpp`: 使用此文件创建测试上下文
