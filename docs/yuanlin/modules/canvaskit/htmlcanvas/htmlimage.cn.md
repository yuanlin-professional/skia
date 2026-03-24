# HTMLImage - HTML 图像元素模拟

> 源文件: `modules/canvaskit/htmlcanvas/htmlimage.js`

## 概述

`HTMLImage` 是 CanvasKit HTML Canvas 兼容层中对浏览器原生 `HTMLImageElement` 的轻量级模拟实现。它将 CanvasKit 的 `SkImage` 对象包装为一个具有 `width`、`height`、`naturalWidth`、`naturalHeight` 属性的对象，使其能够在 `CanvasRenderingContext2D.drawImage()` 等需要图像源的 API 中使用。

该文件仅有 11 行代码，是整个 htmlcanvas 兼容层中最简洁的模块之一，体现了"最小化适配"的设计哲学。

## 架构位置

```
CanvasKit (WASM)
├── SkImage (C++/WASM)          ← 底层图像对象
└── htmlcanvas 兼容层
    ├── htmlimage.js             ← 本文件: SkImage 的 HTMLImageElement 适配器
    ├── canvas2dcontext.js       ← drawImage() 中检测并解包 HTMLImage
    └── ...
```

`HTMLImage` 作为 CanvasKit 原生 `SkImage` 与 HTML Canvas 2D API 之间的桥梁。在 `canvas2dcontext.js` 的 `drawImage` 方法中，会通过 `instanceof HTMLImage` 检查传入的图像参数，如果匹配则调用 `getSkImage()` 获取底层的 SkImage 对象。

## 主要类与结构体

### `HTMLImage(skImage)`

构造函数，接受一个 CanvasKit `SkImage` 对象作为参数。

**实例属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `_skImage` | SkImage | 内部存储的 CanvasKit 图像引用（私有） |
| `width` | number | 图像宽度（像素），可写但写入无效果 |
| `height` | number | 图像高度（像素），可写但写入无效果 |
| `naturalWidth` | number | 图像原始宽度，等同于 `width` |
| `naturalHeight` | number | 图像原始高度，等同于 `height` |

**实例方法**：

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `getSkImage()` | SkImage | 返回底层的 CanvasKit SkImage 对象 |

## 公共 API 函数

### `HTMLImage(skImage)` - 构造函数

```javascript
function HTMLImage(skImage)
```

**参数**：
- `skImage` (SkImage): CanvasKit 的图像对象，必须提供有效的 `width()` 和 `height()` 方法。

**使用示例**：
```javascript
var skImage = CanvasKit.MakeImageFromEncoded(buffer);
var htmlImg = new HTMLImage(skImage);
ctx.drawImage(htmlImg, 0, 0);  // 可直接传给 drawImage
```

### `getSkImage()` - 获取底层图像

```javascript
htmlImage.getSkImage()  // 返回 SkImage
```

返回构造时传入的 `skImage` 引用。这是一个闭包方法——它通过闭包直接引用构造函数的参数，而非通过 `this._skImage` 访问。

## 内部实现细节

1. **闭包 vs 属性访问**: `getSkImage()` 方法通过闭包直接捕获构造函数参数 `skImage`，而非使用 `return this._skImage`。这意味着即使外部代码修改了 `this._skImage`，`getSkImage()` 仍然返回原始的 skImage 对象。

2. **可写但无效的属性**: `width`、`height`、`naturalWidth`、`naturalHeight` 都是普通的实例属性（非 getter/setter），因此是可写的。注释中指出这模仿了 `HTMLImageElement` 的行为——浏览器中这些属性也可以被赋值，但不会改变实际图像的尺寸。

3. **naturalWidth/naturalHeight 等同性**: `naturalWidth` 和 `naturalHeight` 直接等于 `width` 和 `height`。在浏览器中，`naturalWidth/Height` 表示图像的固有尺寸，而 `width/height` 可能被 CSS 样式修改。由于 CanvasKit 环境中不存在 CSS 样式系统，两者始终相同。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| CanvasKit `SkImage` | 输入依赖 | 构造函数需要一个有效的 SkImage 对象 |

**被依赖**：
- `canvas2dcontext.js` 中的 `drawImage()` 方法通过 `instanceof HTMLImage` 检测并解包图像

## 设计模式与设计决策

1. **适配器模式（Adapter Pattern）**: HTMLImage 是经典适配器模式的实现。它将 CanvasKit 的 SkImage 接口适配为 HTML Canvas API 期望的 HTMLImageElement 接口，使得上层代码可以统一处理图像对象。

2. **最小接口原则**: 只实现了 `drawImage()` 所需的最小属性集（width、height、naturalWidth、naturalHeight），没有模拟 HTMLImageElement 的 `src`、`onload`、`onerror` 等异步加载接口，因为 CanvasKit 环境中图像数据已经在内存中。

3. **构造函数模式**: 使用传统的函数构造函数（而非 ES6 class），与整个 htmlcanvas 兼容层的代码风格保持一致，并有利于 Closure Compiler 的优化。

## 性能考量

- **零拷贝**: `HTMLImage` 不复制图像数据，仅保存 SkImage 的引用。构造和使用的开销可以忽略不计。
- **轻量包装**: 整个对象仅包含 4 个数值属性和 1 个方法引用加 1 个内部 SkImage 引用，内存占用极小。
- **无生命周期管理**: HTMLImage 不负责 SkImage 的生命周期管理（没有 `dispose()` 或 `delete()` 方法）。调用者需自行管理底层 SkImage 的释放。

## 相关文件

- `modules/canvaskit/htmlcanvas/canvas2dcontext.js` - `drawImage()` 中使用 HTMLImage，通过 `instanceof` 检测后调用 `getSkImage()`
- `modules/canvaskit/htmlcanvas/htmlcanvas.js` - HTML Canvas 兼容层的主入口，注册 HTMLImage 到 CanvasKit 命名空间
- `modules/canvaskit/htmlcanvas/pattern.js` - CanvasPattern 可能也使用图像作为纹理源
