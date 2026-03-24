# skparagraph - 段落文本排版引擎

## 概述

skparagraph 是 Skia 图形库中的高级文本排版模块,提供了完整的段落级文本布局(layout)和渲染(paint)能力。该模块最初为 Flutter 框架设计,实现了类似于 CSS 文本排版规范的段落排版功能,支持多样式文本、双向文本(BiDi)、字体回退(font fallback)、省略号截断、占位符(placeholder)以及丰富的文本装饰效果。

该模块构建于 Skia 的核心字体和画布系统之上,同时依赖 `skshaper` 模块进行文本整形(text shaping)和 `skunicode` 模块进行 Unicode 属性分析。skparagraph 的设计采用了构建器模式(Builder Pattern),用户通过 `ParagraphBuilder` 逐步添加文本和样式,然后构建出 `Paragraph` 对象进行布局和绘制。

skparagraph 提供了丰富的查询 API,支持根据文本索引获取字形位置、根据坐标查询字符位置、获取选区矩形等功能,这些对于文本编辑器的实现至关重要。模块还包含段落缓存机制(`ParagraphCache`),可在文本微小变化时复用之前的排版结果,大幅提升文本编辑场景下的性能。

整个模块位于 `skia::textlayout` 命名空间下,所有类型定义和接口设计都充分考虑了 Flutter/Dart 的使用场景,因此多处类型命名(如 `DartTypes.h`)直接反映了与 Dart 侧的对应关系。

## 架构图

```
+------------------------------------------------------------------+
|                       ParagraphBuilder                           |
|  (pushStyle / addText / addPlaceholder / Build)                  |
+---------------------------+--------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                         Paragraph                                |
|  (layout / paint / getRectsForRange / getGlyphPositionAt...)     |
+----------+-------------------+-------------------+---------------+
           |                   |                   |
           v                   v                   v
+----------------+   +------------------+   +------------------+
|  ParagraphImpl |   |  ParagraphCache  |   |  FontCollection  |
|  (核心实现)     |   |  (排版结果缓存)   |   |  (字体管理)       |
+-------+--------+   +------------------+   +------------------+
        |
        +---+--------+--------+--------+
        |   |        |        |        |
        v   v        v        v        v
   +------+ +------+ +------+ +------+ +----------+
   | Run  | |Cluster| |TextLine| |TextWrapper| |OneLineShaper|
   |(排版段)|(字符簇) |(文本行) |(换行器)    |(整形器)       |
   +------+ +------+ +------+ +----------+ +----------+
                                                |
                                                v
                                    +---------------------+
                                    |  SkShaper (skshaper)|
                                    |  SkUnicode (skunicode)|
                                    +---------------------+
```

## 目录结构

```
modules/skparagraph/
|-- BUILD.bazel                  # Bazel 构建配置
|-- BUILD.gn                     # GN 构建配置
|-- skparagraph.gni              # GNI 源文件清单(自动生成)
|-- test.html                    # WebAssembly 测试页面
|-- include/                     # 公共头文件(API 接口)
|   |-- DartTypes.h              # Dart/Flutter 兼容类型定义
|   |-- FontArguments.h          # 字体参数封装
|   |-- FontCollection.h         # 字体集合管理器
|   |-- Metrics.h                # 行度量与样式度量
|   |-- Paragraph.h              # 段落抽象基类
|   |-- ParagraphBuilder.h       # 段落构建器接口
|   |-- ParagraphCache.h         # 段落缓存
|   |-- ParagraphPainter.h       # 段落绘制器抽象
|   |-- ParagraphStyle.h         # 段落样式与支柱样式
|   |-- TextShadow.h             # 文本阴影
|   |-- TextStyle.h              # 文本样式(字体/颜色/装饰等)
|   |-- TypefaceFontProvider.h   # 自定义字体提供器
|-- src/                         # 内部实现
|   |-- Decorations.cpp/h        # 文本装饰(下划线/删除线等)
|   |-- FontArguments.cpp        # 字体参数实现
|   |-- FontCollection.cpp       # 字体集合实现
|   |-- Iterators.h              # 语言迭代器
|   |-- OneLineShaper.cpp/h      # 单行文本整形器
|   |-- ParagraphBuilderImpl.cpp/h  # 段落构建器实现
|   |-- ParagraphCache.cpp       # 段落缓存实现
|   |-- ParagraphImpl.cpp/h      # 段落核心实现
|   |-- ParagraphPainterImpl.cpp/h  # Canvas 绘制器实现
|   |-- ParagraphStyle.cpp       # 段落样式实现
|   |-- Run.cpp/h                # 排版段(Run)与字符簇(Cluster)
|   |-- TextLine.cpp/h           # 文本行
|   |-- TextShadow.cpp           # 文本阴影实现
|   |-- TextStyle.cpp            # 文本样式实现
|   |-- TextWrapper.cpp/h        # 文本换行器
|   |-- TypefaceFontProvider.cpp # 字体提供器实现
|-- bench/                       # 性能基准测试
|   |-- ParagraphBench.cpp       # 段落排版性能测试
|-- gm/                          # Golden Master 测试
|   |-- simple_gm.cpp            # 简单渲染测试
|-- slides/                      # 演示幻灯片
|   |-- ParagraphSlide.cpp       # 段落功能演示
|-- tests/                       # 单元测试
|   |-- SkParagraphTest.cpp      # 段落核心测试
|   |-- SkShaperJSONWriter.cpp/h # Shaper JSON 输出工具
|   |-- SkShaperJSONWriterTest.cpp # JSON 输出测试
|-- utils/                       # 工具类
    |-- TestFontCollection.cpp/h # 测试用字体集合
```

## 关键类与函数

### 公共接口类

| 类名 | 文件 | 职责 |
|------|------|------|
| `Paragraph` | `include/Paragraph.h` | 段落抽象基类,定义 layout/paint/查询等核心接口 |
| `ParagraphBuilder` | `include/ParagraphBuilder.h` | 段落构建器,通过 pushStyle/addText/Build 构建段落 |
| `ParagraphStyle` | `include/ParagraphStyle.h` | 段落级样式:对齐、方向、最大行数、省略号等 |
| `StrutStyle` | `include/ParagraphStyle.h` | 支柱样式:控制行高的全局基线参考 |
| `TextStyle` | `include/TextStyle.h` | 文本样式:字体、颜色、装饰、阴影、间距等 |
| `FontCollection` | `include/FontCollection.h` | 字体集合管理,支持多级字体管理器和字体回退 |
| `ParagraphPainter` | `include/ParagraphPainter.h` | 抽象绘制器,支持自定义绘制后端 |
| `ParagraphCache` | `include/ParagraphCache.h` | 段落缓存,加速文本编辑场景 |
| `TypefaceFontProvider` | `include/TypefaceFontProvider.h` | 自定义字体管理器(SkFontMgr 实现) |
| `FontArguments` | `include/FontArguments.h` | 可变字体参数封装(variation axes, palette) |
| `TextShadow` | `include/TextShadow.h` | 文本阴影配置(颜色、偏移、模糊半径) |

### 内部实现类

| 类名 | 文件 | 职责 |
|------|------|------|
| `ParagraphImpl` | `src/ParagraphImpl.h` | Paragraph 的完整实现,包含排版管线全流程 |
| `ParagraphBuilderImpl` | `src/ParagraphBuilderImpl.h` | ParagraphBuilder 的实现,管理样式栈和文本 |
| `Run` | `src/Run.h` | 排版段:相同属性的连续字形序列 |
| `Cluster` | `src/Run.h` | 字符簇:一个或多个字形组成的最小排版单元 |
| `TextLine` | `src/TextLine.h` | 文本行:包含多个 Run 和布局信息 |
| `TextWrapper` | `src/TextWrapper.h` | 换行算法实现,处理软换行和硬换行 |
| `OneLineShaper` | `src/OneLineShaper.h` | 单行整形器,协调 SkShaper 进行文本整形 |
| `Decorations` | `src/Decorations.h` | 文本装饰绘制(下划线、上划线、删除线) |
| `InternalLineMetrics` | `src/Run.h` | 行内度量:上升(ascent)、下降(descent)、行距(leading) |
| `CanvasParagraphPainter` | `src/ParagraphPainterImpl.h` | 基于 SkCanvas 的绘制器实现 |
| `LangIterator` | `src/Iterators.h` | 语言迭代器,为 SkShaper 提供语言信息 |

### 核心排版流程函数

```cpp
// ParagraphImpl 中的排版管线:
void ParagraphImpl::layout(SkScalar width);
  |-- computeCodeUnitProperties()     // 步骤1: 计算 Unicode 属性(换行/空格/字素)
  |-- applySpacingAndBuildClusterTable() // 步骤2: 应用字间距并构建 Cluster 表
  |-- shapeTextIntoEndlessLine()      // 步骤3: 将文本整形为无限长单行
  |-- breakShapedTextIntoLines()      // 步骤4: 将整形后的文本折行
  |-- formatLines()                   // 步骤5: 对齐格式化各行
```

### 关键枚举类型

- `TextAlign`: 文本对齐(左/右/居中/两端对齐/起始/结束)
- `TextDirection`: 文本方向(LTR/RTL)
- `TextDecoration`: 装饰类型(无/下划线/上划线/删除线)
- `RectHeightStyle`: 选区矩形高度模式(紧凑/最大/含行距)
- `RectWidthStyle`: 选区矩形宽度模式(紧凑/最大)
- `PlaceholderAlignment`: 占位符对齐方式(基线/上/下/顶/底/中)
- `TextBaseline`: 基线类型(字母基线/表意基线)
- `InternalState`: 内部状态机(kUnknown -> kIndexed -> kShaped -> kLineBroken -> kFormatted -> kDrawn)

## 依赖关系

```
skparagraph
  |-- Skia Core (SkCanvas, SkFont, SkPaint, SkTextBlob, SkPath, SkPicture)
  |-- skshaper (SkShaper: 文本整形接口)
  |   |-- SkShaper::RunHandler (整形回调)
  |   |-- SkShaper::FontRunIterator (字体迭代器)
  |   |-- SkShaper::BiDiRunIterator (双向文本迭代器)
  |   |-- SkShaper::ScriptRunIterator (脚本迭代器)
  |   |-- SkShaper::LanguageRunIterator (语言迭代器)
  |-- skunicode (SkUnicode: Unicode 属性查询)
  |   |-- 字符分类 (空格/控制字符/表意文字/Emoji)
  |   |-- 断行分析 (软换行/硬换行)
  |   |-- 字素簇分割 (grapheme cluster)
  |   |-- 双向文本分析 (BiDi regions)
  |   |-- 词边界检测
  |-- SkFontMgr (字体管理器)
  |-- HarfBuzz (通过 skshaper 间接依赖,可选)
  |-- ICU (通过 skunicode 间接依赖,可选)
```

## 设计模式分析

### 1. 构建器模式 (Builder Pattern)
`ParagraphBuilder` 是典型的构建器模式实现。用户通过一系列方法调用构建复杂的段落对象:
```cpp
auto builder = ParagraphBuilder::make(style, fontCollection, unicode);
builder->pushStyle(boldStyle);
builder->addText("Bold text ");
builder->pop();
builder->addText("Normal text");
auto paragraph = builder->Build();
```

### 2. 抽象工厂模式 (Abstract Factory)
`ParagraphPainter` 定义了抽象绘制接口,`CanvasParagraphPainter` 提供了基于 SkCanvas 的实现。这允许客户端提供自定义绘制后端,如 Flutter 的自定义渲染器。

### 3. 访问者模式 (Visitor Pattern)
`Paragraph::visit()` 和 `Paragraph::extendedVisit()` 使用访问者模式遍历排版结果,允许外部代码访问每个字形的详细信息而无需暴露内部数据结构。

### 4. 样式栈模式 (Style Stack)
`ParagraphBuilder` 使用样式栈管理嵌套的文本样式。`pushStyle()` 压栈,`pop()` 弹栈,`addText()` 使用栈顶样式。

### 5. 缓存模式 (Cache Pattern)
`ParagraphCache` 实现了排版结果缓存,以文本内容和样式为键,在文本编辑场景中避免重复排版。

### 6. 状态机模式 (State Machine)
`ParagraphImpl` 使用 `InternalState` 枚举跟踪排版管线进度:
`kUnknown -> kIndexed -> kShaped -> kLineBroken -> kFormatted -> kDrawn`

## 数据流

```
输入文本 + 样式
       |
       v
[ParagraphBuilder::addText/pushStyle]
       |
       v
构建 Block 数组 (TextRange + TextStyle)
       |
       v
[ParagraphImpl::layout(width)]
       |
       +-- [computeCodeUnitProperties()]
       |       使用 SkUnicode 分析每个代码单元的属性
       |       (空格/换行/字素/表意文字/Emoji等)
       |
       +-- [applySpacingAndBuildClusterTable()]
       |       将字母间距和词间距应用到字符簇
       |
       +-- [shapeTextIntoEndlessLine()]
       |       OneLineShaper 调用 SkShaper 进行文本整形
       |       -> 生成 Run 数组 (字形ID + 位置 + 字体)
       |       -> 构建 Cluster 表 (将字形映射回文本)
       |
       +-- [breakShapedTextIntoLines(maxWidth)]
       |       TextWrapper 根据宽度约束和换行规则拆分为多行
       |       -> 生成 TextLine 数组
       |       -> 处理省略号截断
       |
       +-- [formatLines(maxWidth)]
               根据 TextAlign 调整每行位置
               -> 处理两端对齐的词间距分配
       |
       v
排版完成 -> paint() 绘制到 SkCanvas
       |
       v
查询 API: getRectsForRange / getGlyphPositionAtCoordinate / getWordBoundary 等
```

## 相关文档与参考

- **skshaper 模块**: `modules/skshaper/` - 底层文本整形引擎
- **skunicode 模块**: `modules/skunicode/` - Unicode 属性分析
- **Skia 字体系统**: `include/core/SkFont.h`, `include/core/SkFontMgr.h`
- **Flutter 文本排版**: skparagraph 是 Flutter 在桌面和 Web 平台的文本排版后端
- **CSS 文本规范**: 模块的排版行为参考了 CSS Text Module Level 3 和 CSS Inline Layout Module
- **Unicode 双向算法**: UAX #9 (Unicode Bidirectional Algorithm)
- **Unicode 换行算法**: UAX #14 (Unicode Line Breaking Algorithm)
- **Unicode 字素簇**: UAX #29 (Unicode Text Segmentation)
