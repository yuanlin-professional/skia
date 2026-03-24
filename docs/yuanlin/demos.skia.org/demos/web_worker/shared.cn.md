# shared.js - Skottie 动画渲染共享逻辑

> 源文件: `demos.skia.org/demos/web_worker/shared.js`

## 概述

定义了 `SkottieExample` 函数,提供 Skottie 动画的加载和渲染循环逻辑,被主线程和 Worker 线程共同使用。

## 架构位置

Web Worker 演示中的共享渲染逻辑层。

## 公共 API 函数

- **`SkottieExample(CanvasKit, surface, jsonStr)`**: 加载 Skottie 动画并启动渲染循环

## 内部实现细节

使用 `CanvasKit.MakeAnimation` 解析 JSON,通过 `performance.now()` 计算播放进度,使用 `surface.requestAnimationFrame` 驱动动画循环。动画始终循环播放。

## 依赖关系

- CanvasKit.MakeAnimation

## 性能考量

使用 requestAnimationFrame 确保与显示刷新率同步。

## 相关文件

- `demos.skia.org/demos/web_worker/main.js`, `worker.js`
