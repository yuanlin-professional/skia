# SkOTTableIndexToLocation

> 源文件: src/sfnt/SkOTTable_loca.h

## 概述

`SkOTTable_loca.h` 定义了 OpenType/TrueType 字体的 loca (Index to Location) 表结构。loca 表存储 glyf 表中每个字形数据的偏移量,用于快速定位字形轮廓数据。该表支持两种格式:短格式(16位偏移)和长格式(32位偏移),格式选择由 head 表的 `indexToLocFormat` 字段决定。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_head.h (字体头表,指定 loca 格式)
    ├── SkOTTable_maxp.h (提供 numGlyphs)
    ├── SkOTTable_loca.h (位置索引表) ←
    └── SkOTTable_glyf.h (字形轮廓数据表)
```

## 主要类与结构体

### SkOTTableIndexToLocation

```cpp
struct SkOTTableIndexToLocation {
    static const SK_OT_CHAR TAG0 = 'l';
    static const SK_OT_CHAR TAG1 = 'o';
    static const SK_OT_CHAR TAG2 = 'c';
    static const SK_OT_CHAR TAG3 = 'a';
    static const SK_OT_ULONG TAG = SkOTTableTAG<...>::value;

    union Offsets {
        SK_OT_USHORT shortOffset[1];  // 短格式(16位)
        SK_OT_ULONG longOffset[1];    // 长格式(32位)
    } offsets;
};
```

**标签**: `"loca"`

### 格式选择

由 `head.indexToLocFormat` 决定:
- **0**: 短格式,实际偏移 = shortOffset[i] × 2
- **1**: 长格式,实际偏移 = longOffset[i]

## 表结构

### 短格式 (indexToLocFormat = 0)

```
数组大小: numGlyphs + 1
元素类型: uint16_t
实际偏移: shortOffset[i] × 2 (单位:字节)
最大 glyf 表大小: 128 KB (65536 × 2)

示例:
shortOffset[0] = 0      → 字形 0 从 glyf + 0 开始
shortOffset[1] = 50     → 字形 1 从 glyf + 100 开始
shortOffset[2] = 50     → 字形 2 为空字形(大小为0)
```

### 长格式 (indexToLocFormat = 1)

```
数组大小: numGlyphs + 1
元素类型: uint32_t
实际偏移: longOffset[i] (单位:字节)
最大 glyf 表大小: 4 GB

示例:
longOffset[0] = 0       → 字形 0 从 glyf + 0 开始
longOffset[1] = 500     → 字形 1 从 glyf + 500 开始
longOffset[2] = 500     → 字形 2 为空字形(大小为0)
```

## 公共 API 函数

```cpp
// 读取表格
const SkOTTableIndexToLocation* loca = typeface->getTableData<...>(TAG);
const SkOTTableHead* head = ...;
const SkOTTableMaximumProfile* maxp = ...;

// 获取格式
int16_t format = SkEndian_SwapBE16(head->indexToLocFormat);
uint16_t numGlyphs = ...;  // 从 maxp 表获取

// 获取字形偏移量和大小
void getGlyphLocation(uint16_t glyphID, uint32_t* offset, uint32_t* size) {
    if (format == 0) {
        // 短格式
        uint16_t start = SkEndian_SwapBE16(loca->offsets.shortOffset[glyphID]);
        uint16_t end = SkEndian_SwapBE16(loca->offsets.shortOffset[glyphID + 1]);
        *offset = start * 2;
        *size = (end - start) * 2;
    } else {
        // 长格式
        uint32_t start = SkEndian_SwapBE32(loca->offsets.longOffset[glyphID]);
        uint32_t end = SkEndian_SwapBE32(loca->offsets.longOffset[glyphID + 1]);
        *offset = start;
        *size = end - start;
    }
}

// 检查是否为空字形
bool isEmptyGlyph(uint16_t glyphID) {
    if (format == 0) {
        return loca->offsets.shortOffset[glyphID] ==
               loca->offsets.shortOffset[glyphID + 1];
    } else {
        return loca->offsets.longOffset[glyphID] ==
               loca->offsets.longOffset[glyphID + 1];
    }
}
```

## 内部实现细节

### 变长数组

实际数组大小为 `numGlyphs + 1`:
- 前 numGlyphs 个元素对应各字形起始位置
- 最后一个元素标记 glyf 表末尾

### 空字形检测

如果 `offset[i] == offset[i+1]`,则字形 i 为空:
- 无轮廓数据
- 常见于空格等不可见字符

### 字节对齐

短格式的实际偏移是 `shortOffset × 2`:
- glyf 表数据按 2 字节对齐
- 节省 loca 表空间(50%)

## 依赖关系

```
SkOTTable_loca.h
├── src/base/SkEndian.h
└── src/sfnt/SkOTTableTypes.h
```

**协作表格**:
- **head 表**: 提供 `indexToLocFormat`
- **maxp 表**: 提供 `numGlyphs`
- **glyf 表**: 存储字形数据

## 设计模式与设计决策

### 1. 双格式支持

**短格式**:
- 适用于小字体(glyf < 128KB)
- 节省 50% 空间
- 2 字节对齐限制

**长格式**:
- 适用于大字体
- 支持 4GB glyf 表
- 无对齐限制

### 2. 尾部哨兵

数组包含 `numGlyphs + 1` 个元素:
- 最后一个元素是哨兵
- 简化大小计算: `size = offset[i+1] - offset[i]`
- 避免特殊处理最后一个字形

### 3. 隐式大小编码

不直接存储字形大小,而是通过相邻偏移量差值计算:
- 节省空间
- 支持变长数据
- 自然支持空字形(差值为 0)

## 性能考量

### 格式选择权衡

| 指标 | 短格式 | 长格式 |
|------|--------|--------|
| 每个偏移量 | 2 字节 | 4 字节 |
| 1000 字形表大小 | 2002 字节 | 4004 字节 |
| 访问速度 | 快(更紧凑) | 稍慢 |
| 最大 glyf 大小 | 128 KB | 4 GB |

### 访问模式

```cpp
// O(1) 随机访问
uint32_t offset = getGlyphOffset(glyphID);

// 缓存友好的顺序访问
for (uint16_t i = 0; i < numGlyphs; ++i) {
    loadGlyph(i);
}
```

### 内存占用

典型字体(1000 字形):
- 短格式: ~2KB
- 长格式: ~4KB
- 易于整表缓存

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_head.h` | 字体头表 | 指定 loca 格式 |
| `src/sfnt/SkOTTable_glyf.h` | 字形数据表 | loca 提供索引 |
| `src/sfnt/SkOTTable_maxp.h` | 最大轮廓表 | 提供 numGlyphs |
| `src/ports/SkScalerContext_*.cpp` | 字形缩放实现 | 使用 loca 加载字形 |

loca 表通过简洁的设计实现了高效的字形数据索引,双格式支持在空间效率和灵活性之间取得平衡。
