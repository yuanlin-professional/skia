# CreatePlatformGLTestContext_glx.cpp - GLX GL 测试上下文

> 源文件: `tools/ganesh/gl/glx/CreatePlatformGLTestContext_glx.cpp`

## 概述

实现基于 GLX (OpenGL Extension to X Window System) 的 Linux 平台 GL 测试上下文。支持 GL 和 GL ES 上下文创建,自动协商最高可用版本。

## 架构位置

Skia GPU 测试基础设施的 X11/Linux 平台适配层,要求 GLX 1.3+。

## 主要类与结构体

- **`GLXGLTestContext`**: 继承自 `GLTestContext`,持有 `GLXContext`、`Display*`、`Pixmap`、`GLXPixmap`

## 公共 API 函数

- **`CreatePlatformGLTestContext()`**: 工厂函数
- **`CreateBestContext()`**: 静态方法,创建最高版本的 GL/GL ES 上下文

## 内部实现细节

通过 GLX FBConfig 选择最佳帧缓冲配置,使用 `glXCreateContextAttribsARB` 从最高版本(GL 4.4 / GL ES 3.0)向下尝试创建上下文。使用 X Pixmap 而非窗口作为渲染目标。安装自定义 X 错误处理器来捕获上下文创建失败。Display 通过 `AutoDisplay` 单例管理。

## 依赖关系

- X11/Xlib.h, GL/glx.h, GL/glu.h
- `GrGLInterfaces::MakeGLX()`: GLX GL 接口
- `SkOnce`: 用于线程安全的 `XInitThreads` 调用

## 设计模式与设计决策

- 版本降级策略:从最高版本向下尝试,确保获得最佳功能集
- 使用 Pixmap 而非窗口,避免创建可见窗口
- X 错误处理器临时替换,避免创建失败导致程序崩溃

## 性能考量

Display 连接通过单例缓存,FBConfig 选择偏好更高采样数。

## 相关文件

- `include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h`
