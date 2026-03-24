# SkDraw_vertices

> 源文件
> - src/core/SkDraw_vertices.cpp

## 概述

`SkDraw_vertices` 实现了顶点绘制（vertices drawing）在CPU光栅化器中的核心功能，对应 `SkCanvas::drawVertices()` API。它支持将三角形网格绘制到位图，支持独立的位置和纹理坐标、每顶点颜色、自定义混合器，以及透视投影的正确处理。该模块使用 `SkRasterPipeline` 构建着色管线，通过 `SkTriColorShader` 和 `SkTransformShader` 实现顶点着色，是实现2D/3D混合渲染和粒子系统的关键组件。

## 架构位置

该文件位于 `src/core` 核心绘制层，属于 `skcpu::Draw` 命名空间。它是 `SkDraw` 绘制引擎的扩展，与 `SkDraw_atlas.cpp`、`SkDraw_text.cpp` 并列。它连接高层API（`SkCanvas`、`SkVertices`）和底层光栅化器（`SkScan`、`SkBlitter`），处理复杂的坐标变换和着色器组合逻辑。

## 主要类与结构体

该文件为 `skcpu::Draw` 类添加成员函数，不定义独立的公共类。

### 核心函数

```cpp
namespace skcpu {
void Draw::drawVertices(const SkVertices* vertices,
                        sk_sp<SkBlender> blender,
                        const SkPaint& paint,
                        bool skipColorXform) const

void Draw::drawFixedVertices(const SkVertices* vertices,
                              sk_sp<SkBlender> blender,
                              const SkPaint& paint,
                              const SkMatrix& ctmInverse,
                              const SkPoint* dev2,
                              const SkPoint3* dev3,
                              SkArenaAlloc* outerAlloc,
                              bool skipColorXform) const
```

**函数职责：**
- `drawVertices`：入口函数，执行CTM变换和预处理
- `drawFixedVertices`：核心实现，执行实际的三角形光栅化

## 公共 API 函数

### drawVertices

```cpp
void Draw::drawVertices(const SkVertices* vertices,
                        sk_sp<SkBlender> blender,
                        const SkPaint& paint,
                        bool skipColorXform) const
```

**参数说明：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `vertices` | `const SkVertices*` | 顶点数据（位置、纹理坐标、颜色、索引） |
| `blender` | `sk_sp<SkBlender>` | 颜色与纹理的混合器 |
| `paint` | `const SkPaint&` | 绘制属性（shader、alpha等） |
| `skipColorXform` | `bool` | 是否跳过颜色空间转换（调试用） |

**执行流程：**
1. 验证顶点数量（至少3个）和裁剪区域
2. 计算CTM的逆矩阵
3. 分配内存（栈上分配器，大小基于顶点数）
4. 将顶点位置变换到设备空间（透视使用 `SkPoint3`，非透视使用 `SkPoint`）
5. 检查变换结果的有效性（有限值、非空边界）
6. 调用 `drawFixedVertices` 执行光栅化

### drawFixedVertices

内部函数，执行实际的三角形迭代和光栅化。

**核心步骤：**
1. 提取顶点数据（位置、纹理坐标、颜色、索引）
2. 处理纹理坐标（如果没有则使用位置）
3. 优化混合器（kSrc移除颜色，kDst移除纹理）
4. 转换颜色到目标色彩空间
5. 创建 `SkTriColorShader`（三角形颜色插值）
6. 创建 `SkTransformShader`（纹理坐标变换）
7. 组合着色器（应用混合器）
8. 构建光栅管线和blitter
9. 使用 `VertState` 迭代三角形
10. 对每个三角形更新着色器并调用 `fill_triangle`

## 内部实现细节

### 颜色处理

**颜色空间转换：**
```cpp
static SkPMColor4f* convert_colors(const SkColor src[], int count,
                                   SkColorSpace* deviceCS,
                                   SkArenaAlloc* alloc,
                                   bool skipColorXform)
```
将 `SkColor`（sRGB BGRA8888）转换为 `SkPMColor4f`（预乘浮点RGBA），支持颜色空间转换。使用 `SkConvertPixels` 执行批量转换。

**不透明性检测：**
```cpp
static bool compute_is_opaque(const SkColor colors[], int count) {
    uint32_t c = ~0;
    for (int i = 0; i < count; ++i) {
        c &= colors[i];
    }
    return SkColorGetA(c) == 0xFF;
}
```
通过位与操作高效检测所有颜色是否完全不透明。

### 纹理坐标变换

**变换矩阵计算：**
```cpp
std::optional<SkMatrix> texture_to_matrix(const VertState& state,
                                          const SkPoint verts[],
                                          const SkPoint texs[])
```
使用 `SkMatrix::PolyToPoly` 计算从顶点位置到纹理坐标的仿射变换。这允许纹理坐标独立于位置坐标，支持复杂的UV映射。

**TransformShader更新：**
每个三角形前更新变换：
```cpp
if (!transformShader || ((localM = texture_to_matrix(state, positions, texCoords)) &&
                         transformShader->update(SkMatrix::Concat(*localM, ctmInverse)))) {
    fill_triangle(state, blitter, *fRC, dev2, dev3);
}
```

### 透视裁剪

**齐次坐标处理：**
对于透视情况（`dev3` 非空），使用 `fill_triangle_3` 执行裁剪：

```cpp
static void fill_triangle_3(const VertState& state, SkBlitter* blitter,
                            const SkRasterClip& rc, const SkPoint3 dev3[])
```

**裁剪算法：**
1. 对三角形的每条边检查Z值（近平面裁剪）
2. 如果顶点在近平面前（`z <= tol`，`tol=0.05`），计算与平面的交点
3. 生成裁剪后的多边形（可能是3或4个顶点）
4. 透视除法：`(x/z, y/z)` 得到屏幕坐标
5. 分解为三角形并填充

**数值稳定性：**
使用 `sk_ieee_float_divide` 避免除零：
```cpp
float scale = sk_ieee_float_divide(1.0f, outPoints[i].fZ);
dst[i].set(outPoints[i].fX * scale, outPoints[i].fY * scale);
```

### 混合器优化

```cpp
if (std::optional<SkBlendMode> bm = as_BB(blender)->asBlendMode(); bm.has_value() && colors) {
    switch (*bm) {
        case SkBlendMode::kSrc:
            colors = nullptr;  // 忽略顶点颜色
            break;
        case SkBlendMode::kDst:
            blenderIsDst = true;
            texCoords = nullptr;  // 忽略纹理
            paintShader = nullptr;
            break;
        default: break;
    }
}
```

**kSrc模式：** 只使用纹理，移除颜色处理（性能优化）
**kDst模式：** 只使用顶点颜色，移除纹理采样

### VertState 三角形迭代

`VertState` 封装三角形枚举逻辑：
- **三角带（triangle strip）：** 顺序连接顶点
- **三角扇（triangle fan）：** 所有三角形共享第一个顶点
- **独立三角形（triangles）：** 每3个顶点一个三角形
- **索引模式：** 使用索引数组引用顶点

```cpp
VertState state(vertexCount, indices, indexCount);
VertState::Proc vertProc = state.chooseProc(info.mode());
while (vertProc(&state)) {
    // state.f0, state.f1, state.f2 是当前三角形的顶点索引
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkVertices` | 顶点数据容器 |
| `SkTriColorShader` | 三角形内颜色插值 |
| `SkTransformShader` | 动态纹理坐标变换 |
| `SkRasterPipeline` | 着色计算管线 |
| `SkConvertPixels` | 批量颜色格式转换 |
| `SkScan` | 三角形光栅化 |
| `VertState` | 三角形网格迭代 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkCanvas::drawVertices()` | 高层API入口 |
| `SkDevice` | 设备抽象层分发到CPU实现 |

## 设计模式与设计决策

**着色器组合模式：** 使用 `SkShaders::Blend` 组合多个着色器：
```cpp
auto applyShaderColorBlend = [&](SkShader* shader) -> sk_sp<SkShader> {
    return SkShaders::Blend(blender, sk_ref_sp(triColorShader),
                            sk_ref_sp(shader));
};
```
这种组合方式灵活且可扩展。

**策略模式：** 根据是否有透视、是否有独立纹理坐标等条件，选择不同的渲染策略（`dev2` vs `dev3`，`transformShader` vs 直接纹理）。

**栈分配优化：** 使用预估大小的栈分配器：
```cpp
constexpr size_t kOuterSize = sizeof(SkTriColorShader) +
                              (2 * sizeof(SkPoint) + sizeof(SkColor4f)) * kDefVertexCount;
SkSTArenaAlloc<kOuterSize> outerAlloc;
```
`kDefVertexCount=16` 覆盖大多数小型网格。

**懒惰更新：** 着色器的变换和颜色参数在每个三角形前才更新，而非预先计算所有三角形的参数。这减少了缓存未使用数据的可能。

**提前退出：** 在多个检查点提前返回（空顶点、退化矩阵、无限值等），避免无效计算。

## 性能考量

**内存局部性：** `drawFixedVertices` 接收预变换的顶点（`dev2/dev3`），避免重复变换。所有顶点数据连续存储，遍历时缓存友好。

**分支预测：** 透视vs非透视、有无颜色等分支在整个绘制过程中是稳定的，分支预测器能有效工作。

**批量颜色转换：** 使用 `SkConvertPixels` 一次转换所有颜色，比逐个转换快（利用SIMD）。

**不透明优化：** 通过 `compute_is_opaque` 检测，告知blitter可以使用快速路径：
```cpp
triColorShader = outerAlloc->make<SkTriColorShader>(compute_is_opaque(colors, vertexCount),
                                                    usePerspective);
```

**零高度三角形跳过：** `fill_triangle` 内部处理退化三角形（面积为0），直接跳过。

**栈vs堆权衡：** 对于16个以下顶点（占多数），完全在栈上分配。更大的网格会触发堆分配，但这是合理的（通常性能不是瓶颈）。

**管线复用：** 管线构建开销大，但在所有三角形间共享。仅shader上下文（变换矩阵、颜色）每三角形更新。

**透视裁剪开销：** 透视情况下，每个三角形需要裁剪计算（多次浮点除法）。这是不可避免的，但实现已优化（最小化计算次数）。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkCanvas.h` | 定义 `drawVertices()` API |
| `include/core/SkVertices.h` | 顶点数据容器 |
| `src/shaders/SkTriColorShader.h` | 三角形颜色插值着色器 |
| `src/shaders/SkTransformShader.h` | 可更新变换的着色器 |
| `src/core/SkVertState.h` | 三角形迭代工具 |
| `src/core/SkScan.h` | 三角形填充入口 |
| `src/core/SkConvertPixels.h` | 颜色格式转换 |
| `src/core/SkDraw.h` | 绘制引擎基类 |
