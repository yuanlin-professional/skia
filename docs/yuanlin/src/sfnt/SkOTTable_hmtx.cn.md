# SkOTTableHorizontalMetrics

> 源文件: src/sfnt/SkOTTable_hmtx.h

## 概述

`SkOTTable_hmtx.h` 定义了 OpenType 字体的 hmtx (Horizontal Metrics) 表结构。hmtx 表存储每个字形的水平度量信息,包括前进宽度(advance width)和左侧轴承距(left side bearing, LSB)。该表与 hhea 表协同工作,采用压缩存储策略以节省空间:前 numberOfHMetrics 个字形存储完整度量,剩余字形仅存储 LSB(共享最后一个前进宽度)。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTable_hhea.h (水平头表,提供 numberOfHMetrics)
    ├── SkOTTable_hmtx.h (水平度量表) ←
    └── SkOTTable_maxp.h (提供 numGlyphs)
```

## 主要类与结构体

### SkOTTableHorizontalMetrics

```cpp
struct SkOTTableHorizontalMetrics {
    static const SK_OT_CHAR TAG0 = 'h';
    static const SK_OT_CHAR TAG1 = 'm';
    static const SK_OT_CHAR TAG2 = 't';
    static const SK_OT_CHAR TAG3 = 'x';
    static const SK_OT_ULONG TAG = SkOTTableTAG<...>::value;

    struct FullMetric {
        SK_OT_USHORT advanceWidth;  // 前进宽度
        SK_OT_SHORT lsb;            // 左侧轴承距
    } longHorMetric[1/*hhea::numberOfHMetrics*/];

    struct ShortMetric {
        SK_OT_SHORT lsb;  // 仅左侧轴承距
    }; /* maxp::numGlyphs - hhea::numberOfHMetrics */
};
```

**标签**: `"hmtx"`

### FullMetric (完整度量)

```cpp
struct FullMetric {
    SK_OT_USHORT advanceWidth;  // 前进宽度(无符号)
    SK_OT_SHORT lsb;            // 左侧轴承距(有符号)
};
```

**大小**: 4 字节

**语义**:
- **advanceWidth**: 字形的水平前进宽度,光标移动的距离
- **lsb**: 字形原点到左侧边界的距离,可为负值

### ShortMetric (简化度量)

```cpp
struct ShortMetric {
    SK_OT_SHORT lsb;  // 仅左侧轴承距
};
```

**大小**: 2 字节

**用途**: 对于等宽字形,共享最后一个 advanceWidth,仅存储 LSB

## 存储布局

```
表结构:
[FullMetric × numberOfHMetrics]  ← 前 numberOfHMetrics 个字形
[ShortMetric × (numGlyphs - numberOfHMetrics)]  ← 剩余字形

示例 (numGlyphs=1000, numberOfHMetrics=900):
- 字形 0-899: FullMetric (4 字节 × 900 = 3600 字节)
- 字形 900-999: ShortMetric (2 字节 × 100 = 200 字节)
- 总大小: 3800 字节
```

## 公共 API 函数

```cpp
// 读取 hmtx 表
const SkOTTableHorizontalMetrics* hmtx =
    typeface->getTableData<SkOTTableHorizontalMetrics>(TAG);

// 获取 hhea 和 maxp 信息
const SkOTTableHorizontalHeader* hhea = ...;
const SkOTTableMaximumProfile* maxp = ...;
uint16_t numberOfHMetrics = SkEndian_SwapBE16(hhea->numberOfHMetrics);
uint16_t numGlyphs = SkEndian_SwapBE16(maxp->numGlyphs);

// 访问字形度量
void getMetrics(uint16_t glyphID, uint16_t* advanceWidth, int16_t* lsb) {
    if (glyphID < numberOfHMetrics) {
        // 完整度量
        const auto& metric = hmtx->longHorMetric[glyphID];
        *advanceWidth = SkEndian_SwapBE16(metric.advanceWidth);
        *lsb = SkEndian_SwapBE16(metric.lsb);
    } else {
        // 简化度量:共享最后一个 advanceWidth
        *advanceWidth = SkEndian_SwapBE16(
            hmtx->longHorMetric[numberOfHMetrics - 1].advanceWidth);

        // LSB 在 ShortMetric 数组中
        const auto* shortMetrics = reinterpret_cast<const ShortMetric*>(
            &hmtx->longHorMetric[numberOfHMetrics]);
        *lsb = SkEndian_SwapBE16(
            shortMetrics[glyphID - numberOfHMetrics].lsb);
    }
}
```

## 内部实现细节

### 变长数组

表包含两个变长数组:
- `longHorMetric[]`: 大小由 `hhea::numberOfHMetrics` 决定
- 隐式的 `ShortMetric[]`: 紧随其后,大小为 `numGlyphs - numberOfHMetrics`

### 内存计算

```cpp
size_t fullMetricsSize = numberOfHMetrics * sizeof(FullMetric);
size_t shortMetricsSize = (numGlyphs - numberOfHMetrics) * sizeof(ShortMetric);
size_t totalSize = fullMetricsSize + shortMetricsSize;
```

### 字节序处理

所有多字节值都是大端序:
```cpp
uint16_t advanceWidth = SkEndian_SwapBE16(metric.advanceWidth);
int16_t lsb = SkEndian_SwapBE16(metric.lsb);  // 有符号
```

## 依赖关系

```
SkOTTable_hmtx.h
├── src/base/SkEndian.h (字节序转换)
└── src/sfnt/SkOTTableTypes.h (基础类型)
```

**协作表格**:
- **hhea 表**: 提供 `numberOfHMetrics`
- **maxp 表**: 提供 `numGlyphs`

## 设计模式与设计决策

### 1. 压缩存储策略

**优化**: 等宽字形共享 advanceWidth

**效果**:
```
假设 1000 个字形,最后 100 个等宽:
- 未压缩: 1000 × 4 = 4000 字节
- 压缩后: 900 × 4 + 100 × 2 = 3800 字节
- 节省: 200 字节 (5%)
```

对于等宽字体(如终端字体):
```
假设 1000 个字形全等宽:
- 未压缩: 1000 × 4 = 4000 字节
- 压缩后: 1 × 4 + 999 × 2 = 2002 字节
- 节省: 1998 字节 (50%)
```

### 2. 两级度量结构

**设计**: FullMetric vs ShortMetric

**优势**:
- 适应比例字体(大部分字形用 FullMetric)
- 优化等宽字体(大部分字形用 ShortMetric)
- 灵活调整压缩比例

### 3. 有符号 LSB

LSB 使用有符号类型:
- 支持负值(字形超出原点左侧)
- 常见于斜体和手写字体

## 性能考量

### 访问模式

```cpp
// 顺序访问(缓存友好)
for (uint16_t gid = 0; gid < numGlyphs; ++gid) {
    getMetrics(gid, &aw, &lsb);
}

// 随机访问(需要条件分支)
if (gid < numberOfHMetrics) {
    // 分支 1: FullMetric
} else {
    // 分支 2: ShortMetric
}
```

### 缓存优化

典型表大小:
- 1000 字形: ~4KB
- 易于缓存
- 减少磁盘 I/O

### 分支预测

对于比例字体,`numberOfHMetrics` 通常接近 `numGlyphs`,分支预测友好。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_hhea.h` | 水平头表 | 提供 numberOfHMetrics |
| `src/sfnt/SkOTTable_maxp.h` | 最大轮廓表 | 提供 numGlyphs |
| `src/sfnt/SkOTTable_glyf.h` | 字形数据表 | 使用度量信息 |
| `src/core/SkScalerContext.h` | 字形缩放上下文 | 使用水平度量 |

hmtx 表通过智能的压缩策略在节省存储空间的同时保持高效的随机访问性能,是字体排版系统的核心数据源。
