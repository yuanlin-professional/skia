# egl_context - Fiddle EGL GPU 上下文创建

> 源文件: `tools/fiddle/egl_context.cpp`

## 概述

egl_context.cpp 为 Skia Fiddle 工具提供基于 EGL（Embedded-System Graphics Library）的 GPU 上下文创建实现。它创建一个 OpenGL ES 的 `GrDirectContext`，用于在支持 EGL 的 Linux 服务器上运行 GPU 加速的 Fiddle 示例。

## 架构位置

位于 `tools/fiddle/` 目录，是 Fiddle 框架的平台相关 GPU 后端之一。与 `null_context.cpp` 互为替代实现。

## 主要类与结构体

无类定义。

## 公共 API 函数

### `create_direct_context`
```cpp
sk_sp<GrDirectContext> create_direct_context(std::ostringstream& driverinfo,
    std::unique_ptr<sk_gpu_test::GLTestContext>* glContext);
```
创建 EGL 环境下的 `GrDirectContext`，并将 GL 版本、厂商、渲染器和扩展信息写入 `driverinfo`。

## 内部实现细节

- 使用 `sk_gpu_test::CreatePlatformGLTestContext` 创建平台 GL 测试上下文（OpenGL ES 标准）
- 调用 `glGetString` 获取驱动信息用于调试输出
- 创建失败时清理资源并返回 nullptr

## 依赖关系

- `EGL/egl.h`, `GLES2/gl2.h` - EGL 和 OpenGL ES API
- `include/gpu/ganesh/GrDirectContext.h` - GPU 上下文
- `tools/ganesh/gl/GLTestContext.h` - GL 测试上下文

## 设计模式与设计决策

- **策略模式**: `create_direct_context` 的不同实现（EGL/null）可在编译时选择

## 性能考量

上下文创建是一次性操作，不涉及持续性能考量。

## 相关文件

- `tools/fiddle/null_context.cpp` - 无 GL 驱动时的降级实现
- `tools/fiddle/fiddle_main.h` - Fiddle 主框架
