# ParagraphStyle

> 源文件: [modules/skparagraph/include/ParagraphStyle.h](../../../../modules/skparagraph/include/ParagraphStyle.h)

## 概述

`ParagraphStyle` 定义了文本段落的全局样式配置，包括文本对齐方式、文本方向、最大行数、省略号、行高、文本高度行为等。该文件同时定义了 `StrutStyle`（支柱样式），用于控制行间距的统一基准。这两个结构体共同构成了段落排版的全局配置参数，影响段落中所有文本的布局行为。

## 架构位置

```
skia::textlayout 命名空间
  ParagraphStyle  ← 本文件定义
    ├── 被 ParagraphBuilder 接受作为构建参数
    ├── 被 Paragraph 内部存储
    └── 包含:
          ├── StrutStyle (支柱样式)
          └── TextStyle (默认文本样式)
```

`ParagraphStyle` 是段落排版的顶层配置对象，控制段落级别的布局行为。

## 主要类与结构体

### StrutStyle（支柱样式）
- 定义段落中行间距的统一基准
- 属性：
  - `fFontFamilies` - 支柱字体族列表
  - `fFontStyle` - 支柱字体样式（粗细/宽度/倾斜）
  - `fFontSize` - 支柱字体大小
  - `fHeight` - 行高乘数
  - `fLeading` - 行距
  - `fForceHeight` - 是否强制使用支柱高度
  - `fEnabled` - 是否启用支柱
  - `fHeightOverride` - 是否覆盖高度
  - `fHalfLeading` - 是否使用半行距模式

### ParagraphStyle（段落样式）
- 段落的全局配置
- 包含 `StrutStyle`、默认 `TextStyle`、对齐、方向、行数限制、省略号等

## 公共 API 函数

### StrutStyle 方法
- `getFontFamilies()` / `setFontFamilies(...)` - 字体族
- `getFontStyle()` / `setFontStyle(...)` - 字体样式
- `getFontSize()` / `setFontSize(...)` - 字体大小
- `getHeight()` / `setHeight(...)` - 行高乘数
- `getLeading()` / `setLeading(...)` - 行距
- `getStrutEnabled()` / `setStrutEnabled(...)` - 启用/禁用
- `getForceStrutHeight()` / `setForceStrutHeight(...)` - 强制高度
- `getHeightOverride()` / `setHeightOverride(...)` - 高度覆盖
- `getHalfLeading()` / `setHalfLeading(...)` - 半行距
- `operator==` - 基于 `nearlyEqual` 的浮点安全比较

### ParagraphStyle 方法
- `getStrutStyle()` / `setStrutStyle(...)` - 支柱样式
- `getTextStyle()` / `setTextStyle(...)` - 默认文本样式
- `getTextDirection()` / `setTextDirection(...)` - 文本方向（LTR/RTL）
- `getTextAlign()` / `setTextAlign(...)` - 文本对齐
- `getMaxLines()` / `setMaxLines(...)` - 最大行数
- `getEllipsis()` / `setEllipsis(...)` - 省略号文本（UTF-8 和 UTF-16）
- `getHeight()` / `setHeight(...)` - 段落高度
- `getTextHeightBehavior()` / `setTextHeightBehavior(...)` - 文本高度行为
- `getReplaceTabCharacters()` / `setReplaceTabCharacters(...)` - Tab 字符替换
- `fakeMissingFontStyles()` / `setFakeMissingFontStyles(...)` - 模拟缺失字体样式
- `getApplyRoundingHack()` / `setApplyRoundingHack(...)` - 舍入修正
- `unlimited_lines()` - 是否无行数限制
- `ellipsized()` - 是否设置了省略号
- `effective_align()` - 考虑文本方向的实际对齐方式
- `hintingIsOn()` / `turnHintingOff()` - 字体提示控制

## 内部实现细节

### 相等性比较

`ParagraphStyle::operator==` 比较了所有影响布局的属性，包括高度、省略号（UTF-8 和 UTF-16 两种形式）、方向、对齐、默认文本样式、Tab 替换和字体样式模拟标志。

`StrutStyle::operator==` 使用 `nearlyEqual` 进行浮点数比较（而非精确相等），避免浮点精度问题导致不必要的重排。

### 省略号双编码

段落样式同时维护 `fEllipsis`（`SkString`，UTF-8）和 `fEllipsisUtf16`（`std::u16string`，UTF-16）两个省略号字段，允许客户端以任一编码设置省略号文本。`ellipsized()` 检查两者是否至少有一个非空。

### 行数限制

`fLinesLimit` 默认值为 `std::numeric_limits<size_t>::max()`，表示无限制。`unlimited_lines()` 方法检查此条件。

### 舍入修正标志

`fApplyRoundingHack` 默认为 `true`，是一个兼容性标志，控制是否应用舍入修正。这是为了与 Flutter 框架的现有行为保持一致。

## 依赖关系

- **Skia 核心**: `SkFontStyle`、`SkScalar`、`SkString`
- **skparagraph 模块**: `DartTypes`（TextAlign、TextDirection、TextHeightBehavior）、`TextStyle`
- **标准库**: `<algorithm>`、`<limits>`、`<string>`、`<vector>`

## 设计模式与设计决策

1. **值语义结构体**: `StrutStyle` 和 `ParagraphStyle` 均为值类型，支持拷贝和比较，适合作为配置参数传递。

2. **getter/setter 模式**: 所有属性通过 getter/setter 方法访问，保持了封装性并允许未来添加验证逻辑。

3. **支柱样式独立**: `StrutStyle` 作为独立结构体嵌入 `ParagraphStyle`，既可以独立配置也可以关联到段落。支柱机制源自 Flutter/Dart 的文本排版需求。

4. **浮点安全比较**: 使用 `nearlyEqual` 而非 `==` 比较浮点属性，避免了浮点精度问题。

5. **双编码省略号**: 同时支持 UTF-8 和 UTF-16 省略号，兼容不同客户端的编码习惯。

6. **向后兼容标志**: `fApplyRoundingHack` 和 `fFakeMissingFontStyles` 等布尔标志提供了渐进式的行为变更机制，允许在不破坏现有客户端的情况下引入新的排版行为。

7. **行数限制的哨兵值**: 使用 `std::numeric_limits<size_t>::max()` 作为无限行数的哨兵值，`unlimited_lines()` 方法封装了这个比较，提供了语义清晰的查询接口。

### StrutStyle 的设计来源

支柱（Strut）概念来源于 Flutter 框架的文本排版需求。在传统的文本排版中，行高由每个运行（run）中最高的字形决定。支柱机制允许指定一个独立于文本内容的行高基准，确保即使文本内容变化，行高也保持一致。这在 UI 布局中非常有用，可以防止不同字体或字号导致的行高跳变。

## 性能考量

- `ParagraphStyle` 作为配置对象，仅在段落创建时使用，不在渲染热路径中。
- `operator==` 用于段落缓存的键比较，采用短路求值减少不必要的比较。比较顺序经过优化，先比较最可能不同的属性（如文本方向、对齐方式）。
- `StrutStyle` 比较使用 `nearlyEqual`，虽然比精确比较稍慢，但避免了浮点精度差异导致的假阴性匹配（即两个视觉上等价的样式被判为不同）。
- `ParagraphStyle` 的拷贝涉及 `TextStyle`（默认文本样式）和 `StrutStyle` 的拷贝，其中 `TextStyle` 包含 vector 成员（字体族列表、阴影列表等），拷贝开销略高。应尽量避免不必要的拷贝。

### effective_align 方法

`effective_align()` 方法将逻辑对齐（`kStart`/`kEnd`）解析为物理对齐（`kLeft`/`kRight`），考虑当前的文本方向。该方法在布局阶段被频繁调用，但仅涉及简单的条件判断，不构成性能瓶颈。

### 段落缓存交互

`ParagraphStyle` 的 `operator==` 是段落缓存命中判断的关键路径。当缓存命中时，可以跳过整个布局计算（包括文本分析、字形整形、行断裂等），带来数量级的性能提升。因此，比较操作的正确性和效率对整体性能至关重要。

### 省略号处理

当 `ellipsized()` 返回 true 时，段落布局需要额外处理截断和省略号插入逻辑。两种编码的省略号字段（UTF-8 和 UTF-16）在使用时可能需要编码转换，但这仅在超出最大行数时发生。

## 相关文件

- `modules/skparagraph/include/DartTypes.h` - TextAlign、TextDirection 等枚举定义
- `modules/skparagraph/include/TextStyle.h` - 文本样式（默认样式的类型）
- `modules/skparagraph/include/Paragraph.h` - 存储段落样式的段落类
- `modules/skparagraph/include/ParagraphBuilder.h` - 接受段落样式的构建器
- `modules/skparagraph/src/ParagraphStyle.cpp` - 实现文件（包含 effective_align 等方法）
- `modules/skparagraph/include/ParagraphCache.h` - 使用 ParagraphStyle 的比较进行缓存匹配
- `include/core/SkFontStyle.h` - 字体样式（StrutStyle 中使用）
- `include/core/SkScalar.h` - 标量类型（SkScalar）
- `include/core/SkString.h` - 字符串类型（省略号存储）
- `modules/skparagraph/include/FontCollection.h` - 字体集合（与段落样式配合使用）
- `modules/skparagraph/src/ParagraphImpl.h` - 段落实现（消费段落样式）
