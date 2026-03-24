# SmallPathRenderer

> 源文件
> - `src/gpu/ganesh/ops/SmallPathRenderer.h`
> - `src/gpu/ganesh/ops/SmallPathRenderer.cpp`

## 概述

`SmallPathRenderer` 是 Ganesh GPU 后端中专门用于渲染小路径的路径渲染器。该渲染器通过将小路径光栅化到纹理图集（atlas）中，然后作为纹理四边形绘制，实现高效的小路径批处理渲染。这种方法特别适合文本渲染和 UI 图标等包含大量重复小路径的场景。

该渲染器仅在未定义 `SK_ENABLE_OPTIMIZE_SIZE` 时可用，因为它需要额外的代码和纹理图集管理。

## 架构位置

```
skia/src/gpu/ganesh/
  PathRenderer (基类)
    └── SmallPathRenderer
        ├── 使用 SmallPathAtlasMgr (图集管理器)
        └── 使用 SmallPathShapeData (形状数据缓存)
```

## 主要类与结构体

### SmallPathRenderer

**继承关系：** `PathRenderer`

**模板渲染策略：**
1. 检查路径是否在缓存中
2. 如果不在，光栅化路径到图集纹理
3. 将路径作为纹理四边形绘制

**不支持的功能：**
- 模板操作（`kNoSupport_StencilSupport`）
- 大路径（由其他渲染器处理）

## 公共 API 函数

### 核心方法

```cpp
const char* name() const override { return "Small"; }
```
返回渲染器名称。

```cpp
StencilSupport onGetStencilSupport(const GrStyledShape&) const override
```
返回模板支持级别（无支持）。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以绘制给定路径。

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行路径绘制。

## 内部实现细节

### 路径大小判断

```cpp
// 检查路径边界是否足够小
constexpr static SkScalar kMaxDimension = 256.0f;

SkRect bounds = shape.bounds();
SkScalar maxDimension = std::max(bounds.width(), bounds.height());

if (maxDimension > kMaxDimension) {
    return CanDrawPath::kNo;
}
```

**大小限制原因：**
- 纹理图集有限的空间
- 大路径光栅化成本高
- 大路径不适合缓存复用

### 图集缓存策略

```cpp
// 1. 查找或创建形状数据
SmallPathShapeData* shapeData =
    atlasMgr->findOrCreate(shape, desiredDimension);

// 2. 检查是否需要上传到图集
if (!shapeData->fAtlasLocator.isValid()) {
    // 光栅化路径到位图
    SkBitmap bitmap;
    rasterize_path(shape, &bitmap);

    // 上传到图集
    GrDrawOpAtlas::ErrorCode error =
        atlasMgr->addToAtlas(resourceProvider, target,
                            bitmap.width(), bitmap.height(),
                            bitmap.getPixels(),
                            &shapeData->fAtlasLocator);

    if (error != GrDrawOpAtlas::ErrorCode::kSucceeded) {
        // 处理图集满的情况
    }
}

// 3. 使用图集位置绘制四边形
draw_quad_from_atlas(shapeData->fAtlasLocator, ...);
```

### 路径光栅化

```cpp
void rasterize_path(const GrStyledShape& shape, SkBitmap* bitmap) {
    // 1. 计算合适的光栅化尺寸
    SkISize dimensions = compute_raster_size(shape);

    // 2. 分配位图
    bitmap->allocPixels(SkImageInfo::MakeA8(dimensions.width(),
                                             dimensions.height()));

    // 3. 在 CPU 上光栅化
    SkCanvas canvas(*bitmap);
    canvas.clear(SK_ColorTRANSPARENT);
    canvas.drawPath(shape.path(), paint);
}
```

### 形状变换处理

```cpp
SmallPathShapeData* findOrCreate(
    const GrStyledShape& shape,
    const SkMatrix& ctm
) {
    // 计算形状在设备空间的尺寸
    SkRect devBounds = transform_bounds(shape.bounds(), ctm);

    // 计算合适的图集尺寸（考虑DPI）
    int desiredDimension = compute_atlas_dimension(devBounds);

    // 使用形状和尺寸作为缓存键
    SmallPathShapeDataKey key(shape, desiredDimension);

    return fShapeCache.findOrCreate(key);
}
```

### 图集纹理管理

```cpp
class SmallPathAtlasMgr {
    std::unique_ptr<GrDrawOpAtlas> fAtlas;
    ShapeCache fShapeCache;  // 形状数据缓存
    ShapeDataList fShapeList;  // LRU列表

    void evict(GrPlotLocator locator) override {
        // 当图集区域被回收时，使缓存条目无效
        for (auto* shapeData : fShapeList) {
            if (shapeData->fAtlasLocator.plotLocator() == locator) {
                shapeData->fAtlasLocator.invalidate();
            }
        }
    }
};
```

### 绘制四边形生成

```cpp
void draw_atlas_quad(
    const GrAtlasLocator& locator,
    const SkMatrix& viewMatrix,
    const SkRect& shapeBounds,
    GrPaint&& paint
) {
    // 1. 获取纹理坐标
    SkRect uvRect = locator.getUVRect();

    // 2. 计算设备空间四边形
    SkRect devRect = viewMatrix.mapRect(shapeBounds);

    // 3. 创建纹理四边形操作
    GrOp::Owner op = TextureOp::Make(
        context,
        std::move(paint),
        viewMatrix,
        atlasSurfaceProxy,
        uvRect,
        devRect,
        ...
    );

    // 4. 添加操作
    sdc->addDrawOp(std::move(op));
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRenderer` | 路径渲染器基类 |
| `SmallPathAtlasMgr` | 图集管理器 |
| `SmallPathShapeData` | 形状数据缓存 |
| `GrDrawOpAtlas` | 绘制操作图集 |
| `TextureOp` | 纹理操作 |
| `GrStyledShape` | 样式化形状 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `PathRendererChain` | 路径渲染器链 |
| `SurfaceDrawContext` | 表面绘制上下文 |

## 设计模式与设计决策

### 缓存与图集模式

通过纹理图集实现路径复用：
- 光栅化一次，多次绘制
- 特别适合文本和图标

### 延迟光栅化

只在需要时光栅化：
- 第一次使用时光栅化
- 后续使用从缓存读取

### LRU 驱逐策略

使用最近最少使用策略管理图集：
```cpp
void setUseToken(SmallPathShapeData* data, skgpu::Token token) {
    fAtlas->setLastUseToken(data->fAtlasLocator, token);
}
```

### 尺寸分桶

根据设备空间尺寸分桶缓存：
- 相同形状在不同尺寸下有不同缓存条目
- 避免缩放质量损失

### 条件编译

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
// ... 实现 ...
#endif
```

在优化大小的构建中完全移除。

## 性能考量

### 批处理优势

1. **纹理绘制快速**：比光栅化路径快得多
2. **批量处理**：多个小路径可以合并为单次绘制
3. **GPU 友好**：简单的纹理四边形

### 缓存效率

1. **复用率高**：文本和UI图标重复使用
2. **内存可控**：图集大小固定
3. **LRU驱逐**：自动管理内存

### 光栅化开销

1. **CPU光栅化**：第一次使用有开销
2. **上传开销**：纹理上传到GPU
3. **图集查找**：哈希表查找

### 何时不适用

- **大路径**：超过256像素
- **复杂路径**：光栅化成本高于直接渲染
- **单次绘制**：无复用机会

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `SmallPathAtlasMgr.h` | 依赖 | 图集管理器 |
| `SmallPathShapeData.h` | 依赖 | 形状数据 |
| `PathRenderer.h` | 基类 | 路径渲染器基类 |
| `GrDrawOpAtlas.h` | 依赖 | 绘制操作图集 |
| `TextureOp.h` | 使用 | 纹理操作 |
| `GrStyledShape.h` | 依赖 | 样式化形状 |
