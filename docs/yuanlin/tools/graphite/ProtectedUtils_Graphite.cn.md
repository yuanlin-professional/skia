# ProtectedUtils_Graphite.cpp - Graphite 受保护内容工具

> 源文件: `tools/graphite/ProtectedUtils_Graphite.cpp`

## 概述

提供了在 Graphite GPU 后端创建受保护 (Protected) SkSurface 和 SkImage 的测试辅助函数,用于测试 DRM 受保护内容渲染功能。

## 架构位置

属于 Skia Graphite 测试工具层,被 GPU 保护内容相关的单元测试使用。

## 主要类与结构体

无独立类,所有函数在 `ProtectedUtils` 命名空间中。

## 公共 API 函数

- **`CreateProtectedSkSurface()`**: 创建受保护的渲染表面,填充蓝色
- **`CreateProtectedSkImage()`**: 创建受保护的后端纹理图像

## 内部实现细节

通过 `sk_gpu_test::MakeBackendTextureSurface` 和 `MakeBackendTextureImage` 创建 GPU 资源,`Protected` 参数控制是否启用保护模式。创建失败时调用 `SK_ABORT` 终止程序。

## 依赖关系

- `tools/gpu/BackendSurfaceFactory.h`, `BackendTextureImageFactory.h`
- Graphite Recorder API

## 设计模式与设计决策

测试辅助函数设计,创建失败即崩溃(fail-fast),适用于测试环境。

## 性能考量

仅用于测试,不涉及性能优化。

## 相关文件

- `tools/gpu/ProtectedUtils.h`: 头文件
