# specs/web-img-decode - Web 图像解码 API 提案

## 概述

`web-img-decode/` 包含一个 Web 图像解码 API 的规范提案。该提案旨在简化
在 JavaScript 中将编码图像字节（Blob 或 ArrayBuffer）转换为 ImageData
（Uint8ClampedArray）的过程，以便进行后续的图像处理。

## 背景

目前在浏览器中进行图像解码操作较为繁琐。例如，用户从磁盘选择图片并将其
转换为灰度图，需要经过 Image 元素创建、Canvas 绘制等多个中间步骤。

## 目录结构

```
web-img-decode/
├── README.md            # 提案说明
├── current/             # 当前方案演示
│   └── index.html       # 展示当前繁琐的解码方式
└── proposed/            # 提议方案演示
    └── index.html       # 展示简洁的新 API
```

## 提案内容

提议的新 API 使得图像解码过程大大简化。概念验证实现基于 CanvasKit WASM 库，
但设计目标是让 Web 浏览器原生支持此功能。

## 相关文档与参考

- CanvasKit: `modules/canvaskit/`
- ImageData API: https://developer.mozilla.org/en-US/docs/Web/API/ImageData
