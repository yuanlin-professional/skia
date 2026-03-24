# SkOTTable_head - OpenType head 表定义

> 源文件: `src/sfnt/SkOTTable_head.h`

## 概述

`SkOTTable_head.h` 定义了 OpenType/TrueType 字体中 `head`（Font Header）表的 C++ 内存映射结构。`head` 表是每个字体文件必须包含的基础表，存储了字体的全局信息，包括版本号、修订版本、校验和、创建/修改时间、字形边界框、Mac 样式标志、最低推荐像素大小、`loca` 表偏移格式等关键元数据。该结构体大小为 54 字节。

## 架构位置

`head` 表是字体文件结构中最基础的表之一，位于 `src/sfnt/` 目录下。它被 `SkOTTable_glyf.h` 依赖（用于确定 `loca` 表的偏移格式），同时被字体加载和渲染的各个环节使用。`head` 表中的 `unitsPerEm` 字段是所有字形坐标的基础单位。

## 主要类与结构体

### `SkOTTableHead`
`head` 表的完整结构体定义，54 字节。

#### 版本与校验字段
- `version`: 表版本，固定为 `0x00010000`（1.0）
- `fontRevision`: 字体修订版本号
- `checksumAdjustment`: 全字体校验和调整值
- `magicNumber`: 魔数，固定为 `0x5F0F3CF5`

#### `Flags` 联合体
字体全局标志（16 位），分为两组：
- **0-7 位**: `BaselineAtY0`（基线在 Y=0）、`LeftSidebearingAtX0`（左侧承在 X=0）、`InstructionsDependOnPointSize`（指令依赖点大小）、`IntegerScaling`（整数缩放）、`InstructionsAlterAdvanceWidth`（指令改变前进宽度）、`VerticalCenteredGlyphs_Apple`（垂直居中字形，Apple 专用）、`RequiresLayout_Apple`（需要布局处理，Apple 专用）
- **8-15 位**: `GXMetamorphosis_Apple`（GX 变形）、`HasStrongRTL_Apple`（强右到左）、`HasIndicStyleRearrangement`（印度语系重排）、`AgfaMicroTypeExpressProcessed`（Agfa 处理标记）、`FontConverted`（字体已转换）、`DesignedForClearType`（为 ClearType 设计）、`LastResort`（最后手段字体）

#### 全局度量字段
- `unitsPerEm`: 每 EM 单位数（字体坐标系的基础）
- `created`, `modified`: 64 位长日期时间（从 1904-01-01 起的秒数）
- `xMin`, `yMin`, `xMax`, `yMax`: 所有字形的全局边界框

#### `MacStyle` 联合体
Mac 平台样式标志（16 位）：
- `Bold`, `Italic`, `Underline`, `Outline`, `Shadow`, `Condensed`, `Extended`

#### 其他字段
- `lowestRecPPEM`: 最低推荐每 EM 像素数
- `FontDirectionHint`: 字体方向提示（混合方向/仅LTR/强LTR/仅RTL/强RTL）
- `IndexToLocFormat`: `loca` 表偏移格式（`ShortOffsets` 或 `LongOffsets`）
- `GlyphDataFormat`: 字形数据格式（当前仅 `CurrentFormat`=0）

## 公共 API 函数

该文件为纯数据结构定义，无公共函数。

## 内部实现细节

1. **魔数验证**: `magicNumberConst` 常量用于验证 `head` 表的完整性，值为 `0x5F0F3CF5`。

2. **字体校验和**: `fontChecksum` 常量 `0xB1B0AFBA` 用于整个字体文件的校验和计算。

3. **IndexToLocFormat**: 这是 `glyf` 表迭代器的关键字段。`ShortOffsets`(0) 表示 `loca` 表使用 16 位偏移（实际偏移需左移 1 位），`LongOffsets`(1) 表示使用 32 位偏移。

4. **FontDirectionHint 的负值处理**: RTL 方向使用负值（-1 和 -2），通过 `static_cast<SK_OT_SHORT>` 将 `uint16_t` 的大端负值转换为有符号类型。

5. **偏移量验证**: 文件末尾的两个 `static_assert` 分别验证 `glyphDataFormat` 字段位于偏移 52 处以及整个结构体大小为 54 字节。

## 依赖关系

- `src/base/SkEndian.h`: 字节序转换工具
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型（`SK_OT_Fixed`, `SK_OT_LONGDATETIME` 等）
- `<stddef.h>`: `offsetof` 宏（用于静态断言）

## 设计模式与设计决策

1. **零拷贝内存映射**: 1 字节对齐的 `#pragma pack(push, 1)` 确保结构体可直接映射到字体文件的二进制数据。

2. **枚举类型安全**: `FontDirectionHint`, `IndexToLocFormat`, `GlyphDataFormat` 使用强类型枚举嵌套在结构体中，提供类型安全的同时保持二进制兼容。

3. **Apple 扩展标注**: Apple 特有的标志位通过 `_Apple` 后缀明确标注，区分标准 OpenType 语义和 Apple 扩展语义。

## 性能考量

- **54 字节紧凑布局**: 单次内存读取即可获取全部信息
- **编译时常量**: 所有版本号和魔数在编译时计算
- **静态断言**: 编译期验证结构体布局正确性，避免运行时错误

## 相关文件

- `src/sfnt/SkOTTable_glyf.h`: 字形数据表（依赖 `IndexToLocFormat`）
- `src/sfnt/SkOTTable_loca.h`: 位置索引表
- `src/sfnt/SkOTTableTypes.h`: OpenType 基础类型
- `src/sfnt/SkOTTable_OS_2_V4.h`: OS/2 表（另一个核心元数据表）
