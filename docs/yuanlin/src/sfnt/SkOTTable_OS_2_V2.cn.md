# SkOTTable_OS_2_V2 - OpenType OS/2 表版本 2

> 源文件:
> - `src/sfnt/SkOTTable_OS_2_V2.h`

## 概述

`SkOTTable_OS_2_V2.h` 定义了 OpenType/TrueType 字体中 OS/2 表版本 2 的数据结构。OS/2 表（也称为 "OS/2 and Windows Metrics" 表）包含了 Windows 平台所需的各种字体度量信息，包括权重、宽度、嵌入许可、PANOSE 分类、Unicode 范围、代码页范围、排版度量等。

该结构体使用 `#pragma pack(push, 1)` 确保与字体文件中的二进制布局完全匹配，大小恰好为 96 字节。所有多字节字段使用大端序存储。

## 架构位置

```
src/sfnt/
  SkOTTable_OS_2.h       // OS/2 表版本选择器
  SkOTTable_OS_2_VA.h     // 版本 A（Apple 原始 TT）
  SkOTTable_OS_2_V0.h     // 版本 0
  SkOTTable_OS_2_V1.h     // 版本 1
  SkOTTable_OS_2_V2.h     // 版本 2 （本文件）
  SkOTTable_OS_2_V3.h     // 版本 3
  SkOTTable_OS_2_V4.h     // 版本 4
  SkOTTableTypes.h         // 基础类型定义
  SkPanose.h               // PANOSE 分类
  SkIBMFamilyClass.h       // IBM 字体族分类
```

## 主要类与结构体

### `SkOTTableOS2_V2`

完整的 OS/2 表版本 2 结构体（96 字节），使用 1 字节对齐打包。

**版本标识：**
```cpp
static const SK_OT_USHORT VERSION = SkTEndian_SwapBE16(2);
```

### 权重与宽度

**`WeightClass`：**

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `Thin` | 100 | 极细 |
| `ExtraLight` | 200 | 特细 |
| `Light` | 300 | 细 |
| `Normal` | 400 | 正常 |
| `Medium` | 500 | 中等 |
| `SemiBold` | 600 | 半粗 |
| `Bold` | 700 | 粗 |
| `ExtraBold` | 800 | 特粗 |
| `Black` | 900 | 黑 |

**`WidthClass`：**

从 `UltraCondensed(1)` 到 `UltraExpanded(9)`。

### 嵌入类型 (`fsType`)

通过位域或原始掩码访问：

| 标志 | 位 | 说明 |
|------|-----|------|
| `Restricted` | 1 | 限制嵌入 |
| `PreviewPrint` | 2 | 预览打印嵌入 |
| `Editable` | 3 | 可编辑嵌入 |
| `NoSubsetting` | 8 | 禁止子集化 |
| `Bitmap` | 9 | 仅位图嵌入 |

### Unicode 范围 (`ulUnicodeRange`)

128 位（4 个 ULONG），标识字体支持的 Unicode 块。通过 `Field`（位域）或 `Raw`（掩码常量）两种方式访问。

**部分关键范围（以 `Raw::l0` 为例）：**

| 掩码 | 说明 |
|------|------|
| `BasicLatinMask` | 基本拉丁 (U+0020-U+007E) |
| `CyrillicMask` | 西里尔文 |
| `ArabicMask` | 阿拉伯文 |
| `CJKUnifiedIdeographsMask` (l1) | CJK 统一表意文字 |
| `HangulMask` (l1) | 韩文 |

### 字体选择标志 (`fsSelection`)

| 标志 | 说明 |
|------|------|
| `Italic` | 斜体 |
| `Underscore` | 下划线 |
| `Negative` | 反色 |
| `Outlined` | 轮廓 |
| `Strikeout` | 删除线 |
| `Bold` | 粗体 |
| `Regular` | 正常 |

### 代码页范围 (`ulCodePageRange`)

64 位（2 个 ULONG），版本 1 新增。标识字体支持的代码页。

**部分关键代码页：**

| 掩码 (l0) | 说明 |
|-----------|------|
| `Latin1_1252Mask` | 拉丁 1 (1252) |
| `Cyrillic_1251Mask` | 西里尔文 (1251) |
| `JISJapan_932Mask` | 日文 Shift-JIS (932) |
| `ChineseSimplified_936Mask` | 简体中文 GBK (936) |
| `ChineseTraditional_950Mask` | 繁体中文 Big5 (950) |
| `KoreanWansung_949Mask` | 韩文 (949) |

### 版本 2 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `sxHeight` | SK_OT_SHORT | 小写字母 x 高度 |
| `sCapHeight` | SK_OT_SHORT | 大写字母高度 |
| `usDefaultChar` | SK_OT_USHORT | 默认字符 |
| `usBreakChar` | SK_OT_USHORT | 换行字符 |
| `usMaxContext` | SK_OT_USHORT | 最大上下文长度 |

### 排版度量（从版本 0 继承）

| 字段 | 说明 |
|------|------|
| `sTypoAscender` | 排版上升高度 |
| `sTypoDescender` | 排版下降高度 |
| `sTypoLineGap` | 排版行间距 |
| `usWinAscent` | Windows 上升 |
| `usWinDescent` | Windows 下降 |

## 依赖关系

- `src/base/SkEndian.h` - 大端序转换宏 `SkTEndian_SwapBE16`
- `src/sfnt/SkOTTableTypes.h` - `SK_OT_USHORT`、`SK_OT_SHORT`、`SK_OT_ULONG` 等基础类型
- `src/sfnt/SkPanose.h` - PANOSE 分类结构
- `src/sfnt/SkIBMFamilyClass.h` - IBM 字体族分类

## 设计模式与设计决策

1. **二进制布局映射**：使用 `#pragma pack(push, 1)` 确保与字体文件布局一一对应
2. **双重访问模式**：每个位域字段都提供 `Field`（结构化位域）和 `Raw`（掩码常量）两种访问方式
3. **大端序常量**：所有枚举值和掩码常量预先转换为大端序，避免运行时转换
4. **编译期大小校验**：`static_assert(sizeof(SkOTTableOS2_V2) == 96)` 确保结构体大小正确
5. **版本继承**：版本 2 包含版本 0 和版本 1 的所有字段

## 性能考量

1. **零拷贝访问**：结构体可直接映射到字体文件内存，无需解析
2. **编译期字节序转换**：所有常量在编译时完成字节序转换
3. **位域操作**：使用位运算进行标志检测，无分支开销

### 版本演进对比

| 特性 | VA (68B) | V0 (78B) | V1 (86B) | V2 (96B) |
|------|---------|---------|---------|---------|
| 排版度量 | 无 | 有 | 有 | 有 |
| 代码页范围 | 无 | 无 | 有 | 有 |
| xHeight/CapHeight | 无 | 无 | 无 | 有 |
| Unicode 范围 | 原始 | 结构化 | 结构化 | 结构化 |
| 权重值范围 | 1-9 | 100-900 | 100-900 | 100-900 |

### 位域访问示例

```cpp
// 通过 Field 访问
if (os2.fsSelection.field.Bold) { ... }
if (os2.fsType.field.NoSubsetting) { ... }

// 通过 Raw 掩码访问
if (os2.fsSelection.raw.value & SkOTTableOS2_V2::Selection::Raw::BoldMask) { ... }
if (os2.ulUnicodeRange.raw.value[0] & SkOTTableOS2_V2::UnicodeRange::Raw::l0::CJKUnifiedIdeographsMask) { ... }
```

### PANOSE 分类

`panose` 字段是一个 10 字节的分类系统，描述字体的视觉特征：

| 字节 | 说明 |
|------|------|
| 0 | 字体族类型（拉丁文字、拉丁手写体等） |
| 1 | 衬线样式 |
| 2 | 权重 |
| 3 | 比例 |
| 4 | 对比度 |
| 5 | 笔画变化 |
| 6 | 手臂样式 |
| 7 | 字母形式 |
| 8 | 中线位置 |
| 9 | x 高度 |

### IBM 字体族分类

`sFamilyClass` 是一个 2 字节字段，使用 IBM 字体族分类系统：
- 高字节：类别（如 1=Old Style Serifs, 2=Transitional Serifs 等）
- 低字节：子类别

### 供应商 ID

`achVendID[4]` 是四字节的字体供应商标识，例如：
- `'GOOG'` - Google
- `'ADBE'` - Adobe
- `'MSFT'` - Microsoft
- `'APPL'` - Apple

## 相关文件

- `src/sfnt/SkOTTable_OS_2.h` - OS/2 表版本选择器
- `src/sfnt/SkOTTable_OS_2_VA.h` - 原始 Apple TT 版本
- `src/sfnt/SkOTTable_OS_2_V4.h` - 版本 4
- `src/sfnt/SkOTTableTypes.h` - OT 基础类型
- `src/sfnt/SkPanose.h` - PANOSE 分类
- `src/sfnt/SkIBMFamilyClass.h` - IBM 字体族分类
