# CanvasKit GM - WebAssembly 图形测试框架

> 源文件: `modules/canvaskit/gm.js`

## 概述

gm.js 是 CanvasKit 的 WebAssembly 图形测试（GM，即 "Gold Master" 测试）运行时初始化文件。它为 WASM 端的 GM 测试提供了 WebGL 上下文创建和资源加载功能。该文件不是 CanvasKit 本身的一部分，而是独立的测试运行时（`WasmGMTests`），用于在浏览器环境中执行 Skia 的图形回归测试。

## 架构位置

该文件在测试构建中作为独立的 WASM 模块入口，直接绑定到 Emscripten 的 `Module` 对象。

```
测试运行框架
  └── gm.js (WASM 测试运行时)
        ├── WasmGMTests.GetWebGLContext() → WebGL 上下文
        ├── WasmGMTests.LoadResource() → C++ 资源加载
        └── onRuntimeInitialized() → 初始化回调
              └── C++ GM 测试 (WASM 编译)
```

## 主要类与结构体

### `WasmGMTests`
- 即 `Module` 对象（Emscripten WASM 模块）
- 通过 `onRuntimeInitialized` 回调在运行时就绪后扩展功能

## 公共 API 函数

### `WasmGMTests.GetWebGLContext(canvas, webGLVersion)`
- **功能**：为指定 Canvas 创建 WebGL 上下文
- **参数**：
  - `canvas`：HTML Canvas 元素
  - `webGLVersion`：1 或 2（WebGL 版本）
- **返回值**：WebGL 上下文句柄，失败时返回 0
- **实现**：
  1. 配置上下文属性（alpha、depth、stencil、antialias 等）
  2. 调用 Emscripten 的 `GL.createContext()` 创建上下文
  3. 通过 `GL.makeContextCurrent()` 设为当前上下文

### WebGL 上下文配置
```javascript
var contextAttributes = {
    'alpha': 1,
    'depth': 0,            // 离屏渲染不需要深度缓冲
    'stencil': 0,          // 离屏渲染不需要模板缓冲
    'antialias': 0,        // 由 Skia 控制抗锯齿
    'premultipliedAlpha': 1,
    'preserveDrawingBuffer': 0,
    'preferLowPowerToHighPerformance': 0,
    'failIfMajorPerformanceCaveat': 0,
    'enableExtensionsByDefault': 1,
    'explicitSwapControl': 0,
    'renderViaOffscreenBackBuffer': 0,
    'majorVersion': webGLVersion,
};
```

### `WasmGMTests.LoadResource(name, buffer)`
- **功能**：将测试资源（图像、字体等）加载到 WASM 内存中
- **参数**：
  - `name`：资源名称（字符串标识符）
  - `buffer`：ArrayBuffer 格式的资源数据
- **实现**：调用内部 `copyArrayBuffer` 将数据拷贝到 WASM 堆，然后通过 `_LoadResource` 传递给 C++
- **内存**：WASM 端获取数据所有权

### `copyArrayBuffer(buffer)`（内部函数）
- **功能**：将 ArrayBuffer 拷贝到 WASM 堆
- **实现**：
  ```javascript
  var ptr = WasmGMTests._malloc(buffer.byteLength);
  WasmGMTests.HEAPU8.set(new Uint8Array(buffer), ptr);
  return ptr;
  ```

## 内部实现细节

### WebGL 上下文创建

使用 Emscripten 的 `GL.createContext()` 和 `GL.makeContextCurrent()` 而非标准的 `canvas.getContext('webgl')`，因为 Emscripten 需要管理 WebGL 状态以协调 WASM 和 JavaScript 之间的 GL 调用。

### 资源加载内存模型

`LoadResource` 先在 JavaScript 侧通过 `_malloc` + `HEAPU8.set` 完成数据拷贝，然后将指针和长度传给 C++ 的 `_LoadResource`。C++ 端接管内存所有权，JavaScript 侧不需要释放。

### 离屏渲染优化

WebGL 上下文禁用了 depth（深度）和 stencil（模板）缓冲，因为 GM 测试在离屏 Canvas 上运行，不需要这些特性。禁用抗锯齿是因为 Skia 有自己的抗锯齿实现。

## 依赖关系

- **Emscripten 运行时**：`Module`、`GL.createContext`、`GL.makeContextCurrent`、`HEAPU8`、`_malloc`
- **C++ WASM 绑定**：`_LoadResource`
- **浏览器 API**：WebGL

## 设计模式与设计决策

1. **onRuntimeInitialized 模式**：使用 Emscripten 标准的运行时就绪回调，确保在 WASM 编译完成和内存初始化后才注册 JavaScript 函数。

2. **Emscripten GL 管理**：使用 Emscripten 的 GL 库而非原生 WebGL API，确保 WASM 中的 OpenGL 调用与 JavaScript 层的 WebGL 状态保持同步。

3. **数据所有权转移**：资源数据通过 WASM 内存传递给 C++，C++ 负责生命周期管理，避免了跨语言的引用计数。

## 性能考量

- 资源加载涉及从 JavaScript ArrayBuffer 到 WASM 堆的完整拷贝
- WebGL 上下文创建是一次性操作
- 禁用不需要的 WebGL 特性（depth、stencil）减少了内存和 GPU 开销
- `enableExtensionsByDefault: 1` 预加载所有 WebGL 扩展，避免运行时按需查询

## 相关文件

- `modules/canvaskit/gm_bindings.cpp` - GM 测试 C++ 绑定
- `modules/canvaskit/WasmCommon.h` - WASM 通用头文件
- `gm/` - Skia GM 测试源码目录
- `tools/gm_runner.js` - GM 测试浏览器端运行器
