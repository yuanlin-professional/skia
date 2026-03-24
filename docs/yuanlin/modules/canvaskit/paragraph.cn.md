# CanvasKit 段落排版 JavaScript 辅助层 (paragraph.js)

> 源文件: `modules/canvaskit/paragraph.js`

## 概述

`paragraph.js` 是 CanvasKit 中段落文本排版功能的 JavaScript 辅助层，约 397 行代码。它负责在 JS 端构建和序列化文本样式、段落样式、支柱样式等复杂配置对象，将颜色、字体族名称、阴影、字体特性等数据打包到 WASM 堆中，然后调用 C++ 绑定（`paragraph_bindings.cpp`）完成实际的段落构建和布局。同时，它还提供了查询结果的反序列化（如将 Float32Array 转换为矩形对象数组）以及字体注册等便捷功能。

## 架构位置

```
JavaScript 应用
  └── CanvasKit.ParagraphBuilder.Make() / pushStyle() / ...  ← paragraph.js
      └── copyArrays() → WASM 堆序列化
      └── CanvasKit.ParagraphBuilder._Make() / _pushStyle()  ← paragraph_bindings.cpp
          └── skparagraph::ParagraphBuilderImpl (C++)
```

## 主要类与结构体

### CanvasKit.ParagraphStyle(s)

段落样式初始化函数，设置默认值并处理省略号字符串的 WASM 序列化：

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `disableHinting` | `false` | 禁用字体微调 |
| `ellipsis` | 无 | 省略号字符（序列化为 `_ellipsisPtr` + `_ellipsisLen`） |
| `heightMultiplier` | `-1`（未设置） | 行高倍数 |
| `maxLines` | `0` | 最大行数 |
| `textAlign` | `TextAlign.Start` | 文本对齐 |
| `textDirection` | `TextDirection.LTR` | 文本方向 |
| `textHeightBehavior` | `TextHeightBehavior.All` | 文本高度行为 |
| `strutStyle` | 默认支柱样式 | 支柱样式 |
| `textStyle` | 默认文本样式 | 文本样式 |
| `applyRoundingHack` | `true` | 应用舍入修正 |

### CanvasKit.TextStyle(s)

文本样式初始化函数，设置字体大小、间距、装饰等默认值。

### fontStyle(s) / strutStyle(s)

内部辅助函数，分别初始化字体样式和支柱样式的默认值。

## 公共 API 函数

### ParagraphBuilder 工厂方法

| 方法 | 说明 |
|------|------|
| `ParagraphBuilder.Make(paragraphStyle, fontManager)` | 使用字体管理器创建构建器 |
| `ParagraphBuilder.MakeFromFontProvider(paragraphStyle, fontProvider)` | 使用字体提供器创建构建器 |
| `ParagraphBuilder.MakeFromFontCollection(paragraphStyle, fontCollection)` | 使用字体集合创建构建器 |
| `ParagraphBuilder.ShapeText(text, blocks, width)` | 静态文本塑形 |

### ParagraphBuilder 原型方法

| 方法 | 说明 |
|------|------|
| `pushStyle(textStyle)` | 推入文本样式 |
| `pushPaintStyle(textStyle, fg, bg)` | 推入带画笔的文本样式 |
| `addPlaceholder(width, height, alignment, baseline, offset)` | 添加占位符 |
| `setWordsUtf8/16(words)` | 设置客户端词边界 |
| `setGraphemeBreaksUtf8/16(graphemeBreaks)` | 设置客户端字素边界 |
| `setLineBreaksUtf8/16(lineBreaks)` | 设置客户端换行边界 |

### Paragraph 原型方法

| 方法 | 说明 |
|------|------|
| `getRectsForRange(start, end, hStyle, wStyle)` | 获取文本范围的矩形列表 |
| `getRectsForPlaceholders()` | 获取占位符矩形列表 |
| `getGlyphInfoAt(index)` | 获取指定索引的字形信息 |
| `getClosestGlyphInfoAtCoordinate(dx, dy)` | 获取坐标最近的字形信息 |

### TypefaceFontProvider 原型方法

| 方法 | 说明 |
|------|------|
| `registerFont(font, family)` | 注册字体（ArrayBuffer + 字体族名称） |

## 内部实现细节

### copyArrays / freeArrays 模式

`copyArrays(textStyle)` 是核心序列化函数，将文本样式中的所有数组/对象属性转换为 WASM 指针：

1. **颜色**: `color`, `foregroundColor`, `backgroundColor`, `decorationColor` 通过 `copyColorToWasm` 序列化。使用预分配的 scratch 指针避免每次分配
2. **字体族**: 字符串数组通过 `naiveCopyStrArray` 转换为 null-terminated 字符串的指针数组
3. **区域设置**: 通过 `cacheOrCopyString` 序列化
4. **阴影**: 颜色、偏移和模糊半径分别序列化为三个独立的数组
5. **字体特性**: 名称和值分别序列化为字符串指针数组和整数数组
6. **可变字体轴**: 轴标签和值分别序列化

`freeArrays(textStyle)` 在 C++ 调用完成后释放临时分配的内存。

### cacheOrCopyString

字符串缓存机制：将 JS 字符串拷贝到 WASM 堆后缓存指针。相同字符串的后续调用直接返回缓存的指针，避免内存无限增长。使用 `stringToUTF8`（Emscripten 内置）进行 UTF-8 转换。

### floatArrayToRects

将 C++ 返回的紧凑 Float32Array（每 5 个 float 为一组：4 个 Rect + 1 个方向标志）转换为 `{rect, dir}` 对象数组，并释放 Float32Array 底层内存。

### convertDirection

将 C++ 返回的字形方向数值（0 = RTL, 1 = LTR）转换为 CanvasKit 枚举常量。

### 哨兵值约定

- `fontSize == null` → 设为 `-1`（C++ 端判断 `-1` 表示"未设置"）
- `heightMultiplier == null` → 设为 `-1`
- `maxLines == 0` → 表示无限制

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `memory.js` | `copy1dArray`, `copyColorToWasm`, `copyFlexibleColorArray`, `freeArraysThatAreNotMallocedByUsers` |
| `paragraph_bindings.cpp` | C++ 端绑定（`_Make`, `_pushStyle`, `_getRectsForRange` 等） |
| `color.js` | `CanvasKit.BLACK` 默认颜色 |
| Emscripten | `lengthBytesUTF8`, `stringToUTF8` |
| `CanvasKit.Typeface` | 字体注册时使用 |

## 设计模式与设计决策

- **序列化/反序列化模式**: JS 端负责将复杂对象序列化为扁平的 WASM 指针数组，C++ 端负责反序列化
- **字符串缓存**: `cacheOrCopyString` 缓存机制避免了高频操作中重复的字符串分配
- **Scratch 缓冲区**: 颜色使用预分配的 scratch 指针，避免每次样式推送时分配内存
- **配对的 copy/free**: `copyArrays` 和 `freeArrays` 必须成对调用，确保不泄漏内存
- **哨兵值而非 undefined**: 使用 `-1` 和 `0` 作为"未设置"标记，因为 Emscripten value_object 要求所有字段有明确类型
- **闭包保护**: 使用 `['']` 语法（如 `s['fontSize']`）防止 Closure Compiler 最小化属性名

## 性能考量

- `copyArrays` 在每次 `pushStyle`、`Make` 时执行，涉及多次 `_malloc` 和内存拷贝
- `cacheOrCopyString` 缓存字体族名称等常用字符串，避免重复分配
- `floatArrayToRects` 在解码后立即释放底层内存，避免长期持有 WASM 堆内存
- `freeArrays` 释放临时分配的指针数组，但不释放 scratch 和缓存的字符串
- 客户端 ICU 数据（`setWordsUtf8` 等）通过 `copy1dArray` 一次性传入，并在使用后有条件释放

## 相关文件

- `modules/canvaskit/paragraph_bindings.cpp` — C++ 端段落绑定
- `modules/canvaskit/paragraph_bindings_gen.cpp` — 段落枚举绑定
- `modules/canvaskit/memory.js` — WASM 内存管理
- `modules/canvaskit/color.js` — 颜色工具
- `modules/skparagraph/include/Paragraph.h` — 段落核心 API
