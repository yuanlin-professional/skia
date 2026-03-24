# SkDraw_text

> 源文件
> - src/core/SkDraw_text.cpp

## 概述

`SkDraw_text` 实现了文本绘制在CPU光栅化器中的核心功能，负责将字形（glyph）渲染到位图表面。它处理遮罩（mask）格式的字形绘制，包括灰度、LCD亚像素和ARGB彩色字形，支持复杂的裁剪区域（矩形、区域、抗锯齿裁剪）。该模块是 `SkCanvas::drawTextBlob()` 和相关文本API在CPU后端的最终执行层，通过 `GlyphRunPainter` 与更高层的文本布局和字形缓存系统集成。

## 架构位置

该文件位于 `src/core` 核心绘制层，属于 `skcpu::Draw` 命名空间。它是 `SkDraw` 绘制引擎的文本渲染扩展，与 `SkDraw_atlas.cpp`、`SkDraw_vertices.cpp` 并列。它处于文本渲染管线的底层：`SkCanvas` → `GlyphRunPainter` → `SkDraw::paintMasks()` → `SkBlitter`。该模块不处理文本布局或字形选择，仅负责已光栅化字形的绘制。

## 主要类与结构体

该文件为 `skcpu::Draw` 类添加成员函数，不定义独立的公共类。

### 核心函数

```cpp
namespace skcpu {
void Draw::paintMasks(SkZip<const SkGlyph*, SkPoint> accepted,
                      const SkPaint& paint) const;

void Draw::drawGlyphRunList(SkCanvas* canvas,
                            GlyphRunListPainter* glyphPainter,
                            const sktext::GlyphRunList& glyphRunList,
                            const SkPaint& paint) const;
}
```

## 公共 API 函数

### paintMasks

```cpp
void Draw::paintMasks(SkZip<const SkGlyph*, SkPoint> accepted,
                      const SkPaint& paint) const
```

绘制字形遮罩的核心函数。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `accepted` | `SkZip<const SkGlyph*, SkPoint>` | 字形指针与位置的配对列表 |
| `paint` | `const SkPaint&` | 绘制属性（颜色、混合模式等） |

**执行流程：**

1. **创建Blitter：**
   ```cpp
   SkSTArenaAlloc<kSkBlitterContextSize> alloc;
   SkBlitter* blitter = SkBlitter::Choose(fDst, *fCTM, paint, &alloc,
                                          SkDrawCoverage::kNo, ...);
   ```

2. **包装抗锯齿裁剪：**
   ```cpp
   SkAAClipBlitterWrapper wrapper{*fRC, blitter};
   blitter = wrapper.getBlitter();
   ```
   如果裁剪区域是抗锯齿的，用 `SkAAClipBlitterWrapper` 包装blitter。

3. **判断裁剪类型：**
   - **区域裁剪（`useRegion = true`）：** 使用 `SkRegion::Cliperator` 迭代裁剪矩形
   - **矩形裁剪（`useRegion = false`）：** 直接使用边界矩形裁剪

4. **迭代字形：**
   对每个字形：
   - 调用 `check_glyph_position(pos)` 验证位置有效性
   - 获取字形遮罩：`mask = glyph->mask(pos)`
   - 如果是ARGB格式，转换为sprite并调用 `drawSprite()`
   - 否则根据裁剪类型，调用 `blitter->blitMask(mask, rect)`

### drawGlyphRunList

```cpp
void Draw::drawGlyphRunList(SkCanvas* canvas,
                            GlyphRunListPainter* glyphPainter,
                            const sktext::GlyphRunList& glyphRunList,
                            const SkPaint& paint) const
```

文本绘制的入口函数，委托给 `GlyphRunPainter`。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `canvas` | `SkCanvas*` | 画布上下文（用于状态查询） |
| `glyphPainter` | `GlyphRunListPainter*` | 高层字形绘制器 |
| `glyphRunList` | `const sktext::GlyphRunList&` | 字形运行列表（已布局的文本） |
| `paint` | `const SkPaint&` | 绘制属性 |

**职责：**
- 验证裁剪区域非空（`fRC->isEmpty()`）
- 调用 `glyphPainter->drawForBitmapDevice(canvas, this, glyphRunList, paint, *fCTM)`
- `GlyphRunPainter` 负责字形选择、缓存查询、格式转换，最终回调 `paintMasks()`

## 内部实现细节

### 字形位置验证

```cpp
static bool check_glyph_position(SkPoint position)
```

防止字形被绘制到设备空间边界外或跨越边界，这会导致坐标溢出或缓冲区越界。

**验证逻辑：**
```cpp
auto gt = [](float a, int b) { return !(a <= (float)b); };
auto lt = [](float a, int b) { return !(a >= (float)b); };
return !(gt(position.fX, INT_MAX - (INT16_MAX + UINT16_MAX)) ||
         lt(position.fX, INT_MIN - (INT16_MIN + 0)) ||
         gt(position.fY, INT_MAX - (INT16_MAX + UINT16_MAX)) ||
         lt(position.fY, INT_MIN - (INT16_MIN + 0)));
```

**边界计算：**
- 字形左上角：`INT16_MIN` 到 `INT16_MAX`
- 字形尺寸：最大 `UINT16_MAX`
- 总边界：`INT_MIN - INT16_MIN` 到 `INT_MAX - INT16_MAX - UINT16_MAX`

**NaN处理：** 使用 `!(a <= b)` 而非 `a > b`，使得NaN值被安全拒绝。

### 裁剪策略

**区域裁剪（Region Clipping）：**
当裁剪区域是复杂形状（多个不连续矩形）时：
```cpp
SkRegion::Cliperator clipper(fRC->bwRgn(), mask.fBounds);
if (!clipper.done()) {
    const SkIRect& cr = clipper.rect();
    do {
        blitter->blitMask(mask, cr);
        clipper.next();
    } while (!clipper.done());
}
```
`Cliperator` 迭代所有与字形相交的裁剪矩形，每个矩形调用一次 `blitMask`。

**矩形裁剪（Rectangle Clipping）：**
当裁剪区域是单个矩形或抗锯齿裁剪时：
```cpp
SkIRect clipBounds = fRC->isBW() ? fRC->bwRgn().getBounds()
                                 : fRC->aaRgn().getBounds();
SkIRect storage;
const SkIRect* bounds = &mask.fBounds;
if (!clipBounds.containsNoEmptyCheck(mask.fBounds)) {
    if (!storage.intersect(mask.fBounds, clipBounds)) {
        continue;  // 完全在裁剪外
    }
    bounds = &storage;
}
blitter->blitMask(mask, *bounds);
```
提前计算交集，避免blitter处理完全超出裁剪的区域。

### ARGB字形处理

ARGB格式字形（彩色emoji、彩色字体）不使用遮罩blitting，而是作为sprite绘制：
```cpp
if (SkMask::kARGB32_Format == mask.fFormat) {
    SkBitmap bm;
    bm.installPixels(SkImageInfo::MakeN32Premul(mask.fBounds.size()),
                     const_cast<uint8_t*>(mask.fImage),
                     mask.fRowBytes);
    bm.setImmutable();
    this->drawSprite(bm, mask.fBounds.x(), mask.fBounds.y(), paint);
}
```
将遮罩数据包装为 `SkBitmap`，然后调用sprite绘制路径。这允许正确应用混合模式和颜色过滤器。

### 栈分配器使用

```cpp
SkSTArenaAlloc<kSkBlitterContextSize> alloc;
```
使用栈上的内存池（3332字节）分配blitter和相关上下文，避免堆分配开销。对于大多数文本绘制，这个大小足够。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkGlyph` | 字形数据结构 |
| `SkBlitter` | 像素绘制器 |
| `GlyphRunPainter` | 高层字形绘制器 |
| `SkAAClip` | 抗锯齿裁剪 |
| `SkRasterClip` | 裁剪区域管理 |
| `SkRegion` | 复杂裁剪区域 |
| `SkMask` | 字形遮罩表示 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkCanvas::drawTextBlob()` | 高层文本API |
| `GlyphRunListPainter` | 回调 `paintMasks()` |
| `SkDevice` | 设备层分发到CPU实现 |

## 设计模式与设计决策

**迭代器模式：** 使用 `SkZip` 迭代字形和位置的配对，使用 `SkRegion::Cliperator` 迭代裁剪矩形。这些迭代器隐藏了底层数据结构的复杂性。

**包装器模式：** `SkAAClipBlitterWrapper` 包装blitter，透明地添加抗锯齿裁剪支持，无需修改blitter代码。

**策略模式：** 根据裁剪类型（区域vs矩形）和字形格式（遮罩vs ARGB）选择不同的处理策略。

**提前验证：** 在绘制前检查字形位置，避免后续处理中的溢出或断言失败。

**惰性优化：** 只有在需要时才计算交集（`storage.intersect`），大多数字形完全在裁剪内，跳过计算。

**编译器优化辅助：** Windows特定的编译指示禁用未初始化变量警告（`#pragma warning`），避免误报同时保持性能。

## 性能考量

**快速路径检查：** `clipBounds.containsNoEmptyCheck(mask.fBounds)` 使用快速路径检查字形是否完全在裁剪内：
```cpp
if (!clipBounds.containsNoEmptyCheck(mask.fBounds)) {
    // 慢速路径：计算交集
}
```
大多数字形会走快速路径。

**栈分配优势：** `SkSTArenaAlloc` 避免malloc/free开销，对于大量小字形（如中文文本），性能提升显著。

**区域裁剪开销：** 复杂裁剪（多个矩形）会导致每个字形多次调用 `blitMask`，开销较大。但这是正确性所必需的。

**位置验证成本：** `check_glyph_position` 对每个字形执行，有一定开销。但相比绘制本身，开销可忽略，且避免了严重的bug。

**ARGB字形路径：** 彩色字形的sprite路径比遮罩路径慢（需要完整的混合管线），但彩色字形通常数量较少（emoji）。

**批处理绘制：** 字形以批次传递（`SkZip<...> accepted`），允许共享blitter和栈分配器，比逐个调用高效。

**内联辅助函数：** `check_glyph_position` 是 `static` 函数，编译器可以内联到调用点。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkCanvas.h` | 公共文本绘制API |
| `src/core/SkGlyph.h` | 字形数据结构 |
| `src/core/SkGlyphRunPainter.h` | 高层字形绘制器 |
| `src/core/SkBlitter.h` | Blitter接口 |
| `src/core/SkAAClip.h` | 抗锯齿裁剪 |
| `src/core/SkRasterClip.h` | 裁剪区域管理 |
| `src/core/SkDraw.h` | 绘制引擎基类 |
| `src/core/SkMask.h` | 字形遮罩定义 |
| `include/core/SkRegion.h` | 复杂区域表示 |
