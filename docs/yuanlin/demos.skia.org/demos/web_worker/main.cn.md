# main.js - Web Worker 演示主线程

> 源文件: `demos.skia.org/demos/web_worker/main.js`

## 概述

Web Worker 演示的主线程入口,同时在主线程和 Worker 线程中各渲染一个 Skottie 动画。包含一个模拟繁忙操作的按钮,用于对比展示 Worker 线程渲染的优势。

## 架构位置

Skia Web Worker 演示的主线程控制逻辑。

## 主要类与结构体

无。

## 公共 API 函数

无。

## 内部实现细节

将一个 canvas 通过 `transferControlToOffscreen()` 转移给 Worker,另一个 canvas 在主线程上渲染。点击按钮时执行 1300ms 的同步循环,演示主线程阻塞时 Worker 线程动画不受影响。

## 依赖关系

- canvaskit-wasm, shared.js, worker.js

## 设计模式与设计决策

对比演示模式: 同一动画在主线程和 Worker 线程同时渲染。

## 性能考量

模拟 1300ms 阻塞展示 Worker 渲染的平滑优势。

## 相关文件

- `demos.skia.org/demos/web_worker/worker.js`, `shared.js`
