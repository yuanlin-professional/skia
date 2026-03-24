# DartTypes

> 源文件: [modules/skparagraph/include/DartTypes.h](../../../../modules/skparagraph/include/DartTypes.h)

## 概述

`DartTypes.h` 定义了 Skia 段落排版模块中与 Dart/Flutter 框架对齐的基础类型和枚举。这些类型包括文本对齐方式、文本方向、矩形高度/宽度样式、文本基线类型、文本高度行为、行度量样式等，以及辅助数据结构如 `PositionWithAffinity`、`TextBox`、`SkRange` 模板等。该文件是整个 skparagraph 模块的类型基础设施。

## 架构位置

```
skia::textlayout 命名空间
  DartTypes.h  ← 基础类型定义层
    ├── 被 TextStyle.h 引用
    ├── 被 ParagraphStyle.h 引用
    ├── 被 Paragraph.h 引用
    └── 被 Metrics.h 引用
```

作为模块的基础类型头文件，被几乎所有其他 skparagraph 头文件依赖。

## 主要类与结构体

### 枚举类型

#### Affinity
- `kUpstream` / `kDownstream` - 文本位置亲和性，用于光标定位（在双向文本边界处决定光标属于前一个还是后一个运行）

#### RectHeightStyle
- `kTight` - 紧凑边界框，适合每个运行的高度
- `kMax` - 最大高度，同一行所有矩形使用该行最大运行高度
- `kIncludeLineSpacingMiddle` - 包含行距（上下各一半）
- `kIncludeLineSpacingTop` - 行距加到顶部
- `kIncludeLineSpacingBottom` - 行距加到底部
- `kStrut` - 使用支柱高度

#### RectWidthStyle
- `kTight` - 紧凑宽度
- `kMax` - 最大宽度（每行最后矩形扩展到最宽行的宽度）

#### TextAlign
- `kLeft` / `kRight` / `kCenter` / `kJustify` / `kStart` / `kEnd`
- `kStart`/`kEnd` 根据文本方向动态解析为 `kLeft` 或 `kRight`

#### TextDirection
- `kRtl`（从右到左）/ `kLtr`（从左到右）

#### TextBaseline
- `kAlphabetic`（字母基线）/ `kIdeographic`（表意文字基线）

#### TextHeightBehavior
- `kAll = 0x0` - 默认行为
- `kDisableFirstAscent = 0x1` - 禁用第一行上升
- `kDisableLastDescent = 0x2` - 禁用最后行下降
- `kDisableAll = 0x3` - 禁用两者

#### LineMetricStyle
- `Typographic` - 基于固定基线的排版度量
- `CSS` - CSS 风格的度量（分割行距，含高度调整）

### 数据结构

#### PositionWithAffinity
- `position`（`int32_t`）: 文本位置
- `affinity`（`Affinity`）: 位置亲和性
- 用于 `getGlyphPositionAtCoordinate` 的返回值

#### TextBox
- `rect`（`SkRect`）: 边界矩形
- `direction`（`TextDirection`）: 文本方向
- 用于 `getRectsForRange` 的返回值

#### SkRange<T>（模板）
- 表示 [start, end) 范围
- 提供 `width()`、`Shift()`、`contains()`、`intersects()`、`intersection()`、`empty()` 等操作
- `EMPTY_RANGE` 常量表示空范围（start = end = `EMPTY_INDEX`）

### 辅助函数

#### directional_for_each
```cpp
template<typename C, typename UnaryFunction>
UnaryFunction directional_for_each(C& c, bool forwards, UnaryFunction f);
```
根据方向参数选择正向或反向遍历容器，支持双向文本处理。

## 公共 API 函数

### SkRange<T> 方法
- `width()` - 返回范围宽度（`end - start`）
- `Shift(delta)` - 整体平移范围
- `contains(other)` - 检查是否包含另一个范围
- `intersects(other)` - 检查是否与另一个范围相交
- `intersection(other)` - 返回两个范围的交集
- `empty()` - 检查是否为空范围

## 内部实现细节

### 常量定义
- `EMPTY_INDEX = std::numeric_limits<size_t>::max()` - 空索引的哨兵值
- `EMPTY_RANGE` - 使用 EMPTY_INDEX 构造的空范围常量

### SignedT 类型别名
`SkRange<T>` 内部定义了 `SignedT = std::make_signed_t<T>`，使得 `Shift` 操作可以接受负数偏移量（用于反向移动范围）。

### TextHeightBehavior 位标志
使用位标志设计，支持组合（如 `kDisableAll = kDisableFirstAscent | kDisableLastDescent`），允许独立控制首行和末行的高度行为。

## 依赖关系

- **Skia 核心**: `SkRect`、`SkTypes`
- **标准库**: `<algorithm>`、`<iterator>`、`<limits>`

## 设计模式与设计决策

1. **与 Flutter/Dart 对齐**: 类型名称和枚举值与 Dart 的 `dart:ui` 库中的文本排版 API 保持一致，降低了 Flutter 引擎集成的复杂度。

2. **位标志模式**: `TextHeightBehavior` 和 `TextDecoration`（在其他文件中）使用位标志，支持灵活的组合配置。

3. **范围模板**: `SkRange<T>` 提供了通用的范围抽象，在整个模块中广泛用于表示文本范围、块范围等。

4. **哨兵值**: 使用 `max()` 作为空索引的哨兵值，与 0 区分（0 是有效的文本索引）。

5. **方向遍历抽象**: `directional_for_each` 将正向/反向遍历统一为一个函数调用，简化了双向文本处理逻辑。

## 性能考量

- 所有类型为轻量级值类型或枚举，无堆分配。
- `SkRange` 的所有操作为 O(1) 常量时间。
- `directional_for_each` 通过编译期模板实例化分支选择，运行时无额外分支开销。
- 枚举使用默认底层类型（int），枚举比较为单指令操作。

### SkRange 模板的使用模式

`SkRange<size_t>` 在 skparagraph 模块中被大量使用，主要作为以下别名：
- `TextRange` - 文本索引范围
- `BlockRange` - 样式块索引范围

由于 `SkRange` 的所有方法都是内联的，编译器可以完全消除函数调用开销。`intersection()` 方法使用 `std::max`/`std::min` 实现，在现代 CPU 上通常编译为条件移动指令（cmov），避免分支预测失败。

### RectHeightStyle 对查询性能的影响

不同的 `RectHeightStyle` 选项影响 `getRectsForRange` 的计算复杂度：
- `kTight` 最简单，直接使用每个运行的高度
- `kMax` 需要先扫描整行找到最大高度
- `kIncludeLineSpacing*` 变体需要计算行间距的分配
- `kStrut` 需要查询支柱样式参数

### TextBox 的内存布局

`TextBox` 结构体（`SkRect` + `TextDirection`）约 20 字节，`getRectsForRange` 返回的 `vector<TextBox>` 在长文本选区场景下可能包含大量元素，应注意内存分配。

## 相关文件

- `modules/skparagraph/include/TextStyle.h` - 使用 TextDecoration 等类型
- `modules/skparagraph/include/ParagraphStyle.h` - 使用 TextAlign、TextDirection 等
- `modules/skparagraph/include/Paragraph.h` - 使用 TextBox、PositionWithAffinity 等
- `modules/skparagraph/include/Metrics.h` - 使用 TextRange（SkRange 的别名）
