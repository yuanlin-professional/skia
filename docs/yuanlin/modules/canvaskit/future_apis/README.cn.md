# future_apis - 未来 Web API 技术调研文档

## 概述

`future_apis` 目录包含 CanvasKit 团队对新兴 Web 平台 API 的技术调研和集成方案文档。
这些文档记录了尚在标准化或实验阶段的 Web API，评估它们对 CanvasKit 的潜在价值，
并提供了原型验证的步骤和示例代码。

目前包含两个技术调研文档：
- **WebGPU.md** - WebGPU 图形 API 的调研，探索将 CanvasKit 的渲染后端从 WebGL 迁移到
  WebGPU 的可能性。WebGPU 提供了更接近现代图形 API（Vulkan/Metal/D3D12）的编程模型，
  具有更好的性能和更丰富的 GPU 计算能力。
- **ImageDecoder.md** - ImageDecoder API 的调研，用于浏览器原生的图像解码（包括动画图像），
  可与 `CanvasKit.MakeImageFromCanvasImageSource` 配合使用，替代 CanvasKit 自带的编解码器。

这些文档既是技术决策的历史记录，也是 CanvasKit 未来发展方向的路线图参考。

## 架构图

```
+---------------------------------------------------+
|             CanvasKit 渲染后端演进                   |
+---------------------------------------------------+
|                                                   |
|  当前状态:                                         |
|  +-------------------+  +-------------------+     |
|  | WebGL 后端 (稳定)  |  | CPU 后端 (稳定)    |     |
|  | Ganesh 渲染引擎    |  | 纯软件光栅化       |     |
|  +-------------------+  +-------------------+     |
|                                                   |
|  未来方向:                                         |
|  +-------------------+  +-------------------+     |
|  | WebGPU 后端 (实验) |  | ImageDecoder API  |     |
|  | Dawn 渲染引擎      |  | 浏览器原生解码      |     |
|  | Graphite 架构      |  | 替代内置编解码器    |     |
|  +-------------------+  +-------------------+     |
+---------------------------------------------------+
```

## 目录结构

```
future_apis/
|-- WebGPU.md            # WebGPU 技术调研文档
|-- ImageDecoder.md      # ImageDecoder API 技术调研文档
```

## 关键类与函数

### WebGPU 集成（已部分实现）

WebGPU 后端已在 CanvasKit 中得到实验性支持：
```javascript
// WebGPU 使用方式（实验性）
const adapter = await navigator.gpu.requestAdapter();
const device = await adapter.requestDevice();
const devCtx = CanvasKit.MakeGPUDeviceContext(device);
const canvasCtx = CanvasKit.MakeGPUCanvasContext(devCtx, canvas);
canvasCtx.requestAnimationFrame((canvas) => {
    // 在 WebGPU 表面上绘制
});
```

### ImageDecoder API 使用示例

```javascript
// 静态图像
const response = await fetch(imageUrl);
const data = await response.arrayBuffer();
const decoder = new ImageDecoder({ data });
const bitmap = await decoder.decode();
const skImage = CanvasKit.MakeImageFromCanvasImageSource(bitmap);

// 动画图像（GIF）
for (let frame = 0; frame < decoder.frameCount; frame++) {
    const bitmap = await decoder.decode(frame);
    const skImage = CanvasKit.MakeImageFromCanvasImageSource(bitmap);
}
```

## 依赖关系

- **WebGPU**: Dawn (Chromium WebGPU 实现)、Emscripten WebGPU 绑定
- **ImageDecoder**: Web Codecs 提案的一部分
- **CanvasKit 核心**: `MakeImageFromCanvasImageSource`、`MakeGPUDeviceContext` 等

## 设计模式分析

### 渐进式集成
WebGPU 支持采用渐进式集成策略：先在 `webgpu.js` 中实现基础绑定，通过 `compile.sh webgpu`
标志启用，允许早期采用者在实验环境中验证。随着 WebGPU 标准的成熟，逐步扩展功能。

### 平台能力探测
ImageDecoder API 作为浏览器原生能力，可以减少 WASM 二进制中的编解码器代码（约几十 KB），
同时利用浏览器的硬件加速解码，提升性能并减小包体积。

## 数据流

```
WebGPU 渲染流程:
  navigator.gpu.requestAdapter()
       |
       v
  adapter.requestDevice()
       |
       v
  CanvasKit.MakeGPUDeviceContext(device)
       |
       v
  CanvasKit.MakeGPUCanvasContext(devCtx, canvas)
       |
       v
  requestAnimationFrame 循环 ----> getCurrentTexture()
       |                              |
       v                              v
  canvas.draw*() ----> Skia/Dawn ----> GPU 渲染
```

## 相关文档与参考

- **WebGPU 规范**: https://gpuweb.github.io/gpuweb/
- **WebGPU 实现状态**: https://github.com/gpuweb/gpuweb/wiki/Implementation-Status
- **Dawn (Chromium WebGPU)**: https://dawn.googlesource.com/dawn
- **ImageDecoder 提案**: https://github.com/dalecurtis/image-decoder-api/blob/master/explainer.md
- **Web Codecs**: https://github.com/WICG/web-codecs/blob/master/explainer.md
- **CanvasKit WebGPU 构建**: `./compile.sh webgpu`
- **WebGPU JS 绑定**: `webgpu.js`
