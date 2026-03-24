# SkAdvancedTypefaceMetrics

> 源文件
> - src/core/SkAdvancedTypefaceMetrics.h

## 概述

`SkAdvancedTypefaceMetrics` 是 Skia 图形库中用于描述字体高级度量信息的结构体。它主要被 PDF 后端使用，用于正确地嵌入字体并生成符合 PDF 标准的字体描述符，确保文档能够准确渲染和跨平台显示文本。

## 架构位置

`SkAdvancedTypefaceMetrics` 位于 Skia 的字体系统和文档输出层之间，作为字体元数据的标准化接口。它将字体文件的内部信息转换为 PDF 等格式所需的元数据。

```
Skia Core
  └── Font System
      ├── SkTypeface (字体抽象)
      │   └── getAdvancedMetrics() (生成元数据)
      ├── SkAdvancedTypefaceMetrics (元数据结构)
      └── PDF Backend
          └── SkPDFFont (使用元数据嵌入字体)
```

## 主要类与结构体

### SkAdvancedTypefaceMetrics

**继承关系**
- 独立结构体（无继承）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPostScriptName` | `SkString` | PostScript 字体名称，用于 PDF 的 `FontName` 和 `BaseFont` |
| `fStyle` | `StyleFlags` | 字体样式特征标志 |
| `fType` | `FontType` | 底层字体程序类型（Type1/CFF/TrueType 等） |
| `fFlags` | `FontFlags` | 全局字体标志（变体/不可嵌入/不可子集等） |
| `fItalicAngle` | `int16_t` | 斜体角度（逆时针，度数，相对垂直线） |
| `fAscent` | `int16_t` | 最大上升高度（字体单位，不含变音符） |
| `fDescent` | `int16_t` | 最大下降深度（字体单位，负值） |
| `fStemV` | `int16_t` | 主垂直笔画粗细（字体单位） |
| `fCapHeight` | `int16_t` | 大写字母高度（从基线到平顶，字体单位） |
| `fBBox` | `SkIRect` | 所有字形的包围盒（字体单位） |

### StyleFlags 枚举

**定义**
```cpp
enum StyleFlags : uint32_t {
    kFixedPitch_Style  = 0x00000001,  // 等宽字体
    kSerif_Style       = 0x00000002,  // 衬线字体
    kScript_Style      = 0x00000008,  // 手写/草书体
    kItalic_Style      = 0x00000040,  // 斜体
    kAllCaps_Style     = 0x00010000,  // 全大写
    kSmallCaps_Style   = 0x00020000,  // 小型大写
    kForceBold_Style   = 0x00040000   // 强制粗体
};
```

**特点**
- 位掩码标志，可组合使用
- 值匹配 PDF 文件格式规范
- 支持 `is_bitmask_enum` 特化（位运算安全）

### FontType 枚举

**定义**
```cpp
enum FontType : uint8_t {
    kType1_Font,      // Type 1 PostScript 字体
    kType1CID_Font,   // Type 1 CID 字体（多字节）
    kCFF_Font,        // Compact Font Format
    kTrueType_Font,   // TrueType 字体
    kOther_Font,      // 其他/未知类型
};
```

**说明**
- 决定字体在 PDF 中的嵌入方式
- `kOther_Font` 时不填充逐字形信息

### FontFlags 枚举

**定义**
```cpp
enum FontFlags : uint8_t {
    kVariable_FontFlag       = 1 << 0,  // 可变字体
    kNotEmbeddable_FontFlag  = 1 << 1,  // 许可禁止嵌入
    kNotSubsettable_FontFlag = 1 << 2,  // 许可禁止子集化
    kAltDataFormat_FontFlag  = 1 << 3,  // 数据已压缩
};
```

**说明**
- 控制字体的使用和嵌入行为
- PDF 生成器必须遵守嵌入限制
- 子集化可减小文件大小

## 公共 API 函数

### 默认初始化

所有成员都有默认值：
- 字符串：空字符串
- 标志：0（无标志）
- 数值：0
- 包围盒：`{0, 0, 0, 0}`

### 访问方式

作为 POD 结构体，所有成员都是公开的，直接访问：
```cpp
SkAdvancedTypefaceMetrics metrics;
metrics.fPostScriptName = "Helvetica";
metrics.fStyle = kFixedPitch_Style | kSerif_Style;
metrics.fType = kTrueType_Font;
```

### 生成方式

通常由 `SkTypeface::getAdvancedMetrics()` 填充：
```cpp
std::unique_ptr<SkAdvancedTypefaceMetrics> metrics =
    typeface->getAdvancedMetrics();
```

## 内部实现细节

### 字体单位（Font Units）

大多数度量值使用"字体单位"（em-square 的分数）：
- **TrueType**: 通常 2048 单位/em
- **Type 1/CFF**: 通常 1000 单位/em
- **转换**: 实际像素 = (字体单位 × 字体大小) / unitsPerEm

示例：
```
fAscent = 1800 (字体单位)
unitsPerEm = 2048
字体大小 = 12pt
实际上升 = (1800 × 12) / 2048 ≈ 10.5pt
```

### PostScript 名称规范

`fPostScriptName` 的要求：
- 只包含 ASCII 字符
- 无空格（用连字符替代）
- 最大长度：63 字符（PDF 限制）
- 示例：`"Helvetica-Bold"`, `"TimesNewRoman-Italic"`

### StyleFlags 位运算

使用 `sknonstd::is_bitmask_enum` 特化支持：
```cpp
StyleFlags combined = kSerif_Style | kItalic_Style;
if (combined & kSerif_Style) { /* ... */ }
```

### 度量值语义

| 度量值 | 正值方向 | 说明 |
|-------|---------|------|
| `fAscent` | 向上 | 基线以上的最大高度 |
| `fDescent` | 向下（负值） | 基线以下的最大深度 |
| `fCapHeight` | 向上 | 大写字母顶部高度 |
| `fStemV` | 无方向 | 垂直笔画粗细 |
| `fItalicAngle` | 逆时针 | 0° = 垂直，正值向左倾斜 |

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkRect.h` | `SkIRect` 包围盒类型 |
| `include/core/SkString.h` | `SkString` 字符串类型 |
| `src/base/SkBitmaskEnum.h` | 位掩码枚举特化 |
| `<type_traits>` | `std::true_type` 元编程 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkTypeface` 派生类 | 实现 `getAdvancedMetrics()` |
| `SkPDFFont` | 生成 PDF 字体描述符 |
| `SkPDFDocument` | 字体嵌入和子集化 |
| 字体工具 | 字体信息提取和分析 |

## 设计模式与设计决策

### POD 结构体设计
- **选择**: 纯数据结构（无方法）
- **优势**:
  - 简单直接，易于理解
  - 零开销抽象
  - 易于序列化和传递

### 枚举值匹配 PDF 标准
- **动机**: 直接对应 PDF 规范的 `Flags` 字段
- **实现**: `StyleFlags` 的值与 PDF 标准一致
- **优势**: 无需转换映射表

### 位掩码枚举支持
- **机制**: `is_bitmask_enum` 特化
- **效果**: 支持类型安全的位运算
- **优势**: 防止错误的标志组合

### 可选信息设计
- **体现**: `fType == kOther_Font` 时跳过某些字段
- **灵活性**: 支持不完整的字体信息
- **健壮性**: 处理未知字体格式

## 性能考量

### 内存占用

```cpp
sizeof(SkAdvancedTypefaceMetrics) ≈ 64-80 字节
  - SkString fPostScriptName:  24 字节
  - StyleFlags fStyle:         4 字节
  - FontType fType:            1 字节
  - FontFlags fFlags:          1 字节
  - int16_t × 5:              10 字节
  - SkIRect fBBox:            16 字节
  - 对齐填充:                 ~8 字节
```

### 生成开销

`getAdvancedMetrics()` 的典型开销：
- **TrueType**: ~10-50µs（解析表头）
- **Type 1**: ~50-200µs（解析 AFM/PFB）
- **系统字体**: 可能涉及字体缓存查询

### 使用建议

| 场景 | 建议 | 原因 |
|------|------|------|
| PDF 生成 | 缓存结果 | 避免重复解析 |
| 字体切换 | 延迟获取 | 只在需要时获取 |
| 批量处理 | 并行获取 | I/O 密集操作 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkTypeface.h` | 使用者 | `getAdvancedMetrics()` 方法 |
| `src/pdf/SkPDFFont.h` | 主要使用者 | PDF 字体嵌入 |
| `src/pdf/SkPDFDocument.cpp` | 使用者 | 文档字体管理 |
| `src/ports/SkFontHost_*.cpp` | 实现者 | 平台特定的字体信息提取 |
| `src/sfnt/SkOTTable_*.h` | 协作 | TrueType/OpenType 表解析 |
