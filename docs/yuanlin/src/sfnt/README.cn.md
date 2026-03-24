# src/sfnt - SFNT 字体表解析模块

## 概述

`src/sfnt` 是 Skia 中负责解析 SFNT（Spline Font / Scalable Font）格式字体文件的底层模块。SFNT 是 TrueType 和 OpenType 字体文件的通用容器格式，该模块提供了对字体文件中各种关键数据表的 C++ 结构化映射，使得 Skia 可以直接从字体二进制数据中读取元数据、度量信息和字形轮廓等关键数据。

该模块的设计哲学是"零拷贝直接映射"——所有数据结构都使用 `#pragma pack(push, 1)` 精确控制内存布局，使其与字体文件中的二进制格式一一对应。所有数值字段使用大端字节序的自定义类型（以 `SK_OT_` 为前缀），配合 `SkEndian` 工具实现跨平台的字节序转换。这种设计允许 Skia 将字体文件数据直接强制转换为 C++ 结构体指针，无需额外的解析和转换步骤，从而实现了极高的解析效率。

本模块覆盖了 OpenType 规范中最核心的数据表，包括：文件头解析（`SkSFNTHeader`、`SkTTCFHeader`）、字体元数据（`head`、`name`、`OS/2`）、字形度量（`hhea`、`hmtx`、`maxp`）、字形轮廓（`glyf`、`loca`）、网格拟合控制（`gasp`）、嵌入式位图（`EBDT`、`EBLC`、`EBSC`）、可变字体（`fvar`）以及彩色位图字体（`sbix`）等。此外还包含了 PANOSE 字体分类系统和 IBM 字体族分类的完整定义。

该模块被 Skia 的字体后端（如 FreeType、CoreText、DirectWrite 等平台特定实现）广泛使用，用于提取字体名称、检测字体属性、计算度量信息等操作。

## 架构图

```
+-------------------------------------------------------------------+
|                    字体文件 (TrueType / OpenType)                   |
|  .ttf / .otf / .ttc 二进制数据                                     |
+-------------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
|                     SkSFNTHeader / SkTTCFHeader                    |
|  字体类型识别 (TrueType/OpenType CFF/TTC集合)                      |
|  表目录解析 (TableDirectoryEntry[numTables])                        |
+-------------------------------------------------------------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
  +---------------+   +---------------+   +---------------+
  | 元数据表       |   | 度量信息表     |   | 字形数据表     |
  | head (头部)    |   | hhea (水平头)  |   | glyf (字形)   |
  | name (名称)    |   | hmtx (水平度量)|   | loca (定位)   |
  | OS/2 (V0~V4)  |   | maxp (最大值)  |   | EBDT (位图)   |
  | gasp (网格拟合) |   | post (PostScript)|  | EBLC (位图定位)|
  | fvar (可变轴)  |   |               |   | sbix (彩色位图)|
  +---------------+   +---------------+   +---------------+
          |
          v
  +-------------------------------------------------------------------+
  |                         SkOTUtils                                  |
  |  CalcTableChecksum() - 校验和计算                                   |
  |  RenameFont() - 字体重命名                                         |
  |  LocalizedStrings_NameTable - 本地化字符串迭代                       |
  |  SetAdvancedTypefaceFlags() - 高级字体属性设置                       |
  +-------------------------------------------------------------------+
          |
          v
  +-------------------------------------------------------------------+
  |              Skia 字体后端 (SkTypeface 子类)                        |
  |  SkTypeface_FreeType / SkTypeface_Mac / SkTypeface_Win             |
  +-------------------------------------------------------------------+
```

## 目录结构

```
src/sfnt/
|-- BUILD.bazel                # Bazel 构建配置
|-- SkSFNTHeader.h             # SFNT 文件头和表目录结构
|-- SkTTCFHeader.h             # TrueType Collection 文件头
|-- SkOTTableTypes.h           # OpenType 基础数据类型定义
|-- SkOTTable_head.h           # 'head' 表 - 字体头部信息
|-- SkOTTable_name.h/.cpp      # 'name' 表 - 字体名称和本地化字符串
|-- SkOTTable_OS_2.h           # 'OS/2' 表 - 聚合入口（含所有版本）
|-- SkOTTable_OS_2_VA.h        # 'OS/2' 表 - Apple 原始版本
|-- SkOTTable_OS_2_V0.h        # 'OS/2' 表 - 版本 0
|-- SkOTTable_OS_2_V1.h        # 'OS/2' 表 - 版本 1
|-- SkOTTable_OS_2_V2.h        # 'OS/2' 表 - 版本 2
|-- SkOTTable_OS_2_V3.h        # 'OS/2' 表 - 版本 3
|-- SkOTTable_OS_2_V4.h        # 'OS/2' 表 - 版本 4
|-- SkOTTable_hhea.h           # 'hhea' 表 - 水平头部信息
|-- SkOTTable_hmtx.h           # 'hmtx' 表 - 水平度量数据
|-- SkOTTable_maxp.h           # 'maxp' 表 - 最大值概要
|-- SkOTTable_maxp_TT.h        # 'maxp' 表 - TrueType 版本
|-- SkOTTable_maxp_CFF.h       # 'maxp' 表 - CFF 版本
|-- SkOTTable_glyf.h           # 'glyf' 表 - 字形轮廓数据
|-- SkOTTable_loca.h           # 'loca' 表 - 字形定位索引
|-- SkOTTable_post.h           # 'post' 表 - PostScript 名称
|-- SkOTTable_gasp.h           # 'gasp' 表 - 网格拟合和扫描过程
|-- SkOTTable_fvar.h           # 'fvar' 表 - 可变字体轴定义
|-- SkOTTable_EBDT.h           # 'EBDT' 表 - 嵌入式位图数据
|-- SkOTTable_EBLC.h           # 'EBLC' 表 - 嵌入式位图定位
|-- SkOTTable_EBSC.h           # 'EBSC' 表 - 嵌入式位图缩放
|-- SkOTTable_sbix.h           # 'sbix' 表 - 标准位图图形 (Apple)
|-- SkPanose.h                 # PANOSE 字体分类系统
|-- SkIBMFamilyClass.h         # IBM 字体族分类
|-- SkOTUtils.h/.cpp           # OpenType 工具函数
```

## 关键类与函数

### SkSFNTHeader（SFNT 文件头）
```cpp
struct SkSFNTHeader {
    SK_SFNT_ULONG fontType;       // 字体类型标签
    SK_SFNT_USHORT numTables;     // 表数量
    SK_SFNT_USHORT searchRange;   // 二分查找范围
    SK_SFNT_USHORT entrySelector; // 二分查找选择器
    SK_SFNT_USHORT rangeShift;    // 范围偏移

    struct TableDirectoryEntry {
        SK_SFNT_ULONG tag;            // 表标签（如 'head', 'name'）
        SK_SFNT_ULONG checksum;       // 校验和
        SK_SFNT_ULONG offset;         // 从文件头开始的偏移量
        SK_SFNT_ULONG logicalLength;  // 逻辑长度
    };
};
```
SFNT 文件头是解析字体文件的起点。通过 `fontType` 字段区分四种字体类型：
- `fontType_WindowsTrueType` (0x00010000) - Windows TrueType
- `fontType_MacTrueType` ('true') - Mac TrueType
- `fontType_PostScript` ('typ1') - PostScript Type 1
- `fontType_OpenTypeCFF` ('OTTO') - OpenType CFF

### SkTTCFHeader（TTC 集合文件头）
```cpp
struct SkTTCFHeader {
    SK_SFNT_ULONG ttcTag;      // 'ttcf' 标签
    SK_OT_Fixed version;        // 版本号 (1.0 或 2.0)
    SK_OT_ULONG numOffsets;     // 字体偏移量数组
    // SK_OT_ULONG offset[numOffsets] 紧随其后
    struct Version2Ext {        // 版本2扩展：DSIG签名
        SK_OT_ULONG dsigType;
        SK_OT_ULONG dsigLength;
        SK_OT_ULONG dsigOffset;
    };
};
```
TrueType Collection（.ttc）文件允许将多个字体打包到一个文件中。SkTTCFHeader 解析集合头部，提供对每个子字体的偏移定位。

### SkOTTableHead（'head' 表）
```cpp
struct SkOTTableHead {
    SK_OT_Fixed version;              // 表版本
    SK_OT_Fixed fontRevision;         // 字体修订号
    SK_OT_ULONG checksumAdjustment;   // 校验和调整值
    SK_OT_ULONG magicNumber;          // 魔数 0x5F0F3CF5
    union Flags { ... } flags;        // 字体标志位
    SK_OT_USHORT unitsPerEm;          // 每 Em 的设计单位数
    SK_OT_LONGDATETIME created;       // 创建时间
    SK_OT_LONGDATETIME modified;      // 修改时间
    SK_OT_SHORT xMin, yMin, xMax, yMax;  // 全局边界框
    union MacStyle { ... } macStyle;  // Mac 样式标志（粗体、斜体等）
    SK_OT_USHORT lowestRecPPEM;       // 最低推荐像素/Em
    struct IndexToLocFormat { ... };  // loca 表偏移格式（短/长）
};
```
'head' 表包含字体的全局属性。`unitsPerEm` 是最关键的值之一，它定义了字体设计空间到实际渲染空间的转换比例。`IndexToLocFormat` 决定了 'loca' 表中使用短偏移（2字节）还是长偏移（4字节）。

### SkOTTableName（'name' 表）
```cpp
struct SkOTTableName {
    SK_OT_USHORT format;     // 格式版本 (0 或 1)
    SK_OT_USHORT count;      // 名称记录数量
    SK_OT_USHORT stringOffset;  // 字符串存储区偏移

    struct Record {
        struct PlatformID { ... };    // 平台 (Unicode/Mac/Windows)
        union EncodingID { ... };     // 编码方式
        union LanguageID { ... };     // 语言标识
        union NameID { ... };         // 名称类型 (字体族名、样式名等)
        SK_OT_USHORT length;         // 字符串长度
        SK_OT_USHORT offset;         // 字符串偏移
    };

    class Iterator {                  // 名称记录遍历器
        bool next(Record&);
    };
};
```
'name' 表存储字体的所有可读名称（字体族名、设计师名、许可证等），支持多平台、多编码、多语言的名称记录。`NameID::Predefined` 枚举定义了标准名称类型，包括 `FontFamilyName`、`PostscriptName`、`WWSFamilyName` 等。Iterator 类提供了跨平台的名称遍历功能。

### SkOTTableOS2（'OS/2' 表）
```cpp
struct SkOTTableOS2 {
    union Version {
        SK_OT_USHORT version;
        struct VA : SkOTTableOS2_VA { } vA;  // Apple 原始 (68 字节)
        struct V0 : SkOTTableOS2_V0 { } v0;  // 版本 0 (78 字节)
        struct V1 : SkOTTableOS2_V1 { } v1;  // 版本 1 (86 字节)
        struct V2 : SkOTTableOS2_V2 { } v2;  // 版本 2 (96 字节)
        struct V3 : SkOTTableOS2_V3 { } v3;  // 版本 3 (96 字节)
        struct V4 : SkOTTableOS2_V4 { } v4;  // 版本 4 (96 字节)
    } version;
};
```
'OS/2' 表是最复杂的 OpenType 表之一，包含字体的跨平台度量和分类信息。Skia 为每个版本提供了独立的结构体，通过 union 统一访问。该表包含字重、字宽、字体类型许可、PANOSE 分类、Unicode 范围位图、厂商 ID 等大量关键元数据。

### SkOTTableGlyph / SkOTTableGlyphData（'glyf' 表）
```cpp
struct SkOTTableGlyphData {
    SK_OT_SHORT numberOfContours;  // -1 表示复合字形，>0 表示简单字形
    SK_OT_FWORD xMin, yMin, xMax, yMax;  // 字形边界框

    struct Simple {                // 简单字形
        SK_OT_USHORT endPtsOfContours[];  // 每个轮廓的终点索引
        struct Instructions { ... };       // TrueType 指令
        union Flags { ... };              // 点标志（曲线/直线）
    };

    struct Composite {             // 复合字形
        struct Component {
            union Flags { ... };          // 组件标志
            SK_OT_USHORT glyphIndex;      // 引用的字形索引
            union Transform { ... };      // 变换矩阵
        };
    };
};
```
'glyf' 表包含所有字形的轮廓数据。简单字形由一组轮廓点组成，每个点标记为曲线点或直线点。复合字形通过引用其他字形并应用变换矩阵来构建，支持缩放、旋转和平移。

### SkOTTableGridAndScanProcedure（'gasp' 表）
```cpp
struct SkOTTableGridAndScanProcedure {
    SK_OT_USHORT version;
    SK_OT_USHORT numRanges;
    struct GaspRange {
        SK_OT_USHORT maxPPEM;     // 该范围的最大像素/Em
        union behavior {
            Gridfit,               // 网格拟合
            DoGray,                // 灰度抗锯齿
            SymmetricGridfit,      // 对称网格拟合 (v1)
            SymmetricSmoothing,    // 对称平滑 (v1)
        } flags;
    };
};
```
'gasp' 表控制不同字号下的字形光栅化策略，指定何时使用网格拟合和灰度抗锯齿。

### SkPanose（PANOSE 分类）
```cpp
struct SkPanose {
    enum class FamilyType : SK_OT_BYTE {
        TextAndDisplay, Script, Decorative, Pictoral
    } bFamilyType;

    union Data {
        struct TextAndDisplay {
            SerifStyle, Weight, Proportion, Contrast,
            StrokeVariation, ArmStyle, Letterform, Midline, XHeight
        };
        struct Script { ... };
        struct Decorative { ... };
        struct Pictoral { ... };
    } data;
};
```
PANOSE 是一个10字节的字体分类系统。第一个字节（FamilyType）决定后续9个字节的含义。对于最常见的 TextAndDisplay 类型，分类维度包括：衬线样式、字重、比例、对比度、笔画变化、手臂样式、字母形态、中线和 x 高度。

### SkOTUtils（OpenType 工具）
```cpp
struct SkOTUtils {
    static uint32_t CalcTableChecksum(SK_OT_ULONG* data, size_t length);
    static SkData* RenameFont(SkStreamAsset* fontData,
                              const char* fontName, int fontNameLen);
    class LocalizedStrings_NameTable : public SkTypeface::LocalizedStrings { ... };
    class LocalizedStrings_SingleName : public SkTypeface::LocalizedStrings { ... };
    static void SetAdvancedTypefaceFlags(SkOTTableOS2_V4::Type fsType,
                                         SkAdvancedTypefaceMetrics* info);
};
```
SkOTUtils 提供了一组实用工具函数。`CalcTableChecksum` 计算 OpenType 表校验和用于验证数据完整性。`RenameFont` 通过替换 'name' 表实现字体重命名。`LocalizedStrings_NameTable` 是 `SkTypeface::LocalizedStrings` 的实现，提供从 'name' 表中遍历本地化字体名称的能力。

### SkOTTableTypes（基础类型系统）
```cpp
typedef uint8_t  SK_OT_BYTE;
typedef int8_t   SK_OT_CHAR;
typedef uint16_t SK_OT_SHORT, SK_OT_USHORT;
typedef uint32_t SK_OT_ULONG, SK_OT_LONG;
typedef int32_t  SK_OT_Fixed;       // 16.16 有符号定点数
typedef uint16_t SK_OT_F2DOT14;     // 2.14 有符号定点数
typedef uint16_t SK_OT_FWORD;       // 字体设计单位
typedef uint64_t SK_OT_LONGDATETIME; // 1904年1月1日以来的秒数

template<typename T> class SkOTTableTAG {
    static const SK_OT_ULONG value;  // 大端序的四字节标签
};
```
所有 `SK_OT_` 前缀的类型均为大端字节序，与字体文件中的二进制格式直接对应。`SkOTTableTAG` 模板类通过类型的 `TAG0`~`TAG3` 静态常量自动计算大端序标签值。

## 依赖关系

### 上游依赖
- `src/base/SkEndian.h` - 字节序转换工具（`SkTEndian_SwapBE16/32`）
- `include/core/SkFourByteTag.h` - 四字节标签工具
- `include/core/SkString.h` - 字符串类型（用于 name 表解析）
- `include/core/SkTypeface.h` - SkTypeface::LocalizedStrings 接口
- `include/core/SkTypes.h` - 基础类型定义

### 下游消费者
- `src/ports/SkTypeface_*.cpp` - 各平台字体后端实现
- `src/core/SkAdvancedTypefaceMetrics.h` - 高级字体度量提取
- `src/pdf/` - PDF 输出中的字体嵌入
- `tools/fonts/` - 字体测试和工具

## 设计模式分析

### 零拷贝映射模式（Memory-Mapped Struct Pattern）
整个模块最核心的设计模式。通过 `#pragma pack(push, 1)` 和 `static_assert` 确保 C++ 结构体的内存布局与二进制格式完全一致，允许直接的 `reinterpret_cast` 操作。例如 `static_assert(sizeof(SkOTTableHead) == 54)` 确保了 head 表的精确映射。

### 标签分发模式（Tag Dispatch Pattern）
`SkOTTableTAG` 模板类通过每个表结构的 `TAG0`~`TAG3` 静态常量在编译时计算标签值，实现了类型安全的表标识。这种方式将运行时的字符串比较转化为编译时的常量计算。

### 版本化联合体模式（Versioned Union Pattern）
`SkOTTableOS2` 使用联合体（union）统一管理从 VA 到 V4 的所有版本，通过版本字段选择正确的结构体解释。这种设计优雅地处理了 OpenType 规范中表结构随版本演进的问题。

### 位域映射模式（Bitfield Mapping Pattern）
许多表（如 head 的 Flags 和 MacStyle）同时提供 `Field`（位域结构）和 `Raw`（掩码常量）两种访问方式，前者便于代码可读性，后者便于位运算操作。

### 迭代器模式（Iterator Pattern）
`SkOTTableName::Iterator` 和 `SkOTTableGlyph::Iterator` 提供了对复杂变长数据结构的顺序遍历能力，封装了偏移计算和边界检查的细节。

## 数据流

```
1. 字体文件加载
   SkStreamAsset 提供字体二进制数据流
        |
        v
2. 文件头解析
   SkSFNTHeader: 识别字体类型 + 读取表目录
   SkTTCFHeader: 若为 TTC 集合，读取各字体偏移
        |
        v
3. 表定位
   通过 TableDirectoryEntry.tag 匹配所需表
   通过 TableDirectoryEntry.offset 定位表数据
   通过 CalcTableChecksum() 验证数据完整性
        |
        v
4. 数据提取 (根据需要)
   SkOTTableHead    --> unitsPerEm, 全局边界框, 标志位
   SkOTTableName    --> 字体族名, 样式名, 本地化名称
   SkOTTableOS2     --> 字重, 字宽, PANOSE 分类, 许可类型
   SkOTTableGlyph   --> 字形轮廓 (简单/复合)
   SkOTTable_hhea   --> 上升/下降度量, 行间距
   SkOTTable_hmtx   --> 每个字形的水平度量
        |
        v
5. 数据消费
   SkTypeface 子类使用提取的数据:
   - 字体匹配和选择 (名称, 样式, 分类)
   - 度量计算 (行高, 字符宽度)
   - 字形渲染 (轮廓, 位图)
   - PDF 字体嵌入 (子集化, 重命名)
```

## 相关文档与参考

- [OpenType 规范](https://docs.microsoft.com/en-us/typography/opentype/spec/) - 微软官方 OpenType 规范
- [TrueType 参考手册](https://developer.apple.com/fonts/TrueType-Reference-Manual/) - Apple TrueType 参考
- [PANOSE 分类系统](https://monotype.github.io/panose/) - PANOSE 字体分类标准
- `src/ports/SkTypeface_FreeType.cpp` - FreeType 字体后端（使用本模块）
- `src/ports/SkTypeface_mac_ct.cpp` - macOS CoreText 字体后端
- `src/core/SkAdvancedTypefaceMetrics.h` - 高级字体度量提取
- `include/core/SkTypeface.h` - SkTypeface 公共 API
- `src/pdf/SkPDFFont.cpp` - PDF 字体嵌入（使用本模块进行子集化）
