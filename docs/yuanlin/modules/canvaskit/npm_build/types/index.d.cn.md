# CanvasKit TypeScript 类型定义 (index.d.ts)

> 源文件: `modules/canvaskit/npm_build/types/index.d.ts`

## 概述

`index.d.ts` 是 CanvasKit npm 包的完整 TypeScript 类型定义文件，约 4948 行。它为 CanvasKit 的所有公共 API 提供了类型声明，涵盖初始化选项、核心图形接口（Canvas, Paint, Path, Image, Surface）、GPU 上下文（WebGL/WebGPU）、文本排版（Paragraph, Font, TextBlob）、动画（Skottie）、效果链（Shader, ColorFilter, ImageFilter, PathEffect, RuntimeEffect）、矩阵与向量工具、颜色工具以及大量枚举类型。该文件是 TypeScript 用户使用 CanvasKit 的必备类型基础设施，最低要求 TypeScript 4.4。

## 架构位置

```
TypeScript 应用
  └── import CanvasKitInit from 'canvaskit-wasm'  ← index.d.ts 提供类型
      └── CanvasKit 接口（完整类型化）
          ├── 核心类型: Canvas, Paint, Path, Image, Surface, ...
          ├── 工厂类型: ShaderFactory, ColorFilterFactory, ...
          ├── 枚举类型: BlendMode, ColorType, AlphaType, ...
          ├── 输入类型: InputRect, InputMatrix, InputColor, ...
          └── 辅助类型: MallocObj, WebGLContextHandle, ...
```

## 主要类与结构体

### 顶层接口

| 接口 | 说明 |
|------|------|
| `CanvasKitInitOptions` | 初始化选项（`locateFile`, `instantiateWasm`） |
| `CanvasKit` | 主入口接口，包含所有工厂方法、构造器、枚举和常量 |

### 核心绘图接口

| 接口 | 关键成员 |
|------|---------|
| `Canvas` | clear, clipPath/Rect/RRect, concat, drawImage/Path/Circle/Text/Glyphs, save/restore, rotate/scale/translate, readPixels, writePixels |
| `Paint` | setColor, setStyle, setStrokeWidth, setAntiAlias, setShader, setColorFilter, setImageFilter, setBlendMode, copy |
| `Path` | addArc, addPath, addRect/RRect/Oval, computeTightBounds, contains, dash, stroke, trim, toSVGString, toCmds |
| `PathBuilder` | moveTo, lineTo, cubicTo, quadTo, conicTo, arcTo, close, addRect/RRect/Oval, transform, snapshot, detach |
| `Image` | width, height, readPixels, encodeToBytes, makeShaderCubic/Options, getImageInfo, getColorSpace, makeCopyWithDefaultMipmaps |
| `Surface` | getCanvas, makeImageSnapshot, flush, dispose, makeSurface, reportBackendCreationFailure, makeImageFromTexture/TextureSource, updateTextureFromSource |

### GPU 接口

| 接口 | 说明 |
|------|------|
| `GrDirectContext` | getResourceCacheLimitBytes, getResourceCacheUsageBytes, setResourceCacheLimitBytes, releaseResourcesAndAbandonContext |
| `WebGPUDeviceContext` | WebGPU 设备上下文 |
| `WebGPUCanvasContext` | WebGPU 画布上下文 |

### 文本排版接口

| 接口 | 说明 |
|------|------|
| `Font` | setSize, setTypeface, getMetrics, getGlyphWidths/IDs/Bounds/Intercepts |
| `FontMgr` | countFamilies, getFamilyName |
| `Typeface` | getGlyphIDs |
| `TextBlob` | 不可变文本绘制单元 |
| `Paragraph` | didExceedMaxLines, getHeight/MaxWidth/MinIntrinsicWidth/MaxIntrinsicWidth, getRectsForRange/Placeholders, getGlyphInfoAt, getLineMetrics, layout |
| `ParagraphBuilder` | Make, MakeFromFontProvider, addText, pushStyle/pushPaintStyle, pop, build, reset |

### 效果链接口

| 接口 | 说明 |
|------|------|
| `Shader` / `ShaderFactory` | 着色器（渐变、噪声、颜色、混合） |
| `ColorFilter` / `ColorFilterFactory` | 颜色滤镜（混合、组合、矩阵、SRGB 转换） |
| `ImageFilter` / `ImageFilterFactory` | 图像滤镜（模糊、颜色、阴影、位移、膨胀/腐蚀） |
| `PathEffect` / `PathEffectFactory` | 路径效果（虚线、离散、圆角、1D/2D 路径） |
| `MaskFilter` / `MaskFilterFactory` | 遮罩滤镜（模糊） |
| `RuntimeEffect` / `RuntimeEffectFactory` | SkSL 运行时效果 |
| `Blender` / `BlenderFactory` | 混合器 |

### 动画接口

| 接口 | 说明 |
|------|------|
| `SkottieAnimation` | render, seek/seekFrame, duration, fps, size |
| `ManagedSkottieAnimation` | 扩展版：getColorProps, getOpacityProps, getTextProps, getTransformProps, setColor/Opacity/Text/Transform, getSlotInfo, slot 操作, 文本编辑器 |

### 矩阵与向量辅助

| 接口 | 说明 |
|------|------|
| `Matrix3x3Helpers` | identity, invert, mapPoints, multiply, rotated, scaled, skewed, translated |
| `Matrix4x4Helpers` | identity, translated, scaled, rotated, lookat, perspective, multiply, invert, transpose, setupCamera |
| `VectorHelpers` | dot, length, normalize, mulScalar, add, sub, dist, cross |
| `ColorMatrixHelpers` | identity, scaled, rotated, postTranslate, concat |

### 样式配置接口

| 接口 | 说明 |
|------|------|
| `ParagraphStyle` | textAlign, textDirection, maxLines, ellipsis, textStyle, strutStyle, heightMultiplier |
| `TextStyle` | color, fontFamilies, fontSize, fontStyle, letterSpacing, shadows, fontFeatures, fontVariations |
| `StrutStyle` | strutEnabled, fontFamilies, fontStyle, fontSize, heightMultiplier |

### 输入类型别名

| 类型 | 说明 |
|------|------|
| `InputRect` / `InputIRect` | 接受 Rect/IRect 或 MallocObj |
| `InputMatrix` | 接受 3x2/3x3/4x4 数组、DOMMatrix 或 MallocObj |
| `InputColor` | 接受 Color 或 MallocObj |
| `InputVector3` | 接受 Vector3 或 MallocObj |
| `TextureSource` | HTMLImageElement, HTMLVideoElement, HTMLCanvasElement, ImageBitmap, OffscreenCanvas, VideoFrame, ImageData |

## 公共 API 函数

### 默认导出

```typescript
export default function CanvasKitInit(opts?: CanvasKitInitOptions): Promise<CanvasKit>;
```

### CanvasKit 顶层方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `Color(r, g, b, a?)` | `Color` | CSS rgba 风格颜色 |
| `Color4f(r, g, b, a?)` | `Color` | 4-float 颜色 |
| `ColorAsInt(r, g, b, a?)` | `ColorInt` | 32 位整数颜色 |
| `parseColorString(str)` | `Color` | 解析 CSS 颜色字符串 |
| `Malloc(typedArray, len)` | `MallocObj` | WASM 堆内存分配 |
| `Free(m)` | `void` | 释放 Malloc 内存 |
| `MakeCanvasSurface(canvas)` | `Surface \| null` | 创建画布表面 |
| `MakeWebGLCanvasSurface(canvas, cs?, opts?)` | `Surface \| null` | WebGL 表面 |
| `MakeGPUCanvasSurface(ctx, cs, w?, h?)` | `Surface \| null` | WebGPU 表面 |
| `MakeImageFromEncoded(bytes)` | `Image \| null` | 解码图像 |
| `MakeAnimatedImageFromEncoded(bytes)` | `AnimatedImage \| null` | 解码动画图像 |
| `MakeManagedAnimation(json, assets?, ...)` | `ManagedSkottieAnimation` | 创建 Lottie 动画 |

## 内部实现细节

### 类型层次设计

- **EmbindObject**: 所有通过 Emscripten embind 绑定的 C++ 对象的基接口，提供 `delete()` 和 `deleteLater()` 方法以及 `isDeleted()` / `isAliasOf()` 查询
- **Saveable**: 支持 `save()`/`restore()`/`getSaveCount()` 的 Canvas 状态管理接口
- **readonly 构造器/工厂**: 使用 `readonly` 修饰确保类型安全，防止运行时赋值

### 灵活的输入类型

大量使用联合类型（如 `InputMatrix = MallocObj | number[] | Float32Array | DOMMatrix`）允许调用方以多种形式传入数据，匹配 JavaScript 端的灵活处理逻辑。

### 特性标记

通过可选属性标记编译时功能：
- `gpu?: boolean` — GPU 支持
- `skottie?: boolean` — Skottie 基础支持
- `managed_skottie?: boolean` — 高级 Skottie 支持
- `rt_effect?: boolean` — RuntimeEffect 支持

### WebGPU 类型集成

通过 `/// <reference types="@webgpu/types" />` 引用 WebGPU 类型定义，支持 `GPUDevice`、`GPUTexture` 等 WebGPU 原生类型。

### 枚举值类型

所有枚举使用 opaque 类型模式（如 `AlphaType` 包含 `Opaque`, `Premul`, `Unpremul` 属性），提供自动补全同时保持类型安全。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `@webgpu/types` | WebGPU 类型定义（通过 triple-slash 引用） |
| TypeScript >= 4.4 | 最低 TypeScript 版本要求 |

## 设计模式与设计决策

- **接口优于类**: 全部使用 `interface` 而非 `class`，因为实际对象来自 WASM，TypeScript 只需提供类型检查
- **工厂分离**: 将构造器接口（如 `FontConstructor`）和工厂接口（如 `ShaderFactory`）从主接口分离，保持 CanvasKit 接口的组织清晰
- **灵活输入类型**: 通过 `Input*` 类型别名支持多种输入格式，降低使用门槛
- **枚举的 opaque 类型**: 枚举值不使用 TypeScript enum，而是使用带品牌标记的接口，防止数字字面量被误用
- **EmbindObject 基类**: 统一了所有 WASM 对象的生命周期管理接口

## 性能考量

- 类型定义文件本身不影响运行时性能
- TypeScript 编译时类型检查可在开发阶段捕获 API 误用，减少运行时错误
- `MallocObj` 类型的存在提醒开发者关注内存管理
- 4948 行的大型 .d.ts 文件可能略微增加 TypeScript 编译器的内存使用

## 相关文件

- `modules/canvaskit/npm_build/types/canvaskit-wasm-tests.ts` — 类型定义的测试文件
- `modules/canvaskit/canvaskit_bindings.cpp` — 实际绑定实现
- `modules/canvaskit/npm_build/package.json` — npm 包配置
- `modules/canvaskit/npm_build/types/tsconfig.json` — TypeScript 编译配置
