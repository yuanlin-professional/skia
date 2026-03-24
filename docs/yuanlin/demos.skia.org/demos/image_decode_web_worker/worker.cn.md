# worker.js - 图像解码 Web Worker

> 源文件: `demos.skia.org/demos/image_decode_web_worker/worker.js`

## 概述

在 Web Worker 中执行图像解码,通过 `createImageBitmap` 和 `OffscreenCanvas` 将图像数据解码为原始像素数组,然后通过可转移对象(Transferable)高效传回主线程。

## 架构位置

图像解码演示的后台解码线程。

## 公共 API 函数

通过 message 事件接收 Blob,返回 `{width, height, decodedArrayBuffer}`。

## 内部实现细节

接收图像 Blob -> `createImageBitmap` 解码 -> 绘制到 OffscreenCanvas -> `getImageData` 获取像素 -> 通过 Transferable 传输 ArrayBuffer(零拷贝)。

## 依赖关系

- Web Worker API, OffscreenCanvas, createImageBitmap

## 性能考量

使用 Transferable 传输避免像素数据拷贝,解码在后台线程不阻塞动画。

## 相关文件

- `demos.skia.org/demos/image_decode_web_worker/main.js`
