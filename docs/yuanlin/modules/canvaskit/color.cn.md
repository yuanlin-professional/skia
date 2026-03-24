# CanvasKit 颜色处理模块 (color.js)

> 源文件: `modules/canvaskit/color.js`

## 概述

`color.js` 是 CanvasKit 中处理颜色创建、转换和解析的 JavaScript 模块。它提供了多种颜色构造方式（CSS rgba 格式、32 位整数格式、4 浮点数格式），定义了常用颜色常量（如 BLACK、WHITE、RED 等），以及 CSS 颜色字符串解析功能。所有颜色在内部统一表示为 `Float32Array` 的四个未预乘的 32 位浮点数 [r, g, b, a]，每个分量范围 [0.0, 1.0]。

## 架构位置

该文件是 CanvasKit JavaScript 辅助层的基础模块之一，被几乎所有涉及颜色操作的 JS 模块引用（如 `skottie.js`、`paragraph.js` 等），并通过 `memory.js` 的 `copyColorToWasm` 系列函数序列化到 WASM 堆传递给 C++ 端。

```
JavaScript 应用
  └── CanvasKit.Color() / Color4f() / parseColorString()  ← color.js
      └── memory.js: copyColorToWasm()
          └── C++ 端: SkColor4f / SkColor
```

## 主要类与结构体

该模块不定义类，颜色以 `Float32Array(4)` 表示。

### 颜色常量

通过 `Object.defineProperty` 以 getter 形式定义，每次访问返回新实例以防止被意外修改：

| 常量 | RGBA 值 |
|------|---------|
| `TRANSPARENT` | (0, 0, 0, 0) |
| `BLACK` | (0, 0, 0, 1) |
| `WHITE` | (1, 1, 1, 1) |
| `RED` | (1, 0, 0, 1) |
| `GREEN` | (0, 1, 0, 1) |
| `BLUE` | (0, 0, 1, 1) |
| `YELLOW` | (1, 1, 0, 1) |
| `CYAN` | (0, 1, 1, 1) |
| `MAGENTA` | (1, 0, 1, 1) |

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CanvasKit.Color(r, g, b, a)` | 从 CSS 风格的 rgba 值创建颜色（r,g,b: 0-255, a: 0.0-1.0） |
| `CanvasKit.ColorAsInt(r, g, b, a)` | 创建 32 位无符号整数颜色（各通道 0-255）|
| `CanvasKit.Color4f(r, g, b, a)` | 从 4 个 float 创建颜色（各通道 0.0-1.0） |
| `CanvasKit.getColorComponents(color)` | 将 Color4f 转换回 CSS 风格 [r(0-255), g(0-255), b(0-255), a(0-1)] |
| `CanvasKit.parseColorString(colorStr, colorMap)` | 解析 CSS 颜色字符串（支持 hex, rgb, rgba 格式） |
| `CanvasKit.multiplyByAlpha(color, alpha)` | 将颜色的 alpha 通道乘以指定值，返回新颜色 |

## 内部实现细节

### 颜色整数编码

`ColorAsInt` 将颜色编码为 32 位无符号整数，布局为 `AARRGGBB`（与 Skia C++ 的 SkColor 和 Flutter 一致）。使用 `& 0xFFFFFFF` 截断为 32 位，`>>> 0` 确保为无符号整数。

### CSS 颜色字符串解析

`parseColorString` 支持以下格式：

- **Hex 格式**: `#RGB`, `#RGBA`, `#RRGGBB`, `#RRGGBBAA`
  - 短格式通过乘以 17 展开（如 `e` -> `ee` = 14 -> 238）
  - 使用 `switch` 的 fall-through 特性处理有无 alpha 通道
- **rgb/rgba 函数**: `rgb(r, g, b)`, `rgba(r, g, b, a)`
  - alpha 支持数值和百分比格式
- **命名颜色**: 通过可选的 `colorMap` 字典查找
- **灰度/HSL**: 标记为 TODO，未实现

### 颜色类型检测

`isCanvasKitColor(ob)` 通过检查对象是否为长度 4 的 `Float32Array` 来判断是否为 CanvasKit 颜色。

### 颜色格式转换

- **`toUint32Color(c)`**: 从 Float32Array 颜色转换为 32 位整数（`AARRGGBB`）
- **`assureIntColors(arr)`**: 将各种颜色数组格式（Float32Array / Uint32Array / Array of Color4f）统一转换为 Uint32Array
- **`uIntColorToCanvasKitColor(c)`**: 从 32 位整数还原为 Float32Array 颜色

### clamp 函数

`clamp(c)` 将值约束在 [0, 255] 范围内，并四舍五入到整数。处理 `undefined`/`NaN` 时默认为 0。

### valueOrPercent

解析 CSS alpha 值时，支持纯数值和百分比两种格式（如 `0.5` 或 `50%`）。未定义时默认为 1（不透明）。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `CanvasKit` 全局对象 | 挂载颜色 API |
| `Debug` 函数 | 未识别颜色时输出警告 |
| `wasMalloced` | 用于 `assureIntColors` 检测内存来源 |

## 设计模式与设计决策

- **Float32Array 内部表示**: 选择 `Float32Array(4)` 而非普通数组，与 Skia C++ 端的 `SkColor4f`（四个 float）直接对应，可直接通过 `HEAPF32` 拷贝到 WASM 堆
- **防御性常量**: 颜色常量使用 `Object.defineProperty` getter，每次访问返回新实例，防止 `CanvasKit.BLACK[0] = 1` 这类意外修改
- **CSS 兼容 API**: `Color(r, g, b, a)` 接受 CSS 风格的 0-255 范围值，降低 Web 开发者的使用门槛
- **渐进式精度**: 提供 `Color`（整数精度）和 `Color4f`（浮点精度）两种构造方式，适应不同精度需求
- **宽松的解析器**: `parseColorString` 对无法识别的颜色返回 BLACK 并输出警告，而非抛出异常
- **纯函数设计**: `multiplyByAlpha` 返回新颜色副本，不修改输入

## 性能考量

- `Float32Array.of(r, g, b, a)` 是颜色创建的最快路径，直接分配固定大小的 TypedArray
- 颜色常量通过 getter 每次创建新对象，高频访问场景下应缓存到局部变量
- `toUint32Color` 和 `assureIntColors` 涉及浮点到整数的批量转换，对大量颜色可能产生一定开销
- `parseColorString` 使用字符串操作和 `parseInt`，相比直接构造颜色有额外开销，适合初始化时使用
- `clamp` 内部调用 `Math.round`、`Math.max`、`Math.min`，已被现代 JS 引擎高度优化

## 相关文件

- `modules/canvaskit/memory.js` — `copyColorToWasm`, `copyColorFromWasm` 等颜色序列化函数
- `modules/canvaskit/canvaskit_bindings.cpp` — C++ 端颜色处理（`ptrToSkColor4f`）
- `include/core/SkColor.h` — Skia 原生颜色类型定义
- `modules/canvaskit/htmlcanvas/color.js` — Canvas2D 兼容层的颜色映射表
