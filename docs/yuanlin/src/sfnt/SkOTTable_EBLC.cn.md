# SkOTTableEmbeddedBitmapLocation

> 源文件: src/sfnt/SkOTTable_EBLC.h

## 概述

`SkOTTable_EBLC.h` 定义了 OpenType 字体中的 EBLC (Embedded Bitmap Location) 表格结构。EBLC 表用于存储嵌入式位图字形的位置信息和度量数据,与 EBDT (Embedded Bitmap Data) 表配合使用,实现位图字体的高效存储和访问。

该表格主要用于在特定尺寸下提供预渲染的位图字形,常见于东亚字体和小尺寸字体显示。通过索引结构,系统可以快速定位特定字形的位图数据而无需遍历整个表格。

## 架构位置

```
Skia 字体系统
└── src/sfnt/ (OpenType/TrueType 字体支持)
    ├── SkOTTableTypes.h (基础类型定义)
    ├── SkOTTable_EBLC.h (位图位置表) ←
    └── SkOTTable_EBDT.h (位图数据表)
```

**定位**:
- **模块**: 字体表格解析层
- **功能**: 位图字形索引和定位
- **配合**: 与 EBDT 表协同工作

## 主要类与结构体

### SkOTTableEmbeddedBitmapLocation (主结构)

```cpp
struct SkOTTableEmbeddedBitmapLocation {
    static const SK_OT_CHAR TAG0 = 'E';
    static const SK_OT_CHAR TAG1 = 'B';
    static const SK_OT_CHAR TAG2 = 'L';
    static const SK_OT_CHAR TAG3 = 'C';

    SK_OT_Fixed version;  // 版本号 (2.0)
    SK_OT_ULONG numSizes; // 尺寸数量
};
```

**关键字段**:
- `version`: 当前版本为 0x00020000 (2.0)
- `numSizes`: 后续 BitmapSizeTable 数组的元素数量

### SbitLineMetrics (行度量)

```cpp
struct SbitLineMetrics {
    SK_OT_CHAR ascender;            // 上升高度
    SK_OT_CHAR descender;           // 下降高度
    SK_OT_BYTE widthMax;            // 最大宽度
    SK_OT_CHAR caretSlopeNumerator; // 光标斜率分子
    SK_OT_CHAR caretSlopeDenominator; // 光标斜率分母
    SK_OT_CHAR caretOffset;         // 光标偏移
    SK_OT_CHAR minOriginSB;         // 最小原点边距
    SK_OT_CHAR minAdvanceSB;        // 最小前进边距
    SK_OT_CHAR maxBeforeBL;         // 基线前最大值
    SK_OT_CHAR minAfterBL;          // 基线后最小值
    SK_OT_CHAR pad1;                // 填充字节
    SK_OT_CHAR pad2;                // 填充字节
};
```

**用途**: 描述文本渲染的垂直和水平度量信息

### BitmapSizeTable (尺寸表)

```cpp
struct BitmapSizeTable {
    SK_OT_ULONG indexSubTableArrayOffset; // 子表数组偏移
    SK_OT_ULONG indexTablesSize;          // 索引表大小
    SK_OT_ULONG numberOfIndexSubTables;   // 子表数量
    SK_OT_ULONG colorRef;                 // 颜色参考(未使用)
    SbitLineMetrics hori;                 // 水平度量
    SbitLineMetrics vert;                 // 垂直度量
    SK_OT_USHORT startGlyphIndex;         // 起始字形索引
    SK_OT_USHORT endGlyphIndex;           // 结束字形索引
    SK_OT_BYTE ppemX;                     // 水平像素/EM
    SK_OT_BYTE ppemY;                     // 垂直像素/EM
    BitDepth bitDepth;                    // 位深度
    Flags flags;                          // 标志位
};
```

**核心功能**: 为特定尺寸的位图定义索引信息和度量属性

### BitDepth (位深度枚举)

```cpp
struct BitDepth {
    enum Value : SK_OT_BYTE {
        BW = 1,       // 黑白 (1 bpp)
        Gray4 = 2,    // 4级灰度 (2 bpp)
        Gray16 = 4,   // 16级灰度 (4 bpp)
        Gray256 = 8,  // 256级灰度 (8 bpp)
    };
    SK_OT_BYTE value;
};
```

**说明**: 支持 Microsoft 光栅器 v.1.7 及更高版本

### IndexSubTableArray (索引子表数组)

```cpp
struct IndexSubTableArray {
    SK_OT_USHORT firstGlyphIndex;  // 范围首字形
    SK_OT_USHORT lastGlyphIndex;   // 范围末字形(含)
    SK_OT_ULONG additionalOffsetToIndexSubtable; // 子表偏移
};
```

**用途**: 将字形范围映射到索引子表

### IndexSubHeader (子表头)

```cpp
struct IndexSubHeader {
    SK_OT_USHORT indexFormat;    // 索引格式
    SK_OT_USHORT imageFormat;    // 图像格式(EBDT)
    SK_OT_ULONG imageDataOffset; // 图像数据偏移
};
```

## 索引子表格式

### IndexSubTable1 (变长度量,4字节偏移)

```cpp
struct IndexSubTable1 {
    IndexSubHeader header;
    // SK_OT_ULONG offsetArray[lastGlyphIndex - firstGlyphIndex + 1 + 1];
};
```

**特点**: 每个字形有独立的偏移量,适合度量差异大的字形集

### IndexSubTable2 (相同度量)

```cpp
struct IndexSubTable2 {
    IndexSubHeader header;
    SK_OT_ULONG imageSize; // 所有字形大小相同
    SkOTTableEmbeddedBitmapData::BigGlyphMetrics bigMetrics;
};
```

**优化**: 所有字形共享相同度量和大小,节省空间

### IndexSubTable3 (变长度量,2字节偏移)

```cpp
struct IndexSubTable3 {
    IndexSubHeader header;
    // SK_OT_USHORT offsetArray[lastGlyphIndex - firstGlyphIndex + 1 + 1];
};
```

**适用场景**: 偏移量较小时使用2字节偏移节省空间

### IndexSubTable4 (稀疏字形码)

```cpp
struct IndexSubTable4 {
    IndexSubHeader header;
    SK_OT_ULONG numGlyphs;
    struct CodeOffsetPair {
        SK_OT_USHORT glyphCode; // 字形码
        SK_OT_USHORT offset;    // 偏移量
    }; // glyphArray[numGlyphs+1]
};
```

**用途**: 处理字形索引不连续的情况

### IndexSubTable5 (稀疏字形码,固定度量)

```cpp
struct IndexSubTable5 {
    IndexSubHeader header;
    SK_OT_ULONG imageSize; // 所有字形大小相同
    SkOTTableEmbeddedBitmapData::BigGlyphMetrics bigMetrics;
    SK_OT_ULONG numGlyphs;
    // SK_OT_USHORT glyphCodeArray[numGlyphs]
};
```

**组合优势**: 结合稀疏存储和固定度量的优点

## 公共 API 函数

该文件是纯数据结构定义,不提供函数接口。使用方式:

1. **读取表格头**:
```cpp
const SkOTTableEmbeddedBitmapLocation* eblc =
    font->getTableData<SkOTTableEmbeddedBitmapLocation>(TAG);
```

2. **遍历尺寸表**:
```cpp
const BitmapSizeTable* sizeTable =
    reinterpret_cast<const BitmapSizeTable*>(eblc + 1);
for (uint32_t i = 0; i < SkEndian_SwapBE32(eblc->numSizes); ++i) {
    // 处理 sizeTable[i]
}
```

3. **访问索引子表**:
```cpp
const IndexSubTableArray* subArray =
    reinterpret_cast<const IndexSubTableArray*>(
        reinterpret_cast<const uint8_t*>(eblc) +
        SkEndian_SwapBE32(sizeTable->indexSubTableArrayOffset));
```

## 内部实现细节

### 内存布局

使用 `#pragma pack(push, 1)` 确保结构体紧凑排列,无填充字节:
- 直接映射到字体文件二进制数据
- 保证跨平台的内存布局一致性

### 大端序处理

所有多字节字段都是大端序,访问时需要转换:
```cpp
uint32_t numSizes = SkEndian_SwapBE32(eblc->numSizes);
```

### 偏移量计算

所有偏移量都是相对于 EBLC 表起始位置:
```cpp
const uint8_t* eblcBase = reinterpret_cast<const uint8_t*>(eblc);
const IndexSubTable* subTable =
    reinterpret_cast<const IndexSubTable*>(
        eblcBase + offset);
```

### 变长数组处理

多个结构体末尾包含变长数组(用注释表示):
- 实际大小在运行时根据表格数据确定
- 需要手动计算指针偏移

## 依赖关系

```
SkOTTable_EBLC.h
├── src/base/SkEndian.h (字节序转换)
├── src/sfnt/SkOTTableTypes.h (基础类型)
└── src/sfnt/SkOTTable_EBDT.h (位图数据定义)
    └── BigGlyphMetrics (字形度量)
```

**被依赖方**:
- 字体光栅化引擎
- 位图字形缓存系统
- 字体度量计算模块

## 设计模式与设计决策

### 1. 分层索引结构

**设计**: BitmapSizeTable → IndexSubTableArray → IndexSubTable
**优势**:
- 快速定位特定尺寸的位图
- 支持同一字体多个预渲染尺寸
- 减少线性搜索开销

### 2. 多格式支持

提供5种索引子表格式以适应不同场景:
- **Format 1/3**: 变长度量字形
- **Format 2/5**: 固定度量字形
- **Format 4/5**: 稀疏字形码

### 3. 度量数据分离

水平和垂直度量分开存储:
- 支持横排和竖排文本
- 适应不同书写系统

### 4. 位深度枚举

支持多种位深度:
- 黑白位图(1 bpp)
- 灰度图(2/4/8 bpp)
- 适应不同显示需求

## 性能考量

### 查找优化

1. **二分查找**: 字形索引通常有序,可用二分查找
2. **范围分组**: IndexSubTableArray 按字形范围分组
3. **缓存友好**: 紧凑内存布局提高缓存命中率

### 内存效率

- **格式选择**: 根据字形特性选择最紧凑的格式
- **2字节 vs 4字节偏移**: Format 3 比 Format 1 节省50%空间
- **共享度量**: Format 2/5 避免重复存储度量数据

### 访问模式

```
查找字形位图:
1. 定位 BitmapSizeTable (O(log n))
2. 查找 IndexSubTableArray (O(log n))
3. 根据格式读取偏移量 (O(1))
4. 访问 EBDT 数据 (O(1))
```

总时间复杂度: O(log n)

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_EBDT.h` | 位图数据表 | 存储实际位图,本表提供索引 |
| `src/sfnt/SkOTTable_EBSC.h` | 位图缩放表 | 位图尺寸匹配策略 |
| `src/sfnt/SkOTTableTypes.h` | 基础类型 | 提供所有类型定义 |
| `src/base/SkEndian.h` | 字节序工具 | 大小端转换 |
| `src/core/SkScalerContext.h` | 字形缩放上下文 | 使用位图数据进行渲染 |
| `src/ports/SkTypeface_*.cpp` | 平台字体实现 | 读取和解析 EBLC 表 |

EBLC 表是 OpenType 位图字体支持的核心组件,通过高效的索引结构实现快速字形查找,特别适合小尺寸字体和东亚字符集的显示优化。
