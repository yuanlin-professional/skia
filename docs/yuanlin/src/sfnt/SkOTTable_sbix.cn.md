# SkOTTable_sbix

> 源文件: src/sfnt/SkOTTable_sbix.h

## 概述

`SkOTTable_sbix.h` 定义了 OpenType `sbix` (Standard Bitmap Graphics) 表的结构,用于存储彩色位图字形(如emoji表情符号)。该表支持多种图像格式(PNG、JPEG、TIFF)和多个分辨率(strikes),允许字体包含像素完美的位图表示,而非仅依赖矢量轮廓。这是 Apple 引入的彩色emoji字体技术,被 macOS 和 iOS 广泛使用。

`sbix` 表通过存储预渲染的位图图像,在小尺寸或复杂图形(如emoji)场景下提供更好的视觉效果和性能。

## 架构位置

- **模块路径**: `src/sfnt/`
- **表标签**: `'sbix'`
- **用途**: 彩色位图字形存储
- **依赖**: `SkOTTableTypes.h`, `SkUtils.h`, `SkTemplates.h`
- **被使用者**: emoji渲染、位图字形加载

## 主要类与结构体

### SkOTTableStandardBitmapGraphics (sbix 表头)

**成员**:
```cpp
SK_OT_USHORT version;        // 必须为1
SK_OT_USHORT flags;          // Bit 0: 1, Bit 1: 绘制轮廓, Bits 2-15: 保留
SK_OT_ULONG numStrikes;      // Strike(分辨率)数量
// SK_OT_ULONG strikeOffsets[numStrikes];  // Strike偏移数组
```

**方法**:
```cpp
SK_OT_ULONG strikeOffset(int strikeIndex);  // 获取Strike偏移(未对齐读取)
```

### Strike (分辨率记录)

每个Strike代表特定ppem(每em像素数)下的位图集合。

**成员**:
```cpp
SK_OT_USHORT ppem;           // 每em像素数(如64表示64×64)
SK_OT_USHORT ppi;            // 设计像素密度
// SK_OT_ULONG glyphDataOffsets[numGlyphs+1];  // 字形数据偏移
```

**方法**:
```cpp
SK_OT_ULONG glyphDataOffset(int glyphId);  // 获取字形数据偏移
```

### GlyphData (字形位图数据)

单个字形的位图数据。

**成员**:
```cpp
SK_OT_SHORT originOffsetX;   // x偏移(像素)
SK_OT_SHORT originOffsetY;   // y偏移(像素,y轴向上)
SK_OT_ULONG graphicType;     // 图像类型: 'jpg ', 'png ', 'tiff', 'dupe'
// SK_OT_BYTE data[];         // 实际图像数据
```

**方法**:
```cpp
SK_OT_BYTE* data();          // 获取图像数据指针
const SK_OT_BYTE* data() const;
```

**图像类型**:
- `'jpg '` (0x6A70 6720): JPEG图像
- `'png '` (0x706E 6720): PNG图像(最常用,支持透明)
- `'tiff'` (0x7469 6666): TIFF图像
- `'dupe'` (0x6475 7065): 引用其他字形(避免重复数据)

## 公共 API 函数

**访问示例**:
```cpp
const SkOTTableStandardBitmapGraphics* sbix = /* 读取 */;

// 遍历所有Strike(分辨率)
for (uint32_t i = 0; i < SkEndian_SwapBE32(sbix->numStrikes); ++i) {
    uint32_t strikeOff = SkEndian_SwapBE32(sbix->strikeOffset(i));
    const Strike* strike = (const Strike*)((const uint8_t*)sbix + strikeOff);

    uint16_t ppem = SkEndian_SwapBE16(strike->ppem);
    // 选择合适分辨率...

    // 获取特定字形的位图
    uint32_t glyphOff = SkEndian_SwapBE32(strike->glyphDataOffset(glyphId));
    const GlyphData* glyph = (const GlyphData*)((const uint8_t*)strike + glyphOff);

    uint32_t graphicType = SkEndian_SwapBE32(glyph->graphicType);
    if (graphicType == 'png ') {
        const uint8_t* pngData = glyph->data();
        // 解码PNG...
    }
}
```

## 内部实现细节

### 1. 未对齐读取

由于数据布局可能未对齐,使用 `sk_unaligned_load`:
```cpp
SK_OT_ULONG strikeOffset(int strikeIndex) {
    return sk_unaligned_load<SK_OT_ULONG>(
        SkTAddOffset<void*>(&numStrikes, sizeof(numStrikes) + sizeof(SK_OT_ULONG)*strikeIndex));
}
```

避免ARM等架构上的未对齐访问崩溃。

### 2. 数据布局

```
[SkOTTableStandardBitmapGraphics 表头]
[uint32_t strikeOffsets[numStrikes]]
[Strike 1]
  [uint32_t glyphDataOffsets[numGlyphs+1]]
  [GlyphData for glyph 0]
    [图像数据]
  [GlyphData for glyph 1]
    [图像数据]
  ...
[Strike 2]
  ...
```

### 3. 'dupe' 类型处理

当 `graphicType == 'dupe'` 时,data区域存储引用的glyphId:
```cpp
if (graphicType == 'dupe') {
    uint16_t referenceGlyphId = *(uint16_t*)glyph->data();
    // 使用referenceGlyphId的位图数据
}
```

节省相同图形的重复存储(如不同肤色的同一emoji)。

### 4. Strike选择策略

根据目标渲染尺寸选择最接近的Strike:
```cpp
int bestStrike = 0;
int minDiff = INT_MAX;
for (int i = 0; i < numStrikes; ++i) {
    int diff = abs((int)strike->ppem - targetSize);
    if (diff < minDiff) {
        minDiff = diff;
        bestStrike = i;
    }
}
```

避免位图缩放失真。

## 依赖关系

### 直接依赖

- `src/sfnt/SkOTTableTypes.h`: 类型定义
- `src/base/SkUtils.h`: `sk_unaligned_load`
- `include/private/base/SkTemplates.h`: `SkTAddOffset`, `SkTAfter`

### 被依赖情况

- emoji字形渲染器
- `SkTypeface`: 位图字形查询
- 图像解码器(PNG/JPEG)

## 设计模式与设计决策

### 1. 多分辨率支持

通过Strike机制支持多种ppem:
- 小尺寸优化(16×16)
- 中等尺寸(64×64)
- 高分辨率(160×160)

### 2. 多格式支持

支持PNG、JPEG、TIFF:
- PNG: 透明度支持,最常用
- JPEG: 高压缩比,照片风格emoji
- TIFF: 高质量,较少使用

### 3. 引用机制

'dupe'类型避免重复数据:
- 节省文件大小
- 快速查找引用

### 4. 坐标系

originOffsetY 使用 y轴向上坐标系:
- 与 OpenType 标准一致
- 需要转换为屏幕坐标

## 性能考量

### 1. 位图缓存

预渲染位图避免实时光栅化:
- 复杂emoji瞬时显示
- 无抗锯齿计算开销

### 2. 文件大小

多Strike和高分辨率导致大文件:
- Apple Color Emoji: 约70MB
- 使用PNG压缩减小
- 'dupe'机制共享数据

### 3. Strike查找

O(n) Strike选择:
- 通常只有3-5个Strike
- 开销可忽略

### 4. 图像解码

需要实时解码PNG/JPEG:
- 首次使用解码并缓存
- 硬件解码器加速

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkUtils.h`

### 相关表定义

- `src/sfnt/SkOTTable_CBDT.h`: 另一种彩色位图格式(Google/Microsoft)
- `src/sfnt/SkOTTable_EBLC.h`: CBDT的索引表

### 图像处理

- `src/codec/SkPngCodec.h`: PNG解码
- `src/codec/SkJpegCodec.h`: JPEG解码

该文件支持 Skia 渲染彩色emoji和位图字形,是现代操作系统emoji显示的基础设施。
