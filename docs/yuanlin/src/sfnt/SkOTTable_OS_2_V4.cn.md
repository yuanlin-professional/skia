# SkOTTable_OS_2_V4 - OpenType OS/2 表版本 4 定义

> 源文件: `src/sfnt/SkOTTable_OS_2_V4.h`

## 概述

`SkOTTable_OS_2_V4.h` 定义了 OpenType/TrueType 字体中 OS/2 表版本 4 的 C++ 内存映射结构。OS/2 表（OS/2 and Windows Metrics）是字体中最重要的元数据表之一，包含字体的字重、宽度类别、嵌入许可、PANOSE 分类、Unicode 范围覆盖、代码页范围、排版度量等关键信息。版本 4 相较于版本 3 增加了 `WWS`（Weight/Width/Slope）和 `Oblique` 选择标志，新增了 Balinese 等 Unicode 范围支持。该结构体总大小为 96 字节。

## 架构位置

该文件位于 Skia 的 `src/sfnt/` 目录下，是 SFNT 字体解析子系统的组成部分。OS/2 表在字体选择、样式匹配、文本布局等场景中被广泛使用。Skia 的字体匹配算法会读取 `usWeightClass`、`usWidthClass`、`fsSelection` 等字段来确定字体的粗细、宽度和样式属性。该文件与 `SkOTTable_OS_2_V3.h`（版本 3）共享类似的结构但有扩展。

## 主要类与结构体

### `SkOTTableOS2_V4`
OS/2 表版本 4 的主结构体，所有字段按大端字节序存储。

#### 基本字体度量字段
- `version`: 表版本号，值为 4
- `xAvgCharWidth`: 平均字符宽度
- `usWeightClass`: 字重分类（100-900，对应 Thin 到 Black）
- `usWidthClass`: 宽度分类（1-9，对应 UltraCondensed 到 UltraExpanded）

#### `WeightClass` 嵌套结构
枚举值定义了标准字重等级：
- `Thin`(100), `ExtraLight`(200), `Light`(300), `Normal`(400), `Medium`(500)
- `SemiBold`(600), `Bold`(700), `ExtraBold`(800), `Black`(900)

#### `WidthClass` 嵌套结构
枚举值定义了标准宽度等级：
- `UltraCondensed`(1) 到 `UltraExpanded`(9)

#### `Type` 联合体
嵌入许可标志，控制字体的分发和嵌入权限：
- `Restricted`: 限制性许可
- `PreviewPrint`: 允许预览和打印
- `Editable`: 允许编辑
- `NoSubsetting`: 禁止子集化
- `Bitmap`: 仅允许位图嵌入

#### `UnicodeRange` 联合体
128 位的 Unicode 范围覆盖标志（4 个 32 位长字），声明字体支持哪些 Unicode 块。版本 4 新增了 Balinese、Vai、NKo、PhagsPa 等脚本的支持标志。分为 4 层（`l0`-`l3`），覆盖从 BasicLatin 到 DominoTiles_MahjongTiles 的完整 Unicode 块。

#### `Selection` 联合体
字体选择标志（`fsSelection`），版本 4 新增：
- `WWS`(bit 8): 标识字体遵循 Weight/Width/Slope 命名约定
- `Oblique`(bit 9): 标识字体为倾斜体（区别于 Italic）
- 沿用标志: `Italic`, `Bold`, `Regular`, `Underscore`, `Negative`, `Outlined`, `Strikeout`, `UseTypoMetrics`

#### `CodePageRange` 联合体
64 位的代码页范围标志（2 个 32 位长字），声明字体支持哪些代码页编码（如 Latin1_1252、JISJapan_932、ChineseSimplified_936 等）。

#### 排版度量字段
- `sTypoAscender`, `sTypoDescender`, `sTypoLineGap`: 排版上升/下降/行间距
- `usWinAscent`, `usWinDescent`: Windows 裁剪度量
- `sxHeight`, `sCapHeight`: x 高度和大写字母高度
- `usDefaultChar`, `usBreakChar`: 默认字符和断行字符
- `usMaxContext`: 最大上下文长度

## 公共 API 函数

该文件为纯数据结构定义，不包含函数。所有访问通过直接读取结构体成员实现。

## 内部实现细节

1. **字节序处理**: 所有常量值在编译时通过 `SkTEndian_SwapBE16` 进行大端转换，使得比较操作可以直接与内存中的数据进行。

2. **位域双重访问**: 所有标志字段都提供 `Field`（位域结构体）和 `Raw`（位掩码常量）两种访问方式。`Field` 使用 `SK_OT_BYTE_BITFIELD` 宏按平台字节序定义位域，`Raw` 使用 `SkOTSetUSHORTBit`/`SkOTSetULONGBit` 模板生成大端掩码。

3. **PANOSE 嵌入**: 结构体内嵌了 `SkPanose` 和 `SkIBMFamilyClass`，分别提供 PANOSE 字体分类和 IBM 家族分类信息。

4. **静态断言**: 文件末尾通过 `static_assert(sizeof(SkOTTableOS2_V4) == 96)` 确保结构体大小与规范一致。

5. **版本区分**: `version0`、`version1`、`version2` 注释标明了各字段首次出现的版本号，帮助理解不同版本间的字段差异。

## 依赖关系

- `src/base/SkEndian.h`: 字节序转换工具
- `src/sfnt/SkIBMFamilyClass.h`: IBM 字体家族分类定义
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型和位操作辅助模板
- `src/sfnt/SkPanose.h`: PANOSE 字体分类系统定义

## 设计模式与设计决策

1. **内存映射模式**: 1 字节对齐的结构体直接映射到字体文件二进制数据，实现零拷贝解析。

2. **版本继承设计**: 版本 4 相对于版本 3 是增量扩展，新增的字段和标志位通过扩展现有联合体的枚举值实现，保持了向后兼容性。

3. **枚举类型安全**: `WeightClass` 和 `WidthClass` 使用强类型枚举（`enum Value : SK_OT_USHORT`），在类型安全的同时保持与底层二进制数据的兼容性。

4. **全面的 Unicode 覆盖**: `UnicodeRange` 的 128 位标志涵盖了 OpenType 规范中定义的所有 Unicode 块，版本 4 填充了版本 3 中的部分保留位。

## 性能考量

- **编译时常量**: 所有枚举值和掩码常量在编译时计算，运行时比较操作无额外开销
- **直接内存访问**: 结构体与文件格式一一对应，无需反序列化步骤
- **96 字节紧凑布局**: 单次缓存行读取即可获取大部分关键字段

## 相关文件

- `src/sfnt/SkOTTable_OS_2_V3.h`: OS/2 表版本 3（上一版本）
- `src/sfnt/SkOTTable_OS_2_V0.h` ~ `SkOTTable_OS_2_V2.h`: 更早的版本定义
- `src/sfnt/SkPanose.h`: PANOSE 分类系统
- `src/sfnt/SkIBMFamilyClass.h`: IBM 家族分类
- `src/sfnt/SkOTTable_head.h`: 字体头表
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型
