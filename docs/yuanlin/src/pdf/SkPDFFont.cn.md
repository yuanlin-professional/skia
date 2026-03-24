# SkPDFFont (PDF 字体)

> 源文件:
> - `src/pdf/SkPDFFont.h`
> - `src/pdf/SkPDFFont.cpp`

## 概述

`SkPDFFont` 模块实现了 Skia PDF 生成器的字体管理系统。它负责将 Skia 的字体和字形（glyph）信息转换为 PDF 规范要求的字体对象。该模块包含三个核心类：`SkPDFStrikeSpec`（PDF 字形规格）、`SkPDFStrike`（PDF 字形打击集，管理字形到字体资源的映射）和 `SkPDFFont`（单个 PDF 字体资源）。源文件超过 1100 行，处理了字体嵌入、字形子集化、Unicode 映射、以及多种字体类型（Type1, TrueType, CFF, CID）的生成。

## 架构位置

```
SkPDFDevice (绘制层)
  |
  |-- SkPDFStrike::Make() (获取/创建 Strike)
  |     |
  |     |-- SkPDFStrike::getFontResource() (获取字体资源)
  |           |
  |           v
  |       SkPDFFont (字体对象)
  |         |-- emitSubset() (生成 PDF 字体子集)
  |               |-- Type1Font / TrueType / CFF 具体实现
  |
  v
SkPDFDocument (文档输出)
```

## 主要类与结构体

### `SkPDFStrikeSpec`

封装了字形规格（`SkStrikeSpec`）和 em-unit 尺寸，用于创建和缓存字形打击集。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStrikeSpec` | `SkStrikeSpec` | 字形查找规格 |
| `fUnitsPerEM` | `SkScalar` | 每 em 单位数 |

### `SkPDFStrike`

字形打击集，管理一组字体资源。继承自 `SkRefCnt`，由 `SkPDFDocument` 拥有。

**关键成员：**
- `fPath` / `fImage` -- 路径模式和图像模式的 StrikeSpec
- `fHasMaskFilter` -- 是否有遮罩滤镜
- `fFontMap` -- 字形 ID 到 `SkPDFFont` 的映射
- `fDoc` -- 所属的 PDF 文档

**关键方法：**
- `Make(doc, font, paint)` -- 工厂方法，创建或查找已有的 Strike
- `getFontResource(glyph)` -- 获取字形对应的字体资源

### `SkPDFFont`

PDF 字体对象，由 `SkPDFStrike` 拥有。

**关键成员：**
- `fStrike` -- 所属的 Strike
- `fGlyphUsage` -- 字形使用记录
- `fIndirectReference` -- PDF 间接引用
- `fFontType` -- 字体类型（Type1, TrueType, CFF 等）

## 公共 API 函数

### 字体类型判断

- **`getType()`** -- 返回字体类型（`SkAdvancedTypefaceMetrics::FontType`）
- **`FontType(strike, metrics)`** -- 静态方法，根据 Strike 和元数据确定字体类型
- **`IsMultiByte(type)`** -- 判断字体编码是否支持超过 255 的字形 ID
- **`multiByteGlyphs()`** -- 当前字体是否为多字节编码
- **`CanEmbedTypeface(typeface, doc)`** -- 检查字体是否允许嵌入

### 字形操作

- **`hasGlyph(gid)`** -- 检查字体是否编码了该字形
- **`glyphToPDFFontEncoding(gid)`** -- 将字形 ID 转换为 PDF 字体编码
- **`noteGlyphUsage(glyph)`** -- 记录字形使用
- **`firstGlyphID()` / `lastGlyphID()`** -- 字体编码的字形 ID 范围

### 字体元数据

- **`GetMetrics(typeface, canon)`** -- 获取并缓存字体的高级排版元数据
- **`GetUnicodeMap(typeface, canon)`** -- 获取字形到 Unicode 的映射
- **`GetUnicodeMapEx(typeface, canon)`** -- 获取扩展的字形到 Unicode 映射
- **`GetType1GlyphNames(typeface, dst)`** -- 获取 Type1 字体的字形名称
- **`PopulateCommonFontDescriptor(descriptor, metrics, emSize, defaultWidth)`** -- 填充通用字体描述符

### 字体输出

- **`emitSubset(doc)`** -- 将字体子集输出到 PDF 文档

## 内部实现细节

### Strike 缓存与规范化

`SkPDFStrike::Make()` 对字体进行大量规范化处理：
- 禁用基线对齐、嵌入位图、强制自动微调
- 设置抗锯齿模式、线性度量
- 重置缩放和倾斜（由 SkPDFDevice 应用）
- 将画笔效果（模糊、虚线）按比例缩放到 em 尺寸

规范化后的 Strike 通过 descriptor 进行缓存查找。

### 字体类型分流

不同字体类型在 `emitSubset()` 中分流到不同的处理路径：
- Type1 -> `SkPDFEmitType1Font`
- TrueType -> TrueType 子集化和 CID 字体
- CFF -> CFF 子集化和 CID 字体

### 字体类型确定

`FontType()` 静态方法根据 Strike 和字体元数据确定 PDF 字体类型：
- 如果字体数据不可用或不可嵌入，可能退化为路径字形或位图字形
- Type1 字体保持原始格式
- TrueType 和 CFF 字体使用 CID 编码以支持超过 255 个字形

### 多字节编码

PDF 字体分为两类编码方案：
- **单字节**：Type1 字体，每个字体资源最多 255 个字形
- **多字节**：CID 字体（Type1CID, TrueType, CFF），支持 65536 个字形

对于单字节字体，`glyphToPDFFontEncoding()` 将字形 ID 偏移到 `[1, 255]` 范围。

### 字形子集化

PDF 字体只包含实际使用的字形子集。`fGlyphUsage` 记录了所有被使用的字形 ID，在 `emitSubset()` 时只嵌入这些字形的数据。

### 画笔效果缩放

`scale_paint()` 将画笔的遮罩滤镜（如模糊）和路径效果（如虚线）按字体大小比例缩放，使得字形路径可以在 em 尺寸空间中正确渲染。

### 图像字形

对于无法用路径表示的字形（如彩色 emoji），使用位图表示。`fImage` StrikeSpec 用于生成适当分辨率的字形图像。

## 依赖关系

**内部依赖：**
- `SkPDFTypes` -- PDF 基础类型（Dict, Array, Ref）
- `SkPDFGlyphUse` -- 字形使用记录
- `SkPDFDocumentPriv` -- 文档内部接口
- `SkPDFMakeToUnicodeCmap` -- ToUnicode CMap 生成
- `SkPDFMakeCIDGlyphWidthsArray` -- CID 字形宽度数组
- `SkPDFSubsetFont` -- 字体子集化
- `SkPDFType1Font` -- Type1 字体处理
- `SkAdvancedTypefaceMetrics` -- 字体元数据
- `SkStrikeSpec` -- 字形查找规格

**外部依赖：**
- `SkTypeface`, `SkFont`, `SkPaint` -- Skia 字体和绘制
- `SkGlyph`, `SkStrike` -- 字形处理
- `SkTHash` -- 哈希容器

## 设计模式与设计决策

1. **Strike 模式**：借鉴 Skia 的 Strike 缓存机制，将相同字体参数的字形请求聚合到同一个 Strike 中，实现资源去重。

2. **两种 StrikeSpec**：路径模式（全分辨率，用于向量字形）和图像模式（固定分辨率，用于位图字形）分开管理，允许不同的质量/尺寸权衡。

3. **延迟子集化**：字形使用记录在绘制过程中积累，直到文档完成时才进行字体子集化和输出。这确保只嵌入实际使用的字形。

4. **Type1 字体 255 限制**：Type1 字体单个资源最多支持 255 个字形。当字形数超出时，创建多个字体资源，每个覆盖不同的字形 ID 范围。

## 性能考量

- **Strike 缓存**：相同字体参数的多次请求复用同一 Strike，避免重复创建。
- **字形子集化**：只嵌入使用过的字形，显著减小 PDF 文件大小。
- **元数据缓存**：`GetMetrics` 和 `GetUnicodeMap` 的结果被缓存在文档中。
- **字体描述符共享**：同一 typeface 的不同 SkPDFFont 共享字体描述符。

## 相关文件

- `src/pdf/SkPDFType1Font.h` -- Type1 字体处理
- `src/pdf/SkPDFMakeToUnicodeCmap.h` -- ToUnicode CMap 生成
- `src/pdf/SkPDFMakeCIDGlyphWidthsArray.h` -- CID 字形宽度数组
- `src/pdf/SkPDFSubsetFont.h` -- 字体子集化
- `src/pdf/SkPDFGlyphUse.h` -- 字形使用记录
- `src/pdf/SkPDFTypes.h` -- PDF 基础类型
- `src/pdf/SkPDFDocumentPriv.h` -- 文档内部接口（缓存管理）
- `src/pdf/SkPDFDevice.h` -- 绘制设备（字体请求入口）
- `src/pdf/SkPDFBitmap.h` -- 位图（图像字形）
- `src/pdf/SkPDFFormXObject.h` -- Form XObject（复杂字形）
- `src/pdf/SkPDFGraphicState.h` -- 图形状态
- `src/core/SkAdvancedTypefaceMetrics.h` -- 字体元数据
- `src/core/SkStrikeSpec.h` -- 字形查找规格
- `src/core/SkGlyph.h` -- 字形数据
