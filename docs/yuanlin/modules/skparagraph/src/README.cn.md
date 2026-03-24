# skparagraph/src - 段落排版核心实现

## 概述

`src/` 目录包含 skparagraph 模块的全部内部实现代码。这些文件实现了 `include/` 中定义的抽象接口,构成了段落排版引擎的核心处理管线。从文本整形(shaping)到换行(line breaking)、从样式应用到最终绘制,所有复杂的排版逻辑都在此目录中实现。

核心排版流程由 `ParagraphImpl` 驱动,它维护了一个状态机来跟踪排版管线的进度。排版过程涉及多个关键组件的协作:`OneLineShaper` 负责调用 SkShaper 进行文本整形,`TextWrapper` 负责根据宽度约束将整形后的文本拆分为多行,`TextLine` 负责管理单行的布局和绘制,`Decorations` 负责绘制文本装饰效果。

本目录中的所有类都属于内部实现,不保证 ABI 稳定性。外部代码不应直接包含这些头文件。

## 架构图

```
+---------------------------------------------------------------+
|                    ParagraphBuilderImpl                        |
|  (管理样式栈, 收集文本和 Block, 构建 ParagraphImpl)             |
+---------------------------+-----------------------------------+
                            |  Build()
                            v
+---------------------------------------------------------------+
|                      ParagraphImpl                             |
|  状态机: kUnknown -> kIndexed -> kShaped -> kLineBroken        |
|          -> kFormatted -> kDrawn                               |
+-------+-------+-------+-------+-------------------------------+
        |       |       |       |
        v       v       v       v
+--------+ +--------+ +--------+ +-------+
|Unicode | |OneLine | |Text    | |Text   |
|属性计算 | |Shaper  | |Wrapper | |Line   |
|        | |文本整形 | |换行    | |行管理  |
+--------+ +--------+ +--------+ +---+---+
                                     |
                               +-----+------+
                               |            |
                               v            v
                        +----------+  +----------+
                        |Decorations|  |ParagraphPainter|
                        |装饰绘制   |  |Impl (Canvas)   |
                        +----------+  +----------+
```

## 目录结构

```
src/
|-- BUILD.bazel                  # Bazel 构建规则
|-- ParagraphBuilderImpl.cpp     # 段落构建器实现 (样式栈/文本收集/Build)
|-- ParagraphBuilderImpl.h       # 段落构建器实现头文件
|-- ParagraphImpl.cpp            # 段落核心实现 (排版管线)
|-- ParagraphImpl.h              # 段落核心实现头文件
|-- ParagraphCache.cpp           # 段落缓存实现
|-- ParagraphStyle.cpp           # 段落样式实现
|-- OneLineShaper.cpp            # 单行文本整形器 (调用 SkShaper)
|-- OneLineShaper.h              # 单行整形器头文件
|-- Run.cpp                      # Run 和 Cluster 实现
|-- Run.h                        # Run, Cluster, InternalLineMetrics 定义
|-- TextLine.cpp                 # 文本行布局与绘制
|-- TextLine.h                   # 文本行定义
|-- TextWrapper.cpp              # 文本换行算法
|-- TextWrapper.h                # 换行器定义
|-- FontCollection.cpp           # 字体集合实现
|-- FontArguments.cpp            # 字体参数实现
|-- TextStyle.cpp                # 文本样式比较与匹配
|-- TextShadow.cpp               # 文本阴影实现
|-- TypefaceFontProvider.cpp     # 自定义字体提供器实现
|-- Decorations.cpp              # 文本装饰(下划线等)绘制
|-- Decorations.h                # 装饰绘制器头文件
|-- ParagraphPainterImpl.cpp     # Canvas 段落绘制器实现
|-- ParagraphPainterImpl.h       # Canvas 绘制器头文件
|-- Iterators.h                  # LangIterator 语言迭代器
```

## 关键类与函数

### ParagraphImpl - 排版管线核心

`ParagraphImpl` 继承自 `Paragraph`,实现完整的排版管线:

```cpp
class ParagraphImpl final : public Paragraph {
    // 排版管线5步
    bool computeCodeUnitProperties();       // 1. 分析Unicode属性
    void applySpacingAndBuildClusterTable();// 2. 构建Cluster表
    bool shapeTextIntoEndlessLine();        // 3. 文本整形
    void breakShapedTextIntoLines(SkScalar);// 4. 换行
    void formatLines(SkScalar maxWidth);    // 5. 格式化对齐

    // 内部状态
    InternalState fState;  // kUnknown -> kIndexed -> kShaped -> kLineBroken -> kFormatted
    skia_private::TArray<Run> fRuns;          // 整形后的排版段
    skia_private::TArray<Cluster> fClusters;  // 字符簇表
    skia_private::TArray<TextLine> fLines;    // 排版后的文本行
    skia_private::TArray<SkUnicode::CodeUnitFlags> fCodeUnitProperties; // Unicode属性
};
```

### Run - 排版段

`Run` 是文本整形的基本输出单位,表示使用同一字体和属性的连续字形序列:

```cpp
class Run {
    SkFont fFont;                    // 使用的字体
    TextRange fTextRange;            // 对应的文本范围
    STArray<64, SkGlyphID> fGlyphs;  // 字形ID数组
    STArray<64, SkPoint> fPositions;  // 字形位置数组
    STArray<64, uint32_t> fClusterIndexes; // 字形到Cluster的映射
    uint8_t fBidiLevel;              // BiDi嵌入级别(偶数LTR,奇数RTL)
    SkFontMetrics fFontMetrics;      // 字体度量信息
    SkScalar fHeightMultiplier;      // 行高乘数
};
```

### Cluster - 字符簇

`Cluster` 将字形映射回文本,是最小的可断行排版单元:

```cpp
class Cluster {
    enum BreakType { None, GraphemeBreak, SoftLineBreak, HardLineBreak };
    RunIndex fRunIndex;        // 所属的Run索引
    TextRange fTextRange;      // 对应的文本范围
    SkScalar fWidth;           // 簇的宽度
    SkScalar fHeight;          // 簇的高度
    bool fIsWhiteSpaceBreak;   // 是否是空格断行点
    bool fIsHardBreak;         // 是否是硬换行
    bool fIsIdeographic;       // 是否是表意文字
};
```

### TextLine - 文本行

`TextLine` 管理一行文本的布局和绘制:

```cpp
class TextLine {
    TextRange fTextExcludingSpaces;   // 不含尾部空格的文本范围
    TextRange fText;                   // 完整文本范围
    ClusterRange fClusterRange;        // Cluster范围
    SkVector fAdvance;                 // 行尺寸(宽x高)
    SkVector fOffset;                  // 行位置偏移
    std::unique_ptr<Run> fEllipsis;    // 省略号Run(如有)
    InternalLineMetrics fSizes;        // 行度量信息

    void format(TextAlign align, SkScalar maxWidth);  // 对齐格式化
    void paint(ParagraphPainter* painter, SkScalar x, SkScalar y); // 绘制
    void createEllipsis(SkScalar maxWidth, const SkString& ellipsis, bool ltr); // 创建省略号
};
```

### TextWrapper - 换行器

`TextWrapper` 实现基于宽度约束的文本换行算法:

```cpp
class TextWrapper {
    void breakTextIntoLines(ParagraphImpl* parent,
                            SkScalar maxWidth,
                            const AddLineToParagraph& addLine);
    // 内部辅助
    void lookAhead(SkScalar maxWidth, Cluster* end, bool roundingHack);
    void moveForward(bool hasEllipsis);
    void trimEndSpaces(TextAlign align);
};
```

### OneLineShaper - 单行整形器

`OneLineShaper` 继承自 `SkShaper::RunHandler`,协调文本整形过程:

```cpp
class OneLineShaper : public SkShaper::RunHandler {
    bool shape();  // 执行整形
    // 字体回退处理
    void matchResolvedFonts(const TextStyle&, const TypefaceVisitor&);
    // Emoji序列检测
    static SkUnichar getEmojiSequenceStart(SkUnicode*, const char**, const char*);
    // RunHandler 回调
    Buffer runBuffer(const RunInfo& info) override;
    void commitRunBuffer(const RunInfo&) override;
};
```

### Decorations - 文本装饰

```cpp
class Decorations {
    void paint(ParagraphPainter*, const TextStyle&, const TextLine::ClipContext&, SkScalar baseline);
    // 内部计算
    void calculateThickness(TextStyle, sk_sp<SkTypeface>);   // 线宽
    void calculatePosition(TextDecoration, SkScalar ascent);  // 位置
    void calculateWaves(const TextStyle&, SkRect clip);       // 波浪线路径
    void calculateGaps(const TextLine::ClipContext&, ...);    // 间隙(kGaps模式)
};
```

## 依赖关系

```
src/ (内部实现)
  |-- include/ (公共接口: Paragraph, ParagraphBuilder, TextStyle 等)
  |-- Skia Core
  |   |-- SkCanvas, SkPaint, SkFont, SkTextBlob, SkTextBlobBuilder
  |   |-- SkPath, SkPicture, SkPictureRecorder
  |   |-- SkFontMetrics, SkFontMgr, SkTypeface
  |   |-- SkTArray, SkTHash, SkOnce, SkMutex
  |-- skshaper
  |   |-- SkShaper (文本整形主接口)
  |   |-- SkShaper::RunHandler (整形回调,OneLineShaper实现)
  |-- skunicode
  |   |-- SkUnicode (Unicode属性查询)
  |   |-- SkUnicode::CodeUnitFlags (代码单元标志)
  |   |-- SkBidiIterator (双向文本迭代)
  |   |-- SkBreakIterator (断行迭代)
```

## 设计模式分析

### 管线模式 (Pipeline Pattern)
`ParagraphImpl::layout()` 实现了一个5步排版管线,每一步都依赖前一步的输出。通过 `InternalState` 状态机确保步骤按序执行,并支持在文本微小变化时跳过已完成的步骤。

### 回调模式 (Callback Pattern)
- `OneLineShaper` 作为 `SkShaper::RunHandler` 接收整形结果
- `TextWrapper` 通过 `AddLineToParagraph` 回调将行信息传递给 `ParagraphImpl`
- `TextLine` 使用 `RunVisitor`, `RunStyleVisitor`, `ClustersVisitor` 遍历内部结构

### 享元模式 (Flyweight Pattern)
`Run` 中的 `GlyphData`(字形ID、位置、偏移、Cluster索引)使用 `std::shared_ptr` 共享,允许段落缓存命中时避免重复拷贝大量字形数据。

### 延迟计算 (Lazy Evaluation)
- UTF-16 映射表(`fUTF8IndexForUTF16Index`, `fUTF16IndexForUTF8Index`)仅在首次需要时通过 `SkOnce` 计算
- `TextLine` 的 `TextBlobRecord` 缓存在首次绘制时构建

## 数据流

```
ParagraphBuilderImpl::Build()
  |
  +-- 收集: fUtf8 (文本), fStyledBlocks (样式块), fPlaceholders (占位符)
  |
  +-- 构造 ParagraphImpl(text, style, blocks, placeholders, fonts, unicode)
  |
  v
ParagraphImpl::layout(width)
  |
  1. computeCodeUnitProperties()
  |   输入: fText, fUnicode
  |   输出: fCodeUnitProperties[] -- 每个代码单元的标志位
  |         fBidiRegions[] -- 双向文本区域
  |         fWords[] -- 词边界
  |
  2. applySpacingAndBuildClusterTable()
  |   输入: fRuns[], fCodeUnitProperties[]
  |   输出: fClusters[] -- 字符簇表
  |         应用 letterSpacing 和 wordSpacing
  |
  3. shapeTextIntoEndlessLine()
  |   输入: fText, fTextStyles[], fBidiRegions[], fUnicode
  |   过程: OneLineShaper 遍历 BiDi 区域 -> 遍历样式 -> 调用 SkShaper
  |   输出: fRuns[] -- 排版段数组(字形+位置+字体)
  |
  4. breakShapedTextIntoLines(maxWidth)
  |   输入: fClusters[], maxWidth, ellipsis
  |   过程: TextWrapper 逐词/逐簇前进, 检查宽度约束
  |   输出: fLines[] -- 文本行数组
  |
  5. formatLines(maxWidth)
  |   输入: fLines[], textAlign, maxWidth
  |   过程: 根据对齐方式调整每行偏移, 处理两端对齐
  |   输出: 每行的最终位置
  |
  v
ParagraphImpl::paint(canvas, x, y)
  |
  +-- 遍历 fLines[]
        +-- TextLine::paint(painter, x, y)
              +-- 绘制背景(paintBackground)
              +-- 绘制阴影(paintShadow)
              +-- 绘制文本(drawTextBlob)
              +-- 绘制装饰(Decorations::paint)
```

## 相关文档与参考

- **公共接口**: `modules/skparagraph/include/` - API 定义
- **SkShaper**: `modules/skshaper/include/SkShaper.h` - 文本整形接口
- **SkUnicode**: `modules/skunicode/include/SkUnicode.h` - Unicode 属性分析
- **测试代码**: `modules/skparagraph/tests/SkParagraphTest.cpp` - 详尽的功能测试
- **性能测试**: `modules/skparagraph/bench/ParagraphBench.cpp` - 排版性能基准
