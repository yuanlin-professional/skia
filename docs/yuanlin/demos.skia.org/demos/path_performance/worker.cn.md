# worker.js - 路径性能测试 Worker

> 源文件: `demos.skia.org/demos/path_performance/worker.js`

## 概述

路径渲染性能对比演示的 Web Worker 线程,负责在后台执行 Path2D 和 CanvasKit 两种渲染方法,并定期报告帧率。

## 架构位置

路径性能演示的后台渲染引擎。

## 公共 API 函数

通过 postMessage 接收消息:
- 带 `svgData` 和 `offscreenCanvas` 的消息: 初始化渲染器
- 带 `switchMethod` 的消息: 切换渲染方法

## 内部实现细节

维护两个 `Animator` 实例,分别驱动 `Path2dRenderer` 和 `CanvasKitRenderer`。每秒通过 `setInterval` 向主线程报告帧数和总渲染时间。

## 依赖关系

- canvaskit-wasm, shared.js (渲染器类定义)

## 性能考量

在 Worker 线程中渲染避免影响主线程 UI 响应性。帧率报告每秒发送一次。

## 相关文件

- `demos.skia.org/demos/path_performance/main.js`, `shared.js`
