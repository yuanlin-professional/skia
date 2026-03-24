# RegionOp

> 源文件
> - `src/gpu/ganesh/ops/RegionOp.h`
> - `src/gpu/ganesh/ops/RegionOp.cpp`

## 概述

`RegionOp` 是 Ganesh GPU 后端中用于渲染区域（SkRegion）的操作。区域是由多个不相交矩形组成的复杂形状，该操作将区域分解为一系列矩形并高效地批量渲染它们。支持非抗锯齿（kNone）和 MSAA 抗锯齿模式。

区域操作常用于渲染复杂的裁剪区域或由多个矩形组成的形状，在 UI 渲染中特别常见。

## 架构位置

```
skia/src/gpu/ganesh/ops/
  RegionOp (命名空间)
    └── RegionOpImpl (内部实现)
        ├── 继承自 GrMeshDrawOp
        └── 使用 GrSimpleMeshDrawOpHelperWithStencil
```

## 主要类与结构体

### RegionOpImpl

**继承关系：** `GrMeshDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHelper` | `GrSimpleMeshDrawOpHelperWithStencil` | 绘制辅助器 |
| `fViewMatrix` | `SkMatrix` | 视图变换矩阵 |
| `fRegions` | `STArray<1, RegionInfo>` | 区域信息数组 |
| `fWideColor` | `bool` | 是否使用宽色域 |
| `fMesh` | `GrSimpleMesh*` | 网格数据 |
| `fProgramInfo` | `GrProgramInfo*` | 程序信息 |

### RegionInfo 结构体

```cpp
struct RegionInfo {
    SkPMColor4f fColor;  // 颜色
    SkRegion fRegion;    // 区域
};
```

## 公共 API 函数

### 工厂方法

```cpp
GrOp::Owner Make(
    GrRecordingContext* context,
    GrPaint&& paint,
    const SkMatrix& viewMatrix,
    const SkRegion& region,
    GrAAType aaType,
    const GrUserStencilSettings* stencilSettings = nullptr
)
```

## 内部实现细节

### 矩形分解

```cpp
void onPrepareDraws(GrMeshDrawTarget* target) {
    // 计算总矩形数
    for (int i = 0; i < numRegions; i++) {
        numRects += fRegions[i].fRegion.computeRegionComplexity();
    }

    // 分配顶点缓冲区
    QuadHelper helper(target, vertexStride, numRects);

    // 遍历每个区域的矩形
    for (int i = 0; i < numRegions; i++) {
        SkRegion::Iterator iter(fRegions[i].fRegion);
        while (!iter.done()) {
            SkRect rect = SkRect::Make(iter.rect());
            vertices.writeQuad(VertexWriter::TriStripFromRect(rect), color);
            iter.next();
        }
    }
}
```

### 操作合并

```cpp
CombineResult onCombineIfPossible(GrOp* t, ...) {
    auto* that = t->cast<RegionOpImpl>();

    // 检查视图矩阵和辅助器兼容性
    if (fViewMatrix != that->fViewMatrix) return kCannotCombine;
    if (!fHelper.isCompatible(that->fHelper, ...)) return kCannotCombine;

    // 合并区域
    fRegions.push_back_n(that->fRegions.size(), that->fRegions.begin());
    fWideColor |= that->fWideColor;

    return kMerged;
}
```

### 几何处理器创建

```cpp
GrGeometryProcessor* make_gp(
    SkArenaAlloc* arena,
    const SkMatrix& viewMatrix,
    bool wideColor
) {
    Color::Type colorType = wideColor
        ? Color::kPremulWideColorAttribute_Type
        : Color::kPremulGrColorAttribute_Type;

    return GrDefaultGeoProcFactory::Make(
        arena,
        colorType,
        Coverage::kSolid_Type,
        LocalCoords::kUsePosition_Type,
        viewMatrix
    );
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrMeshDrawOp` | 网格绘制操作基类 |
| `GrSimpleMeshDrawOpHelperWithStencil` | 绘制辅助器 |
| `GrDefaultGeoProcFactory` | 默认几何处理器工厂 |
| `SkRegion` | 区域类 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SurfaceDrawContext` | 表面绘制上下文 |
| `SkDevice` | 设备层 |

## 设计模式与设计决策

### 命名空间工厂模式

使用命名空间隐藏实现细节，只暴露工厂函数。

### 迭代器模式

使用 `SkRegion::Iterator` 遍历区域中的矩形。

### 批处理优化

支持合并多个区域操作，减少 draw call。

## 性能考量

### 安全数学

使用 `SkSafeMath` 防止矩形计数溢出。

### 顶点数据优化

每个矩形4个顶点，使用三角带减少顶点数。

### 内存预分配

预先计算总矩形数，一次性分配顶点缓冲区。

### 宽色域支持

按需启用宽色域，节省顶点属性空间。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `SkRegion.h` | 依赖 | 区域类 |
| `GrSimpleMeshDrawOpHelperWithStencil.h` | 依赖 | 绘制辅助器 |
| `GrDefaultGeoProcFactory.h` | 依赖 | 几何处理器工厂 |
| `QuadHelper.h` | 使用 | 四边形辅助类 |
