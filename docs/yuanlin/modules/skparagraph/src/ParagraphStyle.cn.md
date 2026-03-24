# ParagraphStyle

> 源文件: modules/skparagraph/src/ParagraphStyle.cpp

## 概述

`ParagraphStyle` 是 Skia 段落排版系统中用于定义段落级样式属性的核心配置类。该类管理文本对齐方式、文本方向、行高、行数限制等影响整个段落布局的全局属性。与作用于单个字符或文本片段的 `TextStyle` 不同，`ParagraphStyle` 定义了段落的整体排版行为。

该实现文件提供了 `ParagraphStyle` 和 `StrutStyle`（支柱样式）两个类的构造函数和辅助方法。`StrutStyle` 用于为段落定义最小行高约束，确保文本行即使在使用小字号时也能保持一致的垂直间距。`effective_align()` 方法将抽象的对齐方式（如 `kStart`、`kEnd`）转换为基于文本方向的具体对齐（左对齐或右对齐）。

## 架构位置

`ParagraphStyle` 在 Skia 段落排版架构中的位置：

```
Skia 文本排版层次
├── modules/skparagraph/           段落排版模块
│   ├── include/
│   │   ├── ParagraphStyle.h      段落样式接口（本类声明）
│   │   ├── TextStyle.h           字符级样式（对比）
│   │   ├── Paragraph.h           段落抽象接口
│   │   └── ParagraphBuilder.h    段落构建器
│   └── src/
│       ├── ParagraphStyle.cpp    本实现文件
│       ├── ParagraphImpl.cpp     段落核心实现
│       └── TextLine.cpp          文本行布局
└── modules/skshaper/              底层文本整形
    └── include/SkShaper.h
```

**角色定位**：
- **配置层**：提供段落构建器的初始配置
- **全局样式**：影响整个段落的排版决策
- **布局参数**：传递给文本行布局和换行算法

## 主要类与结构体

### StrutStyle 类

```cpp
class StrutStyle {
public:
    SkFontStyle fFontStyle;    // 字体样式（粗细、宽度、倾斜）
    SkScalar fFontSize;        // 字体大小
    SkScalar fHeight;          // 行高倍数
    SkScalar fLeading;         // 额外行间距
    bool fForceHeight;         // 强制使用支柱高度
    bool fHeightOverride;      // 覆盖字体度量高度
    bool fHalfLeading;         // 使用半行距模式
    bool fEnabled;             // 是否启用支柱样式
};
```

**用途**：定义段落的最小行高和基线网格约束。

**默认值**：
```cpp
StrutStyle::StrutStyle() {
    fFontStyle = SkFontStyle::Normal();
    fFontSize = 14;
    fHeight = 1;
    fLeading = -1;           // 负值表示使用字体默认行距
    fForceHeight = false;
    fHeightOverride = false;
    fHalfLeading = false;
    fEnabled = false;        // 默认不启用
}
```

### ParagraphStyle 类

```cpp
class ParagraphStyle {
public:
    TextAlign fTextAlign;                // 文本对齐方式
    TextDirection fTextDirection;        // 文本方向（LTR/RTL）
    size_t fLinesLimit;                  // 最大行数限制
    SkScalar fHeight;                    // 行高倍数
    TextHeightBehavior fTextHeightBehavior; // 文本高度行为
    bool fHintingIsOn;                   // 是否启用字体提示
    bool fReplaceTabCharacters;          // 是否替换制表符
    bool fFakeMissingFontStyles;         // 伪造缺失的字体样式
    // ... 其他成员
};
```

**默认配置**：
```cpp
ParagraphStyle::ParagraphStyle() {
    fTextAlign = TextAlign::kStart;                  // 起始对齐
    fTextDirection = TextDirection::kLtr;            // 从左到右
    fLinesLimit = std::numeric_limits<size_t>::max(); // 无限行数
    fHeight = 1;                                     // 正常行高
    fTextHeightBehavior = TextHeightBehavior::kAll;
    fHintingIsOn = true;                             // 启用提示
    fReplaceTabCharacters = false;
    fFakeMissingFontStyles = true;                   // 允许样式模拟
}
```

## 公共 API 函数

### 构造函数

```cpp
StrutStyle::StrutStyle();
ParagraphStyle::ParagraphStyle();
```

**功能**：使用合理的默认值初始化样式对象。

**设计考量**：
- 默认不启用 `StrutStyle`（`fEnabled = false`）
- 无限行数限制（`std::numeric_limits<size_t>::max()`）
- 支持文本方向感知的对齐（`kStart` 而非硬编码 `kLeft`）

### 有效对齐计算

```cpp
TextAlign ParagraphStyle::effective_align() const;
```

**功能**：根据段落文本方向解析抽象对齐方式为具体对齐。

**转换规则**：

| 输入对齐 (`fTextAlign`) | 文本方向 (`fTextDirection`) | 输出对齐 |
|------------------------|---------------------------|---------|
| `kStart`               | `kLtr`                    | `kLeft` |
| `kStart`               | `kRtl`                    | `kRight`|
| `kEnd`                 | `kLtr`                    | `kRight`|
| `kEnd`                 | `kRtl`                    | `kLeft` |
| `kLeft/kRight/kCenter/kJustify` | 任意          | 不变     |

**实现**：
```cpp
TextAlign ParagraphStyle::effective_align() const {
    if (fTextAlign == TextAlign::kStart) {
        return (fTextDirection == TextDirection::kLtr) ? TextAlign::kLeft : TextAlign::kRight;
    } else if (fTextAlign == TextAlign::kEnd) {
        return (fTextDirection == TextDirection::kLtr) ? TextAlign::kRight : TextAlign::kLeft;
    } else {
        return fTextAlign;
    }
}
```

**应用场景**：
- 在文本行布局时确定字形的水平放置位置
- 支持国际化文本的自动对齐调整
- 简化 API（开发者无需关心文本方向细节）

## 内部实现细节

### StrutStyle 的作用机制

支柱样式（Strut）类似于印刷术语中的"支撑柱"，定义了文本行的最小高度：

1. **启用条件**：
   ```cpp
   if (strutStyle.fEnabled) {
       // 计算支柱度量
       SkFontMetrics strutMetrics = calculateStrutMetrics(strutStyle);
       // 确保行高不小于支柱高度
       lineHeight = std::max(lineHeight, strutMetrics.height());
   }
   ```

2. **高度计算**：
   - 当 `fHeightOverride = true`：使用 `fHeight * fFontSize` 作为总高度
   - 当 `fHeightOverride = false`：使用字体的实际度量乘以 `fHeight`
   - `fLeading >= 0` 时添加额外的行间距

3. **半行距模式**：
   ```cpp
   if (fHalfLeading) {
       // 行距均匀分布在上下
       ascent -= leading / 2;
       descent += leading / 2;
   }
   ```

### 行数限制的处理

`fLinesLimit` 在段落布局时的应用：

```cpp
// 伪代码示例
while (hasMoreText && currentLineCount < style.fLinesLimit) {
    layoutNextLine();
    currentLineCount++;
}

if (currentLineCount >= style.fLinesLimit && hasMoreText) {
    applyEllipsis();  // 应用省略号
}
```

**性能优化**：使用 `std::numeric_limits<size_t>::max()` 作为"无限制"标记，避免分支判断。

### 制表符替换

`fReplaceTabCharacters` 控制制表符的处理方式：

- **true**：将 `\t` 转换为空格或自定义宽度
- **false**：保留制表符，使用字体的制表符字形

这是实现细节，具体替换逻辑位于 `ParagraphImpl::buildClusterTable()` 中。

### 字体样式伪造

`fFakeMissingFontStyles` 允许系统在字体不支持特定样式时进行模拟：

```cpp
if (style.fFakeMissingFontStyles) {
    // 如果字体没有粗体变体，通过描边模拟
    // 如果字体没有斜体，通过倾斜矩阵模拟
}
```

这是常见的文本渲染优化，确保即使字体缺失样式变体，文本仍能正确显示。

## 依赖关系

### 头文件依赖

```cpp
#include "modules/skparagraph/include/DartTypes.h"    // TextAlign, TextDirection 等枚举
#include "modules/skparagraph/include/ParagraphStyle.h"
#include "src/base/SkUTF.h"                            // UTF 处理工具
#include "src/core/SkStringUtils.h"                    // 字符串工具
```

### 类型依赖

- `SkFontStyle` - 字体粗细/宽度/倾斜配置
- `SkScalar` - Skia 浮点标量类型
- `TextAlign`, `TextDirection`, `TextHeightBehavior` - DartTypes.h 中的枚举

### 被依赖关系

```
ParagraphStyle.cpp 被以下模块使用：
├── ParagraphBuilder.cpp    使用此配置创建段落
├── ParagraphImpl.cpp       布局时查询样式属性
├── TextLine.cpp            应用对齐和行高设置
└── ParagraphCache.cpp      作为缓存键的一部分
```

## 设计模式与设计决策

### 值对象模式（Value Object）

`ParagraphStyle` 和 `StrutStyle` 都是纯数据类（POD-like），采用值语义：

- **不可变性**：构造后通常不修改（通过 `ParagraphBuilder` 设置）
- **可复制**：支持深拷贝，安全传递
- **无副作用**：不持有资源，仅存储配置

### 默认即合理原则

构造函数提供的默认值经过精心设计：

```cpp
fLinesLimit = std::numeric_limits<size_t>::max();  // 而非 0 或 -1
fHeight = 1;                                       // 而非 0（避免除零）
fHintingIsOn = true;                               // 默认启用，提升可读性
```

这些默认值确保即使不进行配置，段落也能正常渲染。

### 文本方向抽象

`kStart` 和 `kEnd` 对齐方式的设计体现了国际化考量：

```
从左到右语言（英语）：Start → Left，End → Right
从右到左语言（阿拉伯语）：Start → Right，End → Left
```

通过 `effective_align()` 延迟解析，使 API 更加语义化。

### 分离关注点

段落样式与文本样式分离：

- **ParagraphStyle**：段落级属性（对齐、方向、行数）
- **TextStyle**：字符级属性（颜色、字号、字体）

这种设计使样式管理更清晰，避免单一类过于臃肿。

## 性能考量

### 轻量级结构

`ParagraphStyle` 主要包含基本类型和小型结构体：

```cpp
sizeof(ParagraphStyle) ≈ 几十字节
```

**优势**：
- 复制成本低
- 缓存友好
- 适合按值传递

### 行数限制的优化

使用 `std::numeric_limits<size_t>::max()` 而非布尔标志：

```cpp
// 高效：单次比较
if (currentLineCount >= style.fLinesLimit) break;

// 不采用：需要两次检查
if (style.hasLimit && currentLineCount >= style.lineLimit) break;
```

### StrutStyle 的条件计算

通过 `fEnabled` 标志避免不必要的计算：

```cpp
if (strutStyle.fEnabled) {
    // 仅在需要时计算支柱度量
}
```

大多数段落不使用支柱样式，这节省了字体度量查询的开销。

### 对齐计算的分支预测

`effective_align()` 的实现有利于 CPU 分支预测：

```cpp
if (fTextAlign == TextAlign::kStart) { ... }
else if (fTextAlign == TextAlign::kEnd) { ... }
else { return fTextAlign; }  // 最常见的分支（直接对齐）
```

大多数文本使用明确对齐（`kLeft`, `kCenter`），不需要转换。

## 相关文件

### 接口定义
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/ParagraphStyle.h` - 类声明和文档
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/DartTypes.h` - 枚举类型定义

### 核心实现
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/ParagraphImpl.cpp` - 段落布局实现
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/TextLine.cpp` - 文本行应用样式

### 相关样式
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextStyle.h` - 字符级样式
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/TextStyle.cpp` - 文本样式实现

### 使用示例
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/ParagraphBuilder.h` - 段落构建器 API
- `/Users/yuanlin/workspace/skia/modules/skparagraph/tests/ParagraphTest.cpp` - 单元测试

### 工具依赖
- `/Users/yuanlin/workspace/skia/src/base/SkUTF.h` - UTF 字符处理
- `/Users/yuanlin/workspace/skia/include/core/SkFontStyle.h` - 字体样式定义
