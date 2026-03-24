# ShadowRRectOp

> 源文件
> - `src/gpu/ganesh/ops/ShadowRRectOp.h`
> - `src/gpu/ganesh/ops/ShadowRRectOp.cpp`

## 概述

`ShadowRRectOp` 是 Ganesh GPU 后端中用于渲染圆角矩形阴影的操作。该操作实现了模糊阴影效果，支持圆形和圆角矩形的阴影渲染，使用衰减纹理和几何扩展技术实现高效的软阴影效果。

阴影渲染使用预计算的径向衰减纹理，通过几何扩展和纹理采样实现模糊效果，避免了昂贵的多次模糊操作。

## 架构位置

```
skia/src/gpu/ganesh/ops/
  ShadowRRectOp (命名空间)
    └── ShadowCircularRRectOp (内部实现)
        ├── 继承自 GrMeshDrawOp
        └── 使用 GrShadowGeoProc
```

## 主要类与结构体

### ShadowCircularRRectOp

**继承关系：** `GrMeshDrawOp`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFalloffView` | `GrSurfaceProxyView` | 衰减纹理视图 |
| `fGeoData` | `TArray<Geometry>` | 几何数据数组 |
| `fVertCount` | `int` | 顶点数量 |
| `fIndexCount` | `int` | 索引数量 |
| `fProgramInfo` | `GrProgramInfo*` | 程序信息 |
| `fMesh` | `GrSimpleMesh*` | 网格数据 |

### Geometry 结构体

```cpp
struct Geometry {
    GrColor fColor;          // 阴影颜色
    SkScalar fOuterRadius;   // 外半径
    SkScalar fUmbraInset;    // 本影内缩
    SkScalar fInnerRadius;   // 内半径
    SkScalar fBlurRadius;    // 模糊半径
    SkRect fDevBounds;       // 设备边界
    RRectType fType;         // 类型（填充/描边/过描边）
    bool fIsCircle;          // 是否为圆形
};
```

## 公共 API 函数

### 工厂方法

```cpp
GrOp::Owner Make(
    GrRecordingContext* context,
    GrColor color,
    const SkMatrix& viewMatrix,
    const SkRRect& rrect,
    SkScalar blurWidth,
    SkScalar insetWidth
)
```

## 内部实现细节

### 阴影几何类型

#### 圆形阴影

- **填充**：9顶点八边形（中心点+8个外围点）
- **描边**：16顶点双层八边形（内圈8点+外圈8点）

#### 圆角矩形阴影

- **填充**：24顶点九宫格布局
- **描边**：24顶点九宫格布局
- **过描边**：28顶点九宫格布局（额外的中心矩形）

### 顶点生成

```cpp
void onPrepareDraws(GrMeshDrawTarget* target) override {
    // 1. 分配顶点和索引缓冲区
    sk_sp<const GrGpuBuffer> vb;
    int firstVertex;
    VertexWriter verts = target->makeVertexWriter(...);

    // 2. 生成顶点数据
    for (const auto& geo : fGeoData) {
        if (geo.fIsCircle) {
            fill_circle_data(...);
        } else {
            fill_rrect_data(...);
        }
    }

    // 3. 获取或创建索引缓冲区
    sk_sp<const GrBuffer> ib = get_index_buffer(...);

    // 4. 配置网格
    fMesh = target->allocMesh();
    fMesh->setIndexed(...);
}
```

### 衰减纹理

使用预计算的径向衰减纹理：
- 1D 衰减曲线存储在纹理中
- 根据距离边界的距离采样纹理
- 实现软阴影边缘

```glsl
// 片段着色器中
float dist = distance_to_edge(...);
float alpha = texture(falloffTexture, dist).a;
```

### 索引缓冲区

不同阴影类型使用预定义的索引模式：

```cpp
// 圆形填充：24个索引（8个三角形）
static const uint16_t gFillCircleIndices[] = {
    0, 1, 8, 1, 2, 8, 2, 3, 8, ...
};

// 圆角矩形过描边：多个索引集
static const uint16_t gRRectIndices[] = {
    // 过描边四边形
    0, 6, 25, 0, 25, 24, ...
    // 角落
    0, 1, 2, 0, 2, 3, ...
    // 边缘
    0, 5, 11, 0, 11, 6, ...
    // 填充四边形
    0, 6, 18, 0, 18, 12,
};
```

### 操作合并

```cpp
CombineResult onCombineIfPossible(GrOp* t, ...) {
    auto* that = t->cast<ShadowCircularRRectOp>();

    // 检查纹理兼容性
    if (fFalloffView != that->fFalloffView) return kCannotCombine;

    // 合并几何数据
    fGeoData.push_back_n(that->fGeoData.size(), that->fGeoData.begin());
    fVertCount += that->fVertCount;
    fIndexCount += that->fIndexCount;

    return kMerged;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrMeshDrawOp` | 网格绘制操作基类 |
| `GrShadowGeoProc` | 阴影几何处理器 |
| `GrThreadSafeCache` | 线程安全缓存（存储衰减纹理） |
| `GrMippedBitmap` | Mip 映射位图 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkShadowUtils` | 阴影工具类 |
| `SurfaceDrawContext` | 表面绘制上下文 |

## 设计模式与设计决策

### 纹理共享

衰减纹理在所有阴影操作间共享，使用线程安全缓存管理。

### 几何优化

针对圆形和圆角矩形使用不同的几何布局，优化顶点数量。

### 索引缓冲区复用

静态索引缓冲区在多次绘制间复用。

### 类型化几何

使用 `RRectType` 枚举区分填充、描边和过描边。

## 性能考量

### 顶点数量最小化

- 圆形填充：9顶点
- 圆形描边：16顶点
- 圆角矩形：24或28顶点

### 纹理采样优化

使用1D衰减纹理而非2D，节省内存和带宽。

### 批处理

支持合并多个阴影，减少 draw call。

### 几何实例化

相同类型的阴影共享索引缓冲区。

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrShadowGeoProc.h` | 依赖 | 阴影几何处理器 |
| `SkShadowUtils.h` | 使用者 | 阴影工具类 |
| `GrThreadSafeCache.h` | 依赖 | 线程安全缓存 |
| `GrMippedBitmap.h` | 依赖 | Mip 映射位图 |
