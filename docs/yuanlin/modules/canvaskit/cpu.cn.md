# CanvasKit CPU 模块 - 软件渲染 Surface 管理

> 源文件: `modules/canvaskit/cpu.js`

## 概述

cpu.js 是 CanvasKit WebAssembly 模块的 CPU（软件渲染）后端初始化文件。它为 CanvasKit 提供了基于软件光栅化的 Surface 创建、像素管理和 HTML Canvas 集成功能。当不使用 GPU 后端（WebGL/WebGPU）时，该文件负责分配 WASM 内存中的像素缓冲区，并在刷新时将渲染结果通过 `putImageData` API 输出到 HTML Canvas 元素。

## 架构位置

该文件属于 CanvasKit 的后端抽象层，通过 `_extraInitializations` 注册机制在 WASM 模块初始化时执行。它与 GPU 后端文件（webgl.js、webgpu.js）互斥或互补：

```
CanvasKit 初始化
  ├── preamble.js (入口)
  ├── cpu.js (CPU 后端) ← 本文件
  │     ├── MakeSWCanvasSurface()
  │     ├── MakeSurface()
  │     ├── Surface.flush()
  │     └── Surface.dispose()
  ├── webgl.js (WebGL 后端, 可选)
  └── postamble.js (收尾)
```

## 主要类与结构体

### Surface 扩展属性
CPU Surface 在创建时附加以下 JavaScript 属性：
- `_canvas`：关联的 HTML Canvas 元素（用于像素输出），可为 null
- `_width` / `_height`：Surface 尺寸
- `_pixelLen`：像素缓冲区字节长度（width * height * 4）
- `_pixelPtr`：WASM 堆中像素数据的指针

## 公共 API 函数

### `CanvasKit.MakeSWCanvasSurface(idOrElement)`
- **功能**：创建关联到 HTML Canvas 的 CPU Surface
- **参数**：HTML Canvas 元素或其 ID 字符串
- **返回值**：关联了 HTML Canvas 的 Surface 对象
- **流程**：解析输入 -> 获取 canvas 尺寸 -> 调用 `MakeSurface()` -> 绑定 `_canvas`
- **兼容性**：支持 `HTMLCanvasElement` 和 `OffscreenCanvas`

### `CanvasKit.MakeCanvasSurface()`
- **功能**：通用 Surface 创建入口
- **行为**：若 GPU 后端未设置此函数，则默认指向 `MakeSWCanvasSurface`

### `CanvasKit.MakeSurface(width, height)`
- **功能**：创建指定尺寸的 CPU Surface
- **实现细节**：
  - 使用 RGBA_8888 颜色类型 + Unpremul Alpha + SRGB 色彩空间
  - 通过 `CanvasKit._malloc` 在 WASM 堆上分配像素缓冲区
  - 调用 `Surface._makeRasterDirect` 创建底层 Skia Surface
  - 初始化像素为透明黑色（`clear(TRANSPARENT)`）
- **注意**：当前不支持 CPU Surface 的色彩空间定制（受 `putImageData` API 限制）

### `CanvasKit.MakeRasterDirectSurface(imageInfo, mallocObj, bytesPerRow)`
- **功能**：从用户提供的内存创建直接光栅 Surface
- **参数**：`mallocObj` 需通过 `CanvasKit.Malloc` 分配

### `Surface.prototype.flush(dirtyRect)`
- **功能**：刷新 Surface 内容到关联的 HTML Canvas
- **实现**：
  1. 设置当前 GPU 上下文（CPU 模式下为空操作）
  2. 调用底层 `_flush()`
  3. 若存在关联的 HTML Canvas：
     - 从 WASM 堆创建 `Uint8ClampedArray` 视图
     - 构建 `ImageData` 对象
     - 通过 `putImageData` 输出到 Canvas 2D 上下文
  4. 支持可选的脏矩形（`dirtyRect`）局部更新

### `Surface.prototype.dispose()`
- **功能**：释放 Surface 资源
- **实现**：释放像素缓冲区（`_free`），然后调用 `delete()` 释放 C++ 对象

### `CanvasKit.setCurrentContext()`
- **功能**：CPU 模式下为空操作（no-op）

### `CanvasKit.getCurrentGrDirectContext()`
- **功能**：CPU 模式下返回 null（无 GPU 上下文）

## 内部实现细节

### 像素缓冲区管理

CPU Surface 使用 WASM 线性内存中的连续缓冲区存储像素数据：
```javascript
var pixelLen = width * height * 4;  // RGBA_8888, 4字节/像素
var pixelPtr = CanvasKit._malloc(pixelLen);
```

`_makeRasterDirect` 将此缓冲区作为 Skia Surface 的后端存储，Skia 的渲染操作直接写入该内存区域。

### HTML Canvas 输出

刷新时通过 `Uint8ClampedArray` 在 WASM 堆上创建零拷贝视图：
```javascript
var pixels = new Uint8ClampedArray(CanvasKit.HEAPU8.buffer, this._pixelPtr, this._pixelLen);
var imageData = new ImageData(pixels, this._width, this._height);
```
这是 WASM 与浏览器 Canvas API 之间最高效的数据传递方式。

### GPU 后端兼容

通过条件检查 `if (!CanvasKit.MakeCanvasSurface)` 确保 CPU 后端不覆盖 GPU 后端已设置的函数，实现了后端的透明切换。

## 依赖关系

- **Emscripten 运行时**：`Module`（WASM 模块全局对象）、`HEAPU8`（堆视图）、`_malloc` / `_free`
- **CanvasKit C++ 绑定**：`Surface._makeRasterDirect`、`Surface._flush`
- **浏览器 API**：`HTMLCanvasElement`、`OffscreenCanvas`、`ImageData`、`CanvasRenderingContext2D.putImageData`

## 设计模式与设计决策

1. **延迟初始化**：通过 `_extraInitializations` 数组注册，确保在 WASM 运行时就绪后才执行 JavaScript 扩展。

2. **RasterDirect vs Raster**：注释中提到 `RasterDirect` 比 `Raster` 快 10%，因为避免了 Premul<->Unpremul 的额外转换。Surface 直接使用 Unpremul 格式匹配 HTML Canvas 的期望。

3. **零拷贝像素传递**：使用 `Uint8ClampedArray` 视图而非复制数据，最大限度减少了 CPU Surface 到 HTML Canvas 的传输开销。

4. **后端透明抽象**：`setCurrentContext` 和 `getCurrentGrDirectContext` 提供了 GPU 后端的接口存根，使上层代码不必关心当前使用的后端。

## 性能考量

- `putImageData` 是 CPU Surface 到 HTML Canvas 的性能瓶颈，每帧需要传输完整的像素缓冲区
- 脏矩形（`dirtyRect`）支持允许仅更新画面变化的区域，减少 `putImageData` 的数据量
- RGBA_8888 + Unpremul 格式避免了每帧的格式转换开销
- 不支持色彩空间定制是因为 `putImageData` 强制使用 RGBA_8888
- `_makeRasterDirect` 避免了像素数据的额外拷贝

## 补充说明

### CPU vs GPU Surface 对比

| 特性 | CPU Surface | GPU Surface (WebGL) |
|------|-------------|-------------------|
| 像素存储 | WASM 堆内存 | GPU 纹理 |
| 输出方式 | putImageData | WebGL SwapBuffers |
| 色彩空间 | 仅 SRGB | 可配置 |
| 性能瓶颈 | CPU->Canvas 像素拷贝 | GPU 命令提交 |
| 抗锯齿 | 软件实现 | 硬件 MSAA |
| 适用场景 | Node.js/Worker/无 GPU | 浏览器交互应用 |

### Surface 生命周期

1. `MakeSurface()` / `MakeSWCanvasSurface()`：分配 WASM 堆内存，创建 Skia Surface
2. `getCanvas()`：获取关联的 SkCanvas，执行绘制操作
3. `flush()`：将 WASM 像素缓冲区输出到 HTML Canvas
4. `dispose()`：释放 WASM 堆内存和 C++ Surface 对象

每个阶段都涉及 JavaScript 和 WASM C++ 层之间的交互。

### Unpremul Alpha 的选择

CPU Surface 使用 Unpremultiplied Alpha 是因为 HTML Canvas 的 `putImageData` API 期望非预乘格式。虽然 Skia 内部渲染通常使用预乘 Alpha（Premul），但使用 `_makeRasterDirect` 配合 Unpremul 格式可以避免每帧的格式转换。源代码注释提到 Premul -> Unpremul 的转换可能导致 10 倍性能下降。

## 相关文件

- `modules/canvaskit/preamble.js` - CanvasKit 模块入口
- `modules/canvaskit/postamble.js` - CanvasKit 模块收尾
- `modules/canvaskit/webgl.js` - WebGL GPU 后端（可选替代）
- `modules/canvaskit/interface.js` - CanvasKit JavaScript 接口
- `modules/canvaskit/externs.js` - Closure Compiler 外部声明
