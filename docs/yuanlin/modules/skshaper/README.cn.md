# skshaper - 文本整形引擎

## 概述

skshaper 是 Skia 图形库的文本整形(text shaping)模块,负责将 Unicode 文本转换为可渲染的字形(glyph)序列。文本整形是现代文本排版的核心环节,它处理了从字符到字形的复杂映射关系,包括连字(ligature)、字距调整(kerning)、上下文替换(contextual substitution)、双向文本(BiDi)重排序以及脚本特定的排版规则。

skshaper 采用了多后端架构设计,支持三种整形后端:HarfBuzz(完整的 OpenType 整形引擎)、CoreText(macOS/iOS 原生整形引擎)以及 Primitive(基础回退整形器)。这种设计允许根据平台能力和构建配置选择最适合的整形引擎。模块还引入了工厂模式(`SkShapers::Factory`),使得客户端可以在运行时选择整形后端。

skshaper 是 skparagraph(段落排版)模块的核心依赖。skparagraph 通过 `SkShaper::RunHandler` 接口接收整形结果,然后进行后续的换行和布局处理。同时,skshaper 依赖 skunicode 模块提供 Unicode 属性分析,如双向文本检测和脚本分类。

整形过程由一系列 `RunIterator` 驱动,它们将输入文本分割为具有相同属性的连续区段(run):相同字体的 `FontRunIterator`、相同 BiDi 级别的 `BiDiRunIterator`、相同脚本的 `ScriptRunIterator` 和相同语言的 `LanguageRunIterator`。整形器对每个区段调用底层整形引擎,并通过 `RunHandler` 回调输出结果。

## 架构图

```
+----------------------------------------------------------------+
|                          客户端代码                              |
|  (skparagraph::OneLineShaper / 直接使用者)                      |
+----------------------------+-----------------------------------+
                             |
                             v
+----------------------------------------------------------------+
|                         SkShaper                                |
|  shape(utf8, fontIter, bidiIter, scriptIter, langIter,         |
|        features, width, runHandler)                             |
+--------+------------------+-------------------+----------------+
         |                  |                   |
         v                  v                   v
+-----------------+ +-----------------+ +-----------------+
| HarfBuzz Shaper | | CoreText Shaper | | Primitive Shaper|
| (SkShaper_hb)   | | (SkShaper_ct)   | | (SkShaper_prim) |
| 完整 OpenType   | | macOS/iOS 原生   | | 基础回退        |
+---------+-------+ +-----------------+ +-----------------+
          |
          v
+-------------------+       +-------------------+
| HarfBuzz 库       |       | SkUnicode         |
| (OpenType 整形)   |       | (Unicode 属性)    |
+-------------------+       +-------------------+

+----------------------------------------------------------------+
|                      RunIterator 体系                           |
| FontRunIterator | BiDiRunIterator | ScriptRunIterator |         |
|                 | LanguageRunIterator                  |         |
+----------------------------------------------------------------+
                             |
                             v
+----------------------------------------------------------------+
|                       RunHandler                                |
| beginLine -> runInfo -> commitRunInfo -> runBuffer ->           |
| commitRunBuffer -> commitLine                                   |
+----------------------------------------------------------------+
```

## 目录结构

```
modules/skshaper/
|-- BUILD.bazel              # Bazel 构建配置
|-- BUILD.gn                 # GN 构建配置
|-- skshaper.gni             # GNI 源文件清单(自动生成)
|-- include/                 # 公共头文件
|   |-- BUILD.bazel
|   |-- SkShaper.h           # 核心整形器接口与 RunHandler
|   |-- SkShaper_factory.h   # 整形器工厂抽象
|   |-- SkShaper_harfbuzz.h  # HarfBuzz 整形器工厂函数
|   |-- SkShaper_coretext.h  # CoreText 整形器工厂函数
|   |-- SkShaper_skunicode.h # SkUnicode BiDi 迭代器工厂函数
|-- src/                     # 实现代码
|   |-- BUILD.bazel
|   |-- SkShaper.cpp         # 基础整形器实现与辅助函数
|   |-- SkShaper_factory.cpp # Primitive 工厂实现
|   |-- SkShaper_primitive.cpp  # 基础回退整形器
|   |-- SkShaper_harfbuzz.cpp   # HarfBuzz 整形器实现
|   |-- SkShaper_coretext.cpp   # CoreText 整形器实现
|   |-- SkShaper_skunicode.cpp  # SkUnicode BiDi 迭代器实现
|-- tests/                   # 测试
|   |-- BUILD.bazel
|   |-- ShaperTest.cpp       # 整形器单元测试
|-- utils/                   # 工具
    |-- BUILD.bazel
    |-- FactoryHelpers.h     # 工厂辅助(BestAvailable/HarfbuzzFactory)
```

## 关键类与函数

### SkShaper - 核心整形器

```cpp
class SkShaper {
public:
    // 完整整形接口
    virtual void shape(const char* utf8, size_t utf8Bytes,
                       FontRunIterator&, BiDiRunIterator&,
                       ScriptRunIterator&, LanguageRunIterator&,
                       const Feature* features, size_t featuresSize,
                       SkScalar width, RunHandler*) const = 0;

    // 简化接口(使用默认迭代器)
    virtual void shape(const char* utf8, size_t utf8Bytes,
                       const SkFont& srcFont, bool leftToRight,
                       SkScalar width, RunHandler*) const = 0;
};
```

### RunIterator 体系

| 迭代器 | 职责 | 输出 |
|--------|------|------|
| `FontRunIterator` | 按字体分段 | `currentFont()` |
| `BiDiRunIterator` | 按 BiDi 级别分段 | `currentLevel()` (偶数LTR,奇数RTL) |
| `ScriptRunIterator` | 按脚本分段 | `currentScript()` (ISO 15924 标签) |
| `LanguageRunIterator` | 按语言分段 | `currentLanguage()` (BCP-47 标签) |

### RunHandler - 整形结果回调

```cpp
class RunHandler {
    virtual void beginLine() = 0;           // 行开始
    virtual void runInfo(const RunInfo&) = 0;  // Run 信息(用于预分配)
    virtual void commitRunInfo() = 0;       // 所有 RunInfo 提交完毕
    virtual Buffer runBuffer(const RunInfo&) = 0;  // 请求输出缓冲区
    virtual void commitRunBuffer(const RunInfo&) = 0;  // Run 数据填充完毕
    virtual void commitLine() = 0;          // 行结束
};

struct Buffer {
    SkGlyphID* glyphs;   // 字形 ID 数组
    SkPoint* positions;   // 字形位置数组
    SkPoint* offsets;     // 字形偏移(可选)
    uint32_t* clusters;   // 字形到文本的映射(可选)
    SkPoint point;        // 基准点偏移
};
```

### SkTextBlobBuilderRunHandler

```cpp
class SkTextBlobBuilderRunHandler final : public SkShaper::RunHandler {
    // 便捷工具类:将整形结果直接构建为 SkTextBlob
    sk_sp<SkTextBlob> makeBlob();
    SkPoint endPoint();
};
```

### 整形器工厂

| 命名空间 | 函数 | 说明 |
|----------|------|------|
| `SkShapers::HB` | `ShaperDrivenWrapper()` | HarfBuzz 整形器(逐Run整形) |
| `SkShapers::HB` | `ShapeThenWrap()` | HarfBuzz 整形器(先整形后换行) |
| `SkShapers::HB` | `ShapeDontWrapOrReorder()` | HarfBuzz 整形器(不换行不重排) |
| `SkShapers::HB` | `ScriptRunIterator()` | HarfBuzz 脚本检测迭代器 |
| `SkShapers::CT` | `CoreText()` | macOS CoreText 整形器 |
| `SkShapers::Primitive` | `PrimitiveText()` | 基础回退整形器 |
| `SkShapers::unicode` | `BidiRunIterator()` | 基于 SkUnicode 的 BiDi 迭代器 |

### SkShapers::Factory - 整形器工厂抽象

```cpp
class Factory : public SkRefCnt {
    virtual std::unique_ptr<SkShaper> makeShaper(sk_sp<SkFontMgr> fallback) = 0;
    virtual std::unique_ptr<SkShaper::BiDiRunIterator> makeBidiRunIterator(...) = 0;
    virtual std::unique_ptr<SkShaper::ScriptRunIterator> makeScriptRunIterator(...) = 0;
    virtual SkUnicode* getUnicode() = 0;
};
// 预定义工厂: HarfbuzzFactory, CoreTextFactory, Primitive::Factory
```

## 依赖关系

```
skshaper
  |-- Skia Core
  |   |-- SkFont, SkFontMgr, SkFontStyle, SkTypeface
  |   |-- SkTextBlob, SkTextBlobBuilder
  |   |-- SkPoint, SkScalar, SkString, SkFourByteTag
  |   |-- SkRefCnt, SkSpan
  |
  |-- skunicode (可选,当 SK_SHAPER_UNICODE_AVAILABLE 定义时)
  |   |-- SkUnicode (BiDi 分析、脚本检测)
  |   |-- SkBidiIterator (双向文本迭代)
  |
  |-- HarfBuzz (可选,当 SK_SHAPER_HARFBUZZ_AVAILABLE 定义时)
  |   |-- hb_buffer_t (整形缓冲区)
  |   |-- hb_font_t (HarfBuzz 字体对象)
  |   |-- hb_shape() (核心整形函数)
  |
  |-- CoreText (可选,当 SK_SHAPER_CORETEXT_AVAILABLE 定义时,仅 Apple 平台)
  |   |-- CTLine, CTRun (CoreText 类型)
```

## 设计模式分析

### 1. 策略模式 (Strategy Pattern)
三个整形后端(HarfBuzz/CoreText/Primitive)实现了相同的 `SkShaper` 接口,客户端可以根据需要选择不同的整形策略,而无需修改调用代码。

### 2. 抽象工厂模式 (Abstract Factory)
`SkShapers::Factory` 定义了创建整形器及其配套迭代器的抽象接口,`HarfbuzzFactory`、`CoreTextFactory` 和 `Primitive::Factory` 提供了具体实现。`BestAvailable()` 函数根据编译配置自动选择最佳工厂。

### 3. 迭代器模式 (Iterator Pattern)
`RunIterator` 体系将文本分段逻辑抽象为迭代器接口,`FontRunIterator`、`BiDiRunIterator`、`ScriptRunIterator`、`LanguageRunIterator` 各自负责一种属性的分段。整形器通过组合这些迭代器来确定每个文本区段的属性。

### 4. 回调模式 (Callback Pattern)
`RunHandler` 使用回调模式输出整形结果。这种设计避免了大量中间数据的分配,允许调用方直接将结果写入目标数据结构。

### 5. 空对象模式 (Null Object)
`TrivialFontRunIterator`、`TrivialBiDiRunIterator`、`TrivialScriptRunIterator`、`TrivialLanguageRunIterator` 提供了"平凡"迭代器实现,将整个文本视为单一区段,用作默认值或测试。

## 数据流

```
输入: UTF-8 文本 + 字体 + BiDi 级别 + 脚本 + 语言 + OpenType 特性 + 宽度约束

SkShaper::shape()
  |
  +-- FontRunIterator: 将文本按字体分段
  |     (字体回退: 遍历 SkFontMgr 查找能渲染每个字符的字体)
  |
  +-- BiDiRunIterator: 将文本按 BiDi 嵌入级别分段
  |     (使用 SkUnicode/ICU 的 BiDi 算法)
  |
  +-- ScriptRunIterator: 将文本按 Unicode 脚本分段
  |     (HarfBuzz 的 hb_script_t 或 ICU 的脚本检测)
  |
  +-- LanguageRunIterator: 将文本按语言标签分段
  |
  +-- 计算所有迭代器的交集区段
  |
  +-- 对每个区段调用底层整形引擎:
  |     HarfBuzz:  hb_shape(hb_font, hb_buffer, features)
  |     CoreText:  CTLineCreateWithAttributedString()
  |     Primitive: 简单的字符到字形一一映射
  |
  +-- 通过 RunHandler 输出结果:
        beginLine()
          -> runInfo() (报告每个 Run 的元信息)
          -> commitRunInfo()
          -> runBuffer() (获取输出缓冲区)
             填写: glyphs[], positions[], offsets[], clusters[]
          -> commitRunBuffer()
        commitLine()

输出: 字形 ID 数组 + 字形位置 + 字形到文本映射 + 字体信息
```

## 相关文档与参考

- **skparagraph 模块**: `modules/skparagraph/` - 使用 skshaper 进行段落排版
- **skunicode 模块**: `modules/skunicode/` - 提供 Unicode 属性分析
- **HarfBuzz**: https://harfbuzz.github.io/ - OpenType 文本整形引擎
- **CoreText**: Apple 平台的文本整形框架
- **Unicode UAX #9**: Unicode 双向算法 (BiDi)
- **Unicode UAX #24**: Unicode 脚本属性
- **OpenType 规范**: 字体特性(features)、GSUB/GPOS 表
- **ISO 15924**: 脚本代码标准
- **BCP-47**: 语言标签标准
