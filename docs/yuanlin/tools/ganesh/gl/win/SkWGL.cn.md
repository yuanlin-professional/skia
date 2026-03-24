# SkWGL.h - Windows WGL 扩展接口声明

> 源文件: `tools/ganesh/gl/win/SkWGL.h`

## 概述

`SkWGL.h` 定义了 Windows 平台上 WGL 扩展的 C++ 接口。它提供了 WGL 像素格式属性常量、上下文创建标志、扩展函数封装类 `SkWGLExtensions`、上下文请求类型枚举以及 Pbuffer 上下文管理类 `SkWGLPbufferContext`。

## 架构位置

作为 Skia Windows GL 工具层的头文件,定义了 WGL 交互的公共 API。被 `SkWGL_win.cpp`(实现)和 `CreatePlatformGLTestContext_win.cpp`(使用方)共同依赖。

## 主要类与结构体

- **`SkWGLExtensions`**: 封装 WGL ARB/EXT 扩展函数(像素格式查询、上下文创建、Pbuffer 等)
- **`SkWGLPbufferContext`**: 引用计数的 Pbuffer 上下文包装器,继承自 `SkRefCnt`
- **`SkWGLContextRequest`** (枚举): 上下文类型请求(Core Profile、Compatibility Profile、GL ES)

## 公共 API 函数

- `SkWGLExtensions` 的全部方法: `hasExtension`, `choosePixelFormat`, `selectFormat`, `createContextAttribs`, `swapInterval`, Pbuffer 系列方法
- `SkCreateWGLContext()`: 高层接口,创建 OpenGL 渲染上下文
- `SkWGLPbufferContext::Create()`: 创建 Pbuffer 离屏上下文

## 内部实现细节

定义了所有必要的 WGL 属性常量(如 `SK_WGL_DRAW_TO_WINDOW`、`SK_WGL_SAMPLES` 等),避免直接依赖 Windows SDK 中的 WGL 头文件。函数指针类型定义为静态成员,被所有实例共享。

## 依赖关系

- `include/core/SkRefCnt.h`: 引用计数基类
- `src/base/SkLeanWindows.h`: 精简的 Windows 头文件包含

## 设计模式与设计决策

- 静态函数指针设计确保全局唯一初始化
- `selectFormat` 方法提供了比 `wglChoosePixelFormat` 更精确的格式选择策略

## 性能考量

所有函数指针为类级别静态成员,避免每个实例的重复查找。

## 相关文件

- `tools/ganesh/gl/win/SkWGL_win.cpp`: 实现文件
