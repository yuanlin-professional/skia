# impl.js - Web 图像解码 Polyfill 实现

> 源文件: `specs/web-img-decode/proposed/impl/impl.js`

## 概述

`impl.js` 是一个 JavaScript polyfill 实现，基于 CanvasKit（Skia 的 WebAssembly 版本）提供增强的 Web 图像解码能力。该文件实现了 `createImageData` 函数，允许在浏览器中使用 Skia 的图像解码能力将编码的图像数据（如 PNG、JPEG 等）解码为 `ImageData` 对象，同时支持调整尺寸、颜色类型和预乘透明度等选项。

此文件是 Skia 团队为 Web 标准提案（Web Image Decode API）编写的参考实现/原型。

## 架构位置

```
Skia Web 标准提案
├── specs/web-img-decode/
│   └── proposed/
│       ├── spec.html          <-- API 规范文档
│       └── impl/
│           └── impl.js        <-- 本文件：Polyfill 参考实现
└── modules/canvaskit/         <-- CanvasKit WebAssembly 模块
```

## 主要类与结构体

本文件不定义类，通过 IIFE（立即调用函数表达式）将两个函数挂载到 `window` 对象上。

## 公共 API 函数

### `window.loadPolyfill()`
初始化 polyfill，加载 CanvasKit WebAssembly 模块。

```javascript
window.loadPolyfill = () => {
    return CanvasKitInit({
        locateFile: (file) => 'https://unpkg.com/canvaskit-wasm@0.6.0/bin/' + file,
    }).ready().then((CK) => {
        CanvasKit = CK;
    });
}
```

返回一个 Promise，在 CanvasKit 加载完成后 resolve。

### `window.createImageData(src, options)`
核心 API：将编码的图像数据解码为 `ImageData` 对象。

参数：
- `src`: 编码的图像数据（如 PNG/JPEG 的 ArrayBuffer）
- `options`: 解码选项对象
  - `resizeWidth`: 目标宽度（可选）
  - `resizeHeight`: 目标高度（可选）
  - `premul`: 是否使用预乘 alpha（boolean）
  - `colorType`: 颜色类型，`"float32"` 或 `"uint8"`（默认）

返回值：`ImageData` 对象。

## 内部实现细节

### 解码流程

1. **创建 Skia 图像**：`CanvasKit.MakeImageFromEncoded(src)` 从编码数据创建 SkImage
2. **构建图像信息**：根据 options 设置目标尺寸、alpha 类型和颜色类型
3. **读取像素**：`skImg.readPixels(imageInfo, 0, 0)` 执行解码和格式转换
4. **类型转换**：将像素数据转换为 `Uint8ClampedArray`（`ImageData` 的要求）
5. **创建 ImageData**：使用标准 `ImageData` 构造函数创建结果
6. **清理**：调用 `skImg.delete()` 释放 WebAssembly 内存

### 颜色类型处理

```javascript
switch (options.colorType) {
    case "float32":
        imageInfo.colorType = CanvasKit.ColorType.RGBA_F32;
        output = new Uint8ClampedArray(pixels);  // 额外复制
        break;
    case "uint8":
    default:
        imageInfo.colorType = CanvasKit.ColorType.RGBA_8888;
        output = new Uint8ClampedArray(pixels.buffer);  // 零复制转换
        break;
}
```

- `uint8` 模式：使用 `RGBA_8888` 格式，可以零复制转换为 `Uint8ClampedArray`
- `float32` 模式：使用 `RGBA_F32` 格式，但由于 `ImageData` 仅支持 `Uint8`，需要额外复制（这是浏览器 API 的限制）

### Alpha 类型

```javascript
alphaType: options.premul ? CanvasKit.AlphaType.Premul : CanvasKit.AlphaType.Unpremul
```

支持预乘（Premultiplied）和非预乘（Unpremultiplied）两种 alpha 模式。

## 依赖关系

- **CanvasKit（运行时）**：`canvaskit-wasm@0.6.0` 通过 CDN（unpkg.com）加载
- **浏览器 API**：`ImageData`, `Uint8ClampedArray`, `Promise`

## 设计模式与设计决策

1. **IIFE 封装**：使用 `(function(window) { ... })(window)` 模式将实现封装在闭包中，`CanvasKit` 变量作为模块私有状态，避免全局命名空间污染。

2. **延迟加载**：CanvasKit 不在脚本加载时初始化，而是通过 `loadPolyfill()` 显式触发。这允许页面控制加载时机，避免不必要的大型 WASM 文件下载。

3. **CDN 加载**：CanvasKit WASM 从 unpkg CDN 加载，简化了演示和原型阶段的部署。生产环境应自行托管。

4. **浏览器 API 兼容**：返回标准的 `ImageData` 对象，与现有 Canvas 2D API 完全兼容（如 `ctx.putImageData()`）。

5. **选项驱动**：通过 options 对象传递所有可选参数，API 设计清晰且可扩展。

## 性能考量

- **WASM 加载开销**：首次调用 `loadPolyfill()` 需要下载和编译 CanvasKit WASM 模块（数 MB），是最大的一次性开销。
- **float32 额外复制**：由于 `ImageData` 的限制，`float32` 颜色类型需要额外的数据复制，性能不如 `uint8` 模式。
- **WASM 内存管理**：`skImg.delete()` 必须手动调用以释放 WebAssembly 堆上的内存。遗忘调用会导致内存泄漏。
- **零复制优化**：`uint8` 模式通过 `new Uint8ClampedArray(pixels.buffer)` 实现视图级转换，避免数据复制。
- **readPixels 开销**：`readPixels` 可能触发图像解码和格式转换，是主要的计算瓶颈。

## 相关文件

- `specs/web-img-decode/proposed/` - Web 图像解码 API 规范提案
- `modules/canvaskit/` - CanvasKit WebAssembly 模块源代码
- `modules/canvaskit/canvaskit_bindings.cpp` - CanvasKit C++ 绑定
