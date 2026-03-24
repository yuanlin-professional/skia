# SkOTTable_glyf - OpenType glyf 表解析

> 源文件: `src/sfnt/SkOTTable_glyf.h`

## 概述

`SkOTTable_glyf.h` 定义了 OpenType/TrueType 字体中 `glyf`（Glyph Data）表的 C++ 内存映射结构。该文件提供了对字形轮廓数据的直接访问能力，包括简单字形（Simple Glyph）和复合字形（Composite Glyph）的数据解析。`glyf` 表是 TrueType 字体中存储字形矢量轮廓的核心表，每个字形的控制点、轮廓数和指令都记录在其中。

## 架构位置

该文件位于 Skia 的 `src/sfnt/` 目录下，属于 SFNT（Scalable Font）子系统。该子系统负责解析 OpenType/TrueType 字体文件的二进制表结构，为上层字体渲染引擎提供底层数据访问。`SkOTTable_glyf.h` 与 `SkOTTable_head.h`（提供 `IndexToLocFormat`）和 `SkOTTable_loca.h`（提供字形偏移索引）协同工作，共同完成字形数据的定位和解析。

## 主要类与结构体

### `SkOTTableGlyph`
表示整个 `glyf` 表的入口结构体。定义了表标签 `'glyf'`，并包含一个内部 `Iterator` 类用于遍历字形。

### `SkOTTableGlyph::Iterator`
字形遍历迭代器，通过 `loca` 表（索引到位置映射）来定位各个字形在 `glyf` 表中的偏移量。
- **构造参数**: `glyf` 表引用、`loca` 表引用、偏移格式（短偏移或长偏移）
- `advance(uint16_t num)`: 向前跳过 `num` 个字形
- `next()`: 返回当前字形数据的指针并前进一步；如果偏移量未变（表示空字形），则返回 `nullptr`

### `SkOTTableGlyphData`
单个字形的头部数据结构，包含：
- `numberOfContours`: 轮廓数量（-1 表示复合字形，>0 表示简单字形）
- `xMin`, `yMin`, `xMax`, `yMax`: 字形的边界框

### `SkOTTableGlyphData::Simple`
简单字形的数据结构，包含：
- `endPtsOfContours[]`: 每个轮廓的最后一个点的索引（变长数组）
- `Instructions`: 字形指令（TrueType hinting 指令）
- `Flags`: 控制点标志位联合体，包含 `OnCurve`、`xShortVector`、`yShortVector`、`Repeat` 等标志

### `SkOTTableGlyphData::Composite`
复合字形的数据结构，由多个 `Component` 组成：
- `Component::Flags`: 复合标志位，包括 `ARG_1_AND_2_ARE_WORDS`、`WE_HAVE_A_SCALE`、`MORE_COMPONENTS`、`WE_HAVE_A_TWO_BY_TWO` 等
- `Component::Transform`: 变换联合体，支持无变换、统一缩放、XY 独立缩放和 2x2 矩阵变换
- `Component::Transform::WordValue`/`ByteValue`/`WordIndex`/`ByteIndex`: 不同参数格式的偏移或索引值

## 公共 API 函数

该文件为纯头文件结构体定义，不包含独立函数。所有功能通过结构体成员和 `Iterator` 类的方法实现：

- `Iterator::advance(uint16_t num)`: 跳过指定数量的字形
- `Iterator::next()`: 获取下一个字形数据指针

## 内部实现细节

1. **字节序处理**: 所有多字节字段通过 `SkEndian_SwapBE16`/`SkEndian_SwapBE32` 进行大端转换，因为 OpenType 字体文件采用大端字节序。

2. **内存布局**: 使用 `#pragma pack(push, 1)` 确保结构体按 1 字节对齐，与磁盘上的字体文件二进制布局完全匹配。

3. **偏移计算**: `Iterator` 根据 `head` 表中的 `IndexToLocFormat` 字段决定使用短偏移（16 位，左移 1 位得到实际偏移）还是长偏移（32 位直接偏移）。

4. **空字形检测**: 当连续两个字形的偏移量相同时，`next()` 返回 `nullptr`，表示该字形没有轮廓数据（如空格字符）。

5. **变长数组模拟**: 使用 `data[1/*length*/]` 模式表示变长数组，实际大小由运行时字段决定。

## 依赖关系

- `src/base/SkEndian.h`: 提供字节序转换宏
- `src/sfnt/SkOTTableTypes.h`: 提供基础 OpenType 类型定义（`SK_OT_SHORT`, `SK_OT_FWORD` 等）
- `src/sfnt/SkOTTable_head.h`: 提供 `IndexToLocFormat` 枚举，决定 loca 表的偏移格式
- `src/sfnt/SkOTTable_loca.h`: 提供 `SkOTTableIndexToLocation`，存储字形到偏移的映射

## 设计模式与设计决策

1. **内存映射模式**: 结构体直接映射到字体文件的二进制数据上，避免额外的解析开销，实现零拷贝访问。

2. **联合体双重访问**: `Flags` 使用 `Field`（位域结构）和 `Raw`（掩码常量）两种访问方式，`Field` 便于阅读和调试，`Raw` 便于高效的位操作。

3. **迭代器模式**: `Iterator` 类封装了通过 `loca` 表间接访问字形的复杂性，提供简洁的遍历接口。

4. **前向声明**: `SkOTTableGlyphData` 在 `SkOTTableGlyph` 之前进行前向声明，因为 `Iterator::next()` 的返回类型需要它。

## 性能考量

- **零拷贝访问**: 结构体直接映射到字体文件内存，无需反序列化，提供最优的访问性能
- **O(1) 字形定位**: 通过 `loca` 表索引直接计算偏移量，每次字形访问为常数时间
- **最小内存开销**: `Iterator` 仅维护当前字形索引和偏移量两个状态变量

## 相关文件

- `src/sfnt/SkOTTable_head.h`: 字体头表，提供 `IndexToLocFormat`
- `src/sfnt/SkOTTable_loca.h`: 位置索引表，提供字形偏移量
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型定义
- `src/sfnt/SkOTTable_OS_2_V4.h`: OS/2 表，提供字体度量信息
