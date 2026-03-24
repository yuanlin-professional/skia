# postamble.js

> 源文件: modules/canvaskit/postamble.js

## 概述

`postamble.js` 是 CanvasKit 模块的后置脚本,用于关闭在 `preamble.js` 中打开的作用域。这是一个极简的文件,只包含一行闭包结束代码,作为 Emscripten 编译过程中代码包装的一部分。

该文件与 `preamble.js` 配对使用,共同构成 CanvasKit 模块的代码封装边界,防止全局命名空间污染,同时将 Module 对象暴露为 CanvasKit 的实际内容。

## 架构位置

```
skia/
├── modules/
│   └── canvaskit/
│       ├── preamble.js        # 前置脚本 - 打开作用域
│       ├── postamble.js       # 本文件 - 关闭作用域
│       ├── canvaskit.js       # Emscripten 生成的核心代码
│       ├── canvas.js          # Canvas API 扩展
│       ├── surface.js         # Surface API 扩展
│       └── compile.sh         # 编译脚本
```

在编译过程中,文件组织顺序为:
```
preamble.js
  → Emscripten 生成代码
  → 各种功能扩展模块
  → postamble.js
```

## 主要类与结构体

本文件不包含类或结构体定义,仅包含作用域闭合代码。

## 公共 API 函数

本文件不提供公共 API,仅负责代码结构。

## 内部实现细节

### 作用域闭合

```javascript
}(Module)); // When this file is loaded in, the high level object is "Module";
```

**解释**:
- `}`: 闭合在 `preamble.js` 中开始的立即执行函数表达式(IIFE)
- `(Module)`: 将 `Module` 对象作为参数传递给 IIFE
- 注释说明在文件加载时,顶层对象是 `Module`

### 与 preamble.js 的配对

**preamble.js** 的开头:
```javascript
(function(CanvasKit){
  // CanvasKit 模块代码
```

**postamble.js** 的结尾:
```javascript
}(Module)); // 关闭作用域,传入 Module
```

**效果**: 整个 CanvasKit 代码被包装在一个函数作用域内,`Module` 对象在内部被视为 `CanvasKit`。

### Emscripten 集成

Emscripten 允许通过 `--pre-js` 和 `--post-js` 标志指定前置和后置脚本:

```bash
emcc ... \
  --pre-js preamble.js \
  --post-js postamble.js \
  -o canvaskit.js
```

**编译结果**:
```javascript
// preamble.js 内容
(function(CanvasKit){
  // Emscripten 生成的代码
  var Module = { ... };
  // 其他扩展代码
// postamble.js 内容
}(Module));
```

## 依赖关系

### 前置依赖

**preamble.js**: 必须在编译链中先于本文件执行,否则会产生语法错误(不匹配的闭括号)。

### 后续使用

**用户代码**: 加载 canvaskit.js 后,可以访问全局的 CanvasKit 对象:
```javascript
<script src="canvaskit.js"></script>
<script>
  CanvasKit.init().then((CK) => {
    // 使用 CanvasKit API
  });
</script>
```

### Module 对象

**Emscripten 的 Module**: Emscripten 默认创建名为 `Module` 的全局对象,包含 WebAssembly 实例和所有导出的函数。

**重命名为 CanvasKit**: 通过 IIFE 参数,`Module` 在函数内部被重命名为 `CanvasKit`,提供更友好的 API 名称。

## 设计模式与设计决策

### 立即执行函数表达式(IIFE)模式

```javascript
(function(CanvasKit){
  // 代码
}(Module));
```

**优点**:
1. **命名空间隔离**: 避免全局变量污染
2. **变量私有化**: 内部变量不会泄露到全局
3. **参数重命名**: 将 `Module` 重命名为 `CanvasKit`
4. **模块封装**: 只暴露需要的 API

### 约定优于配置

文件名 `postamble` 清晰表明其用途,与 `preamble` 对应,无需额外文档即可理解。

### 分离关注点

- **preamble.js**: 负责作用域开始和初始化
- **Emscripten 生成代码**: 核心功能
- **扩展模块**: 功能增强
- **postamble.js**: 负责作用域关闭

每个文件职责单一,易于维护。

### 防御性编程

注释明确指出 `Module` 对象的来源,帮助理解代码执行上下文。

## 性能考量

### 代码体积

**最小化**: 仅两行代码,对最终代码包体积几乎无影响(约 60 字节)。

### 执行性能

**零开销**: 闭包在解析时创建,运行时无额外开销。现代 JavaScript 引擎会优化 IIFE。

### 压缩友好

该代码模式对代码压缩工具非常友好:
- 参数名可以被缩短
- 注释会被移除
- 不会影响压缩效率

**压缩后**:
```javascript
}(Module));
```
甚至可能与前面的代码合并到一行。

### 最佳实践

1. **保持配对**: 确保 preamble 和 postamble 始终配对使用
2. **不要修改**: 除非理解整个模块系统,否则不要修改此文件
3. **检查编译**: 编译后验证代码结构完整性

## 相关文件

### 配对文件
- `modules/canvaskit/preamble.js` - 前置脚本,打开作用域

### 类似的 postamble 文件
- `modules/canvaskit/htmlcanvas/postamble.js` - HTMLCanvas 模块的后置脚本
- 其他子模块的 postamble 文件

### 编译相关
- `modules/canvaskit/compile.sh` - 编译脚本,指定 pre-js 和 post-js
- `modules/canvaskit/BUILD.bazel` - Bazel 构建规则

### Emscripten 文档
- Emscripten `--pre-js` 和 `--post-js` 选项文档
- Module 对象自定义文档

### 模块系统
- `modules/canvaskit/canvaskit.js` - 最终编译产物
- Emscripten 生成的核心代码
