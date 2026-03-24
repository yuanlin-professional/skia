# path2d.js - 路径构建函数与 Path2D 类

> 源文件: `modules/canvaskit/htmlcanvas/path2d.js`

## 概述

`path2d.js` 实现了 HTML Canvas 规范中的 `CanvasPath` 接口方法（作为自由函数）以及 `Path2D` 类。该文件包含 209 行代码，是整个 htmlcanvas 兼容层中路径绑制系统的核心。

文件分为两部分：
1. **路径辅助函数**（第 1-141 行）：`arc`、`arcTo`、`bezierCurveTo`、`closePath`、`ellipse`、`lineTo`、`moveTo`、`quadraticCurveTo`、`rect` 等独立函数，接受 PathBuilder 作为第一个参数。这些函数同时被 `CanvasRenderingContext2D` 和 `Path2D` 类共享使用。
2. **Path2D 类**（第 143-209 行）：对上述辅助函数的对象化封装，实现了标准 Path2D 接口。

## 架构位置

```
CanvasRenderingContext2D                Path2D 类
├── this.arc(...)                       ├── this.arc(...)
├── this.lineTo(...)                    ├── this.lineTo(...)
│   ...                                 │   ...
└── 调用自由函数                         └── 调用自由函数
         │                                       │
         ▼                                       ▼
    路径辅助函数 (arc, lineTo, ellipse, ...)
         │
         ▼
    CanvasKit.PathBuilder (WASM)
         │
         ▼
    Skia SkPathBuilder (C++)
```

路径辅助函数作为共享基础设施，被 `CanvasRenderingContext2D`（操作 `_currentPath`）和 `Path2D`（操作 `this._path`）同时使用，避免了代码重复。

## 主要类与结构体

### Path2D(path?)

模拟浏览器原生 `Path2D` 对象的构造函数。

**构造函数参数**：
- `path`（可选）：初始路径数据，可以是：
  - **SVG 路径字符串**（如 `'M 10 10 L 20 20'`）：通过 `CanvasKit.Path.MakeFromSVGString()` 解析
  - **另一个 Path2D 对象**：通过 `_getPath()` 获取路径快照并复制
  - **未提供**：创建空路径

**内部属性**：

| 属性 | 类型 | 说明 |
|------|------|------|
| `_path` | CanvasKit.PathBuilder | 内部路径构建器实例 |

### 路径辅助函数

这些函数不属于任何类，而是模块级自由函数。它们的第一个参数都是 `skpath`（CanvasKit.PathBuilder 实例）。

| 函数 | 说明 |
|------|------|
| `arc(skpath, x, y, radius, startAngle, endAngle, ccw)` | 圆弧（委托给 ellipse） |
| `arcTo(skpath, x1, y1, x2, y2, radius)` | 切线弧 |
| `bezierCurveTo(skpath, cp1x, cp1y, cp2x, cp2y, x, y)` | 三次贝塞尔曲线 |
| `closePath(skpath)` | 闭合子路径 |
| `_ellipseHelper(skpath, x, y, radiusX, radiusY, startAngle, endAngle)` | 椭圆绘制内部辅助 |
| `ellipse(skpath, x, y, radiusX, radiusY, rotation, startAngle, endAngle, ccw)` | 完整椭圆弧 |
| `lineTo(skpath, x, y)` | 直线段 |
| `moveTo(skpath, x, y)` | 移动到指定点 |
| `quadraticCurveTo(skpath, cpx, cpy, x, y)` | 二次贝塞尔曲线 |
| `rect(skpath, x, y, width, height)` | 矩形 |

## 公共 API 函数

### Path2D 实例方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `addPath(path2d, transform?)` | `(Path2D, DOMMatrix?) -> void` | 添加另一个 Path2D 的路径，可选变换 |
| `arc()` | `(x, y, radius, startAngle, endAngle, ccw?) -> void` | 圆弧 |
| `arcTo()` | `(x1, y1, x2, y2, radius) -> void` | 切线弧 |
| `bezierCurveTo()` | `(cp1x, cp1y, cp2x, cp2y, x, y) -> void` | 三次贝塞尔曲线 |
| `closePath()` | `() -> void` | 闭合当前子路径 |
| `ellipse()` | `(x, y, rx, ry, rotation, startAngle, endAngle, ccw?) -> void` | 椭圆弧 |
| `lineTo()` | `(x, y) -> void` | 直线段 |
| `moveTo()` | `(x, y) -> void` | 移动画笔位置 |
| `quadraticCurveTo()` | `(cpx, cpy, x, y) -> void` | 二次贝塞尔曲线 |
| `rect()` | `(x, y, width, height) -> void` | 矩形子路径 |

### Path2D 内部方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `_getPath()` | `() -> CanvasKit.Path` | 返回当前路径的快照（snapshot），调用者负责删除 |

## 内部实现细节

### 椭圆弧的绘制算法 (ellipse / _ellipseHelper)

这是本文件最复杂的实现，共约 60 行代码，基于 Chrome/Blink 的实现逻辑。

**角度规范化（基于 Chrome 的 CanonicalizeAngle）**：
1. 将 startAngle 规范化到 [0, 2*PI) 范围
2. 计算规范化偏移量 delta，同步调整 endAngle

**终止角调整（基于 Chrome 的 AdjustEndAngle）**：
- 非逆时针且弧度 >= 2*PI：画完整椭圆（endAngle = startAngle + 2*PI）
- 逆时针且弧度 >= 2*PI：画完整椭圆（endAngle = startAngle - 2*PI）
- 非逆时针且 startAngle > endAngle：补全到正方向
- 逆时针且 startAngle < endAngle：补全到反方向

**360 度特殊处理（_ellipseHelper）**：
- 当扫描角度接近 360 度时，分为两个 180 度弧段绘制。因为 Skia 的 `arcToOval` 在尝试绘制完整 360 度时不会产生任何输出。

**旋转处理**：
- 如果有旋转角度（rotation != 0），先对路径应用逆旋转变换，绘制未旋转的椭圆弧，再应用正旋转变换。
- 无旋转时跳过变换步骤作为优化。

**不使用 addArc/addOval 的原因**：
注释明确指出不能使用 `addArc` 或 `addOval`，因为这些方法会自动闭合弧段，而 HTML Canvas 规范要求弧段保持开放（除非用户显式调用 `closePath()`）。

### 输入验证策略

所有路径函数共享一致的输入验证模式：

1. **`allAreFinite()` 检查**：如果任何参数为 NaN 或 Infinity，静默返回（不抛异常）
2. **负半径检查**：`arcTo` 和 `ellipse` 对负半径抛出异常 `'radii cannot be negative'`
3. **空路径自动 moveTo**：`arcTo`、`bezierCurveTo`、`lineTo`、`quadraticCurveTo` 在路径为空时，自动在第一个控制点/目标点处插入 `moveTo`

### closePath 的特殊行为

```javascript
function closePath(skpath) {
  if (skpath.isEmpty()) return;
  if (skpath.countPoints() != 1) {
    skpath.close();
  }
}
```

对于空路径或只有一个点的路径不执行 close 操作，这与浏览器行为一致。

### Path2D.addPath 的变换格式

`addPath` 接受 DOMMatrix 格式的变换对象 `{a, b, c, d, e, f}`，转换为 CanvasKit 的 3x3 矩阵格式 `[a, c, e, b, d, f]`（行主序）。未提供变换时默认使用单位矩阵。

### Path2D._getPath 的快照语义

`_getPath()` 调用 `this._path.snapshot()` 返回路径的不可变快照（CanvasKit.Path 类型）。每次调用都创建新的路径对象，调用者需在使用完毕后调用 `path.delete()` 释放内存。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| `CanvasKit.PathBuilder` | WASM 类 | 路径构建器，提供 moveTo/lineTo/cubicTo 等方法 |
| `CanvasKit.Path` | WASM 类 | 不可变路径对象（由 snapshot() 创建） |
| `CanvasKit.Path.MakeFromSVGString()` | WASM 静态方法 | SVG 路径字符串解析 |
| `CanvasKit.LTRBRect()` / `CanvasKit.XYWHRect()` | WASM 函数 | 矩形构造 |
| `CanvasKit.Matrix.rotated()` | WASM 函数 | 旋转矩阵构造 |
| `allAreFinite()` | util.js | 数值有限性验证 |
| `radiansToDegrees()` | util.js | 弧度到角度转换 |
| `almostEqual()` | util.js | 浮点数近似比较 |

**被依赖**：
- `canvas2dcontext.js` - 路径辅助函数被 CanvasRenderingContext2D 的同名方法调用
- `canvas2dcontext.js` - Path2D 对象可传给 fill()、stroke()、clip()、isPointInPath() 等方法

## 设计模式与设计决策

### 1. 函数提升 + 对象委托模式

路径操作被实现为独立的自由函数（而非某个类的方法），接受 PathBuilder 作为参数。Path2D 和 CanvasRenderingContext2D 都通过委托调用这些函数。这种设计：
- 避免了代码重复
- 保持了函数的可测试性
- 符合 Canvas 规范中 CanvasPath mixin 的概念（路径操作是共享接口）

### 2. 基于 Chromium 的实现参考

椭圆弧算法直接参考了 Chromium Blink 引擎的实现（代码注释中提供了 Chrome 源码链接），确保行为与主流浏览器一致。

### 3. 快照模式

`_getPath()` 返回路径快照而非引用，确保 Path2D 的内部状态不会被外部修改意外影响。代价是每次调用都创建新对象。

### 4. 防御性编程

每个路径函数都进行输入验证，非法输入（NaN、Infinity）被静默忽略而非抛出异常（负半径除外）。这与浏览器行为完全一致。

## 性能考量

- **360 度弧段分割**: 完整圆/椭圆被分为两个 180 度段绘制，引入一次额外的 `arcToOval` 调用。这是 Skia 底层限制的必要规避。

- **旋转椭圆的双重变换**: 带旋转的椭圆需要对整个路径做两次矩阵变换（先逆旋转再正旋转）。对于复杂路径，这可能成为性能热点。

- **allAreFinite 检查开销**: 每个路径函数调用都进行参数有效性检查。在高频调用场景中（如数千条线段），这些检查会累积为可测量的开销。

- **Path2D 快照成本**: `_getPath()` 每次调用都创建完整的路径副本。在频繁使用 Path2D 绘制的场景中（如将同一 Path2D 传给多次 `fill()`），每次都会产生路径复制和删除的开销。

- **SVG 路径解析**: `Path2D` 构造函数支持 SVG 路径字符串，解析工作由 WASM 层完成。复杂 SVG 路径的解析可能较慢，但通常只在构造时执行一次。

- **内存管理**: 通过 `_getPath()` 创建的路径快照需要调用者负责 `delete()`。如果遗漏，会导致 WASM 堆内存泄漏。Path2D 自身的 `_path`（PathBuilder）也需要在不再使用时清理。

## 相关文件

- `modules/canvaskit/htmlcanvas/canvas2dcontext.js` - 使用路径辅助函数和 Path2D 类
- `modules/canvaskit/htmlcanvas/util.js` - 提供 `allAreFinite()`、`radiansToDegrees()`、`almostEqual()` 等工具函数
- `modules/canvaskit/htmlcanvas/htmlcanvas.js` - 注册 Path2D 到 CanvasKit 命名空间
- `modules/canvaskit/htmlcanvas/preamble.js` - 作用域前导代码
- `modules/canvaskit/htmlcanvas/postamble.js` - 作用域闭合代码
