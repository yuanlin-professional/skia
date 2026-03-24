# SkOTTableEmbeddedBitmapData

> 源文件: src/sfnt/SkOTTable_EBDT.h

## 概述

`SkOTTable_EBDT.h` 定义了 OpenType 字体中的 EBDT (Embedded Bitmap Data) 表结构。EBDT 表存储实际的嵌入式位图字形数据,与 EBLC (Embedded Bitmap Location) 表配合使用。EBLC 提供索引和位置信息,而 EBDT 存储实际的位图图像数据。该表支持多种位图格式和度量类型,适用于特定尺寸下的预渲染字形显示。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTableTypes.h (基础类型)
    ├── SkOTTable_head.h (字体头表)
    ├── SkOTTable_loca.h (位置表)
    ├── SkOTTable_EBLC.h (位图位置索引)
    └── SkOTTable_EBDT.h (位图数据) ←
```

## 主要类与结构体

### SkOTTableEmbeddedBitmapData (主结构)

```cpp
struct SkOTTableEmbeddedBitmapData {
    static const SK_OT_CHAR TAG0 = 'E';
    static const SK_OT_CHAR TAG1 = 'B';
    static const SK_OT_CHAR TAG2 = 'D';
    static const SK_OT_CHAR TAG3 = 'T';
    static const SK_OT_ULONG TAG = SkOTTableTAG<...>::value;

    SK_OT_Fixed version;  // 版本 2.0
    static const SK_OT_Fixed version_initial = SkTEndian_SwapBE32(0x00020000);
};
```

### BigGlyphMetrics (大字形度量)

```cpp
struct BigGlyphMetrics {
    SK_OT_BYTE height;        // 字形高度
    SK_OT_BYTE width;         // 字形宽度
    SK_OT_CHAR horiBearingX;  // 水平方向 X 轴承距
    SK_OT_CHAR horiBearingY;  // 水平方向 Y 轴承距
    SK_OT_BYTE horiAdvance;   // 水平前进宽度
    SK_OT_CHAR vertBearingX;  // 垂直方向 X 轴承距
    SK_OT_CHAR vertBearingY;  // 垂直方向 Y 轴承距
    SK_OT_BYTE vertAdvance;   // 垂直前进宽度
};
```

**用途**: 提供完整的水平和垂直布局度量信息

### SmallGlyphMetrics (小字形度量)

```cpp
struct SmallGlyphMetrics {
    SK_OT_BYTE height;   // 字形高度
    SK_OT_BYTE width;    // 字形宽度
    SK_OT_CHAR bearingX; // X 轴承距
    SK_OT_CHAR bearingY; // Y 轴承距
    SK_OT_BYTE advance;  // 前进宽度
};
```

**用途**: 节省空间的简化度量,仅支持单一方向

## 位图格式

### Format 1 (小度量 + 字节对齐)

```cpp
struct Format1 {
    SmallGlyphMetrics smallGlyphMetrics;
    // SK_OT_BYTE[] byteAlignedBitmap;
};
```

**特点**: 每行字节对齐,便于处理

### Format 2 (小度量 + 位对齐)

```cpp
struct Format2 {
    SmallGlyphMetrics smallGlyphMetrics;
    // SK_OT_BYTE[] bitAlignedBitmap;
};
```

**特点**: 位紧凑排列,节省空间

### Format 4 (Mac 专用压缩格式)

```cpp
struct Format4 {
    SK_OT_ULONG whiteTreeOffset;  // 白色像素树偏移
    SK_OT_ULONG blackTreeOffset;  // 黑色像素树偏移
    SK_OT_ULONG glyphDataOffset;  // 字形数据偏移
};
```

**说明**: 使用二叉树压缩,仅在 Mac 上使用

### Format 5 (EBLC 度量 + 位对齐)

```cpp
struct Format5 {
    // SK_OT_BYTE[] bitAlignedBitmap;
};
```

**特点**: 度量信息在 EBLC 中,数据紧凑

### Format 6 (大度量 + 字节对齐)

```cpp
struct Format6 {
    BigGlyphMetrics bigGlyphMetrics;
    // SK_OT_BYTE[] byteAlignedBitmap;
};
```

**用途**: 支持复杂字形的完整度量

### Format 7 (大度量 + 位对齐)

```cpp
struct Format7 {
    BigGlyphMetrics bigGlyphMetrics;
    // SK_OT_BYTE[] bitAlignedBitmap;
};
```

**组合**: 完整度量 + 紧凑存储

## 复合字形格式

### EBDTComponent (复合组件)

```cpp
struct EBDTComponent {
    SK_OT_USHORT glyphCode; // 组件字形码
    SK_OT_CHAR xOffset;     // X 偏移
    SK_OT_CHAR yOffset;     // Y 偏移
};
```

### Format 8 (小度量复合字形)

```cpp
struct Format8 {
    SmallGlyphMetrics smallMetrics;
    SK_OT_BYTE pad;
    SK_OT_USHORT numComponents;
    // EBDTComponent componentArray[numComponents];
};
```

### Format 9 (大度量复合字形)

```cpp
struct Format9 {
    BigGlyphMetrics bigMetrics;
    SK_OT_USHORT numComponents;
    // EBDTComponent componentArray[numComponents];
};
```

**用途**: 通过组合已有字形构建新字形,节省存储空间

## 公共 API 函数

该文件为纯数据结构定义,使用方式:

```cpp
// 1. 从 EBLC 获取偏移量
const SkOTTableEmbeddedBitmapLocation* eblc = ...;
uint32_t imageDataOffset = SkEndian_SwapBE32(
    indexSubTable->header.imageDataOffset);

// 2. 访问 EBDT 数据
const SkOTTableEmbeddedBitmapData* ebdt = ...;
const uint8_t* ebdtBase = reinterpret_cast<const uint8_t*>(ebdt);
const void* glyphData = ebdtBase + imageDataOffset;

// 3. 根据格式解析数据
switch (imageFormat) {
    case 1: {
        const auto* fmt1 = reinterpret_cast<const Format1*>(glyphData);
        // 处理字节对齐位图
        break;
    }
    case 6: {
        const auto* fmt6 = reinterpret_cast<const Format6*>(glyphData);
        // 使用 bigGlyphMetrics
        break;
    }
}
```

## 内部实现细节

### 内存布局

使用 `#pragma pack(push, 1)` 确保紧凑排列,与字体文件二进制格式精确对应。

### 格式选择策略

- **Format 1/2/6/7**: 独立字形,包含度量
- **Format 5**: 共享度量(在 EBLC 中),最紧凑
- **Format 4**: Mac 专用压缩
- **Format 8/9**: 复合字形,重用现有字形

### 位图数据编码

1. **字节对齐** (Format 1/6): 每行从新字节开始
2. **位对齐** (Format 2/5/7): 位紧密排列,需要位操作解码
3. **压缩** (Format 4): 二叉树编码,需要专门解码器

## 依赖关系

```
SkOTTable_EBDT.h
├── src/base/SkEndian.h (字节序)
├── src/sfnt/SkOTTableTypes.h (基础类型)
├── src/sfnt/SkOTTable_head.h (字体头)
└── src/sfnt/SkOTTable_loca.h (位置表)
```

**协作关系**:
- **EBLC 表**: 提供索引和偏移量
- **EBDT 表**: 存储实际位图数据

## 设计模式与设计决策

### 1. 格式多样性

9种格式适应不同需求:
- 简单 vs 复杂度量
- 空间效率 vs 访问速度
- 独立 vs 复合字形

### 2. 度量分离

- **嵌入度量** (Format 1/2/6/7/8/9): 自包含
- **外部度量** (Format 5): 节省重复数据

### 3. 复合字形

Format 8/9 支持字形重用:
- 减少存储空间
- 便于维护一致性
- 支持变体字形

## 性能考量

### 访问模式

```
查找字形位图:
EBLC 索引 → 获取偏移 → EBDT 数据 → 解码位图
```

### 解码开销

- **字节对齐**: 直接访问,零开销
- **位对齐**: 需要位操作,轻微开销
- **压缩格式**: 需要解码算法,较大开销

### 缓存策略

- 缓存解码后的位图
- 避免重复解码
- 按需加载

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_EBLC.h` | 位图位置表 | 提供索引和偏移 |
| `src/sfnt/SkOTTable_EBSC.h` | 位图缩放表 | 尺寸匹配策略 |
| `src/sfnt/SkOTTableTypes.h` | 基础类型 | 类型定义 |
| `src/core/SkScalerContext.h` | 字形缩放 | 使用位图数据 |

EBDT 表是 OpenType 位图字体的数据存储核心,通过多种格式支持灵活高效的位图字形存储和访问。
