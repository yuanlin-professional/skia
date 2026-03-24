# SkiaMetalContext.mm - Metal 渲染上下文

> 源文件: `tools/skottie_ios_app/SkiaMetalContext.mm`

## 概述

实现了基于 Apple Metal API 的 Skia GPU 渲染上下文。使用 MTKView (Metal Kit) 配合 Skia Ganesh Metal 后端进行硬件加速渲染。

## 架构位置

Skottie iOS 应用的首选渲染后端,提供最佳性能。

## 主要类与结构体

- **`SkiaMtkView`**: MTKView 子类,使用 Metal 后端渲染 Skia 内容
- **`SkiaMetalContext`**: SkiaContext 子类,管理 Metal 设备、命令队列和 GrDirectContext

## 公共 API 函数

- **`MakeSkiaMetalContext()`**: 工厂函数,创建 Metal 渲染上下文

## 内部实现细节

初始化时创建系统默认 Metal 设备和命令队列,然后通过 `GrDirectContexts::MakeMetal` 创建 Ganesh Metal 上下文。每帧渲染通过 `SkMtkViewToSurface` 获取当前 drawable 的 SkSurface,渲染完成后通过命令缓冲区提交。动画暂停时启用 `enableSetNeedsDisplay` 模式减少不必要的重绘。

## 依赖关系

- Metal.framework, MetalKit.framework
- `GrMtlDirectContext.h`: Ganesh Metal 上下文
- `SkMetalViewBridge.h`: MTKView 到 Skia Surface 的桥接

## 设计模式与设计决策

- 使用 MTKView 的帧回调机制驱动动画循环
- 暂停时自动切换到按需重绘模式节省电量

## 性能考量

Metal 提供最低延迟和最高吞吐量。帧率限制为 30fps。暂停状态下不进行不必要的 GPU 提交。

## 相关文件

- `tools/skottie_ios_app/SkMetalViewBridge.h`
