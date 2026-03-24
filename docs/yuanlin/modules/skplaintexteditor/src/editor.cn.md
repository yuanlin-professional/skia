# Editor 实现 - Skia 纯文本编辑器核心逻辑

> 源文件: `modules/skplaintexteditor/src/editor.cpp`

## 概述

`editor.cpp` 是 `SkPlainTextEditor::Editor` 类的完整实现文件，包含 517 行代码。它实现了纯文本编辑器的所有核心功能：文本插入与删除（支持跨段落操作）、九种方向的光标移动（包括字符级、词级、行级和视觉行级）、文本选择与复制、位置查询与映射、文本渲染以及按需文本 shaping。该文件是编辑器模块中最大且最复杂的实现文件。

## 架构位置

该文件是 `editor.h` 声明的所有方法的实现，是编辑器模块的核心引擎。它向下依赖 `StringSlice` 进行文本存储、`shape.h` 中的 `Shape()` 函数进行文本排版，向上为 `editor_application.cpp` 提供所有编辑操作。在整个模块中承担 Model 和 Controller 的双重角色。

## 主要类与结构体

### 内部辅助函数

| 函数 | 说明 |
|------|------|
| `offset(SkRect, SkIPoint)` | 矩形偏移 |
| `valid_utf8(const char*, size_t)` | 验证 UTF-8 有效性 |
| `readlines(data, size, f)` | 零分配按行迭代（类似 Python readlines） |
| `remove_newline(str, len)` | 移除尾部换行创建 StringSlice |
| `is_utf8_continuation(char)` | 检查 UTF-8 连续字节 |
| `next_utf8(p, end)` | 前进到下一个 UTF-8 字符 |
| `prev_utf8(p, begin)` | 后退到上一个 UTF-8 字符 |
| `align_utf8(p, begin)` | 对齐到 UTF-8 字符边界 |
| `count_char(string, value)` | 统计字符出现次数 |
| `align_column(str, p)` | 对齐字节偏移到有效 UTF-8 位置 |
| `find_first_larger(list, value)` | 二分查找首个大于 value 的位置 |
| `find_closest_x(bounds, x, b, e)` | 查找最接近 x 坐标的光标位置 |
| `append(dst, count, src, n)` | 追加数据到缓冲区或计算大小 |

## 公共 API 函数

### 属性设置

| 方法 | 说明 |
|------|------|
| `void setFont(SkFont)` | 设置字体，标记所有行脏 |
| `void setFontMgr(sk_sp<SkFontMgr>)` | 设置字体管理器 |
| `void setWidth(int)` | 设置布局宽度 |

### 编辑操作

| 方法 | 说明 |
|------|------|
| `TextPosition insert(TextPosition, const char*, size_t)` | 插入 UTF-8 文本 |
| `TextPosition remove(TextPosition, TextPosition)` | 删除区间文本 |
| `size_t copy(TextPosition, TextPosition, char*) const` | 复制文本 |

### 导航

| 方法 | 说明 |
|------|------|
| `TextPosition move(Movement, TextPosition) const` | 光标移动（9 种方向） |
| `TextPosition getPosition(SkIPoint)` | 像素坐标到文本位置 |
| `SkRect getLocation(TextPosition)` | 文本位置到像素坐标 |

### 渲染

| 方法 | 说明 |
|------|------|
| `void paint(SkCanvas*, PaintOpts)` | 渲染到 Canvas |

## 内部实现细节

### 文本插入 (`insert`)
```cpp
TextPosition Editor::insert(TextPosition pos, const char* utf8Text, size_t byteLen) {
    if (!valid_utf8(utf8Text, byteLen) || 0 == byteLen) return pos;
    pos = this->move(Movement::kNowhere, pos);  // 规范化位置
    // 插入文本到当前段落
    fLines[pos.fParagraphIndex].fText.insert(pos.fTextByteIndex, utf8Text, byteLen);
    // 检查是否包含换行符，如果有则拆分段落
    size_t newlinecount = count_char(fLines[pos.fParagraphIndex].fText, '\n');
    if (newlinecount > 0) {
        // 在换行位置拆分为多个段落
        StringSlice src = std::move(fLines[pos.fParagraphIndex].fText);
        fLines.insert(next, newlinecount, TextLine());
        readlines(src.begin(), src.size(), [&line](const char* str, size_t l) {
            (line++)->fText = remove_newline(str, l);
        });
    }
}
```

关键点：
- UTF-8 有效性验证在插入前执行
- 使用 `kNowhere` 移动规范化位置，修正越界索引
- 插入后检查换行符并拆分段落
- 使用 `readlines` 进行零分配的行解析

### 文本删除 (`remove`)
处理两种情况：
1. **同段落删除**: 直接在 StringSlice 上调用 `remove`
2. **跨段落删除**: 将首段尾部和末段头部合并，删除中间段落

```cpp
if (start.fParagraphIndex == end.fParagraphIndex) {
    fLines[start.fParagraphIndex].fText.remove(start.fTextByteIndex, ...);
} else {
    auto& line = fLines[start.fParagraphIndex];
    line.fText.remove(start.fTextByteIndex, ...);
    line.fText.insert(start.fTextByteIndex, /* 末段剩余文本 */);
    fLines.erase(fLines.begin() + start.fParagraphIndex + 1,
                 fLines.begin() + end.fParagraphIndex + 1);
}
```

### 文本复制 (`copy`)
支持双模式：`dst == nullptr` 时仅计算大小，否则执行实际复制。跨段落复制时在段落间插入换行符。

### 光标移动 (`move`) - 核心算法
该方法实现了九种移动方向，是文件中最复杂的函数：

- **kNowhere**: 规范化位置（修正越界，对齐 UTF-8 边界）
- **kLeft/kRight**: 字符级移动，支持跨段落
- **kHome/kEnd**: 移动到视觉行首/行尾（基于 `fLineEndOffsets`）
- **kUp/kDown**: 视觉行级移动，使用 `find_closest_x` 保持水平位置
- **kWordLeft/kWordRight**: 词级移动，基于预计算的 `fWordBoundaries`

```cpp
case Movement::kUp: {
    float x = fLines[pos.fParagraphIndex].fCursorPos[pos.fTextByteIndex].left();
    const auto& list = fLines[pos.fParagraphIndex].fLineEndOffsets;
    size_t f = find_first_larger(list, pos.fTextByteIndex);
    if (f > 0) {
        // 同段落上一视觉行
        pos.fTextByteIndex = find_closest_x(cursorPos, x, prev_begin, list[f-1]);
    } else if (pos.fParagraphIndex > 0) {
        // 上一段落最后一视觉行
        --pos.fParagraphIndex;
        pos.fTextByteIndex = find_closest_x(newLine.fCursorPos, x, ...);
    }
}
```

### 像素位置查询 (`getPosition`)
遍历所有行，对每行构建包含文本边界的矩形区域，然后在匹配行内查找最精确的光标位置。使用 `kUnsetRect` 哨兵值跳过无效的光标位置。

### 渲染 (`paint`)
```cpp
void Editor::paint(SkCanvas* c, PaintOpts options) {
    this->reshapeAll();
    if (!c) return;  // 仅 shaping，不渲染
    // 1. 绘制背景
    c->drawPaint(SkPaint(options.fBackgroundColor));
    // 2. 绘制选择区域
    for (TextPosition pos = min(selBegin, selEnd); pos < max(selBegin, selEnd); ...) {
        c->drawRect(offset(l.fCursorPos[pos.fTextByteIndex], l.fOrigin), selection);
    }
    // 3. 绘制光标
    c->drawRect(Editor::getLocation(options.fCursor), SkPaint(options.fCursorColor));
    // 4. 绘制文本
    for (const TextLine& line : fLines) {
        if (line.fBlob) c->drawTextBlob(line.fBlob.get(), ...);
    }
}
```

### 文本 shaping (`reshapeAll`)
```cpp
void Editor::reshapeAll() {
    if (fNeedsReshape) {
        for (TextLine& line : fLines) {
            if (!line.fShaped) {
                ShapeResult result = Shape(line.fText.begin(), line.fText.size(),
                                           fFont, fFontMgr, fLocale, shape_width);
                line.fBlob = std::move(result.blob);
                line.fLineEndOffsets = std::move(result.lineBreakOffsets);
                line.fCursorPos = std::move(result.glyphBounds);
                line.fWordBoundaries = std::move(result.wordBreaks);
                line.fHeight = result.verticalAdvance;
                line.fShaped = true;
            }
        }
        // 计算行布局（y 坐标）
        int y = 0;
        for (TextLine& line : fLines) {
            line.fOrigin = {0, y};
            y += line.fHeight;
        }
        fHeight = y;
        fNeedsReshape = false;
    }
}
```

代码中有被注释掉的并行 shaping 代码路径（`SK_EDITOR_GO_FAST`），使用 `SkExecutor` 线程池进行多线程 shaping。

### UTF-8 处理工具函数
```cpp
static inline bool is_utf8_continuation(char v) {
    return ((unsigned char)v & 0b11000000) == 0b10000000;
}
```
通过检查高两位判断是否为 UTF-8 连续字节（10xxxxxx 模式）。`next_utf8`、`prev_utf8`、`align_utf8` 基于此实现 UTF-8 安全的字节级导航。

## 依赖关系

- **直接依赖**: `editor.h`、`SkCanvas.h`、`SkExecutor.h`、`SkPath.h`、`SkUTF.h`
- **模块依赖**: `shape.h`（文本 shaping 函数）
- **数据结构**: `StringSlice`（文本存储）
- **被使用**: `editor_application.cpp`

## 设计模式与设计决策

- **段落模型**: 文本按硬换行分割为段落，每段落独立 shaping。这简化了编辑操作（大多数编辑只影响一个段落），但跨段落操作需要特殊处理
- **字节索引**: 使用 UTF-8 字节索引而非字符索引，避免了 O(n) 的索引转换，但需要在所有边界处确保 UTF-8 对齐
- **位置规范化**: `move(kNowhere, pos)` 用于修正无效位置，是一种防御性编程策略
- **零分配行解析**: `readlines` 模板函数在不分配内存的情况下解析行，回调直接引用原始数据
- **选择绘制**: 选择区域通过逐字符绘制矩形实现，而非使用连续的选择矩形区域
- **二分查找优化**: `find_first_larger` 使用 `std::upper_bound` 在软换行偏移列表中进行二分查找

## 性能考量

- **按需 shaping**: 仅脏行需要重新 shaping，通过 `fShaped` 标记控制
- **并行 shaping 支持**: `SK_EDITOR_GO_FAST` 代码路径支持使用线程池进行并行行 shaping，但默认未启用
- **光标位置缓存**: `fCursorPos` 数组在 shaping 时预计算，使后续的光标移动和命中测试为 O(1) 或 O(log n)
- **词边界预计算**: `fWordBoundaries` 在 shaping 时预计算，避免每次词移动时重新查询 Unicode
- **选择绘制开销**: 选择区域逐字符绘制可能在大选择时产生大量 `drawRect` 调用，是一个潜在的性能瓶颈
- **`paint(nullptr, ...)` 预热**: 支持传入空 Canvas 仅执行 shaping，用于在首次显示前预热
- **视觉行导航**: `kUp`/`kDown` 使用 `find_closest_x` 线性扫描光标位置数组，对于非常长的行（数千字符）可能较慢

## 相关文件

- `modules/skplaintexteditor/include/editor.h` — 类声明和接口定义
- `modules/skplaintexteditor/src/shape.h` — `Shape()` 函数和 `ShapeResult` 结构体
- `modules/skplaintexteditor/include/stringslice.h` — 文本存储
- `modules/skplaintexteditor/app/editor_application.cpp` — 应用层调用
- `src/base/SkUTF.h` — UTF-8 编解码工具
- `include/core/SkCanvas.h` — 渲染 API
