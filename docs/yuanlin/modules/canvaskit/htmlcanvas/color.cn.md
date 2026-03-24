# color.js - CSS 颜色解析与序列化

> 源文件: `modules/canvaskit/htmlcanvas/color.js`

## 概述

`color.js` 是 CanvasKit HTML Canvas 兼容层的颜色处理模块，负责 CSS 颜色字符串与 CanvasKit 内部颜色表示（Float32Array）之间的双向转换。该文件包含三个主要部分：

1. **预计算的 CSS 命名颜色映射表**（`colorMap`）：包含 149 个 CSS 标准命名颜色的 Float32Array 表示
2. **颜色序列化函数**（`colorToString`）：将 CanvasKit 颜色转为 CSS 颜色字符串
3. **颜色解析函数**（`parseColor`）：将 CSS 颜色字符串解析为 CanvasKit 颜色

这些功能被 `CanvasRenderingContext2D` 的 fillStyle、strokeStyle、shadowColor 等属性的 getter/setter 广泛使用。

## 架构位置

```
Canvas 2D API 属性 (fillStyle, strokeStyle, shadowColor 等)
    │
    ▼
color.js
├── parseColor(str)      ← 字符串 → CanvasKit 颜色 (set 时调用)
├── colorToString(color)  ← CanvasKit 颜色 → 字符串 (get 时调用)
└── colorMap              ← 命名颜色查找表
    │
    ▼
CanvasKit.parseColorString()  ← 底层颜色解析引擎
CanvasKit.getColorComponents() ← 底层颜色分量提取
```

本模块是颜色子系统的核心，位于 Canvas 2D 上下文与 CanvasKit WASM 引擎之间。所有需要处理 CSS 颜色字符串的模块（包括渐变的 `addColorStop`）都依赖本文件提供的函数。

## 主要类与结构体

### `colorMap` - 命名颜色映射表

一个 JavaScript 对象字典（标注为 `@dict` 以供 Closure Compiler 优化），包含 149 个 CSS 命名颜色条目。

**数据格式**：
```javascript
{
  'colorname': Float32Array.of(r, g, b, a),
  // r, g, b, a 为 0.0-1.0 范围的浮点数
}
```

**特殊条目**：
- `'transparent'`: `Float32Array.of(0.000, 0.000, 0.000, 0.000)` - 唯一 alpha 为 0 的颜色
- 灰色双拼写：`'gray'`/`'grey'`、`'darkgray'`/`'darkgrey'` 等（共 8 对英式/美式拼写）

**数据来源**：该映射表的数据由 `_namedcolors.js` 脚本预计算生成，颜色值来自 CSS Color Level 4 规范。

## 公共 API 函数

### `colorToString(skcolor)` - 颜色序列化

```javascript
function colorToString(skcolor) -> string
```

将 CanvasKit 内部颜色表示转换为符合 W3C 规范的 CSS 颜色字符串。

**参数**：
- `skcolor`: CanvasKit 颜色对象（Float32Array 格式）

**返回值**：
- 当 alpha 为 1.0 时：返回 6 位十六进制字符串，如 `'#ff0000'`
- 当 alpha 不为 1.0 时：返回 rgba 函数表示，如 `'rgba(255, 0, 0, 0.50000000)'`

**实现细节**：
1. 通过 `CanvasKit.getColorComponents()` 提取 RGBA 分量（0-255 整数）
2. 对于不透明颜色：将 RGB 分量转为小写十六进制，单字符补零（如 `'a'` → `'0a'`）
3. 对于半透明颜色：alpha 为 0 或 1 时保持整数，否则保留 8 位小数精度

**规范引用**：遵循 [HTML Canvas 颜色序列化规范](https://html.spec.whatwg.org/multipage/canvas.html#serialisation-of-a-color)。

### `parseColor(colorStr)` - 颜色解析

```javascript
function parseColor(colorStr) -> CanvasKitColor
```

将 CSS 颜色字符串解析为 CanvasKit 内部颜色表示。

**参数**：
- `colorStr` (string): CSS 颜色字符串，支持命名颜色、十六进制、rgb/rgba 等格式

**返回值**：
- CanvasKit 颜色对象（Float32Array 格式）

**实现**：直接委托给 `CanvasKit.parseColorString(colorStr, colorMap)`，将 `colorMap` 作为命名颜色查找表传入。实际的字符串解析逻辑由 CanvasKit WASM 模块内部的 C++ 代码处理。

### 测试接口

```javascript
CanvasKit._testing['parseColor'] = parseColor;
CanvasKit._testing['colorToString'] = colorToString;
```

两个函数均注册到 `CanvasKit._testing` 命名空间，供单元测试直接调用。

## 内部实现细节

### 颜色值的浮点表示

CanvasKit 使用 Float32Array 存储颜色，分量范围为 0.0-1.0（而非传统的 0-255 整数）。`colorMap` 中的值已预转换为此格式，精度保留到小数点后 3 位（如 `0.941`），足以表示 8 位色深的所有值。

### colorToString 的序列化策略

序列化采用两种格式的选择逻辑：

```
if alpha === 1.0:
    → '#rrggbb' (十六进制，无 alpha)
else:
    → 'rgba(r, g, b, a)' (函数表示，含 alpha)
```

这与浏览器行为一致：完全不透明的颜色用更紧凑的十六进制表示，半透明颜色用 rgba() 表示。

### alpha 精度处理

对于半透明颜色，alpha 值的精度处理有特殊逻辑：
- `a === 0` 或 `a === 1`：保持整数形式（`'rgba(0, 0, 0, 0)'`）
- 其他值：使用 `toFixed(8)` 保留 8 位小数（`'rgba(255, 0, 0, 0.50000000)'`）

8 位小数精度确保在颜色值往返转换（parse → serialize → parse）时不会丢失精度。

### `@dict` 注解

`colorMap` 上方的 `/* @dict */` 注解告知 Closure Compiler 该对象的属性名不应被重命名（混淆），因为颜色名称是运行时通过字符串键查找的。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| `CanvasKit.getColorComponents()` | WASM 函数 | 从颜色对象中提取 RGBA 分量 |
| `CanvasKit.parseColorString()` | WASM 函数 | 解析 CSS 颜色字符串（包括 hex、rgb、hsl 等） |
| `_namedcolors.js` | 构建工具 | 生成 colorMap 数据（离线依赖） |

**被依赖**：
- `canvas2dcontext.js` - fillStyle/strokeStyle/shadowColor 的 get/set
- `radialgradient.js` - `addColorStop()` 中解析颜色字符串
- `lineargradient.js` - `addColorStop()` 中解析颜色字符串

## 设计模式与设计决策

### 1. 预计算查找表模式

所有 149 个命名颜色在模块加载时已经以 Float32Array 形式存在，无需运行时计算。这是典型的空间换时间策略——牺牲约 2.4KB 的代码/内存空间，换取命名颜色查找的 O(1) 时间复杂度。

### 2. 解析委托给 WASM

`parseColor()` 几乎不包含 JavaScript 端的解析逻辑，而是将全部工作委托给 `CanvasKit.parseColorString()`。这样做的好处：
- 利用 C++ 的高效字符串解析能力
- 避免在 JS 层重复实现复杂的 CSS 颜色语法解析（hex3/hex4/hex6/hex8、rgb/rgba、hsl/hsla 等）
- 只需在 JS 层维护命名颜色表（因为这是纯数据，放在 JS 层更方便管理和预计算）

### 3. 规范严格一致性

`colorToString` 的输出格式严格遵循 W3C 规范的序列化要求：
- 十六进制使用小写字母
- 不透明颜色用 `#rrggbb` 而非 `#RRGGBB` 或 `rgb()`
- alpha 值的精度处理确保往返一致性

### 4. 测试可观察性

通过 `CanvasKit._testing` 暴露内部函数的做法，使单元测试可以直接验证颜色解析和序列化逻辑，而无需通过 Canvas 2D 上下文间接测试。

## 性能考量

- **命名颜色查找**: JavaScript 对象属性查找的平均时间复杂度为 O(1)，149 个条目不会有哈希冲突问题。

- **Float32Array 创建**: `colorMap` 中的每个颜色值在模块加载时通过 `Float32Array.of()` 创建一次，后续查找只返回引用。但注意这些 Float32Array 是共享的，如果调用者修改了返回值，会影响全局映射表。

- **序列化开销**: `colorToString()` 每次调用都需要跨 WASM 边界调用 `getColorComponents()` 并进行字符串拼接。在频繁读取 `fillStyle`/`strokeStyle` 的场景中，可以考虑缓存序列化结果。

- **解析开销**: `parseColor()` 的每次调用都涉及 WASM 函数调用。对于重复解析相同颜色字符串的场景（如动画循环中反复设置同一颜色），没有缓存机制。

- **内存占用**: colorMap 包含 149 个 Float32Array（每个 16 字节）加上字符串键，总计约 5-6KB（含字符串和对象开销）。

## 相关文件

- `modules/canvaskit/htmlcanvas/_namedcolors.js` - 生成 colorMap 数据的预计算脚本
- `modules/canvaskit/htmlcanvas/canvas2dcontext.js` - 使用 parseColor/colorToString 处理颜色属性
- `modules/canvaskit/htmlcanvas/lineargradient.js` - addColorStop 中使用 parseColor
- `modules/canvaskit/htmlcanvas/radialgradient.js` - addColorStop 中使用 parseColor
- `modules/canvaskit/htmlcanvas/htmlcanvas.js` - 主入口文件
