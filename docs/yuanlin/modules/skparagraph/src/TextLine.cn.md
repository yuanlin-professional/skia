# TextLine

> 源文件: modules/skparagraph/src/TextLine.h, modules/skparagraph/src/TextLine.cpp

## 概述

`TextLine` 是 Skia 段落布局系统中的核心类,表示经过换行和布局后的单个文本行。该类负责管理行内的所有文本运行(Run)、字形簇(Cluster)、视觉顺序、文本测量、渲染绘制、命中测试以及文本选择框的计算。

作为段落渲染的基本单元,`TextLine` 连接了上层的段落布局逻辑和底层的文本绘制系统,处理复杂的双向文本(Bidi)重排、文本装饰、阴影效果、省略号截断、文本对齐和两端对齐等高级排版功能。

## 架构位置

`TextLine` 位于段落布局模块的核心实现层,是连接段落布局和文本绘制的关键组件:

```
skia/modules/skparagraph/
├── include/
│   ├── Paragraph.h              # 段落公共接口
│   └── ParagraphPainter.h       # 绘制抽象接口
└── src/
    ├── ParagraphImpl.h/.cpp     # 段落实现,管理多个TextLine
    ├── TextLine.h/.cpp          # 文本行实现
    ├── Run.h/.cpp               # 文本运行单元
    ├── TextWrapper.h/.cpp       # 文本换行器(生成TextLine)
    └── OneLineShaper.h/.cpp     # 单行文本整形器
```

**层次关系:**
- `ParagraphImpl` 管理多个 `TextLine` 对象
- `TextLine` 引用 `ParagraphImpl` 的 `Run` 和 `Cluster` 数据
- `TextWrapper` 负责创建和布局 `TextLine`
- `TextLine` 使用 `ParagraphPainter` 进行绘制

## 主要类与结构体

### TextLine
```cpp
class TextLine
```
文本行的核心类,表示段落中的一行文本。

**关键成员变量:**
- `fOwner`: 所属的 `ParagraphImpl` 指针
- `fBlockRange`: 样式块范围
- `fTextExcludingSpaces`: 不包含尾随空格的文本范围
- `fText`: 文本范围
- `fTextIncludingNewlines`: 包含换行符的文本范围
- `fClusterRange`: 字形簇范围
- `fGhostClusterRange`: 包含幽灵空格的字形簇范围
- `fRunsInVisualOrder`: 视觉顺序的运行索引数组
- `fAdvance`: 文本尺寸(宽度和高度)
- `fOffset`: 文本位置
- `fShift`: 对齐偏移(用于右对齐、居中对齐)
- `fWidthWithSpaces`: 包含空格的宽度
- `fEllipsis`: 省略号运行(如果行被截断)
- `fSizes`: 行度量(包含 strut)
- `fMaxRunMetrics`: 最大运行度量(不包含 strut)
- `fTextBlobCache`: 文本块缓存,用于优化绘制
- `fHasBackground/fHasShadows/fHasDecorations`: 快速标志

### ClipContext
```cpp
struct ClipContext
```
文本测量和裁剪的上下文信息:

**成员:**
- `run`: 指向 Run 的指针
- `pos`: 字形位置
- `size`: 字形数量
- `fTextShift`: 文本在运行内的偏移
- `clip`: 裁剪矩形
- `fExcludedTrailingSpaces`: 排除的尾随空格宽度
- `clippingNeeded`: 是否需要裁剪

### TextAdjustment
```cpp
enum TextAdjustment
```
文本调整模式,用于字形边界对齐:

- `GlyphCluster`: 字形簇对齐
- `GlyphemeCluster`: 字素簇对齐(基础字形+附加符号)
- `Grapheme`: 字位对齐
- `GraphemeGluster`: 字形簇和字位对齐的组合

### TextBlobRecord
```cpp
struct TextBlobRecord
```
缓存的文本块记录:

**成员:**
- `fBlob`: 文本块智能指针
- `fOffset`: 绘制偏移
- `fPaint`: 绘制样式
- `fBounds`: 边界框
- `fClippingNeeded`: 是否需要裁剪
- `fClipRect`: 裁剪矩形
- `fVisitor_Run/fVisitor_Pos`: 访问器字段

## 公共 API 函数

### 构造与查询
```cpp
TextLine(ParagraphImpl* owner, SkVector offset, SkVector advance,
         BlockRange blocks, TextRange textExcludingSpaces, TextRange text,
         TextRange textIncludingNewlines, ClusterRange clusters,
         ClusterRange clustersWithGhosts, SkScalar widthWithSpaces,
         InternalLineMetrics sizes)
```
构造文本行,初始化所有布局信息和视觉顺序。

```cpp
TextRange trimmedText() const
TextRange text() const
TextRange textWithNewlines() const
SkScalar width() const
SkScalar height() const
SkScalar spacesWidth() const
```
获取文本范围和尺寸信息。

### 格式化与对齐
```cpp
void format(TextAlign align, SkScalar maxWidth)
```
根据对齐方式格式化文本行,支持左对齐、右对齐、居中对齐和两端对齐。

```cpp
void createEllipsis(SkScalar maxWidth, const SkString& ellipsis, bool ltr)
```
创建省略号并截断行尾文本,使其适配最大宽度。

### 绘制与缓存
```cpp
void paint(ParagraphPainter* painter, SkScalar x, SkScalar y)
```
绘制文本行,包括背景、阴影、文本和装饰线。绘制顺序确保视觉效果正确。

```cpp
void ensureTextBlobCachePopulated()
```
填充文本块缓存,优化重复绘制性能。

### 迭代器接口
```cpp
void iterateThroughVisualRuns(bool includingGhostSpaces, const RunVisitor& visitor) const
```
按视觉顺序遍历文本运行。

```cpp
void iterateThroughClustersInGlyphsOrder(bool reverse, bool includeGhosts,
                                         const ClustersVisitor& visitor) const
```
按字形顺序遍历字形簇。

```cpp
SkScalar iterateThroughSingleRunByStyles(TextAdjustment textAdjustment,
                                         const Run* run, SkScalar runOffset,
                                         TextRange textRange, StyleType styleType,
                                         const RunStyleVisitor& visitor) const
```
在单个运行内按样式遍历文本段。

### 文本测量与命中测试
```cpp
ClipContext measureTextInsideOneRun(TextRange textRange, const Run* run,
                                    SkScalar runOffsetInLine, SkScalar textOffsetInRunInLine,
                                    bool includeGhostSpaces, TextAdjustment textAdjustment) const
```
测量运行内指定文本范围的尺寸和裁剪信息。

```cpp
PositionWithAffinity getGlyphPositionAtCoordinate(SkScalar dx)
```
根据 x 坐标获取文本光标位置,支持双向文本。

```cpp
void getRectsForRange(TextRange textRange, RectHeightStyle rectHeightStyle,
                      RectWidthStyle rectWidthStyle, std::vector<TextBox>& boxes) const
```
获取指定文本范围的选择框矩形,支持多种高度和宽度样式。

```cpp
void getRectsForPlaceholders(std::vector<TextBox>& boxes)
```
获取行内占位符的边界框。

### 度量信息
```cpp
LineMetrics getMetrics() const
```
获取行的完整度量信息,包括基线、高度、宽度和样式度量。

```cpp
SkScalar alphabeticBaseline() const
SkScalar ideographicBaseline() const
SkScalar baseline() const
```
获取不同类型的基线位置。

## 内部实现细节

### Bidi 视觉重排
构造函数中执行双向文本的视觉重排:

```cpp
fOwner->getUnicode()->reorderVisual(runLevels.data(), numRuns, logicalOrder.data());
```

关键逻辑:
- 收集每个运行的 Bidi 级别
- 调用 Unicode 库的 `reorderVisual` 进行重排
- 占位符保持原始顺序不参与 Bidi 重排
- 将逻辑顺序映射到 `fRunsInVisualOrder`

### 两端对齐实现
`justify()` 方法实现复杂的两端对齐逻辑:

```cpp
void TextLine::justify(SkScalar maxWidth)
```

**算法步骤:**
1. 统计空白间隙数量(单词之间的空格、表意文字前后)
2. 计算每个间隙需要增加的宽度: `step = (maxWidth - textLen + whitespaceLen) / whitespacePatches`
3. 遍历所有字形簇,在空白位置累积偏移
4. 调用 `shiftCluster()` 将偏移存储到 `run.fJustificationShifts`
5. 处理幽灵空格(尾随空格)的特殊对齐

**特殊处理:**
- 行首空格不计入间隙
- 行尾空格不计入间隙
- 表意文字(中日韩文字)前后各计一个间隙
- RTL 文本的特殊处理

### 省略号整形
`shapeEllipsis()` 使用 HarfBuzz 整形器动态生成省略号:

**实现流程:**
1. 使用 `ShapeHandler` 作为整形回调
2. 尝试当前运行的字体
3. 遍历所有配置的字体族
4. 启用字体回退机制查找合适的字体
5. 返回整形后的省略号 Run

### 文本块缓存优化
`ensureTextBlobCachePopulated()` 构建文本块缓存:

**优化策略:**
- 快速路径: 单一样式块、单一运行、无省略号时直接构建一个文本块
- 通用路径: 遍历所有运行和样式,为每个样式段构建独立的文本块
- 缓存后重复绘制无需重新构建

### 文本测量核心算法
`measureTextInsideOneRun()` 是测量的核心:

**处理流程:**
1. 查找文本范围对应的字形簇边界
2. 根据 `TextAdjustment` 调整到字位边界
3. 计算字形的宽度和高度
4. 处理字形簇边界不对齐的情况,计算左右修正量
5. 应用两端对齐的偏移
6. 处理尾随空格的特殊裁剪逻辑

### 命中测试算法
`getGlyphPositionAtCoordinate()` 实现精确的光标定位:

**算法步骤:**
1. 遍历视觉运行找到包含坐标的运行
2. 在运行内线性搜索字形位置(TODO: 改为二分搜索)
3. 找到最接近的字形边界
4. 计算字形中心,判断光标在左侧还是右侧
5. 处理多字位情况,按比例计算字位内的位置
6. 返回 UTF-16 索引和亲和性(上游/下游)

### 选择框计算
`getRectsForRange()` 生成文本选择框:

**复杂逻辑:**
- 支持多种高度样式(最大高度、紧凑高度、Strut、行距分布)
- 处理尾随空格的特殊布局
- 尝试合并相邻的相同属性矩形
- RTL 文本的特殊处理
- 两端对齐时尾随空格的位置调整

## 依赖关系

### 核心依赖
- **ParagraphImpl**: 所属段落,提供全局数据访问
- **Run**: 文本运行单元,存储整形后的字形数据
- **Cluster**: 字形簇,连接文本和字形
- **ParagraphPainter**: 绘制抽象接口
- **SkTextBlob**: Skia 文本块,优化的绘制单元
- **SkShaper**: HarfBuzz 整形器,用于省略号整形
- **SkUnicode**: Unicode 处理,Bidi 重排

### 外部调用
- `ParagraphImpl::paint()` 调用 `TextLine::paint()` 绘制每一行
- `ParagraphImpl::getRectsForRange()` 调用 `TextLine::getRectsForRange()` 计算选择框
- `ParagraphImpl::getGlyphPositionAtCoordinate()` 调用 `TextLine::getGlyphPositionAtCoordinate()` 命中测试

### 依赖图
```
ParagraphImpl
    ↓ (owns)
TextLine
    ↓ (uses)
Run + Cluster
    ↓ (uses)
SkTextBlob + SkShaper
```

## 设计模式与设计决策

### 迭代器模式
提供多种迭代器接口遍历文本行的不同维度:
- **视觉运行迭代器**: 按屏幕显示顺序遍历
- **字形簇迭代器**: 按字形逻辑顺序遍历
- **样式段迭代器**: 在运行内按样式分段遍历

使用函数对象(lambda)作为访问器,灵活高效。

### 惰性计算
文本块缓存采用惰性构建策略:
- 首次绘制时构建缓存
- 使用 `fTextBlobCachePopulated` 标志避免重复构建
- 布局改变时缓存失效,需要重建

### 分离关注点
绘制顺序精心设计,确保视觉正确:
1. 背景(最底层)
2. 阴影(文本下方)
3. 文本主体
4. 装饰线(最上层)

每种绘制元素独立遍历和处理。

### 优化快速路径
多处使用快速路径优化常见场景:
- 单样式单运行的文本块构建
- 空行的特殊处理
- 标志位快速跳过不需要的绘制阶段

### 坐标系统设计
精心设计的坐标系统:
- **行内坐标**: 相对于行起点的偏移
- **段落坐标**: 相对于段落起点的偏移(通过 `fOffset`)
- **画布坐标**: 最终绘制时的绝对坐标

转换关系清晰,易于调试。

## 性能考量

### 缓存策略
- **文本块缓存**: 避免每次绘制都重新构建 `SkTextBlob`
- **快速标志**: `fHasBackground/fHasShadows/fHasDecorations` 跳过不必要的遍历
- **STArray 优化**: `fRunsInVisualOrder` 使用小数组优化,避免常见情况下的堆分配

### 内存布局
- 使用 `skia_private::STArray<1, size_t>` 为单运行行优化,减少内存分配
- 文本块缓存使用 `std::vector` 动态增长
- 两端对齐偏移存储在 Run 对象中,避免重复计算

### 绘制优化
- 批量绘制文本块,减少绘制调用
- 仅在必要时使用裁剪(通过 `clippingNeeded` 标志)
- 背景、阴影、装饰各自独立遍历,避免无效计算

### 算法复杂度
- **命中测试**: 当前为线性搜索 O(n),代码注释提到应改为二分搜索 O(log n)
- **视觉遍历**: O(runs * styles),对于大多数文档都是小常数
- **两端对齐**: O(clusters),线性遍历一次

### Flutter 兼容性处理
代码中多处注释标记了为 Flutter 兼容性添加的特殊逻辑:
- `littleRound()`: 四舍五入到小数点后两位,匹配 Flutter 测试
- `compareRound()`: 浮点数比较的容差处理
- 尾随空格的特殊处理
- 最后一行的硬换行标记

这些逻辑计划未来移除,但目前保留以确保兼容性。

## 相关文件

### 接口与定义
- `modules/skparagraph/include/Paragraph.h`: 段落公共接口
- `modules/skparagraph/include/TextStyle.h`: 文本样式定义
- `modules/skparagraph/include/Metrics.h`: 度量信息定义

### 协作类
- `modules/skparagraph/src/ParagraphImpl.h/.cpp`: 段落实现,所有者
- `modules/skparagraph/src/Run.h/.cpp`: 文本运行单元
- `modules/skparagraph/src/TextWrapper.h/.cpp`: 文本换行器,创建 TextLine
- `modules/skparagraph/src/ParagraphPainterImpl.h/.cpp`: 绘制实现
- `modules/skparagraph/src/Decorations.h/.cpp`: 装饰线绘制

### 底层依赖
- `include/core/SkTextBlob.h`: 文本块
- `modules/skshaper/include/SkShaper.h`: 文本整形器
- `modules/skunicode/include/SkUnicode.h`: Unicode 处理
