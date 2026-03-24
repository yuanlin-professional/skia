# CanvasKit Release 构建配置 (release.js)

> 源文件: `modules/canvaskit/release.js`

## 概述

`release.js` 是 CanvasKit 的发布（Release）构建配置文件，仅包含 5 行代码。它定义了 `Debug` 函数为空函数体和 `IsDebug` 常量为 `false`，使得 Google Closure Compiler 能够在编译时识别并移除所有调试相关的代码路径，从而减小最终 WASM 包的体积并略微提升运行时性能。该文件虽然极其简短，但其影响范围覆盖整个 CanvasKit JavaScript 层，是构建系统中 Debug/Release 模式切换的关键枢纽。

## 架构位置

该文件与 `debug.js`（调试构建）互斥，在编译时由构建系统选择其中之一链接到最终产物中。它影响 CanvasKit JS 层中所有使用 `Debug()` 和 `IsDebug` 的代码。

```
构建系统
  ├── release.js  ← 发布构建时包含（Debug = 空, IsDebug = false）
  └── debug.js    ← 调试构建时包含（Debug = console.warn, IsDebug = true）
      └── 被 matrix.js, memory.js 等文件中的 Debug/IsDebug 引用
```

## 主要类与结构体

无。

## 公共 API 函数

| 函数/常量 | 值 | 说明 |
|----------|-----|------|
| `Debug(msg)` | 空函数 | Closure Compiler 会优化移除所有对此函数的调用及其参数字符串 |
| `IsDebug` | `false` | 编译时常量，Closure Compiler 会消除所有 `if (IsDebug)` 分支中的死代码 |

## 内部实现细节

### 源代码内容

文件仅包含以下 5 行代码：

```javascript
function Debug(msg) {
  // by leaving this blank, closure optimizes out calls (and the messages)
  // which trims down code size and marginally improves runtime speed.
}
/** @const */ var IsDebug = false;
```

### Debug 函数的空函数体机制

`Debug` 函数体故意留空。Closure Compiler 在高级优化模式（ADVANCED_OPTIMIZATIONS）下的行为：
1. 检测到 `Debug` 函数体为空（无副作用）
2. 内联该函数到所有调用点
3. 由于函数体为空，调用点的参数表达式（通常是字符串拼接）也被识别为无副作用
4. 整个调用语句（包括参数构造）被完全移除

例如，`Debug('Warning, uninvertible matrix')` 在 Release 构建中会被完全消除，不仅删除了函数调用，连字符串字面量也不会出现在最终输出中。

### IsDebug 常量的死代码消除

`IsDebug` 使用 `/** @const */` JSDoc 注解标记为常量。Closure Compiler 的处理流程：
1. 将 `IsDebug` 内联为字面值 `false`
2. 所有 `if (IsDebug)` 条件求值为 `if (false)`
3. 整个 `if` 分支体被识别为不可达代码
4. 不可达代码被完全剔除

这意味着在 `matrix.js`、`memory.js` 等文件中类似如下的参数校验代码：

```javascript
if (IsDebug && (ptArr.length % 2)) {
    throw 'mapPoints requires an even length arr';
}
```

在 Release 构建中会被完全消除，不产生任何运行时开销。

## 依赖关系

无外部依赖。该文件被 CanvasKit JS 层的所有文件隐式依赖。

## 设计模式与设计决策

- **编译时条件编译**: 通过在 Release/Debug 构建中替换不同的文件实现条件编译，类似 C++ 的 `#ifdef NDEBUG`
- **Closure Compiler 协作**: 利用 `@const` 注解和空函数体，让 Closure Compiler 的死代码消除发挥最大效果
- **零运行时开销**: Release 构建中所有调试代码完全消失，不留任何条件检查痕迹

## 性能考量

- 空 `Debug` 函数允许 Closure Compiler 移除所有调试日志的字符串构造和函数调用
- `IsDebug = false` 使所有 `if (IsDebug)` 守卫的参数校验代码被完全剔除
- 对最终产物大小和运行时性能均有正面影响

## 相关文件

- `modules/canvaskit/debug.js` — 调试构建版本，`Debug` 函数实现为 `console.warn`，`IsDebug` 设为 `true`
- `modules/canvaskit/matrix.js` — 大量使用 `IsDebug` 进行矩阵参数校验（NaN 检查、维度检查等）
- `modules/canvaskit/memory.js` — 使用 `Debug` 输出内存操作警告信息
- `modules/canvaskit/color.js` — 使用 `Debug` 报告无法识别的颜色字符串
- `modules/canvaskit/webgl.js` — 使用 `Debug` 报告 GPU 回退和纹理操作警告
- `modules/canvaskit/skottie.js` — 间接依赖（通过 memory.js 的辅助函数）
- `modules/canvaskit/paragraph.js` — 使用 `Debug` 报告字体加载失败
- CanvasKit 构建系统（GN/Bazel） — 负责选择 `release.js` 或 `debug.js` 参与编译
