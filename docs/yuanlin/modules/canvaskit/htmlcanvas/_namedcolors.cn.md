# _namedcolors.js - CSS 命名颜色预计算脚本

> 源文件: `modules/canvaskit/htmlcanvas/_namedcolors.js`

## 概述

`_namedcolors.js` 是一个 Node.js 辅助脚本，用于预计算 CSS 规范中定义的全部 148 个命名颜色（Named Colors）。该脚本通过调用 CanvasKit 的 `CanvasKit.Color()` 函数，将每个 CSS 命名颜色的 RGB 值转换为 CanvasKit 内部使用的颜色表示格式（Float32Array），并将结果以 JSON 格式输出到控制台。其输出用于填充 `color.js` 中的 `colorMap` 字典，避免在运行时重复计算这些颜色值。

该脚本本身不在浏览器中运行，它是一个构建时/开发时的工具脚本，只需在颜色定义发生变化时运行一次。

## 架构位置

```
CanvasKit (WASM)
└── htmlcanvas 兼容层
    ├── color.js          ← 使用本脚本的输出结果 (colorMap)
    ├── _namedcolors.js   ← 本文件 (预计算工具)
    └── canvas2dcontext.js
```

本脚本位于 CanvasKit 的 HTML Canvas 兼容层中，属于颜色处理子系统的构建辅助工具。它是 `color.js` 的上游依赖——`color.js` 中硬编码的 `colorMap` 数据来自本脚本的输出。

## 主要类与结构体

本文件没有定义类或结构体。核心数据结构是一个 JavaScript 对象字面量 `colorMap`：

- **`colorMap`**: 一个键值对字典，键为 CSS 颜色名称字符串（如 `'aliceblue'`、`'red'`），值为 `CanvasKit.Color(r, g, b)` 的调用结果。包含 148 个标准 CSS 命名颜色加上 `transparent` 共 149 个条目。颜色名称全部为小写形式，符合 CSS 规范要求。

## 公共 API 函数

本文件不导出任何公共 API。它是一个一次性运行的 Node.js 脚本。

**运行方式**：
```bash
node ./htmlcanvas/_namedcolors.js --expose-wasm
```

运行后，脚本将 `colorMap` 序列化为 JSON 并输出到标准输出（`console.log(JSON.stringify(colorMap))`）。开发者需将输出结果手动复制到 `color.js` 中。

## 内部实现细节

1. **CanvasKit 初始化**: 脚本首先通过 `require` 加载本地编译好的 CanvasKit WASM 模块（路径为 `../canvaskit/bin/canvaskit.js`），并使用 `locateFile` 回调指定 WASM 二进制文件的位置。

2. **颜色映射构建**: 在 CanvasKit 初始化完成的 Promise 回调中，创建一个包含所有 CSS 命名颜色的字典。每个颜色通过 `CanvasKit.Color(r, g, b)` 构造，其中 RGB 值来自 CSS Color Level 4 规范（`https://drafts.csswg.org/css-color/#named-colors`）。

3. **特殊颜色**: 包含 `transparent`（`CanvasKit.Color(0, 0, 0, 0)`），这是唯一一个指定了 alpha 值为 0 的颜色。

4. **灰色变体**: 对于英式和美式拼写均提供了对应条目（如 `gray`/`grey`、`darkgray`/`darkgrey`），确保两种拼写都可以被正确解析。

5. **JSON 序列化**: 最终通过 `JSON.stringify` 将 CanvasKit 颜色对象序列化。CanvasKit.Color 返回的是 Float32Array，JSON.stringify 后会变成浮点数值数组，这正是 `color.js` 中 `Float32Array.of(...)` 所需的数据格式。

## 依赖关系

| 依赖项 | 类型 | 说明 |
|--------|------|------|
| `canvaskit.js` (WASM 模块) | 运行时依赖 | 提供 `CanvasKit.Color()` 函数用于颜色值计算 |
| Node.js | 环境依赖 | 脚本通过 Node.js 运行 |
| CSS Color Level 4 规范 | 规范依赖 | 颜色名称和 RGB 值的权威来源 |

**被依赖**：
- `color.js` 使用本脚本的输出作为 `colorMap` 的初始数据

## 设计模式与设计决策

1. **预计算模式（Pre-computation）**: 这是本文件最核心的设计决策。由于 JavaScript/Closure Compiler 没有类似 C++ `constexpr` 的编译期求值机制，脚本选择在构建阶段预先计算所有命名颜色的值，而非在运行时动态计算。注释中明确说明了这一点：*"JS/closure doesn't have a constexpr like thing"*。

2. **离线计算 + 手动迁移**: 脚本的输出需要人工复制到 `color.js`，而不是通过自动化构建管道。注释指出 *"This should likely never need to be re-run"*，因为 CSS 命名颜色集合是标准化的且极少变动。

3. **规范一致性**: 颜色定义严格遵循 W3C CSS Color Level 4 草案规范，确保 CanvasKit 的 HTML Canvas 兼容层能正确解析浏览器标准中的命名颜色。

## 性能考量

- **启动时间优化**: 预计算颜色值避免了在 CanvasKit 模块初始化时调用 149 次 `CanvasKit.Color()` 的开销。虽然单次调用代价极低，但在资源受限的环境（如移动端 WebAssembly）中，消除不必要的初始化工作仍有意义。

- **代码体积优化**: 直接使用 `Float32Array.of(...)` 字面量比在运行时引入 CanvasKit.Color 调用逻辑更利于 Closure Compiler 的代码压缩和 tree-shaking。

- **内存效率**: 颜色值存储为 `Float32Array`（每个颜色 4 个 32 位浮点数 = 16 字节），整个 colorMap 约占 149 * 16 = 2384 字节，开销非常小。

## 相关文件

- `modules/canvaskit/htmlcanvas/color.js` - 使用本脚本输出的 colorMap，提供颜色解析和序列化功能
- `modules/canvaskit/htmlcanvas/canvas2dcontext.js` - 通过 `parseColor()` 间接使用 colorMap
- `modules/canvaskit/htmlcanvas/lineargradient.js` - 渐变中的颜色停靠点使用 `parseColor()`
- `modules/canvaskit/htmlcanvas/radialgradient.js` - 径向渐变中的颜色停靠点使用 `parseColor()`
