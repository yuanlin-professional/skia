# SkiaUIContext.mm - CPU 渲染上下文

> 源文件: `tools/skottie_ios_app/SkiaUIContext.mm`

## 概述

实现了基于 CPU 软件光栅化的 Skia 渲染上下文,使用 `SkBitmap` 作为后备缓冲区,通过 Core Graphics 将渲染结果显示到 UIView 上。

## 架构位置

Skottie iOS 应用的 CPU 渲染后端实现,作为 Metal 和 GL 不可用时的降级方案。

## 主要类与结构体

- **`SkiaUIView`**: UIView 子类,使用 CPU SkBitmap 渲染
- **`SkiaUIContext`**: SkiaContext 子类,管理 CPU 渲染视图

## 公共 API 函数

- **`MakeSkiaUIContext()`**: 工厂函数,创建 CPU 渲染上下文

## 内部实现细节

使用 `SkBitmap::allocN32Pixels` 分配像素缓冲区,通过 `SkCGDrawBitmap` 将位图绘制到 Core Graphics 上下文。帧率固定在 30fps,使用 NSTimer 调度重绘。

## 依赖关系

- `SkCGUtils.h`: Skia 到 Core Graphics 的桥接工具
- `SkTime.h`: 时间工具

## 设计模式与设计决策

CPU 渲染作为最低限度的后备方案,保证在任何 iOS 设备上都能运行。

## 性能考量

CPU 渲染性能较低,但不需要 GPU 资源。位图尺寸跟随视图尺寸自动调整。

## 相关文件

- `tools/skottie_ios_app/SkiaContext.h`
