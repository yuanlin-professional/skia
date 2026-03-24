# SkPanose - PANOSE 字体分类系统

> 源文件: `src/sfnt/SkPanose.h`

## 概述

`SkPanose.h` 定义了 PANOSE 字体分类系统的 C++ 结构体。PANOSE 是一个由 10 个字节组成的字体分类描述符，用于对字体进行形态学分类。第一个字节 `bFamilyType` 决定了后续 9 个字节的含义，支持四种字体家族：文本与显示（TextAndDisplay）、手写体（Script）、装饰体（Decorative）和图形符号（Pictoral）。PANOSE 系统被广泛用于字体匹配和替换算法中，是 OS/2 表的组成部分。该结构体固定为 10 字节。

## 架构位置

该文件位于 `src/sfnt/` 目录下，属于 SFNT 字体解析子系统。`SkPanose` 结构体作为 `SkOTTableOS2_V0` 到 `SkOTTableOS2_V4` 各版本 OS/2 表的嵌入成员，提供字体的 PANOSE 分类信息。该分类信息在字体匹配时被用于计算字体间的相似度。

## 主要类与结构体

### `SkPanose`
顶层结构体，10 字节大小。

#### `FamilyType` 枚举
决定后续 9 字节含义的分类头：
- `Any`(0): 任意
- `NoFit`(1): 不适用
- `TextAndDisplay`(2): 文本与显示字体
- `Script`(3): 手写体
- `Decorative`(4): 装饰体
- `Pictoral`(5): 图形符号

#### `Data` 联合体
根据 `bFamilyType` 的值，后续 9 字节分别映射为以下子结构之一：

### `Data::TextAndDisplay`
文本与显示字体的 9 个分类维度：
- `SerifStyle`: 衬线风格（16 种，包括 Cove, Square, Thin, Bone, NormalSans, Rounded 等）
- `Weight`: 字重（VeryLight 到 ExtraBlack，12 级）
- `Proportion`: 比例（OldStyle, Modern, EvenWidth, Expanded, Condensed, Monospaced 等）
- `Contrast`: 对比度（None 到 VeryHigh，10 级）
- `StrokeVariation`: 笔画变化（有 SK_WIN_PANOSE 和非 SK_WIN_PANOSE 两个版本）
- `ArmStyle`: 臂型（直臂/非直臂的水平/楔形/垂直/单衬线/双衬线）
- `Letterform`: 字母形态（Normal/Oblique 的 Contact/Weighted/Boxed/Flattened/Rounded 等）
- `Midline`: 中线位置（Standard/High/Constant/Low 的 Trimmed/Pointed/Serifed）
- `XHeight`: x 高度（Constant/Ducking 的 Small/Standard/Large）

### `Data::Script`
手写体的 9 个分类维度：
- `ToolKind`: 工具类型（FlatNib, PressurePoint, Engraved, Ball, Brush 等）
- `Weight`: 字重（与 TextAndDisplay 相同的 12 级）
- `Spacing`: 间距（ProportionalSpaced, Monospaced）
- `AspectRatio`: 纵横比（VeryCondensed 到 VeryExpanded）
- `Contrast`: 对比度
- `Topology`: 拓扑结构（Roman/Cursive/Blackletter 的 Disconnected/Trailing/Connected）
- `Form`: 形态（Upright/Oblique/Exaggerated 的 NoWrapping 到 ExtremeWrapping）
- `Finials`: 收笔（None/Sharp/Tapered/Round 的 NoLoops/ClosedLoops/OpenLoops）
- `XAscent`: x 上升高度

### `Data::Decorative`
装饰体的 9 个分类维度：
- `Class`: 装饰类别（Derivative, NonStandard_Topology, Initials, Cartoon, PictureStems 等）
- `Weight`: 字重
- `Aspect`: 纵横比（SuperCondensed 到 Monospaced）
- `Contrast`: 对比度（增加了 HorizontalLow/Medium/High 和 Broken）
- `SerifVariant`: 衬线变体（比 TextAndDisplay 多出 Script 选项，共 16 种）
- `Treatment`: 处理方式（StandardSolidFill, White_NoFill, PatternedFill 等）
- `Lining`: 线条（None, Inline, Outline, Engraved, Shadow, Relief, Backdrop）
- `Topology`: 拓扑结构（Standard, Square, MultipleSegment, Cursive, Blackletter 等）
- `RangeOfCharacters`: 字符范围（ExtendedCollection, Litterals, NoLowerCase, SmallCaps）

### `Data::Pictoral`
图形符号的 9 个分类维度：
- `Kind`: 种类（Montages, Pictures, Shapes, Scientific, Music, Patterns, Icons, Logos 等）
- `Weight`: 字重（仅 NoFit）
- `Spacing`: 间距
- `AspectRatioAndContrast`: 纵横比与对比度（仅 NoFit）
- `AspectRatio94`, `AspectRatio119`, `AspectRatio157`, `AspectRatio163`: 不同尺寸下的纵横比分类

## 公共 API 函数

该文件为纯数据结构定义，无公共函数。

## 内部实现细节

1. **条件编译**: `StrokeVariation` 枚举有两个版本。当定义 `SK_WIN_PANOSE` 时使用 Windows/FontForge/Apple TT 规范的定义（GradualDiagonal 开始，8 个值）；否则使用 HP Panose 规范的定义（NoVariation 开始，10 个值）。

2. **联合体覆盖**: `Data` 联合体让 4 种家族类型共享同一段 9 字节内存，通过 `bFamilyType` 确定正确的解释方式。

3. **强类型枚举**: 所有分类维度使用 `enum class : SK_OT_BYTE` 强类型枚举，每个枚举值占用 1 字节，确保类型安全和二进制兼容。

4. **图形符号特殊性**: `Pictoral` 家族的 `Weight` 和 `AspectRatioAndContrast` 维度仅有 `NoFit` 一个值，反映了图形符号在这些维度上缺乏有意义的分类。

5. **多纵横比维度**: `Pictoral` 家族的 4 个纵横比维度（94、119、157、163）对应不同的参考尺寸，提供更精细的图形符号宽度分类。

## 依赖关系

- `src/sfnt/SkOTTableTypes.h`: 提供 `SK_OT_BYTE` 类型定义

## 设计模式与设计决策

1. **多态联合体**: 使用 C 风格的标签联合体（tagged union）模式，`bFamilyType` 作为标签字段，`Data` 联合体作为变体数据。

2. **完整规范映射**: 所有 PANOSE 规范中定义的枚举值都被一一映射，确保能够表示任意合法的 PANOSE 描述符。

3. **平台兼容性**: 通过 `SK_WIN_PANOSE` 条件编译支持不同平台对 StrokeVariation 的不同定义，避免了跨平台不一致性。

4. **紧凑固定布局**: 10 字节的固定大小与 PANOSE 规范完全一致，适合直接嵌入 OS/2 表结构体中。

## 性能考量

- **10 字节固定大小**: 极度紧凑，适合缓存和快速比较
- **直接内存映射**: 无需解析，直接从字体文件内存读取
- **字体匹配优化**: PANOSE 值可用于快速预筛选，减少详细字体比较的次数

## 相关文件

- `src/sfnt/SkOTTable_OS_2_V0.h` ~ `SkOTTable_OS_2_V4.h`: 嵌入 SkPanose 的 OS/2 表各版本
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型定义
- `src/sfnt/SkIBMFamilyClass.h`: IBM 家族分类（与 PANOSE 互补的另一分类系统）
