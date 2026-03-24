# GlyphData

> 源文件
> - `src/gpu/ganesh/text/GlyphData.h`
> - `src/gpu/ganesh/text/GlyphData.cpp`

## 概述

`GlyphData` 是 Ganesh 文本渲染系统中的字形数据管理类,负责维护 SubRun(子渲染单元)的 packed glyph ID 到图集位置的映射关系。它协调字形图集位置数据随图集演化的更新,提供字形创建、图集再生成、顶点数据填充等核心功能。该类还包含三个相关结构体:`GlyphEntryKey`(字形键)、`GlyphEntry`(字形条目,包含图集位置)和 `Glyph`(轻量级适配器),形成完整的字形数据管理体系。

## 架构位置

`GlyphData` 位于 Skia GPU 文本渲染管线的数据管理层:

```
Skia 文本渲染架构
├── SubRun 层
│   └── SubRun (存储 GlyphData)
├── 字形数据层
│   ├── GlyphData (字形数据管理器) ← 当前类
│   ├── GlyphEntry (字形条目,包含图集位置)
│   ├── Glyph (字形适配器)
│   └── TextStrike (字形缓存条目)
├── 图集管理层
│   ├── GrAtlasManager (图集管理器)
│   ├── GrAtlasLocator (图集定位器)
│   └── GrBulkUsePlotUpdater (批量使用更新器)
├── 顶点生成层
│   └── VertexFiller (顶点填充器)
└── GPU 绘制层
    └── GrMeshDrawTarget (网格绘制目标)
```

该类是 SubRun 与图集系统之间的核心桥梁。

## 主要类与结构体

### 类继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `GlyphData` | 独立类 | 字形数据管理主类 |

### 相关结构体

| 结构体 | 说明 |
|--------|------|
| `GlyphEntryKey` | 字形条目键(SkPackedGlyphID + MaskFormat) |
| `GlyphEntry` | 字形条目(包含 GlyphEntryKey 和 GrAtlasLocator) |
| `Glyph` | 轻量级适配器,持有 GlyphEntry* 指针 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTextStrike` | `sk_sp<TextStrike>` | 关联的文本 Strike(字形缓存条目) |
| `fAtlasGeneration` | `uint64_t` | 图集代际号,跟踪图集内容变化 |
| `fBulkUseUpdater` | `GrBulkUsePlotUpdater` | 批量使用令牌更新器 |

### 顶点结构体(匿名命名空间)

| 结构体 | 字段 | 用途 |
|--------|------|------|
| `Mask2DVertex` | `SkPoint devicePos`, `GrColor color`, `AtlasPt atlasPos` | 2D 掩码/SDFT/彩色文本 |
| `ARGB2DVertex` | `SkPoint devicePos`, `AtlasPt atlasPos` | 2D ARGB 彩色文本(无独立颜色) |
| `Mask3DVertex` | `SkPoint3 devicePos`, `GrColor color`, `AtlasPt atlasPos` | 3D/透视 SDFT |
| `ARGB3DVertex` | `SkPoint3 devicePos`, `AtlasPt atlasPos` | 3D/透视 ARGB 彩色文本 |

## 公共 API 函数

### 静态工厂函数

```cpp
static sk_sp<TextStrike> FindStrike(sktext::gpu::StrikeCache* cache,
                                     const SkStrikeSpec& spec);
```
从 StrikeCache 获取或创建 TextStrike(委托给 `TextStrike::GetOrCreate`)。

### 字形创建

```cpp
Glyph makeGlyphFromID(SkPackedGlyphID, MaskFormat);
```
从 packed glyph ID 和掩码格式创建 `Glyph` 对象,内部从 TextStrike 获取 `GlyphEntry*`。

### 图集再生成

```cpp
std::tuple<bool, int> regenerateAtlas(int begin, int end,
                                       sktext::gpu::GlyphVector& glyphVector,
                                       MaskFormat maskFormat,
                                       int srcPadding,
                                       GrMeshDrawTarget* target);
```
为指定范围的字形重新生成图集条目。返回 `{success, glyphs_placed_in_atlas}`。

**处理逻辑:**
- 检查图集代际号,如果不匹配则需要重新上传
- 使用 `SkBulkGlyphMetricsAndImages` 批量获取字形图像
- 调用 `GrAtlasManager::addGlyphToAtlas` 添加缺失字形
- 更新批量使用令牌,防止图集驱逐
- 仅当所有字形成功放置后更新代际号

### 顶点处理

```cpp
size_t vertexStride(MaskFormat, const SkMatrix& positionMatrix) const;
```
根据掩码格式和矩阵返回顶点步幅:
- **ARGB + 透视**: `sizeof(ARGB3DVertex)` (20 字节)
- **ARGB + 2D**: `sizeof(ARGB2DVertex)` (12 字节)
- **掩码 + 透视**: `sizeof(Mask3DVertex)` (24 字节)
- **掩码 + 2D**: `sizeof(Mask2DVertex)` (16 字节)

```cpp
void fillVertexData(const sktext::gpu::VertexFiller& vf,
                    SkSpan<const Glyph> glyphs,
                    int offset, int count,
                    const SkPMColor4f& pmColor,
                    const SkMatrix& positionMatrix,
                    SkIRect clip,
                    void* vertexBuffer);
```
填充顶点缓冲区,根据变换类型选择优化路径:
- **直接路径(无变换)**: 使用 `fillDirectNoClipping` 或 `fillDirectClipped`
- **2D 变换**: 使用 `fill2D`
- **3D 透视**: 使用 `fill3D`

## 内部实现细节

### 顶点填充优化路径

**1. 直接无裁剪路径** (99% 常见情况):
```cpp
void fillDirectNoClipping(SkZip<Mask2DVertex[4], const Glyph, const SkPoint> quadData,
                          GrColor color, SkPoint originOffset) {
    for (auto [quad, glyph, leftTop] : quadData) {
        auto [al, at, ar, ab] = glyph.entry().fAtlasLocator.getUVs();
        SkScalar dl = leftTop.x() + originOffset.x(),
                 dt = leftTop.y() + originOffset.y(),
                 dr = dl + (ar - al),
                 db = dt + (ab - at);
        quad[0] = {{dl, dt}, color, {al, at}};  // L,T
        // ... 其他顶点
    }
}
```

**2. 直接有裁剪路径**:
```cpp
if (!clip->containsNoEmptyCheck(devIRect)) {
    if (SkIRect clipped; clipped.intersect(devIRect, *clip)) {
        al += clipped.left() - devIRect.left();  // 调整图集坐标
        at += clipped.top() - devIRect.top();
        ar += clipped.right() - devIRect.right();
        ab += clipped.bottom() - devIRect.bottom();
        // 使用裁剪后的设备坐标
    } else {
        // 完全裁剪:生成退化四边形(全零)
    }
}
```

**3. 2D 变换路径**:
```cpp
template <typename Quad, typename VertexData>
void fill2D(SkZip<Quad, const Glyph, const VertexData> quadData,
            GrColor color, const SkMatrix& viewDifference) {
    for (auto [quad, glyph, leftTop] : quadData) {
        auto [l, t] = leftTop;
        auto [r, b] = leftTop + glyph.entry().fAtlasLocator.widthHeight();
        SkPoint lt = viewDifference.mapPoint({l, t}),
                lb = viewDifference.mapPoint({l, b}),
                rt = viewDifference.mapPoint({r, t}),
                rb = viewDifference.mapPoint({r, b});
        // 填充四个顶点
    }
}
```

**4. 3D 透视路径**:
```cpp
auto mapXYZ = [&](SkScalar x, SkScalar y) {
    return viewDifference.mapPointToHomogeneous({x, y});
};
// 映射到齐次坐标 SkPoint3
```

### 图集代际检测

```cpp
uint64_t currentAtlasGen = atlasManager->atlasGeneration(maskFormat);
if (fAtlasGeneration != currentAtlasGen) {
    // 图集已变化,需要重新上传所有字形
    fBulkUseUpdater.reset();
    for (int i = begin; i < end; i++) {
        if (!atlasManager->hasGlyph(maskFormat, glyph.entry())) {
            atlasManager->addGlyphToAtlas(...);
        }
        atlasManager->addGlyphToBulkAndSetUseToken(...);
    }
    // 仅当所有字形成功时更新代际号
    if (success && begin + glyphsPlacedInAtlas == glyphVector.glyphCount()) {
        fAtlasGeneration = atlasManager->atlasGeneration(maskFormat);
    }
} else {
    // 图集未变化,仅更新使用令牌
    atlasManager->setUseTokenBulk(fBulkUseUpdater, ...);
}
```

### 批量字形获取

```cpp
SkBulkGlyphMetricsAndImages metricsAndImages{fTextStrike->strikeSpec()};
for (int i = begin; i < end; i++) {
    const SkGlyph& skGlyph = *metricsAndImages.glyph(glyph.packedID());
    // 自动批量从 Strike 获取,减少单个查找开销
}
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `TextStrike` | 强依赖 | 字形缓存条目,提供 GlyphEntry 存储 |
| `GrAtlasManager` | 强依赖 | 图集管理和字形添加 |
| `GrAtlasLocator` | 强依赖 | 图集位置定位器 |
| `GrBulkUsePlotUpdater` | 强依赖 | 批量使用令牌更新 |
| `GrMeshDrawTarget` | 使用依赖 | 获取图集管理器和上传目标 |
| `sktext::gpu::GlyphVector` | 使用依赖 | 字形向量容器 |
| `sktext::gpu::VertexFiller` | 使用依赖 | 顶点填充策略 |
| `SkBulkGlyphMetricsAndImages` | 使用依赖 | 批量字形图像获取 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| SubRun 实现类 | 存储 GlyphData,协调渲染 |
| `GrTextBlob` | 通过 SubRun 访问 GlyphData |
| 文本渲染操作 | 使用 GlyphData 生成顶点数据 |

## 设计模式与设计决策

### 适配器模式

`Glyph` 类作为 `GlyphEntry*` 的轻量级适配器:
```cpp
class Glyph {
    GlyphEntry* fEntry;
public:
    explicit Glyph(GlyphEntry* entry) : fEntry{entry} {}
    SkPackedGlyphID packedID() const { return fEntry->fGlyphEntryKey.fPackedID; }
    GlyphEntry& entry() const { return *fEntry; }
};
```
禁止拷贝和移动,确保仅通过指针引用访问。

### 模板优化

顶点填充函数使用模板避免运行时分支:
```cpp
template <typename Quad, typename VertexData>
void fillDirectClipped(SkZip<Quad, const Glyph, const VertexData> quadData, ...);
```
编译时确定顶点类型,生成特化代码。

### 代际缓存失效

使用单调递增的代际号快速检测图集内容变化,避免逐字形检查:
```cpp
uint64_t fAtlasGeneration{GrAtlasGenerationCounter::kInvalidGeneration};
```

### 分离键和值

`GlyphEntryKey` 独立于 `GlyphEntry`,支持高效哈希查找:
```cpp
struct GlyphEntryKey {
    const SkPackedGlyphID fPackedID;
    MaskFormat fFormat;
    uint32_t hash() const { return fPackedID.hash(); }  // 仅哈希 ID,格式参与比较
};
```

### 批量令牌更新

使用 `GrBulkUsePlotUpdater` 去重并批量更新使用令牌:
```cpp
fBulkUseUpdater.reset();  // 新代际开始时重置
atlasManager->addGlyphToBulkAndSetUseToken(&fBulkUseUpdater, ...);
```

## 性能考量

### 顶点生成快速路径

**直接无裁剪路径优化**:
- 无矩阵变换(仅平移)
- 无裁剪检测
- 简单的加法和减法计算
- 对应 99% 的文本渲染场景

### 结构体布局

顶点结构体紧凑排列,最小化内存占用:
- `Mask2DVertex`: 16 字节 (4+4+4+2+2)
- `ARGB2DVertex`: 12 字节 (4+4+2+2)
- 利用 GPU 对齐要求优化缓存访问

### 批量图集操作

```cpp
SkBulkGlyphMetricsAndImages metricsAndImages{fTextStrike->strikeSpec()};
```
一次性预取所有字形数据,减少 Strike 查找开销。

### 代际比较优化

```cpp
if (fAtlasGeneration != currentAtlasGen) {
    // 重新上传
} else {
    // 仅更新令牌(快速路径)
    if (end == glyphVector.glyphCount()) {
        atlasManager->setUseTokenBulk(...);  // 批量更新
    }
    return {true, end - begin};  // 直接返回
}
```

### 裁剪早期退出

```cpp
if (!clip->containsNoEmptyCheck(devIRect)) {
    // 大多数情况无需裁剪,早期退出
}
```

### SkZip 迭代器

```cpp
for (auto [quad, glyph, leftTop] : quadData) {
    // 同时迭代三个数组,无额外索引计算
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/text/TextStrike.h` | 协作 | 字形缓存条目 |
| `src/gpu/ganesh/text/GrAtlasManager.h` | 依赖 | 图集管理器 |
| `src/gpu/ganesh/GrAtlasTypes.h` | 类型 | GrAtlasLocator 定义 |
| `src/text/gpu/GlyphVector.h` | 协作 | 字形向量容器 |
| `src/text/gpu/VertexFiller.h` | 协作 | 顶点填充策略 |
| `src/text/gpu/StrikeCache.h` | 依赖 | Strike 缓存系统 |
| `src/core/SkGlyph.h` | 类型 | 核心字形定义 |
| `src/core/SkStrike.h` | 依赖 | Strike 实现 |
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 协作 | 网格绘制目标 |
| `src/gpu/ganesh/GrColor.h` | 工具 | 颜色打包工具 |
