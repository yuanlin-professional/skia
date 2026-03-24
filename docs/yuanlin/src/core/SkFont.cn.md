# SkFont

> 源文件
> - include/core/SkFont.h
> - src/core/SkFont.cpp

## 概述

`SkFont` 是 Skia 中用于控制文本绘制和测量选项的核心类。它封装了字体相关的所有渲染属性,包括字体大小、字体族(typeface)、缩放、倾斜、抗锯齿模式、提示(hinting)级别等。`SkFont` 提供了丰富的 API 来测量文本尺寸、获取字形位置、转换文本到字形 ID、查询字体度量信息等功能。

与旧版的 `SkPaint` 文本 API 不同,`SkFont` 专注于字体属性,将文本渲染参数与绘制样式分离,使 API 更加清晰和高效。它是现代 Skia 文本渲染管线的基础,与 `SkTypeface`(字体族)、`SkPaint`(绘制样式)协同工作。

## 架构位置

`SkFont` 在 Skia 文本渲染管线中处于核心位置:

```
应用层
    ↓
SkCanvas::drawText/drawTextBlob
    ↓
SkFont (字体属性) + SkPaint (绘制样式)
    ↓
SkStrikeSpec (字形缓存规格)
    ↓
SkStrike (字形缓存)
    ↓
SkGlyph (字形数据)
    ↓
Blitter (像素绘制)
```

**关键交互**:
- **SkTypeface**: 提供字体族和字形数据
- **SkPaint**: 提供颜色、混合模式、特效等绘制样式
- **SkStrikeSpec**: 使用 `SkFont` 生成字形缓存的规格说明
- **SkGlyph**: 存储单个字形的度量和位图数据

## 主要类与结构体

### SkFont

**继承关系**
- 无继承关系,值类型(value type)

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTypeface` | `sk_sp<SkTypeface>` | 字体族智能指针,包含字形数据和字体表 |
| `fSize` | `SkScalar` | 字体大小(EM 单位),默认 12.0 |
| `fScaleX` | `SkScalar` | 水平缩放比例,默认 1.0(用于模拟压缩/扩展字体) |
| `fSkewX` | `SkScalar` | 水平倾斜角度,默认 0.0(用于模拟斜体) |
| `fFlags` | `uint8_t` | 标志位集合(自动提示、嵌入位图、子像素等) |
| `fEdging` | `uint8_t` | 边缘渲染模式(别名、抗锯齿、亚像素抗锯齿) |
| `fHinting` | `uint8_t` | 提示级别(None/Slight/Normal/Full) |

**枚举类型: Edging**

| 枚举值 | 说明 |
|-------|------|
| `kAlias` | 无抗锯齿,边缘像素完全不透明 |
| `kAntiAlias` | 抗锯齿,边缘像素可能半透明 |
| `kSubpixelAntiAlias` | 亚像素抗锯齿,利用 RGB 子像素提高清晰度 |

**标志位(PrivFlags)**

| 标志位 | 说明 |
|-------|------|
| `kForceAutoHinting_PrivFlag` | 强制使用 FreeType 的自动提示 |
| `kEmbeddedBitmaps_PrivFlag` | 允许使用字体中的嵌入位图 |
| `kSubpixel_PrivFlag` | 允许在子像素位置绘制字形 |
| `kLinearMetrics_PrivFlag` | 请求线性可缩放的字体度量 |
| `kEmbolden_PrivFlag` | 通过增加描边宽度模拟粗体 |
| `kBaselineSnap_PrivFlag` | 在轴对齐变换时将基线对齐到像素 |

## 公共 API 函数

### 构造函数

```cpp
SkFont();
SkFont(sk_sp<SkTypeface> typeface);
SkFont(sk_sp<SkTypeface> typeface, SkScalar size);
SkFont(sk_sp<SkTypeface> typeface, SkScalar size, SkScalar scaleX, SkScalar skewX);
```
- **功能**: 创建 `SkFont` 对象
- **默认值**:
  - `size`: 12.0
  - `scaleX`: 1.0
  - `skewX`: 0.0
  - `typeface`: 空字体(绘制时不显示任何内容)

### 属性访问器

```cpp
// Getters
SkTypeface* getTypeface() const;
sk_sp<SkTypeface> refTypeface() const;
SkScalar getSize() const;
SkScalar getScaleX() const;
SkScalar getSkewX() const;
Edging getEdging() const;
SkFontHinting getHinting() const;

// Setters
void setTypeface(sk_sp<SkTypeface> tf);
void setSize(SkScalar textSize);
void setScaleX(SkScalar scaleX);
void setSkewX(SkScalar skewX);
void setEdging(Edging edging);
void setHinting(SkFontHinting hintingLevel);
```

### 标志位访问器

```cpp
bool isForceAutoHinting() const;
bool isEmbeddedBitmaps() const;
bool isSubpixel() const;
bool isLinearMetrics() const;
bool isEmbolden() const;
bool isBaselineSnap() const;

void setForceAutoHinting(bool);
void setEmbeddedBitmaps(bool);
void setSubpixel(bool);
void setLinearMetrics(bool);
void setEmbolden(bool);
void setBaselineSnap(bool);
```

### 文本转换

```cpp
size_t textToGlyphs(const void* text, size_t byteLength, SkTextEncoding encoding,
                    SkSpan<SkGlyphID> glyphs) const;
```
- **功能**: 将文本转换为字形 ID
- **参数**:
  - `text`: 文本数据指针
  - `byteLength`: 文本字节长度
  - `encoding`: 文本编码(UTF8/UTF16/UTF32/GlyphID)
  - `glyphs`: 输出字形 ID 的缓冲区
- **返回值**: 字形数量
- **特点**: 如果 `glyphs` 为空,仅计数不输出

```cpp
SkGlyphID unicharToGlyph(SkUnichar uni) const;
void unicharsToGlyphs(SkSpan<const SkUnichar> src, SkSpan<SkGlyphID> dst) const;
size_t countText(const void* text, size_t byteLength, SkTextEncoding encoding) const;
```

### 文本测量

```cpp
SkScalar measureText(const void* text, size_t byteLength, SkTextEncoding encoding,
                     SkRect* bounds = nullptr) const;
SkScalar measureText(const void* text, size_t byteLength, SkTextEncoding encoding,
                     SkRect* bounds, const SkPaint* paint) const;
```
- **功能**: 测量文本的前进宽度和边界框
- **返回值**: 文本总前进宽度(advance width)
- **输出**: `bounds` - 文本的紧凑边界框(相对于原点)
- **注意**: 提供 `paint` 参数时会考虑描边、特效等对边界框的影响

### 字形度量

```cpp
void getWidthsBounds(SkSpan<const SkGlyphID> glyphs, SkSpan<SkScalar> widths,
                     SkSpan<SkRect> bounds, const SkPaint* paint) const;
void getWidths(SkSpan<const SkGlyphID> glyphs, SkSpan<SkScalar> widths) const;
SkScalar getWidth(SkGlyphID glyph) const;
void getBounds(SkSpan<const SkGlyphID> glyphs, SkSpan<SkRect> bounds,
               const SkPaint* paint) const;
SkRect getBounds(SkGlyphID glyph, const SkPaint* paint) const;
```
- **功能**: 获取字形的前进宽度和边界框
- **批量处理**: 一次性获取多个字形的度量数据,提高效率

### 字形定位

```cpp
void getPos(SkSpan<const SkGlyphID> glyphs, SkSpan<SkPoint> pos,
            SkPoint origin = {0, 0}) const;
void getXPos(SkSpan<const SkGlyphID> glyphs, SkSpan<SkScalar> xpos,
             SkScalar origin = 0) const;
```
- **功能**: 计算字形的绘制位置
- **用途**: 为文本布局生成字形位置数组

### 路径提取

```cpp
std::optional<SkPath> getPath(SkGlyphID glyphID) const;
void getPaths(SkSpan<const SkGlyphID> glyphIDs,
              void (*glyphPathProc)(const SkPath* pathOrNull, const SkMatrix& mx, void* ctx),
              void* ctx) const;
```
- **功能**: 获取字形的轮廓路径
- **返回值**:
  - `getPath`: 返回 `std::optional<SkPath>`,位图字形返回空
  - `getPaths`: 通过回调函数返回每个字形的路径
- **矩阵**: 路径已应用字体大小的缩放变换

### 字体度量

```cpp
SkScalar getMetrics(SkFontMetrics* metrics) const;
SkScalar getSpacing() const;
```
- **功能**: 获取字体的度量信息
- **返回值**: 推荐的行间距(descent + ascent + leading)
- **输出**: `metrics` - 包含上升、下降、行距、X 高度等信息

### 线段相交

```cpp
std::vector<SkScalar> getIntercepts(SkSpan<const SkGlyphID> glyphs,
                                    SkSpan<const SkPoint> pos,
                                    SkScalar top, SkScalar bottom,
                                    const SkPaint* = nullptr) const;
```
- **功能**: 计算字形与水平线段的相交区间
- **用途**: 实现文本装饰效果(如删除线、下划线)

### 工具函数

```cpp
SkFont makeWithSize(SkScalar size) const;
void dump() const;
bool operator==(const SkFont& font) const;
bool operator!=(const SkFont& font) const;
```

## 内部实现细节

### 规范化处理

所有测量和渲染操作都通过 `SkStrikeSpec` 进行规范化:

```cpp
auto [strikeSpec, strikeToSourceScale] = SkStrikeSpec::MakeCanonicalized(*this, paint);
```

**规范化目的**:
- 将字体参数转换为标准形式,提高缓存命中率
- 处理极端的 `scaleX` 和 `skewX` 值
- 考虑 `SkPaint` 的特效对字形的影响

**缩放因子** (`strikeToSourceScale`):
- 表示规范化后的缓存字形与原始字体尺寸的比例
- 用于将缓存字形的度量值还原到实际尺寸

### 路径模式设置

当需要获取字形路径时,字体会切换到路径模式:

```cpp
SkScalar SkFont::setupForAsPaths(SkPaint* paint) {
    // 1. 禁用嵌入位图和强制自动提示
    fFlags = (fFlags & ~flagsToIgnore) | kSubpixel_PrivFlag;

    // 2. 禁用提示
    this->setHinting(SkFontHinting::kNone);

    // 3. 降级亚像素抗锯齿到普通抗锯齿
    if (this->getEdging() == Edging::kSubpixelAntiAlias) {
        this->setEdging(Edging::kAntiAlias);
    }

    // 4. 设置规范化大小
    SkScalar textSize = fSize;
    this->setSize(SkIntToScalar(SkFontPriv::kCanonicalTextSizeForPaths));

    return textSize / SkFontPriv::kCanonicalTextSizeForPaths;
}
```

**规范化大小**: `kCanonicalTextSizeForPaths` 通常为 2048,匹配字体设计单位。

### 文本测量实现

```cpp
SkScalar SkFont::measureText(const void* text, size_t length, SkTextEncoding encoding,
                             SkRect* bounds, const SkPaint* paint) const {
    // 1. 转换文本到字形 ID
    SkAutoToGlyphs atg(*this, text, length, encoding);

    // 2. 获取规范化的 strike spec
    auto [strikeSpec, strikeToSourceScale] = SkStrikeSpec::MakeCanonicalized(*this, paint);

    // 3. 从字形缓存获取度量数据
    SkBulkGlyphMetrics metrics{strikeSpec};
    SkSpan<const SkGlyph*> glyphs = metrics.glyphs(glyphIDs);

    // 4. 累加前进宽度和计算边界框
    SkScalar width = 0;
    if (bounds) {
        *bounds = glyphs[0]->rect();
        width = glyphs[0]->advanceX();
        for (size_t i = 1; i < glyphIDs.size(); ++i) {
            SkRect r = glyphs[i]->rect();
            r.offset(width, 0);
            bounds->join(r);
            width += glyphs[i]->advanceX();
        }
    } else {
        for (auto glyph : glyphs) {
            width += glyph->advanceX();
        }
    }

    // 5. 还原到实际尺寸
    width *= strikeToSourceScale;
    if (bounds) {
        *bounds = scale_rect(*bounds, strikeToSourceScale);
    }

    return width;
}
```

### 字形批量处理

使用 `SkBulkGlyphMetrics` 和 `SkBulkGlyphMetricsAndPaths` 批量获取字形数据:

```cpp
SkBulkGlyphMetrics metrics{strikeSpec};
SkSpan<const SkGlyph*> glyphs = metrics.glyphs(glyphIDs);
```

**优势**:
- 减少缓存查找次数
- 提高缓存局部性
- 支持预取优化

### 字体度量缩放

```cpp
void SkFontPriv::ScaleFontMetrics(SkFontMetrics* metrics, SkScalar scale) {
    metrics->fTop *= scale;
    metrics->fAscent *= scale;
    metrics->fDescent *= scale;
    metrics->fBottom *= scale;
    metrics->fLeading *= scale;
    metrics->fAvgCharWidth *= scale;
    metrics->fMaxCharWidth *= scale;
    metrics->fXMin *= scale;
    metrics->fXMax *= scale;
    metrics->fXHeight *= scale;
    metrics->fCapHeight *= scale;
    metrics->fUnderlineThickness *= scale;
    metrics->fUnderlinePosition *= scale;
    metrics->fStrikeoutThickness *= scale;
    metrics->fStrikeoutPosition *= scale;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkTypeface` | 提供字形数据和字体表 |
| `SkPaint` | 提供绘制样式(可选) |
| `SkStrikeSpec` | 生成字形缓存规格 |
| `SkStrike` | 字形缓存 |
| `SkGlyph` | 单个字形的度量和位图数据 |
| `SkPath` | 字形轮廓路径 |
| `SkMatrix` | 变换矩阵 |
| `SkFontMetrics` | 字体度量数据结构 |
| `SkUTF` | UTF 编码转换 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkCanvas` | 使用 `SkFont` 绘制文本 |
| `SkTextBlob` | 存储字体和字形布局信息 |
| `SkShaper` | 使用 `SkFont` 进行文本整形 |
| `SkParagraph` | 段落排版中使用 `SkFont` |
| `GlyphRunListPainter` | 光栅化管线使用 `SkFont` |

## 设计模式与设计决策

### 值语义设计

`SkFont` 采用值语义而非引用计数:

```cpp
SkFont font1;
SkFont font2 = font1;  // 拷贝,不是共享
font2.setSize(20);     // 不影响 font1
```

**优势**:
- 避免意外的状态共享
- 简化生命周期管理
- 支持高效的栈分配

**实现**: 使用 `sk_is_trivially_relocatable` 标记,支持高效移动

### 与 SkPaint 的关系

旧版 Skia 将文本属性放在 `SkPaint` 中,新版将其分离到 `SkFont`:

```cpp
// 旧 API (已弃用)
paint.setTextSize(20);
canvas.drawText(..., paint);

// 新 API
SkFont font;
font.setSize(20);
canvas.drawText(..., font, paint);
```

**设计理由**:
- **职责分离**: 字体属性 vs 绘制样式
- **性能优化**: 字体缓存键不需要考虑颜色、混合模式等
- **API 清晰**: 更符合直觉的参数组织

### 默认值选择

```cpp
#define kDefault_Size       SkPaintDefaults_TextSize  // 12.0
#define kDefault_Flags      SkFont::kBaselineSnap_PrivFlag
#define kDefault_Edging     SkFont::Edging::kAntiAlias
#define kDefault_Hinting    SkPaintDefaults_Hinting
```

**设计决策**:
- **默认大小 12**: 平衡可读性和性能
- **默认抗锯齿**: 现代显示器标准配置
- **基线对齐**: 提高文本清晰度

### 尺寸验证

```cpp
static inline SkScalar valid_size(SkScalar size) {
    return std::max<SkScalar>(0, size);
}
```
- 负数大小被钳制为 0
- NaN 和无穷大通过比较被转换为 0
- 保证字体大小永远非负

## 性能考量

### 字形缓存优化

1. **规范化**: 将不同的 `SkFont` 映射到相同的缓存条目
2. **批量查询**: 使用 `SkBulkGlyphMetrics` 减少缓存查找
3. **Strike 重用**: 相同参数的字体共享 strike 缓存

### 内联属性访问

大多数 getter 函数都是内联的:
```cpp
SkScalar getSize() const { return fSize; }
SkScalar getScaleX() const { return fScaleX; }
```
- 零函数调用开销
- 编译器优化友好

### 避免不必要的转换

```cpp
size_t countText(const void* text, size_t byteLength, SkTextEncoding encoding) const {
    return this->textToGlyphs(text, byteLength, encoding, {});
}
```
- 复用 `textToGlyphs`,传递空 span 仅计数
- 避免重复的编码解析

### 位置计算优化

```cpp
void SkFont::getXPos(SkSpan<const SkGlyphID> gIDs, SkSpan<SkScalar> xpos,
                     SkScalar origin) const {
    SkScalar loc = origin;
    for (auto [xposition, glyph] : SkMakeZip(xpos.first(n), glyphs.first(n))) {
        xposition = loc;
        loc += glyph->advanceX() * strikeToSourceScale;
    }
}
```
- 使用 `SkMakeZip` 高效遍历
- 单次缓存查询获取所有字形

### 路径缓存

字形路径存储在 `SkGlyph` 中,首次访问后缓存:
```cpp
const SkPath* SkGlyph::path() const {
    if (!fPathData) {
        // 从 typeface 加载路径并缓存
    }
    return fPathData->fPath;
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkTypeface.h` | 依赖 | 字体族接口 |
| `include/core/SkPaint.h` | 协作 | 绘制样式 |
| `include/core/SkFontMetrics.h` | 数据结构 | 字体度量信息 |
| `include/core/SkFontTypes.h` | 枚举 | 字体相关枚举(提示、编码等) |
| `src/core/SkStrikeSpec.h` | 依赖 | 字形缓存规格 |
| `src/core/SkStrike.h` | 依赖 | 字形缓存实现 |
| `src/core/SkGlyph.h` | 依赖 | 字形数据结构 |
| `src/core/SkFontPriv.h` | 内部辅助 | 字体私有辅助函数 |
| `include/core/SkCanvas.h` | 使用者 | 画布文本绘制接口 |
| `src/core/SkTextBlob.h` | 使用者 | 文本 blob 数据结构 |
