# shared.js - 路径性能测试共享渲染器

> 源文件: `demos.skia.org/demos/path_performance/shared.js`

## 概述

定义了路径性能演示中使用的三种渲染器(`SVGRenderer`、`Path2dRenderer`、`CanvasKitRenderer`)和通用的 `Animator` 动画控制器,以及共享的工具函数。

## 架构位置

路径性能演示的共享渲染基础设施,被主线程和 Worker 线程同时使用。

## 主要类与结构体

- **`Animator`**: 帧动画控制器,管理 requestAnimationFrame 循环和帧率统计
- **`SVGRenderer`**: 通过 CSS transform 动画 SVG 元素
- **`Path2dRenderer`**: 使用 Canvas 2D API 的 Path2D 渲染器
- **`CanvasKitRenderer`**: 使用 CanvasKit WebGL 后端渲染

## 公共 API 函数

- **`circleCoordinates(origin, radius, radians)`**: 计算圆上点坐标
- 各渲染器的 `render(x, y)` 方法
- `Animator` 的 `start()`/`stop()` 方法

## 内部实现细节

所有渲染器绘制相同的 SVG 路径图案(600x600 区域,70px 间隔重复)。SVGRenderer 通过克隆 SVG 元素创建图案,Path2dRenderer 使用 Canvas 2D 的 Path2D 对象,CanvasKitRenderer 使用 CanvasKit.Path。Animator 使用圆周运动生成动画位移。

## 依赖关系

- CanvasKit (CanvasKitRenderer)
- Canvas 2D API (Path2dRenderer)
- DOM API (SVGRenderer)

## 设计模式与设计决策

策略模式: 三种渲染器实现相同的 `render(x, y)` 接口。

## 性能考量

CanvasKitRenderer 使用 WebGL 硬件加速,Path2dRenderer 使用 Canvas 2D 软件/硬件混合渲染,SVGRenderer 依赖浏览器 SVG 引擎。

## 相关文件

- `demos.skia.org/demos/path_performance/main.js`, `worker.js`
