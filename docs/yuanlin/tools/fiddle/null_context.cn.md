# null_context - Fiddle 空 GL 上下文实现

> 源文件: `tools/fiddle/null_context.cpp`

## 概述

null_context.cpp 为 Fiddle 工具提供一个降级的 GPU 上下文创建实现，在既无 Mesa 也无 EGL 可用的环境中使用。它简单返回 nullptr，表示无法创建 GPU 上下文。

## 架构位置

位于 `tools/fiddle/` 目录，是 `create_direct_context` 的降级实现。当构建环境不支持 OpenGL 时链接此文件。

## 主要类与结构体

无。

## 公共 API 函数

### `create_direct_context`
返回 nullptr 并在 driverinfo 中记录 "(no GL driver available)"。

## 内部实现细节

仅 3 行有效代码。

## 依赖关系

- `tools/fiddle/fiddle_main.h`

## 设计模式与设计决策

- **空对象模式**: 提供合法但无功能的实现，确保编译链接成功

## 性能考量

无。

## 相关文件

- `tools/fiddle/egl_context.cpp` - 有功能的 EGL 实现
