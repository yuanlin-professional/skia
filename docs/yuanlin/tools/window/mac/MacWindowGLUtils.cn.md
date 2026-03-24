# MacWindowGLUtils - macOS OpenGL 像素格式工具

> 源文件: `tools/window/mac/MacWindowGLUtils.h`

## 概述

此文件提供了 macOS 上创建 OpenGL 像素格式的工具函数 `GetGLPixelFormat`。它封装了 `NSOpenGLPixelFormat` 的创建过程，配置了硬件加速、双缓冲、OpenGL 3.2 Core Profile 等属性，并支持可选的 MSAA 多重采样。由于 Apple 已弃用整个 NSOpenGL API，文件中使用了 pragma 指令抑制弃用警告。

## 架构位置

- 位于 `skwindow` 命名空间
- 提供静态内联工具函数
- 被 macOS OpenGL 窗口上下文实现使用
- 使用 Cocoa 框架

## 主要类与结构体

无自定义类，提供独立函数。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GetGLPixelFormat(int sampleCount)` | 创建指定采样数的 NSOpenGLPixelFormat |

## 内部实现细节

### 像素格式属性配置
固定属性（最多 19 个）：
- `NSOpenGLPFAAccelerated` - 硬件加速
- `NSOpenGLPFAClosestPolicy` - 最近匹配策略
- `NSOpenGLPFADoubleBuffer` - 双缓冲
- `NSOpenGLPFAOpenGLProfile` = `NSOpenGLProfileVersion3_2Core` - OpenGL 3.2 Core Profile
- 颜色：24 位 RGB + 8 位 Alpha
- 深度缓冲：0（不使用）
- 模板缓冲：8 位

当 `sampleCount > 1` 时，额外添加 `NSOpenGLPFAMultisample`、`NSOpenGLPFASampleBuffers = 1`、`NSOpenGLPFASamples = sampleCount`。

### 弃用警告处理
使用 `#pragma clang diagnostic` 抑制 `-Wdeprecated-declarations` 警告，因为 NSOpenGL 在 macOS 上已全面弃用。

## 依赖关系

- `include/private/base/SkAssert.h` - 断言支持
- `<Cocoa/Cocoa.h>` - NSOpenGLPixelFormat

## 设计模式与设计决策

- **静态内联**: 作为头文件工具函数，避免链接依赖
- **属性数组边界保护**: 使用 `kMaxAttributes = 19` 和 `SkASSERT` 防止数组越界
- **弃用 API 适配**: 通过 pragma 明确标记使用已弃用 API 的范围

## 性能考量

像素格式创建是一次性初始化操作，不影响渲染性能。MSAA 启用会增加帧缓冲区大小和渲染负担。

## 相关文件

- `tools/window/mac/GLWindowContext_mac.mm` - macOS GL 窗口上下文（使用此工具）
- `tools/window/mac/MacWindowInfo.h` - macOS 窗口信息
