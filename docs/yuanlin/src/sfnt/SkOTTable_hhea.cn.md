# SkOTTable_hhea

> 源文件: src/sfnt/SkOTTable_hhea.h

## 概述

`SkOTTable_hhea.h` 定义了 OpenType `hhea` (Horizontal Header) 表的结构,存储字体的水平排版度量信息。该表包含字体的上升高度(ascender)、下降高度(descender)、行间距(line gap)等关键排版参数,以及最大字形宽度、侧边距等度量数据。这些信息对于文本布局和行间距计算至关重要,是任何文本渲染引擎的基础数据。

`hhea` 表与 `hmtx` (Horizontal Metrics) 表配合使用,`hhea` 提供全局度量,`hmtx` 提供每个字形的具体宽度数据。

## 架构位置

- **模块路径**: `src/sfnt/`
- **表标签**: `'hhea'`
- **规范**: TrueType/OpenType 必需表
- **依赖**: `SkOTTableTypes.h`, `SkEndian.h`
- **配合**: `hmtx` 表(水平度量)

## 主要类与结构体

### SkOTTableHorizontalHeader

**成员**(36字节):
```cpp
SK_OT_Fixed version;                // 版本(1.0 = 0x00010000)
SK_OT_FWORD Ascender;               // 上升高度(基线以上)
SK_OT_FWORD Descender;              // 下降高度(基线以下,通常为负)
SK_OT_FWORD LineGap;                // 行间距
SK_OT_UFWORD advanceWidthMax;       // 最大前进宽度
SK_OT_FWORD minLeftSideBearing;     // 最小左侧边距
SK_OT_FWORD minRightSideBearing;    // 最小右侧边距
SK_OT_FWORD xMaxExtent;             // max(lsb + xMax - xMin)
SK_OT_SHORT caretSlopeRise;         // 光标斜率分子(垂直=1)
SK_OT_SHORT caretSlopeRun;          // 光标斜率分母(垂直=0)
SK_OT_SHORT caretOffset;            // 光标偏移(斜体字体)
SK_OT_SHORT Reserved24-30;          // 保留字段(4个,必须为0)
MetricDataFormat metricDataFormat;  // 度量格式(必须为0)
SK_OT_USHORT numberOfHMetrics;      // hmtx表中的度量记录数
```

### MetricDataFormat

```cpp
enum Value : SK_OT_SHORT {
    CurrentFormat = 0  // 唯一支持的格式
};
```

## 公共 API 函数

仅包含数据结构定义。

**使用示例**:
```cpp
const SkOTTableHorizontalHeader* hhea = /* 读取 */;

int16_t ascender = SkEndian_SwapBE16(hhea->Ascender);
int16_t descender = SkEndian_SwapBE16(hhea->Descender);
int16_t lineGap = SkEndian_SwapBE16(hhea->LineGap);

// 计算行高
int16_t lineHeight = ascender - descender + lineGap;  // descender通常为负

uint16_t numMetrics = SkEndian_SwapBE16(hhea->numberOfHMetrics);
// 用于解析hmtx表
```

## 内部实现细节

### 1. 度量含义

```
    ┌─────── Ascender ───────┐
    │                        │
────┼────────────────────────┼──── 基线(Baseline)
    │                        │
    └─────── Descender ──────┘  (负值)

    ├──── LineGap ────┤
```

**Ascender**: 最高字形顶部到基线的距离
**Descender**: 最低字形底部到基线的距离(负值)
**LineGap**: 推荐的额外行间距

**总行高**: `Ascender - Descender + LineGap`

### 2. 侧边距度量

```
minLeftSideBearing ─┤                     ├─ minRightSideBearing
                    │ ┌───────────┐       │
                    │ │   字形    │       │
                    │ └───────────┘       │
                    ├───────────────────────┤ advanceWidthMax
```

**minLeftSideBearing**: 所有字形的最小左侧边距
**minRightSideBearing**: 所有字形的最小右侧边距
**advanceWidthMax**: 最大字形宽度(前进距离)
**xMaxExtent**: 字形最大水平范围

### 3. 光标斜率

用于斜体字体的光标定位:
```cpp
// 光标角度 = atan(caretSlopeRise / caretSlopeRun)
// 正常直立字体: rise=1, run=0 (垂直)
// 斜体字体: rise=1, run=斜度 (例如 run=4 表示1:4斜率)
```

### 4. numberOfHMetrics

指示 `hmtx` 表中完整度量记录的数量:
- 前 `numberOfHMetrics` 个字形有完整的 `<advanceWidth, lsb>` 记录
- 剩余字形只有 `lsb`,共享最后一个 `advanceWidth`

优化技术:固定宽度字体(等宽)可大幅减小 `hmtx` 表。

## 依赖关系

### 直接依赖

- `src/sfnt/SkOTTableTypes.h`: OpenType 类型
- `src/base/SkEndian.h`: 字节序转换

### 被依赖情况

- `SkTypeface`: 字体度量查询
- 文本布局引擎: 行高计算
- `SkFontMetrics`: Skia字体度量封装
- `hmtx` 表解析: 依赖 `numberOfHMetrics`

## 设计模式与设计决策

### 1. 全局度量分离

将全局度量与逐字形度量分离:
- `hhea`: 全局参数(36字节)
- `hmtx`: 逐字形数据(可达MB级)

### 2. 固定大小结构

36字节固定大小:
- 快速读取
- 无可变长度字段
- 缓存友好

### 3. 保留字段

8字节保留空间:
- 未来扩展
- 必须清零

### 4. 度量格式标志

`metricDataFormat` 预留扩展:
- 当前只支持格式0
- 未来可支持新格式

## 性能考量

### 1. 缓存效率

36字节表:
- 单个缓存行容纳
- 频繁访问零开销

### 2. hmtx 优化

`numberOfHMetrics` 优化:
- 等宽字体:仅1个完整记录
- 比例字体:所有字形记录
- 节省50-90%空间(等宽场景)

### 3. 行高预计算

度量数据在字体加载时一次读取:
- 避免重复解析
- 存储在 `SkFontMetrics` 中

## 相关文件

### 核心依赖

- `src/sfnt/SkOTTableTypes.h`
- `src/base/SkEndian.h`

### 相关表

- `src/sfnt/SkOTTable_hmtx.h`: 水平度量(配合使用)
- `src/sfnt/SkOTTable_vhea.h`: 垂直头表(垂直排版)
- `src/sfnt/SkOTTable_vmtx.h`: 垂直度量

### Skia 接口

- `include/core/SkFontMetrics.h`: Skia度量API
- `include/core/SkTypeface.h`: 字体接口

该表是文本排版的基础,为 Skia 提供关键的字体度量信息,确保正确的行高计算和文本布局。
