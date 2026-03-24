# Metrics

> 源文件: [modules/skparagraph/include/Metrics.h](../../../../modules/skparagraph/include/Metrics.h)

## 概述

`Metrics.h` 定义了 Skia 段落排版模块中的度量数据结构，包括 `StyleMetrics`（样式度量）和 `LineMetrics`（行度量）。`StyleMetrics` 将文本样式与对应的字体度量关联起来，`LineMetrics` 记录段落中每一行的详细布局信息（起止索引、上升/下降量、高度、宽度、基线位置等）。这些数据结构是段落排版结果的核心输出，供客户端查询行信息和绘制光标/选区。

## 架构位置

```
skia::textlayout 命名空间
  Paragraph
    └── getLineMetrics() → std::vector<LineMetrics>  ← 本文件定义
          └── LineMetrics
                └── fLineMetrics: std::map<size_t, StyleMetrics>
                      └── StyleMetrics (文本样式 + 字体度量)
```

`Metrics` 是段落布局结果的数据层，由 `ParagraphImpl` 在布局过程中填充，通过 `Paragraph::getLineMetrics` 接口暴露给客户端。

## 主要类与结构体

### StyleMetrics
- 关联一个 `TextStyle` 指针和对应的 `SkFontMetrics`
- 字体度量包含：Top、Ascent、Descent、Bottom、Leading、AvgCharWidth、MaxCharWidth、XMin、XMax、XHeight、CapHeight、UnderlineThickness/Position、StrikeoutThickness/Position

### LineMetrics
- 描述段落中单行的完整布局信息
- 文本范围：
  - `fStartIndex` - 行起始文本索引
  - `fEndIndex` - 行结束文本索引
  - `fEndExcludingWhitespaces` - 不含尾随空白的结束索引
  - `fEndIncludingNewline` - 含换行符的结束索引
  - `fHardBreak` - 是否为硬换行
- 布局度量：
  - `fAscent` / `fDescent` - 行的上升/下降量（正值）
  - `fUnscaledAscent` - 未缩放的上升量
  - `fHeight` - 累积段落高度（包含当前行）
  - `fWidth` - 行宽
  - `fLeft` - 行左边缘位置
  - `fBaseline` - 基线距段落顶部的 y 坐标
  - `fLineNumber` - 零索引行号
- 运行度量映射：
  - `fLineMetrics` - `std::map<size_t, StyleMetrics>`，按文本索引映射到对应的样式度量

## 公共 API 函数

### StyleMetrics 构造函数
```cpp
explicit StyleMetrics(const TextStyle* style);
StyleMetrics(const TextStyle* style, SkFontMetrics& metrics);
```
从文本样式构造，可选地传入字体度量。

### LineMetrics 构造函数
```cpp
LineMetrics();
LineMetrics(size_t start, size_t end, size_t end_excluding_whitespace,
            size_t end_including_newline, bool hard_break);
```
默认构造和参数化构造。

## 内部实现细节

### 度量值的符号约定

注释说明上升量和下降量均为正值：
- 行的顶边 = `baseline - ascent`
- 行的底边 = `baseline + descent`
- 当前行高 = `round(ascent + descent)`

这与 `SkFontMetrics` 中上升为负值的约定不同，此处已转换为正值。

### 累积高度

`fHeight` 不是当前行的高度，而是段落从开头到当前行底部的累积高度。这方便客户端直接用此值作为段落的总渲染高度。

### 运行度量映射

`fLineMetrics`（`std::map<size_t, StyleMetrics>`）将文本索引映射到字体度量。第一个运行的键为 `fStartIndex`。这些度量是布局前的基础值（base values），用于计算最终的行度量。

### 默认值

度量值的默认值经过精心选择：
- `fAscent` 默认为 `SK_ScalarMax`（正无穷大）
- `fDescent` 默认为 `SK_ScalarMin`（负无穷大）
- 这些极值确保在取最值运算中不会错误地影响结果

## 依赖关系

- **Skia 核心**: `SkFontMetrics`、`SkScalar`
- **skparagraph 模块**: `TextStyle`
- **标准库**: `<map>`

## 设计模式与设计决策

1. **数据传输对象（DTO）**: `LineMetrics` 和 `StyleMetrics` 纯粹作为数据容器使用，没有业务逻辑。

2. **公开成员变量**: 两个类都使用公开成员变量而非 getter/setter，这简化了访问但减少了封装性，符合性能敏感的度量数据的使用模式。

3. **与 Flutter 对齐**: `LineMetrics` 的字段设计与 Flutter 的 `LineMetrics` 类一一对应，方便引擎层的数据传递。

4. **有序映射**: `fLineMetrics` 使用 `std::map`（有序映射），保证按文本索引顺序遍历运行度量。

5. **指针引用样式**: `StyleMetrics` 持有 `const TextStyle*` 而非拷贝，避免了样式对象的重复存储，但要求样式的生命周期覆盖度量数据的使用期。

## 性能考量

- `StyleMetrics` 包含一个指针和一个 `SkFontMetrics`（约 60 字节），拷贝开销可接受。
- `LineMetrics` 包含多个基本类型成员和一个 `std::map`，map 的分配和查找为 O(log N)。
- 度量数据在布局时一次性计算，查询时直接读取。
- `std::map` 的有序性在遍历时有用，但若查找频繁可考虑替换为 `std::unordered_map`。

## 相关文件

- `modules/skparagraph/include/Paragraph.h` - `getLineMetrics()` 方法定义
- `modules/skparagraph/include/TextStyle.h` - `TextStyle` 类（StyleMetrics 引用）
- `modules/skparagraph/src/ParagraphImpl.h` - 布局实现（填充度量数据）
- `include/core/SkFontMetrics.h` - Skia 字体度量结构
