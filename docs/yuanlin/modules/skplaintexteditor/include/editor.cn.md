# Editor - Skia 纯文本编辑器核心类

> 源文件: `modules/skplaintexteditor/include/editor.h`

## 概述

`editor.h` 定义了 `SkPlainTextEditor::Editor` 类，这是 Skia 纯文本编辑器模块的核心接口。该类提供了完整的文本编辑功能，包括文本插入/删除、光标移动（字符级、词级、行级）、选择和复制、文本渲染以及位置查询。`Editor` 管理一个按段落（硬换行）组织的文本行集合，每行独立进行文本 shaping 和布局。

## 架构位置

`Editor` 是 `skplaintexteditor` 模块的核心类，位于模块的公共接口层。它向上为应用层（`editor_application.cpp`）提供编辑操作 API，向下依赖 `StringSlice` 进行文本存储、`SkShaper` 进行文本排版、`SkTextBlob` 进行渲染。该类同时扮演 Model（文本数据管理）和部分 Controller（光标移动逻辑）的角色。

## 主要类与结构体

### `Editor`
主编辑器类，管理文本内容、布局和渲染。

### `Editor::TextPosition`
```cpp
struct TextPosition {
    size_t fTextByteIndex = SIZE_MAX;   // UTF-8 字节索引
    size_t fParagraphIndex = SIZE_MAX;  // 段落索引（基于硬换行）
};
```
使用 `SIZE_MAX` 作为默认无效值，支持比较运算符（`==`、`!=`、`<`）。

### `Editor::Movement`
```cpp
enum class Movement {
    kNowhere, kLeft, kUp, kRight, kDown,
    kHome, kEnd, kWordLeft, kWordRight,
};
```
定义九种光标移动方向。

### `Editor::PaintOpts`
```cpp
struct PaintOpts {
    SkColor4f fBackgroundColor = {1, 1, 1, 1};    // 白色背景
    SkColor4f fForegroundColor = {0, 0, 0, 1};    // 黑色文字
    SkColor4f fSelectionColor = {0.729f, 0.827f, 0.988f, 1};  // 浅蓝选择
    SkColor4f fCursorColor = {1, 0, 0, 1};        // 红色光标
    TextPosition fSelectionBegin, fSelectionEnd, fCursor;
};
```

### `Editor::Text`（迭代器适配）
```cpp
struct Text {
    const std::vector<TextLine>& fLines;
    struct Iterator { /* ... */ };
};
```
支持 range-based for 循环遍历所有行文本。

### `Editor::TextLine`（私有）
```cpp
struct TextLine {
    StringSlice fText;                     // 文本内容
    sk_sp<const SkTextBlob> fBlob;        // 排版后的 TextBlob
    std::vector<SkRect> fCursorPos;       // 每字节的光标位置
    std::vector<size_t> fLineEndOffsets;  // 软换行偏移
    std::vector<bool> fWordBoundaries;    // 词边界标记
    SkIPoint fOrigin = {0, 0};            // 行原点
    int fHeight = 0;                       // 行高
    bool fShaped = false;                  // 是否已排版
};
```

## 公共 API 函数

### 属性访问

| 方法 | 说明 |
|------|------|
| `int getHeight() const` | 获取文本总高度（画布显示单位） |
| `void setWidth(int)` | 设置显示宽度，可能触发重新排版 |
| `const SkFont& font() const` | 获取当前字体 |
| `void setFont(SkFont)` | 设置字体，标记所有行需要重新排版 |
| `void setFontMgr(sk_sp<SkFontMgr>)` | 设置字体管理器 |
| `Text text() const` | 获取可遍历的文本行集合 |
| `int lineHeight(size_t) const` | 获取指定行的高度 |
| `size_t lineCount() const` | 获取行数 |
| `StringView line(size_t) const` | 获取指定行的文本视图 |

### 编辑操作

| 方法 | 说明 |
|------|------|
| `TextPosition insert(TextPosition, const char*, size_t)` | 在指定位置插入 UTF-8 文本 |
| `TextPosition remove(TextPosition, TextPosition)` | 删除两个位置之间的文本 |
| `size_t copy(TextPosition, TextPosition, char*) const` | 复制选择区域文本 |

### 导航与定位

| 方法 | 说明 |
|------|------|
| `TextPosition move(Movement, TextPosition) const` | 按指定方向移动光标 |
| `TextPosition getPosition(SkIPoint)` | 从像素坐标获取文本位置 |
| `SkRect getLocation(TextPosition)` | 从文本位置获取像素坐标 |

### 渲染

| 方法 | 说明 |
|------|------|
| `void paint(SkCanvas*, PaintOpts)` | 渲染编辑器内容到 Canvas |

## 内部实现细节

### 文本组织
- 文本按段落（硬换行 `\n`）组织为 `TextLine` 向量
- 每个段落可能包含多个软换行（由文本 shaping 产生），通过 `fLineEndOffsets` 记录
- `TextPosition` 使用段落索引和字节偏移定位，而非全局字符偏移

### 延迟排版
- `fNeedsReshape` 标志控制全局重新排版
- 每个 `TextLine` 有独立的 `fShaped` 标志
- 排版在 `reshapeAll()` 中按需执行，由 `paint()` 和 `getPosition()` 等方法触发

### TextPosition 比较运算符
```cpp
static inline bool operator<(const TextPosition& u, const TextPosition& v) {
    return u.fParagraphIndex < v.fParagraphIndex ||
           (u.fParagraphIndex == v.fParagraphIndex && u.fTextByteIndex < v.fTextByteIndex);
}
```
先比较段落索引，再比较字节偏移，提供全序关系。

## 依赖关系

- **直接依赖**: `stringslice.h`、`stringview.h`、`SkColor.h`、`SkFont.h`、`SkFontMgr.h`、`SkTextBlob.h`、`SkString.h`
- **前向声明**: `SkCanvas`、`SkShaper`
- **被使用**: `editor_application.cpp`（应用层）
- **实现文件**: `editor.cpp`

## 设计模式与设计决策

- **段落模型**: 使用硬换行分割段落而非按显示行组织，与现代文本编辑器的段落模型一致
- **UTF-8 字节索引**: `TextPosition` 使用字节索引而非字符索引或代码点索引，这简化了底层文本操作但增加了 UTF-8 对齐的复杂性
- **延迟排版**: 通过脏标记延迟文本 shaping，避免在连续编辑操作中重复排版
- **只读迭代器**: `Text` 结构体提供只读迭代访问，保护内部数据结构
- **显式像素坐标**: 位置查询和设置使用像素坐标 (`SkIPoint`/`SkRect`)，而非抽象单位
- **TODO 注释**: 头文件中有多处 TODO，表明这是一个进行中的设计，包括重命名为 TextParagraph、支持多光标/选择等

## 性能考量

- **按行排版**: 每行独立排版，仅变化的行需要重新 shaping
- **光标位置缓存**: `fCursorPos` 向量为每个字节位置缓存矩形坐标，使光标定位为 O(1) 查找
- **词边界预计算**: `fWordBoundaries` 在排版时预计算，使词级移动为 O(n) 扫描而非每次重新查询 Unicode 断词
- **`SIZE_MAX` 哨兵值**: 使用 `SIZE_MAX` 作为无效位置，避免额外的 `std::optional` 开销

## 相关文件

- `modules/skplaintexteditor/src/editor.cpp` — `Editor` 的完整实现
- `modules/skplaintexteditor/include/stringslice.h` — 文本存储类
- `modules/skplaintexteditor/include/stringview.h` — 轻量文本视图
- `modules/skplaintexteditor/app/editor_application.cpp` — 应用层代码
- `modules/skplaintexteditor/src/shape.h` — 文本 shaping 接口
