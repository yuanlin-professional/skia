# CanvasKit Skottie C++ 绑定 (skottie_bindings)

> 源文件: `modules/canvaskit/skottie_bindings.cpp`

## 概述

`skottie_bindings.cpp` 是 CanvasKit 中 Skottie（Lottie 动画引擎）的核心 C++ 绑定文件，约 860 行代码。它通过 Emscripten 的 `embind` 机制，将 Skia 的 Lottie 动画播放、属性控制、插槽管理和文本编辑功能完整暴露给 JavaScript。该文件定义了 `ManagedAnimation` 管理类、`SkottieAssetProvider` 资源提供器、`JSLogger` 日志适配器等核心类，是 CanvasKit Skottie 功能的 C++ 实现中枢。

## 架构位置

```
JavaScript (skottie.js)
  └── _MakeManagedAnimation()
      └── skottie_bindings.cpp
          ├── ManagedAnimation  ← 动画管理包装类
          │   ├── skottie::Animation  ← 核心动画引擎
          │   ├── CustomPropertyManager ← 属性管理
          │   ├── SlotManager ← 插槽系统
          │   └── TextEditor ← 文本编辑器
          ├── SkottieAssetProvider ← 资源加载
          ├── JSLogger ← JS 日志桥接
          └── EMSCRIPTEN_BINDINGS(Skottie) ← 绑定声明
```

## 主要类与结构体

### SimpleSlottableTextProperty

JS 端文本属性的 C++ 映射结构体，包含字体、文本内容、大小、对齐、颜色等字段。实现了到 `skottie::TextPropertyValue` 的隐式转换运算符。

| 字段 | 类型 | 说明 |
|------|------|------|
| `typeface` | `sk_sp<SkTypeface>` | 字体 |
| `text` | `std::string` | 文本内容 |
| `textSize` / `minTextSize` / `maxTextSize` | `float` | 字体大小范围 |
| `horizAlign` | `para::TextAlign` | 水平对齐 |
| `vertAlign` | `skottie::Shaper::VAlign` | 垂直对齐 |
| `fillColorPtr` / `strokeColorPtr` | `WASMPointerF32` | 颜色指针（从 WASM 堆读取） |
| `boundingBoxPtr` | `WASMPointerF32` | 边界框指针 |

### WebTrack

包装 JS 音频播放器对象的 `ExternalTrackAsset` 实现，将 `seek(t)` 调用转发到 JS 对象的 `seek` 方法。

### SkottieAssetProvider

自定义的 `skottie::ResourceProvider` 实现，管理从 JS 传入的资源（图像、音频、字体等）。

| 方法 | 说明 |
|------|------|
| `loadImageAsset(path, name, id)` | 按名称查找图像资源并解码 |
| `loadAudioAsset(path, name, id)` | 按 ID 查找音频播放器 |
| `load(path, name)` | 按名称加载原始数据资源 |

### JSLogger

将 JS 日志对象适配为 `skottie::Logger` 接口，将错误和警告转发到 JS 端的 `onError`/`onWarning` 方法。

### ManagedAnimation

核心管理类，封装了 `skottie::Animation`、`CustomPropertyManager`、`SlotManager` 和可选的 `TextEditor`。

**动画控制**:
| 方法 | 说明 |
|------|------|
| `render(canvas, dst)` | 渲染到画布 |
| `seek(t)` / `seekFrame(frame)` | 时间定位，返回损伤矩形 |
| `duration()` / `fps()` / `size()` / `version()` | 动画元数据 |

**属性管理**:
| 方法 | 说明 |
|------|------|
| `getColorProps()` / `setColor()` | 颜色属性读写 |
| `getOpacityProps()` / `setOpacity()` | 透明度属性读写 |
| `getTextProps()` / `setText()` | 文本属性读写 |
| `getTransformProps()` / `setTransform()` | 变换属性读写 |
| `getMarkers()` | 获取动画标记列表 |

**插槽系统**:
| 方法 | 说明 |
|------|------|
| `getSlotInfo()` | 获取所有插槽 ID 分类信息 |
| `getColorSlot()` / `setColorSlot()` | 颜色插槽 |
| `getScalarSlot()` / `setScalarSlot()` | 标量插槽 |
| `getVec2Slot()` / `setVec2Slot()` | 2D 向量插槽 |
| `getTextSlot()` / `setTextSlot()` | 文本插槽 |
| `setImageSlot()` | 图像插槽 |

**文本编辑器**:
| 方法 | 说明 |
|------|------|
| `attachEditor(layerID, layerIndex)` | 附加文本编辑器到指定图层 |
| `enableEditor(enable)` | 启用/禁用编辑器 |
| `dispatchEditorKey(key)` | 分发键盘事件 |
| `dispatchEditorPointer(x, y, state, mod)` | 分发鼠标事件 |
| `setEditorCursorWeight(w)` | 设置光标粗细 |

## 公共 API 函数

### EMSCRIPTEN_BINDINGS 暴露的函数

| 函数 | 说明 |
|------|------|
| `MakeAnimation(json)` | 从 JSON 创建简单动画 |
| `_MakeManagedAnimation(json, assetCount, nptr, dptr, sptr, prop_prefix, soundMap, logger)` | 从 JSON 和打包资源创建受管动画 |

### 暴露的枚举

| 枚举 | 说明 |
|------|------|
| `InputState` | 输入状态 (Down/Up/Move/Right/Left) |
| `ModifierKey` | 修饰键 (None/Shift/Control/Option/Command/FirstPress) |
| `VerticalTextAlign` | 垂直文本对齐 (Top/TopBaseline/VisualTop/VisualCenter/VisualBottom) |
| `ResizePolicy` | 文本缩放策略 (None/ScaleToFit/DownscaleToFit) |

## 内部实现细节

### 资源解包与编解码器注册

`_MakeManagedAnimation` 从 WASM 堆中的指针数组解包资源名称、数据和大小。使用 `SkOnce` 确保图像编解码器（PNG/JPEG/GIF/WEBP）只注册一次。所有资源同时传给 `SkottieAssetProvider` 和自定义字体管理器（因为无法在此阶段区分图像和字体）。

### 资源加载链

资源通过 `DataURIResourceProviderProxy` 包装，支持 Base64 编码的 Data URI。底层由 `SkottieAssetProvider` 提供实际资源查找。图像资源通过 `DecodeImageData` 解码为多帧图像资产。

### 颜色转换

颜色在 JS 端以 `Float32Array(4)` 表示（SkColor4f），在 C++ 端通过 `ptrToSkColor4f` 从 WASM 指针读取，再调用 `toSkColor()` 转换为 32 位 SkColor。

### 文本属性转换

`SimpleSlottableTextProperty` 到 `TextPropertyValue` 的转换处理了多种枚举映射：
- `TextAlign` (Left/Center/Right) -> `SkTextUtils::Align`
- `LineBreakType` (Soft/Hard) -> `Shaper::LinebreakPolicy`
- `TextDirection` (LTR/RTL) -> `Shaper::Direction`

### 文本编辑器键盘映射

`dispatchEditorKey` 将 Web 标准按键名映射到编辑器内部字符：
- `ArrowLeft` -> `[`
- `ArrowRight` -> `]`
- `Backspace` -> `\`
- 单 Unicode 码点直接传递

### 属性返回的 JSArray/JSObject 构建

所有返回 JS 对象的方法（如 `getColorProps`, `getTextSlot`, `getTransformProps`）手动构建 `emscripten::val` 对象，使用 `MakeTypedArray` 传递浮点数组。

## 依赖关系

| 类别 | 依赖项 |
|------|-------|
| Skia 核心 | SkCanvas, SkImage, SkFontMgr, SkString, SkCodec |
| Skottie | Skottie.h, SkottieProperty.h, SlotManager.h, SkottieUtils.h, TextEditor.h |
| 段落排版 | Paragraph.h（用于文本对齐枚举） |
| 资源管理 | SkResources.h（DataURIResourceProviderProxy, MultiFrameImageAsset） |
| 场景图 | SkSGInvalidationController.h（损伤矩形追踪） |
| 编解码器 | SkGifDecoder, SkJpegDecoder, SkPngDecoder, SkWebpDecoder（条件编译） |
| 字体 | SkFontMgr_data.h（自定义数据字体管理器） |
| Unicode | SkUnicode.h（换行类型） |
| 文本塑形 | SkShapers/FactoryHelpers.h |
| Emscripten | emscripten.h, emscripten/bind.h |

## 设计模式与设计决策

- **外观模式**: `ManagedAnimation` 是一个外观（Facade），统一了 Animation、PropertyManager、SlotManager 和 TextEditor 的接口
- **资源提供者模式**: `SkottieAssetProvider` 实现 `ResourceProvider` 接口，将 JS 端传入的资源字典转化为 Skia 资源加载接口
- **适配器模式**: `JSLogger` 和 `WebTrack` 将 JS 对象适配为 C++ 接口
- **延迟编解码器注册**: 使用 `SkOnce` 在首次创建动画时注册编解码器，避免不必要的初始化
- **值对象绑定**: `SimpleSlottableTextProperty` 使用 `value_object` 绑定，允许 JS 端直接以普通对象形式传入
- **常量标记**: `constant("managed_skottie", true)` 和 `constant("skottie", true)` 允许 JS 端检测 Skottie 模块是否已编译链接

## 性能考量

- `seek`/`seekFrame` 使用 `InvalidationController` 追踪损伤矩形，只返回需要重绘的区域
- 属性查询方法（`getColorProps` 等）每次调用都创建新的 JS 数组，频繁查询时应缓存结果
- 图像资源使用 `MultiFrameImageAsset` 支持多帧（如 GIF），预解码策略避免渲染时解码
- 字体资源通过 `SkFontMgr_New_Custom_Data` 创建自定义字体管理器，所有资源都会被尝试作为字体加载（因为无法在此阶段区分类型）
- 文本编辑器的键盘事件处理使用 `SkUTF::NextUTF8` 解析 UTF-8，对单码点输入高效

## 相关文件

- `modules/canvaskit/skottie.js` — JS 端辅助层
- `modules/skottie/include/Skottie.h` — Skottie 核心 API
- `modules/skottie/include/SlotManager.h` — 插槽管理器
- `modules/skottie/utils/SkottieUtils.h` — 属性管理工具
- `modules/skottie/utils/TextEditor.h` — 文本编辑器
- `modules/skresources/include/SkResources.h` — 资源加载框架
- `modules/canvaskit/WasmCommon.h` — WASM 指针类型和辅助函数
