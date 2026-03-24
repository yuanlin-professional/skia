# ParagraphBuilderImpl

> 源文件: modules/skparagraph/src/ParagraphBuilderImpl.h, modules/skparagraph/src/ParagraphBuilderImpl.cpp

## 概述

`ParagraphBuilderImpl` 是 Skia 段落模块中 `ParagraphBuilder` 接口的核心实现,负责段落构建过程的全部逻辑。它采用构建器模式(Builder Pattern),允许用户逐步添加文本内容、应用样式、插入占位符,最终构建出可以进行布局和渲染的 `Paragraph` 对象。该类管理文本缓冲区、样式栈、样式块范围、占位符信息以及 UTF-8/UTF-16 编码映射,是段落 API 的入口点和核心协调者。

## 架构位置

`ParagraphBuilderImpl` 在段落模块的架构中处于关键位置,连接公共 API 和内部实现:

```
用户代码
    ↓
ParagraphBuilder (接口)
    ↓
ParagraphBuilderImpl (本类)
    ├→ 管理 TextStyle 栈
    ├→ 管理 Block 范围
    ├→ 管理 Placeholder
    ├→ 持有 FontCollection
    ├→ 持有 SkUnicode
    └→ 构建 ParagraphImpl
         ├→ OneLineShaper (文本整形)
         ├→ TextWrapper (换行)
         └→ TextLine (行布局)
```

该类是段落构建阶段的协调者,收集所有必要信息后将其传递给 `ParagraphImpl` 进行布局计算。它不负责布局或渲染,仅负责数据收集和组织。

## 主要类与结构体

### ParagraphBuilderImpl 核心成员

```cpp
class ParagraphBuilderImpl : public ParagraphBuilder {
    SkString fUtf8;                                     // UTF-8 文本缓冲区
    skia_private::STArray<4, TextStyle, true> fTextStyles;  // 样式栈
    skia_private::STArray<4, Block, true> fStyledBlocks;    // 样式块
    skia_private::STArray<4, Placeholder, true> fPlaceholders; // 占位符
    sk_sp<FontCollection> fFontCollection;              // 字体集合
    ParagraphStyle fParagraphStyle;                     // 段落样式
    sk_sp<SkUnicode> fUnicode;                         // Unicode 处理器
};
```

核心数据成员说明:
- **fUtf8**: 存储所有添加的文本,使用 UTF-8 编码。所有文本操作最终都追加到这个缓冲区
- **fTextStyles**: 样式栈,支持嵌套样式的 push/pop 操作。栈顶样式应用于后续添加的文本
- **fStyledBlocks**: 记录每个样式块的文本范围和对应的样式。一个样式块表示一段具有相同样式的连续文本
- **fPlaceholders**: 占位符列表,用于在文本中插入非文本元素(如图像、视频)
- **fFontCollection**: 字体集合,提供字体查询和回退功能
- **fUnicode**: Unicode 处理器,用于文本分段、断行等操作

### Block 结构

```cpp
struct Block {
    TextRange fRange;     // 文本范围(UTF-8 索引)
    TextStyle fStyle;     // 应用于该范围的样式
};
```

表示一个连续的样式范围,所有位于 `fRange` 内的文本共享相同的 `fStyle`。

### Placeholder 结构

```cpp
struct Placeholder {
    size_t fStart, fEnd;              // 占位符在文本中的位置
    PlaceholderStyle fStyle;          // 占位符样式(尺寸、对齐等)
    TextStyle fTextStyle;             // 相关的文本样式
    BlockRange fBlocksBefore;         // 占位符之前的样式块范围
    TextRange fRange;                 // 占位符表示的文本范围
};
```

占位符用 Unicode 字符 `0xFFFC` (对象替换字符) 表示,允许在文本流中嵌入非文本内容。

## 公共 API 函数

### 构造与工厂方法

```cpp
ParagraphBuilderImpl(const ParagraphStyle& style,
                     sk_sp<FontCollection> fontCollection,
                     sk_sp<SkUnicode> unicode);
```
构造函数,初始化段落样式、字体集合和 Unicode 处理器。自动启动第一个样式块。

```cpp
static std::unique_ptr<ParagraphBuilder> make(...);
```
工厂方法,创建 `ParagraphBuilderImpl` 实例。推荐使用该方法而非直接构造。

### 样式管理

```cpp
void pushStyle(const TextStyle& style) override;
```
将样式压入栈,后续添加的文本将使用该样式。如果新样式与当前样式块相同,则复用现有块;否则创建新块。

```cpp
void pop() override;
```
从样式栈中弹出最顶层样式,恢复到之前的样式。如果栈为空,使用段落样式的默认文本样式。

```cpp
TextStyle peekStyle() override;
```
查看当前样式(栈顶样式或默认样式),不修改栈状态。

### 文本添加

```cpp
void addText(const std::u16string& text) override;
void addText(const char* text) override;
void addText(const char* text, size_t len) override;
```
添加文本到构建器。UTF-16 版本会自动转换为 UTF-8。所有文本都追加到 `fUtf8` 缓冲区,并使用当前栈顶样式。

### 占位符

```cpp
void addPlaceholder(const PlaceholderStyle& placeholderStyle) override;
```
在当前位置插入占位符,用于嵌入图像、视频等非文本元素。内部会添加 Unicode 对象替换字符 `0xFFFC`。

### 构建

```cpp
std::unique_ptr<Paragraph> Build() override;
```
完成构建过程,返回可用于布局和渲染的 `Paragraph` 对象。内部调用 `finalize()` 完成样式块,然后创建 `ParagraphImpl` 实例。

### 辅助方法

```cpp
SkSpan<char> getText() override;
const ParagraphStyle& getParagraphStyle() const override;
void Reset() override;
```
- `getText()`: 获取当前文本内容的只读视图
- `getParagraphStyle()`: 获取段落样式
- `Reset()`: 重置构建器状态,允许复用实例构建新段落(Flutter 优化)

## 内部实现细节

### 样式栈机制

样式栈实现了样式的嵌套和恢复:
```cpp
void pushStyle(const TextStyle& style) {
    fTextStyles.push_back(style);
    if (当前块可以复用) {
        // 样式相同,继续使用当前块
    } else {
        startStyledBlock();  // 创建新块
    }
}
```

`pop()` 操作移除栈顶样式并创建新的样式块,确保后续文本使用正确的样式。

### 样式块管理

样式块按照文本添加顺序线性排列:
```cpp
void startStyledBlock() {
    endRunIfNeeded();  // 结束当前块
    fStyledBlocks.emplace_back(fUtf8.size(), fUtf8.size(), internalPeekStyle());
}
```

每次样式变化时,当前块的结束位置被设置为当前文本长度,然后创建新块。

### 占位符处理

占位符插入涉及多步操作:
1. 结束当前样式块
2. 记录占位符之前的样式块范围和文本范围
3. 创建特殊样式并添加 `0xFFFC` 字符
4. 恢复原样式
5. 创建 `Placeholder` 对象记录所有信息

### UTF-8/UTF-16 映射

为支持客户端 Unicode 实现,构建器维护 UTF-8 和 UTF-16 索引的双向映射:
```cpp
void ensureUTF16Mapping() {
    fillUTF16MappingOnce([&] {
        SkUnicode::extractUtfConversionMapping(...);
    });
}
```

映射在首次需要时延迟构建,使用 `SkOnce` 确保只构建一次。

### finalize() 过程

`finalize()` 在构建前调用,完成最后的样式块:
```cpp
void finalize() {
    if (!fUtf8.isEmpty()) {
        this->endRunIfNeeded();  // 关闭最后一个样式块
    }
    fTextIsFinalized = true;  // 标记为已完成
}
```

此后不允许再添加文本或样式。

### Build() 流程

```cpp
std::unique_ptr<Paragraph> Build() {
    finalize();                              // 1. 完成样式块
    addPlaceholder(PlaceholderStyle(), true); // 2. 添加虚拟占位符
    return std::make_unique<ParagraphImpl>(   // 3. 创建 ParagraphImpl
        fUtf8, fParagraphStyle, fStyledBlocks, fPlaceholders,
        fFontCollection, fUnicode);
}
```

虚拟占位符用于统一处理边界情况,简化 `ParagraphImpl` 的逻辑。

## 依赖关系

### Skia 核心依赖
- **SkString**: 文本缓冲区
- **SkUnicode**: Unicode 处理(断行、分词、字素簇分割)
- **SkRefCnt / sk_sp**: 智能指针和引用计数

### 段落模块依赖
- **ParagraphStyle / TextStyle**: 样式定义
- **FontCollection**: 字体管理
- **ParagraphImpl**: 段落实现类(构建目标)
- **Block / Placeholder**: 数据结构定义

### 容器
- **skia_private::STArray**: 小型优化数组,避免小数据的堆分配
- **std::vector**: 用于客户端 ICU 数据

## 设计模式与设计决策

### 构建器模式

`ParagraphBuilderImpl` 是典型的构建器模式实现:
- **分步构建**: 通过多次 `addText()` / `pushStyle()` / `pop()` 调用逐步构建复杂对象
- **流畅接口**: 支持链式调用(虽然未返回 `this`)
- **延迟构建**: 实际的 `Paragraph` 对象只在 `Build()` 时创建

### 栈式样式管理

使用栈管理嵌套样式,这是文档编辑器的常见模式:
```cpp
builder.pushStyle(bold);
builder.addText("Bold ");
builder.pushStyle(italic);
builder.addText("Bold+Italic");
builder.pop();
builder.addText(" Bold");
builder.pop();
```

这种设计直观且易于实现复杂的嵌套样式。

### 小型优化数组 (STArray)

使用 `STArray<4, ...>` 为小型数据提供栈上存储,避免堆分配:
```cpp
skia_private::STArray<4, TextStyle, true> fTextStyles;
```

大多数段落的样式嵌套深度不超过 4 层,这个优化避免了频繁的小内存分配。

### 延迟映射构建

UTF-8/UTF-16 映射只在需要时构建,使用 `SkOnce` 确保线程安全的单次初始化。这避免了不必要的计算开销。

### 设计决策

1. **UTF-8 内部存储**: 所有文本以 UTF-8 存储,提供紧凑的内存表示和与 Skia 其他部分的兼容性。

2. **样式块而非字符样式**: 使用范围-样式对而非为每个字符存储样式,大幅减少内存占用。

3. **不可变构建**: `finalize()` 后不允许修改,确保状态一致性并简化并发处理。

4. **客户端 ICU 支持**: 通过条件编译支持客户端提供的 Unicode 数据,允许使用自定义断行/分词规则。

5. **Reset() 复用**: 支持重置和复用构建器实例,这是 Flutter 的性能优化需求,避免频繁创建/销毁对象。

## 性能考量

### 内存分配

- **STArray 优化**: 小型数据使用栈分配,避免堆开销
- **SkString 预分配**: `SkString` 自动管理容量,减少重分配
- **延迟映射**: UTF-8/UTF-16 映射仅在需要时构建

### 时间复杂度

- **pushStyle() / pop()**: O(1) 栈操作
- **addText()**: O(n) 其中 n 是添加的文本长度,仅涉及字符串追加
- **Build()**: O(m) 其中 m 是总文本长度,需要拷贝数据到 `ParagraphImpl`

### 样式块优化

连续相同样式的文本合并为一个块:
```cpp
if (fStyledBlocks.back().fStyle == style) {
    // 复用现有块,无需创建新块
}
```

这减少了样式块数量,提高后续布局性能。

### 复用优化

`Reset()` 方法允许复用构建器实例:
```cpp
builder.Reset();  // 清空状态
// 可以构建新段落
```

这在循环构建多个段落时避免了对象创建/销毁开销,是 Flutter 框架的关键优化。

## 相关文件

### 接口定义
- `modules/skparagraph/include/ParagraphBuilder.h`: 抽象接口
- `modules/skparagraph/include/TextStyle.h`: 文本样式定义
- `modules/skparagraph/include/ParagraphStyle.h`: 段落样式定义

### 实现文件
- `modules/skparagraph/src/ParagraphImpl.h/cpp`: 段落实现(构建目标)
- `modules/skparagraph/src/OneLineShaper.h/cpp`: 文本整形
- `modules/skparagraph/src/TextWrapper.h/cpp`: 文本换行

### 依赖模块
- `modules/skparagraph/include/FontCollection.h`: 字体管理
- `modules/skunicode/include/SkUnicode.h`: Unicode 处理
- `include/private/base/SkOnce.h`: 单次初始化原语

### 测试文件
- `modules/skparagraph/tests/ParagraphTest.cpp`: 单元测试
- `modules/skparagraph/slides/ParagraphSlide.cpp`: 视觉测试

该类是段落模块的核心入口,理解其实现对于掌握整个段落系统至关重要。它的设计体现了构建器模式的优雅和实用性,同时包含了多项性能优化措施。
