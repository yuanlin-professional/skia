# SkOTTableEmbeddedBitmapScaling

> 源文件: src/sfnt/SkOTTable_EBSC.h

## 概述

`SkOTTable_EBSC.h` 定义了 OpenType 字体中的 EBSC (Embedded Bitmap Scaling) 表结构。EBSC 表指定了当请求的字体尺寸没有对应的预渲染位图时,应该使用哪个现有位图尺寸进行缩放。该表为位图字体提供了优雅的尺寸回退机制,在保证显示质量的同时减少存储空间需求。

## 架构位置

```
Skia 字体系统
└── src/sfnt/
    ├── SkOTTableTypes.h (基础类型)
    ├── SkOTTable_EBLC.h (位图位置,包含 SbitLineMetrics)
    ├── SkOTTable_EBDT.h (位图数据)
    └── SkOTTable_EBSC.h (位图缩放策略) ←
```

**定位**: 位图字体尺寸匹配和回退策略

## 主要类与结构体

### SkOTTableEmbeddedBitmapScaling (主结构)

```cpp
struct SkOTTableEmbeddedBitmapScaling {
    static const SK_OT_CHAR TAG0 = 'E';
    static const SK_OT_CHAR TAG1 = 'S';  // 注意是 'S' 不是 'B'
    static const SK_OT_CHAR TAG2 = 'B';
    static const SK_OT_CHAR TAG3 = 'C';
    static const SK_OT_ULONG TAG = SkOTTableTAG<...>::value;

    SK_OT_Fixed version;  // 版本 2.0
    static const SK_OT_Fixed version_initial =
        SkTEndian_SwapBE32(0x00020000);

    SK_OT_ULONG numSizes;  // 缩放表项数量
};
```

**标签**: `"ESBC"` (Embedded Scaling Bitmap Component)

### BitmapScaleTable (缩放表项)

```cpp
struct BitmapScaleTable {
    SkOTTableEmbeddedBitmapLocation::SbitLineMetrics hori;  // 水平度量
    SkOTTableEmbeddedBitmapLocation::SbitLineMetrics vert;  // 垂直度量
    SK_OT_BYTE ppemX;            // 目标水平像素/EM
    SK_OT_BYTE ppemY;            // 目标垂直像素/EM
    SK_OT_BYTE substitutePpemX;  // 替代水平像素/EM
    SK_OT_BYTE substitutePpemY;  // 替代垂直像素/EM
}; // bitmapScaleTable[numSizes];
```

**语义**:
- **ppemX/ppemY**: 用户请求的目标尺寸
- **substitutePpemX/substitutePpemY**: 实际使用的位图尺寸
- **hori/vert**: 缩放后的预期度量

## 工作原理

### 尺寸匹配流程

```
1. 用户请求字体尺寸: 16 ppem
   ↓
2. 查找 EBLC 表: 没有 16 ppem 的位图
   ↓
3. 查找 EBSC 表:
   找到条目 {ppem: 16, substitute: 12}
   ↓
4. 使用 12 ppem 位图并缩放到 16 ppem
   ↓
5. 应用 EBSC 表中的调整后度量
```

### 度量调整

EBSC 表提供缩放后的度量,而非简单线性缩放:
```cpp
// 不是简单的:
scaled_metric = original_metric * (16 / 12)

// 而是使用 EBSC 表提供的精确值:
scaled_metric = bitmapScaleTable[i].hori.ascender
```

## 公共 API 函数

该文件为纯数据结构定义,使用方式:

```cpp
// 1. 读取 EBSC 表
const SkOTTableEmbeddedBitmapScaling* ebsc =
    typeface->getTableData<SkOTTableEmbeddedBitmapScaling>(TAG);

if (!ebsc) {
    // 没有 EBSC 表,使用默认缩放策略
    return;
}

// 2. 遍历缩放表
uint32_t numSizes = SkEndian_SwapBE32(ebsc->numSizes);
const BitmapScaleTable* scaleTable =
    reinterpret_cast<const BitmapScaleTable*>(ebsc + 1);

// 3. 查找匹配的尺寸
for (uint32_t i = 0; i < numSizes; ++i) {
    if (scaleTable[i].ppemX == requestedPpemX &&
        scaleTable[i].ppemY == requestedPpemY) {
        // 找到匹配项
        uint8_t substitutePpem = scaleTable[i].substitutePpemX;
        // 使用 substitutePpem 的位图进行缩放
        break;
    }
}
```

## 内部实现细节

### 内存布局

```cpp
#pragma pack(push, 1)  // 紧凑打包

// 表结构:
// [表头: version + numSizes]
// [BitmapScaleTable 数组: numSizes 个元素]
```

### SbitLineMetrics 重用

EBSC 表重用了 EBLC 表的 `SbitLineMetrics` 结构:
- 避免重复定义
- 保持一致性
- 包含完整的行度量信息

### 变长数组

`BitmapScaleTable` 数组紧随表头:
```cpp
const BitmapScaleTable* tables =
    reinterpret_cast<const BitmapScaleTable*>(
        reinterpret_cast<const uint8_t*>(ebsc) +
        sizeof(SkOTTableEmbeddedBitmapScaling));
```

## 依赖关系

```
SkOTTable_EBSC.h
├── src/base/SkEndian.h (字节序转换)
├── src/sfnt/SkOTTableTypes.h (基础类型)
└── src/sfnt/SkOTTable_EBLC.h (SbitLineMetrics 定义)
```

**协作关系**:
- **EBLC**: 提供可用的位图尺寸
- **EBSC**: 提供尺寸回退策略
- **EBDT**: 存储实际位图数据

## 设计模式与设计决策

### 1. 显式缩放映射

**设计**: 明确指定每个目标尺寸的替代尺寸

**优势**:
- 字体设计师可精确控制回退策略
- 支持非线性尺寸映射
- 可针对不同尺寸优化度量

**示例**:
```
10 ppem → 使用 12 ppem (放大)
14 ppem → 使用 12 ppem (缩小)
20 ppem → 使用 16 ppem (放大)
```

### 2. 度量预计算

EBSC 表包含缩放后的度量:
- 避免运行时计算
- 支持非线性度量调整
- 保证显示质量

### 3. 可选表

EBSC 表是可选的:
- 如果不存在,使用默认缩放策略(最近邻)
- 字体可选择性提供此表
- 减少简单位图字体的复杂性

## 性能考量

### 查找效率

```cpp
// 线性查找,但通常表很小
for (uint32_t i = 0; i < numSizes; ++i) {
    if (match_ppem(...)) { ... }
}
```

**优化策略**:
- 通常 numSizes 较小 (< 10)
- 可缓存查找结果
- 可按 ppem 排序并二分查找

### 内存占用

每个 `BitmapScaleTable` 占:
```
SbitLineMetrics (12字节) × 2 + 4字节 = 28字节
```

典型表大小:
```
表头(8字节) + 10个尺寸(280字节) = 288字节
```

极其紧凑,易于缓存。

### 避免动态缩放

通过预选择合适的替代尺寸:
- 减少缩放比例
- 提高缩放质量
- 降低计算开销

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_EBLC.h` | 位图位置表 | 提供 SbitLineMetrics,列出可用尺寸 |
| `src/sfnt/SkOTTable_EBDT.h` | 位图数据表 | 存储实际位图 |
| `src/sfnt/SkOTTableTypes.h` | 基础类型 | 类型定义 |
| `src/core/SkScalerContext.h` | 字形缩放上下文 | 使用 EBSC 选择尺寸 |
| `src/ports/SkScalerContext_*.cpp` | 平台缩放实现 | 实现尺寸回退逻辑 |

EBSC 表为位图字体提供了智能的尺寸回退机制,通过预定义的映射和度量调整,在减少存储空间的同时保证显示质量。它是位图字体系统的重要优化组件。
