# ParagraphImpl - 段落排版实现

> 源文件: [`modules/skparagraph/src/ParagraphImpl.h`](../../../modules/skparagraph/src/ParagraphImpl.h), [`modules/skparagraph/src/ParagraphImpl.cpp`](../../../modules/skparagraph/src/ParagraphImpl.cpp)

## 概述

ParagraphImpl 是 Skia 段落排版模块（skparagraph）的核心实现类，继承自抽象基类 `Paragraph`。它负责将富文本内容进行完整的排版处理，包括文本整形（shaping）、断行（line breaking）、格式化（formatting）和绘制（painting）。该类与 Flutter 文本排版引擎深度集成，是 Flutter 框架中文本渲染的底层实现。

ParagraphImpl 管理着从输入文本到最终渲染的完整生命周期，通过内部状态机跟踪排版进度，并支持增量布局优化。

## 架构位置

ParagraphImpl 位于 skparagraph 模块的核心层：

- **上层调用者**: ParagraphBuilder（构建段落）、Flutter 引擎
- **同层组件**: TextLine（行管理）、TextWrapper（断行器）、OneLineShaper（整形器）、Run（运行）、Cluster（字符簇）
- **下层依赖**: SkUnicode（Unicode 处理）、FontCollection（字体管理）、SkShaper（文本整形）
- **缓存层**: ParagraphCache（段落级别的整形结果缓存）

## 主要类与结构体

### `ParagraphImpl` 类

继承自 `Paragraph`，是段落排版的完整实现。

```cpp
class ParagraphImpl final : public Paragraph {
public:
    ParagraphImpl(const SkString& text, ParagraphStyle style,
                  TArray<Block, true> blocks, TArray<Placeholder, true> placeholders,
                  sk_sp<FontCollection> fonts, sk_sp<SkUnicode> unicode);
    void layout(SkScalar width) override;
    void paint(SkCanvas* canvas, SkScalar x, SkScalar y) override;
    // ... 众多查询和操作方法
};
```

### `StyleBlock<TStyle>` 模板结构体
将文本范围（TextRange）与样式关联的容器，用于存储字母间距、词间距、背景色、前景色、阴影和装饰等样式。

```cpp
template <typename TStyle>
struct StyleBlock {
    TextRange fRange;
    TStyle fStyle;
};
```

### `ResolvedFontDescriptor` 结构体
记录字体解析结果，包含解析后的 SkFont 和对应文本起始位置。

### `InternalState` 枚举
排版处理的内部状态机：
- `kUnknown = 0` - 初始状态
- `kIndexed = 1` - 文本已索引（Unicode 属性已计算）
- `kShaped = 2` - 文本已整形
- `kLineBroken = 5` - 已完成断行
- `kFormatted = 6` - 已格式化（对齐等）
- `kDrawn = 7` - 已绘制

## 公共 API 函数

### 核心排版方法

| 函数 | 说明 |
|------|------|
| `layout(SkScalar width)` | 在指定宽度内执行排版，是主入口 |
| `paint(SkCanvas*, SkScalar x, SkScalar y)` | 使用 SkCanvas 绘制段落 |
| `paint(ParagraphPainter*, SkScalar x, SkScalar y)` | 使用自定义绘制器绘制段落 |

### 查询方法

| 函数 | 说明 |
|------|------|
| `getRectsForRange(start, end, heightStyle, widthStyle)` | 获取文本范围的包围矩形列表 |
| `getRectsForPlaceholders()` | 获取所有占位符的矩形 |
| `getGlyphPositionAtCoordinate(dx, dy)` | 根据坐标获取字形位置 |
| `getWordBoundary(offset)` | 获取包含指定偏移量的单词边界 |
| `getLineMetrics(metrics)` | 获取所有行的度量信息 |
| `getLineNumberAt(codeUnitIndex)` | 获取指定文本索引所在行号 |
| `getLineNumberAtUTF16Offset(offset)` | 获取 UTF-16 偏移量所在行号 |
| `getGlyphClusterAt(index, info)` | 获取指定索引处的字形簇信息 |
| `getClosestGlyphClusterAt(dx, dy, info)` | 获取最近坐标处的字形簇信息 |
| `getGlyphInfoAtUTF16Offset(index, info)` | 获取 UTF-16 偏移量处的字形信息 |
| `getFontAt(codeUnitIndex)` | 获取指定位置使用的字体 |
| `getFonts()` | 获取段落中使用的所有字体信息 |

### 更新方法

| 函数 | 说明 |
|------|------|
| `updateTextAlign(textAlign)` | 更新文本对齐方式 |
| `updateFontSize(from, to, fontSize)` | 更新字体大小 |
| `updateForegroundPaint(from, to, paint)` | 更新前景色 |
| `updateBackgroundPaint(from, to, paint)` | 更新背景色 |
| `markDirty()` | 标记段落为需要重新排版 |

### 遍历方法

| 函数 | 说明 |
|------|------|
| `visit(Visitor&)` | 遍历段落的所有文本运行和字形信息 |
| `extendedVisit(ExtendedVisitor&)` | 增强版遍历，包含字形边界等额外信息 |
| `getPath(lineNumber, dest)` | 获取指定行的路径轮廓 |

## 内部实现细节

### 排版流水线（layout 方法）

`layout()` 是核心入口，实现了增量排版优化的状态机：

1. **状态判断与优化**
   - 单行文本且宽度足够：直接跳到整形后状态
   - 宽度变化但已断行：从整形状态重新开始
   - 无变化：复用之前的结果

2. **整形阶段**（kUnknown -> kShaped）
   - 先查询 ParagraphCache，命中则跳过整形
   - `computeCodeUnitProperties()`: 计算 Unicode 属性（BiDi 区域、空白字符、换行符等）
   - `shapeTextIntoEndlessLine()`: 使用 OneLineShaper 将文本整形为一条无限长的行
   - `applySpacingAndBuildClusterTable()`: 应用字间距/字母间距并构建字符簇表

3. **断行阶段**（kShaped -> kLineBroken）
   - `breakShapedTextIntoLines()`: 使用 TextWrapper 将整形文本按指定宽度断行
   - 单行优化：无换行符、无内部空格、单运行时使用快速路径

4. **格式化阶段**（kLineBroken -> kFormatted）
   - `formatLines()`: 对每行应用对齐方式（左、右、居中、两端对齐）

### 字符簇表构建

`buildClusterTable()` 将整形后的运行（Run）转换为字符簇（Cluster）序列：
- 遍历所有运行的字形，按输入文本顺序创建字符簇
- 构建 `fClustersIndexFromCodeUnit` 索引表实现文本位置到簇的快速查找
- 占位符运行创建独立的单簇

### 间距处理

`applySpacingAndBuildClusterTable()` 处理三种情况：
1. 无间距（最常见）：直接构建簇表
2. 全局字母间距：统一应用后构建簇表
3. 复杂间距：先构建簇表，再遍历每个簇应用对应的间距样式

### UTF-16 映射

`ensureUTF16Mapping()` 使用 `SkOnce` 确保 UTF-8/UTF-16 索引映射只构建一次，支持 Flutter 中 UTF-16 偏移量的查询方法。

### Strut 度量

`resolveStrut()` 计算 strut（支撑线）度量：
- 支持半行间距（half leading）模式
- 支持高度覆盖（height override）
- 可强制所有行使用 strut 高度

### 行号查找

`getLineNumberAt()` 使用二分查找定位行号，时间复杂度 O(log n)。

## 依赖关系

- `modules/skparagraph/include/Paragraph.h` - 抽象基类
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式
- `modules/skparagraph/include/TextStyle.h` - 文本样式
- `modules/skparagraph/include/FontCollection.h` - 字体集合
- `modules/skparagraph/include/ParagraphCache.h` - 段落缓存
- `modules/skparagraph/src/Run.h` - 运行（整形后的文本片段）
- `modules/skparagraph/src/TextLine.h` - 文本行
- `modules/skparagraph/src/TextWrapper.h` - 断行器
- `modules/skparagraph/src/OneLineShaper.h` - 文本整形器
- `modules/skunicode/include/SkUnicode.h` - Unicode 处理接口
- `include/core/SkCanvas.h` - 画布（绘制用）
- `include/core/SkPicture.h` - 图片录制（缓存绘制命令）

## 设计模式与设计决策

### 状态机模式
使用 InternalState 枚举管理排版流水线状态。每个状态代表排版进度的一个阶段，支持从中间状态重新开始（增量排版）。状态只能向更高状态推进，回退时会清除对应阶段的数据。

### 缓存策略
- **段落缓存**: 通过 ParagraphCache 缓存整形结果，避免对相同文本和样式的重复整形
- **UTF-16 映射缓存**: 使用 SkOnce 确保惰性构建且只构建一次
- **Picture 缓存**: 将绘制命令录制为 SkPicture，避免重复绘制

### Flutter 兼容性
代码中有大量针对 Flutter 行为的特殊处理：
- `littleRound()` 函数对浮点数进行精度舍入以匹配 Flutter 测试
- `getApplyRoundingHack()` 控制宽度舍入行为
- 空行度量的两种不同计算方式（空段落 vs 段落内空行）
- 单行省略号和最大行数的特殊处理

### 友元类设计
ParagraphImpl 将 TextWrapper、OneLineShaper、ParagraphBuilder、ParagraphCache 等声明为友元类，允许它们直接访问内部数据结构，避免了过多的 getter/setter 开销。

## 性能考量

1. **增量布局**: 通过状态机避免重复计算。宽度不变时直接复用之前的结果；宽度变化但文本不变时跳过整形阶段。

2. **单行快速路径**: `breakShapedTextIntoLines()` 对仅有一行、单运行、无换行符、无内部空白的常见情况进行了特殊优化，避免启动完整的断行逻辑。

3. **段落缓存**: 通过 ParagraphCache 缓存整形结果，相同文本和样式的段落可以直接复用。

4. **惰性 UTF-16 映射**: UTF-8/UTF-16 索引映射仅在需要时构建（通过 `SkOnce`），且只构建一次。

5. **行号二分查找**: `getLineNumberAt()` 使用二分查找，时间复杂度从 O(n) 降到 O(log n)。

6. **簇索引表**: `fClustersIndexFromCodeUnit` 数组提供 O(1) 的文本位置到字符簇的查找。

7. **间距优化**: 对最常见的无间距情况跳过所有间距处理；对全局统一字母间距使用简化路径。

8. **内存预分配**: `fClusters.reserve_exact()` 在构建簇表前预分配足够的空间，避免动态扩容。

## 相关文件

- `modules/skparagraph/include/Paragraph.h` - 抽象基类定义
- `modules/skparagraph/include/ParagraphBuilder.h` - 段落构建器
- `modules/skparagraph/src/TextWrapper.h` / `.cpp` - 断行实现
- `modules/skparagraph/src/OneLineShaper.h` / `.cpp` - 文本整形实现
- `modules/skparagraph/src/TextLine.h` / `.cpp` - 文本行实现
- `modules/skparagraph/src/Run.h` / `.cpp` - 运行和字符簇定义
- `modules/skparagraph/include/ParagraphCache.h` - 段落缓存
- `modules/skparagraph/src/ParagraphPainterImpl.h` - 画布绘制器适配
