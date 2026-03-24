# CanvasKit 核心 C++ 绑定 (canvaskit_bindings)

> 源文件: `modules/canvaskit/canvaskit_bindings.cpp`

## 概述

`canvaskit_bindings.cpp` 是 CanvasKit 最核心且最大的 C++ 绑定文件，约 3260 行代码。它通过 Emscripten 的 `embind` 机制，将 Skia 的绝大部分核心图形 API 暴露给 JavaScript/WebAssembly 环境。涵盖范围包括：画布（Canvas）操作、路径（Path）创建与操作、画笔（Paint）配置、图像（Image）解码与编码、着色器（Shader）和滤镜（Filter）、GPU 上下文（GrDirectContext）与渲染表面（Surface）管理、文本绘制（Font/TextBlob）、颜色空间（ColorSpace）、路径效果（PathEffect）、运行时效果（RuntimeEffect/SkSL）等。该文件是 CanvasKit 功能的中枢。

## 架构位置

```
JavaScript 应用 / CanvasKit JS 辅助层
  └── EMSCRIPTEN_BINDINGS(Skia)  ← canvaskit_bindings.cpp
      ├── SkCanvas — 绘图操作
      ├── SkPaint — 画笔配置
      ├── SkPath / SkPathBuilder — 路径创建
      ├── SkImage — 图像加载与操作
      ├── SkSurface — 渲染表面
      ├── GrDirectContext — GPU 上下文（WebGL/WebGPU）
      ├── SkShader / SkColorFilter / SkImageFilter — 效果链
      ├── SkFont / SkTextBlob / SkTypeface — 文本系统
      ├── SkRuntimeEffect — SkSL 着色器
      ├── SkPicture / SkPictureRecorder — 录制与回放
      ├── SkColorSpace — 颜色空间管理
      ├── SkPathEffect — 路径效果
      ├── SkVertices — 顶点绘制
      └── 各种枚举常量
```

## 主要类与结构体

### 辅助结构体

| 结构体 | 说明 |
|--------|------|
| `OptionalMatrix` | 从 WASM 指针可选构建 SkMatrix |
| `SimpleImageInfo` | 简化的图像信息（width, height, colorType, alphaType, colorSpace） |
| `ColorSettings` | WebGL 颜色类型和像素格式配置 |
| `StrokeOpts` | 描边路径参数（宽度、斜接限制、连接样式、端帽、精度） |
| `GradientBuilder` | 渐变着色器构建辅助（颜色数组处理、本地矩阵） |
| `RuntimeEffectUniform` | SkSL 运行时效果的 uniform 变量描述 |
| `TextureReleaseContext` | WebGL 纹理释放上下文 |

### GPU 相关类（条件编译）

| 类 | 说明 |
|----|------|
| `ExternalWebGLTexture` | 包装 WebGL 纹理的 `GrExternalTexture` 实现 |
| `WebGLTextureImageGenerator` | 延迟创建 WebGL 纹理的图像生成器 |

## 公共 API 函数

### 图像解码与创建

| 函数 | 说明 |
|------|------|
| `DecodeImageData(data)` | 自动检测格式并解码图像（支持 BMP/GIF/ICO/JPEG/PNG/WBMP/WEBP） |
| `_decodeImage(ptr, len)` | 解码静态图像 |
| `_decodeAnimatedImage(ptr, len)` | 解码动画图像 |
| `_MakeImage(ii, pPtr, plen, rowBytes)` | 从像素数据创建图像 |

### GPU 表面创建（WebGL）

| 函数 | 说明 |
|------|------|
| `_MakeGrContext()` | 创建 GL 渲染上下文 |
| `_MakeOnScreenGLSurface(ctx, w, h, colorSpace, [sc, st])` | 创建屏上 GL 表面 |
| `_MakeRenderTargetWH(ctx, w, h)` / `_MakeRenderTargetII(ctx, ii)` | 创建离屏渲染目标 |

### 路径操作

| 函数 | 说明 |
|------|------|
| `Apply*` 系列 | 路径构建链式操作（MoveTo, LineTo, CubicTo, ArcTo 等） |
| `ToCmds(path)` | 将路径导出为命令数组 |
| `MakePathFromCmds(ptr, numCmds)` | 从命令数组创建路径 |
| `MakePathFromSVGString(str)` | 从 SVG 路径字符串创建路径 |
| `ToSVGString(path)` | 将路径导出为 SVG 字符串 |
| `MakePathFromInterpolation(path1, path2, weight)` | 路径插值 |
| `MakeDashed(path, on, off, phase)` | 创建虚线路径 |
| `MakeTrimmed(path, startT, stopT, isComplement)` | 创建截取路径 |
| `MakeStroked(path, opts)` | 将描边路径转换为填充路径 |

### 绑定的核心类

**CanvasKit 绑定了以下 Skia 核心类（部分列表）**：

| 类 | 关键方法 |
|----|---------|
| `SkCanvas` | clear, clipPath/Rect/RRect, concat, drawPath/Image/Circle/Line/Text/Glyphs, save/restore, rotate/scale/translate |
| `SkPaint` | setColor, setStyle, setStrokeWidth, setAntiAlias, setShader, setColorFilter, setImageFilter, setBlendMode |
| `SkPath` / `SkPathBuilder` | moveTo, lineTo, cubicTo, quadTo, conicTo, arcTo, close, transform, addPath |
| `SkImage` | width/height, readPixels, encodeToBytes, makeShader, getImageInfo, getColorSpace |
| `SkSurface` | getCanvas, makeImageSnapshot, flush, reportBackendCreationFailure, makeSurface |
| `SkShader` | MakeLinearGradient, MakeRadialGradient, MakeSweepGradient, MakeTwoPointConicalGradient, MakeColor, MakeBlend, MakeFractalNoise, MakeTurbulence |
| `SkColorFilter` | MakeBlend, MakeCompose, MakeLerp, MakeMatrix, MakeSRGBToLinearGamma, MakeLuma |
| `SkImageFilter` | MakeBlur, MakeColorFilter, MakeCompose, MakeDropShadow, MakeErode, MakeDilate, MakeDisplacementMap, MakeImage, MakeOffset, MakeShader |
| `SkPathEffect` | MakeDash, MakeDiscrete, MakeCorner, MakePath1D, MakePath2D, MakeCompose |
| `SkFont` | setSize, setTypeface, getMetrics, getGlyphWidths, getGlyphIDs |
| `SkTextBlob` | MakeFromText, MakeFromGlyphs, MakeFromRSXform |
| `SkTypeface` | MakeTypefaceFromData, getGlyphIDs |
| `SkPicture` / `SkPictureRecorder` | 录制与序列化 |
| `SkColorSpace` | SRGB, DISPLAY_P3, ADOBE_RGB, Equals |
| `SkRuntimeEffect` | MakeForShader, MakeForBlender, MakeForColorFilter |
| `SkVertices` | MakeCopy（自定义顶点绘制） |
| `SkContourMeasure` | getLength, getPosTan, getSegment |

### 枚举常量

文件导出了大量枚举：`AlphaType`, `BlendMode`, `BlurStyle`, `ClipOp`, `ColorType`, `FillType`, `FilterMode`, `FontEdging`, `FontHinting`, `ImageFormat`, `MipmapMode`, `PaintStyle`, `PathOp`, `PointMode`, `StrokeCap`, `StrokeJoin`, `TileMode`, `VertexMode` 等。

## 内部实现细节

### Apply* 包装模式

所有路径操作使用 `Apply*` 包装函数，返回 void 而非路径对象。这避免了 Emscripten 默认绑定中返回值不被 JS 捕获时的内存泄漏问题。JS 端的 `interface.js` 将这些方法包装为链式调用。

### 图像解码器按需编译

通过 `SK_CODEC_DECODES_*` 条件编译宏，客户端可选择编译哪些图像格式支持，从而控制 WASM 包大小。`DecodeImageData` 按固定顺序尝试每种解码器。

### 路径命令数组格式

`ToCmds`/`MakePathFromCmds` 使用紧凑的浮点数组格式：命令类型（MOVE=0, LINE=1, QUAD=2, CONIC=3, CUBIC=4, CLOSE=5）后跟对应数量的坐标值。

### RuntimeEffect uniform 类型转换

`castUniforms` 将 JS 传入的浮点 uniform 数据中的整数类型字段转换为正确的位模式，因为 JS 端统一以 float 传递所有 uniform 数据。

### WebGL 表面创建

`MakeOnScreenGLSurface` 包装 FBO 0（屏上帧缓冲区）为 Skia 渲染目标，在创建前清除颜色和模板缓冲区并重置 Skia 的 GL 状态。根据颜色空间自动选择 RGBA8 或 RGBA16F 格式。

### WebGPU 表面创建

`MakeGPUTextureSurface` 从 JS 端导入 WebGPU 纹理，使用 `emscripten_webgpu_import_texture` 转换为 C++ 句柄。`ReplaceBackendTexture` 支持交换链纹理的高效替换。

### 序列化与反序列化

SkPicture 序列化时包含字体数据（`always_save_typeface_bytes`），反序列化时注册 FreeType 字体工厂并使用自定义图像解码回调。

### 析构器处理

对于 `SkContourMeasure`、`SkVertices`、`SkTextBlob`、`SkTypeface` 等具有私有析构器的类，提供空的 `raw_destructor` 特化以满足 Emscripten 要求。

## 依赖关系

该文件依赖范围极广，涵盖 Skia 的几乎所有核心模块：

| 类别 | 主要依赖 |
|------|---------|
| 核心 | SkCanvas, SkPaint, SkPath, SkImage, SkSurface, SkColor, SkData, SkStream |
| 效果 | SkShader, SkColorFilter, SkImageFilter, SkPathEffect, SkBlender |
| GPU | GrDirectContext, GrGLInterface, SkSurfaceGanesh（WebGL），WebGPU 头文件 |
| 文本 | SkFont, SkTextBlob, SkTypeface, SkFontMgr |
| 编码 | SkPngEncoder, SkJpegEncoder, SkWebpEncoder |
| 解码 | SkCodec 及各格式解码器（条件编译） |
| SkSL | SkRuntimeEffect, SkSLCompiler, SkSLDebugTrace |
| 路径操作 | SkPathOps（条件编译） |
| 工具 | SkParsePath, SkShadowUtils |
| Emscripten | emscripten.h, emscripten/bind.h, emscripten/html5.h |

## 设计模式与设计决策

- **条件编译架构**: 大量使用 `#ifdef` 控制功能模块（GPU/WebGL/WebGPU/Fonts/PathOps/RuntimeEffect/序列化等），允许构建不同功能子集的 WASM 包
- **Apply 包装模式**: 所有修改型路径操作返回 void 而非对象，防止 Emscripten 绑定中的内存泄漏
- **指针传递优化**: 颜色、矩形、矩阵等数据通过 WASM 指针传递，避免 Emscripten 值对象的序列化开销
- **GradientBuilder 模式**: 使用辅助结构体处理渐变参数的复杂转换（颜色格式、本地矩阵、插值模式）
- **按需解码器**: 图像解码器通过编译标志按需包含，最小化 WASM 包大小
- **常量标记**: `constant("gpu", true)` 等允许 JS 端检测特定功能是否可用
- **select_overload**: 使用 Emscripten 的 `select_overload` 处理 C++ 函数重载

## 性能考量

- 路径命令数组使用紧凑浮点格式，减少跨边界传输量
- GPU 表面创建时自动查询采样数和模板位，避免不必要的显式配置
- 图像编码支持质量参数控制（JPEG/WebP），允许在质量和大小间取舍
- `DecodeImageData` 按固定顺序尝试解码器，首次匹配即返回，避免不必要的尝试
- SkPicture 反序列化使用 `SkOnce` 确保字体工厂只注册一次
- `toBytes` 使用 `typed_memory_view` + `slice` 创建 WASM 堆外的独立副本，避免 use-after-free
- WebGL 表面创建包含完整的 GL 状态重置，确保 Skia 状态机一致性

## 相关文件

- `modules/canvaskit/WasmCommon.h` — WASM 指针类型和辅助函数（MakeTypedArray 等）
- `modules/canvaskit/interface.js` — JS 端的链式调用包装
- `modules/canvaskit/memory.js` — JS/WASM 内存管理
- `modules/canvaskit/webgl.js` — WebGL 上下文管理
- `modules/canvaskit/color.js` — 颜色工具
- `modules/canvaskit/matrix.js` — 矩阵工具
- `include/core/*.h` — Skia 核心头文件
- `include/effects/*.h` — Skia 效果头文件
