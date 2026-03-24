# SkPDFMakeCIDGlyphWidthsArray - CID 字形宽度数组生成

> 源文件：
> - `src/pdf/SkPDFMakeCIDGlyphWidthsArray.h`
> - `src/pdf/SkPDFMakeCIDGlyphWidthsArray.cpp`

## 概述

`SkPDFMakeCIDGlyphWidthsArray` 是 Skia PDF 后端中用于生成 CID 字体的字形宽度数组（/W 数组）的模块。根据 PDF 规范（PDF 32000-1:2008, 第 270 页），CID 字体的宽度数组支持可变格式，可以为连续的 CID 指定单独宽度，或为一个 CID 范围指定统一宽度。该模块实现了一种启发式压缩算法，在保持准确性的前提下尽量减少输出的 /W 数组大小。

## 架构位置

该模块位于 PDF 字体处理子系统中，被 `SkPDFFont` 在嵌入 CID 字体描述时调用。

```
SkPDFDocument
  └── SkPDFFont (字体子系统)
        └── SkPDFMakeCIDGlyphWidthsArray (宽度数组生成)
              ├── SkPDFStrikeSpec (字形度量获取)
              ├── SkPDFGlyphUse (字形子集信息)
              └── SkBulkGlyphMetricsAndPaths (批量字形路径获取)
```

## 主要类与结构体

该模块没有定义公共类，仅提供一个独立函数。内部使用了以下辅助函数：

### `from_font_units`（内部）

```cpp
SkScalar from_font_units(SkScalar scaled, uint16_t emSize);
```

将字体 em 单位的度量值转换为 PDF 标准的 1000 单位制。当 `emSize` 恰好为 1000 时直接返回原值以避免不必要的除法运算。

### `find_mode_or_0`（内部）

```cpp
SkScalar find_mode_or_0(SkSpan<const SkScalar> advances);
```

在已排序的 advance 数组中查找众数（出现频率最高的值）。如果数组为空则返回 0。该函数假设输入已排序，通过单次遍历完成众数查找。

## 公共 API 函数

### `SkPDFMakeCIDGlyphWidthsArray`

```cpp
std::unique_ptr<SkPDFArray> SkPDFMakeCIDGlyphWidthsArray(
    const SkPDFStrikeSpec& strikeSpec,
    const SkPDFGlyphUse& subset,
    int32_t* defaultAdvance);
```

**参数：**
- `strikeSpec`：字体规格信息，包含 `fUnitsPerEM`（em 单位大小）和 `fStrikeSpec`（用于获取字形度量）
- `subset`：字形子集，标识文档中实际使用的字形 ID 集合
- `defaultAdvance`：输出参数，返回最常见的宽度值（众数），将用作 PDF 的 /DW（默认宽度）

**返回值：** 包含 /W 数组内容的 `SkPDFArray` 对象

## 内部实现细节

### 宽度编码格式

PDF /W 数组支持两种编码格式：
- **范围（range）格式**：`gfid [adv1 adv2 ... advN]` — 从字形 ID 开始，数组中依次列出每个连续 CID 的宽度
- **运行（run）格式**：`gfid_start gfid_end advance` — 从起始到结束 CID 的所有字形共享同一宽度

### 启发式压缩规则

算法基于以下 ASCII 字符数估算来决定最优编码：
- 假设一个 advance 值加空格平均占 10 个字符
- 一个字形 ID 加空格平均占 4 个字符
- 范围中的未使用 GID 加空格占 2 个字符

具体规则：
1. **规则 a**：跳过与默认宽度相同的字形（无需编码）
2. **规则 b**：连续 2 个以上相同宽度时创建 run 格式
3. **规则 c**：范围中遇到默认宽度时结束范围
4. **规则 d**：范围中连续 4 个以上空缺时结束范围
5. **规则 e**：2 次以上重复且累计 4 个以上空缺时结束范围
6. **规则 f**：3 次以上连续重复时结束范围转为 run

### 默认宽度计算

算法首先筛选出所有整数宽度值（因为 poppler 等 PDF 阅读器要求 /DW 为整数），排序后通过 `find_mode_or_0` 找到众数作为默认宽度。等于默认宽度的字形将被跳过，从而减少输出大小。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | `SkPDFArray` 及其工厂函数 |
| `SkPDFFont.h` | `SkPDFStrikeSpec` 结构体 |
| `SkPDFGlyphUse.h` | 字形子集位图 |
| `SkGlyph.h` | `SkGlyph` 字形度量数据 |
| `SkStrikeSpec.h` | `SkBulkGlyphMetricsAndPaths` 批量度量获取 |
| `SkScalar.h` | 标量类型定义 |
| `SkSpan.h` | 范围视图 |

## 设计模式与设计决策

1. **启发式编码**：采用基于字符数估算的贪心算法，在编码紧凑性和实现复杂性之间取得平衡。代码中详细注释了每条规则的推导依据。

2. **整数默认宽度**：由于 poppler（一个广泛使用的 PDF 解析库）要求 /DW 为整数，算法仅从整数宽度中选取众数。这是一个兼容性妥协。

3. **单函数设计**：整个模块仅暴露一个公共函数，接口极简，符合单一职责原则。

4. **子集感知**：通过 `SkPDFGlyphUse` 仅处理文档实际使用的字形，避免为未使用字形生成不必要的宽度数据。

## 性能考量

- **排序开销**：`std::sort` 用于整数 advance 数组以支持众数查找，时间复杂度 O(n log n)。
- **单次遍历生成**：主循环对字形数组进行单次遍历（带少量前瞻），时间复杂度接近 O(n)。
- **批量字形度量获取**：使用 `SkBulkGlyphMetricsAndPaths` 一次性获取所有字形度量，避免逐个查询的开销。
- **预计算 advance 数组**：将 em 单位到 1000 单位的转换在主循环前一次性完成，避免重复计算。
- **em=1000 快速路径**：`from_font_units` 对 emSize=1000 的常见情况进行短路优化。

## 相关文件

- `src/pdf/SkPDFFont.h` / `src/pdf/SkPDFFont.cpp` — 调用方，CID 字体嵌入逻辑
- `src/pdf/SkPDFGlyphUse.h` — 字形子集位图定义
- `src/pdf/SkPDFTypes.h` — PDF 基本类型
- `src/core/SkGlyph.h` — 字形数据结构
- `src/core/SkStrikeSpec.h` — 字形度量规格
