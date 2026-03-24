# radialgradient.js - 径向渐变实现

> 源文件: `modules/canvaskit/htmlcanvas/radialgradient.js`

## 概述

`radialgradient.js` 实现了 HTML Canvas API 中的径向渐变功能，对应 `CanvasRenderingContext2D.createRadialGradient()` 返回的渐变对象。该文件包含 77 行代码，定义了 `RadialCanvasGradient` 类，它将 Canvas 2D 的径向渐变语义映射到 CanvasKit/Skia 的 `TwoPointConicalGradient`（双点锥形渐变）上。

文件开头注释特别指出了一个重要的术语差异：Skia 中的"radial gradient"与 Canvas API 中的"radial gradient"含义不同——Canvas 的径向渐变在 Skia 中对应的是"两点锥形渐变"（TwoPointConicalGradient）。

## 架构位置

```
CanvasRenderingContext2D
├── createRadialGradient(x1, y1, r1, x2, y2, r2)
│       └── new RadialCanvasGradient(...)  ← 本文件
│
├── fillStyle = gradient
│       └── gradient._getShader(currentTransform)
│               └── CanvasKit.Shader.MakeTwoPointConicalGradient(...)
│
└── _fillPaint() / _strokePaint()
        └── paint.setShader(shader)
```

`RadialCanvasGradient` 充当 Canvas 2D API 与 CanvasKit Shader 系统之间的适配层。用户通过 `createRadialGradient()` 创建实例，通过 `addColorStop()` 添加颜色断点，然后将其赋给 `fillStyle` 或 `strokeStyle`。在实际绘制时，`_getShader()` 被调用以创建底层的 Skia shader。

## 主要类与结构体

### `RadialCanvasGradient(x1, y1, r1, x2, y2, r2)`

径向渐变对象，模拟浏览器的 `CanvasGradient` 接口。

**构造函数参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `x1` | number | 起始圆的圆心 X 坐标 |
| `y1` | number | 起始圆的圆心 Y 坐标 |
| `r1` | number | 起始圆的半径 |
| `x2` | number | 结束圆的圆心 X 坐标 |
| `y2` | number | 结束圆的圆心 Y 坐标 |
| `r2` | number | 结束圆的半径 |

**内部属性**：

| 属性 | 类型 | 初始值 | 说明 |
|------|------|--------|------|
| `_shader` | CanvasKit.Shader | null | 缓存的着色器对象 |
| `_colors` | Array | [] | 颜色断点数组（CanvasKit 颜色格式） |
| `_pos` | Array | [] | 颜色断点位置数组（0.0-1.0） |

## 公共 API 函数

### `addColorStop(offset, color)` - 添加颜色断点

```javascript
gradient.addColorStop(offset, color)
```

**参数**：
- `offset` (number): 颜色断点位置，范围 [0, 1]。小于 0、大于 1 或非有限数将抛出异常。
- `color` (string): CSS 颜色字符串，通过 `parseColor()` 解析。

**行为细节**：
- 如果在同一 offset 位置已存在颜色断点，新颜色会**覆盖**旧颜色（而非追加）。
- 新断点按 offset 值的升序插入到正确位置（使用线性扫描查找插入点）。
- 规范说明：多个相同 offset 的断点应按添加顺序排列，但由于 Canvas API 不提供删除断点的方法，覆盖行为等效于保留最后添加的值。

### `_copy()` - 复制渐变对象（内部方法）

```javascript
gradient._copy() -> RadialCanvasGradient
```

创建当前渐变对象的浅副本，复制颜色和位置数组（使用 `slice()`）。用于 `CanvasRenderingContext2D.save()` 保存填充/描边样式时。

### `_dispose()` - 释放着色器资源（内部方法）

```javascript
gradient._dispose()
```

删除缓存的 Skia shader 对象并置空引用。在渐变不再使用时或需要重新创建 shader 时调用。

### `_getShader(currentTransform)` - 获取 Skia 着色器（内部方法）

```javascript
gradient._getShader(currentTransform) -> CanvasKit.Shader
```

根据当前变换矩阵创建或重新创建 Skia shader。这是渐变对象最核心的方法。

**参数**：
- `currentTransform` (Float32Array): 当前 Canvas 2D 上下文的变换矩阵（3x3 行主序）。

**返回值**：
- CanvasKit.Shader 对象，可直接设置到 Paint 上。

## 内部实现细节

### 变换矩阵应用

根据 W3C 规范，渐变的控制点必须在渲染时受当前变换矩阵（CTM）影响。`_getShader` 的实现：

1. **点变换**：将两个圆心 `(x1, y1)` 和 `(x2, y2)` 通过 `CanvasKit.Matrix.mapPoints()` 映射到变换后的坐标空间。

2. **半径缩放**：从变换矩阵中提取缩放因子。计算方式为 X 轴和 Y 轴缩放分量的平均值：
   ```javascript
   var sx = currentTransform[0];  // 矩阵元素 [0,0]
   var sy = currentTransform[4];  // 矩阵元素 [1,1]
   var scaleFactor = (Math.abs(sx) + Math.abs(sy)) / 2;
   ```
   然后将两个半径乘以该缩放因子。

3. **Shader 创建**：调用 `CanvasKit.Shader.MakeTwoPointConicalGradient()` 创建底层 shader，使用 `CanvasKit.TileMode.Clamp`（边缘颜色延伸）作为平铺模式。

### 半径缩放的近似处理

当变换矩阵包含非均匀缩放（sx != sy）或旋转时，圆形应变为椭圆形。然而 Skia 的 TwoPointConicalGradient 仅支持圆形，因此使用平均缩放因子作为近似。这在非均匀缩放场景下会产生与浏览器原生实现的差异。

### Shader 的惰性创建与重建

- Shader 不在 `addColorStop()` 时创建，而是在 `_getShader()` 首次调用时创建。
- 每次调用 `_getShader()` 都会先 `_dispose()` 旧 shader 再创建新的。这是因为变换矩阵可能在两次绘制之间发生变化。
- 这意味着如果变换矩阵未变且颜色断点未变，shader 仍会被不必要地重建。

### addColorStop 的有序插入

颜色断点通过线性扫描找到正确的插入位置，然后使用 `Array.splice()` 插入。这确保 `_pos` 数组始终保持升序排列，这是 `MakeTwoPointConicalGradient()` 的要求。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| `CanvasKit.Shader.MakeTwoPointConicalGradient()` | WASM 方法 | 创建双点锥形渐变 shader |
| `CanvasKit.Matrix.mapPoints()` | WASM 方法 | 对渐变控制点应用矩阵变换 |
| `CanvasKit.TileMode.Clamp` | WASM 常量 | 渐变平铺模式 |
| `parseColor()` | color.js | CSS 颜色字符串解析 |

**被依赖**：
- `canvas2dcontext.js` - `createRadialGradient()` 创建实例；fillStyle/strokeStyle 的 setter 检测 `_getShader` 方法判断是否为效果对象

## 设计模式与设计决策

### 1. 惰性求值模式（Lazy Evaluation）

Shader 的创建被延迟到实际需要绘制时（`_getShader` 调用时）。这样做的理由：
- 创建时变换矩阵未知，无法提前生成正确的 shader
- 用户可能在创建渐变后添加多个颜色断点，提前创建会导致多次重建

### 2. 术语桥接

文件开头的注释明确了术语映射关系：Canvas 的 "RadialGradient" = Skia 的 "TwoPointConicalGradient"。这对于理解和维护代码至关重要。

### 3. 协议接口（Duck Typing）

`RadialCanvasGradient` 通过实现 `_getShader()`、`_copy()`、`_dispose()` 方法来满足 `CanvasRenderingContext2D` 对"效果对象"的接口期望。这些方法名称在 LinearCanvasGradient 和 CanvasPattern 中也存在，形成隐式的接口约定。

## 性能考量

- **Shader 重建开销**: 每次 `_getShader()` 调用都销毁旧 shader 并创建新 shader，即使参数未变。这涉及 WASM 堆上的内存分配和释放。在动画场景中，如果渐变被频繁重绘但变换矩阵不变，这是一个可优化点。

- **线性扫描插入**: `addColorStop` 使用 O(n) 的线性扫描查找插入位置。对于典型的渐变（2-10 个断点），性能不是问题。

- **缩放因子近似**: 平均缩放因子的计算仅使用矩阵对角线元素，忽略了旋转和剪切分量。这在大多数常见场景下足够准确，但在极端变换下可能产生视觉偏差。

- **内存管理**: `_dispose()` 确保 shader 资源被正确释放。`_copy()` 创建新的 RadialCanvasGradient 实例但不复制 shader（shader 为 null），只在需要时重建。

## 相关文件

- `modules/canvaskit/htmlcanvas/canvas2dcontext.js` - 通过 `createRadialGradient()` 创建实例，通过 `_getShader()` 获取 shader
- `modules/canvaskit/htmlcanvas/lineargradient.js` - 线性渐变的对应实现，与本文件结构类似
- `modules/canvaskit/htmlcanvas/color.js` - `parseColor()` 用于解析 `addColorStop` 的颜色参数
- `modules/canvaskit/htmlcanvas/pattern.js` - CanvasPattern，实现了相同的效果对象接口（`_getShader`/`_copy`/`_dispose`）
- `modules/canvaskit/htmlcanvas/htmlcanvas.js` - 注册 RadialCanvasGradient 到 CanvasKit
