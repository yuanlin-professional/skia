# SkShaper_primitive - 基础文本塑形器实现

> 源文件: `modules/skshaper/src/SkShaper_primitive.cpp`

## 概述

SkShaper_primitive.cpp 实现了最基础的文本塑形器 SkShaperPrimitive。它不依赖任何外部排版库（如 HarfBuzz），仅使用 Skia 的 SkFont API 进行简单的字符到字形映射和宽度测量。该实现不支持复杂文字处理（连字、字形替换、标记定位），也不处理 BiDi 重排和脚本检测，但提供了基本的按宽度换行能力。

## 架构位置

SkShaperPrimitive 是 skshaper 模块的最低层后端，作为没有 HarfBuzz 或 CoreText 时的兜底实现。它可以在任何 Skia 构建中使用，无需额外依赖。

**选择优先级**: HarfBuzz > CoreText > **Primitive**

## 主要类与结构体

### `SkShaperPrimitive`
继承自 SkShaper，实现所有 `shape()` 方法。是唯一无外部依赖的塑形器实现。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkShapers::Primitive::PrimitiveText()` | 创建原始塑形器实例 |
| `SkShaper::MakePrimitive()` | 旧版创建接口 |

## 内部实现细节

### 换行实现（`linebreak` 函数）
简单的按宽度换行算法：
1. 逐字符扫描文本，累加字形前进量
2. 跟踪单词边界（空白字符到非空白字符的转换）
3. 当累加宽度超过限制时：
   - 如果当前在空白字符处：在前一个位置断行，后续空白归入尾部
   - 如果有之前的单词边界：回退到该边界
   - 如果该单词是行首唯一单词：回退到上一个字形
   - 否则（首字符即溢出）：允许溢出，后续空白归入尾部

### 空白字符判断（`is_breaking_whitespace`）
识别约 16 种 Unicode 可断行空白字符，包括：
- 普通空格 (U+0020)
- 各种排版空格（EN QUAD、EM SPACE、THIN SPACE 等）
- 零宽空格 (U+200B)
- 表意空格 (U+3000)

注意：NO-BREAK SPACE (U+00A0) 和 ZERO WIDTH NO-BREAK SPACE (U+FEFF) 被显式排除。

### 塑形流程
1. 从 FontRunIterator 获取字体（仅使用第一个运行的字体）
2. 使用 `font.countText()` 计算字形数量
3. 使用 `font.textToGlyphs()` 进行批量字符到字形映射
4. 使用 `font.getWidths()` 获取所有字形宽度
5. 按行循环：
   - 调用 `linebreak()` 确定每行的文本范围
   - 通过 RunHandler 回调输出每行数据
   - 每个字符假定映射到恰好一个字形

### 簇（cluster）映射
使用简单的 1:1 映射：每个 UTF-8 字符映射到一个字形，cluster 值为该字符在文本中的字节偏移。

## 依赖关系

- **SkFont**: 字形映射和宽度查询
- **SkUTF**: UTF-8 编码处理（NextUTF8、CountUTF8）
- **SkShaper**: 基类和 RunHandler 接口
- 无外部库依赖（不需要 HarfBuzz、ICU 或 CoreText）

## 设计模式与设计决策

1. **最小依赖原则**: 仅依赖 Skia 核心 API，确保在任何构建配置下可用。
2. **简化假设**: 假设每个 Unicode 字符映射到一个字形，不处理连字等复杂映射。
3. **忽略 BiDi/Script/Language**: shape 方法接收这些迭代器但不使用，所有文本按 LTR 处理。
4. **贪心换行**: linebreak 使用简单的贪心算法，非最优但足够实用。

## 性能考量

- **批量 API**: 使用 `textToGlyphs` 和 `getWidths` 批量处理，避免逐字形调用
- **无复杂排版开销**: 不执行 GSUB/GPOS 表查找、连字处理或标记定位
- **内存**: 分配 glyphs 和 advances 数组，大小与字形数量成正比
- **局限性**: 对于阿拉伯语、印地语等复杂文字，输出结果可能不正确

### 换行算法详解

`linebreak` 函数的贪心换行逻辑：

```
初始化: accumulatedWidth = 0, wordStart = text, prevWS = true, trailing = 0

对每个字符 c:
  accumulatedWidth += advance[glyphIndex++]

  如果 c 是非空白且前一个是空白:
    wordStart = prevText  // 记录新单词起始

  如果 accumulatedWidth > width:
    情况1: c 是空白
      -> 在前一个位置断行，消费后续空白作为尾部
    情况2: wordStart != start (之前有单词边界)
      -> 回退到 wordStart
    情况3: prevText > start (不是第一个字符)
      -> 回退到上一个字符
    情况4: 第一个字符就溢出
      -> 允许溢出，消费后续空白作为尾部
```

### is_breaking_whitespace 支持的字符
完整的可断行空白字符列表：
- U+0020 SPACE
- U+1680 OGHAM SPACE MARK
- U+180E MONGOLIAN VOWEL SEPARATOR
- U+2000-U+200A 各种排版空格（EN QUAD 到 HAIR SPACE）
- U+200B ZERO WIDTH SPACE
- U+202F NARROW NO-BREAK SPACE
- U+205F MEDIUM MATHEMATICAL SPACE
- U+3000 IDEOGRAPHIC SPACE

注意不包括 U+00A0 (NO-BREAK SPACE) 和 U+FEFF (ZERO WIDTH NO-BREAK SPACE)。

### 与 HarfBuzz 后端的对比
| 特性 | Primitive | HarfBuzz |
|------|-----------|----------|
| 字形映射 | 1:1（字符到字形） | 多:多（连字、分解） |
| 字距调整 | 无 | OpenType kern/GPOS |
| 复杂文字 | 不支持 | 完整支持 |
| BiDi | 不处理 | 完整支持 |
| 换行 | 简单贪心 | Unicode 行断行 |
| 外部依赖 | 无 | HarfBuzz + SkUnicode |

### 字体运行处理
Primitive 塑形器仅使用第一个字体运行的字体：
```cpp
if (!fontRuns.atEnd()) {
    fontRuns.consume();
    font = fontRuns.currentFont();
}
```
这意味着如果文本跨越多个字体运行，只会使用第一个字体。对于需要字体回退的多语言文本，Primitive 塑形器无法正确处理。

## 相关文件

- `modules/skshaper/include/SkShaper.h` - SkShaper 基类和 Primitive 命名空间声明
- `modules/skshaper/include/SkShaper_factory.h` - Factory 接口
- `src/base/SkUTF.h` - UTF-8 编码工具

## 使用注意事项

1. Primitive 塑形器不支持复杂文字（阿拉伯语、天城体等），这些文字需要 HarfBuzz
2. 仅使用第一个字体运行的字体，忽略后续字体运行
3. BiDi、脚本和语言迭代器参数被完全忽略
4. 换行算法为简单贪心，不考虑连字符断行
5. 每个 Unicode 字符假设映射到恰好一个字形
6. 适合测试、原型设计或仅处理简单拉丁文本的场景
