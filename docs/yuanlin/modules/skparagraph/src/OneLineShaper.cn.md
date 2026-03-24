# OneLineShaper

> 源文件: modules/skparagraph/src/OneLineShaper.h, modules/skparagraph/src/OneLineShaper.cpp

## 概述

`OneLineShaper` 是 Skia 段落布局系统中的文本整形器(text shaper),负责将原始文本转换为可渲染的字形(glyph)序列。该类作为 `SkShaper::RunHandler` 的实现,与 HarfBuzz 整形引擎协作,处理复杂的文本整形需求,包括字体回退(font fallback)、未解析字形处理、表情符号识别、字体特性应用等。

整形过程涉及多个层次的处理:按整形区域(Bidi、脚本、语言)分段,按字体样式组合,按字体族匹配,最终通过 HarfBuzz 生成字形并构建 `Run` 对象。

## 架构位置

`OneLineShaper` 位于段落布局系统的文本处理层,连接 Unicode 文本和整形后的字形数据:

```
skia/modules/skparagraph/
├── include/
│   └── Paragraph.h
└── src/
    ├── ParagraphImpl.h/.cpp        # 段落实现,调用OneLineShaper
    ├── OneLineShaper.h/.cpp        # 文本整形器
    ├── Run.h/.cpp                  # 整形结果(Run对象)
    └── Iterators.h                 # 文本迭代器(Bidi、脚本等)
```

**数据流:**
```
Unicode文本 → OneLineShaper → HarfBuzz → Run对象 → ParagraphImpl
```

**调用关系:**
- `ParagraphImpl::shape()` 创建 `OneLineShaper` 并调用 `shape()`
- `OneLineShaper` 使用 `SkShaper` (HarfBuzz) 进行整形
- 整形结果通过 `RunHandler` 回调接口返回并存储为 `Run` 对象

## 主要类与结构体

### OneLineShaper
```cpp
class OneLineShaper : public SkShaper::RunHandler
```
文本整形器,实现 HarfBuzz 的 `RunHandler` 接口。

**核心成员:**
- `fParagraph`: 所属的段落实现指针
- `fCurrentRun`: 当前正在处理的 Run
- `fCurrentText`: 当前处理的文本范围
- `fUnresolvedBlocks`: 未解析的文本块队列
- `fResolvedBlocks`: 已解析的文本块数组
- `fFallbackFonts`: 字体回退缓存(码点到字体的映射)
- `fHeight`: 行高倍数
- `fUseHalfLeading`: 是否使用半行距
- `fBaselineShift`: 基线偏移
- `fAdvance`: 累积的前进宽度和高度
- `fUnresolvedGlyphs`: 未解析字形数量
- `fUniqueRunId`: 唯一的 Run ID 生成器

### RunBlock
```cpp
struct RunBlock
```
文本块的表示,可能是已解析或未解析的。

**成员:**
- `fRun`: 关联的 Run 对象(未解析时可能为 null)
- `fText`: 文本范围
- `fGlyphs`: 字形范围

**类型:**
- 未解析块: `fRun == nullptr`,仅包含文本范围
- 部分解析块: `fRun != nullptr`,但字形范围小于 Run 大小
- 完全解析块: `fRun != nullptr`,字形范围等于 Run 大小

### FontKey
```cpp
struct FontKey
```
字体回退缓存的键。

**成员:**
- `fUnicode`: Unicode 码点
- `fFontStyle`: 字体样式
- `fLocale`: 语言区域
- `fFontArgs`: 字体参数

实现了 `operator==` 和 `Hasher`,用于哈希表查找。

### Resolved 枚举
```cpp
enum Resolved {
    Nothing,     // 未解析任何字符
    Something,   // 解析了部分字符
    Everything   // 解析了所有字符
};
```

## 公共 API 函数

### 主入口
```cpp
bool shape()
```
执行整形操作的主入口,遍历段落中的所有整形区域,应用字体样式,执行 HarfBuzz 整形,最终生成 Run 对象。

**返回:** 整形是否成功

### 工具函数
```cpp
size_t unresolvedGlyphs()
```
获取未解析的字形数量,用于判断整形质量。

```cpp
static SkUnichar getEmojiSequenceStart(SkUnicode* unicode,
                                       const char** begin,
                                       const char* end)
```
静态工具函数,检测文本起始是否为表情符号序列,如果是则返回第一个码点并前进指针,否则返回 -1。

**实现:** 基于 Unicode TR51 表情符号序列定义

## 内部实现细节

### 整形流程
完整的整形流程分为多个层次:

```cpp
bool OneLineShaper::shape() {
    return iterateThroughShapingRegions([&](TextRange textRange, SkSpan<Block> styleSpan,
                                             SkScalar& advanceX, TextIndex, uint8_t) {
        iterateThroughFontStyles(textRange, styleSpan, [&](Block block, TArray<SkShaper::Feature> features) {
            matchResolvedFonts(block.fStyle, [&](sk_sp<SkTypeface> typeface) {
                // 实际调用 HarfBuzz 整形
                shaper->shape(...);
                return hasUnresolved ? Resolved::Something : Resolved::Everything;
            });
        });
        finish(block, fHeight, advanceX);
        return fAdvance.fX;
    });
}
```

**层次结构:**
1. **整形区域**: 按 Bidi 级别、脚本、语言分割文本
2. **字体样式**: 合并相同字体属性的样式块
3. **字体匹配**: 尝试配置的字体族和回退字体
4. **HarfBuzz 整形**: 实际的整形操作
5. **处理结果**: 分类已解析和未解析的字形

### RunHandler 回调实现
作为 `SkShaper::RunHandler`,实现以下回调:

```cpp
Buffer runBuffer(const RunInfo& info) override {
    fCurrentRun = std::make_shared<Run>(fParagraph, info, fCurrentText.start,
                                        fHeight, fUseHalfLeading, fBaselineShift,
                                        ++fUniqueRunId, fAdvance.fX);
    return fCurrentRun->newRunBuffer();
}

void commitRunBuffer(const RunInfo&) override {
    // 分类已解析和未解析的字形
    sortOutGlyphs([&](GlyphRange block) {
        addUnresolvedWithRun(block);
    });

    // 填充已解析的间隙
    if (oldUnresolvedCount == fUnresolvedBlocks.size()) {
        addFullyResolved();
    } else {
        fillGaps(oldUnresolvedCount);
    }
}
```

**关键点:**
- `runBuffer()`: 创建 Run 对象并返回缓冲区给 HarfBuzz 填充
- `commitRunBuffer()`: 分析整形结果,区分已解析和未解析的部分

### 字形解析状态分类
`sortOutGlyphs()` 遍历字形,按字位(grapheme)边界分类已解析和未解析的字形:

```cpp
void OneLineShaper::sortOutGlyphs(std::function<void(GlyphRange)>&& sortOutUnresolvedBLock) {
    GlyphRange block = EMPTY_RANGE;
    bool graphemeResolved = false;
    TextIndex graphemeStart = EMPTY_INDEX;

    for (size_t i = 0; i < fCurrentRun->size(); ++i) {
        auto glyph = fCurrentRun->fGlyphs[i];
        GraphemeIndex gi = fParagraph->findPreviousGraphemeBoundary(ci);

        if (gi 变化) {
            // 新字位开始
            bool isControl = fParagraph->codeUnitHasProperty(ci, SkUnicode::CodeUnitFlags::kControl);
            graphemeResolved = glyph != 0 || isControl;
            graphemeStart = gi;
        } else if (glyph == 0) {
            // 字位内有未解析字形,整个字位标记为未解析
            graphemeResolved = false;
        }

        if (!graphemeResolved) {
            // 扩展未解析块
        } else {
            // 结束未解析块并报告
        }
    }
}
```

**设计决策:**
- 按字位而非单个字形分类,确保字位完整性
- 控制字符(Control codepoints)视为已解析,避免误报
- 未解析块可能跨越多个字形

### 填充已解析间隙
`fillGaps()` 在未解析块之间填充已解析的部分:

```cpp
void OneLineShaper::fillGaps(size_t startingCount) {
    TextIndex resolvedTextStart = resolvedTextLimits.start;
    GlyphIndex resolvedGlyphsStart = 0;

    for (auto& unresolved : 新添加的未解析块) {
        // 前面的已解析部分
        TextRange resolvedText(resolvedTextStart, unresolved.fText.start);
        if (resolvedText.width() > 0) {
            GlyphRange resolvedGlyphs(resolvedGlyphsStart, unresolved.fGlyphs.start);
            fResolvedBlocks.emplace_back(resolved);
        }

        resolvedGlyphsStart = unresolved.fGlyphs.end;
        resolvedTextStart = unresolved.fText.end;
    }

    // 最后的已解析部分
    if (resolvedText.width() > 0) {
        fResolvedBlocks.emplace_back(resolved);
    }
}
```

处理 LTR 和 RTL 的不同顺序逻辑。

### 字体回退处理
`matchResolvedFonts()` 实现多层次的字体回退:

```cpp
void OneLineShaper::matchResolvedFonts(const TextStyle& textStyle, const TypefaceVisitor& visitor) {
    // 1. 尝试配置的字体族
    for (const auto& typeface : textStyle.getFontFamilies()) {
        if (visitor(typeface) == Resolved::Everything) {
            return;
        }
    }

    // 2. 字体回退启用时
    if (fParagraph->fFontCollection->fontFallbackEnabled()) {
        while (!fUnresolvedBlocks.empty()) {
            auto unresolvedRange = fUnresolvedBlocks.front().fText;
            THashSet<SkUnichar> alreadyTriedCodepoints;

            // 遍历未解析块的每个码点/表情符号
            while (ch != chEnd) {
                // 检测表情符号序列
                SkUnichar emojiStart = OneLineShaper::getEmojiSequenceStart(...);
                if (emojiStart != -1) {
                    typeface = fParagraph->fFontCollection->defaultEmojiFallback(...);
                } else {
                    // 普通码点,先查缓存
                    codepoint = SkUTF::NextUTF8(...);
                    FontKey fontKey(codepoint, textStyle.getFontStyle(), ...);
                    auto found = fFallbackFonts.find(fontKey);
                    if (found != nullptr) {
                        typeface = *found;
                    } else {
                        typeface = fParagraph->fFontCollection->defaultFallback(...);
                        fFallbackFonts.set(fontKey, typeface);
                    }
                }

                // 尝试使用找到的字体
                if (typeface && visitor(typeface) == Resolved::Everything) {
                    break;
                }
            }
        }
    }
}
```

**回退策略:**
1. 使用配置的字体族列表
2. 针对每个未解析码点查找默认回退字体
3. 表情符号使用专门的表情字体回退
4. 缓存回退字体避免重复查找

### 表情符号检测
`getEmojiSequenceStart()` 识别表情符号序列:

```cpp
SkUnichar OneLineShaper::getEmojiSequenceStart(SkUnicode* unicode,
                                               const char** begin,
                                               const char* end) {
    const char* start = *begin;
    SkUnichar firstCodepoint = SkUTF::NextUTF8WithReplacement(begin, end);

    if (!unicode->isEmoji(firstCodepoint)) {
        *begin = start;  // 回退指针
        return -1;
    }

    // 检查是否为多码点表情序列
    while (*begin < end) {
        if (unicode->isEmojiComponent(...)) {
            // 继续前进
            continue;
        }
        break;
    }

    return firstCodepoint;
}
```

支持复杂的表情序列,如肤色修饰符、ZWJ 序列等。

### 最终装配
`finish()` 将所有已解析和未解析的块装配成最终的 Run 列表:

```cpp
void OneLineShaper::finish(const Block& block, SkScalar height, SkScalar& advanceX) {
    // 1. 将剩余未解析块加入已解析列表
    while (!fUnresolvedBlocks.empty()) {
        auto unresolved = fUnresolvedBlocks.front();
        fResolvedBlocks.emplace_back(unresolved);
        fUnresolvedGlyphs += unresolved.fGlyphs.width();
        fParagraph->addUnresolvedCodepoints(unresolved.fText);
    }

    // 2. 按文本顺序排序
    std::sort(fResolvedBlocks.begin(), fResolvedBlocks.end(),
              [](const RunBlock& a, const RunBlock& b) {
                  return a.fText.start < b.fText.start;
              });

    // 3. 将块转换为 Run 对象并添加到段落
    for (auto& resolvedBlock : fResolvedBlocks) {
        if (resolvedBlock.isFullyResolved()) {
            // 直接移动整个 Run
            fParagraph->fRuns.emplace_back(*resolvedBlock.fRun);
        } else if (run != nullptr) {
            // 复制 Run 的一部分
            // 创建新 Run,复制指定范围的字形、位置、偏移
            ...
        }
    }
}
```

**关键操作:**
- 排序确保文本连续性
- 区分完全解析(直接移动)和部分解析(复制子范围)
- 记录字体切换位置(`fFontSwitches`)

### 字体特性应用
`iterateThroughFontStyles()` 收集并应用字体特性:

```cpp
void OneLineShaper::iterateThroughFontStyles(...) {
    TArray<SkShaper::Feature> features;

    auto addFeatures = [&features](const Block& block) {
        // 用户配置的字体特性
        for (auto& ff : block.fStyle.getFontFeatures()) {
            SkShaper::Feature feature = {
                SkSetFourByteTag(ff.fName[0], ff.fName[1], ff.fName[2], ff.fName[3]),
                ff.fValue,
                block.fRange.start,
                block.fRange.end
            };
            features.emplace_back(feature);
        }

        // 字符间距时禁用连字
        if (block.fStyle.getLetterSpacing() > 0) {
            features.emplace_back(SkShaper::Feature{
                SkSetFourByteTag('l', 'i', 'g', 'a'), 0, ...
            });
        }
    };

    // 合并相同字体属性的样式块
    for (auto& block : styleSpan) {
        if (block.fStyle.matchOneAttribute(StyleType::kFont, combinedBlock.fStyle)) {
            combinedBlock.add(blockRange);
            addFeatures(block);
        } else {
            visitor(combinedBlock, features);
            combinedBlock = block;
            features.clear();
            addFeatures(block);
        }
    }
}
```

支持 OpenType 特性如连字(liga)、小型大写字母(smcp)等。

## 依赖关系

### 核心依赖
- **SkShaper**: HarfBuzz 整形器接口
- **ParagraphImpl**: 段落实现,提供文本、样式、字体集合
- **SkUnicode**: Unicode 属性查询(表情符号、字位边界等)
- **FontCollection**: 字体管理和回退
- **Run**: 整形结果的存储

### 使用的迭代器
- **Bidi 迭代器**: 按双向文本级别分割
- **Script 迭代器**: 按 Unicode 脚本分割
- **Language 迭代器**: 按语言分割
- **Font 迭代器**: 按字体族分割

### 依赖图
```
OneLineShaper
    ↓ (uses)
SkShaper (HarfBuzz) + SkUnicode + FontCollection
    ↓ (produces)
Run 对象
    ↓ (stored in)
ParagraphImpl
```

## 设计模式与设计决策

### 策略模式
使用函数对象(lambda)作为访问器,支持不同的处理策略:
- `ShapeVisitor`: 整形区域访问器
- `ShapeSingleFontVisitor`: 单字体样式访问器
- `TypefaceVisitor`: 字体匹配访问器

灵活性高,易于测试和扩展。

### 分层处理
整形流程分为多个层次,每层处理特定的关注点:
1. 整形区域(Bidi/脚本/语言)
2. 字体样式合并
3. 字体匹配和回退
4. HarfBuzz 整形
5. 结果分类和装配

清晰的分层使代码易于理解和维护。

### 缓存优化
- **字体回退缓存**: `fFallbackFonts` 避免重复查找
- **表情字体缓存**: 表情回退结果也可缓存
- **字位边界缓存**: ParagraphImpl 缓存字位边界

### 惰性解析
未解析的块在 `finish()` 阶段才最终处理,允许多次尝试不同字体。

### 块合并优化
相邻的相同属性块合并为单个块,减少 HarfBuzz 调用次数。

## 性能考量

### 内存管理
- **共享 Run 数据**: 使用 `std::shared_ptr<Run>` 共享字形数据
- **队列和数组**: `fUnresolvedBlocks` 使用 `std::deque` 支持高效的首尾操作
- **哈希表**: `fFallbackFonts` 使用 `THashMap` 快速查找

### 整形优化
- **批量整形**: 相同属性的文本合并为一次整形调用
- **字体回退缓存**: 避免重复的字体查找
- **字位级分类**: 按字位而非字形分类,减少细粒度处理

### 表情处理
- 专门的表情序列检测,避免错误分割
- 表情字体回退优先使用彩色表情字体

### 未解析字形处理
- 逐码点尝试回退字体,最大化解析率
- 缓存未解析码点,供上层报告或替换处理

## 相关文件

### 整形相关
- `modules/skshaper/include/SkShaper.h`: HarfBuzz 整形器接口
- `modules/skshaper/include/SkShaper_harfbuzz.h`: HarfBuzz 实现
- `modules/skparagraph/src/Iterators.h`: 文本迭代器(Bidi、脚本等)

### 段落系统
- `modules/skparagraph/src/ParagraphImpl.h/.cpp`: 段落实现,调用者
- `modules/skparagraph/src/Run.h/.cpp`: 整形结果存储

### Unicode 处理
- `modules/skunicode/include/SkUnicode.h`: Unicode 属性查询

### 字体管理
- `modules/skparagraph/include/FontCollection.h`: 字体集合和回退
