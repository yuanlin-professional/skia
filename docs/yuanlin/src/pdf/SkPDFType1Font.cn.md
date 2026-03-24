# SkPDFType1Font (PDF Type1 字体)

> 源文件:
> - `src/pdf/SkPDFType1Font.h`
> - `src/pdf/SkPDFType1Font.cpp`

## 概述

`SkPDFType1Font` 模块实现了 PDF 中 Type1 字体的嵌入和输出逻辑。Type1 是 Adobe 定义的经典 PostScript 字体格式，包含三个部分：明文头部（PostScript 语法）、加密字形数据、以及固定的尾部标记。该模块处理 PFB（二进制 PostScript 字体）和 PFA（ASCII PostScript 字体）两种格式的解析和转换，生成符合 PDF 规范的 Type1 字体对象。源文件约 370 行。

## 架构位置

```
SkPDFFont::emitSubset()
  |
  |-- [Type1 字体] -> SkPDFEmitType1Font()
  |                      |-- 创建字体描述符
  |                      |-- 解析和嵌入字体数据（PFB/PFA）
  |                      |-- 生成字形宽度数组
  |                      |-- 生成编码差异表
  |
  |-- [TrueType] -> 其他处理路径
  |-- [CFF] -> 其他处理路径
```

## 主要类与结构体

本模块不定义类，提供一个核心函数。

## 公共 API 函数

### 核心函数

```cpp
void SkPDFEmitType1Font(const SkPDFFont& pdfFont, SkPDFDocument* doc);
```

将 Type1 字体作为 PDF Font 对象输出到文档。

**处理流程：**
1. 获取字形名称列表
2. 创建字体描述符（FontDescriptor），包含字体元数据和嵌入的字体文件
3. 构建 Font 字典，包含：
   - `/Subtype /Type1`
   - `/BaseFont` -- PostScript 字体名称
   - `/FirstChar` / `/LastChar` -- 编码范围
   - `/Widths` -- 字形宽度数组
   - `/Encoding` -- 编码差异表
   - `/FontDescriptor` -- 字体描述符引用

## 内部实现细节

### PFB 格式解析

`parsePFB()` 解析 PFB（Printer Font Binary）文件的三段结构：
- **段 1**（类型 1）：ASCII 明文头部，包含 PostScript 字典
- **段 2**（类型 2）：二进制加密的字形程序
- **段 3**（类型 1）：尾部（512 个零 + cleartomark）
- **段 4**（类型 3）：EOF 标记

每段有 6 字节的头部：`0x80` + 段类型（1 字节）+ 段长度（4 字节小端）。

### PFA 格式解析

`parsePFA()` 解析 PFA（Printer Font ASCII）文件：
- 头部以 `eexec` 结束
- 数据段为十六进制编码的加密字形数据
- 尾部以 512 个 ASCII 零 + `cleartomark` 标识

PFA 解析后需要将十六进制数据转换为二进制，因为 PDF 只支持二进制格式的 Type1 字体。

### 字体流转换

`convert_type1_font_stream()` 统一处理 PFB 和 PFA 格式：
1. 读取完整字体数据并 NUL 终止
2. 尝试按 PFB 格式解析
3. PFB 解析成功则去除段头部，拼接三段数据
4. 失败则尝试 PFA 格式解析
5. PFA 需要将十六进制数据转换为二进制

### 字体描述符

`make_type1_font_descriptor()` 创建 PDF FontDescriptor：
- 填充通用字体元数据（名称、标志、包围框等）
- 如果字体允许嵌入，解析字体数据并创建 FontFile 流
- FontFile 流包含 `/Length1`（头部）、`/Length2`（数据）、`/Length3`（尾部）

### 编码差异表

为 Type1 字体生成 `/Encoding` 字典，包含 `/Differences` 数组。该数组将 PDF 字符代码映射到 PostScript 字形名称。未知字形使用 `"UNKNOWN"` 作为名称。

### 字形宽度

通过 `SkBulkGlyphMetrics` 批量获取字形的水平推进宽度（advanceX），并从字体单位转换为基于 1000 的标准单位。

### 字体描述符缓存

`type1_font_descriptor()` 按 typeface ID 缓存字体描述符，确保同一字体的多个 SkPDFFont 实例共享描述符。

### 字形名称缓存

`type_1_glyphnames()` 按 typeface ID 缓存字形名称列表，通过 `SkTypeface::getPostScriptGlyphNames` 获取。

## 依赖关系

**内部依赖：**
- `SkPDFFont` -- 字体基础类
- `SkPDFTypes` -- PDF 对象类型（Dict, Array, Stream）
- `SkPDFDocumentPriv` -- 文档内部接口
- `SkAdvancedTypefaceMetrics` -- 字体元数据
- `SkStrikeSpec` / `SkGlyph` -- 字形查找

**外部依赖：**
- `SkTypeface`, `SkData`, `SkStream` -- Skia 基础类型
- `SkTHash` -- 哈希容器（缓存）
- `<ctype.h>`, `<cstring>` -- C 标准库

## 设计模式与设计决策

1. **双格式支持**：同时支持 PFB（二进制）和 PFA（ASCII）两种 Type1 字体格式，确保兼容性。

2. **统一转换**：无论输入格式如何，都转换为 PDF 要求的二进制格式，简化后续处理。

3. **嵌入检查**：在嵌入字体前检查 `NotEmbeddable` 标志，尊重字体许可证限制。

4. **描述符共享**：同一 typeface 的不同字体资源（覆盖不同字形范围）共享字体描述符，减少重复。

5. **不确定字形名称回退**：对于空的字形名称使用 `"UNKNOWN"` 作为占位符，确保编码差异表的完整性。

## 性能考量

- **字体数据单次解析**：字体数据只在嵌入时解析一次，解析结果直接用于 PDF 流。
- **批量字形度量**：使用 `SkBulkGlyphMetrics` 批量获取字形宽度，减少单次查询开销。
- **缓存复用**：字体描述符和字形名称按 typeface ID 缓存，避免重复计算。
- **内存映射**：使用 `AutoTMalloc` 一次性分配解析缓冲区，避免多次分配。

## 相关文件

- `src/pdf/SkPDFFont.h` -- 字体基础类
- `src/pdf/SkPDFTypes.h` -- PDF 对象类型
- `src/pdf/SkPDFDocumentPriv.h` -- 文档内部接口
- `src/core/SkAdvancedTypefaceMetrics.h` -- 字体元数据
