# ParagraphBuilder

> 源文件: [modules/skparagraph/include/ParagraphBuilder.h](../../../../modules/skparagraph/include/ParagraphBuilder.h)

## 概述

`ParagraphBuilder` 是 Skia 段落排版模块的构建器接口，提供了一种流式 API 来构建 `Paragraph` 对象。客户端通过推入/弹出文本样式、添加文本和占位符等操作逐步构建段落内容，最后调用 `Build()` 生成可用于布局和渲染的 `Paragraph` 实例。该类是段落构建的入口点，封装了文本样式栈管理和 Unicode 处理的复杂性。

## 架构位置

```
skia::textlayout 命名空间
  ParagraphBuilder (抽象接口)  ← 本文件定义
    └── ParagraphBuilderImpl (内部实现)
          ├── 使用 FontCollection 管理字体
          ├── 使用 SkUnicode 进行文本分析
          └── Build() → Paragraph (ParagraphImpl)
```

`ParagraphBuilder` 是客户端创建段落的唯一入口，通过静态工厂方法 `make()` 创建实现实例。

## 主要类与结构体

### ParagraphBuilder
- 抽象基类，定义段落构建的公共接口
- 受保护的默认构造函数，仅通过 `make()` 工厂方法创建
- 管理文本样式栈、文本内容和占位符

## 公共 API 函数

### 样式管理
```cpp
virtual void pushStyle(const TextStyle& style) = 0;
```
将文本样式压入栈。后续添加的文本将使用栈顶样式。

```cpp
virtual void pop() = 0;
```
弹出栈顶样式，恢复到之前的样式。

```cpp
virtual TextStyle peekStyle() = 0;
```
查看当前栈顶样式（不弹出）。

### 文本添加
```cpp
virtual void addText(const std::u16string& text) = 0;
virtual void addText(const char* text) = 0;
virtual void addText(const char* text, size_t len) = 0;
```
添加文本内容，支持 UTF-16 和 UTF-8 两种编码。文本将使用当前栈顶样式。

### 占位符
```cpp
virtual void addPlaceholder(const PlaceholderStyle& placeholderStyle) = 0;
```
添加占位符，在文本中预留空间供 Flutter 等框架插入自定义内容。内部添加一个对象替换字符（U+FFFC）。

### 构建
```cpp
virtual std::unique_ptr<Paragraph> Build() = 0;
```
构建并返回一个 `Paragraph` 对象，可用于布局（`layout`）和绘制（`paint`）。

### 查询
```cpp
virtual SkSpan<char> getText() = 0;
virtual const ParagraphStyle& getParagraphStyle() const = 0;
```
获取当前累积的文本内容和段落样式。

### 重置
```cpp
virtual void Reset() = 0;
```
重置构建器到初始状态，清除所有文本、样式和占位符，但保留初始的 `ParagraphStyle`。

### 工厂方法
```cpp
static std::unique_ptr<ParagraphBuilder> make(const ParagraphStyle& style,
                                              sk_sp<FontCollection> fontCollection,
                                              sk_sp<SkUnicode> unicode);
```
静态工厂方法，创建一个新的 `ParagraphBuilder` 实例。

### Client Unicode 支持（条件编译）
```cpp
virtual void setWordsUtf8(std::vector<SkUnicode::Position> wordsUtf8) = 0;
virtual void setWordsUtf16(std::vector<SkUnicode::Position> wordsUtf16) = 0;
virtual void setGraphemeBreaksUtf8(...) = 0;
virtual void setGraphemeBreaksUtf16(...) = 0;
virtual void setLineBreaksUtf8(...) = 0;
virtual void setLineBreaksUtf16(...) = 0;
virtual std::tuple<...> getClientICUData() const = 0;
virtual void SetUnicode(sk_sp<SkUnicode> unicode) = 0;
```
在 `SK_UNICODE_CLIENT_IMPLEMENTATION` 宏启用时可用，允许客户端直接提供 Unicode 分词、字素边界和换行信息，而非依赖内置的 ICU 库。

## 内部实现细节

### 样式栈机制

`ParagraphBuilder` 使用栈（stack）管理文本样式。`pushStyle` 将新样式压入栈，`addText` 使用栈顶样式格式化文本，`pop` 恢复到之前的样式。这种设计支持嵌套样式（如在粗体文本中嵌入斜体）。

### 占位符字符

`addPlaceholder` 在文本流中插入 Unicode 对象替换字符 U+FFFC，该字符在排版时被替换为指定尺寸的占位空间。

### Client Unicode 模式

条件编译块 `#if !defined(SK_DISABLE_LEGACY_CLIENT_UNICODE) && defined(SK_UNICODE_CLIENT_IMPLEMENTATION)` 提供了一种替代方案，允许在没有 ICU 库的环境中工作。客户端需要预先计算好分词、字素和换行信息并传入。

## 依赖关系

- **skparagraph 模块**: `FontCollection`、`Paragraph`、`ParagraphStyle`、`TextStyle`
- **skunicode 模块**: `SkUnicode`（Unicode 文本处理）
- **标准库**: `<memory>`、`<stack>`、`<string>`、`<tuple>`、`<vector>`

## 设计模式与设计决策

1. **建造者模式（Builder Pattern）**: 经典的建造者模式实现，将复杂对象（`Paragraph`）的构建过程封装在 `ParagraphBuilder` 中，提供逐步构建的流式 API。

2. **工厂方法模式**: `make()` 静态方法隐藏了具体实现类的创建细节，客户端仅依赖抽象接口。

3. **样式栈设计**: 使用栈管理文本样式，支持直观的嵌套样式语义，与 Flutter 的 `TextSpan` 树结构自然对应。

4. **编码兼容性**: 同时提供 UTF-8 和 UTF-16 的文本输入接口，兼容不同平台的文本表示需求（如 Java/Flutter 使用 UTF-16，C/Unix 使用 UTF-8）。

5. **可选 Unicode 依赖**: 通过条件编译支持 Client Unicode 模式，降低了对 ICU 库的硬依赖，适用于嵌入式环境。

## 性能考量

- `pushStyle`/`pop` 为栈操作，O(1) 时间复杂度。
- `addText` 的复杂度与文本长度成正比。
- `Build()` 是计算密集型操作，涉及文本分析和样式合并。
- `Reset()` 允许复用 `ParagraphBuilder` 实例，避免重复创建和销毁的开销。

## 相关文件

- `modules/skparagraph/src/ParagraphBuilderImpl.h` - 实际实现类
- `modules/skparagraph/include/Paragraph.h` - 段落抽象接口
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式
- `modules/skparagraph/include/TextStyle.h` - 文本样式（含 PlaceholderStyle）
- `modules/skparagraph/include/FontCollection.h` - 字体集合
- `modules/skunicode/include/SkUnicode.h` - Unicode 处理接口
