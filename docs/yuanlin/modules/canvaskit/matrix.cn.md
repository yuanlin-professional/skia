# CanvasKit 矩阵运算模块 (matrix.js)

> 源文件: `modules/canvaskit/matrix.js`

## 概述

`matrix.js` 是 CanvasKit 中纯 JavaScript 实现的矩阵运算库，提供 3x3 矩阵（`CanvasKit.Matrix`）、4x4 矩阵（`CanvasKit.M44`）、向量运算（`CanvasKit.Vector`）以及颜色矩阵（`CanvasKit.ColorMatrix`）的创建和操作功能。该模块将 Skia C++ 中 `SkMatrix`、`SkM44` 和 `SkColorMatrix` 的核心功能移植到 JavaScript 端，以减少 JS 与 C++ 之间频繁跨层调用带来的复杂性和性能开销。

## 架构位置

该文件位于 CanvasKit 的 JavaScript 辅助层，在 WASM 模块加载前运行。矩阵对象以普通 JavaScript 数组（行优先排列）表示，可直接传入 CanvasKit 的 C++ 绑定方法中（由 `memory.js` 中的 `copy3x3MatrixToWasm` / `copy4x4MatrixToWasm` 负责拷贝到 WASM 堆）。

```
JavaScript 应用
  └── CanvasKit.Matrix / M44 / Vector / ColorMatrix  ← matrix.js
      └── memory.js（矩阵序列化到 WASM 堆）
          └── C++ CanvasKit 绑定（SkMatrix / SkM44）
```

## 主要类与结构体

### CanvasKit.Matrix（3x3 矩阵）

以长度为 9 的 JavaScript 数组表示，行优先排列。用于 2D 仿射变换（平移、缩放、旋转、倾斜）及透视变换。

### CanvasKit.M44（4x4 矩阵）

以长度为 16 的 JavaScript 数组表示，行优先排列。用于 3D 变换，包括透视投影、相机设置和空间旋转。

### CanvasKit.Vector（向量运算）

支持任意长度的向量操作，包括点积、叉积、归一化、加减法等。

### CanvasKit.ColorMatrix（颜色矩阵）

以长度为 20 的 `Float32Array` 表示，由 4x4 颜色变换矩阵和 1x4 平移向量组成。用于颜色滤镜操作。

## 公共 API 函数

### CanvasKit.Matrix

| 函数 | 说明 |
|------|------|
| `identity()` | 返回 3x3 单位矩阵 |
| `invert(m)` | 返回矩阵 m 的逆矩阵，不可逆时返回 null |
| `mapPoints(matrix, ptArr)` | 使用矩阵变换点数组（原地修改） |
| `multiply(...)` | 接受任意数量 3x3 矩阵参数，从左到右相乘 |
| `rotated(radians, px, py)` | 创建绕点 (px, py) 旋转 radians 弧度的矩阵 |
| `scaled(sx, sy, px, py)` | 创建以 (px, py) 为中心的缩放矩阵 |
| `skewed(kx, ky, px, py)` | 创建以 (px, py) 为中心的倾斜矩阵 |
| `translated(dx, dy)` | 创建平移矩阵 |

### CanvasKit.M44

| 函数 | 说明 |
|------|------|
| `identity()` | 返回 4x4 单位矩阵 |
| `translated(vec)` | 创建 3D 平移矩阵 |
| `scaled(vec)` | 创建 3D 缩放矩阵 |
| `rotated(axisVec, radians)` | 创建绕任意轴旋转的矩阵 |
| `rotatedUnitSinCos(axisVec, sinAngle, cosAngle)` | 使用 sin/cos 值创建旋转矩阵（避免重复三角运算） |
| `lookat(eyeVec, centerVec, upVec)` | 创建视图矩阵（相机朝向） |
| `perspective(near, far, angle)` | 创建透视投影矩阵 |
| `rc(m, r, c)` | 获取矩阵第 r 行第 c 列的元素 |
| `multiply(...)` | 接受任意数量 4x4 矩阵参数，从左到右相乘 |
| `invert(m)` | 返回 4x4 矩阵的逆矩阵 |
| `transpose(m)` | 返回转置矩阵 |
| `mustInvert(m)` | 求逆矩阵，不可逆时抛出异常 |
| `setupCamera(area, zscale, cam)` | 根据相机参数构建完整的 3D 视角矩阵 |

### CanvasKit.Vector

| 函数 | 说明 |
|------|------|
| `dot(a, b)` | 计算向量点积 |
| `lengthSquared(v)` | 计算向量长度的平方 |
| `length(v)` | 计算向量长度 |
| `mulScalar(v, s)` | 向量标量乘法 |
| `add(a, b)` / `sub(a, b)` | 向量加法/减法 |
| `dist(a, b)` | 计算两向量之间的距离 |
| `normalize(v)` | 向量归一化 |
| `cross(a, b)` | 计算三维向量叉积 |

### CanvasKit.ColorMatrix

| 函数 | 说明 |
|------|------|
| `identity()` | 返回单位颜色矩阵 |
| `scaled(rs, gs, bs, as)` | 创建各通道缩放的颜色矩阵 |
| `rotated(axis, sine, cosine)` | 创建颜色空间旋转矩阵（axis: 0=R, 1=G, 2=B） |
| `postTranslate(m, dr, dg, db, da)` | 为颜色矩阵添加后平移量 |
| `concat(outer, inner)` | 连接两个颜色矩阵（outer * inner） |

## 内部实现细节

### 核心辅助函数

- **`sdot(...)`**: 接受偶数个标量参数，计算成对乘积之和，用于矩阵元素构造
- **`identityN(n)`**: 生成 n x n 单位矩阵（扁平数组形式）
- **`stride(v, m, width, offset, colStride)`**: 紧凑的数组写入函数，将向量按对角线/偏移模式写入矩阵。例如 `stride([sx, sy], identity, 3, 0, 1)` 可设置对角线上的缩放因子
- **`multiply(m1, m2, size)`**: 通用方阵乘法，支持任意大小
- **`multiplyMany(size, listOfMatrices)`**: 将多个矩阵从左到右依次相乘

### 3x3 矩阵逆运算

使用 Sarrus 规则计算行列式，通过伴随矩阵除以行列式得到逆矩阵。行列式为 0 时返回 null。

### 4x4 矩阵逆运算

从 `SkM44.cpp` 移植，使用余因子展开法。注意代码中元素索引假设行优先存储（对应 C++ 的列优先做了转换）。包含对 NaN 和 Infinity 的安全检查。

### 颜色矩阵布局

20 个浮点数的布局为 4x5 矩阵：前 4 列为 4x4 颜色变换矩阵，第 5 列为各通道的后平移量。索引常量 `rScale=0, gScale=6, bScale=12, aScale=18` 对应对角线位置。

### Debug 模式检查

多处使用 `IsDebug` 标志进行参数校验（数组长度、NaN 检查），Release 构建中这些检查会被 Closure Compiler 优化移除。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `CanvasKit` 全局对象 | 挂载所有矩阵操作的命名空间 |
| `IsDebug` / `Debug` | 编译时常量，控制调试检查是否启用 |
| `memory.js` | 将 JS 矩阵数组拷贝到 WASM 堆内存 |

## 设计模式与设计决策

- **纯 JS 实现而非 C++ 绑定**: 注释明确指出，矩阵运算在 JS 端实现是为了"节省在 C++ 和 JS 层之间来回传递的复杂性和开销"。这是一个有意识的性能权衡
- **数组而非对象**: 矩阵以扁平数组表示而非封装对象，与 CanvasKit C++ 绑定的预期输入格式一致，避免序列化开销
- **未使用 DOMMatrix**: 注释说明考虑过 DOMMatrix 但因兼容性不足（需要 polyfill）和缺少 `mapPoints()` 等功能而放弃
- **行优先存储**: 3x3 和 4x4 矩阵均采用行优先排列，与 Skia C++ 端保持一致
- **函数式 API**: 大多数操作返回新矩阵，保持不可变性（`mapPoints` 是例外，原地修改以提高性能）
- **stride 函数的巧妙设计**: 通过 offset 和 colStride 参数，单一函数可表达对角线赋值、列赋值等多种模式，大幅简化了各变换矩阵的构建代码

## 性能考量

- 矩阵运算全在 JS 端完成，避免了 JS-WASM 边界的序列化和函数调用开销
- `mapPoints` 使用原地修改避免分配新数组
- `ColorMatrix` 使用 `Float32Array` 而非普通 Array，利用 TypedArray 的内存布局优势
- 通用 `multiply` 函数使用三重循环，对 3x3/4x4 小矩阵而言效率可接受
- `multiplyMany` 支持多矩阵链式乘法，减少中间临时变量
- Debug 模式下的 NaN/长度检查在 Release 构建中被完全移除，不影响生产性能

## 相关文件

- `modules/canvaskit/memory.js` — 矩阵到 WASM 堆的拷贝逻辑（`copy3x3MatrixToWasm`, `copy4x4MatrixToWasm`）
- `modules/canvaskit/canvaskit_bindings.cpp` — C++ 端使用这些矩阵的绑定
- `include/core/SkMatrix.h` — Skia 原生 3x3 矩阵类
- `include/core/SkM44.h` — Skia 原生 4x4 矩阵类
- `src/core/SkM44.cpp` — 4x4 逆矩阵算法的 C++ 原始实现
