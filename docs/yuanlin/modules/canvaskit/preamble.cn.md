# CanvasKit Preamble - 模块作用域入口

> 源文件: `modules/canvaskit/preamble.js`

## 概述

preamble.js 是 CanvasKit WebAssembly 模块的 JavaScript 作用域入口文件。它通过 IIFE（立即执行函数表达式）开启一个闭合作用域，将后续所有 CanvasKit JavaScript 源文件包裹在同一作用域中，避免全局命名空间污染。该文件与 `postamble.js` 配对使用，分别作为作用域的开始和结束。

## 架构位置

该文件是 CanvasKit 构建输出的第一个 JavaScript 文件，所有后续源文件在编译时按顺序拼接。

```
CanvasKit 构建输出 (canvaskit.js)
  ├── preamble.js ← 本文件（作用域开始）
  │     (function(CanvasKit) {
  ├── util.js
  ├── interface.js
  ├── cpu.js / webgl.js / webgpu.js
  ├── font.js
  ├── rt_shader.js
  ├── pathops.js
  ├── ... 其他 JS 文件
  └── postamble.js（作用域结束）
        }(Module));
```

## 主要类与结构体

本文件不定义任何类或结构体。

## 公共 API 函数

本文件不定义任何函数。

## 内部实现细节

### IIFE 作用域封装

文件内容仅为 IIFE 的开始部分：
```javascript
(function(CanvasKit) {
```

此模式的关键设计：
1. **参数传递**：`CanvasKit` 参数在 `postamble.js` 中绑定到 Emscripten 的 `Module` 对象
2. **作用域隔离**：所有内部函数（如 `copy1dArray`、辅助工具等）对外不可见
3. **单一入口**：`CanvasKit` 成为此作用域内所有代码访问模块功能的唯一入口点

### "故意悬空"注释

```javascript
// This intentionally dangles because we want all the
// JS code to be in the same scope
```

文件的开括号故意不闭合——闭合在 `postamble.js` 中完成。这是一种构建时文件拼接的技巧，替代了 JavaScript 缺少的原生命名空间支持。

### 与 Module 的关系

在 Emscripten 生成的 WASM 胶水代码中，`Module` 是全局的 WASM 模块对象。通过将其作为参数传入 IIFE，CanvasKit 的所有扩展（方法、类、常量）都直接挂载到 `Module` 上，使得最终的 `CanvasKit` 对象就是增强后的 `Module`。

## 依赖关系

- **Emscripten**：`Module` 全局对象
- **构建系统**：依赖文件按正确顺序拼接

## 设计模式与设计决策

1. **IIFE 模块模式**：JavaScript 传统的模块化方案（ES modules 之前），通过函数作用域实现封装。选择此方案是因为 Emscripten 输出不使用 ES module 格式。

2. **文件拼接构建**：将多个 JS 文件拼接为一个捆绑文件，比使用模块加载器更简单，且与 Emscripten 的输出流程兼容。

3. **命名约定**：preamble/postamble（前言/后语）的命名明确表达了这两个文件的配对关系和作用域角色。

## 性能考量

- 该文件仅包含一行代码，无运行时开销
- IIFE 不会产生闭包性能问题，因为整个 CanvasKit 模块生命周期内只创建一次

## 相关文件

- `modules/canvaskit/postamble.js` - 作用域结束配对文件
- `modules/canvaskit/compile.sh` - 构建脚本（控制文件拼接顺序）
- `modules/canvaskit/cpu.js` - CPU 后端（在此作用域内运行）
- `modules/canvaskit/interface.js` - 核心接口（在此作用域内运行）
