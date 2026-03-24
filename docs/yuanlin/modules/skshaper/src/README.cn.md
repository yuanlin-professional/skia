# skshaper/src - 文本整形引擎实现

## 概述

`src/` 目录包含 skshaper 模块所有整形后端的具体实现代码。这里实现了三种文本整形策略:HarfBuzz(功能最完整的 OpenType 整形引擎)、CoreText(Apple 平台原生整形)和 Primitive(最小化回退整形器)。每种策略都实现了 `SkShaper` 抽象接口。

HarfBuzz 后端 (`SkShaper_harfbuzz.cpp`) 是最重要的实现,它提供了三种整形模式:ShaperDrivenWrapper(逐 Run 整形并换行)、ShapeThenWrap(先整形后换行)和 ShapeDontWrapOrReorder(仅整形不处理布局)。HarfBuzz 后端还负责字体回退的协调,当某个字体无法渲染特定字符时,自动从 SkFontMgr 中查找替代字体。

Primitive 后端 (`SkShaper_primitive.cpp`) 作为最后的回退选项,不依赖任何外部库,仅执行简单的字符到字形的一对一映射,不支持连字、字距调整等高级排版特性。

## 架构图

```
+-----------------------------------------------+
|              SkShaper 接口                      |
+-------+------------+------------+--------------+
        |            |            |
        v            v            v
+-------------+ +----------+ +------------+
|SkShaper_hb  | |SkShaper  | |SkShaper    |
|.cpp         | |_coretext | |_primitive  |
|             | |.cpp      | |.cpp        |
|3种整形模式: | |          | |            |
|- ShaperDriven| |CTLine    | |逐字符映射  |
|- ShapeThenWrap| |CTRun    | |无连字/字距 |
|- ShapeDontWrap| |         | |            |
+------+------+ +----------+ +------------+
       |
       v
+------+------+     +-------------+
| HarfBuzz库  |     |SkShaper     |
| hb_shape()  |     |_skunicode   |
| hb_font_t   |     |.cpp         |
| hb_buffer_t |     |BiDi迭代器   |
+-------------+     +-------------+
       |                  |
       v                  v
+-------------+     +----------+
|SkTypeface   |     |SkUnicode |
|(字体数据)    |     |(BiDi分析) |
+-------------+     +----------+
```

## 目录结构

```
src/
|-- BUILD.bazel              # Bazel 构建规则
|-- SkShaper.cpp             # 基础实现: MakeFontMgrRunIterator, MakeStdLanguageRunIterator
|-- SkShaper_factory.cpp     # Primitive::Factory 实现
|-- SkShaper_primitive.cpp   # Primitive 整形器: 简单字符到字形映射
|-- SkShaper_harfbuzz.cpp    # HarfBuzz 整形器: 完整 OpenType 整形
|-- SkShaper_coretext.cpp    # CoreText 整形器: macOS/iOS 原生整形
|-- SkShaper_skunicode.cpp   # SkUnicode BiDi 迭代器实现
```

## 关键类与函数

### SkShaper.cpp - 通用基础实现

```cpp
// 创建字体回退迭代器
std::unique_ptr<FontRunIterator> SkShaper::MakeFontMgrRunIterator(
    const char* utf8, size_t utf8Bytes,
    const SkFont& font, sk_sp<SkFontMgr> fallback);

// 创建标准语言迭代器
std::unique_ptr<LanguageRunIterator> SkShaper::MakeStdLanguageRunIterator(
    const char* utf8, size_t utf8Bytes);

// SkTextBlobBuilderRunHandler 实现
// - beginLine/commitLine: 管理行的起止
// - runInfo: 累计 ascent/descent/leading 用于行高计算
// - runBuffer: 从 SkTextBlobBuilder 分配存储
// - commitRunBuffer: 更新簇映射偏移
```

### SkShaper_harfbuzz.cpp - HarfBuzz 后端

这是最复杂的实现文件,包含三种整形模式:

| 类 | 模式 | 说明 |
|----|------|------|
| `ShaperDrivenWrapper` | 逐 Run 整形 | 先分段再整形,每个 Run 独立整形后拼合,支持换行 |
| `ShapeThenWrap` | 先整形后换行 | 整行整形后根据宽度约束查找换行点 |
| `ShapeDontWrapOrReorder` | 仅整形 | 仅执行整形,不处理换行和 BiDi 重排序 |

核心整形流程:

```cpp
void shape(utf8, fontIter, bidiIter, scriptIter, langIter, features, width, handler) {
    // 1. 将 SkFont/SkTypeface 转换为 hb_font_t
    // 2. 将 UTF-8 文本填入 hb_buffer_t
    // 3. 设置 buffer 的脚本、语言、方向
    // 4. 调用 hb_shape(hb_font, hb_buffer, features, num_features)
    // 5. 从 hb_buffer 中提取字形信息
    // 6. 通过 RunHandler 输出结果
}
```

HarfBuzz 缓存管理:

```cpp
void SkShapers::HB::PurgeCaches();  // 清除 HarfBuzz 字体缓存
// HarfBuzz 为每个 SkTypeface 创建 hb_font_t,通过缓存避免重复创建
```

### SkShaper_coretext.cpp - CoreText 后端

```cpp
// 使用 Apple CoreText 框架进行整形
// 1. 将文本和属性创建为 CFAttributedString
// 2. 通过 CTLineCreateWithAttributedString 创建 CTLine
// 3. 遍历 CTRun 提取字形和位置
// 4. 通过 RunHandler 输出结果
```

CoreText 后端的特点:
- 仅在 macOS/iOS 上可用
- 自动处理所有 Apple 平台特定的排版规则
- 不需要额外的 Unicode 库(CoreText 自带)
- 不支持自定义 OpenType 特性(Feature)

### SkShaper_primitive.cpp - Primitive 后端

```cpp
// 最简单的整形器:
// 1. 遍历 UTF-8 文本的每个 Unicode 码点
// 2. 使用 SkFont::textToGlyphs 进行字符到字形映射
// 3. 使用 SkFont::getWidths 获取字形宽度
// 4. 按顺序排列字形位置
// 不支持: 连字、字距调整、上下文替换、复杂脚本
```

### SkShaper_skunicode.cpp - BiDi 迭代器

```cpp
// 基于 SkUnicode 的 BiDi 分析迭代器
// 将 SkUnicode::makeBidiIterator 的结果包装为 SkShaper::BiDiRunIterator
// 输出每个 BiDi 区段的嵌入级别(偶数=LTR, 奇数=RTL)
```

## 依赖关系

```
src/
  |-- include/ (SkShaper.h, SkShaper_*.h 公共接口)
  |-- Skia Core
  |   |-- SkFont, SkTypeface, SkFontMgr, SkFontMetrics
  |   |-- SkTextBlobBuilder, SkGlyphID, SkPoint
  |   |-- SkString, SkSpan, SkTHash
  |-- skunicode (SkShaper_skunicode.cpp, SkShaper_harfbuzz.cpp)
  |   |-- SkUnicode, SkBidiIterator
  |-- HarfBuzz 第三方库 (SkShaper_harfbuzz.cpp)
  |   |-- hb.h, hb-ot.h
  |-- CoreText 框架 (SkShaper_coretext.cpp, 仅 Apple 平台)
  |   |-- CoreText/CoreText.h, CoreFoundation/CoreFoundation.h
```

## 设计模式分析

### 模板方法模式
HarfBuzz 的三种整形模式共享大量公共代码(HarfBuzz 初始化、字体转换、缓冲区管理),但在换行和重排序逻辑上有所不同。公共逻辑提取为基础方法,差异部分由各子类实现。

### 适配器模式
- `SkShaper_harfbuzz.cpp` 将 Skia 的 SkTypeface 适配为 HarfBuzz 的 hb_font_t
- `SkShaper_coretext.cpp` 将 Skia 的 SkFont 适配为 CoreText 的 CTFont
- `SkShaper_skunicode.cpp` 将 SkBidiIterator 适配为 SkShaper::BiDiRunIterator

### 缓存策略
HarfBuzz 后端缓存 hb_font_t 对象(基于 SkTypeface 的唯一 ID),避免在频繁整形时重复创建 HarfBuzz 字体对象。缓存通过 `PurgeCaches()` 手动清除。

## 数据流

```
SkShaper::shape() 调用
  |
  +-- [所有后端共通]
  |   计算 FontRunIterator x BiDiRunIterator x ScriptRunIterator x LanguageRunIterator
  |   的交集,产生最细粒度的区段 (run)
  |
  +-- [HarfBuzz 路径]
  |   |-- 查找/创建 hb_font_t (可能从缓存获取)
  |   |-- 创建 hb_buffer_t, 添加 UTF-8 文本
  |   |-- 设置 script, language, direction
  |   |-- 添加 OpenType features
  |   |-- hb_shape(font, buffer, features, num_features)
  |   |-- 从 buffer 提取: glyph_infos[], glyph_positions[]
  |   |-- 通过 RunHandler 回调输出
  |
  +-- [CoreText 路径]
  |   |-- 创建 CFAttributedString
  |   |-- CTLineCreateWithAttributedString -> CTLine
  |   |-- CFArrayGetCount(CTLineGetGlyphRuns) -> CTRun[]
  |   |-- CTRunGetGlyphs, CTRunGetPositions, CTRunGetStringIndices
  |   |-- 通过 RunHandler 回调输出
  |
  +-- [Primitive 路径]
      |-- SkFont::textToGlyphs(utf8) -> glyphIDs[]
      |-- SkFont::getWidths(glyphIDs) -> widths[]
      |-- 计算累积位置
      |-- 通过 RunHandler 回调输出
```

## 相关文档与参考

- **公共接口**: `modules/skshaper/include/` - API 定义
- **工厂辅助**: `modules/skshaper/utils/FactoryHelpers.h` - BestAvailable 等
- **测试**: `modules/skshaper/tests/ShaperTest.cpp` - 整形器测试
- **HarfBuzz 文档**: https://harfbuzz.github.io/
- **Apple CoreText**: Apple 开发者文档中的 Core Text 编程指南
