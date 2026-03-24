JS 图像解码 (JS Image Decode)
===============

背景
----------

目前，将编码后的 Blob 或 ArrayBuffer 图像字节转换为用于进一步图像处理的 ImageData（Uint8ClampedArray）的过程非常繁琐。
请参阅 current/index.html 中的示例，其中用户可以从磁盘选择图像，然后通过 JS 将其转换为灰度版本（无需后端服务器）。


提案
--------
我们提议……请参阅 proposed/index.html 中的 API，它使此过程更加简洁。
它在底层使用 CanvasKit WASM 库提供功能，但目的是让 Web 浏览器原生支持此功能。
