# CanvasKit Externs - Closure Compiler 外部声明文件

> 源文件: `modules/canvaskit/externs.js`

## 概述

externs.js 是 CanvasKit 的 Google Closure Compiler 外部声明（externs）文件。它的核心目的是防止 Closure 编译器在代码压缩（minification）过程中重命名 CanvasKit 的公共 API 和内部绑定名称。该文件通过声明空对象和空函数骨架，告知编译器哪些标识符具有特殊含义，不应被混淆。文件涵盖了 CanvasKit 的全部公共对象、方法、常量、枚举，以及 Emscripten 提供的运行时符号和浏览器 Canvas API 的 polyfill 声明。

## 架构位置

该文件在 CanvasKit 的构建流程中作为 Closure Compiler 的外部输入，不参与运行时执行：

```
构建流程：
  CanvasKit JS 源码
    + C++ Emscripten 绑定
    + externs.js ← 本文件（编译器提示）
    → Closure Compiler
    → 压缩后的 canvaskit.js
```

## 主要类与结构体

本文件声明了 CanvasKit 的完整 API 表面，主要包括：

### 顶级工厂函数
- 颜色创建：`Color`, `Color4f`, `ColorAsInt`
- 几何构造：`LTRBRect`, `XYWHRect`, `LTRBiRect`, `XYWHiRect`, `RRectXY`
- Surface 创建：`MakeCanvasSurface`, `MakeSWCanvasSurface`, `MakeSurface`, `MakeRenderTarget`
- 图像创建：`MakeImage`, `MakeImageFromEncoded`, `MakeAnimatedImageFromEncoded`
- 其他：`MakePicture`, `MakeVertices`, `Malloc`, `Free`

### 核心渲染类
- **Canvas**：48+ 个公共方法和对应的私有方法（`_drawRect`, `_drawPath` 等）
- **Paint**：样式设置方法（`setAntiAlias`, `setShader`, `setImageFilter` 等）
- **Path** / **PathBuilder**：路径构建和操作
- **Surface**：Surface 生命周期管理
- **Image**：图像编解码和着色器创建

### 文本相关类
- **Font**：字体度量和字形 ID 查询
- **FontMgr** / **TypefaceFontProvider** / **FontCollection**：字体管理
- **Typeface**：字体数据加载
- **TextBlob**：文本渲染对象
- **Paragraph** / **ParagraphBuilder**：段落排版

### 效果类
- **ColorFilter**：颜色滤镜（Blend, Compose, Matrix 等）
- **ImageFilter**：图像滤镜（Blur, DropShadow, DisplacementMap 等）
- **Shader**：着色器（渐变, 噪声, 混合）
- **PathEffect**：路径效果（Dash, Corner, Discrete）
- **MaskFilter**：遮罩滤镜
- **RuntimeEffect**：运行时着色器

### 动画类
- **Animation** / **ManagedAnimation**：Lottie 动画播放
- **AnimatedImage**：动画图像（GIF/WebP）

### 辅助类
- **GrDirectContext**：GPU 资源管理
- **PictureRecorder**：绘制录制
- **Vertices**：顶点数据
- **ContourMeasureIter** / **ContourMeasure**：路径测量

### 数学类
- **Matrix**：3x3 变换矩阵
- **M44**：4x4 变换矩阵
- **Vector**：向量运算
- **ColorMatrix**：颜色矩阵

### 调试类
- **SkpDebugPlayer**：SKP 文件调试播放器

## 公共 API 函数

本文件仅声明函数签名，不包含实现。所有声明的函数分为两类：

1. **公共 API**（如 `Canvas.prototype.drawRect`）：用户直接调用
2. **私有 API**（如 `Canvas._drawRect`）：JavaScript 绑定内部调用 C++ 绑定

## 内部实现细节

### 枚举常量声明

文件声明了大量枚举类型：
- **AlphaType**：Opaque, Premul, Unpremul
- **BlendMode**：29 种混合模式（Clear 到 Luminosity）
- **ColorType**：11 种颜色类型（Alpha_8 到 RGBA_F32）
- **FillType**：Winding, EvenOdd
- **FilterMode**：Linear, Nearest
- **FontWeight**：11 级（Invisible 到 ExtraBlack）
- **PaintStyle**：Fill, Stroke
- **PathOp**：5 种路径操作
- **TileMode**：Clamp, Repeat, Mirror, Decal
- **TextAlign**：Left, Right, Center, Justify, Start, End
- 等等

### Emscripten 堆类型声明

```javascript
HEAPF32: {},  // Float32Array
HEAPF64: {},  // Float64Array
HEAPU8: {},   // Uint8Array
HEAPU16: {},  // Uint16Array
HEAPU32: {},  // Uint32Array
HEAP8: {},    // Int8Array
HEAP16: {},   // Int16Array
HEAP32: {},   // Int32Array
```

### 浏览器 API Polyfill 声明

文件末尾声明了 Canvas 2D API 的完整接口，包括：
- `CanvasRenderingContext2D`：40+ 个方法
- `Path2D`：路径构建方法
- `LinearCanvasGradient` / `RadialCanvasGradient`
- `ImageData` / `DOMMatrix`

### 原型链扩展声明

```javascript
CanvasKit.Paragraph.prototype.getRectsForRange = function() {};
CanvasKit.Surface.prototype.flush = function() {};
CanvasKit.RuntimeEffect.prototype.makeShader = function() {};
```
在 JS 中新声明的原型方法需要在此额外声明，否则 Closure 可能仍会混淆它们。

## 依赖关系

- **Google Closure Compiler**：作为编译器的外部声明输入
- **Emscripten**：声明 WASM 运行时提供的堆视图和内存管理函数
- **浏览器标准**：声明 HTML Canvas API 以防止混淆

## 设计模式与设计决策

1. **防御性声明**：即使某些函数在 JS 中已定义，也需要在 externs 中声明，因为 Closure 编译器会独立分析每个文件。

2. **公私分离**：公共 API（如 `drawRect`）和私有 API（如 `_drawRect`）均需声明，因为 JS 绑定代码会在运行时通过字符串名称引用它们。

3. **手动维护**：由于 Emscripten 不支持自动生成 externs 文件，该文件需要与 C++ 绑定和 JS 接口保持手动同步。

4. **类型注解**：通过 JSDoc 注解（如 `/** @return {CanvasKit.Image} */`）为 Closure 提供类型信息。

## 性能考量

- 该文件不影响运行时性能，仅影响编译器输出
- 正确的 externs 声明确保压缩后的代码与未压缩版本行为一致
- 缺少 externs 声明会导致属性名被混淆，引发运行时 undefined 错误

## 补充说明

### Closure Compiler 混淆问题

如果某个属性未在 externs 中声明，Closure Compiler 可能将其重命名（例如 `drawRect` -> `a`），但 Emscripten 生成的绑定代码仍然使用原始名称引用，导致运行时 `undefined` 错误。因此，externs 文件的完整性至关重要。

### 公共 API vs 私有 API 命名约定

- **公共 API**（无前缀）：由 JavaScript 用户直接调用，如 `Canvas.prototype.drawRect`
- **私有 API**（`_` 前缀）：由 JavaScript 绑定层内部调用 C++ 实现，如 `Canvas._drawRect`
- **原型方法**：在 `prototype` 对象下声明，表示实例方法

私有 API 需要在 externs 中声明是因为 JavaScript 绑定代码（如 interface.js）在运行时通过字符串名称引用这些方法。

### 维护指南

开发新的 CanvasKit 功能时需要同步更新 externs.js：
1. 在 C++ 绑定中添加新函数
2. 在 JavaScript 绑定中使用新函数
3. 在 externs.js 中声明新函数签名
4. 运行 `./compile.sh` 验证 Release 构建无混淆错误

缺失 externs 声明通常表现为：Debug 构建正常，Release（压缩）构建失败。

### 浏览器 API 声明的必要性

文件末尾大量的 `CanvasRenderingContext2D`、`Path2D` 等声明是因为 CanvasKit 可选地包含一个 Canvas 2D API 兼容层。如果这些标准 API 名称被 Closure 混淆，兼容层将无法正常工作。

### 枚举值作为常量

所有枚举（如 `BlendMode`、`ColorType`、`TileMode`）声明为空对象 `{}`，这告诉 Closure 这些是属性名称占位符，实际值由 C++ 绑定在运行时填充。

### API 分类统计

根据文件内容的统计分析：

| 类别 | 类/对象数量 | 公共方法数（约） | 私有方法数（约） |
|------|-----------|----------------|----------------|
| 渲染核心 | Canvas, Paint, Surface | 80+ | 50+ |
| 路径操作 | Path, PathBuilder | 40+ | 30+ |
| 图像处理 | Image, ImageFilter, ColorFilter | 30+ | 15+ |
| 文本排版 | Font, Paragraph, TextBlob, Typeface | 50+ | 20+ |
| 着色器 | Shader, RuntimeEffect | 15+ | 10+ |
| 动画 | Animation, ManagedAnimation | 20+ | 10+ |
| 数学工具 | Matrix, M44, Vector, ColorMatrix | 25+ | 0 |
| 枚举常量 | 25+ 枚举类型 | N/A | N/A |
| Emscripten | HEAP 类型, malloc/free | N/A | 10+ |
| 浏览器 API | Canvas2D, Path2D 等 | 40+ | 0 |

总计约 400+ 个独立的函数/属性声明，使其成为 CanvasKit 中最大的单个文件之一。

## 相关文件

- `modules/canvaskit/compile.sh` - 构建脚本（传递 externs 文件给 Closure）
- `modules/canvaskit/interface.js` - 公共 JS 接口实现
- `modules/canvaskit/canvaskit_bindings.cpp` - C++ Emscripten 绑定
- `modules/canvaskit/cpu.js` - CPU 后端 JS 绑定
- `modules/canvaskit/font.js` - 字体 JS 绑定
- `modules/canvaskit/rt_shader.js` - 运行时着色器 JS 绑定
