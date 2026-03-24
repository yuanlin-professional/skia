# CanvasKit - Skia 的 WebAssembly 绑定库

## 概述

CanvasKit 是 Skia 图形引擎的 WebAssembly (WASM) 封装层，它将 Skia 强大的 C++ 2D 图形能力
带入了 Web 浏览器和 Node.js 环境。通过 Emscripten 工具链将 Skia 的核心 C++ 代码编译为
WebAssembly 字节码，CanvasKit 为 JavaScript/TypeScript 开发者提供了一套接近原生性能的
高级图形绘制 API。

CanvasKit 的设计目标是作为 HTML5 Canvas API 的高性能替代品，同时提供远超标准 Canvas 2D
的功能集。它支持高级文本排版（通过 skparagraph 模块）、Lottie 动画播放（通过 Skottie 模块）、
路径操作（PathOps）、运行时着色器（Runtime Shader / SkSL）、以及 GPU 加速渲染（通过 WebGL
和实验性的 WebGPU 后端）。CanvasKit 被 Flutter Web 引擎深度集成，是其核心渲染基础设施。

从架构上看，CanvasKit 采用分层绑定设计：底层是 C++ 绑定文件（如 `canvaskit_bindings.cpp`），
使用 Emscripten 的 `embind` 机制将 Skia 的 C++ 类和函数暴露给 JavaScript；上层是一组
JavaScript 文件（如 `interface.js`、`font.js`、`paragraph.js` 等），对底层绑定进行包装，
提供更符合 JavaScript 习惯的 API，包括方法链、自动内存管理辅助、以及 TypedArray 数据转换等。

CanvasKit 以 npm 包 `canvaskit-wasm` 的形式发布，当前版本为 0.41.0。它提供三种构建变体：
默认版（精简）、完整版（含 Skottie 等扩展）、以及性能分析版（含完整函数名的 profiling 构建）。
构建系统同时支持 GN 和 Bazel 两种构建方式。

## 架构图

```
+----------------------------------------------------------------------+
|                        JavaScript / TypeScript 应用层                  |
+----------------------------------------------------------------------+
          |                    |                      |
          v                    v                      v
+------------------+  +------------------+  +------------------+
|   preamble.js    |  |   interface.js   |  |   postamble.js   |
|  (作用域开始)     |  | (核心 JS 封装)    |  |  (作用域结束)     |
+------------------+  +------------------+  +------------------+
          |                    |                      |
          v                    v                      v
+----------------------------------------------------------------------+
|                       JS 功能模块层                                    |
|  +----------+ +--------+ +-----------+ +--------+ +----------+       |
|  | color.js | |font.js | |paragraph.js| |webgl.js| |skottie.js|      |
|  +----------+ +--------+ +-----------+ +--------+ +----------+       |
|  +----------+ +--------+ +-----------+ +--------+ +----------+       |
|  |memory.js | |matrix.js| |pathops.js | |webgpu.js| | bidi.js |      |
|  +----------+ +--------+ +-----------+ +--------+ +----------+       |
|  +----------+ +--------+ +-----------+ +----------+                  |
|  | util.js  | | skp.js | |rt_shader.js| |debugger.js|                |
|  +----------+ +--------+ +-----------+ +----------+                  |
+----------------------------------------------------------------------+
          |                    |                      |
          v                    v                      v
+----------------------------------------------------------------------+
|              Emscripten embind 绑定层 (C++ -> WASM -> JS)             |
|  +---------------------------+  +-----------------------------+      |
|  | canvaskit_bindings.cpp    |  | paragraph_bindings.cpp      |      |
|  | (核心绑定: Canvas, Paint, |  | paragraph_bindings_gen.cpp  |      |
|  |  Path, Image, Surface,   |  | (段落排版绑定)               |      |
|  |  ColorFilter, Shader...) |  +-----------------------------+      |
|  +---------------------------+  +-----------------------------+      |
|  +---------------------------+  | skottie_bindings.cpp        |      |
|  | WasmCommon.h              |  | (Lottie 动画绑定)           |      |
|  | (WASM 类型定义与工具)      |  +-----------------------------+      |
|  +---------------------------+  +-----------------------------+      |
|  +---------------------------+  | debugger_bindings.cpp       |      |
|  | bidi_bindings.cpp         |  | (SKP 调试器绑定)            |      |
|  | bidi_bindings_gen.cpp     |  +-----------------------------+      |
|  | (双向文本绑定)             |  +-----------------------------+      |
|  +---------------------------+  | viewer_bindings.cpp         |      |
|                                 | (查看器绑定)                |      |
|                                 +-----------------------------+      |
+----------------------------------------------------------------------+
          |                    |                      |
          v                    v                      v
+----------------------------------------------------------------------+
|                        Skia C++ 核心引擎                              |
|  +----------+ +------------+ +----------+ +----------+               |
|  |SkCanvas  | |SkParagraph | |Skottie   | |SkPathOps |               |
|  |SkPaint   | |SkUnicode   | |SkResources| |SkSL     |               |
|  |SkPath    | |SkShaper    | |SkSG      | |          |               |
|  |SkImage   | |HarfBuzz   | |          | |          |               |
|  |SkSurface | |ICU        | |          | |          |               |
|  +----------+ +------------+ +----------+ +----------+               |
+----------------------------------------------------------------------+
          |                    |
          v                    v
+---------------------------+  +---------------------------+
|  WebGL 后端 (Ganesh)      |  |  WebGPU 后端 (实验性)      |
|  GrDirectContext          |  |  Dawn / wgpu              |
|  GrGLInterface            |  |  emscripten html5_webgpu  |
+---------------------------+  +---------------------------+
          |                    |
          v                    v
+----------------------------------------------------------------------+
|                    浏览器 GPU / CPU 渲染                               |
+----------------------------------------------------------------------+
```

## 目录结构

```
modules/canvaskit/
|-- BUILD.gn                        # GN 构建配置（主构建文件）
|-- BUILD.bazel                     # Bazel 构建配置
|-- canvaskit.gni                   # GN 构建参数声明（功能开关）
|-- Makefile                        # 便捷构建目标（make release/debug/npm 等）
|-- compile.sh                      # GN 编译脚本（处理所有构建选项）
|-- compile_gm.sh                   # GM 测试编译脚本
|-- make_version.sh                 # 版本号生成脚本
|-- package.json                    # npm 开发依赖配置
|-- package-lock.json               # npm 依赖锁定文件
|-- karma.conf.js                   # Karma 测试运行器配置（传统模式）
|-- karma.bazel.js                  # Karma 测试运行器配置（Bazel 模式）
|-- CHANGELOG.md                    # 版本变更日志
|-- README.md                       # 英文说明文档
|-- .gitignore                      # Git 忽略规则
|
|-- canvaskit_bindings.cpp          # 核心 C++ 绑定（Canvas/Paint/Path/Image 等）
|-- paragraph_bindings.cpp          # 段落排版 C++ 绑定
|-- paragraph_bindings_gen.cpp      # 段落排版自动生成绑定
|-- skottie_bindings.cpp            # Skottie (Lottie) 动画 C++ 绑定
|-- bidi_bindings.cpp               # 双向文本 C++ 绑定
|-- bidi_bindings_gen.cpp           # 双向文本自动生成绑定
|-- debugger_bindings.cpp           # SKP 调试器 C++ 绑定
|-- viewer_bindings.cpp             # 查看器 C++ 绑定
|-- gm_bindings.cpp                 # GM 测试 C++ 绑定
|-- WasmCommon.h                    # WASM 公共类型定义与工具头文件
|
|-- preamble.js                     # JS 作用域开始（包裹所有 JS 代码）
|-- postamble.js                    # JS 作用域结束
|-- interface.js                    # 核心 JS 接口封装（Path/Canvas/Surface 等）
|-- color.js                        # 颜色处理工具函数
|-- memory.js                       # 内存管理（Malloc/Free/copy 工具）
|-- util.js                         # 通用工具函数
|-- font.js                         # 字体与文本绘制 JS 封装
|-- paragraph.js                    # 段落排版 JS 封装
|-- bidi.js                         # 双向文本 JS 封装
|-- matrix.js                       # 矩阵辅助工具（3x3/4x4 变换）
|-- pathops.js                      # 路径布尔运算 JS 封装
|-- skottie.js                      # Skottie 动画 JS 封装
|-- rt_shader.js                    # 运行时着色器 (SkSL) JS 封装
|-- skp.js                          # SKP 序列化 JS 封装
|-- debugger.js                     # 调试器 JS 封装
|-- webgl.js                        # WebGL 后端 JS 封装
|-- webgpu.js                       # WebGPU 后端 JS 封装
|-- cpu.js                          # CPU 软件渲染后端 JS 封装
|-- gm.js                           # GM 测试 JS 封装
|-- externs.js                      # Closure Compiler 外部声明
|-- debug.js                        # Debug 构建预注入脚本
|-- release.js                      # Release 构建预注入脚本
|-- catchExceptionNop.js            # 异常捕获空操作
|
|-- htmlcanvas/                     # HTML Canvas 2D API 兼容层
|-- tests/                          # 单元测试与 GM 测试
|-- npm_build/                      # npm 包发布目录
|-- fonts/                          # 内嵌字体资源
|-- external_test/                  # 外部 TypeScript 集成测试
|-- future_apis/                    # 未来 Web API 研究文档
|-- go/                             # Go 语言测试环境工具
|-- wasm_tools/                     # WASM 分析与调试工具
```

## 关键类与函数

### C++ 绑定层（canvaskit_bindings.cpp）

CanvasKit 的核心绑定文件约有数千行代码，使用 Emscripten 的 `EMSCRIPTEN_BINDINGS` 宏将
Skia C++ 类暴露给 JavaScript。以下是主要绑定的类：

| 绑定名称 | 对应 Skia 类 | 功能说明 |
|---------|-------------|---------|
| `Canvas` | `SkCanvas` | 绘图画布，提供 draw* 系列方法 |
| `Paint` | `SkPaint` | 绘制属性（颜色、描边、混合模式等） |
| `Path` / `PathBuilder` | `SkPath` / `SkPathBuilder` | 矢量路径构建与操作 |
| `Image` | `SkImage` | 位图图像 |
| `Surface` | `SkSurface` | 渲染目标表面 |
| `Shader` | `SkShader` | 着色器（渐变、图案等） |
| `ColorFilter` | `SkColorFilter` | 颜色滤镜 |
| `ImageFilter` | `SkImageFilter` | 图像滤镜（模糊、阴影等） |
| `PathEffect` | `SkPathEffect` | 路径效果（虚线、圆角等） |
| `MaskFilter` | `SkMaskFilter` | 遮罩滤镜 |
| `Typeface` | `SkTypeface` | 字体类型 |
| `Font` | `SkFont` | 字体实例（字号、变体等） |
| `FontMgr` | `SkFontMgr` | 字体管理器 |
| `PictureRecorder` | `SkPictureRecorder` | 绘制录制器 |
| `Picture` | `SkPicture` | 已录制的绘制操作 |
| `ColorSpace` | `SkColorSpace` | 色彩空间（SRGB/P3/Adobe RGB） |
| `TextBlob` | `SkTextBlob` | 文本绘制块 |
| `Vertices` | `SkVertices` | 顶点几何数据 |
| `GrDirectContext` | `GrDirectContext` | GPU 图形上下文 |
| `RuntimeEffect` | `SkRuntimeEffect` | SkSL 运行时效果 |
| `AnimatedImage` | `SkAnimatedImage` | 动画图像（GIF 等） |

### WasmCommon.h 类型定义

`WasmCommon.h` 定义了 WASM 与 JavaScript 之间的桥接类型：

```cpp
// 自描述类型别名
using JSColor = int32_t;
using JSArray = emscripten::val;
using JSObject = emscripten::val;
using WASMPointerF32 = uintptr_t;  // Float32Array 指针
using WASMPointerI32 = uintptr_t;  // Int32Array 指针
using WASMPointerU8  = uintptr_t;  // Uint8Array 指针

// JSSpan<T> - 高效 JS 数组访问
// MakeTypedArray<T> - 创建 JS TypedArray
```

`JSSpan<T>` 是一个关键的桥接模板类，它能自动检测 JS 数组是否通过 `CanvasKit.Malloc`
分配的，如果是则直接使用指针（零拷贝），否则执行数据拷贝。这种设计在性能关键路径上可
提供 5-20 倍的加速。

### JavaScript 接口层

**memory.js** - 内存管理核心：
- `CanvasKit.Malloc(TypedArray, len)` - 在 WASM 堆上分配内存
- `CanvasKit.Free(mallocObj)` - 释放 WASM 堆内存
- `copy1dArray(arr, dest, ptr)` - 将 JS 数组拷贝到 WASM 堆
- `copy3x3MatrixToWasm(matr)` / `copy4x4MatrixToWasm(matr)` - 矩阵数据转换
- `copyColorToWasm(color4f)` / `copyRectToWasm(fourFloats)` - 颜色/矩形数据转换

**interface.js** - 核心接口增强：
- `CanvasKit.Path.MakeFromCmds(cmds)` - 从命令数组创建路径
- `CanvasKit.Path.MakeFromVerbsPointsWeights(...)` - 从动词/点/权重创建路径
- `PathBuilder.prototype.addArc/addCircle/addOval/addPath(...)` - 路径构建方法链

**color.js** - 颜色工具：
- `CanvasKit.Color(r, g, b, a)` - CSS rgba() 风格颜色构造
- `CanvasKit.Color4f(r, g, b, a)` - 浮点颜色构造
- `CanvasKit.ColorAsInt(r, g, b, a)` - 32 位整数颜色构造
- 预定义常量：`TRANSPARENT`、`BLACK`、`WHITE`、`RED`、`GREEN`、`BLUE`

**webgl.js** - WebGL 后端：
- `CanvasKit.GetWebGLContext(canvas, attrs)` - 获取 WebGL 上下文
- `CanvasKit.MakeWebGLContext(ctx)` / `MakeGrContext(ctx)` - 创建 GPU 上下文
- `CanvasKit.MakeWebGLCanvasSurface(idOrElement, colorSpace)` - 创建 WebGL 表面
- `CanvasKit.MakeOnScreenGLSurface(grCtx, w, h, colorspace)` - 创建屏幕表面
- `Surface.prototype.makeImageFromTextureSource(src, info)` - 从纹理源创建图像

**webgpu.js** - WebGPU 后端（实验性）：
- `CanvasKit.MakeGPUDeviceContext(device)` - 从 WebGPU 设备创建上下文
- `CanvasKit.MakeGPUCanvasContext(devCtx, canvas, opts)` - 创建画布上下文
- `CanvasKit.MakeGPUCanvasSurface(canvasCtx, colorSpace)` - 创建 GPU 表面
- `CanvasKit.MakeGPUTextureSurface(devCtx, texture, ...)` - 从纹理创建表面

## 依赖关系

### 外部依赖

| 依赖项 | 用途 | 构建标志 |
|-------|------|---------|
| Emscripten SDK | C++ 到 WASM 编译工具链 | 必需 |
| Skia 核心库 | 2D 图形引擎 | 必需 |
| FreeType | 字体光栅化 | `skia_canvaskit_enable_font` |
| HarfBuzz | 文本整形 | `skia_use_harfbuzz` |
| ICU | Unicode 处理 | `skia_use_icu` |
| skparagraph | 段落排版 | `skia_canvaskit_enable_paragraph` |
| Skottie | Lottie 动画 | `skia_enable_skottie` |
| skresources | 动画资源管理 | `skia_enable_skottie` |
| sksg | Skottie 场景图 | `skia_enable_skottie` |
| libjpeg-turbo | JPEG 编解码 | `skia_use_libjpeg_turbo_*` |
| libpng | PNG 编解码 | `skia_use_libpng_*` |
| libwebp | WebP 编解码 | `skia_use_libwebp_*` |
| zlib | 压缩 | `skia_use_zlib` |
| wuffs | 安全图像解码 | `skia_use_wuffs` |

### 内部 Skia 模块依赖

```
canvaskit
  |-- skia (核心)
  |-- skparagraph (段落排版)
  |     |-- skunicode (Unicode)
  |     |-- skshaper (文本整形)
  |-- skottie (Lottie 动画)
  |     |-- skresources (资源加载)
  |     |-- sksg (场景图)
  |-- pathops (路径布尔运算)
  |-- skunicode (Unicode, 用于 bidi)
```

### 构建配置参数（canvaskit.gni）

`canvaskit.gni` 声明了所有可配置的构建开关：

| 参数名 | 默认值 | 说明 |
|-------|-------|------|
| `skia_canvaskit_enable_font` | `true` | 字体与文本支持 |
| `skia_canvaskit_enable_embedded_font` | `true` | 内嵌 NotoMono 字体 |
| `skia_canvaskit_enable_paragraph` | `true` | 段落排版支持 |
| `skia_canvaskit_enable_pathops` | `true` | 路径布尔运算 |
| `skia_canvaskit_enable_rt_shader` | `true` | 运行时着色器 (SkSL) |
| `skia_canvaskit_enable_matrix_helper` | `true` | 矩阵辅助工具 |
| `skia_canvaskit_enable_canvas_bindings` | `true` | HTML Canvas 兼容层 |
| `skia_canvaskit_enable_skp_serialization` | `true` | SKP 序列化 |
| `skia_canvaskit_enable_debugger` | `false` | SKP 调试器 |
| `skia_canvaskit_enable_webgl` | `false` | WebGL 后端 |
| `skia_canvaskit_enable_webgpu` | `false` | WebGPU 后端 |
| `skia_canvaskit_enable_bidi` | `false` | 双向文本支持 |
| `skia_canvaskit_profile_build` | `false` | 性能分析构建 |

## 设计模式分析

### 1. 模块化可裁剪架构

CanvasKit 采用高度模块化的设计，几乎每个功能模块都可以通过编译标志独立开关。这种设计
允许用户根据实际需求定制精简版本。例如，一个不需要文本和动画的应用可以通过
`./compile.sh no_skottie no_font` 将产物体积减少约 50%。

### 2. 预注入脚本模式（Pre-JS Pattern）

所有 JavaScript 模块通过 Emscripten 的 `--pre-js` 机制在编译时注入到最终输出中。
`preamble.js` 开启一个立即执行函数的作用域（IIFE），所有功能模块在同一作用域内共享状态，
最后由 `postamble.js` 关闭作用域。这种模式避免了全局命名空间污染，同时允许 Closure
Compiler 进行高效的代码压缩。

### 3. 零拷贝内存桥接

`WasmCommon.h` 中的 `JSSpan<T>` 模板和 `memory.js` 中的 `Malloc`/`Free` 机制实现了
JavaScript 与 WASM 之间的零拷贝数据传递。当用户通过 `CanvasKit.Malloc` 预分配内存时，
后续传递该内存块到 C++ 函数时无需额外拷贝，直接使用指针偏移访问。

### 4. 延迟初始化模式

通过 `_extraInitializations` 数组，各 GPU 后端（webgl.js / webgpu.js / cpu.js）注册
自己的初始化回调。在 WASM 运行时就绪后（`onRuntimeInitialized`），这些回调依次执行，
确保 GPU 上下文的创建不会过早发生。

### 5. Scratch Buffer 优化

`memory.js` 中预分配了多个 "scratch" 缓冲区（如 `_scratch3x3Matrix`、`_scratchColor`、
`_scratchRRect` 等），用于频繁的小型数据传输。这些缓冲区在初始化时一次分配，后续复用，
避免了每次函数调用时的 `malloc`/`free` 开销。

### 6. 优雅降级策略

`MakeWebGLCanvasSurface` 在 GPU 表面创建失败时，会自动回退到软件渲染模式
（`MakeSWCanvasSurface`），并将 canvas 元素替换为新的（未绑定 WebGL 上下文的）canvas，
确保应用在不支持 WebGL 的环境中仍然可用。

## 数据流

### 初始化流程

```
应用加载 canvaskit.js
        |
        v
CanvasKitInit({ locateFile }) ----> 加载 canvaskit.wasm
        |
        v
Emscripten 运行时初始化
        |
        v
onRuntimeInitialized() 回调执行
        |
        +---> 分配 scratch 缓冲区（颜色、矩阵、矩形等）
        +---> 创建预定义色彩空间（SRGB/P3/Adobe RGB）
        +---> 执行 _extraInitializations 回调
        |         +---> WebGL 初始化 (webgl.js)
        |         +---> 或 WebGPU 初始化 (webgpu.js)
        |         +---> 或 CPU 初始化 (cpu.js)
        |
        v
返回 CanvasKit 对象给 Promise
```

### 渲染流程（WebGL）

```
CanvasKit.MakeWebGLCanvasSurface(canvas)
        |
        v
GetWebGLContext(canvas, attrs) ----> 创建 WebGL2/WebGL1 上下文
        |
        v
MakeWebGLContext(ctx) ----> 创建 GrDirectContext
        |
        v
MakeOnScreenGLSurface(grCtx, w, h, colorspace) ----> 创建 SkSurface
        |
        v
surface.getCanvas() ----> 获取 SkCanvas
        |
        v
canvas.draw*() ----> JS 调用 -> embind -> Skia C++ 绘制命令
        |
        +---> 颜色/矩阵等参数通过 scratch 缓冲区传递
        +---> 数组数据通过 copy1dArray 拷贝到 WASM 堆
        |
        v
surface.flush() ----> Skia 提交 GPU 命令
```

### 内存管理流程

```
方式一：自动管理（简单但较慢）
  JS Array/TypedArray ---> copy1dArray() ---> WASM 堆拷贝 ---> C++ 使用 ---> _free()

方式二：手动管理（高性能）
  CanvasKit.Malloc(Float32Array, N) ---> 获取 WASM 堆指针
        |
        v
  mallocObj.toTypedArray() ---> 获取 TypedArray 视图（零拷贝）
        |
        v
  直接写入数据 ---> 传入 C++ 函数（通过指针，零拷贝）
        |
        v
  CanvasKit.Free(mallocObj) ---> 释放内存

方式三：Skia 对象生命周期
  new CanvasKit.Paint() ---> 创建 C++ 对象（通过 embind）
        |
        v
  paint.setColor(...) ---> 操作 C++ 对象
        |
        v
  paint.delete() ---> 释放 C++ 对象（必须手动调用！）
```

## 构建与使用

### 快速开始

```bash
# 安装 npm 依赖（仅首次或依赖变更时需要）
npm ci

# Release 构建（WebGL 后端）
make release

# Debug 构建
make debug

# 启动本地示例
make local-example
# 访问 http://localhost:8000/npm_build/example.html
```

### 编译选项

```bash
# CPU 软件渲染（无 GPU）
./compile.sh cpu

# WebGPU 后端（实验性）
./compile.sh webgpu

# 精简构建（无 Skottie、无字体）
./compile.sh no_skottie no_font

# Debug 构建
./compile.sh debug_build

# 性能分析构建
./compile.sh profiling
```

### npm 包使用

```javascript
// 浏览器
import CanvasKitInit from 'canvaskit-wasm';
// 或完整版
import CanvasKitInit from 'canvaskit-wasm/full';

const CanvasKit = await CanvasKitInit({
    locateFile: (file) => '/path/to/' + file,
});

// 创建 WebGL 加速的 Canvas 表面
const surface = CanvasKit.MakeWebGLCanvasSurface('myCanvas');
const canvas = surface.getCanvas();

// 绘制
const paint = new CanvasKit.Paint();
paint.setColor(CanvasKit.Color(255, 0, 0, 1.0));
canvas.drawRect(CanvasKit.LTRBRect(10, 10, 100, 100), paint);

surface.flush();
paint.delete();
```

## 测试

### 运行单元测试

```bash
# 构建后运行持续测试
make debug
make test-continuous

# 无头模式运行
make test-continuous-headless

# Bazel 测试
make bazel_test_canvaskit
```

### GM 测试

```bash
# 编译 GM 测试
make gm_tests

# 运行单个 GM
make single-gm
# 访问 http://localhost:8000/wasm_tools/gms.html
```

## 相关文档与参考

- **Skia 官方 CanvasKit 文档**: https://skia.org/docs/user/modules/canvaskit
- **npm 包**: https://www.npmjs.com/package/canvaskit-wasm
- **TypeScript 类型定义**: `npm_build/types/index.d.ts`
- **API 示例**: `npm_build/example.html`、`npm_build/extra.html`
- **变更日志**: `CHANGELOG.md`
- **Emscripten 文档**: https://emscripten.org/
- **embind 参考**: https://emscripten.org/docs/porting/connecting_cpp_and_javascript/embind.html
- **Skottie (Lottie) 模块**: `modules/skottie/`
- **段落排版模块**: `modules/skparagraph/`
- **在线调试工具**: https://jsfiddle.skia.org/canvaskit
- **Bug 提交**: https://skbug.com
- **性能测试工具**: `tools/perf-canvaskit-puppeteer/`
- **Gold 图形正确性**: https://gold.skia.org
- **Perf 性能监控**: https://perf.skia.org
