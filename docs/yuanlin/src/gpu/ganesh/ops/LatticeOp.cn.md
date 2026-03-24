# LatticeOp

> 源文件
> - `src/gpu/ganesh/ops/LatticeOp.h`
> - `src/gpu/ganesh/ops/LatticeOp.cpp`

## 概述

`LatticeOp` 是 Ganesh GPU 后端中用于绘制格子图像（Lattice Images）的操作。格子图像是一种特殊的图像绘制技术，允许将源图像分割成可拉伸和固定的区域，类似于 Android 的 9-patch 图像。该操作支持非抗锯齿（Non-AA）的格子图像渲染，通过纹理采样和几何变换实现高效的图像拉伸效果。

格子绘制通过将图像分割成多个矩形区域，每个区域可以独立拉伸或保持原始尺寸，特别适用于 UI 元素（如按钮、边框）的渲染，能够在不同尺寸下保持良好的视觉效果。

## 架构位置

在 Skia 的 Ganesh 架构中，`LatticeOp` 位于以下层次：

```
skia/
  src/
    gpu/
      ganesh/
        ops/
          GrOp (基类)
            GrDrawOp
              GrMeshDrawOp
                └── NonAALatticeOp (内部实现)
          └── LatticeOp (命名空间)
```

它属于 Ganesh 操作系统的一部分，专门处理格子图像的 GPU 渲染。

## 主要类与结构体

### LatticeGP (几何处理器)

内部使用的几何处理器，负责格子绘制的顶点着色器和片段着色器生成。

**继承关系：** `GrGeometryProcessor`

**关键特性：**
- 处理纹理坐标和纹理域（texture domain）
- 支持颜色空间变换
- 支持纹理过滤（最近邻或线性）
- 每个顶点包含位置、纹理坐标、纹理域和颜色属性

### NonAALatticeOp (操作实现)

实际的格子绘制操作类。

**继承关系：** `GrMeshDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHelper` | `GrSimpleMeshDrawOpHelper` | 绘制操作辅助器 |
| `fPatches` | `STArray<1, Patch, true>` | 格子块数组 |
| `fView` | `GrSurfaceProxyView` | 纹理视图 |
| `fAlphaType` | `SkAlphaType` | Alpha 类型 |
| `fColorSpaceXform` | `sk_sp<GrColorSpaceXform>` | 颜色空间变换 |
| `fFilter` | `GrSamplerState::Filter` | 纹理过滤器 |
| `fWideColor` | `bool` | 是否使用宽色域 |
| `fMesh` | `GrSimpleMesh*` | 网格数据 |
| `fProgramInfo` | `GrProgramInfo*` | 程序信息 |

### Patch 结构体

表示单个格子绘制块的数据。

**成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fIter` | `std::unique_ptr<SkLatticeIter>` | 格子迭代器 |
| `fDst` | `SkRect` | 目标矩形 |
| `fColor` | `SkPMColor4f` | 调制颜色 |

## 公共 API 函数

### 工厂方法

```cpp
namespace skgpu::ganesh::LatticeOp {

GrOp::Owner MakeNonAA(
    GrRecordingContext* context,
    GrPaint&& paint,
    const SkMatrix& viewMatrix,
    GrSurfaceProxyView view,
    SkAlphaType alphaType,
    sk_sp<GrColorSpaceXform> colorSpaceXform,
    GrSamplerState::Filter filter,
    std::unique_ptr<SkLatticeIter> iter,
    const SkRect& dst
)

}
```
创建非抗锯齿的格子绘制操作。

**参数说明：**
- `context`：录制上下文
- `paint`：绘制参数
- `viewMatrix`：视图变换矩阵
- `view`：纹理代理视图
- `alphaType`：Alpha 类型
- `colorSpaceXform`：颜色空间变换
- `filter`：纹理过滤模式（最近邻或线性）
- `iter`：格子迭代器，定义了如何分割图像
- `dst`：目标绘制矩形

## 内部实现细节

### 格子顶点生成

格子绘制的核心是将源图像分割成多个矩形，每个矩形对应一个四边形（quad）：

```cpp
while (patch.fIter->next(&srcR, &dstR)) {
    // 计算纹理坐标
    skvx::float4 coords(srcR.fLeft, srcR.fTop, srcR.fRight, srcR.fBottom);
    coords *= scales;  // 归一化到 [0,1]

    // 计算纹理域（用于边界约束）
    skvx::float4 domain = coords + kDomainOffsets;

    // 处理底部原点的纹理
    if (fView.origin() == kBottomLeft_GrSurfaceOrigin) {
        coords = kFlipMuls * coords + kFlipOffsets;
        domain = shuffle(kFlipMuls * domain + kFlipOffsets);
    }

    // 写入顶点数据
    vertices.writeQuad(...);
}
```

### 纹理域约束

纹理域（texture domain）用于防止纹理采样时的边界问题：
- 在每个矩形边界内缩 0.5 像素
- 在片段着色器中使用 `clamp()` 限制采样坐标
- 这确保了相邻矩形不会互相干扰

```glsl
// 片段着色器中的采样
textureColor = sample(
    sampler,
    clamp(textureCoords, textureDomain.xy, textureDomain.zw)
);
```

### 视图矩阵优化

代码对缩放-平移矩阵进行了特殊优化：

```cpp
bool isScaleTranslate = patch.fViewMatrix.isScaleTranslate();
if (isScaleTranslate) {
    // 直接变换目标矩形
    patch.fIter->mapDstScaleTranslate(patch.fViewMatrix);
    // 使用优化的四边形写入路径
    vertices.writeQuad(VertexWriter::TriStripFromRect(dstR), ...);
} else {
    // 使用通用的四点变换
    patch.fViewMatrix.mapRectToQuad(mappedPts, dstR);
    // 手动写入四个顶点
}
```

### 操作合并

支持合并兼容的格子操作以提高性能：

```cpp
CombineResult onCombineIfPossible(GrOp* t, ...) {
    NonAALatticeOp* that = t->cast<NonAALatticeOp>();

    // 必须使用相同的纹理
    if (fView != that->fView) return kCannotCombine;

    // 必须使用相同的过滤器
    if (fFilter != that->fFilter) return kCannotCombine;

    // 必须使用相同的颜色空间变换
    if (!GrColorSpaceXform::Equals(...)) return kCannotCombine;

    // 合并格子块
    fPatches.move_back_n(that->fPatches.size(), that->fPatches.begin());
    return kMerged;
}
```

### 顶点布局

每个顶点包含以下属性：
1. **位置** (float2)：屏幕空间坐标
2. **纹理坐标** (float2)：归一化的纹理 UV 坐标
3. **纹理域** (float4)：约束采样的边界 (minU, minV, maxU, maxV)
4. **颜色** (byte4 或 float4)：调制颜色

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrMeshDrawOp` | 网格绘制操作基类 |
| `GrSimpleMeshDrawOpHelper` | 绘制辅助器 |
| `SkLatticeIter` | 格子迭代器，提供源和目标矩形 |
| `GrSurfaceProxyView` | 纹理代理视图 |
| `GrColorSpaceXform` | 颜色空间变换 |
| `GrGeometryProcessor` | 几何处理器基类 |
| `GrSamplerState` | 纹理采样状态 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SurfaceDrawContext` | 表面绘制上下文，调用格子操作 |
| `SkDevice` | 设备层，通过 Ganesh 使用格子绘制 |

## 设计模式与设计决策

### 命名空间工厂模式

使用命名空间而不是类来提供工厂方法：
```cpp
namespace skgpu::ganesh::LatticeOp {
    GrOp::Owner MakeNonAA(...);
}
```
这种设计将实现细节（`NonAALatticeOp` 类）隐藏在匿名命名空间中，只暴露创建函数。

### 迭代器模式

使用 `SkLatticeIter` 封装了复杂的格子分割逻辑：
- 隐藏了九宫格、自定义分割的实现细节
- 提供统一的 `next()` 接口遍历所有矩形
- 支持透明度和颜色标志

### 批处理优化

支持多个格子绘制合并到同一次 draw call：
- 使用 `STArray` 存储多个 Patch
- 在 `onPrepareDraws` 中一次性生成所有顶点
- 减少 GPU 状态切换

### 延迟程序创建

程序信息在以下时机创建：
1. `onPrePrepare`：DDL（延迟显示列表）模式
2. `onPrepare`：立即模式
3. 按需创建，避免不必要的开销

## 性能考量

### 顶点数据优化

1. **紧凑布局**：顶点属性按需配置（窄色域 vs 宽色域）
2. **SIMD 计算**：使用 `skvx::float4` 进行向量化坐标计算
3. **批量写入**：通过 `VertexWriter` 高效写入顶点数据

### 矩形变换优化

针对常见的缩放-平移矩阵进行了特殊优化：
- CPU 上直接变换矩形坐标
- 避免在 GPU 上进行透视除法
- 使用更紧凑的顶点数据

### GPU 状态管理

1. **合并兼容操作**：减少 draw call 数量
2. **共享纹理**：相同纹理的格子操作可以合并
3. **单次绑定**：所有合并的格子使用同一纹理绑定

### 内存分配

```cpp
SkSafeMath safeMath;
for (int i = 0; i < patchCnt; i++) {
    numRects = safeMath.addInt(numRects, fPatches[i].fIter->numRectsToDraw());
}
if (!numRects || !safeMath) {
    return;  // 防止溢出
}
```
使用 `SkSafeMath` 防止整数溢出。

### 测试工具支持

提供了随机测试生成器（`GR_DRAW_OP_TEST_DEFINE`）：
- 生成随机的格子配置
- 测试各种边界情况
- 验证操作的正确性

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `SkLatticeIter.h/cpp` | 依赖 | 格子迭代器实现 |
| `GrSimpleMeshDrawOpHelper.h` | 依赖 | 绘制辅助器 |
| `GrGeometryProcessor.h` | 依赖 | 几何处理器基类 |
| `GrSamplerState.h` | 依赖 | 纹理采样配置 |
| `GrColorSpaceXform.h` | 依赖 | 颜色空间变换 |
| `QuadHelper.h` | 使用 | 四边形辅助类 |
| `VertexWriter.h` | 使用 | 顶点写入工具 |
| `GrDrawOpTest.h` | 测试 | 操作测试框架 |
