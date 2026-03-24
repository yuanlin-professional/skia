# canvas2dcontext.js - HTML Canvas 2D 渲染上下文完整实现

> 源文件: `modules/canvaskit/htmlcanvas/canvas2dcontext.js`

## 概述

`canvas2dcontext.js` 是 CanvasKit HTML Canvas 兼容层的核心文件，实现了完整的 `CanvasRenderingContext2D` 接口。该文件包含 1165 行代码，将 W3C HTML Canvas 2D Context API 映射到 CanvasKit（Skia 的 WebAssembly 封装）的底层绘图原语上，使开发者能够使用标准的 Canvas 2D API 进行硬件加速的图形渲染。

主要功能包括：路径绘制（直线、曲线、弧线、椭圆）、图形填充与描边、图像绘制、文本渲染、变换矩阵操作、状态保存/恢复、阴影效果、渐变与图案、像素数据操作，以及合成模式（globalCompositeOperation）的完整支持。

## 架构位置

```
Web 应用代码
    │  调用标准 Canvas 2D API
    ▼
CanvasRenderingContext2D (本文件)
    │  适配/转译
    ▼
CanvasKit JavaScript API
    │  WASM 调用
    ▼
Skia C++ 渲染引擎
    │
    ▼
GPU / CPU 后端
```

本文件是整个 htmlcanvas 兼容层的中枢，连接上层的标准 Canvas API 调用与底层的 CanvasKit/Skia 渲染能力。它依赖同目录下的 `color.js`（颜色解析）、`path2d.js`（路径操作辅助函数）、`radialgradient.js`/`lineargradient.js`（渐变）、`pattern.js`（图案）和 `htmlimage.js`（图像适配）等模块。

## 主要类与结构体

### `CanvasRenderingContext2D(skcanvas)`

核心类，模拟浏览器的 CanvasRenderingContext2D 接口。

**构造函数参数**：
- `skcanvas`: CanvasKit 的 Canvas 对象（由 Surface 创建）

**内部状态属性**：

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `_canvas` | CanvasKit.Canvas | (构造参数) | 底层 Skia 画布 |
| `_paint` | CanvasKit.Paint | 新建实例 | 共享画笔对象 |
| `_font` | CanvasKit.Font | 10px monospace | 文本渲染字体 |
| `_currentPath` | CanvasKit.PathBuilder | 空路径 | 当前构建中的路径 |
| `_currentTransform` | Float32Array | 单位矩阵 | 当前变换矩阵 (3x3) |
| `_strokeStyle` | Color/Effect | BLACK | 描边样式 |
| `_fillStyle` | Color/Effect | BLACK | 填充样式 |
| `_shadowBlur` | number | 0 | 阴影模糊半径 |
| `_shadowColor` | Color | TRANSPARENT | 阴影颜色 |
| `_shadowOffsetX` | number | 0 | 阴影 X 偏移 |
| `_shadowOffsetY` | number | 0 | 阴影 Y 偏移 |
| `_globalAlpha` | number | 1 | 全局透明度 (0-1) |
| `_strokeWidth` | number | 1 | 描边宽度 |
| `_lineDashOffset` | number | 0 | 虚线偏移 |
| `_lineDashList` | Array | [] | 虚线模式数组 |
| `_globalCompositeOperation` | BlendMode | SrcOver | 合成/混合模式 |
| `_canvasStateStack` | Array | [] | 状态保存栈 |
| `_toCleanUp` | Array | [] | 待清理的效果对象 |

### `BlurRadiusToSigma(radius)` - 辅助函数

将 CSS 阴影模糊半径转换为高斯模糊的 sigma 值。当前实现采用 W3C 规范标准（`radius / 2`），同时保留了 Chrome/Blink 遗留实现的注释（`0.288675 * radius + 0.5`）供参考。

## 公共 API 函数

### 属性（通过 Object.defineProperty 定义）

| 属性名 | 读写 | 类型 | 说明 |
|--------|------|------|------|
| `currentTransform` | R/W | DOMMatrix-like | 当前变换矩阵，以 {a,b,c,d,e,f} 格式读写 |
| `fillStyle` | R/W | string/Gradient/Pattern | 填充样式：颜色字符串或渐变/图案对象 |
| `font` | R/W | string | CSS 字体描述符，如 `'16px Arial'` |
| `globalAlpha` | R/W | number | 全局透明度，忽略 NaN/Inf/越界值 |
| `globalCompositeOperation` | R/W | string | 合成操作，支持全部 26 种标准模式 |
| `imageSmoothingEnabled` | R/W | boolean | 始终返回 true（忽略设置） |
| `imageSmoothingQuality` | R/W | string | 始终返回 'high'（忽略设置） |
| `lineCap` | R/W | string | 线端样式：'butt'/'round'/'square' |
| `lineDashOffset` | R/W | number | 虚线偏移量 |
| `lineJoin` | R/W | string | 线连接样式：'miter'/'round'/'bevel' |
| `lineWidth` | R/W | number | 线宽度，忽略 0/负值/NaN |
| `miterLimit` | R/W | number | 尖角限制值 |
| `shadowBlur` | R/W | number | 阴影模糊半径 |
| `shadowColor` | R/W | string | 阴影颜色 |
| `shadowOffsetX` | R/W | number | 阴影 X 偏移 |
| `shadowOffsetY` | R/W | number | 阴影 Y 偏移 |
| `strokeStyle` | R/W | string/Gradient/Pattern | 描边样式 |
| `canvas` | R | null | 只读属性，始终为 null |

### 路径操作方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `arc()` | `(x, y, radius, startAngle, endAngle, ccw)` | 添加圆弧到当前路径 |
| `arcTo()` | `(x1, y1, x2, y2, radius)` | 添加切线弧到当前路径 |
| `beginPath()` | `()` | 清空当前路径并创建新路径 |
| `bezierCurveTo()` | `(cp1x, cp1y, cp2x, cp2y, x, y)` | 三次贝塞尔曲线 |
| `closePath()` | `()` | 闭合当前子路径 |
| `ellipse()` | `(x, y, rx, ry, rotation, startAngle, endAngle, ccw)` | 椭圆弧 |
| `lineTo()` | `(x, y)` | 直线段 |
| `moveTo()` | `(x, y)` | 移动画笔到指定位置 |
| `quadraticCurveTo()` | `(cpx, cpy, x, y)` | 二次贝塞尔曲线 |
| `rect()` | `(x, y, width, height)` | 矩形子路径 |

### 绘制方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `clearRect()` | `(x, y, width, height)` | 清除矩形区域（使用 Clear 混合模式） |
| `fill()` | `(path?, fillRule?)` | 填充路径，支持 Path2D 和 evenodd/nonzero 填充规则 |
| `fillRect()` | `(x, y, width, height)` | 填充矩形 |
| `fillText()` | `(text, x, y, maxWidth?)` | 填充文本（maxWidth 暂未实现） |
| `stroke()` | `(path?)` | 描边路径 |
| `strokeRect()` | `(x, y, width, height)` | 描边矩形 |
| `strokeText()` | `(text, x, y, maxWidth?)` | 描边文本（maxWidth 暂未实现） |
| `drawImage()` | `(img, ...)` | 绘制图像，支持 3/5/9 参数形式 |

### 变换方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `rotate()` | `(radians)` | 旋转（弧度） |
| `scale()` | `(sx, sy)` | 缩放 |
| `translate()` | `(dx, dy)` | 平移 |
| `transform()` | `(a, b, c, d, e, f)` | 乘以变换矩阵 |
| `setTransform()` | `(a, b, c, d, e, f)` | 重置并设置变换矩阵 |
| `resetTransform()` | `()` | 重置为单位矩阵 |

### 状态与辅助方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `save()` | `()` | 保存当前绘图状态到栈 |
| `restore()` | `()` | 从栈恢复绘图状态 |
| `clip()` | `(path?, fillRule?)` | 裁剪区域 |
| `createImageData()` | `(imageData)` 或 `(w, h)` | 创建空白 ImageData |
| `createLinearGradient()` | `(x1, y1, x2, y2)` | 创建线性渐变 |
| `createRadialGradient()` | `(x1, y1, r1, x2, y2, r2)` | 创建径向渐变 |
| `createPattern()` | `(image, repetition)` | 创建图案 |
| `getImageData()` | `(x, y, w, h)` | 读取像素数据 |
| `putImageData()` | `(imageData, x, y, ...)` | 写入像素数据 |
| `getLineDash()` | `()` | 获取虚线模式 |
| `setLineDash()` | `(dashes)` | 设置虚线模式 |
| `isPointInPath()` | `(x, y, fillmode?)` 或 `(path, x, y, fillmode?)` | 点是否在路径填充区域内 |
| `isPointInStroke()` | `(x, y)` 或 `(path, x, y)` | 点是否在路径描边区域内 |
| `measureText()` | `(text)` | 测量文本宽度 |

### 未实现/空操作方法

以下方法存在但不执行任何操作（仅用于 Web 环境兼容）：
- `addHitRegion()`
- `clearHitRegions()`
- `drawFocusIfNeeded()`
- `removeHitRegion()`
- `scrollPathIntoView()`

## 内部实现细节

### 变换矩阵管理策略

这是本文件最复杂的实现细节。变换操作（translate、rotate、scale、transform）采用"逆向补偿"策略：

1. 当用户调用变换方法时，**逆变换**会立即应用到当前路径（`_currentPath`）上。
2. 同时将正变换应用到 CanvasKit 画布上。
3. 这样在绘制时，路径经过画布变换后，之前应用的逆变换恰好抵消，使路径在画布变换应用前的坐标空间中保持不变。
4. 后续新增的路径指令则会受到新变换的影响。

```javascript
// 例：translate 的实现
this.translate = function(dx, dy) {
    var inverted = CanvasKit.Matrix.translated(-dx, -dy);
    this._currentPath.transform(inverted);     // 逆变换应用到已有路径
    this._canvas.translate(dx, dy);             // 正变换应用到画布
    this._currentTransform = this._canvas.getTotalMatrix();
};
```

### 阴影渲染机制

阴影通过三步实现：
1. `_shadowPaint(basePaint)`: 复制基础画笔，设置阴影颜色（含 globalAlpha），添加高斯模糊 MaskFilter。
2. `_applyShadowOffsetMatrix()`: 在设备坐标系中应用阴影偏移——先撤销 CTM，平移阴影偏移量，再恢复 CTM。
3. 绘制时先画阴影再画实际图形，使用 save/restore 隔离阴影偏移矩阵。

阴影仅在满足以下条件时生成：alpha 通道非零，且 shadowBlur/shadowOffsetX/shadowOffsetY 中至少一个非零。

### 填充/描边画笔管理

- `_fillPaint()`: 创建 paint 副本，设置 Fill 样式。如果 `_fillStyle` 是颜色则直接设置（乘以 globalAlpha）；如果是渐变/图案则获取其 shader。
- `_strokePaint()`: 创建 paint 副本，设置 Stroke 样式，应用 strokeWidth 和虚线效果（PathEffect.MakeDash）。
- 两者都返回带有 `dispose()` 方法的画笔副本，调用者负责清理。

### globalCompositeOperation 映射

支持全部 26 种 Canvas 合成模式到 CanvasKit BlendMode 的映射：
- **合成模式 (12种)**: source-over, destination-over, copy, destination, clear, source-in, destination-in, source-out, destination-out, source-atop, destination-atop, xor, lighter
- **混合模式 (14种)**: multiply, screen, overlay, darken, lighten, color-dodge, color-burn, hard-light, soft-light, difference, exclusion, hue, saturation, color, luminosity

注意：`plus-darker` 不受支持，会抛出异常。

### 状态保存/恢复

`save()` 将以下状态压入 `_canvasStateStack`：
- 变换矩阵 (ctm)、画笔副本 (paint)、虚线列表 (ldl)、描边宽度 (sw)
- 描边样式 (ss)、填充样式 (fs)、阴影参数 (sox, soy, sb, shc)
- 全局透明度 (ga)、合成操作 (gco)、虚线偏移 (ldo)、字体字符串 (fontstr)
- 裁剪状态通过 `_canvas.save()` 由 Skia 底层管理

`restore()` 恢复所有状态，并通过矩阵差值计算补偿路径变换。

### putImageData 的设备空间操作

`putImageData()` 必须在设备坐标空间中操作（不受 CTM 影响）。实现方式：
1. 计算当前变换的逆矩阵
2. `save()` 后 `concat(inverted)` 撤销 CTM
3. 绘制图像
4. `restore()` 恢复 CTM

同时支持 dirty rectangle 参数，按照 W3C 规范处理负宽/高值的规范化。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| `CanvasKit` (全局) | WASM 模块 | 提供 Paint、Font、Canvas、PathBuilder、Matrix 等核心类 |
| `color.js` | 同层模块 | `parseColor()` 和 `colorToString()` 函数 |
| `path2d.js` | 同层模块 | `arc()`, `arcTo()`, `lineTo()` 等路径辅助函数 |
| `lineargradient.js` | 同层模块 | `LinearCanvasGradient` 类 |
| `radialgradient.js` | 同层模块 | `RadialCanvasGradient` 类 |
| `pattern.js` | 同层模块 | `CanvasPattern` 类 |
| `htmlimage.js` | 同层模块 | `HTMLImage` 类（drawImage 中使用） |
| `util.js` | 同层模块 | `allAreFinite()`, `radiansToDegrees()`, `almostEqual()` 等工具函数 |
| `font.js` | 同层模块 | `getTypeface()` 字体解析函数 |

**被依赖**：
- `htmlcanvas.js` 主入口文件将 `CanvasRenderingContext2D` 注册到 CanvasKit 命名空间

## 设计模式与设计决策

### 1. 门面模式（Facade Pattern）
`CanvasRenderingContext2D` 是 CanvasKit 复杂 API 的门面，将 Skia 的 Paint/Canvas/Path/Matrix/Shader/MaskFilter 等众多概念隐藏在简洁的 Canvas 2D API 背后。

### 2. 属性代理模式
通过 `Object.defineProperty` 实现属性的 getter/setter，在 set 时进行输入验证（如 globalAlpha 忽略越界值）和类型转换（如 fillStyle 从字符串到颜色对象的转换）。

### 3. Copy-on-Use 画笔管理
每次绘制操作都创建画笔副本（`_fillPaint()`/`_strokePaint()`），而非直接修改共享画笔。这避免了状态污染，但增加了每次绘制的开销。画笔副本在使用后立即 `dispose()`。

### 4. 逆变换路径补偿
变换操作采用逆变换补偿策略（而非路径记录+重放），使路径可以在变换改变前后正确累积。这是为了匹配浏览器中路径在变换改变时的行为：已添加的路径段保持在它们被添加时的坐标空间中。

### 5. 规范一致性优先
实现严格遵循 W3C HTML Canvas 2D Context 规范：
- 无效参数的静默忽略（如非有限数值、负线宽）
- `closePath()` 对单点路径不执行操作
- `setLineDash()` 奇数长度数组自动翻倍
- `putImageData()` 在设备空间操作
- 阴影偏移在设备坐标中应用

### 6. 惰性效果创建
渐变的 shader 在绘制时才创建（`_getShader(currentTransform)`），而非在 `createLinearGradient()` 时，因为 shader 需要结合当前变换矩阵。

## 性能考量

1. **画笔副本开销**: 每次 fill/stroke/fillRect/strokeRect/fillText/strokeText 调用都会创建画笔副本。对于高频绘制场景（如动画），这会产生显著的对象分配和 GC 压力。这是为了正确性（避免状态污染）而做出的性能妥协。

2. **阴影双重绘制**: 启用阴影时，每个绘制操作会执行两次——先画阴影再画实体。如果不需要阴影，应确保 `shadowColor` 的 alpha 为 0 以跳过阴影分支。

3. **变换矩阵同步**: 每次变换操作后都调用 `this._canvas.getTotalMatrix()` 从 WASM 侧获取最新矩阵，涉及跨 WASM 边界的数据传输。

4. **路径逆变换**: 每次变换操作都会对当前路径应用逆变换矩阵，路径越复杂开销越大。在复杂路径构建场景中，频繁改变变换可能成为瓶颈。

5. **图像平滑始终开启**: `imageSmoothingEnabled` 和 `imageSmoothingQuality` 的设置被忽略，始终使用高质量图像平滑。这简化了实现但无法在需要像素精确渲染时禁用抗锯齿。

6. **TextBlob 临时创建**: `fillText()` 和 `strokeText()` 每次调用都创建临时 TextBlob 并在使用后删除。频繁的相同文本渲染没有缓存机制。

7. **measureText() 简化实现**: 当前实现通过累加字形宽度计算文本宽度，仅返回 `{width}` 对象，不包含规范中完整的 TextMetrics 属性（如 actualBoundingBox 等）。

8. **资源清理**: `_dispose()` 方法清理所有分配的资源（画笔、字体、路径、效果对象）。未调用 `_dispose()` 会导致 WASM 内存泄漏，因为 CanvasKit 对象不受 JavaScript GC 管理。

## 相关文件

- `modules/canvaskit/htmlcanvas/htmlcanvas.js` - 兼容层主入口，注册 CanvasRenderingContext2D
- `modules/canvaskit/htmlcanvas/color.js` - 颜色解析/序列化
- `modules/canvaskit/htmlcanvas/path2d.js` - Path2D 类和路径辅助函数
- `modules/canvaskit/htmlcanvas/lineargradient.js` - 线性渐变实现
- `modules/canvaskit/htmlcanvas/radialgradient.js` - 径向渐变实现
- `modules/canvaskit/htmlcanvas/pattern.js` - 图案填充实现
- `modules/canvaskit/htmlcanvas/htmlimage.js` - HTMLImage 适配器
- `modules/canvaskit/htmlcanvas/font.js` - CSS 字体字符串解析
- `modules/canvaskit/htmlcanvas/util.js` - 工具函数
- `modules/canvaskit/htmlcanvas/preamble.js` - 作用域前导代码
- `modules/canvaskit/htmlcanvas/postamble.js` - 作用域闭合代码
