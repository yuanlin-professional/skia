# SkPDFMakeToUnicodeCmap (PDF ToUnicode CMap 生成)

> 源文件:
> - `src/pdf/SkPDFMakeToUnicodeCmap.h`
> - `src/pdf/SkPDFMakeToUnicodeCmap.cpp`

## 概述

`SkPDFMakeToUnicodeCmap` 模块负责生成 PDF 字体的 ToUnicode CMap（字符映射表）。ToUnicode CMap 定义了字形 ID 到 Unicode 码点的反向映射，使 PDF 阅读器能够从 PDF 中提取和搜索文本内容。该模块按照 PDF 规范 1.4 和 Adobe 技术说明 5014 的要求，生成 `bfchar`（单字符映射）和 `bfrange`（字符范围映射）表，并支持单字节和多字节字形编码。源文件约 316 行。

## 架构位置

```
SkPDFFont::emitSubset()
  |
  |-- SkPDFMakeToUnicodeCmap()
  |     |-- append_tounicode_header() (CMap 头部)
  |     |-- SkPDFAppendCmapSections() (bfchar + bfrange 表)
  |     |-- append_cmap_footer() (CMap 尾部)
  |     |
  |     v
  |   CMap 流 -> PDF ToUnicode 流对象
```

## 主要类与结构体

### `BFChar`（内部结构体）

单个字形到 Unicode 的映射：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fGlyphId` | `SkGlyphID` | 字形 ID |
| `fUnicode` | `SkUnichar` | Unicode 码点 |

### `BFRange`（内部结构体）

连续字形范围到 Unicode 的映射：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fStart` | `SkGlyphID` | 范围起始字形 ID |
| `fEnd` | `SkGlyphID` | 范围结束字形 ID |
| `fUnicode` | `SkUnichar` | 起始 Unicode 码点 |

## 公共 API 函数

### 核心函数

```cpp
std::unique_ptr<SkStreamAsset> SkPDFMakeToUnicodeCmap(
    const SkUnichar* glyphToUnicode,
    const THashMap<SkGlyphID, SkString>& glyphToUnicodeEx,
    const SkPDFGlyphUse* subset,
    bool multiByteGlyphs,
    SkGlyphID firstGlyphID,
    SkGlyphID lastGlyphID);
```

生成完整的 ToUnicode CMap 流。

**参数：**
- `glyphToUnicode` -- 字形 ID 到 Unicode 的基本映射数组
- `glyphToUnicodeEx` -- 扩展映射（多码点字形，如连字）
- `subset` -- 字形子集过滤器（仅输出使用过的字形），可为 nullptr
- `multiByteGlyphs` -- 是否使用双字节字形编码（CID 字体为 true）
- `firstGlyphID` / `lastGlyphID` -- 字形 ID 范围

### 测试辅助函数

```cpp
void SkPDFAppendCmapSections(
    const SkUnichar* glyphToUnicode,
    const THashMap<SkGlyphID, SkString>& glyphToUnicodeEx,
    const SkPDFGlyphUse* subset,
    SkDynamicMemoryWStream* cmap,
    bool multiByteGlyphs,
    SkGlyphID firstGlyphID,
    SkGlyphID lastGlyphID);
```

生成 CMap 的 bfchar 和 bfrange 部分（不含头尾）。暴露出来用于单元测试。

## 内部实现细节

### CMap 结构

生成的 CMap 包含以下标准部分：

1. **头部**（`append_tounicode_header`）：
   - `/CIDInit /ProcSet findresource begin`
   - CIDSystemInfo（Adobe-UCS-0）
   - CMapName 和 CMapType
   - Codespace range（单字节 `<00><FF>` 或双字节 `<0000><FFFF>`）

2. **映射表**（`SkPDFAppendCmapSections`）：
   - `beginbfchar` / `endbfchar` 节（单字符映射）
   - 扩展 bfchar 节（多码点字形映射）
   - `beginbfrange` / `endbfrange` 节（范围映射）

3. **尾部**（`append_cmap_footer`）：
   - `endcmap` 和资源定义

### 范围合并算法

`SkPDFAppendCmapSections` 使用单遍扫描算法将连续的字形-Unicode 映射合并为范围：

1. 从 `firstGlyphID` 到 `lastGlyphID` 遍历
2. 对每个字形检查是否在子集中且不在扩展映射中
3. 如果当前字形可以扩展现有范围（连续 ID、相同高字节、连续 Unicode），则扩展
4. 否则将当前范围输出为 bfrange（多字形）或 bfchar（单字形）
5. 开始新范围

**PDF 规范约束：**
- bfrange 不允许跨越高字节边界（如 `<1035><10FF>` 可以，`<1035><1100>` 不行）
- 每个 bf* 列表最多 100 个条目

### 扩展映射处理

`append_bfchar_section_ex()` 单独处理多码点字形映射（如连字 "fi"）。这些字形在 `glyphToUnicodeEx` 哈希表中存储为 UTF-8 字符串，输出时转换为 UTF-16BE 十六进制。

### 字形 ID 偏移

对于非多字节字体（Type1），字形 ID 需要偏移 `firstGlyphID - 1`，因为 Type1 字体的编码空间从 0 开始但字形 ID 可能从较大值开始。

### Unicode 输出格式

所有 Unicode 值以 UTF-16BE 十六进制格式输出。对于 BMP 外的码点，`SkUTF::ToUTF16` 自动生成代理对。

## 依赖关系

**内部依赖：**
- `SkPDFGlyphUse` -- 字形使用记录（子集过滤）
- `SkPDFUtils` -- WriteUInt16BE, WriteUInt8, WriteUTF16beHex

**外部依赖：**
- `SkStream` / `SkDynamicMemoryWStream` -- 输出流
- `SkString` -- 字符串（扩展映射值）
- `SkUTF` -- UTF-8/UTF-16 转换
- `SkTHash` -- 哈希映射（扩展映射）

## 设计模式与设计决策

1. **范围合并优化**：将连续的单字符映射合并为范围映射，减小 CMap 大小。

2. **bfchar 优先于 bfrange**：当范围只有一个字形时使用 bfchar，避免冗余的范围语法。

3. **扩展映射分离**：多码点字形映射（连字等）单独处理，因为它们不适合范围合并。

4. **100 条目分页**：遵循 PDF 规范要求，每个 bfchar/bfrange 列表最多 100 条目。

5. **不执行激进优化**：Adobe 技术说明提到映射可以重叠，但实现选择保证不重叠，牺牲了极端情况下的压缩率但换取了简单性和确定性。

## 性能考量

- **单遍扫描**：范围合并使用 O(n) 的单遍扫描算法，n 为字形范围大小。
- **子集过滤**：通过 `SkPDFGlyphUse` 跳过未使用的字形，减少输出大小。
- **范围合并**：将连续映射合并为范围可以将 CMap 大小减少到 1/3 或更少。
- **流式输出**：直接写入 `SkDynamicMemoryWStream`，最终通过 `detachAsStream` 零拷贝获取结果。

## 相关文件

- `src/pdf/SkPDFFont.h` -- 字体管理（调用者）
- `src/pdf/SkPDFGlyphUse.h` -- 字形使用记录
- `src/pdf/SkPDFUtils.h` -- 十六进制写入工具
- `src/base/SkUTF.h` -- Unicode 工具
