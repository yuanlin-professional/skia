# TextStyle

> 源文件: modules/skparagraph/src/TextStyle.cpp

## 概述

`TextStyle` 是 Skia 段落排版系统中用于定义字符级文本样式属性的核心类。该类封装了字体、颜色、装饰、阴影、字间距等所有影响单个字符或文本片段外观的属性。与定义段落整体布局的 `ParagraphStyle` 不同，`TextStyle` 可以应用于文本的任意子串，支持富文本效果。

该实现文件提供了文本样式的比较、克隆、字体度量计算等核心功能。特别重要的是 `equals()` 和 `equalsByFonts()` 方法，它们用于判断样式是否需要重新整形或重新绘制，这是文本渲染性能优化的关键。`matchOneAttribute()` 方法支持按单个属性（如颜色、装饰）进行比较，用于样式区间的细粒度分割。

## 架构位置

`TextStyle` 在 Skia 文本渲染架构中的位置：

```
Skia 文本排版层次
├── modules/skparagraph/           段落排版模块
│   ├── include/
│   │   ├── TextStyle.h           文本样式类（本类定义）
│   │   ├── ParagraphStyle.h      段落级样式（对比）
│   │   ├── TextShadow.h          阴影效果（组件）
│   │   └── FontArguments.h       字体参数（组件）
│   └── src/
│       ├── TextStyle.cpp         本实现文件
│       ├── ParagraphImpl.cpp     段落实现（应用样式）
│       ├── TextLine.cpp          文本行绘制（使用样式）
│       └── Iterators.h           样式迭代器
├── modules/skshaper/              文本整形模块
│   └── src/SkShaper_harfbuzz.cpp  HarfBuzz 整形（依赖字体样式）
└── include/core/
    ├── SkPaint.h                  绘制参数
    ├── SkFont.h                   字体对象
    └── SkTypeface.h               字体实例
```

**样式应用流程**：
1. **构建阶段**：`ParagraphBuilder::pushStyle()` 应用 `TextStyle`
2. **整形阶段**：`equalsByFonts()` 判断是否需要重新整形
3. **布局阶段**：`getFontMetrics()` 计算行高和基线
4. **绘制阶段**：`equals()` 判断是否可以批量绘制

## 主要类与结构体

### TextStyle 类（核心成员）

```cpp
class TextStyle {
private:
    // 颜色与绘制
    SkColor fColor;                             // 文本颜色
    bool fHasForeground;                        // 是否使用前景画刷
    ParagraphPainter::SkPaintOrID fForeground;  // 前景画刷
    bool fHasBackground;                        // 是否使用背景画刷
    ParagraphPainter::SkPaintOrID fBackground;  // 背景画刷

    // 装饰
    Decoration fDecoration;                     // 下划线/删除线/上划线

    // 字体属性
    SkFontStyle fFontStyle;                     // 粗细/宽度/倾斜
    std::vector<SkString> fFontFamilies;        // 字体家族列表
    SkScalar fFontSize;                         // 字号
    SkFont::Edging fEdging;                     // 抗锯齿类型
    bool fSubpixel;                             // 亚像素定位
    SkFontHinting fHinting;                     // 字体提示

    // 度量调整
    SkScalar fHeight;                           // 行高倍数
    bool fHeightOverride;                       // 覆盖字体行高
    SkScalar fBaselineShift;                    // 基线偏移
    bool fHalfLeading;                          // 半行距模式
    SkScalar fLetterSpacing;                    // 字间距
    SkScalar fWordSpacing;                      // 词间距

    // 其他属性
    SkString fLocale;                           // 语言标识符
    TextBaseline fTextBaseline;                 // 基线类型
    sk_sp<SkTypeface> fTypeface;                // 字体实例
    bool fIsPlaceholder;                        // 是否为占位符

    // 高级效果
    std::vector<TextShadow> fTextShadows;       // 阴影列表
    std::vector<FontFeature> fFontFeatures;     // OpenType 特性
    std::optional<FontArguments> fFontArguments; // 字体变体参数
};
```

### 关联结构体

**Decoration**（装饰）
```cpp
struct Decoration {
    TextDecoration fType;              // 装饰类型（下划线/删除线/上划线）
    TextDecorationMode fMode;          // 模式（穿透/间隙）
    SkColor fColor;                    // 装饰颜色
    TextDecorationStyle fStyle;        // 样式（实线/虚线/波浪线）
    SkScalar fThicknessMultiplier;     // 粗细倍数
};
```

**FontFeature**（字体特性）
```cpp
struct FontFeature {
    SkString fName;   // OpenType 特性标签（如 "liga", "kern"）
    int fValue;       // 特性值（通常 0 或 1）
};
```

### 默认值

```cpp
static const std::vector<SkString>* kDefaultFontFamilies =
    new std::vector<SkString>{SkString("sans-serif")};

// 构造函数默认值（隐式）
fColor = SK_ColorWHITE;
fFontSize = 14.0;
fHeight = 1.0;
fEdging = SkFont::Edging::kAntiAlias;
fSubpixel = true;
fHinting = SkFontHinting::kSlight;
```

## 公共 API 函数

### 样式克隆

```cpp
TextStyle TextStyle::cloneForPlaceholder();
```

**功能**：创建用于占位符的简化样式副本。

**实现**：
```cpp
TextStyle result;
result.fColor = fColor;
result.fFontSize = fFontSize;
result.fFontFamilies = fFontFamilies;
result.fDecoration = fDecoration;
result.fHasBackground = fHasBackground;
result.fBackground = fBackground;
result.fHasForeground = fHasForeground;
result.fForeground = fForeground;
result.fHeightOverride = fHeightOverride;
result.fIsPlaceholder = true;  // 标记为占位符
result.fFontFeatures = fFontFeatures;
result.fHalfLeading = fHalfLeading;
result.fBaselineShift = fBaselineShift;
result.fFontArguments = fFontArguments;
return result;
```

**用途**：占位符（如图片、自定义组件）需要保留某些样式属性（如基线偏移）但不需要完整的文本属性。

### 完整相等性比较

```cpp
bool TextStyle::equals(const TextStyle& other) const;
```

**功能**：判断两个样式是否完全相同，用于样式缓存和批量绘制优化。

**比较逻辑**：
1. **占位符检查**：任一为占位符则不相等
2. **逐成员比较**：颜色、字体、间距、装饰等所有属性
3. **向量比较**：阴影数组和字体特性数组的元素级比较

**关键代码片段**：
```cpp
if (fIsPlaceholder || other.fIsPlaceholder) return false;
if (fColor != other.fColor) return false;
if (!(fDecoration == other.fDecoration)) return false;
if (fFontFamilies != other.fFontFamilies) return false;
if (fTextShadows.size() != other.fTextShadows.size()) return false;
for (size_t i = 0; i < fTextShadows.size(); ++i) {
    if (fTextShadows[i] != other.fTextShadows[i]) return false;
}
// ... 所有其他属性
return true;
```

### 字体相等性比较

```cpp
bool TextStyle::equalsByFonts(const TextStyle& that) const;
```

**功能**：判断两个样式在字体相关属性上是否相同，用于决定是否需要重新整形。

**比较属性**：
- 字体样式（粗细/宽度/倾斜）
- 字体家族列表
- 字号
- 字间距、词间距
- 行高
- 基线偏移
- 语言标识符
- 字体特性
- 字体变体参数

**实现**：
```cpp
return !fIsPlaceholder && !that.fIsPlaceholder &&
       fFontStyle == that.fFontStyle &&
       fFontFamilies == that.fFontFamilies &&
       fFontFeatures == that.fFontFeatures &&
       fFontArguments == that.getFontArguments() &&
       nearlyEqual(fLetterSpacing, that.fLetterSpacing) &&
       nearlyEqual(fWordSpacing, that.fWordSpacing) &&
       nearlyEqual(fHeight, that.fHeight) &&
       nearlyEqual(fBaselineShift, that.fBaselineShift) &&
       nearlyEqual(fFontSize, that.fFontSize) &&
       fLocale == that.fLocale;
```

**注意**：使用 `nearlyEqual()` 进行浮点数比较，容忍微小误差。

### 单属性匹配

```cpp
bool TextStyle::matchOneAttribute(StyleType styleType, const TextStyle& other) const;
```

**功能**：按单个属性类别比较样式，用于样式区间的细粒度分割。

**支持的属性类型**：

| StyleType | 比较内容 |
|-----------|---------|
| `kForeground` | 前景颜色或画刷 |
| `kBackground` | 背景画刷 |
| `kShadow` | 阴影数组 |
| `kDecorations` | 文本装饰 |
| `kLetterSpacing` | 字间距 |
| `kWordSpacing` | 词间距 |
| `kFont` | 所有字体相关属性 |
| `kAllAttributes` | 调用 `equals()` |

**实现示例**：
```cpp
switch (styleType) {
    case kForeground:
        return (!fHasForeground && !other.fHasForeground && fColor == other.fColor) ||
               ( fHasForeground &&  other.fHasForeground && fForeground == other.fForeground);

    case kShadow:
        if (fTextShadows.size() != other.fTextShadows.size()) return false;
        for (int32_t i = 0; i < SkToInt(fTextShadows.size()); ++i) {
            if (fTextShadows[i] != other.fTextShadows[i]) return false;
        }
        return true;

    case kFont:
        return fFontStyle == other.fFontStyle &&
               fLocale == other.fLocale &&
               fFontFamilies == other.fFontFamilies &&
               fFontSize == other.fFontSize &&
               fHeight == other.fHeight &&
               fHalfLeading == other.fHalfLeading &&
               fBaselineShift == other.fBaselineShift &&
               fFontArguments == other.fFontArguments;
    // ...
}
```

### 字体度量计算

```cpp
void TextStyle::getFontMetrics(SkFontMetrics* metrics) const;
```

**功能**：计算字体度量，应用行高覆盖和基线偏移。

**实现步骤**：

1. **创建字体对象**：
```cpp
SkFont font(fTypeface, fFontSize);
font.setEdging(fEdging);
font.setSubpixel(fSubpixel);
font.setHinting(fHinting);
font.getMetrics(metrics);
```

2. **应用行高覆盖**：
```cpp
if (fHeightOverride) {
    auto multiplier = fHeight * fFontSize;
    auto height = metrics->fDescent - metrics->fAscent + metrics->fLeading;
    metrics->fAscent = (metrics->fAscent - metrics->fLeading / 2) * multiplier / height;
    metrics->fDescent = (metrics->fDescent + metrics->fLeading / 2) * multiplier / height;
} else {
    metrics->fAscent = (metrics->fAscent - metrics->fLeading / 2);
    metrics->fDescent = (metrics->fDescent + metrics->fLeading / 2);
}
```

3. **应用基线偏移**：
```cpp
metrics->fAscent += fBaselineShift;
metrics->fDescent += fBaselineShift;
```

**度量调整逻辑**：
- **行距分配**：行距（leading）均匀分布到上升部和下降部
- **高度缩放**：按 `fHeight` 倍数缩放总高度
- **基线偏移**：正值下移文本，负值上移文本

### 字体参数设置

```cpp
void TextStyle::setFontArguments(const std::optional<SkFontArguments>& args);
```

**功能**：设置字体变体参数（可变字体轴、调色板等）。

**实现**：
```cpp
if (!args) {
    fFontArguments.reset();  // 清空参数
    return;
}
fFontArguments.emplace(*args);  // 复制参数
```

使用 `std::optional` 表示参数可能不存在。

## 内部实现细节

### 浮点数比较策略

为避免浮点精度问题，使用 `nearlyEqual()` 辅助函数：

```cpp
static inline bool nearlyEqual(SkScalar x, SkScalar y,
                               SkScalar tolerance = SK_ScalarNearlyZero) {
    if (SkIsFinite(x, y)) {
        return SkScalarNearlyEqual(x, y, tolerance);
    }
    // Inf == Inf, 其他情况为 false
    return x == y;
}
```

**特殊处理**：
- 有限值：使用容差比较
- 无穷大：精确相等
- NaN：总是不相等

### 前景/背景绘制的变体处理

`fForeground` 和 `fBackground` 使用 `std::variant`：

```cpp
using SkPaintOrID = std::variant<SkPaint, PaintID>;
```

**比较逻辑**：
```cpp
// 前景比较
return (!fHasForeground && !other.fHasForeground && fColor == other.fColor) ||
       ( fHasForeground &&  other.fHasForeground && fForeground == other.fForeground);
```

**设计考量**：
- 支持自定义绘制器（使用 `PaintID`）
- 默认使用简单颜色（`fColor`）
- 通过 `fHasForeground` 标志区分模式

### 占位符样式的特殊处理

占位符总是被视为不相等：

```cpp
if (fIsPlaceholder || other.fIsPlaceholder) {
    return false;
}
```

**原因**：
- 占位符表示嵌入对象，不是实际文本
- 避免将占位符与普通文本合并处理
- 简化布局和绘制逻辑

### 装饰比较的结构体相等性

```cpp
struct Decoration {
    bool operator==(const Decoration& other) const {
        return this->fType == other.fType &&
               this->fMode == other.fMode &&
               this->fColor == other.fColor &&
               this->fStyle == other.fStyle &&
               this->fThicknessMultiplier == other.fThicknessMultiplier;
    }
};
```

使用结构体自定义运算符简化比较代码。

### 行高计算的数学原理

字体度量调整公式：

```
原始高度 = descent - ascent + leading
目标高度 = fHeight * fFontSize

缩放因子 = 目标高度 / 原始高度

调整后的 ascent = (ascent - leading/2) * 缩放因子
调整后的 descent = (descent + leading/2) * 缩放因子
```

**说明**：
- 行距均匀分布到上下（`leading/2`）
- 保持字符中心不变
- 确保总高度等于 `fHeight * fFontSize`

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkColor.h"                      // 颜色类型
#include "include/core/SkFontStyle.h"                  // 字体样式
#include "modules/skparagraph/include/TextStyle.h"     // 类声明
```

### 组件依赖

- `TextShadow` - 阴影效果
- `FontArguments` - 字体变体参数
- `FontFeature` - OpenType 特性
- `Decoration` - 文本装饰

### 被依赖关系

```
TextStyle.cpp 被以下模块使用：
├── ParagraphBuilder.cpp    应用文本样式
├── ParagraphImpl.cpp       段落布局和整形
├── TextLine.cpp            文本行绘制
├── ParagraphCache.cpp      样式缓存
└── SkShaper_harfbuzz.cpp   文本整形（字体属性）
```

## 设计模式与设计决策

### 值对象模式

`TextStyle` 是不可变值对象（按惯例）：

```cpp
TextStyle style;
style.setColor(SK_ColorBLACK);  // 构建阶段修改
// 使用后不再修改
```

**优势**：
- 简化并发安全性
- 适合用作缓存键
- 支持按值传递和复制

### 多级相等性判断

提供三种相等性检查：

1. **完全相等**（`equals()`）：用于批量绘制
2. **字体相等**（`equalsByFonts()`）：用于文本整形
3. **单属性相等**（`matchOneAttribute()`）：用于样式分割

**设计理由**：
- 避免不必要的重新整形（字体未变时）
- 支持细粒度样式优化
- 平衡性能和灵活性

### 可选属性模式

使用标志位和可选类型表示可选属性：

```cpp
bool fHasForeground;
ParagraphPainter::SkPaintOrID fForeground;

std::optional<FontArguments> fFontArguments;
```

**替代方案**：
- 使用空值对象（如空 `SkPaint`）- 不明确
- 总是存储所有属性 - 浪费内存

### 近似相等策略

字体相关比较使用近似相等：

```cpp
nearlyEqual(fLetterSpacing, that.fLetterSpacing)
```

**权衡**：
- **优点**：容忍浮点舍入误差，避免不必要的重新整形
- **缺点**：可能遗漏真实差异（极罕见）

完全相等比较使用精确相等，确保缓存正确性。

## 性能考量

### 比较优化

`equals()` 使用短路求值：

```cpp
if (fColor != other.fColor) return false;  // 最可能不同
if (!(fDecoration == other.fDecoration)) return false;
if (fFontFamilies != other.fFontFamilies) return false;
// ... 继续检查更复杂的属性
```

**策略**：先比较简单属性，避免不必要的深度比较。

### 字体度量缓存

`getFontMetrics()` 涉及昂贵的字体查询：

```cpp
SkFont font(fTypeface, fFontSize);
font.getMetrics(metrics);  // 可能访问字体文件
```

**优化**：调用方应缓存度量结果，避免重复计算。

### 向量比较开销

阴影和字体特性的比较是 O(n)：

```cpp
for (size_t i = 0; i < fTextShadows.size(); ++i) {
    if (fTextShadows[i] != other.fTextShadows[i]) return false;
}
```

**缓解策略**：
- 大多数文本使用 0-2 个阴影
- 提前检查向量大小（O(1) 操作）

### 内存占用

```cpp
sizeof(TextStyle) ≈ 200-300 字节
```

**组成**：
- 基本类型：约 100 字节
- 向量（空时）：约 72 字节（3 个向量 * 24 字节）
- 智能指针：8 字节
- 可选类型：约 50 字节

**优化考量**：频繁创建时考虑对象池或共享样式。

## 相关文件

### 接口定义
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextStyle.h` - 类声明和文档

### 依赖组件
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextShadow.h` - 阴影定义
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/FontArguments.h` - 字体参数
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/DartTypes.h` - 枚举类型

### 核心使用
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/ParagraphImpl.cpp` - 段落实现
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/TextLine.cpp` - 文本行绘制
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/ParagraphBuilderImpl.cpp` - 样式应用

### 底层依赖
- `/Users/yuanlin/workspace/skia/include/core/SkFont.h` - 字体对象
- `/Users/yuanlin/workspace/skia/include/core/SkPaint.h` - 绘制参数
- `/Users/yuanlin/workspace/skia/include/core/SkTypeface.h` - 字体实例

### 测试文件
- `/Users/yuanlin/workspace/skia/modules/skparagraph/tests/ParagraphTest.cpp` - 段落测试
- `/Users/yuanlin/workspace/skia/modules/skparagraph/tests/TextStyleTest.cpp` - 样式测试
