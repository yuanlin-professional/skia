# GrSimpleMesh

> 源文件: [src/gpu/ganesh/GrSimpleMesh.h](../../../../src/gpu/ganesh/GrSimpleMesh.h)

## 概述

`GrSimpleMesh` 是 Skia Ganesh GPU 渲染管线中用于描述简单（非实例化、直接绘制）网格数据的结构体。它作为 `GrOp`（GPU 操作）和 `GrOpsRenderPass`（渲染通道）之间的通信桥梁，封装了顶点缓冲区、索引缓冲区以及相关绘制参数。该结构体支持三种绘制模式：纯顶点绘制、索引绘制和基于模式的索引绘制。

## 架构位置

`GrSimpleMesh` 位于 Ganesh GPU 后端的渲染管线中间层：

```
GrOp (GPU 操作)
  |
  v
GrSimpleMesh (网格数据描述)
  |
  v
GrOpsRenderPass (渲染通道，提交 GPU 绘制命令)
  |
  v
GPU 驱动层 (OpenGL / Vulkan / Metal / D3D)
```

各种 Op 类（如 `TextureOp`、`StrokeRectOp`、`RegionOp`、`ShadowRRectOp` 等）在准备绘制时构造 `GrSimpleMesh` 实例，然后将其传递给渲染通道进行实际的 GPU 绘制调用。

## 主要类与结构体

### `GrSimpleMesh`

一个 POD 风格的结构体，持有一次简单绘制调用所需的全部数据。

**成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fIndexBuffer` | `sk_sp<const GrBuffer>` | 索引缓冲区（仅索引绘制模式使用） |
| `fIndexCount` | `int` | 索引数量 |
| `fPatternRepeatCount` | `int` | 模式重复次数（仅模式绘制使用） |
| `fMaxPatternRepetitionsInIndexBuffer` | `int` | 索引缓冲区中最大模式重复次数 |
| `fBaseIndex` | `int` | 索引缓冲区起始偏移 |
| `fMinIndexValue` | `uint16_t` | 最小索引值 |
| `fMaxIndexValue` | `uint16_t` | 最大索引值 |
| `fPrimitiveRestart` | `GrPrimitiveRestart` | 是否启用图元重启，默认 `kNo` |
| `fVertexBuffer` | `sk_sp<const GrBuffer>` | 顶点缓冲区 |
| `fVertexCount` | `int` | 顶点数量（或模式模式下每次模式的顶点数） |
| `fBaseVertex` | `int` | 顶点缓冲区起始偏移，默认为 0 |
| `fIsInitialized` | `bool`（仅 Debug） | 调试模式下标记是否已正确初始化 |

## 公共 API 函数

### `void set(sk_sp<const GrBuffer> vertexBuffer, int vertexCount, int baseVertex)`

设置纯顶点绘制模式。清空索引缓冲区，仅使用顶点缓冲区进行绘制。

- **参数：**
  - `vertexBuffer`：顶点缓冲区智能指针
  - `vertexCount`：顶点数量
  - `baseVertex`：起始顶点偏移（必须 >= 0）

### `void setIndexed(sk_sp<const GrBuffer> indexBuffer, int indexCount, int baseIndex, uint16_t minIndexValue, uint16_t maxIndexValue, GrPrimitiveRestart, sk_sp<const GrBuffer> vertexBuffer, int baseVertex)`

设置索引绘制模式。同时使用索引缓冲区和顶点缓冲区。

- **参数：**
  - `indexBuffer`：索引缓冲区（不可为空）
  - `indexCount`：索引数量（必须 >= 1）
  - `baseIndex`：索引缓冲区起始偏移（必须 >= 0）
  - `minIndexValue` / `maxIndexValue`：索引值范围（max 必须 >= min）
  - `primitiveRestart`：是否启用图元重启
  - `vertexBuffer`：顶点缓冲区
  - `baseVertex`：起始顶点偏移（必须 >= 0）

### `void setIndexedPatterned(sk_sp<const GrBuffer> indexBuffer, int indexCount, int patternRepeatCount, int maxPatternRepetitionsInIndexBuffer, sk_sp<const GrBuffer> vertexBuffer, int patternVertexCount, int baseVertex)`

设置基于模式的索引绘制。适用于需要重复相同索引模式的场景（例如绘制大量相同形状的四边形）。

- **参数：**
  - `indexBuffer`：索引缓冲区（不可为空）
  - `indexCount`：每个模式的索引数量（必须 >= 1）
  - `patternRepeatCount`：模式重复次数（必须 >= 1）
  - `maxPatternRepetitionsInIndexBuffer`：索引缓冲区内的最大重复容量（必须 >= 1）
  - `vertexBuffer`：顶点缓冲区
  - `patternVertexCount`：每个模式的顶点数量（必须 >= 1）
  - `baseVertex`：起始顶点偏移（必须 >= 0）

## 内部实现细节

1. **内联实现**：所有三个 `set` 方法均以 `inline` 方式实现在头文件中，避免函数调用开销，因为这些方法在渲染热路径上被频繁调用。

2. **所有权管理**：缓冲区通过 `sk_sp`（Skia 智能指针）管理，使用 `std::move` 语义转移所有权，避免不必要的引用计数操作。

3. **模式绘制的特殊处理**：`setIndexedPatterned` 方法将 `fVertexCount` 复用为 `patternVertexCount`，同时强制关闭 `GrPrimitiveRestart`（设为 `kNo`），因为模式绘制不支持图元重启。

4. **调试断言**：每个 `set` 方法都包含丰富的 `SkASSERT` 检查，确保参数合法性。`fIsInitialized` 标志仅在 Debug 构建中存在，用于追踪未初始化使用的问题。

5. **`fPatternRepeatCount` 的双重含义**：在 `setIndexed` 中被设为 0，用于区分普通索引绘制和模式索引绘制。

## 依赖关系

- **`include/core/SkRefCnt.h`**：提供 `sk_sp` 智能指针
- **`include/private/base/SkAssert.h`**：提供 `SkASSERT` 断言宏
- **`include/private/base/SkDebug.h`**：提供 `SkDEBUGCODE` 宏
- **`include/private/gpu/ganesh/GrTypesPriv.h`**：提供 `GrPrimitiveRestart` 枚举
- **`src/gpu/ganesh/GrBuffer.h`**：提供 `GrBuffer` 基类

## 设计模式与设计决策

1. **数据传输对象 (DTO) 模式**：`GrSimpleMesh` 是一个纯粹的数据结构，没有复杂的逻辑，仅用于在 Op 和渲染通道之间传递绘制参数。

2. **三种绘制模式的统一表示**：通过单一结构体和三个不同的 `set` 方法，将三种绘制模式（纯顶点、索引、模式索引）统一到同一数据结构中，简化了渲染通道的接口。

3. **关于 TODO 注释**：源码中的 TODO 提到考虑让每个 Op 直接在 `GrOpsRenderPass` 上发出绘制调用，这意味着 `GrSimpleMesh` 可能在未来被重构或移除。

## 性能考量

- **内联函数**：所有 `set` 方法均为内联，消除函数调用开销。
- **移动语义**：缓冲区使用 `std::move` 转移，避免引用计数的原子操作。
- **轻量结构**：该结构体不包含虚函数表，没有继承层次，内存布局紧凑。
- **Debug-only 开销**：`fIsInitialized` 标志仅在 Debug 构建中存在，Release 构建无额外开销。

## 相关文件

- `src/gpu/ganesh/GrBuffer.h`：GPU 缓冲区基类定义
- `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h`：基于 `GrSimpleMesh` 的绘制操作辅助类
- `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.cpp`：辅助类实现
- `src/gpu/ganesh/ops/TextureOp.cpp`：纹理操作中使用 `GrSimpleMesh`
- `src/gpu/ganesh/ops/StrokeRectOp.cpp`：矩形描边操作中使用 `GrSimpleMesh`
- `src/gpu/ganesh/ops/RegionOp.cpp`：区域绘制操作中使用 `GrSimpleMesh`
- `include/private/gpu/ganesh/GrTypesPriv.h`：Ganesh 私有类型定义
