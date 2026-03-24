# CreatePlatformGLTestContext_none.cpp - 空 GL 测试上下文

> 源文件: `tools/ganesh/gl/none/CreatePlatformGLTestContext_none.cpp`

## 概述

提供一个始终返回 nullptr 的 `CreatePlatformGLTestContext` 实现,用于不支持 OpenGL 的平台。

## 架构位置

Skia GPU 测试基础设施中的空实现占位符,确保在所有平台上都能编译链接。

## 主要类与结构体

无。

## 公共 API 函数

- **`CreatePlatformGLTestContext()`**: 始终返回 nullptr

## 内部实现细节

仅包含一个返回 nullptr 的函数实现。

## 依赖关系

- `tools/ganesh/gl/GLTestContext.h`

## 设计模式与设计决策

空对象模式的变体,确保接口在所有平台上的统一性。

## 性能考量

无运行时开销。

## 相关文件

- `tools/ganesh/gl/GLTestContext.h`
