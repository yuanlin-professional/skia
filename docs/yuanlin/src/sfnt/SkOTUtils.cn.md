# SkOTUtils — OpenType 字体工具集

> 源文件：[src/sfnt/SkOTUtils.h](../../src/sfnt/SkOTUtils.h)、[src/sfnt/SkOTUtils.cpp](../../src/sfnt/SkOTUtils.cpp)

## 概述

`SkOTUtils` 是一个 OpenType/SFNT 字体工具结构体，提供了一组静态方法和内部类，用于操作 OpenType 字体的底层数据。其核心功能包括：

- 计算 OpenType 表的校验和（checksum）
- 重命名 SFNT 字体（替换 `name` 表）
- 从字体的 `name` 表中迭代读取本地化字符串（如字体家族名称）
- 根据 OS/2 表中的 `fsType` 字段设置高级字体排版标志位

该工具集主要服务于 Skia 的字体子系统，在字体加载、嵌入（embedding）和元数据读取等场景中被广泛使用。

## 架构位置

`SkOTUtils` 位于 Skia 字体处理的 SFNT 层（`src/sfnt/`），处于字体文件解析与上层字体抽象（如 `SkTypeface`）之间的中间层位置。

```
SkTypeface (上层字体抽象)
    │
    ├── SkTypeface::LocalizedStrings (接口)
    │       ▲
    │       ├── LocalizedStrings_NameTable (从 name 表获取)
    │       └── LocalizedStrings_SingleName (单一名称)
    │
    ├── SkOTUtils (工具层)
    │       ├── CalcTableChecksum()
    │       ├── RenameFont()
    │       └── SetAdvancedTypefaceFlags()
    │
    └── SFNT 数据层 (SkSFNTHeader, SkOTTableName, SkOTTableHead...)
```

## 主要类与结构体

### `SkOTUtils`（结构体）

顶层工具结构体，所有成员均为静态方法或嵌套类。本身无实例数据，仅作为命名空间使用。

### `SkOTUtils::LocalizedStrings_NameTable`

继承自 `SkTypeface::LocalizedStrings`，实现了从 OpenType `name` 表中迭代读取本地化字符串的功能。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTypes` | `SK_OT_USHORT*` | 需要查询的 NameID 类型数组 |
| `fTypesCount` | `int` | 类型数组的长度 |
| `fTypesIndex` | `int` | 当前正在迭代的类型索引 |
| `fNameTableData` | `std::unique_ptr<uint8_t[]>` | name 表原始数据的所有权 |
| `fFamilyNameIter` | `SkOTTableName::Iterator` | name 表记录迭代器 |
| `familyNameTypes[3]` | `SK_OT_USHORT[]`（静态） | 预定义的家族名称 NameID 类型数组 |

`familyNameTypes` 包含三个 NameID：`FontFamilyName`、`PreferredFamily`、`WWSFamilyName`，用于全面查找字体家族名称。

### `SkOTUtils::LocalizedStrings_SingleName`

继承自 `SkTypeface::LocalizedStrings`，是一个只包含单个名称的简单迭代器实现。第一次调用 `next()` 返回该名称，之后返回 `false`。

## 公共 API 函数

### `CalcTableChecksum(SK_OT_ULONG *data, size_t length) -> uint32_t`

计算 OpenType 表的校验和。按照 OpenType 规范，将数据按 4 字节 ULONG 进行大端累加。对齐时将 `length` 向上取整为 4 的倍数。

### `RenameFont(SkStreamAsset* fontData, const char* fontName, int fontNameLen) -> SkData*`

重命名 SFNT 字体。读取原始字体数据流，移除旧的 `name` 表，构建包含指定名称的新 `name` 表。新 `name` 表中包含以下五个必需记录：

1. FontFamilyName
2. FontSubfamilyName
3. UniqueFontIdentifier
4. FullFontName
5. PostscriptName

所有记录均使用 Windows 平台、UnicodeBMPUCS2 和 Symbol 编码，语言为 English_UnitedStates。函数还会更新表目录中的偏移量和校验和，以及 `head` 表中的 checksumAdjustment。

**返回值**：成功时返回新字体数据的 `SkData*`（调用者拥有所有权），失败时返回 `nullptr`。

### `LocalizedStrings_NameTable::Make(const SkTypeface& typeface, SK_OT_USHORT types[], int typesCount) -> sk_sp<LocalizedStrings_NameTable>`

工厂方法。从给定的 `SkTypeface` 中读取 `name` 表数据，构造迭代器。如果无法找到有效的 `name` 表则返回 `nullptr`。

### `LocalizedStrings_NameTable::MakeForFamilyNames(const SkTypeface& typeface) -> sk_sp<LocalizedStrings_NameTable>`

便捷工厂方法。使用预定义的 `familyNameTypes`（FontFamilyName、PreferredFamily、WWSFamilyName）创建迭代器。

### `LocalizedStrings_NameTable::next(SkTypeface::LocalizedString*) -> bool`

迭代获取下一个本地化字符串。当一种 NameID 类型迭代完毕后，自动切换到下一个类型继续迭代。

### `SetAdvancedTypefaceFlags(SkOTTableOS2_V4::Type fsType, SkAdvancedTypefaceMetrics* info)`

根据 OS/2 表的 `fsType` 字段设置字体元数据中的嵌入和子集化标志。逻辑与 `SkTypeface_FreeType::onGetAdvancedMetrics()` 保持一致。

## 内部实现细节

### RenameFont 的实现流程

1. **读取 SFNT 头**：解析 `SkSFNTHeader`，获取表数量。
2. **定位 name 表**：遍历表目录查找 `name` 表的 tag。
3. **计算大小**：新 `name` 表大小 = 表头 + 记录数（2 编码 × 5 名称 = 10 条记录） + 字体名字符串（UTF-16BE）。物理大小向上对齐到 4 字节。
4. **复制数据**：分配新的 `SkData`，将原始数据（去掉旧 name 表）复制到新缓冲区。
5. **修正偏移量**：遍历表目录，对所有偏移量大于旧 name 表位置的条目减去旧表大小。
6. **写入新 name 表**：在数据末尾写入新的 name 表头、记录和字符串。
7. **更新校验和**：计算新 name 表的校验和并更新目录条目；重新计算全局 checksumAdjustment 并写入 `head` 表。

### 本地化字符串迭代

`LocalizedStrings_NameTable::next()` 使用双层迭代策略：内层通过 `SkOTTableName::Iterator` 遍历当前 NameID 类型的所有记录；外层在当前类型耗尽后递增 `fTypesIndex` 并重置迭代器到下一个类型。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkOTTableName` | name 表结构定义和迭代器 |
| `SkOTTableHead` | head 表结构（checksumAdjustment） |
| `SkSFNTHeader` | SFNT 文件头和表目录结构 |
| `SkOTTableOS2_V4` | OS/2 表 fsType 字段定义 |
| `SkOTTableTypes` | OpenType 基本类型定义（SK_OT_ULONG 等） |
| `SkData` | 不可变数据块，用于存储重命名后的字体 |
| `SkStream` | 流式读取原始字体数据 |
| `SkTypeface` | 上层字体抽象（LocalizedStrings 基类） |
| `SkAdvancedTypefaceMetrics` | 高级字体元数据标志位 |
| `SkEndian` | 字节序转换工具 |

## 设计模式与设计决策

1. **命名空间结构体模式**：`SkOTUtils` 作为结构体仅包含静态方法和嵌套类，充当命名空间的角色，将相关的 OpenType 工具函数组织在一起。

2. **迭代器模式**：`LocalizedStrings_NameTable` 继承 `SkTypeface::LocalizedStrings` 接口，提供 `next()` 方法逐条返回本地化字符串，支持多种 NameID 类型的自动链式迭代。

3. **工厂方法模式**：`Make()` 和 `MakeForFamilyNames()` 使用静态工厂方法构造对象，封装了从 `SkTypeface` 读取 name 表数据的复杂性。无效数据时返回 `nullptr` 而不是抛出异常。

4. **字体名称重写策略**：`RenameFont` 同时使用 Symbol 和 UnicodeBMPUCS2 两种编码写入名称记录，确保 GDI 在使用 Symbol cmap 表时仍能正确识别字体。

5. **所有权语义**：`RenameFont` 返回裸指针（调用者负责释放），而 `Make` 系列方法使用 `sk_sp` 智能指针管理生命周期，体现了 Skia 中新旧 API 风格的混合。

## 性能考量

- **CalcTableChecksum** 使用简单的线性遍历，时间复杂度 O(n)，其中 n 为表数据大小。长度按 4 字节对齐后按 ULONG 单位累加，减少循环次数。
- **RenameFont** 需要完整读取和重写整个字体文件数据，对于大字体文件（数 MB）可能产生显著的内存分配和拷贝开销。
- 迭代器模式避免了一次性将所有本地化字符串加载到内存中，适合按需逐条获取。

## 相关文件

- `src/sfnt/SkOTTable_name.h` / `.cpp` — name 表结构定义和迭代器实现
- `src/sfnt/SkOTTable_head.h` — head 表结构定义
- `src/sfnt/SkSFNTHeader.h` — SFNT 文件头和表目录结构
- `src/sfnt/SkOTTable_OS_2_V4.h` — OS/2 表 V4 结构定义
- `src/core/SkAdvancedTypefaceMetrics.h` — 高级字体元数据
- `include/core/SkTypeface.h` — 字体抽象基类（LocalizedStrings 接口）
