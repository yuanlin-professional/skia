# SkOTTableOS2_V1

> 源文件: src/sfnt/SkOTTable_OS_2_V1.h

## 概述

`SkOTTable_OS_2_V1.h` 定义了 OpenType 字体中 OS/2 表的版本 1 结构。OS/2 表是 OpenType 和 TrueType 字体格式中最重要的表之一,包含字体的度量信息、字符集支持、字重、字宽、字体类型等关键元数据。版本 1 在版本 0 的基础上增加了代码页范围(Code Page Range)支持。

该表最初由 Microsoft 和 Adobe 联合开发,用于支持 Windows 和 OS/2 操作系统的字体渲染需求。现代字体系统广泛依赖该表提供的信息来正确显示和匹配字体。

## 架构位置

```
Skia 字体系统
└── src/sfnt/ (OpenType 字体表格支持)
    ├── SkOTTableTypes.h (基础类型)
    ├── SkPanose.h (PANOSE 分类)
    ├── SkIBMFamilyClass.h (IBM 字体分类)
    ├── SkOTTable_OS_2.h (OS/2 表统一接口)
    ├── SkOTTable_OS_2_V0.h (版本 0)
    ├── SkOTTable_OS_2_V1.h (版本 1) ←
    ├── SkOTTable_OS_2_V2.h (版本 2)
    ├── SkOTTable_OS_2_V3.h (版本 3)
    └── SkOTTable_OS_2_V4.h (版本 4)
```

## 主要类与结构体

### SkOTTableOS2_V1 (主结构)

```cpp
struct SkOTTableOS2_V1 {
    SK_OT_USHORT version;  // 版本号 = 1
    static const SK_OT_USHORT VERSION = SkTEndian_SwapBE16(1);

    SK_OT_SHORT xAvgCharWidth;      // 平均字符宽度
    WeightClass usWeightClass;       // 字重类别
    WidthClass usWidthClass;         // 字宽类别
    Type fsType;                     // 字体类型
    // ... (更多字段)
};
```

**关键特性**:
- 版本号: 1
- 总大小: 86 字节
- 新增: `ulCodePageRange` 字段(相比版本 0)

### WeightClass (字重类别)

```cpp
struct WeightClass {
    enum Value : SK_OT_USHORT {
        Thin = SkTEndian_SwapBE16(100),
        ExtraLight = SkTEndian_SwapBE16(200),
        Light = SkTEndian_SwapBE16(300),
        Normal = SkTEndian_SwapBE16(400),
        Medium = SkTEndian_SwapBE16(500),
        SemiBold = SkTEndian_SwapBE16(600),
        Bold = SkTEndian_SwapBE16(700),
        ExtraBold = SkTEndian_SwapBE16(800),
        Black = SkTEndian_SwapBE16(900),
    };
    SK_OT_USHORT value;
};
```

**用途**: 定义字体的粗细程度,影响字体匹配和渲染

### WidthClass (字宽类别)

```cpp
struct WidthClass {
    enum Value : SK_OT_USHORT {
        UltraCondensed = SkTEndian_SwapBE16(1),  // 超窄
        ExtraCondensed = SkTEndian_SwapBE16(2),  // 特窄
        Condensed = SkTEndian_SwapBE16(3),       // 窄
        SemiCondensed = SkTEndian_SwapBE16(4),   // 半窄
        Medium = SkTEndian_SwapBE16(5),          // 中等
        SemiExpanded = SkTEndian_SwapBE16(6),    // 半宽
        Expanded = SkTEndian_SwapBE16(7),        // 宽
        ExtraExpanded = SkTEndian_SwapBE16(8),   // 特宽
        UltraExpanded = SkTEndian_SwapBE16(9),   // 超宽
    };
};
```

**应用**: 用于字体的宽度分类,支持凝聚体和扩展体

### Type (字体类型标志)

```cpp
union Type {
    struct Field {
        // 位字段定义
        SK_OT_BYTE_BITFIELD(
            Reserved00,
            Restricted,    // 受限许可
            PreviewPrint,  // 仅预览/打印
            Editable,      // 可编辑
            ...
        )
    } field;
    struct Raw {
        static const SK_OT_USHORT Installable = 0;  // 可安装
        static const SK_OT_USHORT RestrictedMask = SkOTSetUSHORTBit<1>::value;
        static const SK_OT_USHORT PreviewPrintMask = SkOTSetUSHORTBit<2>::value;
        static const SK_OT_USHORT EditableMask = SkOTSetUSHORTBit<3>::value;
        SK_OT_USHORT value;
    } raw;
};
```

**功能**: 定义字体的使用许可和嵌入权限

### UnicodeRange (Unicode 范围)

128 位标志位(4 × 32位),标识字体支持的 Unicode 字符范围:

```cpp
union UnicodeRange {
    struct Field {
        // l0: 基本拉丁文、希腊文、西里尔文等
        // l1: 符号、CJK 符号、假名、谚文等
        // l2: 兼容性表意文字、特殊符号
        // l3: 保留位
    } field;
    struct Raw {
        SK_OT_ULONG value[4];  // 128 位标志
    } raw;
};
```

**关键范围**:
- **基本拉丁文** (bit 0): U+0020-U+007F
- **CJK 统一表意文字** (bit 59): U+4E00-U+9FFF
- **谚文** (bit 56): 韩文字符
- **假名** (bit 49-50): 日文平假名和片假名

### CodePageRange (代码页范围) - V1 新增

64 位标志位(2 × 32位),标识字体支持的传统代码页:

```cpp
union CodePageRange {
    struct Field {
        // l0: Windows 代码页(1252, 1250, 1251 等)
        //     东亚代码页(932, 936, 949, 950)
        //     特殊字符集(Macintosh, OEM, Symbol)
        // l1: DOS 代码页(437, 850, 852, 860-869 等)
    } field;
    struct Raw {
        struct l0 {
            static const SK_OT_ULONG Latin1_1252Mask = ...;
            static const SK_OT_ULONG JISJapan_932Mask = ...;
            static const SK_OT_ULONG ChineseSimplified_936Mask = ...;
            // ...
        };
        struct l1 {
            static const SK_OT_ULONG US_437Mask = ...;
            static const SK_OT_ULONG WELatin1_850Mask = ...;
            // ...
        };
        SK_OT_ULONG value[2];
    } raw;
};
```

**用途**: 向后兼容传统代码页系统,支持旧版应用

### Selection (选择标志)

```cpp
union Selection {
    struct Field {
        SK_OT_BYTE_BITFIELD(
            Italic,      // 斜体
            Underscore,  // 下划线
            Negative,    // 反色
            Outlined,    // 轮廓
            Strikeout,   // 删除线
            Bold,        // 粗体
            Regular,     // 常规
            ...
        )
    } field;
    struct Raw {
        static const SK_OT_USHORT ItalicMask = SkOTSetUSHORTBit<0>::value;
        static const SK_OT_USHORT BoldMask = SkOTSetUSHORTBit<5>::value;
        SK_OT_USHORT value;
    } raw;
};
```

**应用**: 指示字体的样式属性

## 公共 API 函数

该文件是纯数据结构定义,典型使用方式:

```cpp
// 读取 OS/2 表
const SkOTTableOS2_V1* os2Table =
    typeface->getTableData<SkOTTableOS2_V1>(
        SkOTTableOS2::TAG);

// 获取字重
uint16_t weight = SkEndian_SwapBE16(os2Table->usWeightClass.value);

// 检查 Unicode 范围支持
bool supportsCJK = os2Table->ulUnicodeRange.raw.value[1] &
    SkEndian_SwapBE32(SkOTTableOS2_V1::UnicodeRange::Raw::l1::CJKUnifiedIdeographsMask);

// 获取代码页支持
bool supportsGB2312 = os2Table->ulCodePageRange.raw.value[0] &
    SkEndian_SwapBE32(SkOTTableOS2_V1::CodePageRange::Raw::l0::ChineseSimplified_936Mask);
```

## 内部实现细节

### 内存布局

```cpp
#pragma pack(push, 1)  // 紧凑打包
```

结构体大小精确为 86 字节:
```cpp
static_assert(sizeof(SkOTTableOS2_V1) == 86,
    "sizeof_SkOTTableOS2_V1_not_86");
```

### 字段偏移

- **0-1**: version
- **2-3**: xAvgCharWidth
- **4-5**: usWeightClass
- **6-7**: usWidthClass
- **8-9**: fsType
- **10-23**: 上标/下标度量
- **24-25**: sFamilyClass
- **26-35**: PANOSE 分类
- **36-51**: ulUnicodeRange (16 字节)
- **52-55**: achVendID
- **56-57**: fsSelection
- **58-77**: 字符索引和度量
- **78-85**: ulCodePageRange (8 字节) ← V1 新增

### 位字段处理

位字段使用 `SK_OT_BYTE_BITFIELD` 宏定义:
- 确保跨平台的位排列一致性
- 支持大端序存储格式
- 提供字段级和原始值两种访问方式

### 大端序转换

所有多字节值都是大端序,访问时需转换:
```cpp
uint16_t weight = SkEndian_SwapBE16(os2->usWeightClass.value);
```

## 依赖关系

```
SkOTTable_OS_2_V1.h
├── src/base/SkEndian.h (字节序转换)
├── src/sfnt/SkIBMFamilyClass.h (IBM 字体分类)
├── src/sfnt/SkOTTableTypes.h (基础类型)
└── src/sfnt/SkPanose.h (PANOSE 分类系统)
```

**被依赖方**:
- `SkOTTable_OS_2.h` - OS/2 表版本联合体
- 字体匹配算法
- 字体度量计算
- 字符集检测

## 设计模式与设计决策

### 1. 版本演进设计

- **V0 → V1**: 增加代码页范围支持
- **向后兼容**: 版本字段允许运行时识别
- **独立定义**: 每个版本有单独的结构体

### 2. 联合体(Union)设计

优势:
- **双重访问**: 字段级访问 vs 原始位操作
- **类型安全**: 枚举值提供编译时检查
- **调试友好**: 字段名增强可读性

### 3. 位掩码模板

使用 `SkOTSetUSHORTBit` 和 `SkOTSetULONGBit`:
- 编译时计算位掩码
- 自动处理字节序
- 零运行时开销

### 4. 多字节标志位数组

`ulUnicodeRange` 和 `ulCodePageRange` 使用数组:
- 支持大量标志位(128位 + 64位)
- 保持内存布局连续
- 便于批量检查

## 性能考量

### 直接内存映射

结构体可直接映射到文件数据:
```cpp
const SkOTTableOS2_V1* os2 =
    reinterpret_cast<const SkOTTableOS2_V1*>(tableData);
```

**优势**:
- 零拷贝访问
- 无需解析开销
- 缓存友好

### 字节序转换

- 仅在访问时转换,不修改原始数据
- 现代 CPU 的字节交换是单指令操作
- 可内联,编译器优化效果好

### 位操作效率

```cpp
// 高效的位检查
bool isItalic = os2->fsSelection.raw.value &
    SkOTTableOS2_V1::Selection::Raw::ItalicMask;
```

单次位与操作,极低开销。

### 缓存策略

OS/2 表通常较小(86字节),易于:
- 整表缓存在内存
- 减少重复磁盘访问
- 提高字体匹配速度

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/sfnt/SkOTTable_OS_2.h` | OS/2 表统一接口 | 包含此版本的联合体 |
| `src/sfnt/SkOTTable_OS_2_V0.h` | OS/2 表版本 0 | 前一版本 |
| `src/sfnt/SkOTTable_OS_2_V2.h` | OS/2 表版本 2 | 后续版本 |
| `src/sfnt/SkPanose.h` | PANOSE 分类 | 字段依赖 |
| `src/sfnt/SkIBMFamilyClass.h` | IBM 字体分类 | 字段依赖 |
| `src/ports/SkTypeface_*.cpp` | 平台字体实现 | 读取和使用此表 |
| `src/core/SkFontDescriptor.cpp` | 字体描述符 | 使用字重、字宽等信息 |
| `src/core/SkFontMgr_*.cpp` | 字体管理器 | 字体匹配算法 |

OS/2 表版本 1 是现代字体系统的核心组件,提供了字体分类、度量、字符集支持等关键信息,是字体匹配和渲染的重要基础。
