# SkOTTable_OS_2_V3 - OpenType OS/2 表版本 3 定义

> 源文件: `src/sfnt/SkOTTable_OS_2_V3.h`

## 概述

`SkOTTable_OS_2_V3.h` 定义了 OpenType/TrueType 字体中 OS/2 表版本 3 的 C++ 内存映射结构。OS/2 表提供了字体的核心度量和分类元数据，版本 3 对应 OpenType 1.4 规范。该版本的 Unicode 范围覆盖标志中有较多保留位（如 bit 8, 12, 14, 27, 53, 58 以及 l3 全部保留），这些保留位在版本 4 中被分配给了新的 Unicode 块。该结构体总大小为 96 字节，与版本 4 相同。

## 架构位置

该文件位于 `src/sfnt/` 目录下，是 SFNT 字体解析子系统的一部分。版本 3 和版本 4 的 OS/2 表共享相同的二进制大小（96 字节），但 `UnicodeRange` 和 `Selection` 字段的含义有所不同。Skia 在解析字体时会根据 `version` 字段选择对应的版本结构体来正确解释数据。

## 主要类与结构体

### `SkOTTableOS2_V3`
OS/2 表版本 3 主结构体，VERSION 常量值为 3。

#### 字重与宽度
- `usWeightClass`: 字重分类，枚举值与版本 4 相同（Thin 100 到 Black 900）
- `usWidthClass`: 宽度分类，枚举值与版本 4 相同（UltraCondensed 1 到 UltraExpanded 9）

#### `Type` 联合体
嵌入许可标志，与版本 4 完全一致：
- `Restricted`, `PreviewPrint`, `Editable`, `NoSubsetting`, `Bitmap`

#### 下标/上标度量
- `ySubscriptXSize/YSize/XOffset/YOffset`: 下标尺寸和偏移
- `ySuperscriptXSize/YSize/XOffset/YOffset`: 上标尺寸和偏移
- `yStrikeoutSize`, `yStrikeoutPosition`: 删除线尺寸和位置

#### `UnicodeRange` 联合体
128 位 Unicode 范围覆盖标志。与版本 4 的主要区别在于：
- **l0 层**: bit 8 (Coptic in V4) 和 bit 12 (Vai in V4) 和 bit 14 (NKo in V4) 和 bit 27 (Balinese in V4) 为保留位
- **l1 层**: bit 53 (PhagsPa in V4) 和 bit 58 (Phoenician in V4) 为保留位
- **l2 层**: bit 93-95 (Limbu, TaiLe, NewTaiLue in V4) 为保留位
- **l3 层**: 全部 32 位均为保留位（版本 4 分配了 Buginese 到 DominoTiles 等 27 个脚本）

#### `Selection` 联合体
版本 3 的选择标志较版本 4 更简洁：
- 支持 `Italic`, `Underscore`, `Negative`, `Outlined`, `Strikeout`, `Bold`, `Regular`
- **不支持**: `UseTypoMetrics`(bit 7)、`WWS`(bit 8)、`Oblique`(bit 9) -- 这些在版本 4 中新增

#### `CodePageRange` 联合体
64 位代码页范围标志，与版本 4 完全一致。

#### 排版度量（version0/version1/version2 字段）
与版本 4 相同的排版度量字段：`sTypoAscender`, `sTypoDescender`, `sTypoLineGap`, `usWinAscent`, `usWinDescent`, `sxHeight`, `sCapHeight`, `usDefaultChar`, `usBreakChar`, `usMaxContext`。

## 公共 API 函数

该文件为纯数据结构定义，无公共函数。

## 内部实现细节

1. **保留位处理**: 版本 3 的 `UnicodeRange` 中的保留位命名为 `Reserved0XX` 格式，对应位置的描述在版本 4 中被替换为具体的 Unicode 块名称。

2. **版本标识**: `VERSION` 常量为 `SkTEndian_SwapBE16(3)`，读取字体时先检查此字段确定使用哪个版本的结构体。

3. **Selection 标志差异**: 版本 3 的 `Selection::Field` 中 bit 7 为 `Reserved07`，而版本 4 将其更名为 `UseTypoMetrics`。同样 bit 8-9 在版本 3 中为保留位。

4. **Raw 掩码差异**: `Selection::Raw` 在版本 3 中不定义 `UseTypoMetricsMask`、`WWSMask` 和 `ObliqueMask`，因为这些是版本 4 新增的语义。

5. **UnicodeRange Raw 差异**: 版本 3 的 `UnicodeRange::Raw` 中部分掩码常量被注释为 `//Reserved`，对应的保留位没有定义掩码常量。

## 依赖关系

- `src/base/SkEndian.h`: 字节序转换
- `src/sfnt/SkIBMFamilyClass.h`: IBM 家族分类
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型
- `src/sfnt/SkPanose.h`: PANOSE 分类系统

## 设计模式与设计决策

1. **版本化结构体**: 不同版本的 OS/2 表使用独立的结构体类型（V0-V4），而非单一结构体加版本分支。这使得类型系统能在编译时区分不同版本的字段语义。

2. **保守的保留位处理**: 保留位被显式命名为 `ReservedXXX`，确保代码不会意外使用未定义语义的位。

3. **二进制兼容性**: 版本 3 和版本 4 具有相同的 96 字节大小，使得版本升级不影响内存布局。

4. **完整覆盖的 Raw 掩码**: 即使某些 Unicode 块在版本 3 中对应保留位，已分配的块仍然提供完整的 Raw 掩码定义。

## 性能考量

- **与版本 4 相同的内存占用**: 96 字节的紧凑结构体，高效缓存
- **编译时版本检查**: 通过 VERSION 常量在编译时确定使用哪个结构体
- **零拷贝内存映射**: 直接映射到字体文件数据

## 相关文件

- `src/sfnt/SkOTTable_OS_2_V4.h`: OS/2 表版本 4（下一版本，新增 WWS/Oblique 等）
- `src/sfnt/SkOTTable_OS_2_V2.h`: OS/2 表版本 2
- `src/sfnt/SkOTTable_OS_2_V1.h`: OS/2 表版本 1
- `src/sfnt/SkOTTable_OS_2_V0.h`: OS/2 表版本 0
- `src/sfnt/SkPanose.h`: PANOSE 字体分类
- `src/sfnt/SkIBMFamilyClass.h`: IBM 家族分类
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型
