# CanvasKit 内存管理模块 (memory.js)

> 源文件: `modules/canvaskit/memory.js`

## 概述

`memory.js` 是 CanvasKit 中负责 JavaScript 与 WebAssembly 堆内存之间数据传输的核心工具模块。它提供了内存分配（`Malloc`/`Free`）、数组拷贝（`copy1dArray`）、矩阵转换（`copy3x3MatrixToWasm`/`copy4x4MatrixToWasm`）以及颜色、矩形等常用类型在 JS/WASM 边界的序列化和反序列化功能。该模块是 CanvasKit 所有 JS-to-C++ 数据传输的基础设施层。

## 架构位置

该文件是 CanvasKit JavaScript 层的底层基础设施，几乎所有 JS 端的绑定辅助代码（如 `paragraph.js`、`skottie.js`、`webgl.js`）都依赖它来完成数据到 WASM 堆的搬运。

```
JavaScript 应用代码
  └── CanvasKit JS 辅助层 (paragraph.js, skottie.js, etc.)
      └── memory.js  ← 内存管理与数据序列化
          └── Emscripten WASM 堆 (HEAPU8, HEAPF32, HEAP32, etc.)
              └── C++ Skia 绑定
```

## 主要类与结构体

### MallocObj（由 `CanvasKit.Malloc` 返回）

一个轻量级对象，封装了 WASM 堆上分配的内存块：

| 属性/方法 | 类型 | 说明 |
|----------|------|------|
| `_ck` | `boolean` | 标记为 CanvasKit 分配的内存 |
| `length` | `number` | 元素数量 |
| `byteOffset` | `number` | WASM 堆中的指针偏移 |
| `subarray(start, end)` | `function` | 返回子数组视图 |
| `toTypedArray()` | `function` | 返回指向同一内存的 TypedArray 视图 |

### Scratch 变量

模块定义了一系列"草稿"（scratch）内存缓冲区，在启动时预分配，用于高频临时数据传输以避免反复分配：

- `_scratch3x3Matrix` / `_scratch4x4Matrix` — 矩阵临时缓冲区
- `_scratchColor` — 颜色临时缓冲区
- `_scratchFourFloatsA/B` — 4 浮点数缓冲区（用于 Rect 等）
- `_scratchThreeFloatsA/B` — 3 浮点数缓冲区
- `_scratchIRect` / `_scratchRRect` / `_scratchRRect2` — 矩形/圆角矩形缓冲区

## 公共 API 函数

### 内存分配

| 函数 | 说明 |
|------|------|
| `CanvasKit.Malloc(typedArray, len)` | 在 WASM 堆上分配 `len` 个指定类型元素的内存，返回 MallocObj |
| `CanvasKit.Free(mallocObj)` | 释放由 Malloc 分配的内存 |

### 内部拷贝函数

| 函数 | 说明 |
|------|------|
| `copy1dArray(arr, dest, ptr)` | 将 JS 数组拷贝到 WASM 堆指定类型视图中 |
| `copyFlexibleColorArray(colors)` | 拷贝颜色数组（支持 Float32Array / Uint32Array / Array of Float32Arrays） |
| `copyColorArray(arr)` | 将 SkColor4f 数组拷贝到 WASM 堆 |
| `copy3x3MatrixToWasm(matr)` | 将 3x3 矩阵/DOMMatrix 拷贝到 scratch 指针 |
| `copy4x4MatrixToWasm(matr)` | 将 4x4 矩阵/DOMMatrix 拷贝到 scratch 指针 |
| `copy4x4MatrixFromWasm(matrPtr)` | 从 WASM 堆读取 4x4 矩阵到 JS 数组 |
| `copyColorToWasm(color4f, ptr)` | 拷贝 SkColor4f 到 WASM 堆 |
| `copyColorComponentsToWasm(r, g, b, a)` | 以四个分量拷贝颜色 |
| `copyColorToWasmNoScratch(color4f)` | 拷贝颜色（分配新内存，需调用方释放） |
| `copyColorFromWasm(colorPtr)` | 从 WASM 堆读取颜色到 JS Float32Array |
| `copyRectToWasm(fourFloats, ptr)` | 拷贝 SkRect 到 WASM 堆 |
| `copyIRectToWasm(fourInts, ptr)` | 拷贝 SkIRect 到 WASM 堆 |
| `copyIRectFromWasm(rectMalloc, outputArray)` | 从 WASM 堆读取 SkIRect |
| `copyRRectToWasm(twelveFloats, ptr)` | 拷贝 SkRRect 到 WASM 堆 |

## 内部实现细节

### Malloc/Free 机制

`Malloc` 通过 `CanvasKit._malloc` 在 WASM 堆上分配原始字节，并返回一个包装对象。该对象延迟创建 TypedArray 视图（通过 `toTypedArray()`），并缓存视图以避免重复创建。关键细节：

- 当 WASM 堆增长时，之前的 TypedArray 视图会失效（`length` 变为 0），`toTypedArray()` 会检测并重新创建
- `_ck` 标记用于区分用户通过 `Malloc` 分配的内存和内部临时分配的内存
- `Free` 不仅释放内存，还将 `toTypedArray` 和 `typedArray` 设为 null 以帮助垃圾回收

### copy1dArray 的指针算术

WASM 堆是一个 `uint8_t*` 缓冲区。不同的 TypedArray 视图（如 `HEAPF32`）以不同宽度索引同一缓冲区。当写入时，需要将字节指针转换为对应类型的索引：`ptr / bytesPerElement`。

### 矩阵格式自动转换

`copy3x3MatrixToWasm` 和 `copy4x4MatrixToWasm` 支持多种输入格式：

- **长度 6 的数组**: 3x2 仿射矩阵，自动补充默认透视行 `[0, 0, 1]`
- **长度 9 的数组**: 完整 3x3 矩阵
- **长度 16 的数组**: 4x4 矩阵（3x3 模式下会降采样，4x4 模式下直接拷贝）
- **DOMMatrix 对象**: 通过 `m11`, `m21` 等属性读取（注意 DOMMatrix 是列优先的）

`copy4x4MatrixToWasm` 在将 3x3 矩阵升级为 4x4 时，会先用 0 填充整个矩阵，然后设置对应位置的值并将 `[2,2]` 设为 1。

### scratch 指针的生命周期

scratch 指针在启动时分配，永不释放，生命周期与 WASM 实例相同。使用 scratch 的函数返回的指针不应被外部释放。`freeArraysThatAreNotMallocedByUsers` 函数用于在 C++ 调用完成后有条件地释放非用户分配的内存。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `CanvasKit._malloc` / `CanvasKit._free` | Emscripten 底层内存分配 |
| `CanvasKit.HEAPU8` / `HEAPF32` / `HEAP32` 等 | Emscripten 堆内存视图 |
| `CanvasKit.ColorType` | 颜色类型常量（用于 `copyFlexibleColorArray`） |
| `wasMalloced()` / `nullptr` | 内部标识和空指针常量 |

## 设计模式与设计决策

- **Scratch 缓冲区模式**: 预分配一组固定大小的临时缓冲区，避免高频操作中反复 malloc/free。这是 JS-WASM 互操作中常见的性能优化手段
- **延迟视图创建**: `toTypedArray()` 延迟创建 TypedArray 并缓存，同时处理堆增长导致的视图失效
- **`_ck` 标记**: 通过在对象/数组上附加 `_ck` 属性来区分内存来源，实现零拷贝传递（用户 Malloc 的数据直接返回指针，无需再次拷贝）
- **多格式兼容**: 矩阵拷贝函数支持 DOMMatrix、普通数组和 TypedArray，以及 3x2/3x3/4x4 不同尺寸的自动转换
- **不可变 scratch 指针**: 调用方不应释放 scratch 指针，简化了内存管理责任

## 性能考量

- **Scratch 缓冲区消除频繁分配**: 矩阵、颜色、矩形等高频传输数据使用预分配的 scratch 指针，每次调用只需一次 `set` 操作
- **零拷贝优化**: 通过 `_ck` 标记检测 Malloc 分配的数据，直接返回指针偏移而非拷贝
- **堆增长感知**: `toTypedArray()` 检查 TypedArray 是否因堆增长而失效，确保引用最新的内存视图
- **指针算术而非对象封装**: 所有数据以原始指针和偏移量传递，避免对象创建和垃圾回收压力
- **颜色数组的灵活处理**: `copyFlexibleColorArray` 根据输入类型选择最优路径（Float32Array 直接拷贝 vs Uint32Array 作为 RGBA_8888）

## 相关文件

- `modules/canvaskit/matrix.js` — 矩阵创建和运算（产生传入 memory.js 的矩阵数据）
- `modules/canvaskit/color.js` — 颜色创建（产生传入 memory.js 的颜色数据）
- `modules/canvaskit/canvaskit_bindings.cpp` — 消费 WASM 堆中数据的 C++ 绑定
- `modules/canvaskit/WasmCommon.h` — C++ 端的 WASM 指针类型定义
