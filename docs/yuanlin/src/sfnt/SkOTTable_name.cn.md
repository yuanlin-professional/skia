# SkOTTable_name — OpenType name 表结构定义与解析

> 源文件：[src/sfnt/SkOTTable_name.h](../../src/sfnt/SkOTTable_name.h)、[src/sfnt/SkOTTable_name.cpp](../../src/sfnt/SkOTTable_name.cpp)

## 概述

`SkOTTable_name` 实现了 OpenType 字体规范中 `name` 表（命名表）的完整数据结构定义和解析功能。`name` 表存储字体的各类文本信息，包括字体家族名称、样式名、版权信息、许可证等。

本模块提供：

- **数据结构**：按 OpenType 规范精确映射的 C++ 结构体（使用 `#pragma pack(push, 1)` 保证字节级对齐）
- **平台/编码/语言 ID 枚举**：完整覆盖 Unicode、Macintosh、ISO、Windows 四种平台 ID，以及各平台下的编码 ID 和语言 ID
- **NameID 枚举**：预定义名称类型（FontFamilyName、PostscriptName 等共 22 种）
- **迭代器**：`Iterator` 类用于遍历 name 表中的记录，自动处理字符编码转换
- **语言映射**：Mac Language Designator 和 Windows LCID 到 BCP 47 语言标签的映射表

## 架构位置

`SkOTTable_name` 位于 Skia 的 SFNT 字体数据层（`src/sfnt/`），是 OpenType 表结构定义家族中的一员。

```
SkTypeface (上层字体抽象)
    │
    ├── SkOTUtils::LocalizedStrings_NameTable
    │       │
    │       └── SkOTTableName::Iterator  ← 本模块
    │               │
    │               └── SkOTTableName (数据结构)
    │                       ├── Record (记录结构)
    │                       │   ├── PlatformID
    │                       │   ├── EncodingID (union)
    │                       │   ├── LanguageID (union)
    │                       │   └── NameID (union)
    │                       └── Format1Ext (格式 1 扩展)
    │
    └── SkOTUtils::RenameFont (写入新 name 表)
```

## 主要类与结构体

### `SkOTTableName`

name 表的根结构体。大小恰好 6 字节。

| 字段 | 类型 | 说明 |
|------|------|------|
| `format` | `SK_OT_USHORT` | 格式版本：format_0 或 format_1 |
| `count` | `SK_OT_USHORT` | 名称记录数 |
| `stringOffset` | `SK_OT_USHORT` | 字符串存储区相对于表起始的偏移（字节） |

静态常量：
- `TAG` = `'name'`（四字节标签）
- `format_0` = 0（大端）
- `format_1` = 1（大端，OpenType 1.6 新增，支持 BCP 47 语言标签）

### `SkOTTableName::Record`

单条名称记录结构体，大小 12 字节。包含以下嵌套类型：

#### `Record::PlatformID`

平台标识枚举：

| 枚举值 | 含义 |
|--------|------|
| `Unicode` (0) | Unicode 平台 |
| `Macintosh` (1) | Macintosh 平台 |
| `ISO` (2) | ISO 平台（已弃用） |
| `Windows` (3) | Windows 平台 |
| `Custom` (4) | 自定义平台 |

#### `Record::EncodingID`（union）

根据平台 ID 解释的编码标识：

- **Unicode**：`Unicode10`、`Unicode11`、`Unicode20BMP`、`Unicode20`、`UnicodeVariationSequences`、`UnicodeFull` 等
- **Macintosh**：`Roman`、`Japanese`、`ChineseTraditional`、`ChineseSimplified` 等共 33 种
- **ISO**：`ASCII7`、`ISO10646`、`ISO88591`（已弃用）
- **Windows**：`Symbol`（UCS2-BE）、`UnicodeBMPUCS2`（UCS2-BE，Windows 默认）、`ShiftJIS`、`PRC`、`Big5`、`Wansung`、`Johab`、`UnicodeUCS4`（UTF-16BE）

#### `Record::LanguageID`（union）

语言标识，按平台分组：

- **Macintosh**：151 种语言标识（从 English=0 到 AzerbaijaniRoman=150），Apple 已改用 BCP 47
- **Windows**：206 种 LCID（从 Afrikaans_SouthAfrica=0x0436 到 Yoruba_Nigeria=0x046A），覆盖全球主要语言和地区变体
- **languageTagID**：> 0x7FFF 的值是 Format 1 中 langTagRecord 数组的索引

#### `Record::NameID`（union）

名称类型标识：

| 预定义 ID | 含义 |
|-----------|------|
| 0 | CopyrightNotice（版权声明） |
| 1 | FontFamilyName（字体家族名） |
| 2 | FontSubfamilyName（字体子家族名） |
| 3 | UniqueFontIdentifier（唯一标识符） |
| 4 | FullFontName（完整字体名） |
| 5 | VersionString（版本字符串） |
| 6 | PostscriptName（PostScript 名称） |
| 7 | Trademark（商标） |
| 8-14 | 制造商、设计师、描述、URL、许可证等 |
| 16 | PreferredFamily（首选家族名） |
| 17 | PreferredSubfamily（首选子家族名） |
| 18-22 | CompatibleFullName、SampleText、PostscriptCIDFindfontName、WWSFamilyName、WWSSubfamilyName |

> NameID <= 0xFF 为预定义，> 0xFF 为字体特定。

### `SkOTTableName::Format1Ext`

Format 1 扩展结构（2 字节），包含 `langTagCount` 字段和 `LangTagRecord` 子结构（4 字节：length + offset）。Format 1 语言标签记录始终使用 UTF-16BE 编码，内容遵循 BCP 47 规范。

### `SkOTTableName::Iterator`

name 表记录迭代器，负责遍历和解码名称记录。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fNameTable` | `const uint8_t*` | name 表原始数据指针 |
| `fNameTableSize` | `size_t` | 数据大小 |
| `fIndex` | `size_t` | 当前记录索引 |
| `fType` | `int` | 过滤的 NameID 类型（-1 表示不过滤） |

内部 `Record` 结构包含：`name`（SkString，UTF-8）、`language`（SkString，BCP 47）、`type`（SK_OT_USHORT）。

## 公共 API 函数

### `Iterator::Iterator(const uint8_t* nameTable, size_t size)`

构造不过滤类型的迭代器（fType = -1），将遍历所有 NameID 类型的记录。

### `Iterator::Iterator(const uint8_t* nameTable, size_t size, SK_OT_USHORT type)`

构造指定 NameID 类型过滤的迭代器。

### `Iterator::reset(SK_OT_USHORT type)`

重置迭代器到表起始位置，并设置新的过滤类型。

### `Iterator::next(Record& record) -> bool`

获取下一条匹配记录。返回 `true` 表示成功，`false` 表示已遍历完毕或数据无效。此方法执行以下操作：

1. 解析 name 表头部获取记录数和字符串表偏移
2. 跳过不匹配 fType 的记录（当 fType != -1 时）
3. 根据平台 ID 和编码 ID 将名称字符串解码为 UTF-8
4. 将语言 ID 转换为 BCP 47 语言标签

## 内部实现细节

### 字符编码转换

`Iterator::next()` 根据平台 ID 选择解码策略：

- **Windows / Unicode / ISO 平台**：使用 `SkString_from_UTF16BE()` 将 UTF-16BE 数据转为 UTF-8。Windows 平台额外过滤只支持 Symbol、UnicodeBMPUCS2、UnicodeUCS4 三种编码。
- **Macintosh 平台**：仅支持 Roman 编码，通过 `SkStringFromMacRoman()` 和 `UnicodeFromMacRoman` 查找表将 MacRoman 编码转为 Unicode 再转 UTF-8。MacRoman 前 128 码位与 ASCII 一致，后 128 码位通过查找表映射。
- **Custom 平台**：不应出现在 name 表中，触发断言。

### UTF-16BE 解码

`next_unichar_UTF16BE()` 处理完整的 UTF-16 代理对（surrogate pair）解码：
1. 读取前导 16 位值
2. 如果是尾随代理（trailing surrogate），返回替换字符 U+FFFD
3. 如果是前导代理（leading surrogate），读取并验证后续尾随代理，组合为完整码位
4. 使用公式 `(leading << 10) + trailing + (0x10000 - (0xD800 << 10) - 0xDC00)` 计算最终码位

### 语言 ID 映射

语言 ID 到 BCP 47 的映射分两种情况：

1. **Format 1 + languageID >= 0x8000**：从 langTagRecord 数组中读取 UTF-16BE 编码的 BCP 47 标签
2. **Format 0 或 languageID < 0x8000**：在预排序的 `BCP47FromLanguageID` 表中使用二分查找。该表合并了 Mac Language Designator（0-151）和 Windows LCID（0x0401-0x540A），按 languageID 值升序排列
3. **未知语言 ID**：返回 `"und"`（undetermined）

### 内存安全

所有数据读取使用 `memcpy` 而非指针强制转换，因为 name 表数据可能未对齐。每步都进行边界检查，防止越界读取。

### 字节序处理

所有结构体中的枚举值在编译期通过 `SkTEndian_SwapBE16` 转为大端表示，确保可以直接与从文件读取的原始数据比较，无需运行时转换。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkOTTableTypes.h` | 基本 OpenType 类型（SK_OT_USHORT、SK_OT_ULONG 等） |
| `SkEndian.h` | 字节序宏 `SkTEndian_SwapBE16`、`SkEndian_SwapBE16` |
| `SkString.h` | UTF-8 字符串类 |
| `SkUTF.h` | UTF-16 代理对检测（`IsLeadingSurrogateUTF16`、`IsTrailingSurrogateUTF16`） |
| `SkTSearch.h` | 模板化二分查找 `SkTSearch` |
| `SkStringUtils.h` | 字符串工具 |

## 设计模式与设计决策

1. **Pack 对齐 (#pragma pack(push, 1))**：name 表结构体严格按 1 字节对齐，确保与二进制文件格式的精确映射。Iterator 类在 `#pragma pack(pop)` 之后定义，不受此限制。

2. **编译期字节序转换**：所有枚举值使用 `SkTEndian_SwapBE16` 在编译期转换为大端存储，使得运行时比较操作无需额外的字节序转换，直接与原始字体数据匹配。

3. **union 类型的多态字段**：`EncodingID`、`LanguageID`、`NameID` 使用 union 根据上下文（如 PlatformID）解释相同的二进制数据，精确反映了 OpenType 规范中的条件语义。

4. **安全解析**：`Iterator::next()` 对每个偏移和长度都进行边界检查，使用 `memcpy` 避免未对齐访问，并在遇到不支持的编码时返回空字符串而非崩溃。

5. **合并语言表**：Mac 和 Windows 的语言 ID 映射合并为单一排序表 `BCP47FromLanguageID`，利用两组 ID 范围不重叠的特性简化查找逻辑。

6. **static_assert 验证**：在头文件末尾使用 `static_assert` 验证各结构体大小，确保 pack 对齐生效且结构布局与 OpenType 规范一致。

## 性能考量

- **二分查找语言映射**：`BCP47FromLanguageID` 表按 languageID 排序，使用 `SkTSearch` 进行 O(log n) 查找。表共约 350 条目，最多约 9 次比较。
- **编译期字节序转换**：避免了运行时的逐字段字节序转换开销，特别是在大量枚举值比较的场景中。
- **迭代器按需解码**：每次 `next()` 调用只解码一条记录的名称和语言，避免一次性处理整个 name 表的开销。
- **memcpy 读取**：虽然 memcpy 比直接指针访问稍慢，但保证了未对齐数据的正确读取，避免了某些架构上的对齐异常。
- **MacRoman 查找表**：128 项的静态数组实现 O(1) 字符映射，且数据量小（256 字节），对缓存友好。

## 相关文件

- `src/sfnt/SkOTTableTypes.h` — OpenType 基本类型定义
- `src/sfnt/SkOTUtils.h` / `.cpp` — 使用 name 表的工具函数（RenameFont、LocalizedStrings_NameTable）
- `src/sfnt/SkSFNTHeader.h` — SFNT 文件头结构
- `src/base/SkEndian.h` — 字节序转换宏
- `src/base/SkUTF.h` — UTF 编码工具
- `src/base/SkTSearch.h` — 模板二分查找
- `include/core/SkString.h` — Skia 字符串类
