# Run

> 源文件: modules/skparagraph/src/Run.h, modules/skparagraph/src/Run.cpp

## 概述

`Run` 和 `Cluster` 是 Skia 段落布局系统中的基础数据结构,表示经过文本整形(text shaping)后的基本单元。`Run` 代表一段具有相同属性(字体、方向、脚本等)的连续整形文本,包含字形(glyph)、位置、偏移等信息;`Cluster` 则表示一个或多个字形对应的文本字符簇,是文本和字形之间的桥接单元。

此外,该文件还定义了 `InternalLineMetrics` 类,用于管理行内的度量信息,包括上升高度、下降高度、行距等,支持 Strut 样式和多种基线对齐方式。

## 架构位置

`Run` 和 `Cluster` 位于段落布局系统的底层,是整形后文本的核心表示:

```
skia/modules/skparagraph/
├── include/
│   └── Paragraph.h
└── src/
    ├── ParagraphImpl.h/.cpp     # 段落实现,管理Run和Cluster数组
    ├── Run.h/.cpp               # Run和Cluster定义
    ├── OneLineShaper.h/.cpp     # 文本整形器,生成Run
    ├── TextLine.h/.cpp          # 文本行,引用Run和Cluster
    └── TextWrapper.h/.cpp       # 文本换行器,基于Cluster进行断行
```

**数据流:**
1. `OneLineShaper` 使用 HarfBuzz 整形器生成 `Run` 对象
2. `ParagraphImpl` 根据 `Run` 信息创建 `Cluster` 对象
3. `TextWrapper` 基于 `Cluster` 的断行属性进行换行
4. `TextLine` 引用 `Run` 和 `Cluster` 进行绘制和测量

## 主要类与结构体

### Run
```cpp
class Run
```
表示经过整形的连续文本运行单元,存储字形、位置和度量信息。

**核心成员:**
- `fOwner`: 所属的 `ParagraphImpl` 指针
- `fTextRange`: 文本范围(UTF-8索引)
- `fClusterRange`: 对应的字形簇范围
- `fFont`: 字体对象
- `fGlyphs`: 字形ID数组
- `fPositions`: 字形位置数组
- `fOffsets`: 字形偏移数组
- `fClusterIndexes`: 字形到文本索引的映射
- `fAdvance`: 运行的前进宽度和高度
- `fOffset`: 运行的偏移位置
- `fFontMetrics`: 字体度量信息
- `fBidiLevel`: Bidi级别(决定文本方向)
- `fScript`: 脚本标签(用于识别草书脚本)
- `fJustificationShifts`: 两端对齐的偏移数组
- `fHeightMultiplier`: 行高倍数
- `fBaselineShift`: 基线偏移
- `fPlaceholderIndex`: 占位符索引(如果是占位符)
- `fEllipsis`: 是否为省略号

**GlyphData 共享:**
```cpp
struct GlyphData {
    skia_private::STArray<64, SkGlyphID, true> glyphs;
    skia_private::STArray<64, SkPoint, true> positions;
    skia_private::STArray<64, SkPoint, true> offsets;
    skia_private::STArray<64, uint32_t, true> clusterIndexes;
};
std::shared_ptr<GlyphData> fGlyphData;
```
字形数据通过共享指针在不同段落的 Run 副本之间共享,优化内存使用。

### Cluster
```cpp
class Cluster
```
字形簇,连接文本字符和字形的桥接单元。

**核心成员:**
- `fOwner`: 所属的 `ParagraphImpl` 指针
- `fRunIndex`: 所属的运行索引
- `fTextRange`: 对应的文本范围
- `fGraphemeRange`: 对应的字位范围
- `fStart/fEnd`: 在 Run 中的字形位置范围
- `fWidth/fHeight`: 簇的宽度和高度
- `fHalfLetterSpacing`: 半字符间距(用于文本选择)
- `fIsWhiteSpaceBreak`: 是否为空白断行点
- `fIsIntraWordBreak`: 是否为单词内断行点
- `fIsHardBreak`: 是否为硬换行
- `fIsIdeographic`: 是否为表意文字

**BreakType 枚举:**
```cpp
enum BreakType {
    None,
    GraphemeBreak,   // 字位断点
    SoftLineBreak,   // 软换行断点
    HardLineBreak,   // 硬换行断点
};
```

### InternalLineMetrics
```cpp
class InternalLineMetrics
```
行内度量信息管理类。

**核心成员:**
- `fAscent/fDescent/fLeading`: 上升高度、下降高度、行距
- `fRawAscent/fRawDescent/fRawLeading`: 原始度量(不考虑 Strut)
- `fForceStrut`: 是否强制使用 Strut 样式

### 类型定义
```cpp
typedef size_t RunIndex;
typedef size_t ClusterIndex;
typedef SkRange<size_t> ClusterRange;
typedef size_t GraphemeIndex;
typedef SkRange<GraphemeIndex> GraphemeRange;
typedef size_t GlyphIndex;
typedef SkRange<GlyphIndex> GlyphRange;
```

## 公共 API 函数

### Run 构造与初始化
```cpp
Run(ParagraphImpl* owner, const SkShaper::RunHandler::RunInfo& info,
    size_t firstChar, SkScalar heightMultiplier, bool useHalfLeading,
    SkScalar baselineShift, size_t index, SkScalar shiftX)
```
从 HarfBuzz 整形结果创建 Run 对象。

```cpp
SkShaper::RunHandler::Buffer newRunBuffer()
```
返回用于接收整形结果的缓冲区。

### Run 查询接口
```cpp
bool leftToRight() const
```
判断文本方向,基于 Bidi 级别(偶数为 LTR,奇数为 RTL)。

```cpp
SkScalar positionX(size_t pos) const
```
获取指定字形位置的 X 坐标,包含两端对齐的偏移。

```cpp
SkScalar calculateWidth(size_t start, size_t end, bool clip) const
```
计算字形范围的宽度。

```cpp
SkScalar calculateHeight(LineMetricStyle ascentStyle, LineMetricStyle descentStyle) const
```
根据度量风格计算高度。

```cpp
bool isCursiveScript() const
```
判断是否为草书脚本(阿拉伯语、蒙古语等),影响字符间距的应用。

```cpp
bool isResolved() const
```
判断 Run 是否成功整形(所有字形ID非零)。

### Run 文本操作
```cpp
std::tuple<bool, ClusterIndex, ClusterIndex> findLimitingClusters(TextRange text) const
std::tuple<bool, TextIndex, TextIndex> findLimitingGlyphClusters(TextRange text) const
std::tuple<bool, TextIndex, TextIndex> findLimitingGraphemes(TextRange text) const
```
查找文本范围对应的簇边界、字形簇边界和字位边界。

```cpp
void iterateThroughClustersInTextOrder(Visitor visitor)
void iterateThroughClusters(const ClusterVisitor& visitor)
```
遍历 Run 内的字形簇。

### Run 布局调整
```cpp
void addSpacesAtTheEnd(SkScalar space, Cluster* cluster)
```
在运行末尾添加空格宽度。

```cpp
SkScalar addLetterSpacesEvenly(SkScalar space)
SkScalar addLetterSpacesEvenly(SkScalar space, Cluster* cluster)
```
均匀添加字符间距,草书脚本不应用。

```cpp
void shift(const Cluster* cluster, SkScalar offset)
void extend(const Cluster* cluster, SkScalar offset)
```
移动或扩展簇内的字形位置。

```cpp
void updateMetrics(InternalLineMetrics* endlineMetrics)
```
更新占位符的度量信息,根据对齐方式调整上升和下降高度。

### Run 绘制
```cpp
void copyTo(SkTextBlobBuilder& builder, size_t pos, size_t size) const
```
将字形范围复制到文本块构建器,应用两端对齐的偏移和字形偏移。

### Cluster 查询
```cpp
bool isWhitespaceBreak() const
bool isHardBreak() const
bool isSoftBreak() const
bool isGraphemeBreak() const
bool canBreakLineAfter() const
```
查询簇的断行属性。

```cpp
SkScalar sizeToChar(TextIndex ch) const
SkScalar sizeFromChar(TextIndex ch) const
```
计算簇内到指定字符或从指定字符的宽度,按比例估算。

```cpp
SkScalar trimmedWidth(size_t pos) const
```
计算簇内到指定字形位置的修剪宽度。

```cpp
Run& run() const
SkFont font() const
```
获取簇所属的 Run 和字体。

### InternalLineMetrics 操作
```cpp
void add(Run* run)
void add(InternalLineMetrics other)
```
累积运行或其他度量信息,更新最大/最小值。

```cpp
void updateLineMetrics(InternalLineMetrics& metrics)
```
根据 Strut 设置更新行度量。

```cpp
SkScalar runTop(const Run* run, LineMetricStyle ascentStyle) const
```
计算运行在行内的顶部位置。

```cpp
SkScalar alphabeticBaseline() const
SkScalar ideographicBaseline() const
SkScalar baseline() const
SkScalar height() const
```
获取不同类型的基线和高度。

## 内部实现细节

### Run 度量计算
`calculateMetrics()` 根据行高倍数和半行距设置计算修正后的上升和下降高度:

```cpp
void Run::calculateMetrics() {
    fCorrectAscent = fFontMetrics.fAscent - fFontMetrics.fLeading * 0.5;
    fCorrectDescent = fFontMetrics.fDescent + fFontMetrics.fLeading * 0.5;
    fCorrectLeading = 0;

    if (SkScalarNearlyZero(fHeightMultiplier)) {
        return;
    }

    const auto runHeight = fHeightMultiplier * fFont.getSize();
    const auto fontIntrinsicHeight = fCorrectDescent - fCorrectAscent;

    if (fUseHalfLeading) {
        // 半行距模式: 额外的空间均分到上下
        const auto extraLeading = (runHeight - fontIntrinsicHeight) / 2;
        fCorrectAscent -= extraLeading;
        fCorrectDescent += extraLeading;
    } else {
        // 倍数模式: 按比例缩放
        const auto multiplier = runHeight / fontIntrinsicHeight;
        fCorrectAscent *= multiplier;
        fCorrectDescent *= multiplier;
    }

    // 应用基线偏移
    fCorrectAscent += fBaselineShift;
    fCorrectDescent += fBaselineShift;
}
```

**两种行高模式:**
- **半行距模式**: 额外空间均分到上下,保持字体原始比例
- **倍数模式**: 按比例缩放上升和下降,可能改变字体视觉比例

### 字形数据共享机制
使用 `std::shared_ptr<GlyphData>` 实现字形数据共享:

```cpp
fGlyphData(std::make_shared<GlyphData>())
fGlyphs(fGlyphData->glyphs)
fPositions(fGlyphData->positions)
```

**优势:**
- 段落缓存可以复制 Run 而不复制字形数据
- 多个段落副本共享相同的整形结果
- 减少内存占用,提升缓存效率

**注意:** 字形数据是只读的,布局相关的修改(如两端对齐偏移)存储在独立的 `fJustificationShifts` 中。

### 草书脚本识别
`isCursiveScript()` 识别连写脚本,这些脚本不应用字符间距:

```cpp
bool Run::isCursiveScript() const {
    switch (this->fScript) {
        case SkSetFourByteTag('A', 'r', 'a', 'b'): // ARABIC
        case SkSetFourByteTag('R', 'o', 'h', 'g'): // HANIFI_ROHINGYA
        case SkSetFourByteTag('M', 'a', 'n', 'd'): // MANDAIC
        case SkSetFourByteTag('M', 'o', 'n', 'g'): // MONGOLIAN
        case SkSetFourByteTag('N', 'k', 'o', 'o'): // NKO
        case SkSetFourByteTag('P', 'h', 'a', 'g'): // PHAGS_PA
        case SkSetFourByteTag('S', 'y', 'r', 'c'): // SYRIAC
        return true;
    }
    return false;
}
```

### 字符间距应用
`addLetterSpacesEvenly()` 实现字符间距:

```cpp
SkScalar Run::addLetterSpacesEvenly(SkScalar space, Cluster* cluster) {
    if (this->isCursiveScript()) {
        return 0.0;  // 草书脚本不应用字符间距
    }

    SkScalar shift = 0;
    for (size_t i = cluster->startPos(); i < cluster->endPos(); ++i) {
        fPositions[i].fX += shift;
        shift += space;
    }
    fAdvance.fX += shift;
    cluster->space(shift);
    cluster->setHalfLetterSpacing(space / 2);

    return shift;
}
```

**实现要点:**
- 每个字形后添加固定间距
- 累积偏移应用到后续字形
- 更新运行和簇的宽度
- 记录半间距用于文本选择框计算

### 占位符度量更新
`updateMetrics()` 根据占位符对齐方式调整度量:

```cpp
void Run::updateMetrics(InternalLineMetrics* endlineMetrics) {
    auto placeholderStyle = this->placeholderStyle();
    SkScalar baselineAdjustment = 0;

    switch (placeholderStyle->fBaseline) {
        case TextBaseline::kAlphabetic:
            break;
        case TextBaseline::kIdeographic:
            baselineAdjustment = endlineMetrics->deltaBaselines() / 2;
            break;
    }

    auto height = placeholderStyle->fHeight;
    auto offset = placeholderStyle->fBaselineOffset;

    switch (placeholderStyle->fAlignment) {
        case PlaceholderAlignment::kBaseline:
            fFontMetrics.fAscent = baselineAdjustment - offset;
            fFontMetrics.fDescent = baselineAdjustment + height - offset;
            break;
        case PlaceholderAlignment::kAboveBaseline:
            fFontMetrics.fAscent = baselineAdjustment - height;
            fFontMetrics.fDescent = baselineAdjustment;
            break;
        // ... 其他对齐方式
    }

    this->calculateMetrics();
    endlineMetrics->add(this);
}
```

支持六种对齐方式: Baseline、AboveBaseline、BelowBaseline、Top、Bottom、Middle。

### 文本到字形映射
`findLimitingClusters()` 查找文本范围对应的簇范围:

```cpp
std::tuple<bool, ClusterIndex, ClusterIndex> Run::findLimitingClusters(TextRange text) const {
    ClusterRange clusterRange;
    bool found = true;

    if (leftToRight()) {
        clusterRange.start = fOwner->clusterIndex(text.start);
        clusterRange.end = fOwner->clusterIndex(text.end - 1);
    } else {
        // RTL: 范围反向
        clusterRange.start = fOwner->clusterIndex(text.end);
        clusterRange.end = fOwner->clusterIndex(text.start + 1);
    }

    return std::make_tuple(found, clusterRange.start, clusterRange.end);
}
```

处理 LTR 和 RTL 的不同映射逻辑。

### Cluster 宽度估算
`sizeToChar()` 和 `sizeFromChar()` 按比例估算簇内部分宽度:

```cpp
SkScalar Cluster::sizeToChar(TextIndex ch) const {
    auto shift = ch - fTextRange.start;
    auto ratio = shift * 1.0 / fTextRange.width();
    return SkDoubleToScalar(fWidth * ratio);
}
```

这是一个简化的估算,假设簇内字符均匀分布宽度,实际可能不精确。

### 两端对齐偏移存储
`fJustificationShifts` 存储每个字形的两端对齐偏移:

```cpp
void Run::copyTo(SkTextBlobBuilder& builder, size_t pos, size_t size) const {
    for (size_t i = 0; i < size; ++i) {
        auto point = fPositions[i + pos];
        if (!fJustificationShifts.empty()) {
            point.fX += fJustificationShifts[i + pos].fX;  // 应用两端对齐偏移
        }
        point += fOffsets[i + pos];  // 应用字形偏移
        blobBuffer.points()[i] = point;
    }
}
```

分离存储使得字形数据可以共享,布局相关的偏移独立管理。

## 依赖关系

### 核心依赖
- **ParagraphImpl**: 所有者,管理 Run 和 Cluster 数组
- **SkShaper**: HarfBuzz 整形器,生成 Run 的字形数据
- **SkFont**: 字体对象
- **SkTextBlob**: 最终绘制的文本块
- **SkUnicode**: Unicode 属性查询(断行点、字位等)

### 使用者
- **OneLineShaper**: 创建和整形 Run
- **TextLine**: 使用 Run 和 Cluster 进行绘制和测量
- **TextWrapper**: 使用 Cluster 的断行属性进行换行
- **ParagraphImpl**: 管理所有 Run 和 Cluster,提供查询接口

### 依赖图
```
SkShaper (HarfBuzz)
    ↓ (shapes to)
Run + Cluster
    ↓ (stored in)
ParagraphImpl
    ↓ (used by)
TextLine + TextWrapper
```

## 设计模式与设计决策

### 分离关注点
- **Run**: 专注于整形结果和字形布局
- **Cluster**: 专注于文本到字形的映射和断行属性
- **InternalLineMetrics**: 专注于行度量计算

清晰的职责划分使代码易于理解和维护。

### 共享数据优化
使用 `std::shared_ptr<GlyphData>` 共享字形数据:
- 支持段落缓存和复制
- 减少内存占用
- 整形结果只读,布局修改独立存储

### 迭代器模式
提供多种遍历接口:
- `iterateThroughClustersInTextOrder()`: 按文本顺序遍历,处理 LTR 和 RTL
- `iterateThroughClusters()`: 按视觉顺序遍历
- 使用函数对象(lambda)作为访问器,灵活高效

### 类型安全的索引
定义专用的类型别名:
```cpp
typedef size_t RunIndex;
typedef size_t ClusterIndex;
typedef size_t GraphemeIndex;
typedef size_t GlyphIndex;
```
提高代码可读性,降低索引类型混淆的风险。

### 延迟计算
- 两端对齐偏移仅在需要时计算和存储
- `fJustificationShifts` 初始为空,节省内存

### 边界处理
构造函数中添加额外的边界元素:
```cpp
fPositions[info.glyphCount] = fOffset + fAdvance;  // 额外的位置
fClusterIndexes[info.glyphCount] = ...;            // 额外的索引
```
简化边界条件处理,避免越界检查。

## 性能考量

### 内存布局
- **STArray 优化**: 使用 `skia_private::STArray<64, ...>` 内联前 64 个元素,减少小运行的堆分配
- **共享字形数据**: 段落缓存可以共享整形结果,节省内存
- **独立两端对齐数组**: 仅在需要时分配

### 字形数据访问
- 使用 `SkSpan` 提供常量视图,避免复制
- 引用成员变量(如 `fGlyphs(fGlyphData->glyphs)`)提供直接访问

### 脚本识别优化
使用 `switch` 语句和四字节标签快速识别草书脚本:
```cpp
case SkSetFourByteTag('A', 'r', 'a', 'b'):
```
比字符串比较更高效。

### 字形复制优化
`copyTo()` 使用 `sk_careful_memcpy` 批量复制字形 ID,避免逐个复制。

### 度量计算缓存
度量信息在构造时计算一次,后续直接访问:
- `fCorrectAscent/fCorrectDescent`
- `fFontMetrics`

### 宽度计算估算
`sizeToChar()` 使用简单的比例估算而非精确计算,在性能和精度之间取得平衡。

## 相关文件

### 整形器
- `modules/skparagraph/src/OneLineShaper.h/.cpp`: 使用 HarfBuzz 整形器生成 Run
- `modules/skshaper/include/SkShaper.h`: 整形器接口

### 段落系统
- `modules/skparagraph/src/ParagraphImpl.h/.cpp`: Run 和 Cluster 的管理者
- `modules/skparagraph/src/TextLine.h/.cpp`: 使用 Run 和 Cluster 进行渲染
- `modules/skparagraph/src/TextWrapper.h/.cpp`: 使用 Cluster 进行换行

### Unicode 处理
- `modules/skunicode/include/SkUnicode.h`: Unicode 属性查询

### 核心依赖
- `include/core/SkFont.h`: 字体对象
- `include/core/SkTextBlob.h`: 文本块
- `include/core/SkFontMetrics.h`: 字体度量
