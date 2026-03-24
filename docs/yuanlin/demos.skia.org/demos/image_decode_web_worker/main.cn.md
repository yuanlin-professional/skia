# main.js - 图像解码演示主线程

> 源文件: `demos.skia.org/demos/image_decode_web_worker/main.js`

## 概述

演示在主线程和 Web Worker 中解码大图像的对比效果。主线程持续渲染一个动画圆圈,点击按钮可选择在主线程或 Worker 中解码一张大型 JPEG 图片,直观对比两种方式对动画流畅度的影响。

## 架构位置

Skia Web 图像解码演示的主控制层。

## 公共 API 函数

无公共 API,通过 DOM 事件驱动。

## 内部实现细节

使用 CanvasKit WebGL 表面渲染动画圆圈和解码后的图像。主线程解码使用 `createImageBitmap` + `MakeImageFromCanvasImageSource`,Worker 解码通过 `MakeImage` 从原始像素数据重建图像。支持清除已解码图像。

## 依赖关系

- canvaskit-wasm, worker.js

## 设计模式与设计决策

对比演示模式: 同一操作分别在主线程和 Worker 中执行,通过动画流畅度直观展示差异。

## 性能考量

使用 Wikimedia 上的大型图片(3764x5706)作为测试用例,确保解码开销足够明显。

## 相关文件

- `demos.skia.org/demos/image_decode_web_worker/worker.js`
