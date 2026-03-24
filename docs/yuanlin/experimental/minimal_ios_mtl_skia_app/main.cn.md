# Minimal iOS Metal Skia App

> 源文件: `experimental/minimal_ios_mtl_skia_app/main.mm`

## 概述

`main.mm` 是一个最小化的 iOS 应用程序，演示如何使用 Skia 通过 Metal 后端在 iOS 设备上进行 GPU 渲染。该应用绘制一个持续旋转的线性渐变效果，展示了 Skia + Metal + UIKit 的完整集成流程。

## 架构位置

位于 `experimental/minimal_ios_mtl_skia_app/` 目录，作为 Skia iOS Metal 渲染的参考实现。它使用 Skia 的 Ganesh GPU 后端和 Metal API。

## 主要类与结构体

- **`AppViewDelegate`** (NSObject<MTKViewDelegate>): Metal 视图渲染委托
  - `grContext`: GrDirectContext 非拥有指针
  - `metalQueue`: Metal 命令队列
  - `fPaint`: SkPaint 成员（持有渐变 Shader）
- **`AppViewController`** (UIViewController): 视图控制器
  - `metalDevice` / `metalQueue`: Metal 设备和命令队列
  - `fGrContext`: GrContextHolder（拥有 GrDirectContext）
- **`AppDelegate`** (UIResponder<UIApplicationDelegate>): 应用委托

## 公共 API 函数

- `config_paint(SkPaint*)`: 配置渐变 shader（黑到白的垂直线性渐变）
- `draw_example(SkSurface*, paint, rotation)`: 在画布中心绘制旋转渐变

## 内部实现细节

1. **渲染循环** (`drawInMTKView:`):
   - 配置 paint（懒初始化渐变 shader）
   - 使用 `SkTime::GetNSecs()` 计算旋转角度
   - 通过 `SkMtkViewToSurface` 创建 Skia 表面
   - 绘制旋转渐变并刷新
   - 提交 Metal 命令缓冲区并展示 drawable
2. **初始化** (`viewDidLoad`):
   - 创建 Metal 设备和命令队列
   - 通过 `SkMetalDeviceToGrContext` 创建 Ganesh GPU 上下文
   - 配置 MTKView 并设置委托
3. **应用启动** (`application:didFinishLaunchingWithOptions:`):
   - 创建窗口并设置根视图控制器

## 依赖关系

- Skia 核心: `SkCanvas`, `SkPaint`, `SkSurface`, `SkColorSpace`
- Skia GPU (Ganesh): `GrDirectContext`, `GrBackendSurface`, `SkSurfaceGanesh`
- Skia Metal: `GrMtlTypes`, `SkMetalViewBridge`
- Skia 效果: `SkGradient` (线性渐变)
- Apple 框架: Metal, MetalKit, UIKit

## 设计模式与设计决策

- MVC 架构：AppDelegate -> AppViewController -> AppViewDelegate
- 委托模式: MTKViewDelegate 处理渲染回调
- 非拥有指针 (`assign`) 用于 GrContext 传递到渲染委托
- 渲染前尽可能多地准备工作（paint 配置、旋转计算），最小化表面持有时间

## 性能考量

- 每帧创建新的 SkSurface 包装，但底层 Metal texture 由 MTKView 管理
- `skgpu::ganesh::Flush` 确保 GPU 命令提交
- 旋转使用纳秒级时间戳确保动画平滑

## 相关文件

- `tools/skottie_ios_app/SkMetalViewBridge.h`: Metal 视图桥接工具
- `include/gpu/ganesh/mtl/GrMtlTypes.h`: Metal 类型定义
- `include/gpu/ganesh/SkSurfaceGanesh.h`: Ganesh 表面工厂
