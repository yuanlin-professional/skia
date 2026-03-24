# webgpu.js

> 源文件: modules/canvaskit/webgpu.js

## 概述

`webgpu.js` 是 CanvasKit 模块中用于支持 WebGPU 渲染后端的 JavaScript 绑定文件。WebGPU 是现代浏览器提供的下一代图形 API,提供比 WebGL 更高的性能和更灵活的控制能力。该文件为 CanvasKit 添加了使用 WebGPU 进行硬件加速渲染的能力,包括设备上下文创建、Canvas 上下文管理、表面创建和动画帧请求等核心功能。

该模块实现了从 WebGPU 设备到 Skia 渲染表面的完整桥接,使得 Skia 可以直接使用 WebGPU 的纹理和渲染管线,从而在支持 WebGPU 的浏览器中获得最佳的渲染性能。

## 架构位置

在 Skia 架构中,`webgpu.js` 位于以下位置:

```
skia/
├── modules/
│   └── canvaskit/
│       ├── webgpu.js              # 本文件 - WebGPU 支持
│       ├── cpu.js                 # CPU 渲染后端
│       ├── canvaskit_bindings.cpp # C++ 绑定层
│       └── gpu_bindings.cpp       # GPU 相关绑定
└── src/
    └── gpu/
        ├── ganesh/                # Ganesh GPU 后端
        └── graphite/              # Graphite (新 GPU 后端)
```

该文件是 CanvasKit 的 GPU 渲染支持的一部分,与 `cpu.js` 形成互补关系 - `cpu.js` 提供软件渲染功能,而 `webgpu.js` 提供 WebGPU 硬件加速渲染功能。

## 主要类与结构体

### CanvasKit.MakeGPUDeviceContext(device)

创建 GPU 设备上下文的工厂方法。

**参数**:
- `device`: GPUDevice - WebGPU 设备对象

**返回值**:
- GrContext 对象,包含 `_device` 属性引用原始 WebGPU 设备
- 失败时返回 `null`

**功能**:
将 WebGPU 设备包装为 Skia 的 GrContext,使得 Skia 能够使用 WebGPU 进行渲染。

### CanvasKit.MakeGPUCanvasContext(devCtx, canvas, opts)

创建与 Canvas 元素关联的 GPU 上下文。

**参数**:
- `devCtx`: 设备上下文对象
- `canvas`: HTMLCanvasElement - DOM Canvas 元素
- `opts`: 配置选项对象
  - `format`: GPUTextureFormat - 纹理格式(可选)
  - `alphaMode`: GPUCanvasAlphaMode - Alpha 混合模式(可选)

**返回值**:
- Canvas 上下文对象,包含以下属性:
  - `_inner`: GPUCanvasContext - 实际的 WebGPU Canvas 上下文
  - `_deviceContext`: 设备上下文引用
  - `_textureFormat`: 使用的纹理格式
  - `requestAnimationFrame`: 动画帧请求方法

### CanvasKit.MakeGPUTextureSurface(devCtx, texture, textureFormat, width, height, colorSpace)

从 WebGPU 纹理创建 Skia 渲染表面。

**参数**:
- `devCtx`: 设备上下文
- `texture`: GPUTexture - WebGPU 纹理对象
- `textureFormat`: GPUTextureFormat - 纹理格式
- `width`: 表面宽度
- `height`: 表面高度
- `colorSpace`: 色彩空间(可选,默认为 null)

**返回值**:
- Surface 对象,可以用于获取 Canvas 并进行绘制

## 公共 API 函数

### CanvasKit.MakeGPUDeviceContext(device)

**详细说明**:
这是使用 WebGPU 渲染的第一步。该函数将浏览器提供的 GPUDevice 对象转换为 Skia 可以使用的 GrContext。

**实现细节**:
1. 验证 device 参数是否有效
2. 将 device 存储为 `preinitializedWebGPUDevice`,供 C++ 代码通过 `emscripten_webgpu_get_device()` 访问
3. 调用底层的 `_MakeGrContext()` 创建 Skia 的图形上下文
4. 在返回的上下文对象上附加 `_device` 属性以保持引用

**使用示例**:
```javascript
const adapter = await navigator.gpu.requestAdapter();
const device = await adapter.requestDevice();
const grContext = CanvasKit.MakeGPUDeviceContext(device);
```

### CanvasKit.MakeGPUCanvasContext(devCtx, canvas, opts)

**详细说明**:
将 HTML Canvas 元素配置为使用 WebGPU 渲染,并创建一个可以请求动画帧的上下文对象。

**配置流程**:
1. 从 Canvas 获取 WebGPU 上下文 (`canvas.getContext('webgpu')`)
2. 确定纹理格式:优先使用用户指定的格式,否则使用浏览器首选格式
3. 配置 Canvas 上下文:设置设备、格式和 Alpha 模式
4. 创建封装的上下文对象,包含内部上下文、设备上下文引用和格式信息
5. 添加 `requestAnimationFrame` 方法用于动画循环

**使用示例**:
```javascript
const canvasElement = document.getElementById('myCanvas');
const canvasCtx = CanvasKit.MakeGPUCanvasContext(grContext, canvasElement, {
  format: 'bgra8unorm',
  alphaMode: 'premultiplied'
});
```

### CanvasKit.MakeGPUCanvasSurface(canvasCtx, colorSpace, width, height)

**详细说明**:
从 Canvas 上下文的当前交换链纹理创建 Skia 渲染表面。这是实际进行绘制的表面。

**参数处理**:
- `width` 和 `height` 如果未指定,会自动使用 Canvas 的尺寸
- `colorSpace` 默认为 `null`,使用 sRGB 色彩空间

**实现**:
内部调用 `MakeGPUTextureSurface`,传递当前交换链纹理 (`context.getCurrentTexture()`)。

**返回的 Surface**:
- 附加了 `_canvasContext` 属性,用于后续的交换链管理

### Canvas上下文的 requestAnimationFrame 方法

**功能**:
为基于 WebGPU 的渲染提供动画循环机制。

**工作流程**:
1. 使用浏览器的 `requestAnimationFrame` 调度回调
2. 在回调中创建新的 Surface(基于当前交换链纹理)
3. 如果 Surface 创建失败,输出错误并返回
4. 调用用户提供的回调函数,传递 Canvas 对象
5. 刷新 Surface,将渲染内容提交到屏幕
6. 释放 Surface 资源

**使用示例**:
```javascript
canvasCtx.requestAnimationFrame((canvas) => {
  canvas.clear(CanvasKit.WHITE);
  // 执行绘制操作
  canvas.drawRect(...);
});
```

### Surface.prototype.assignCurrentSwapChainTexture()

**功能**:
将 Surface 的后端纹理替换为当前的交换链纹理。这对于多帧动画很重要。

**限制**:
只能在通过 `MakeGPUCanvasSurface` 创建的 Surface 上使用。

**返回值**:
- `true`: 替换成功
- `false`: 替换失败或 Surface 未绑定到 Canvas 上下文

### Surface.prototype.requestAnimationFrame(callback, dirtyRect)

**功能**:
Surface 级别的动画帧请求,支持增量渲染(通过 `dirtyRect` 指定脏区域)。

**GPU 模式处理**:
1. 检查 Surface 是否使用 GPU 后端
2. 如果使用 GPU,在每帧替换交换链纹理
3. 调用用户回调进行绘制
4. 刷新 Surface,可选地只刷新脏区域

**CPU 模式回退**:
如果 Surface 不是 GPU 后端,则调用内部的 `_requestAnimationFrameInternal` 方法。

### Surface.prototype.drawOnce(callback, dirtyRect)

**功能**:
执行一次性绘制操作,绘制完成后自动释放 Surface。

**适用场景**:
- 静态图像渲染
- 截图生成
- 非交互式内容

**实现**:
与 `requestAnimationFrame` 类似,但在刷新后调用 `dispose()` 释放资源。

## 内部实现细节

### Emscripten 集成

该文件依赖 Emscripten 的 `library_html5_webgpu.js` 工具库,主要使用以下功能:

**JsValStore**:
- JavaScript 值存储机制
- 允许 C++ 代码通过句柄访问 JavaScript 对象
- 使用 `JsValStore.add(obj)` 添加对象,返回句柄
- C++ 端通过 `emscripten_webgpu_import_*` 函数导入对象
- C++ 端负责通过 `emscripten_webgpu_release_js_handle` 释放句柄

**WebGPU 枚举映射**:
- `WebGPU.TextureFormat.indexOf(format)` 将格式字符串转换为枚举索引
- 确保 JavaScript 和 C++ 使用一致的枚举值

### 纹理格式处理

**自动格式选择**:
```javascript
let format = (opts && opts.format) ? opts.format : navigator.gpu.getPreferredCanvasFormat();
```

浏览器的首选格式通常是最优化的,使用它可以避免不必要的格式转换。

**常见格式**:
- `bgra8unorm`: Windows/Chrome 的默认格式
- `rgba8unorm`: 其他平台的常见格式

### 交换链管理

**交换链纹理的生命周期**:
1. 每帧通过 `getCurrentTexture()` 获取新纹理
2. 纹理用于创建或更新 Skia Surface
3. 渲染完成后,纹理自动返回到交换链
4. 下一帧重复此过程

**关键点**:
- 不需要手动管理纹理的释放
- 每帧必须获取新的纹理
- 旧纹理会在下次 `getCurrentTexture()` 调用时失效

### 上下文绑定与状态管理

**设备关联**:
- 每个 Surface 都与特定的设备上下文关联
- 通过 `_canvasContext` 属性保持对 Canvas 上下文的引用
- 确保交换链纹理与正确的设备配对

**状态检查**:
- `reportBackendTypeIsGPU()` 用于检查 Surface 是否使用 GPU 后端
- 这允许同一 API 同时支持 CPU 和 GPU 渲染

## 依赖关系

### JavaScript API 依赖

**WebGPU API**:
- `navigator.gpu`: WebGPU 入口点
- `GPUAdapter`: GPU 适配器
- `GPUDevice`: GPU 设备
- `GPUCanvasContext`: Canvas 的 WebGPU 上下文
- `GPUTexture`: 纹理对象

**浏览器 API**:
- `requestAnimationFrame`: 动画帧调度
- `HTMLCanvasElement`: Canvas DOM 元素

### CanvasKit 内部依赖

**核心对象**:
- `CanvasKit._MakeGrContext`: 创建图形上下文
- `CanvasKit._MakeGPUTextureSurface`: 从纹理创建 Surface
- `CanvasKit.JsValStore`: JavaScript 值存储
- `CanvasKit.WebGPU`: WebGPU 枚举映射

**Surface 方法**:
- `Surface.prototype._replaceBackendTexture`: 替换后端纹理
- `Surface.prototype.reportBackendTypeIsGPU`: 检查后端类型
- `Surface.prototype.getCanvas`: 获取绘图 Canvas
- `Surface.prototype.flush`: 刷新渲染内容
- `Surface.prototype.dispose`: 释放资源

### Emscripten 库依赖

- `library_html5_webgpu.js`: WebGPU 互操作工具
- `emscripten_webgpu_get_device()`: C++ 端获取设备
- `emscripten_webgpu_import_texture()`: 导入纹理对象

## 设计模式与设计决策

### 工厂模式

提供了三个工厂方法来创建不同层次的对象:
1. `MakeGPUDeviceContext`: 创建设备上下文
2. `MakeGPUCanvasContext`: 创建 Canvas 上下文
3. `MakeGPUCanvasSurface`/`MakeGPUTextureSurface`: 创建渲染表面

这种分层设计提供了灵活性,允许高级用户直接使用纹理,同时为常见用例提供便捷的封装。

### 句柄模式

使用 `JsValStore` 实现 JavaScript 对象的句柄管理:
- JavaScript 端不直接传递对象指针给 C++
- 通过句柄索引间接引用对象
- C++ 端可以安全地访问 JavaScript 对象
- 避免了跨语言边界的内存管理问题

### 适配器模式

该文件充当 WebGPU API 和 Skia 内部 API 之间的适配器:
- 转换 WebGPU 对象为 Skia 可用的格式
- 处理坐标系统和格式差异
- 提供统一的 API 接口

### 资源管理模式

**确定性资源释放**:
- `drawOnce` 方法在完成后自动调用 `dispose()`
- 每帧创建新 Surface,旧 Surface 被释放
- 避免资源累积和内存泄漏

**引用保持**:
- 在需要的地方保持对关键对象的引用(如 `_device`, `_canvasContext`)
- 防止 JavaScript 垃圾回收器过早回收对象

### 回退机制

通过 `reportBackendTypeIsGPU()` 检查,API 可以在 GPU 和 CPU 模式之间透明切换:
- 如果 GPU 不可用,自动回退到 CPU 渲染
- 用户代码无需修改
- 提高了代码的健壮性

## 性能考量

### 零拷贝纹理传输

**直接使用交换链纹理**:
- 不复制纹理数据,直接使用 WebGPU 提供的纹理
- Skia 直接渲染到交换链纹理
- 避免了 GPU 到 CPU 再到 GPU 的数据往返

**句柄传递**:
- 使用句柄而非对象复制传递数据
- 减少了 JavaScript 和 C++ 之间的数据传输开销

### 动画优化

**requestAnimationFrame 集成**:
- 与浏览器的刷新率同步
- 避免过度渲染
- 在浏览器准备好时才执行绘制

**增量渲染支持**:
- `dirtyRect` 参数允许指定需要更新的区域
- 只刷新变化的部分,提高性能

### 资源复用

**设备上下文复用**:
- 设备上下文只需创建一次
- 可以用于创建多个 Canvas 上下文和 Surface
- 避免了重复的设备初始化开销

**格式缓存**:
- Canvas 上下文缓存纹理格式
- 避免每帧重复查询浏览器首选格式

### 最佳实践

1. **复用设备上下文**: 应用启动时创建一次,全局复用
2. **批量绘制**: 在一个动画帧内完成所有绘制操作
3. **及时释放**: 使用 `drawOnce` 或手动调用 `dispose()` 释放不再需要的 Surface
4. **使用首选格式**: 不指定格式,让浏览器选择最优格式
5. **错误处理**: 检查所有创建函数的返回值,处理 null 情况

## 相关文件

### 同级别的渲染后端
- `modules/canvaskit/cpu.js` - CPU 软件渲染后端
- `modules/canvaskit/webgl.js` - WebGL 渲染后端

### C++ 绑定实现
- `modules/canvaskit/gpu_bindings.cpp` - GPU 相关的 C++ 绑定
- `modules/canvaskit/canvaskit_bindings.cpp` - 主要的 C++ 绑定

### Skia GPU 后端
- `src/gpu/ganesh/GrDirectContext.cpp` - Ganesh 直接上下文实现
- `src/gpu/ganesh/GrSurface.cpp` - GPU 表面实现
- `include/gpu/GpuTypes.h` - GPU 类型定义

### WebGPU 集成
- Emscripten 的 `library_html5_webgpu.js` - WebGPU 互操作库
- `modules/canvaskit/WasmCommon.h` - WebAssembly 通用定义

### 测试文件
- `modules/canvaskit/tests/webgpu_test.js` - WebGPU 功能测试
- `modules/canvaskit/tests/gpu_test.js` - 通用 GPU 测试

### 构建配置
- `modules/canvaskit/BUILD.bazel` - Bazel 构建规则
- `modules/canvaskit/compile_webgpu.sh` - WebGPU 编译脚本
