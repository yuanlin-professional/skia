# TextWrapper - 文本断行器

> 源文件: [`modules/skparagraph/src/TextWrapper.h`](../../../modules/skparagraph/src/TextWrapper.h), [`modules/skparagraph/src/TextWrapper.cpp`](../../../modules/skparagraph/src/TextWrapper.cpp)

## 概述

TextWrapper 是 Skia 段落排版模块中负责将整形后的文本按指定宽度断行的核心组件。它接收由 OneLineShaper 整形为一条无限长行的字符簇序列，根据最大宽度约束将其拆分为多行，同时计算每行的度量信息、最小/最大固有宽度等排版参数。

TextWrapper 实现了复杂的断行算法，支持按单词断行、按字符簇断行和按字形裁剪等多级回退策略，并处理占位符、省略号、行间距行为等特殊情况。

## 架构位置

TextWrapper 位于 skparagraph 的内部实现层：

- **调用者**: ParagraphImpl::breakShapedTextIntoLines()
- **协作组件**: Cluster（字符簇）、Run（运行）、TextLine（文本行）、InternalLineMetrics（行度量）
- **输入**: ParagraphImpl 中的字符簇数组和段落样式
- **输出**: 通过回调函数（AddLineToParagraph）向 ParagraphImpl 添加文本行

## 主要类与结构体

### `TextWrapper` 类

主类，管理断行过程的状态和算法。

```cpp
class TextWrapper {
public:
    TextWrapper();
    void breakTextIntoLines(ParagraphImpl* parent, SkScalar maxWidth,
                            const AddLineToParagraph& addLine);
    SkScalar height() const;
    SkScalar minIntrinsicWidth() const;
    SkScalar maxIntrinsicWidth() const;
    bool exceededMaxLines() const;
};
```

### `ClusterPos` 内部类

表示字符簇内的精确位置（簇指针 + 簇内偏移）。

```cpp
class ClusterPos {
    Cluster* fCluster;
    size_t fPos;
public:
    void move(bool up);  // 移动到下一个/上一个簇
    void clean();        // 重置位置
};
```

### `TextStretch` 内部类

表示一段文本范围（从起始 ClusterPos 到结束 ClusterPos），跟踪该范围的宽度和行度量。这是断行算法的核心数据结构。

```cpp
class TextStretch {
    ClusterPos fStart, fEnd, fBreak;
    InternalLineMetrics fMetrics;
    SkScalar fWidth;
    SkScalar fWidthWithGhostSpaces;
public:
    void extend(TextStretch& stretch);  // 合并另一段文本
    void extend(Cluster* cluster);       // 添加一个簇
    void startFrom(Cluster*, size_t);    // 从指定位置开始新的范围
    void saveBreak() / restoreBreak();   // 保存/恢复断行点
    void trim() / trim(Cluster*);        // 裁剪尾部空白
};
```

### `LineBreakerWithLittleRounding` 结构体

带有浮点数舍入容差的断行判断器，使用 [maxWidth - 0.25, maxWidth + 0.25] 的容差范围避免浮点精度问题导致的错误断行。

### `AddLineToParagraph` 类型别名

回调函数类型，用于将断行结果添加到 ParagraphImpl：
```cpp
using AddLineToParagraph = std::function<void(
    TextRange textExcludingSpaces, TextRange text, TextRange textIncludingNewlines,
    ClusterRange clusters, ClusterRange clustersWithGhosts,
    SkScalar widthWithSpaces, size_t startClip, size_t endClip,
    SkVector offset, SkVector advance, InternalLineMetrics metrics, bool addEllipsis)>;
```

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `breakTextIntoLines(parent, maxWidth, addLine)` | 核心方法：将文本断行并通过回调添加行 |
| `height()` | 返回所有行的总高度 |
| `minIntrinsicWidth()` | 返回最小固有宽度（最长单词的宽度） |
| `maxIntrinsicWidth()` | 返回最大固有宽度（不断行时每个软断行段的最大宽度） |
| `exceededMaxLines()` | 是否超过了最大行数限制 |

## 内部实现细节

### 断行主循环（breakTextIntoLines）

1. 初始化：设置 fEndLine 为第一个簇
2. **主循环**：当未到达文本末尾时：
   - `lookAhead()`: 向前扫描确定当前行能容纳的内容
   - `moveForward()`: 根据扫描结果确定行的结束位置
   - `trimEndSpaces()`: 移除行尾空白
   - `trimStartSpaces()`: 确定下一行的起始位置
   - 处理省略号、strut度量、TextHeightBehavior
   - 通过 addLine 回调添加行
   - 更新高度和固有宽度
3. **后处理**：扫描剩余文本计算最终的固有宽度

### lookAhead 算法

前瞻扫描是断行的核心，实现了多级策略：

1. **按词扫描**：逐簇前进，遇到空白/软断行符时将当前簇序列（fClusters）合并到词（fWords）
2. **溢出检测**：当累积宽度超过 maxWidth 时：
   - 遇到空白：仍然视为词结尾（空白在行尾可被裁剪）
   - 遇到占位符：如果是唯一内容且太长，标记为 fTooLongCluster
   - 其他情况：继续向前扫描判断是否整个词都超长
3. **超长词处理**：
   - 检查是否有非断行空格（Non-Breaking Space）可以用于辅助断行
   - 标记 fTooLongWord 以允许后续按簇断行
4. **硬断行**：遇到硬换行符立即停止

### moveForward 策略

采用三级回退：
1. 优先使用完整的词（fWords）
2. 如果词太长，使用簇序列（fClusters）
3. 如果簇也太大，使用裁剪片段（fClip）的度量

### 舍入容差处理

`LineBreakerWithLittleRounding` 在 maxWidth +/- 0.25 的范围内使用更精确的舍入判断，避免因浮点精度误差导致不必要的断行。支持两种模式：
- 启用 rounding hack（Round）：匹配 Flutter 旧行为
- 禁用 rounding hack（Floor）：更精确的行为

### 固有宽度计算

- **minIntrinsicWidth**: 所有单词宽度的最大值（即最长单词的宽度）
- **maxIntrinsicWidth**: 所有软断行段宽度的最大值（即不对硬断行段断行时的最大宽度）

## 依赖关系

- `modules/skparagraph/src/ParagraphImpl.h` - 段落实现（提供字符簇、样式等数据）
- `modules/skparagraph/src/TextLine.h` - 文本行和 InternalLineMetrics
- `include/core/SkSpan.h` - 区间视图
- `include/core/SkScalar.h` - 浮点数类型和工具

## 设计模式与设计决策

### 三段式文本追踪
TextWrapper 同时维护三个 TextStretch：
- `fWords`: 已确认的完整单词
- `fClusters`: 正在积累的当前词的簇
- `fClip`: 簇内的裁剪位置

这种分层设计支持从粗到细的断行回退策略。

### 回调式行输出
使用函数回调（AddLineToParagraph）而非直接操作 ParagraphImpl，实现了断行算法与行管理的解耦。

### 不可变输入
TextWrapper 不修改输入的字符簇数据，仅通过指针和位置追踪断行结果，保证了输入数据的安全性。

### Flutter 兼容设计
- 硬换行符处理跳过 `\n` 的度量（Flutter 行为）
- 忽略占位符运行的默认文本样式度量
- 支持 TextHeightBehavior 的 disableFirstAscent 和 disableLastDescent

## 性能考量

1. **单次遍历**: lookAhead 对簇序列仅进行一次前向扫描，而非回溯搜索
2. **惰性度量计算**: InternalLineMetrics 仅在遇到新运行时更新，避免冗余计算
3. **容差范围优化**: LineBreakerWithLittleRounding 使用 fLower/fUpper 快速判断，仅在边界情况才进行精确舍入计算
4. **最小簇表复制**: TextStretch 仅存储指针和位置，不复制实际的簇数据
5. **预处理优化**: 在 ParagraphImpl 中对单行、单运行、无空白的常见情况直接跳过 TextWrapper

## 相关文件

- `modules/skparagraph/src/ParagraphImpl.h` / `.cpp` - 调用方，提供排版上下文
- `modules/skparagraph/src/TextLine.h` / `.cpp` - 文本行定义和行级操作
- `modules/skparagraph/src/Run.h` - Run 和 Cluster 定义
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式（最大行数、省略号等）
