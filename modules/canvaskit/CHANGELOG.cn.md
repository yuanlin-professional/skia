# CanvasKit 变更日志
本项目的所有重要变更将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
本项目遵循 [语义化版本](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

## [0.41.0] - 2026-03-18

### 破坏性变更
 - `Path` 对象现在是不可变的。
 - `PathBuilder` 已暴露，允许客户端增量创建 `Path` 对象。

### 新增
 - 下划线和删除线度量已添加到 FontMetrics 中

### 修复
 - 修复编译设置以跟进 [emsdk#24079](https://github.com/emscripten-core/emscripten/pull/24079)

## [0.40.0] - 2025-03-31

### 变更
 - `Typeface.MakeFreeTypeFaceFromData` 现在更名为 `Typeface.MakeTypefaceFromData`，以与 Skia 库其余部分中 Typeface 的 f 大写保持一致。
   （CK 底层仍然使用 Freetype）。
 - 向 `Font` 构造函数传递 `null` `Typeface` 不再使用默认字体。请参阅
   `CanvasKit.Typeface.GetDefault()` 作为获取内置字体来替代此行为的方法。
 - `MakeManagedAnimation` 不再在提供的 FreeType 数据不在资源映射中时回退到内置字体。

### 新增
 - `CanvasKit.Typeface.GetDefault()` 作为显式获取内置字体（如果有）的方法。
 - `Canvas.quickReject` 快速检查一个 Rect 是否在当前裁剪区域内。
 - `Canvas.saveLayer` 现在接受一个 `TileMode` 参数，影响保存图层中的背景滤镜。

## [0.39.1] - 2023-10-12

### 修复
 - `@webgpu/types` 实际上是一个依赖项，而不仅仅是 devDependency。

## [0.39.0] - 2023-10-11

### 新增
- `ImageFilter.getOutputBounds` 返回应用 `ImageFilter` 后矩形的调整边界。
- `Picture.cullRect` 给出图片中绘制命令的近似边界。
- `Picture.approximateBytesUsed` 返回存储此图片所用字节数的近似值。此大小不包括大型对象如图像。
 - `FontMgr.matchFamilyStyle` 查找与指定 familyName 和样式最匹配的字体。
- `Paint.setBlender` 设置当前混合器。
- `Blender.Mode` 创建实现指定 BlendMode 的混合器。
- `RuntimeEffect.MakeForBlender` 从给定的混合器代码编译 RuntimeEffect。
- `ManagedAnimation` 对 AE Essential Graphics 导出的 lottie 插槽的 getter 和 setter。
   支持 Color、scalar、vec2、text 和 image 插槽类型。
- `ManagedAnimation` 所见即所得编辑器 API：`attachEditor`、`enableEditor`、`dispatchEditorKey`、
  `dispatchEditorPointer`。
- `InputState` 和 `ModifierKey` 枚举。
- `Paragraph.getClosestGlyphInfoAtCoordinate` 和 `Paragraph.getGlyphInfoAt` 返回段落中指定位置/索引处字形或字形簇的相关信息。
- `Paragraph.getLineMetricsAt`，返回某行的行度量。
- `Paragraph.getNumberOfLines`，返回段落中可见行数。
- `Paragraph.getLineNumberAt`，查找包含给定 UTF-16 索引的行。
- `ManagedAnimation.setEditorCursorWeight` -- 调整所见即所得编辑器光标粗细。


### 修复
 - `EmbindObject` 已更新，允许 TypeScript 区分不透明类型，如 Shader、ColorFilter 等。

### 变更
- `MakeSWCanvasSurface` 现在允许传入 `OffscreenCanvas` 元素。
- `Picture.beginRecording` 接受一个可选的 `computeBounds` 布尔参数，当为 true 时，将使生成的录制图片在创建时计算更精确的 `cullRect`。

## [0.38.2] - 2023-06-09

### 新增
 - `Paragraph.unresolvedCodepoints` 允许客户端更轻松地识别字体覆盖范围的缺口。

### 修复
 - `.wasm` 文件现在已在 npm package.json 中导出

## [0.38.1] - 2023-05-02

### 移除
 - 粒子系统已被移除。

### 新增
 - Skottie TransformValue 访问器用于动态图层变换。
 - 新增 `CanvasKit.FontCollection`，它封装了 SkParagraph 的 FontCollection。
   FontCollection 实例包含 SkParagraph 使用的字体缓存和段落布局缓存。
 - 新增 `CanvasKit.ParagraphBuilder.MakeFromFontCollection` 用于创建使用给定 `FontCollection` 的 `ParagraphBuilder`。
 - `Paint.setDither` 已暴露。
 - 文档已改进。

### 变更
 - `Image.encodeToData` 现在更一致地使用 GPU 上下文。

## [0.38.0] - 2023-01-12

### 变更
 - `Paragraph.getRectsForRange` 和 `Paragraph.getRectsForPlaceholders` 之前返回的是 Float32Array 列表，其上通过猴子补丁添加了 'direction' 属性（这是未文档化的）。现在它们返回 `RectWithDirection` 对象。
- `CanvasKit.MakeOnScreenGLSurface` 允许提供缓存的采样计数和模板值，以避免在 Surface 创建时重复查找。

## [0.37.2] - 2022-11-15

### 修复
 - 从纹理创建的图像正确地使内部状态失效，减少闪烁 (skbug.com/40044991)

## [0.37.1] - 2022-11-08

### 修复
 - SkParagraph 中省略号的字体解析算法 (skbug.com/40042867)
 - GrContexts 将正确定位到正确的 WebGL 上下文
 - 使用 no_embedded_font 构建的 CanvasKit 将正确链接并能够从传入的字节加载字体。
 - 使用 fontSize 或 heightMultiplier 为 0 的文本样式将不可见。

## [0.37.0] - 2022-09-07

### 新增
 - Paragraph 新增设置项：`replaceTabCharacters`。
 - SkParagraph 客户端提供的 ICU API 的新 API、测试和示例：
   - buildWithClientInfo
   - getText

### 修复
 - readPixels 调用有时会因 GrDirectContext 的过时内部引用而失败。

## [0.36.1] - 2022-08-22

### 变更
 - 已启用透视文本。

### 修复
 - 在某些 Adreno GPU 上文本不再变形 (http://review.skia.org/571418)

## [0.36.0] - 2022-08-16

### 新增
 - 以下路径方法：`addCircle`、`CanInterpolate` 和 `MakeFromPathInterpolation`。
 - 以下 ImageFilter 工厂方法：`MakeBlend`、`MakeDilate`、`MakeDisplacementMap`、
   `MakeDropShadow`、`MakeDropShadowOnly`、`MakeErode`、`MakeImage`、`MakeOffset` 和 `MakeShader`。
 - `MakeLuma` ColorFilter 工厂方法。
 - `fontVariations` TextStyle 属性。
 - `ColorFilter.MakeBlend` 底层支持浮点颜色，并接受可选的颜色空间。

### 变更
 - 更新了 `dtslint`、`typescript` 和 `@webgpu/types` 版本，用于测试 index.d.ts 类型。

### 修复
 - `Image.readPixels` 应可在通过 `MakeLazyImageFromTextureSource` 创建的 `Image` 上工作
   (https://github.com/flutter/flutter/issues/103803)

### 已知问题
 - `ImageFilter.MakeDisplacementMap` 在某些情况下未按预期运行。

## [0.35.0] - 2022-06-30

### 修复
 - TypeScript 类型声明中的小错误修复。
 - 从 TextureSource 创建预乘 Image 应正确上传纹理到 WebGL。

### 新增
 - `Surface.makeImageFromTextureSource`、`Surface.updateTextureFromSource` 和
   `MakeLazyImageFromTextureSource` 都接受可选的 `srcIsPremul` 参数，用于指定其源数据是否具有预乘 alpha。这避免了在某些情况下对 alpha 的重复乘法。
 - WebGPU 支持。引入了 `CanvasKit.MakeGPUDeviceContext`、`CanvasKit.MakeGPUCanvasContext`、
   `CanvasKit.MakeGPUCanvasSurface` 和 `CanvasKit.MakeGPUTextureSurface`，它们与 WebGPU 的 `GPUDevice` 和 `GPUTexture` 对象兼容。
 - 与 `@webgpu/types` 兼容的 WebGPU API 函数的 Typescript 定义
   (https://www.npmjs.com/package/@webgpu/types)。
 - `CanvasKit.MakeCanvasSurface` 现已弃用。客户端应使用
   `CanvasKit.MakeSWCanvasSurface`、`CanvasKit.MakeOnScreenGLSurface`、
   `CanvasKit.MakeGPUCanvasSurface` 和 `CanvasKit.MakeGPUTextureSurface` 明确指定后端目标。
 - `CanvasKit.MakeGrContext` 现已弃用。客户端应改用 `CanvasKit.MakeWebGLContext` 和
   `CanvasKit.MakeGPUDeviceContext`。

## [0.34.1] - 2022-06-02

### 新增
 - `Canvas.getDeviceClipBounds` (skbug.com/40044431)

### 修复
 - `RuntimeEffect.makeShader` 和 `RuntimeEffect.makeShaderWithChildren` 可以正确接受 MallocObj 或派生的 TypedArrays 作为 uniform 数据，而不会错误释放 uniform 数据。

## [0.34.0] - 2022-05-05

### 破坏性变更
 - `SkRuntimeEffect.makeShader` 和 `SkRuntimeEffect.makeShaderWithChildren` 不再接受
   `isOpaque` 参数。这些函数现在将尽力确定你的着色器是否始终产生不透明输出，并相应优化。如果你确定希望着色器产生不透明输出，请在着色器的 SkSL 代码中这样做。

### 新增
 - `SkPicture.makeShader`
 - Skia 现在有一个 GN 工具链用于编译 CanvasKit。理想情况下，所有设置应该相同，但实际上可能存在一些细微差异。这改变了构建 CanvasKit 的设置（用户不再需要自己下载 emsdk）。

### 变更
 - 如果传入了无效的矩阵类型（例如不是数组、TypedArray 或 DOMMatrix），CanvasKit 将抛出异常而不是错误绘制。

### 修复
 - SkParagraph 对象在存储到 SkPicture 时不再出现字形乱码。
   (skbug.com/40044329)

## [0.33.0] - 2022-02-03

### 新增
 - `Surface.updateTextureFromSource` 通过为给定 `Image` 重用纹理来防止某些平台上的闪烁，而无需始终通过 `Surface.makeImageFromTextureSource` 创建新纹理。(skbug.com/40043812)
 - `ParagraphBuilder.reset` 允许重用底层内存。
 - `PathEffect.MakePath2D`、`PathEffect.MakePath1D` 和 `PathEffect.MakeLine2D`。

### 变更
 - Surface 工厂方法始终生成附带颜色空间的 surface。向 `CanvasKit.MakeWebGLCanvasSurface` 指定 `null` 或调用任何不接受颜色空间的工厂方法，现在将创建颜色空间为 `CanvasKit.ColorSpace.SRGB` 的 surface。
 - 我们现在使用 emscripten 3.1.3 构建/发布。
 - 内部调用不再使用动态分发 (skbug.com/40043887)。
 - JPEG 和 WEBP 编码在完整版本（/bin/full/中）默认启用。

### 修复
 - 通过 `Surface.makeImageFromTextureSource` 提供纹理不应导致 Mipmaps 或 Skia 需要创建纹理的其他位置出现问题 (skbug.com/40043889)
 - `CanvasKit.MakeRenderTarget` 按照文档正确接受 2 或 3 个参数。
 - `CanvasKit.MakeOnScreenGLSurface` 和其他 gpu surface 构造函数正确调整底层 WebGL 上下文，避免损坏和纹理不匹配
   (https://github.com/flutter/flutter/issues/95259)。

## [0.32.0] - 2021-12-15

### 破坏性变更
 - `Canvas.drawVertices` 和 `Canvas.drawPatch` 对默认混合模式的处理方式不同。
   参见 https://bugs.chromium.org/p/skia/issues/detail?id=12662。
 - `Canvas.markCTM` 和 `Canvas.findMarkedCTM` 已被移除。它们实际上是空操作。

### 新增
 - Canvas2D 模拟层中 `measureText` 的粗略实现。如需精确数值，客户端应使用真正的排版库，如 SkParagraph。
 - `AnimatedImage.currentFrameDuration` 已添加，同时增加了一些说明性文档。

### 修复
 - 通过 MakeLazyImageFromTextureSource 创建的图像在绘制时不应再导致某些帧仅部分显示 <skbug.com/40043831>。

## [0.31.0] - 2021-11-16

### 新增
 - `CanvasKit.MakeLazyImageFromTextureSource`，类似于
   `Surface.makeImageFromTextureSource`，但可以在不同的 WebGL 上下文中重用。

### 破坏性变更
 - `Surface.makeImageFromTextureSource` 现在接受可选的 ImageInfo 或 PartialImageInfo，而不是可选的宽度和高度。如果未提供，将使用合理的默认值。

### 修复
 - 某些 `Surface` 方法未正确切换到正确的 WebGL 上下文。
 - 关于 `INVALID_ENUM: enable: invalid capability` 的警告应该减少/消除。

### 移除
 - `FontMgr.MakeTypefaceFromData` 和 `FontMgr.RefDefault` 已被移除，改用
   `Typeface.MakeFreeTypeFaceFromData`

### 变更
 - `make release`、`make debug` 及其变体将输出放在不同位置 (./build)。
 - 示例 .html 文件从新位置 (./build) 加载 CanvasKit。

### 类型变更 (index.d.ts)
 - `Surface.requestAnimationFrame` 和 `Surface.drawOnce` 已正确记录文档。
 - 修复了 TextStyle 中的拼写错误 (decrationStyle => decorationStyle)

## [0.30.0] - 2021-09-15

### 移除
 - `Surface.grContext` 和 `Surface.openGLversion` - 这些之前未记录文档，现在不再暴露。
 - `CanvasKit.setCurrentContext` 和 `CanvasKit.currentContext`。现有调用可以删除。

### 变更
 - CanvasKit API 现在自动处理 WebGL 上下文之间的切换。
 - 减少了 WebGL 上下文切换时的开销。

### 类型变更 (index.d.ts)
 - `Canvas.drawImage*` 调用已正确记录为接受可选的 Paint 或 null。

## [0.29.0] - 2021-08-06

### 新增
 - `Path.makeAsWinding` 已添加，用于将具有 EvenOdd 填充类型的路径转换为使用 Winding 填充类型的等效区域。

### 破坏性变更
 - `Paint.getBlendMode()` 已被移除。
 - `Canvas.drawImageAtCurrentFrame()` 已被移除。
 - FilterQuality 枚举已移除 -- 改为传递 `FilterOptions` | `CubicResampler`。

### 类型变更 (index.d.ts)
 - 将所有 `object` 替换为实际类型，包括 `AnimationMarker`。

## [0.28.1] - 2021-06-28

### 新增
 - `Typeface.MakeFreeTypeFaceFromData` 作为从 .ttf、.woff 或 .woff2 文件字节创建 Typeface 的更便捷方式。
 - `Typeface.getGlyphIDs` - 提供与 `Font.getGlyphIDs` 相同的功能。

### 变更
 - ICU 已从 v65 更新到 v69。
 - Freetype 已从 f9350be 更新到 ff40776。

### 修复
 - 我们不应再需要多次解码同一字体 (skbug.com/40043207)
 - `Font.getGlyphIDs` 第三个参数的类型有误。现在已正确为 Uint16Array。

### 已弃用
 - `FontMgr.MakeTypefaceFromData` 将被移除，改用 `Typeface.MakeFreeTypeFaceFromData`
 - `FontMgr.RefDefault` 将在即将发布的版本中移除。它唯一真正的用途是用于 `FontMgr.MakeTypefaceFromData`。

## [0.28.0] - 2021-06-17

### 新增
 - `Surface.makeImageFromTexture` 和 `Surface.makeImageFromTextureSource` 作为向 CanvasKit 提供 WebGL 纹理并与 WebGL 纹理源（如 &lt;video&gt;）交互的简便方式

### 变更
 - 我们现在使用 emscripten 2.0.20 构建/发布。

### 破坏性变更
 - `Path.toCmds()` 返回扁平化的 Float32Array 而不是二维数组。
 - `Canvaskit.Path.MakeFromCmds` 不再接受二维数组。输入必须是扁平化的，但可以是数组、TypedArray 或 MallocObj。
 - `CanvasKit.*Builder` 已全部移除。客户端应改用 Malloc。

### 移除
 - `CanvasKit.Shader.MakeLerp`，相同效果可以通过 `RuntimeEffect` 轻松生成

### 已知缺陷
 - 在旧版（非 ANGLE）SwiftShader 上，某些需要细分的路径在使用 WebGL 后端 surface 时可能无法正确绘制。(skbug.com/40043054)

## [0.27.0] - 2021-05-20

### 新增
 - `Font.getGlyphIntercepts()`

### 修复
 - 使用某些 exif 元数据的图像的错误。(skbug.com/40043056)

### 移除
 - `Canvas.flush`，之前已被弃用。推荐使用 `Surface.flush` 方法。
 - `AnimatedImage.getCurrentFrame`，之前已被弃用。
   `AnimatedImage.makeImageAtCurrentFrame` 是替代方法，行为完全相同。

## [0.26.0] - 2021-04-23

### 新增
 - 向 `Font` 添加 'isEmbolden, setEmbolden'
 - 向 `Canvas` 添加 'drawGlyphs'
 - 向 `Canvas` 添加 `drawPatch`。
 - 添加 `Strut` 作为 `RectHeightStyle` 枚举。
 - `CanvasKit.RuntimeEffect` 现在支持 SkSL 中的整数 uniform。这些仍然作为浮点数（与所有其他 uniform 一样）传递给 `RuntimeEffect.makeShader`，并在内部转换为整数，以匹配着色器的期望。
 - 向 `TextStyle` 和 `StrutStyle` 添加 'halfLeading'。
 - `ParagraphStyle` 现在接受 textHeightBehavior。

### 移除
 - `Picture.saveAsFile()`，改用 `Picture.serialize()`，客户端可以控制如何存储/编码字节。

## [0.25.1] - 2021-03-30

### 新增
 - Skottie 动态文本属性访问器（文本字符串、字体大小）。
 - drawAtlas 的可选采样参数（paint 的 filter-quality 已忽略/弃用）

### 修复
 - 字体不应泄漏 https://bugs.chromium.org/p/skia/issues/detail?id=11778

## [0.25.0] - 2021-03-02

### 新增
 - CanvasKit 的完整构建版本现在位于 /bin/full。
 - `CanvasKit.rt_effect` 用于测试 RuntimeEffect 代码是否已编译。

### 破坏性变更
 - `ShapedText` 类型已被移除。需要 ShapedText 的客户端应使用 Paragraph API。

### 移除
 - `Font.measureText`，之前已被弃用。客户端应改用 Paragraph API 或 `Font.getGlyphWidths`（后者不进行排版）。
 - `Font.getWidths`，之前已被弃用。客户端应使用 `Font.getGlyphWidths`。

### 类型变更 (index.d.ts)
 - 为 `managed_skottie`、`particles` 和 `skottie` 功能常量添加了文档。

## [0.24.0] - 2021-02-18

### 新增
 - Skottie 工厂 (MakeManagedAnimation) 现在接受可选的 logger 对象。

### 破坏性变更
 - `CanvasKit.getDataBytes` 已被移除，Data 类型也已移除。之前返回 Data 的 2 个 API 现在直接返回包含字节的 Uint8Array。这些 API 是 `Image.encodeToData`（现在更名为 `Image.encodeToBytes`）和 `SkPicture.serialize`。如果编码或序列化失败，这些 API 返回 null。

### 类型变更 (index.d.ts)
 - `Image.encodeToDataWithFormat` 之前被错误地记录为独立项。

## [0.23.0] - 2021-02-04

### 新增
 - 阴影标志的常量。值得注意的是，其中一些值可以在之前的版本中使用。
 - `getShadowLocalBounds()` 用于估算 `Canvas.drawShadow` 绘制的阴影边界。
 - compile.sh 现在接受 "no_matrix"，将省略处理 3x3、4x4 和 SkColorMatrix 的辅助 JS（以防客户端有自己的逻辑来处理）。
 - `CanvasKit.RuntimeEffect.Make` 现在接受一个可选的回调函数，在编译出错时将被调用。
 - `CanvasKit.RuntimeEffect` 现在暴露 uniform。可以使用 `RuntimeEffect.getUniformCount`、`RuntimeEffect.getUniform` 和 `RuntimeEffect.getUniformName` 查询每个 uniform 的数量、维度和名称。所有 uniform 中浮点数的总数（必须传递给 `RuntimeEffect.makeShader`）可以通过 `RuntimeEffect.getUniformFloatCount` 查询。

### 破坏性变更
 - `MakeImprovedNoise` 已被移除。
 - 粒子系统现在使用包含 Effect 和 Particle 代码的单个代码字符串。Uniform API 现在在 Effect 和 Particle 程序之间共享，不再以 `Effect` 或 `Particle` 为前缀。例如，原来的 `ParticleEffect.getEffectUniform` 和 `ParticleEffect.getParticleUniform` 现在合并为：`ParticleEffect.getUniform`。

### 变更
 - `Path.getPoint()` 和 `SkottieAnimation.size()` 现在返回 TypedArray 而不是普通数组。此外，它们接受可选参数，允许将结果复制到提供的 TypedArray 中，而不是分配新的。
 - 传入点的 API 开销应更小（现在可以接受 TypedArray）。
 - `Canvas.drawShadow()` 现在接受 zPlaneParams 和 lightPos 作为 Malloc 分配的和常规的 Float32Arrays。`getShadowLocalBounds()` 也是如此。
 - `ContourMeasure.getPosTan` 返回 Float32Array 而不是普通数组。此外，此方法接受可选参数，允许将结果复制到提供的 Float32Array 中，而不是分配新的。

### 修复
 - 无法使用 WebGL 上下文时返回了不正确的错误。
 - 如有需要，4x4 矩阵通过删除第三列和第三行正确"降采样"为 3x3 矩阵。
 - `SkottieAnimation.size()` 之前错误地返回对象。现在返回长度为 2 的 TypedArray (w, h)。

### 已弃用
 - `Canvas.drawImageRect`、`Canvas.drawImage`、`Canvas.drawAtlas`，
   这些依赖于 Paint 的 FilterQuality，该属性即将移除。请显式传递采样选项。

### 移除
 - `PathMeasure`，已弃用并被 `ContourMeasure` 替代。

## [0.22.0] - 2020-12-17

### 新增
 - `Canvas.drawImageCubic`、`Canvas.drawImageOptions`、`Canvas.drawImageRectCubic`、
   `Canvas.drawImageRectOptions` 用于替代之前需要 FilterQuality 的功能。
 - 此变更日志的副本已发布在 NPM 版本中，便于查阅。

### 破坏性变更
 - `Canvas.drawImageNine` 现在需要一个必选的 FilterMode（Paint 仍然是可选的）。

## [0.21.0] - 2020-12-16

### 新增
 - `Image` 类型新增 `getImageInfo()` 和 `getColorSpace()`。
 - `CanvasKit.deleteContext()` 用于在完成使用、调整大小等情况下删除 WebGL 上下文。
 - `Image.makeCopyWithDefaultMipmaps()` 用于配合 `Image.makeShaderOptions` 使用；在选择非 `None` 的 `MipmapMode` 时必须使用。

### 破坏性变更
 - `Path.addPoly()` 不再接受二维点数组，而是接受扁平化的一维数组。
 - `MakeVertices()` 不再接受二维的点或纹理坐标数组，两处都接受扁平化的一维数组。
 - `Paint.setFilterQuality`、`Paint.getFilterQuality`、`Image.makeShader` 已被移除。
   指定插值设置的新方式是使用新增的 `Image.makeShader*` 方法。`Image.makeShaderCubic` 替代高质量；`Image.makeShaderOptions` 用于中/低质量。

### 变更
 - `MakeImage` 现在已记录在 Typescript 类型 (index.d.ts) 中。参数已精简以与其他类似 API 保持一致。
 - `MakeAnimatedImageFromEncoded` 现在遵循 Exif 元数据。`MakeImageFromEncoded` 之前已经这样做（并继续如此）。
 - Canvas2D 模拟层始终使用高质量图像平滑（这大大简化了底层代码）。
 - 我们现在在测试和部署到 npm 时使用 emsdk 2.0.10 编译 CanvasKit。
 - 我们不再向 npm 发布 "core" 构建版本，而是发布 "profiling" 构建版本，与主构建版本相同，只是带有未混淆的函数调用和其他调试信息，有助于确定运行时间花在哪里。

### 修复
 - `Canvas.drawPoints` 正确接受扁平化的 Array 或 TypedArray 点（如文档所述），而不是二维数组。

### 类型变更 (index.d.ts)
 - 记录了 InputFlexibleColorArray 的附加类型。

## [0.20.0] - 2020-11-12

### 新增
 - `MakeFractalNoise`、`MakeImprovedNoise` 和 `MakeTurbulence` 已添加到 `CanvasKit.Shader`。
 - `MakeRasterDirectSurface` 允许用户直接访问绘制的像素。
 - 向 Paragraph 添加 `getLineMetrics`。
 - `Canvas.saveLayerPaint` 作为实验性的、未文档化的"快速路径"，如果只需要传递 paint。
 - 支持 .woff 和 .woff2 字体。通过向 compile.sh 提供 no_woff2 可禁用 .woff2 以减小代码体积。（这会移除 brotli 解压缩代码）。

### 破坏性变更
 - `CanvasKit.MakePathFromSVGString` 已重命名为 `CanvasKit.Path.MakeFromSVGString`
 - `CanvasKit.MakePathFromOp` 已重命名为 `CanvasKit.Path.MakeFromOp`
 - `Canvas.readPixels` 和 `Image.readPixels` 的 API 已重新设计，以更准确地反映 C++ 后端及彼此。bytesPerRow 现在是必选参数。它们接受 ImageInfo 对象来指定输出格式。此外，它们接受可选的 malloc 分配对象作为最后一个参数。如果提供，数据将被复制到其中，而不是分配新缓冲区。

### 变更
 - 我们现在在测试和部署到 npm 时使用 emsdk 2.0.6 编译 CanvasKit。
 - 我们不再启用 rtti 编译，节省约 1% 的代码体积。
 - `CanvasKit.Shader.Blend`、`...Color` 和 `...Lerp` 已重命名为
   `CanvasKit.Shader.MakeBlend`、`...MakeColor` 和 `...MakeLerp` 以符合命名规范。旧名称将在即将发布的版本中移除。

### 移除
 - `CanvasKit.MakePathFromCmds`；已弃用，改用 `CanvasKit.Path.MakeFromCmds`。
 - `new CanvasKit.Path(path)` 改用现有的 `path.copy()`。
 - 未使用的内部 API (_getRasterN32PremulSurface, Drawable)
 - Canvas2D 模拟层中的 `measureText`，因 measureText 已弃用。

### 已弃用
 - `Font.getWidths` 改用 `Font.getGlyphIDs` 和 `Font.getGlyphWidths`。
 - `Font.measureText` 改用 Paragraph API（实际进行排版的 API）。

### 类型变更 (index.d.ts)
 - MakeFromCmds 的返回值正确反映了 null 的可能性。
 - `CanvasKit.GrContext` 已重命名为 `CanvasKit.GrDirectContext`。
 - 添加了 Shader Gradients 的文档/类型（例如 `CanvasKit.Shader.MakeLinearGradient`）。

## [0.19.0] - 2020-10-08

### 破坏性变更
 - "Sk" 已从所有名称中移除。例如 `new CanvasKit.SkPaint()` 变为
   `new CanvasKit.Paint()`。所有新名称请参见 `./types/index.d.ts`。

### 移除
 - `Surface.captureFrameAsSkPicture`；之前已被弃用。
 - `CanvasKit.MakeSkCornerPathEffect`、`CanvasKit.MakeSkDiscretePathEffect`、
   `CanvasKit.MakeBlurMaskFilter`、`CanvasKit.MakeSkDashPathEffect`、
   `CanvasKit.MakeLinearGradientShader`、`CanvasKit.MakeRadialGradientShader`、
   `CanvasKit.MakeTwoPointConicalGradientShader`；这些之前已被弃用，有替代方法如 `CanvasKit.PathEffect.MakeDash`。
 - `Canvas.concat44`；之前已被弃用，直接使用 `Canvas.concat`

## [0.18.1] - 2020-10-06

### 新增
 - Typescript 类型（和文档）现在位于 types 子文件夹中。我们将随 CanvasKit 库的更改持续更新。

## [0.18.0] - 2020-10-05

### 破坏性变更
 - SkRect 不再从 `CanvasKit.LTRBRect`、`CanvasKit.XYWHRect` 返回，也不再作为 JS 对象接受。取而代之的格式是 4 个浮点数，可以是数组、Float32Array 或 CanvasKit.Malloc 返回的内存片段。这些浮点数是矩形的 left、top、right、bottom 值。
 - SkIRect（整数值矩形）不再作为 JS 对象接受。取而代之的格式是 4 个整数，可以是数组、Int32Array 或 CanvasKit.Malloc 返回的内存片段。这些整数是矩形的 left、top、right、bottom 值。
 - SkRRect（圆角矩形）不再从 `CanvasKit.RRectXY` 返回，也不再作为 JS 对象接受。取而代之的格式是 12 个浮点数，可以是数组、Float32Array 或 CanvasKit.Malloc 返回的内存片段。前 4 个浮点数是矩形的 left、top、right、bottom 值，然后是 4 组点，从左上角开始顺时针排列。此更改允许更快的
   在 JS 和 WASM 代码之间传输。
 - `SkPath.addRoundRect` 已被 `SkPath.addRRect` 替代。可以通过 `CanvasKit.RRectXY` 辅助函数实现相同的功能。
 - `SkPath.addRect` 不再接受 4 个单独的浮点数作为参数。它只接受一个 SkRect（一个包含 4 个浮点数的数组/Float32Array）以及一个可选的布尔值来确定顺时针或逆时针方向。
 - `SkCanvas.saveLayer` 的参数顺序略有不同（更加一致）。现在是 `paint, bounds, backdrop, flags`

### 变更
 - 我们现在在测试和发布到 npm 时使用 emsdk 2.0.0 编译 CanvasKit。
 - WebGL 接口创建在代码大小和速度方面更加精简。
 - 传递给 `CanvasKit.SkRuntimeEffect.Make` 的 SkSL 中使用的 `main` 签名已更改。不再有 `inout half4 color` 参数，效果必须返回它们的颜色。有效签名现在是 `half4 main()` 或 `half4 main(float2 coord)`。
 - `SkPath.getBounds`、`SkShapedText.getBounds` 和 `SkVertices.bounds` 现在接受一个可选参数。如果提供了长度为 4 或更大的 Float32Array，边界将被复制到此数组中，而不是分配一个新数组。
 - `SkCanvas.drawAnimatedImage` 已被移除，取而代之的是调用 `SkCanvas.drawImageAtCurrentFrame` 或 `SkAnimatedImage.makeImageAtCurrentFrame`，然后调用 `SkCanvas.drawImage`。
 - `SkTextBlob.MakeFromRSXform` 也接受一个（可能是 Malloc 分配的）RSXforms 的 Float32Array（详见 SkRSXform。）

### 移除
 - `SkCanvas.drawRoundRect` 已被移除，取而代之的是 `SkCanvas.drawRRect`。可以通过 `CanvasKit.RRectXY` 辅助函数实现相同的功能。
 - `SkPath.arcTo` 已被弃用，取而代之的是 `SkPath.arcToOval`、`SkPath.arcToRotated`、`SkPath.arcToTangent`。
 - 从 `ColorType` 枚举中移除了多余的 ColorTypes。

### 新增
 - `CanvasKit.LTRBiRect` 和 `CanvasKit.XYWHiRect` 作为创建 SkIRects 的辅助函数。
 - `SkCanvas.drawRect4f` 作为一种实验性的无数组 API，适用于已有自己 Rect 表示的客户端。这是实验性的，因为我们不知道在实际使用中它是否更快/更好，也因为在经过一段时间验证之前，我们不想承诺为所有 Rect API（以及类似类型）都提供这些接口。
 - 向 `TextStyle` 添加了以下内容：
   - `decorationStyle`
   - `textBaseline`
   - `letterSpacing`
   - `wordSpacing`
   - `heightMultiplier`
   - `locale`
   - `shadows`
   - `fontFeatures`
 - 向 `ParagraphStyle` 添加了 `strutStyle`。
 - 向 `ParagraphBuilder` 添加了 `addPlaceholder`。
 - 向 `Paragraph` 添加了 `getRectsForPlaceholders`。
 - `SkFont.getGlyphIDs`、`SkFont.getGlyphBounds`、`SkFont.getGlyphWidths` 用于将码位转换为 GlyphIDs 并获取这些字形的相关度量。注意：字形 ID 仅对请求它们的字体有效。
 - `SkTextBlob.MakeFromRSXformGlyphs` 和 `SkTextBlob.MakeFromGlyphs` 作为使用 GlyphIDs 而非码位构建 TextBlobs 的方式。
 - `CanvasKit.MallocGlyphIDs` 作为在 WASM 堆上预分配字形 ID 空间的辅助函数。

### 已弃用
 - `SkAnimatedImage.getCurrentFrame`；建议使用 `SkAnimatedImage.makeImageAtCurrentFrame`（遵循既定的命名规范）。
 - `SkSurface.captureFrameAsSkPicture` 将在未来版本中移除。调用者可以直接使用 `SkPictureRecorder`。
 - `CanvasKit.FourFloatArrayHelper` 及相关辅助函数（主要帮助 drawAtlas）。`CanvasKit.Malloc` 是更好的工具，将很快取代这些。
 - `SkPathMeasure`；SkContourMeasureIter 拥有所有相同的功能和更简洁的模式。

### 修复
 - 修复了 `SkCanvas.drawText` 中的内存泄漏。
 - 减少了 SkTextBlob 在其生命周期内占用的内存。
 - `SkPath.computeTightBounds()` 再次可用。与 getBounds() 一样，它接受一个可选参数来存放边界。

## [0.17.3] - 2020-08-05

### 新增
 - 添加了 `CanvasKit.TypefaceFontProvider`，可用于使用字体族别名注册字体。例如，"Roboto Light" 可以使用别名 "Roboto" 注册，当使用轻字重的 "Roboto" 时将被使用。
 - 添加了 `CanvasKit.ParagraphBuilder.MakeFromFontProvider`，从 `TypefaceFontProvider` 创建 `ParagraphBuilder`。
 - 添加了 `CanvasKit.ParagraphBuilder.pushPaintStyle`，可用于使用画笔而非简单颜色对文本进行描边或填充。

## [0.17.2] - 2020-07-22

### 修复
 - 着色器程序在 WebGL 1.0 中不再生成 `do-while` 循环。

## [0.17.1] - 2020-07-21

### 新增
 - 编译选项用于反序列化 skps 中的效果 `include_effects_deserialization`。

### 变更
 - npm 构建中启用了 Pathops 和 SKP 反序列化/序列化。

## [0.17.0] - 2020-07-20

### 新增
 - 添加了 `CanvasKit.MakeImageFromCanvasImageSource`，它接受 HTMLImageElement、SVGImageElement、HTMLVideoElement、HTMLCanvasElement、ImageBitmap 或 OffscreenCanvas 并返回一个 SkImage。此函数是创建 SkImages 时 `CanvasKit.MakeImageFromEncoded` 的替代方案，用于加载和解码图像。未来，如果使用浏览器 API 解码图像并配合 `CanvasKit.MakeImageFromCanvasImageSource` 而不是 `CanvasKit.MakeImageFromEncoded`，则可以通过移除 wasm 中的图像编解码器来减小 CanvasKit 的代码大小。
 - 在 core.spec.ts 中提供了三个 `CanvasKit.MakeImageFromCanvasImageSource` 的使用示例。
 - 添加了对性能测试和测试中异步回调的支持。
 - `CanvasKit.SkPath.MakeFromVerbsPointsWeights` 和 `CanvasKit.SkPath.addVerbsPointsWeights` 用于一次性提供多个路径操作（例如 moveTo、cubicTo）。
 - `CanvasKit.malloc` 返回的对象现在有一个 `subarray` 方法，其工作方式与普通 TypedArray 版本完全相同。它返回的 TypedArray 也由 WASM 内存支持，传递到 CanvasKit 时将直接使用而不复制数据（就像 `Malloc.toTypedArray` 一样）。
 - `SkM44.setupCamera` 返回一个 4x4 矩阵，用于从相机设置透视视图。
 - `SkPath.arcToOval`、`SkPath.arcToTangent` 和 `SkPath.arcToRotated` 用于替代 `SkPath.arcTo` 的三个重载。https://github.com/flutter/flutter/issues/61305

### 变更
 - 在所有接受颜色数组的地方（渐变生成器、drawAtlas 和 MakeSkVertices），现在可以提供扁平的浮点颜色 Float32Arrays、整数颜色的 Uint32Arrays 或 Float32Array(4) 颜色的二维数组。不应传递数字数组，因为 canvaskit 无法在不全部检查的情况下判断它们是整数还是浮点数。对于渐变，最快的选择是扁平 Float32Array，对于 drawAtlas 和 MakeSkVertices，最快的选择是扁平 Uint32Array。
 - 颜色数组也可以是使用 CanvasKit.Malloc 创建的对象。
 - 将 `reportBackendType` 重命名为 `reportBackendTypeIsGPU` 并使其返回布尔值。
 - `MakeWebGLCanvasSurface` 现在可以接受一个可选的 WebGL 上下文属性字典，用于覆盖默认属性。

### 修复
 - `TextStyle.color` 现在可以正确地使用 Malloc 分配的 Float32Array。
 - 支持 wombat-dressing-room。go/npm-publish

### 已弃用
 - `CanvasKit.MakePathFromCmds` 已重命名为 `CanvasKit.SkPath.MakeFromCmds`。别名将在即将发布的版本中移除。
 - `SkPath.arcTo` 被拆分为三个函数。

## [0.16.2] - 2020-06-05

### 修复
 - 修复了一个 bug，加载字体（和其他内存密集型调用）会导致 CanvasKit 偶尔崩溃，报错 `TypeError: Cannot perform %TypedArray%.prototype.set on a neutered ArrayBuffer`。
 - 错误地释放了传递给 computeTonalColors 的 Malloc 分配的颜色。

## [0.16.1] - 2020-06-04

### 修复
 - 颜色使用无符号整数以兼容 Flutter Web 和之前的行为，而不是有符号整数。

## [0.16.0] - 2020-06-03

### 新增
 - 支持广色域色彩空间 DisplayP3 和 AdobeRGB。但是，在广色域显示器上正确显示需要浏览器将所有内容渲染到 DisplayP3 或 AdobeRGB 配置文件，因为目前还没有办法向浏览器指示 canvas 元素具有非 sRGB 色彩空间。请参阅 extra.html 中的颜色支持示例。仅支持 WebGL2 后端的表面。
 - 添加了 `SkSurface.reportBackendType`，返回 'CPU' 或 'GPU'。
 - 添加了 `SkSurface.imageInfo`，返回一个描述表面大小和颜色属性的 ImageInfo 对象。colorSpace 在使用 ImageInfo 的所有地方都已添加。
 - `CanvasKit.Free` 用于在 `CanvasKit.Malloc` 之后显式清理内存。所有通过 `CanvasKit.Malloc` 分配的内存必须通过 `CanvasKit.Free` 释放，否则会导致内存泄漏。这可以通过减少 JS 和 WASM 端之间的数据复制来提高性能。
 - `CanvasKit.ColorAsInt`、`SkPaint.setColorComponents`、`SkPaint.setColorInt`、`SkCanvas.drawColorComponents`、`SkCanvas.drawColorInt`，适用于希望避免分配颜色分量数组开销且仅需要 8888 颜色的客户端。

### 变更
 - 我们现在使用 Emscripten v1.39.16 编译/发布。
 - `CanvasKit.MakeCanvasSurface` 接受一个新的枚举，指定 CanvasKit 支持的三种色彩空间和像素格式组合之一。
 - 所有 `_Make*Shader` 函数现在在末尾接受一个色彩空间参数。省略它或传递 null 会使其像以前一样运行，默认为 sRGB。
 - `SkPaint.setColor` 接受一个新的色彩空间参数，默认为 sRGB。
 - 在 JS 和 WASM 层之间发送颜色和矩阵所需的分配更少。
 - 所有接受一维数组的 API 也应接受 Malloc 返回的对象。建议传递 Malloc 对象，因为每当 CanvasKit 需要分配内存并需要调整大小时，TypedArray 可能会失效。

### 破坏性变更
 - `CanvasKitInit(...)` 现在直接返回一个 Promise。因此，`CanvasKitInit(...).ready()` 已被移除。
 - `CanvasKit.MakeCanvasSurface` 不再接受覆盖 canvas 元素上宽度/高度的参数。使用 canvas 元素的 width/height 属性来指定绘图区域的大小，使用 CSS width/height 来设置它在页面上显示的大小（应用 CSS 尺寸时，绘制后会重新缩放）。
 - `CanvasKit.Malloc` 返回的内存将不再自动清理。客户端必须使用 `CanvasKit.Free` 来释放内存。
 - `CanvasKit.Malloc` 不再直接返回 TypedArray，而是返回一个可以通过 toTypedArray() 生成 TypedArray 的对象。这是为了避免 "detached ArrayBuffer" 错误：
   <https://github.com/emscripten-core/emscripten/issues/6747>

### 修复
 - WebGL 上下文不再使用 "antialias" 标志创建。使用 "antialias" 会导致 Ganesh 在不知不觉中启用 MSAA 的情况下尝试进行基于覆盖率的 AA 时 AA 质量差。它还降低了性能。

## [0.15.0] - 2020-05-14

### 新增
 - 在所有接受 SkMatrix（即长度为 6/9/16 的数组或 Float32Arrays）的 API 上支持 DOMMatrix。
 - 向 SkFont 添加了 setEdging 和 setEmbeddedBitmaps。你可以通过 compile.sh 参数 `no_alias_font` 禁用绘制锯齿字体的能力（并节省一些代码大小）。

### 移除
 - 先前已弃用的函数 `MakeSkDashPathEffect`、`MakeLinearGradientShader`、`MakeRadialGradientShader`、`MakeTwoPointConicalGradientShader`、`MakeSkCornerPathEffect`、`MakeSkDiscretePathEffect`

### 变更
 - CanvasKit 颜色现在用四个浮点数的 TypedArray 表示。
 - 对 `getError` 的调用应被禁用。这在某些场景下可能带来性能提升。

### 移除
 - SkPaint.setColorf 已过时并被移除。setColor 接受一个始终由浮点数组成的 CanvasKit 颜色。
 - `SkShader.Lerp` 和 `SkShader.Blend` 的 localmatrix 选项。

### 已弃用
 - `SkCanvas.concat44` 已被合并到 concat 中（现在接受 3x2、3x3 或 4x4 矩阵）。它将很快被移除。

### 修复
 - 段落绑定代码中的内存泄漏 (https://github.com/flutter/flutter/issues/56938)
 - Safari 现在在 WebGL2 不可用时正确使用 WebGL1 而不是 WebGL2 (skbug.com/40041519)。

## [0.14.0] - 2020-03-18

### 新增
 - `SkShader.MakeSweepGradient`
 - `SkCanvas.saveLayer` 现在可以用 1 个参数（画笔）调用。在这种情况下将使用当前的有效裁剪区域，因为假定当前矩形为 null。
 - `SkPaint.setAlphaf`
 - 客户端可以向 compile.sh 提供 `no_codecs` 以移除所有编解码器编码和解码代码。如果不需要编解码器，这可以节省超过 100 kb 的压缩大小。

### 已弃用
 - `MakeSkDashPathEffect` 将很快被移除。调用可以用 `SkPathEffect.MakeDash` 替代。
 - `MakeLinearGradientShader` 将很快被移除。调用可以用 `SkShader.MakeLinearGradient` 替代。
 - `MakeRadialGradientShader` 将很快被移除。调用可以用 `SkShader.MakeRadialGradient` 替代。
 - `MakeTwoPointConicalGradientShader` 将很快被移除。调用可以用 `SkShader.MakeTwoPointConicalGradient` 替代。

### 修复
 - 在 canvas2d 模拟层中，阴影在 fillRect 和 strokeRect 上正确绘制。
 - 在 canvas2d 模拟层中，阴影偏移正确地忽略了 CTM。

### 变更
 - 默认停止编译 jpeg 和 webp 编码器。这减少了 100kb 的二进制大小。需要这些编码器的客户端可以向 compile.sh 提供 `force_encode_webp` 或 `force_encode_jpeg`。

### 移除
 - 移除了反向填充类型。
 - 移除了 StrokeAndFill 画笔样式。
 - 移除了 TextEncoding 枚举（它仅在内部使用）。所有函数假定使用 UTF-8。

## [0.13.0] - 2020-02-28

### 已弃用
 - `MakeSkCornerPathEffect` 将很快被移除。调用可以用 `SkPathEffect.MakeCorner` 替代。
 - `MakeSkDiscretePathEffect` 将很快被移除。调用可以用 `SkPathEffect.MakeDiscrete` 替代。

### 新增
 - `SkSurface.drawOnce` 用于绘制单帧（作为已有的用于动画逻辑的 `SkSurface.requestAnimationFrame` 的补充）。
 - `CanvasKit.parseColorString` 用于处理如 "#2288FF" 的颜色字符串。
 - 粒子模块现在暴露效果 uniforms，可以修改以实现实时更新。
 - 在 `SkM44` 中添加了实验性的 4x4 矩阵。
 - 在 `SkVector` 中添加了向量数学函数。
 - `SkRuntimeEffect.makeShaderWithChildren`，可以接受其他着色器作为 fragmentProcessors。
 - `GrContext.releaseResourcesAndAbandonContext` 用于释放 WebGL 上下文。
 - `SkFont` 上的一些方法：`setHinting`、`setLinearMetrics`、`setSubpixel`。

### 变更
 - 我们现在使用 Emscripten v1.39.6 编译/发布。
 - `SkMatrix.multiply` 现在可以接受任意数量的矩阵参数，从左到右相乘。
 - SkMatrix.invert 现在在矩阵不可逆时返回 null。之前它会返回一个单位矩阵。调用者必须确定在这种情况下什么行为是合适的。
 - 在 Canvas2D 兼容层中，底层 SkFont 将设置 setSubpixel(true)。
 - 从 Vertices 构建器中移除了骨骼

### 修复
 - 支持 .otf 字体（.woff 和 .woff2 仍不受支持）。

## [0.12.0] - 2020-01-22

### 新增
 - `SkFontMgr.countFamilies` 和 `SkFontMgr.getFamilyName` 用于暴露解析后的字体名称。

### 变更
 - SKP 序列化/反序列化现已可用（可通过 'no_skp' 禁用）。`SkPicture.DEBUGONLY_saveAsFile` 重命名为 `SkPicture.saveAsFile`，`CanvasKit.MakeSkPicture` 现已暴露。SKP 支持不会发布到 npm 构建中。`force_serialize_skp` 已被移除，因为它是退出机制而非加入机制。

### 修复
 - 有时会导致 'Cannot perform Construct on a neutered ArrayBuffer' 的 bug
 - SkImage.readPixels 的 bug (skbug.com/40041118)
 - Canvas2d 模式下透明颜色的 bug (skbug.com/40041129)

## [0.11.0] - 2020-01-10

### 新增
 - 一个 "Core" 构建，移除了字体、Skottie 动画播放器、粒子演示和 PathOps，可在 `bin/core/` 中找到。它大约是 "CoreWithFonts" 构建大小的一半。
 - 可用于自定义构建的实验性运行时着色器。
 - WebP 支持。
 - `SkAnimatedImage.getCurrentFrame`，返回一个 SkImage。

### 修复
 - `CanvasKit.SaveLayerInitWithPrevious` 和 `CanvasKit.SaveLayerF16ColorType` 常量。
 - 一些编译配置，例如没有字体或仅有 particles/skottie 之一的配置。

### 变更
 - 对编译设置进行了小幅调整以减少代码大小和链接时间。
 - 当底层 C++ 调用已被编译移除时，不再提供 JS 函数。

### 移除
 - `SkShader.Empty`
 - 对 Type 1 字体的支持。这些是古老的字体格式，移除它们可以节省约 135k 的代码大小。

### 破坏性变更
 - 为了减少大多数客户端的代码大小，npm 现在包含两个 CanvasKit 构建。在 `bin/` 中有包含 0.10.0 大部分功能的 "CoreWithFonts" 构建。但是，我们不再发布 Skottie 动画播放器和粒子演示。此外，PathOps 也从此构建中移除了 `MakePathFromOp`、`SkPath.op` 和 `SkPath.simplify`。需要这些功能的客户端建议使用 `compile.sh` 创建自定义构建。
 - `SkPicture.DEBUGONLY_saveAsFile` 被意外包含在发布构建中。它已被移除。需要在发布构建中使用此功能的客户端（例如提交仅在发布版中复现的 bug 报告）应使用 `force_serialize_skp` 标志进行自定义构建。

### 已弃用
 - `SkCanvas.drawAnimatedImage` 将很快被重命名。调用可以用 `SkCanvas.drawImage` 和 `SkAnimatedImage.getCurrentFrame` 替代。

## [0.10.0] - 2019-12-09

### 新增
 - `SkContourMeasureIter` 和 `SkContourMeasure` 作为 `SkPathMeasure` 的替代方案。
 - CanvasKit 图像解码缓存辅助函数：getDecodeCacheLimitBytes()、setDecodeCacheLimitBytes() 和 getDecodeCacheUsedBytes()。
 - `SkShader.Blend`、`SkShader.Color`、`SkShader.Empty`、`SkShader.Lerp`。

### 变更
 - `SkParagraph.getRectsForRange` 返回的值现在具有方向，值为 `CanvasKit.TextDirection`。

### 修复
 - 在 externs 文件中正确定义了 `MakeImage`，可以与 `CanvasKit.Malloc` 配合使用。

## [0.9.0] - 2019-11-18
### 新增
 - 实验性的 `CanvasKit.Malloc`，可用于创建由 C++ WASM 内存支持的 TypedArray。在某些情况下可以节省一次复制（例如 SkColorFilter.MakeMatrix）。这是一个高级功能，请谨慎使用。
 - `SkCanvas.clipRRect`、`SkCanvas.drawColor`
 - Blur、ColorFilter、Compose、MatrixTransform SkImageFilters。可与 `SkPaint.setImageFilter` 配合使用。
 - `SkCanvas.saveLayer` 现在接受 3 或 4 个参数，最多包括 bounds、paint、SkImageFilter、flags。
 - `SkPath.rArcTo`、`SkPath.rConicTo`、`SkPath.rCubicTo`、`SkPath.rLineTo`、`SkPath.rMoveTo`、`SkPath.rQuadTo`。与非相对版本一样，这些都支持链式调用。
 - 向 SkAnimatedImage 添加了 `width()`、`height()`、`reset()`、`getFrameCount()`。
 - `SkCanvas.drawImageNine`、`SkCanvas.drawPoints` 及相关的 `PointMode` 枚举。
 - `SkPath.addPoly`
 - `SkPathMeasure.getSegment`
 - 更多关于 SkParagraph API 的信息，例如 `getLongestLine()`、`getWordBoundary` 等。

### 已弃用
 - `CanvasKit.MakeBlurMaskFilter` 将很快被重命名/移动到 `CanvasKit.SkMaskFilter.MakeBlur`。

### 变更
 - 使用更新版本的 Freetype2（现在跟踪 Skia 的 DEPS）。
 - 使用更新版本的 libpng 和 zlib（现在跟踪 Skia 的 DEPS）。

### 修复
 - 有时回退到 CPU 时的空指针解引用。
 - 实际向 WebGL 请求模板缓冲区。
 - 可以通过向 compile.sh 传递 no_paragraph 或使用 primitive_shaper 来退出 Paragraph API。

## [0.8.0] - 2019-10-21

### 新增
 - `CanvasKit.MakeAnimatedImageFromEncoded`、`SkCanvas.drawAnimatedImage`。
 - `CanvasKit.SkFontMgr.FromData`，接受多个字体数据的 ArrayBuffers，解析它们，读取元数据（例如字体族名称）并将其存储到 SkFontMgr 中。
 - SkParagraph 作为一组可选的 API，用于处理文本布局。

### 变更
 - `no_font` 编译选项应该能去除更多与字体相关的无用代码。
 - `no_embedded_font` 选项现在允许创建 `SkFontMgr.FromData` 而不是总是创建一个空的。
 - 更新到 emscripten 1.38.47
 - 切换到 WebGL 2.0，但在不可用时回退到 1.0 - skbug.com/40040335

### 修复
 - 绘制文本中的空终止符 bug - skbug.com/40040633

## [0.7.0] - 2019-09-18

### 新增
 - `SkCanvas.drawCircle()`、`SkCanvas.getSaveCount()`
 - `SkPath.offset()`、`SkPath.drawOval`
 - `SkRRect` 支持（`SkCanvas.drawRRect`、`SkCanvas.drawDRRect`、`CanvasKit.RRectXY`）。高级用户可以根据需要指定 8 个单独的半径。
 - `CanvasKit.computeTonalColors()`，返回 TonalColors，其中包含一个环境光 SkColor 和一个聚光 SkColor。
 - `CanvasKit.SkColorFilter` 及多种工厂方法。`SkPaint.setColorFilter` 是目前唯一使用这些的消费者。
 - `CanvasKit.SkColorMatrix` 及函数 `.identity()`、`.scaled()`、`.concat()` 等。主要用于 `CanvasKit.SkColorFilter.MakeMatrix`。

### 变更
 - `MakeSkVertices` 使用构建器以节省一次复制。

### 破坏性变更
 - 当 `SkPath.arcTo` 接收七个参数时，它不再自动将前四个转换为 `SkRect`，而是使用它们作为 `arcTo(rx, ry, xAxisRotate, useSmallArc, isCCW, x, y)`（详见 SkPath.h）。

## [0.6.0] - 2019-05-06

### 新增
 - `SkSurface.grContext` 现已暴露。`GrContext` 有新的方法用于监控/设置缓存限制；调整这些可能在某些情况下带来更好的性能。`getResourceCacheLimitBytes`、`setResourceCacheLimitBytes`、`getResourceCacheUsageBytes`
 - `SkCanvas.drawAtlas` 用于从精灵表高效绘制多个精灵，支持一组变换、颜色混合等。
 - `SkColorBuilder`、`RSXFormBuilder`、`SkRectBuilder`，在数组大小固定的情况下，通过减少每帧的 malloc/free 调用来提高性能。
 - 基本的 `SkPicture` 支持。`SkSurface.captureFrameAsSkPicture` 是一个辅助函数，用于捕获 `SkPicture`，可以通过 `SkPicture.DEBUGONLY_saveAsFile` 转储到磁盘（用于调试）。
 - `SkImage.readPixels`，返回像素值的 TypedArray（可以在任何地方安全使用，不需要 delete()）。

### 变更
 - 更好的 WebGL `GrGLCaps` 支持 - 这不应对 API 或正确性产生影响，但可能修复了各种表面类型中的一些 bug。
 - 在 JS 端对 SkColor 使用无符号整数 - 这不应产生任何影响，除非客户端有预计算的颜色，在这种情况下需要重新计算。
 - [破坏性] 将 `CanvasKit.MakeImageShader` 移动到 `SkImage.makeShader` - 移除了 clampUnpremul 参数。

## [0.5.1] - 2019-03-21

### 新增
 - `SkPathMeasure`、`RSXFormBuilder`、`SkFont.getWidths`、`SkTextBlob.MakeFromRSXform`，这些是添加辅助函数 `SkTextBlob.MakeOnPath` 所需的。
 - `SkSurface.requestAnimationFrame` - 对 window.requestAnimationFrame 的封装，处理了以最佳方式使用 CanvasKit 所需的设置/拆卸工作。回调函数的第一个参数是 `SkCanvas` - 调用者应在其上绘制。

### 变更
 - 在 Skia Git 仓库中的位置现在是 `modules/canvaskit`（之前是 `experimental/canvaskit`）

### 修复
 - `CanvasKit.SkMatrix.invert` 中的 Extern bug
 - 回退到 CPU 时现在正确刷新画布以获取 CanvasRenderingContext2D 的访问权限。
 - 编译标志以更好地支持某些显卡的 WebGL1。
 - 大型椭圆路径上的抗锯齿 bug <skbug.com/40040155>

### 已弃用
 - `SkCanvas.flush` 将很快被移除 - 客户端应只调用 `SkSurface.flush`


## [0.5.0] - 2019-03-08

### 新增
 - `CanvasKit.MakeSkVertices` 的 isVolitile 选项。之前（也是当前默认）的行为是将其设为 true；某些应用程序设为 false 可能会更快。
 - `SkCanvas.saveLayer(rect, paint)`
 - `SkCanvas.restoreToCount(int)`，可与 .save() 和 .saveLayer() 的输出一起使用。
 - 来自 modules/particles 的可选粒子库。参见 `CanvasKit.MakeParticles(json)`；
 - 更多用于处理 Surfaces/Contexts 的公共 API：`GetWebGLContext`、`MakeGrContext`、`MakeOnScreenGLSurface`、`MakeRenderTarget`。
 - `SkSurface.getSurface()` 和 `SkCanvas.getSurface()`，用于创建兼容的表面（通常用作工作区，然后通过 `surface.makeImageSnapshot()` "保存"）

### 破坏性变更
 -  `CanvasKit.MakeWebGLCanvasSurface` 不再将 webgl 上下文作为第一个参数，只接受 canvas 或 canvas 的 id。如果用户想管理自己的 GL 上下文，应使用 `GetWebGLContext` -> `MakeGrContext` -> `MakeOnScreenGLSurface` 自行构建 `SkSurface`。

## [0.4.1] - 2019-03-01

### 新增
 - `MakeManagedAnimation` 的可选参数，用于提供外部资源（如图像、字体）。

## [0.4.0] - 2019-02-25

### 新增
 - 暴露了 `SkPath.addRoundRect`、`SkPath.reset`、`SkPath.rewind`。
 - 暴露了 `SkCanvas.drawArc`、`SkCanvas.drawLine`、`SkCanvas.drawOval`、`SkCanvas.drawRoundRect`。
 - 可以将 SkPath 导入/导出为命令数组。参见 `CanvasKit.MakePathFromCmds` 和 `SkPath.toCmds`。
 - `SkCanvas.drawTextBlob()` 和 `SkCanvas.SkTextBlob.MakeFromText()` 用于在画布上绘制文本。
 - `CanvasKit.TextEncoding` 枚举。用于 `SkTextBlob`。
 - 使用 `ShapedText` 对象和 `SkCanvas.drawText` 进行文本整形。在编译时，可以选择使用 Harfbuzz/ICU（默认）或原始版本（"primitive_shaper"），后者仅进行换行处理。使用 Harfbuzz/ICU 会显著增加代码大小（从 4.3 MB 到 6.4 MB）。

### 变更
 - `SkCanvas.drawText()` 现在对原始字符串需要一个 `SkFont` 对象。


### 移除
 -  `SkPaint.setTextSize()`、`SkPaint.getTextSize()`、`SkPaint.setTypeface()` 应使用 `SkFont` 替代。
 - 已弃用的 `CanvasKitInit().then()` 接口（参见 0.3.1 说明）


### 修复
 - `ready()` 在已加载时的潜在 bug。

## [0.3.1] - 2019-01-04
### 新增
 - `SkFont` 现已暴露。
 - `MakeCanvasSurface` 现在可以直接接受一个 canvas 元素。
 - `MakeWebGLCanvasSurface` 现在可以接受一个 WebGL 上下文（整数）并直接使用。

### 变更
 - `CanvasKitInit(...).then()` 不再是推荐的初始化方式。它将在 0.4.0 中移除。请使用返回真正 Promise 的 `CanvasKitInit(...).ready()`。

### 移除
- `SkPaint.measureText` - 请改用 `SkFont.measureText`。

## [0.3.0] - 2018-12-18

### 新增
- 添加了 Canvas2D JS 层。这镜像了 HTML Canvas API。可以在编译时通过向 `compile.sh` 调用添加 `no_canvas` 来省略它。
- `CanvasKit.FontMgr.DefaultRef()` 和 `fontmgr.MakeTypefaceFromData` 用于加载字体。
- 暴露了 `SkPath.setVolatile`。一些动画通过将路径的易变性设置为 true 来获得性能提升。

### 修复
- `SkPath.addRect` 现在正确绘制逆时针与顺时针。

### 变更
- `CanvasKit.MakeImageShader` 不再接受编码字节，而是接受一个由 `CanvasKit.MakeImageFromEncoded` 创建的 `SkImage`。此外，可选参数 `clampIfUnpremul` 和 `localMatrix` 已被暴露。
- `SkPath.arcTo` 现在接受 `startAngle`、`sweepAngle`、`forceMoveTo` 作为附加参数。
- `SkPath.stroke` 有一个新选项 `precision`，默认为 1.0。
- CanvasKit 附带一种字体 (NotoMono) 而不是 Skia TestTypeface。鼓励客户端使用新的 `fontmgr.MakeTypefaceFromData` 以获得更多字体选择。

### 移除
- `CanvasKit.initFonts()` - 不再需要。


## [0.2.1] - 2018-11-20
变更日志历史的开始
