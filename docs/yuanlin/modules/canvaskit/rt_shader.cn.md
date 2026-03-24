# CanvasKit RuntimeEffect Shader - 运行时着色器绑定

> 源文件: `modules/canvaskit/rt_shader.js`

## 概述

rt_shader.js 为 CanvasKit 的 `RuntimeEffect` 类提供 JavaScript 层的高级绑定。它封装了 SkSL（Skia Shading Language）运行时着色器和混合器（Blender）的创建、uniform 设置和子着色器管理功能。该文件是 JavaScript 应用与 Skia 运行时着色器引擎之间的桥梁，处理了 JavaScript 类型数组到 WASM 堆内存的转换。

## 架构位置

该文件属于 CanvasKit 的 JavaScript 绑定层，通过 `_extraInitializations` 机制在初始化时注入。它依赖 C++ 绑定层提供的私有方法（以 `_` 前缀），并对外暴露用户友好的公共 API。

```
用户代码 (JavaScript)
  └── rt_shader.js 公共 API
        ├── RuntimeEffect.Make() → _Make()
        ├── RuntimeEffect.MakeForBlender() → _MakeForBlender()
        ├── makeShader() → _makeShader()
        ├── makeShaderWithChildren() → _makeShaderWithChildren()
        └── makeBlender() → _makeBlender()
              └── C++ Emscripten 绑定
                    └── SkRuntimeEffect (Skia C++)
```

## 主要类与结构体

本文件不定义新类，而是扩展已有的 `CanvasKit.RuntimeEffect` 原型。

## 公共 API 函数

### `CanvasKit.RuntimeEffect.Make(sksl, errorCallback)`
- **功能**：从 SkSL 源码编译运行时着色器效果
- **参数**：
  - `sksl`：SkSL 着色器源代码字符串
  - `errorCallback`：可选的错误回调函数，接收错误信息字符串
- **实现**：将回调封装为 `{onError: fn}` 对象传入 C++（Emscripten `val` 兼容）
- **默认行为**：未提供回调时使用 `console.log` 输出错误

### `CanvasKit.RuntimeEffect.MakeForBlender(sksl, errorCallback)`
- **功能**：从 SkSL 源码编译运行时混合器效果
- **实现**：与 `Make()` 结构相同，调用 `_MakeForBlender`

### `RuntimeEffect.prototype.makeShader(floats, localMatrix)`
- **功能**：从 uniform 值和可选局部矩阵创建着色器
- **参数**：
  - `floats`：Float32Array 或 MallocObj 的 uniform 值数组
  - `localMatrix`：可选的 3x3 变换矩阵
- **内存管理**：检查 `floats['_ck']` 判断是否为 Malloc 分配的内存，决定着色器是否拥有 uniform 数据的所有权
- **大小计算**：`floats.length * 4` 将浮点数计数转换为字节数

### `RuntimeEffect.prototype.makeShaderWithChildren(floats, childrenShaders, localMatrix)`
- **功能**：创建带有子着色器的运行时着色器
- **参数**：
  - `childrenShaders`：其他着色器数组（如 `Image.makeShader()` 的结果）
- **实现细节**：
  - 提取每个子着色器的 Emscripten 内部原始指针（`$$.ptr`）
  - 将指针数组拷贝到 WASM 堆（`HEAPU32`）
  - 传递指针数组和长度到 C++ 层，C++ 会重新包装为 `sk_sp`

### `RuntimeEffect.prototype.makeBlender(floats)`
- **功能**：从 uniform 值创建混合器
- **参数**：与 `makeShader` 的 `floats` 参数相同

## 内部实现细节

### JavaScript 到 WASM 内存转换

所有函数均通过 `copy1dArray` 辅助函数将 JavaScript 类型数组拷贝到 WASM 堆：
```javascript
var fptr = copy1dArray(floats, 'HEAPF32');  // uniform 浮点值
var childrenPointers = copy1dArray(barePointers, 'HEAPU32');  // 子着色器指针
```

### Malloc 内存所有权

通过 `!floats['_ck']` 检测 uniform 数据的来源：
- 普通 JavaScript 数组：着色器获取数据所有权（`shouldOwnUniforms = true`），着色器释放时会释放内存
- MallocObj（由 `CanvasKit.Malloc` 分配）：着色器不获取所有权（`shouldOwnUniforms = false`），用户负责释放

### 局部矩阵处理

`copy3x3MatrixToWasm(localMatrix)` 将 JavaScript 数组形式的 3x3 矩阵拷贝到 WASM 堆，返回指针。

## 依赖关系

- **CanvasKit 内部**：`copy1dArray()`、`copy3x3MatrixToWasm()`（定义在其他 JS 文件中）
- **C++ 绑定**：`RuntimeEffect._Make`、`_MakeForBlender`、`_makeShader`、`_makeShaderWithChildren`、`_makeBlender`
- **Emscripten**：`val` 类型系统、WASM 堆内存（`HEAPF32`、`HEAPU32`）

## 设计模式与设计决策

1. **回调对象封装**：将 JavaScript 函数封装为对象 `{onError: fn}` 传入 C++，这是 Emscripten `val` 绑定的惯用模式。

2. **所有权语义**：通过 `_ck` 属性区分 Malloc 和普通数组，确保内存管理的正确性。

3. **原始指针提取**：对子着色器使用 `$$.ptr` 提取 Emscripten 智能指针的底层原始指针，这是跨越 JS-WASM 边界传递对象引用的标准做法。

4. **字节计数转换**：`floats.length * 4` 在 JavaScript 侧完成浮点到字节的转换，匹配 C++ 侧期望的字节长度参数。

## 性能考量

- 每次创建着色器都会触发 WASM 堆内存拷贝（uniform 值和矩阵）
- MallocObj 模式避免了重复拷贝，适用于频繁更新 uniform 的场景
- 子着色器指针数组的拷贝开销极小（仅 4 字节/指针）
- SkSL 编译（`Make`）是一次性开销，后续创建着色器仅需设置 uniform

## 相关文件

- `modules/canvaskit/externs.js` - RuntimeEffect 外部声明
- `modules/canvaskit/interface.js` - CanvasKit 通用 JavaScript 接口
- `include/effects/SkRuntimeEffect.h` - Skia C++ RuntimeEffect API
- `modules/canvaskit/canvaskit_bindings.cpp` - C++ Emscripten 绑定
