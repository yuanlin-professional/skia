# SkOTTable_OS_2_VA - OpenType OS/2 表版本 A（Apple 原始 TT）

> 源文件:
> - `src/sfnt/SkOTTable_OS_2_VA.h`

## 概述

`SkOTTable_OS_2_VA.h` 定义了 OS/2 表的 Apple 原始 TrueType 版本（Version A）的数据结构。这是 OS/2 表最早的版本，仅包含基本的字体度量信息，不包含排版度量、代码页范围或 Unicode 范围的详细定义。

版本 A 与版本 0 共享相同的版本号 0，两者只能通过表的实际大小来区分（版本 A 为 68 字节，版本 0 为更大的尺寸）。

## 架构位置

```
src/sfnt/
  SkOTTable_OS_2.h       // OS/2 表版本选择器（通过大小区分 VA 和 V0）
  SkOTTable_OS_2_VA.h     // 版本 A - Apple 原始 TT（本文件）
  SkOTTable_OS_2_V0.h     // 版本 0
  SkOTTable_OS_2_V1.h     // 版本 1
  SkOTTable_OS_2_V2.h     // 版本 2
  ...
```

## 主要类与结构体

### `SkOTTableOS2_VA`

原始 Apple TrueType OS/2 表结构体（68 字节），使用 1 字节对齐打包。

```cpp
static const SK_OT_USHORT VERSION = SkTEndian_SwapBE16(0);
```

### 权重类 (`WeightClass`)

与 V2 不同，使用 1-9 的值（而非 100-900）：

| 枚举值 | 数值 | 说明 |
|--------|------|------|
| `UltraLight` | 1 | 超细 |
| `ExtraLight` | 2 | 特细 |
| `Light` | 3 | 细 |
| `SemiLight` | 4 | 半细 |
| `Medium` | 5 | 中等 |
| `SemiBold` | 6 | 半粗 |
| `Bold` | 7 | 粗 |
| `ExtraBold` | 8 | 特粗 |
| `UltraBold` | 9 | 超粗 |

注意：名称也不同（如 `UltraLight` 而非 `Thin`，`SemiLight` 而非 `Normal`）。

### 宽度类 (`WidthClass`)

与 V2 相同，从 `UltraCondensed(1)` 到 `UltraExpanded(9)`。

### 嵌入类型 (`fsType`)

比 V2 简化，仅包含：
- `Restricted`（位 1）
- `PreviewPrint`（位 2）
- `Editable`（位 3）

无 `NoSubsetting` 和 `Bitmap` 标志。

### 字符范围

```cpp
SK_OT_ULONG ulCharRange[4];
```

使用原始 4 ULONG 数组，无结构化的 Unicode 范围定义（与 V2 的 `UnicodeRange` 不同）。

### 字体选择标志 (`fsSelection`)

比 V2 少一个 `Regular` 标志：

| 标志 | 说明 |
|------|------|
| `Italic` | 斜体 |
| `Underscore` | 下划线 |
| `Negative` | 反色 |
| `Outlined` | 轮廓 |
| `Strikeout` | 删除线 |
| `Bold` | 粗体 |

### 不包含的字段

与 V2 相比，VA 版本不包含：
- `sTypoAscender` / `sTypoDescender` / `sTypoLineGap` - 排版度量
- `usWinAscent` / `usWinDescent` - Windows 度量
- `ulCodePageRange` - 代码页范围
- `sxHeight` / `sCapHeight` - x 高度和大写高度

## 公共 API 函数

该头文件仅定义数据结构，不包含函数。结构体字段通过直接内存映射访问。

## 内部实现细节

### 共享字段（从下标偏移到选择标志）

| 字段 | 类型 | 说明 |
|------|------|------|
| `xAvgCharWidth` | SK_OT_SHORT | 平均字符宽度 |
| `usWeightClass` | WeightClass | 权重类 |
| `usWidthClass` | WidthClass | 宽度类 |
| `fsType` | Type union | 嵌入许可 |
| `ySubscriptXSize/YSize/XOffset/YOffset` | SK_OT_SHORT | 下标参数 |
| `ySuperscriptXSize/YSize/XOffset/YOffset` | SK_OT_SHORT | 上标参数 |
| `yStrikeoutSize` / `yStrikeoutPosition` | SK_OT_SHORT | 删除线参数 |
| `sFamilyClass` | SkIBMFamilyClass | IBM 字体族分类 |
| `panose` | SkPanose | PANOSE 分类 |
| `ulCharRange[4]` | SK_OT_ULONG | 字符范围 |
| `achVendID[4]` | SK_OT_CHAR | 供应商 ID |
| `fsSelection` | Selection union | 选择标志 |
| `usFirstCharIndex` / `usLastCharIndex` | SK_OT_USHORT | 首/末字符索引 |

### 大小校验

```cpp
static_assert(sizeof(SkOTTableOS2_VA) == 68, "sizeof_SkOTTableOS2_VA_not_68");
```

## 依赖关系

- `src/base/SkEndian.h` - 字节序转换
- `src/sfnt/SkOTTableTypes.h` - OT 基础类型
- `src/sfnt/SkPanose.h` - PANOSE 分类
- `src/sfnt/SkIBMFamilyClass.h` - IBM 字体族分类

## 设计模式与设计决策

1. **版本区分**：VA 和 V0 共享版本号 0，必须通过表大小区分（68 vs 更大）
2. **Apple 权重值**：使用 1-9 而非 100-900，需要在读取时乘以 100 进行转换
3. **最小化字段**：仅包含 Apple 原始 TrueType 规范定义的字段
4. **`SK_SEQ_END` 标记**：权重和宽度枚举包含 `SK_SEQ_END` 序列结束标记

## 性能考量

1. **最小表大小**：68 字节，是所有 OS/2 版本中最小的
2. **零拷贝映射**：直接映射到字体文件内存
3. **编译期字节序**：所有常量预先转换

### VA 与 V0 的区分方法

由于 VA 和 V0 共享版本号 0，Skia 中通过表大小进行区分：

```cpp
// 在 SkOTTable_OS_2.h 中的逻辑：
if (tableSize == sizeof(SkOTTableOS2_VA)) {
    // 版本 A (68 字节)
} else if (version == 0) {
    // 版本 0 (更大)
}
```

### 权重值转换

VA 版本的权重值为 1-9，而现代 Skia `SkFontStyle` 使用 100-900。转换时需要乘以 100：

```
VA Weight  Modern Weight  说明
1          100            UltraLight / Thin
2          200            ExtraLight
3          300            Light
4          400            SemiLight / Normal
5          500            Medium
6          600            SemiBold
7          700            Bold
8          800            ExtraBold
9          900            UltraBold / Black
```

注意 VA 版本中 "SemiLight"(4) 对应现代的 "Normal"(400)，而不是 350。

### SK_SEQ_END 标记

`WeightClass` 和 `WidthClass` 枚举包含 `SK_SEQ_END` 标记，用于序列化/枚举范围检测。

## 相关文件

- `src/sfnt/SkOTTable_OS_2.h` - OS/2 表版本选择器
- `src/sfnt/SkOTTable_OS_2_V0.h` - 版本 0（与 VA 共享版本号）
- `src/sfnt/SkOTTable_OS_2_V2.h` - 版本 2（完整版本，含 Unicode/CodePage 范围）
- `src/sfnt/SkOTTableTypes.h` - OT 基础类型定义
- `src/sfnt/SkPanose.h` - PANOSE 分类
- `src/sfnt/SkIBMFamilyClass.h` - IBM 字体族分类
