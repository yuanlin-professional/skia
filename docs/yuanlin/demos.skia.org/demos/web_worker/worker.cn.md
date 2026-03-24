# worker.js - Web Worker 渲染线程

> 源文件: `demos.skia.org/demos/web_worker/worker.js`

## 概述

在 Web Worker 中加载 CanvasKit 并渲染 Skottie 动画,演示如何在后台线程中使用 OffscreenCanvas 进行 Skia 渲染,避免阻塞主线程。

## 架构位置

Skia Web Worker 演示的后台渲染线程。

## 主要类与结构体

无。

## 公共 API 函数

无对外 API,通过 `postMessage` 接收 OffscreenCanvas。

## 内部实现细节

使用 `Promise.all` 同步等待 OffscreenCanvas 传输、CanvasKit 初始化和动画 JSON 加载三个异步操作。在 OffscreenCanvas 上创建 WebGL 表面后调用共享的 `SkottieExample` 函数渲染动画。

## 依赖关系

- canvaskit-wasm: 通过 importScripts 从 unpkg CDN 加载
- shared.js: 共享的动画渲染逻辑

## 设计模式与设计决策

使用 OffscreenCanvas API 实现跨线程 Canvas 渲染,主线程保持响应性。

## 性能考量

独立线程渲染不受主线程 JavaScript 执行影响,动画帧率更稳定。

## 相关文件

- `demos.skia.org/demos/web_worker/main.js`, `shared.js`
