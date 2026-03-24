# VerticesRenderStep

> 源文件: `src/gpu/graphite/render/VerticesRenderStep.h`, `src/gpu/graphite/render/VerticesRenderStep.cpp`

## 概述

`VerticesRenderStep` 是 Skia Graphite 中用于渲染 `SkVertices` 网格数据的 `RenderStep` 实现。它支持三角形和三角形带两种图元类型，以及顶点颜色和纹理坐标的可选组合，共产生 8 种变体。该渲染步骤广泛用于自定义网格绘制以及 Android 平台的阴影效果。

## 架构位置

- **上层**: 由 `RendererProvider` 创建，存储在 `fVertices[8]` 数组中
- **基类**: 继承自 `RenderStep`
- **用途**: 处理 `DrawTypeFlags::kDrawVertices` 和 `DrawTypeFlags::kDropShadows`（特定变体）

## 主要类与结构体

### `VerticesRenderStep` 类

继承自 `RenderStep`，通过构造参数组合出 8 种变体：
- **图元类型**: `kTriangles` 或 `kTriangleStrip`
- **顶点颜色**: 有或无
- **纹理坐标**: 有或无

**标志**: `kPerformsShading | kAppendVertices`，有颜色时追加 `kEmitsPrimitiveColor`

**Uniform 变量**:
| 名称 | 类型 | 描述 |
|------|------|------|
| `localToDevice` | `float4x4` | 变换矩阵（顶点在 GPU 上变换） |
| `depth` | `float` | 深度值（避免逐顶点复制） |

**深度/模板设置**: `kDirectDepthLEqualPass`

### 属性组合

根据颜色和纹理坐标的有无，使用 4 种不同的属性布局：

| 变体 | 属性 |
|------|------|
| 仅位置 | `position`, `ssboIndex` |
| 有颜色 | `position`, `vertColor`, `ssboIndex` |
| 有纹理坐标 | `position`, `texCoords`, `ssboIndex` |
| 颜色+纹理坐标 | `position`, `vertColor`, `texCoords`, `ssboIndex` |

颜色属性使用 `kUByte4_norm` 格式（归一化的 4 字节），纹理坐标使用 `kFloat2`。

### Varying

仅在有颜色时定义 `color`（`kHalf4`）varying。

## 公共 API 函数

- **`VerticesRenderStep(Layout, PrimitiveType, bool hasColor, bool hasTexCoords)`** — 构造函数
- **`vertexSkSL()`** — 根据颜色和纹理坐标的配置生成对应的顶点着色器代码
- **`fragmentColorSkSL()`** — 在有颜色时输出 `primitiveColor = color`
- **`writeVertices(DrawWriter*, DrawParams&, uint32_t)`** — 将 SkVertices 数据写入 GPU 缓冲区
- **`writeUniformsAndTextures(DrawParams&, PipelineDataGatherer*)`** — 写入变换矩阵和深度值

## 内部实现细节

### 变体 ID 分配

`variant_id()` 函数根据图元类型、颜色和纹理坐标组合返回唯一的 `RenderStepID`，总共定义了 8 个 ID（`kVertices_Tris` 到 `kVertices_TristripsColorTexCoords`）。

### 顶点写入

`writeVertices()` 从 `SkVerticesPriv` 提取位置、颜色、纹理坐标和索引数据：
- 使用 `VertState` 和 `VertState::Proc` 遍历顶点，自动处理三角形、三角形带和三角形扇（扇形在上层已转换为三角形）
- 通过 `VertexWriter::If()` 条件写入可选的颜色和纹理坐标数据
- 颜色数据从 BGRA 格式转换为预乘 alpha 格式：`half4(vertColor.bgr * vertColor.a, vertColor.a)`

### 顶点着色器变体

4 种着色器变体处理不同的属性组合：
- 有颜色时执行 BGRA→预乘 RGBA 转换
- 有纹理坐标时使用 `texCoords` 作为 `stepLocalCoords`
- 无纹理坐标时使用 `position` 作为 `stepLocalCoords`

### 深度处理

深度值通过 uniform 传递而非逐顶点属性，因为同一绘制调用的所有顶点共享相同的深度值。在顶点着色器中设置 `devPosition.z = depth`。

## 依赖关系

- `SkVertices` / `SkVerticesPriv` — 顶点数据源
- `VertState` — 顶点遍历状态机，处理索引和图元类型
- `DrawWriter` — GPU 缓冲区写入
- `PipelineDataGatherer` — uniform 数据收集

## 设计模式与设计决策

### 编译时变体

通过布尔参数的组合在构造时确定变体，避免运行时分支。每种组合对应固定的属性布局和着色器代码。

### 条件属性写入

使用 `VertexWriter::If()` 在写入顶点数据时条件性地包含颜色和纹理坐标，避免了为每种变体编写独立的写入代码。

### 扇形转换

`SkVertices::kTriangleFan_VertexMode` 在到达 VerticesRenderStep 之前已被转换为 `kTriangles`，因此该步骤不需要处理扇形图元。

## 性能考量

- **GPU 变换**: 顶点变换在 GPU 上执行，减少 CPU 开销
- **深度 uniform**: 每个绘制调用只写入一次深度值，而非逐顶点
- **索引复用**: 当有索引缓冲区时，通过 VertState 机制正确处理索引重用
- **预留缓冲**: 根据索引/顶点数量预留 GPU 缓冲空间，减少重分配

## 相关文件

- `include/core/SkVertices.h` — SkVertices 公共接口
- `src/core/SkVerticesPriv.h` — SkVertices 内部访问
- `src/core/SkVertState.h` — 顶点遍历状态机
- `src/gpu/graphite/RendererProvider.cpp` — 创建 8 种变体
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` — 深度模板设置
