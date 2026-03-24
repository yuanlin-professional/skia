# Iterators (LangIterator)

> 源文件: modules/skparagraph/src/Iterators.h

## 概述

`Iterators.h` 定义了段落排版系统中用于遍历文本属性的迭代器类。其中最主要的是 `LangIterator`（语言迭代器），它实现了 `SkShaper::LanguageRunIterator` 接口，用于在文本整形（text shaping）过程中迭代文本的语言区间（language runs）。该迭代器将文本分割成具有相同语言属性的连续片段，使整形引擎能够针对不同语言应用正确的排版规则。

语言标识符（locale）对文本整形至关重要，因为不同语言即使使用相同字符也可能有不同的排版规则。例如，日文和中文共享许多汉字，但标点符号的处理方式不同；土耳其语的字母大小写转换规则与英语不同。`LangIterator` 通过与 `TextStyle` 系统集成，确保文本的每个部分都使用正确的语言上下文进行处理。

## 架构位置

`LangIterator` 在 Skia 文本渲染管线中的位置：

```
Skia 文本处理流程
├── modules/skparagraph/            段落模块
│   ├── include/
│   │   ├── Paragraph.h            段落接口
│   │   └── TextStyle.h            文本样式（包含 locale）
│   └── src/
│       ├── Iterators.h            本文件（语言迭代器）
│       ├── ParagraphImpl.cpp      使用迭代器进行整形
│       └── TextLine.cpp           文本行处理
├── modules/skshaper/               文本整形模块
│   ├── include/
│   │   └── SkShaper.h             整形器接口（定义 LanguageRunIterator）
│   └── src/
│       └── SkShaper_harfbuzz.cpp  HarfBuzz 整形实现
└── third_party/harfbuzz/           HarfBuzz 库（底层整形引擎）
```

**数据流**：
1. `ParagraphImpl` 创建 `LangIterator` 并传入文本和样式
2. `SkShaper` 调用迭代器获取当前语言区间
3. HarfBuzz 根据语言标识符选择正确的排版特性
4. 迭代器推进到下一个语言区间，重复过程

## 主要类与结构体

### LangIterator 类

```cpp
class LangIterator final : public SkShaper::LanguageRunIterator {
public:
    LangIterator(SkSpan<const char> utf8,
                 SkSpan<Block> styles,
                 const TextStyle& defaultStyle);

    void consume() override;
    size_t endOfCurrentRun() const override;
    bool atEnd() const override;
    const char* currentLanguage() const override;

private:
    SkSpan<const char> fText;        // UTF-8 文本数据
    SkSpan<Block> fTextStyles;       // 文本样式块数组
    const char* fCurrentChar;        // 当前字符位置
    Block* fCurrentStyle;            // 当前样式块
    SkString fCurrentLocale;         // 当前语言标识符
};
```

**成员变量说明**：
- `fText`: 指向 UTF-8 编码的文本缓冲区（不拥有内存）
- `fTextStyles`: 样式块数组，每个块定义一个文本区间的样式
- `fCurrentChar`: 指向当前区间结束位置的字符指针
- `fCurrentStyle`: 指向当前正在处理的样式块
- `fCurrentLocale`: 当前区间的语言标识符（如 "en-US", "zh-CN"）

### Block 结构体（关联类型）

```cpp
struct Block {
    TextRange fRange;    // 文本区间 [start, end)
    TextStyle fStyle;    // 该区间的文本样式
};
```

`Block` 定义在 `TextStyle.h` 中，表示具有统一样式的文本片段。

## 公共 API 函数

### 构造函数

```cpp
LangIterator(SkSpan<const char> utf8,
             SkSpan<Block> styles,
             const TextStyle& defaultStyle)
    : fText(utf8)
    , fTextStyles(styles)
    , fCurrentChar(utf8.data())
    , fCurrentStyle(fTextStyles.data())
    , fCurrentLocale(defaultStyle.getLocale()) {}
```

**参数**：
- `utf8`: UTF-8 编码的文本数据（使用 `SkSpan` 避免拷贝）
- `styles`: 样式块数组，必须按起始位置排序且覆盖整个文本
- `defaultStyle`: 默认文本样式，用于获取初始语言标识符

**前置条件**：
- `styles` 数组不能为空
- 样式块的范围必须连续且覆盖整个 `utf8` 文本

### consume() - 推进迭代器

```cpp
void consume() override {
    const char* textEnd = fText.data() + fText.size();
    const Block* stylesEnd = fTextStyles.data() + fTextStyles.size();

    SkASSERT(fCurrentChar < textEnd);

    if (fCurrentStyle == stylesEnd) {
        fCurrentChar = textEnd;
        return;
    }

    fCurrentChar = fText.data() + fCurrentStyle->fRange.end;
    fCurrentLocale = fCurrentStyle->fStyle.getLocale();

    while (++fCurrentStyle != stylesEnd && !fCurrentStyle->fStyle.isPlaceholder()) {
        if (fCurrentStyle->fStyle.getLocale() != fCurrentLocale) {
            break;
        }
        fCurrentChar = fText.data() + fCurrentStyle->fRange.end;
    }
}
```

**功能**：将迭代器推进到下一个语言区间。

**处理逻辑**：
1. **检查边界**：如果已到达样式数组末尾，跳转到文本末尾
2. **更新位置**：移动到当前样式块的结束位置
3. **提取语言**：保存当前样式的语言标识符
4. **合并相邻区间**：继续推进，合并具有相同语言且非占位符的样式块

**占位符处理**：占位符（placeholder）被视为区间边界，因为它们不是实际文本。

### endOfCurrentRun() - 获取区间结束位置

```cpp
size_t endOfCurrentRun() const override {
    return fCurrentChar - fText.data();
}
```

**返回值**：当前语言区间结束位置的字节偏移量（相对于文本起始）。

### atEnd() - 检查是否结束

```cpp
bool atEnd() const override {
    return fCurrentChar >= fText.data() + fText.size();
}
```

**返回值**：如果迭代器已到达文本末尾返回 `true`。

### currentLanguage() - 获取当前语言

```cpp
const char* currentLanguage() const override {
    return fCurrentLocale.c_str();
}
```

**返回值**：当前区间的语言标识符 C 字符串指针（如 "en-US"）。

## 内部实现细节

### 语言区间合并算法

`consume()` 方法的核心逻辑是合并相邻的相同语言区间：

```cpp
while (++fCurrentStyle != stylesEnd && !fCurrentStyle->fStyle.isPlaceholder()) {
    if (fCurrentStyle->fStyle.getLocale() != fCurrentLocale) {
        break;  // 遇到不同语言，停止合并
    }
    fCurrentChar = fText.data() + fCurrentStyle->fRange.end;
}
```

**合并条件**：
1. 样式块的语言标识符相同
2. 样式块不是占位符
3. 未到达样式数组末尾

**示例**：
```
文本: "Hello 世界"
样式块:
  [0-5):   locale="en", color=red
  [5-6):   locale="en", color=blue    ← 合并
  [6-11):  locale="zh-CN", color=red

结果区间:
  [0-6):   locale="en"
  [6-11):  locale="zh-CN"
```

### 占位符的特殊处理

占位符表示嵌入对象（如图片、自定义小部件），不需要文本整形：

```cpp
if (fCurrentStyle->fStyle.isPlaceholder()) {
    break;  // 占位符结束当前语言区间
}
```

这确保占位符被视为独立区间，不会与周围文本合并。

### 迭代器状态转换

```
初始状态:
  fCurrentChar = fText.data()
  fCurrentStyle = fTextStyles.data()
  fCurrentLocale = defaultStyle.getLocale()

调用 consume():
  ┌─────────────────────────────────┐
  │ 更新 fCurrentChar 到区间结束    │
  │ 提取 fCurrentLocale             │
  │ 合并相同语言的连续样式块         │
  └─────────────────────────────────┘

终止状态:
  fCurrentChar = fText.data() + fText.size()
  fCurrentStyle = stylesEnd
```

### 边界检查与断言

```cpp
SkASSERT(fCurrentChar < textEnd);  // 确保在有效范围内
```

使用断言而非异常处理，遵循 Skia 的设计哲学（调试构建检查，发布构建信任）。

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkSpan.h"                        // 非拥有性数组视图
#include "include/core/SkString.h"                      // 字符串类
#include "include/core/SkTypes.h"                       // SkASSERT 等宏
#include "modules/skparagraph/include/TextStyle.h"      // Block, TextStyle
#include "modules/skshaper/include/SkShaper.h"          // LanguageRunIterator 接口
```

### 接口继承

```cpp
class LangIterator : public SkShaper::LanguageRunIterator
```

实现 `SkShaper` 定义的迭代器接口，使其能够与 HarfBuzz 整形引擎集成。

### 被依赖关系

```
Iterators.h 被以下模块使用：
├── ParagraphImpl.cpp       创建语言迭代器进行文本整形
├── TextLine.cpp            文本行布局时使用
└── SkShaper_harfbuzz.cpp   整形引擎调用迭代器
```

## 设计模式与设计决策

### 迭代器模式

`LangIterator` 是标准迭代器模式的实现：

```cpp
LangIterator iter(text, styles, defaultStyle);
while (!iter.atEnd()) {
    const char* locale = iter.currentLanguage();
    size_t end = iter.endOfCurrentRun();
    // 处理区间 [start, end) 使用语言 locale
    iter.consume();
}
```

**优势**：
- 隐藏内部复杂性（样式块合并逻辑）
- 统一接口，支持多种迭代器类型（语言、脚本、字体）
- 延迟计算，避免预先分割文本

### 非拥有性引用（SkSpan）

使用 `SkSpan<const char>` 和 `SkSpan<Block>` 而非 `std::vector`：

```cpp
SkSpan<const char> fText;       // 不拷贝文本数据
SkSpan<Block> fTextStyles;      // 不拷贝样式数组
```

**优势**：
- 零拷贝，高效传递大型数据
- 明确表达生命周期（数据必须在迭代器使用期间有效）
- 避免不必要的内存分配

### 语言区间合并策略

合并相邻相同语言的样式块：

```
优点:
  - 减少整形引擎的调用次数
  - 优化连字和字形替换（跨样式块边界）

缺点:
  - 增加迭代器复杂性
  - 假设语言是主要的整形边界（而非字体或字号）
```

这是基于实践的权衡：语言差异对整形的影响通常大于样式差异。

### 占位符隔离

将占位符视为区间边界：

```cpp
if (fCurrentStyle->fStyle.isPlaceholder()) {
    break;
}
```

**理由**：
- 占位符不需要文本整形
- 避免整形引擎处理非文本对象
- 简化布局逻辑

## 性能考量

### 时间复杂度

- **构造**：O(1) - 仅初始化指针
- **consume()**：O(k) - k 为连续相同语言的样式块数（通常很小）
- **整体遍历**：O(n) - n 为样式块总数

### 空间复杂度

```cpp
sizeof(LangIterator) = sizeof(SkSpan) * 2 + sizeof(char*) * 2 + sizeof(SkString)
                     ≈ 16 + 16 + 32 = 64 字节
```

**特点**：
- 轻量级对象，适合栈分配
- 不分配堆内存（除 `SkString` 的小字符串优化）

### 缓存友好性

迭代器按顺序访问样式块数组：

```cpp
while (++fCurrentStyle != stylesEnd) { ... }
```

这是理想的缓存访问模式，CPU 可以有效预取数据。

### 优化策略

**快速路径**：大多数文本使用单一语言，迭代器会快速跳过：

```cpp
// 常见情况：整个段落使用同一语言
LangIterator iter(...);
// 第一次 consume() 可能直接到达末尾
iter.consume();  // 合并所有样式块
if (iter.atEnd()) {
    // 单次整形调用处理整个文本
}
```

**占位符跳过**：通过提前检查 `isPlaceholder()` 避免无效合并。

## 相关文件

### 接口定义
- `/Users/yuanlin/workspace/skia/modules/skshaper/include/SkShaper.h` - `LanguageRunIterator` 基类

### 相关迭代器
- `/Users/yuanlin/workspace/skia/modules/skshaper/src/SkShaper_harfbuzz.cpp` - 脚本迭代器、双向文本迭代器

### 使用场景
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/ParagraphImpl.cpp` - 段落布局使用迭代器
- `/Users/yuanlin/workspace/skia/modules/skparagraph/src/TextLine.cpp` - 文本行整形

### 依赖类型
- `/Users/yuanlin/workspace/skia/modules/skparagraph/include/TextStyle.h` - `Block` 和 `TextStyle` 定义
- `/Users/yuanlin/workspace/skia/include/core/SkSpan.h` - 非拥有性数组视图

### 整形引擎
- `/Users/yuanlin/workspace/skia/third_party/harfbuzz/` - HarfBuzz 文本整形库
- `/Users/yuanlin/workspace/skia/modules/skshaper/src/SkShaper_coretext.cpp` - CoreText 整形后端（macOS/iOS）

### 测试文件
- `/Users/yuanlin/workspace/skia/modules/skparagraph/tests/ParagraphTest.cpp` - 段落测试（包含多语言测试）
