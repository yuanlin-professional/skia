# CanvasKit Util - 通用辅助工具函数

> 源文件: `modules/canvaskit/util.js`

## 概述

util.js 提供了 CanvasKit WebAssembly 模块中使用的通用辅助工具函数和常量。该文件定义了角度转换函数（弧度/度数互转）和浮点数近似相等比较函数，以及 Emscripten 兼容的 `nullptr` 常量。这些工具在 CanvasKit 的各个 JavaScript 绑定文件中被广泛使用。

## 架构位置

该文件属于 CanvasKit JavaScript 绑定的基础设施层，在编译时直接包含到 CanvasKit 的捆绑输出中。它不使用 `_extraInitializations` 注册机制，而是作为全局作用域中的立即可用代码。

```
CanvasKit 捆绑输出
  ├── preamble.js (入口作用域开始)
  ├── util.js ← 本文件（全局工具）
  ├── interface.js
  ├── cpu.js / webgl.js
  └── postamble.js (作用域结束)
```

## 主要类与结构体

本文件不定义类，仅提供独立函数和常量。

## 公共 API 函数

### `nullptr`
```javascript
var nullptr = 0;
```
- **功能**：Emscripten 兼容的空指针常量
- **说明**：Emscripten 不接受 JavaScript 的 `null` 作为 `uintptr_t` 参数，因此使用数值 0 代替

### `radiansToDegrees(rad)`
```javascript
function radiansToDegrees(rad) {
    return (rad / Math.PI) * 180;
}
```
- **功能**：将弧度转换为角度

### `degreesToRadians(deg)`
```javascript
function degreesToRadians(deg) {
    return (deg / 180) * Math.PI;
}
```
- **功能**：将角度转换为弧度

### `almostEqual(floata, floatb)`
```javascript
function almostEqual(floata, floatb) {
    return Math.abs(floata - floatb) < 0.00001;
}
```
- **功能**：判断两个浮点数是否近似相等
- **精度**：使用 epsilon = 0.00001（1e-5）

## 内部实现细节

### nullptr 的必要性

Emscripten 的 C++ 绑定期望数值类型的指针参数。JavaScript 的 `null` 在传递给接受 `uintptr_t` 的 C++ 函数时会导致类型错误。使用 `var nullptr = 0` 解决了这个跨语言类型兼容性问题。

### 浮点比较精度

`almostEqual` 使用绝对误差比较（epsilon = 1e-5），适用于 CanvasKit 中常见的坐标和颜色值比较。对于极大或极小的数值，可能需要相对误差比较，但在图形渲染的典型值域内该精度已足够。

## 依赖关系

- **JavaScript 标准库**：`Math.PI`、`Math.abs`
- 无外部依赖

## 设计模式与设计决策

1. **全局工具函数**：作为非模块化的全局函数定义，利用 CanvasKit 的 preamble/postamble 作用域封装避免全局污染。

2. **Emscripten 适配**：`nullptr = 0` 是对 Emscripten 类型系统限制的务实解决方案。

3. **简洁实现**：每个函数都是单行实现，优先考虑可读性和内联优化。

## 性能考量

- 所有函数均为纯数学运算，没有内存分配或 WASM 调用开销
- 现代 JavaScript 引擎会对这类简单函数进行内联优化
- `almostEqual` 使用简单的绝对差值比较，比使用 `Number.EPSILON` 的 ULP 比较更快

## 相关文件

- `modules/canvaskit/preamble.js` - 作用域入口
- `modules/canvaskit/interface.js` - 使用这些工具函数的主要接口文件
- `modules/canvaskit/cpu.js` - CPU 后端中使用 nullptr
- `modules/canvaskit/font.js` - 字体接口中使用 nullptr
