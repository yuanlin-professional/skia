# CanvasKit PathOps - 路径布尔运算绑定

> 源文件: `modules/canvaskit/pathops.js`

## 概述

pathops.js 为 CanvasKit 的 `Path` 类添加了路径布尔运算（Path Operations）功能。该文件提供了两个方法：`op()`（路径布尔运算）和 `simplify()`（路径简化），它们封装了 Skia 的 PathOps 模块的 C++ 实现，并提供了 JavaScript 友好的链式调用接口。

## 架构位置

该文件属于 CanvasKit 的可选功能模块，通过 `_extraInitializations` 机制注册。PathOps 是 Skia 中独立的模块，仅在构建时启用 pathops 功能时才包含。

```
用户代码
  └── pathops.js 公共 API
        ├── Path.prototype.op() → Path._op()
        └── Path.prototype.simplify() → Path._simplify()
              └── C++ Emscripten 绑定
                    └── Skia PathOps (C++)
```

## 主要类与结构体

本文件不定义新类，仅扩展 `CanvasKit.Path` 原型。

## 公共 API 函数

### `Path.prototype.op(otherPath, op)`
- **功能**：对当前路径和另一条路径执行布尔运算
- **参数**：
  - `otherPath`：另一条 Path 对象
  - `op`：布尔运算类型（`CanvasKit.PathOp.Difference`、`Intersect`、`Union`、`XOR`、`ReverseDifference`）
- **返回值**：成功时返回 `this`（支持链式调用），失败时返回 `null`
- **就地修改**：运算结果直接写入当前 Path 对象

### `Path.prototype.simplify()`
- **功能**：简化路径，移除自相交和多余的边
- **返回值**：成功时返回 `this`（支持链式调用），失败时返回 `null`
- **就地修改**：简化结果直接写入当前 Path 对象

## 内部实现细节

### 链式调用模式

两个方法均通过返回 `this` 支持链式调用：
```javascript
CanvasKit.Path.prototype.op = function(otherPath, op) {
    if (this._op(otherPath, op)) {
        return this;
    }
    return null;
};
```

C++ 底层方法（`_op`、`_simplify`）返回布尔值表示成功与否，JavaScript 层将其转换为对象/null 模式。

### 失败处理

返回 `null` 而非抛出异常，允许调用者优雅地处理退化情况（如自相交路径无法简化）。

## 依赖关系

- **C++ 绑定**：`Path._op()`、`Path._simplify()`
- **CanvasKit 运行时**：`_extraInitializations` 注册机制
- **Skia PathOps**：`src/pathops/` 目录下的 C++ 实现

## 设计模式与设计决策

1. **就地修改语义**：与 Skia C++ API 一致，布尔运算直接修改当前路径而非创建新对象，减少了对象分配。

2. **可空返回值**：使用 `this | null` 模式替代布尔返回值，支持链式调用的同时保留了错误检测能力。

3. **可选模块**：作为独立文件，仅在构建时包含 pathops 功能时才编译，减小了不需要此功能的构建体积。

## 性能考量

- PathOps 运算（尤其是 Union 和 XOR）对复杂路径可能较慢，属于计算密集型操作
- 就地修改避免了路径对象的拷贝和额外内存分配
- `simplify()` 可用于优化后续的路径渲染性能（减少边数）

## 相关文件

- `modules/canvaskit/externs.js` - Path.op / Path.simplify 外部声明
- `modules/canvaskit/canvaskit_bindings.cpp` - C++ PathOps 绑定
- `src/pathops/` - Skia PathOps 核心实现
- `include/pathops/SkPathOps.h` - PathOps C++ 公共 API
