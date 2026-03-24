# CanvasKit 文本编辑器 API 工具 (textapi_utils.js)

> 源文件: `modules/canvaskit/npm_build/textapi_utils.js`

## 概述

`textapi_utils.js` 是一个基于 CanvasKit 低级文本 API（`ShapeText`/`getShapedLines`）构建的富文本编辑器原型实现，约 659 行代码。它提供了光标管理（`MakeCursor`）、鼠标交互（`MakeMouse`）、样式管理（`MakeStyle`）以及完整的文本编辑器（`MakeEditor`），支持文本输入/删除、光标移动、选区高亮、富文本样式（粗体/斜体/下划线/颜色/字体大小）应用等功能。该文件是 CanvasKit 文本 API 能力的高级演示。

## 架构位置

```
应用代码
  └── MakeEditor(text, style, cursor, width)  ← textapi_utils.js
      ├── MakeCursor() — 光标绘制
      ├── MakeMouse() — 鼠标状态跟踪
      ├── MakeStyle(length) — 样式管理
      └── CanvasKit.ParagraphBuilder.ShapeText()
          └── paragraph_bindings.cpp → skparagraph (C++)
```

## 主要类与结构体

### MakeCursor

光标/选区绘制对象，支持闪烁光标和选区路径高亮：

| 属性/方法 | 说明 |
|----------|------|
| `setBlinkRate(blinks_per_sec)` | 设置闪烁频率（0 = 不绘制, Infinity = 常亮） |
| `place(x, top, bottom)` | 放置光标线 |
| `setPath(path)` | 设置选区路径（替代光标线） |
| `draw_before(canvas)` | 绘制选区高亮（在文本之前） |
| `draw_after(canvas)` | 绘制光标线（在文本之后，带闪烁效果） |

### MakeMouse

鼠标状态跟踪对象：

| 属性/方法 | 说明 |
|----------|------|
| `setDown(x, y)` | 记录按下位置 |
| `setMove(x, y)` | 更新当前位置 |
| `setUp(x, y)` | 记录释放位置 |
| `isActive()` | 是否处于拖拽状态 |
| `getPos(dx, dy)` | 获取起始和当前位置（带偏移） |

### MakeStyle(length)

文本样式片段，覆盖指定长度的文本：

| 属性 | 说明 |
|------|------|
| `_length` | 覆盖的字符长度 |
| `typeface` / `size` / `color` | 字体/大小/颜色 |
| `bold` / `italic` / `underline` | 粗体/斜体/下划线 |
| `mergeFrom(src)` | 合并样式属性（支持 toggle 模式） |

### MakeEditor(text, style, cursor, width)

完整的文本编辑器，核心对象：

**布局与查询**:
| 方法 | 说明 |
|------|------|
| `getLines()` | 获取塑形后的行数据 |
| `width()` / `height()` / `bounds()` | 编辑器尺寸 |
| `setXY(x, y)` | 设置绘制偏移 |

**编辑操作**:
| 方法 | 说明 |
|------|------|
| `setIndex(i)` | 设置光标位置 |
| `setIndices(a, b)` | 设置选区范围 |
| `moveDX(dx)` | 水平移动光标（左/右） |
| `moveDY(dy)` | 垂直移动光标（上/下行） |
| `insert(charcode)` | 插入字符 |
| `deleteSelection()` | 删除选区或退格 |

**样式操作**:
| 方法 | 说明 |
|------|------|
| `applyStyleToRange(style, start, end)` | 对指定范围应用样式 |
| `applyStyleToSelection(style)` | 对当前选区应用样式 |

**绘制**:
| 方法 | 说明 |
|------|------|
| `draw(canvas)` | 完整绘制编辑器（文本 + 光标/选区） |

## 公共 API 函数

### 坐标/索引转换辅助函数

| 函数 | 说明 |
|------|------|
| `runs_x_to_index(runs, x)` | 从 x 坐标找到最近的文本索引 |
| `lines_pos_to_index(lines, x, y)` | 从 (x,y) 坐标找到文本索引 |
| `runs_index_to_run(runs, index)` | 从文本索引找到所在 run |
| `runs_index_to_x(runs, index)` | 从文本索引找到 x 坐标 |
| `lines_index_to_line(lines, index)` | 从文本索引找到所在行 |
| `lines_index_to_x(lines, index)` | 从文本索引找到 x 坐标 |
| `lines_indices_to_path(lines, a, b, width)` | 从选区范围生成高亮路径 |
| `string_del(str, start, end)` | 字符串范围删除 |

## 内部实现细节

### 文本塑形与行构建

`_buildLines()` 将样式数组合并为稀疏块（相邻且字体相同的样式合并），然后调用 `CanvasKit.ParagraphBuilder.ShapeText()` 进行文本塑形。塑形结果是行数组，每行包含多个 run，每个 run 包含字形、位置和偏移数据。

### 光标定位算法

- **x 坐标到索引**: 遍历 run 中的位置数组，找到 x 落入的两个相邻字形位置之间，取中点比较决定偏左还是偏右
- **索引到 x 坐标**: 在 run 的 offsets 数组中查找精确匹配的索引，返回对应位置
- **上下行移动**: 获取当前行的 x 坐标，在目标行中重新查找最近的索引

### 选区路径生成

`lines_indices_to_path` 处理三种情况：
1. **同行选区**: 单个矩形 (ax, top) 到 (bx, bottom)
2. **跨行选区**: 首行从 ax 到行尾 + 末行从行首到 bx + 中间行全宽矩形

### 样式管理

样式以数组存储，每个元素覆盖一段连续的文本。关键操作：

- **插入**: 找到索引所在的样式片段，增加其长度
- **删除**: 缩减或移除覆盖范围内的样式片段
- **应用样式**: 在范围边界处分裂样式片段，对中间的完整片段调用 `mergeFrom`，对部分覆盖的片段先分裂再合并

### 绘制实现

`draw()` 方法同时遍历 run 数组和 style 数组，处理它们边界不对齐的情况。对每个 (run, style) 交叉区域：
1. 设置字体大小、粗体（embolden）、斜体（skewX）
2. 设置颜色
3. 如果是子范围，切割字形和位置数组
4. 调用 `canvas.drawGlyphs()` 绘制
5. 如果有下划线，使用 `getGlyphIntercepts` 获取字形交叉区域，在间隙处绘制下划线矩形

### 光标闪烁

使用 `Math.floor(Date.now() * draws_per_sec / 1000) & 1` 实现周期性显示/隐藏，不依赖定时器。

## 依赖关系

| 依赖项 | 说明 |
|-------|------|
| `CanvasKit.ParagraphBuilder.ShapeText()` | 文本塑形核心 API |
| `CanvasKit.Paint` / `CanvasKit.Font` / `CanvasKit.Path` | 绘图原语 |
| `CanvasKit.PaintStyle` | 画笔样式常量 |

## 设计模式与设计决策

- **面向数据的编辑器**: 编辑器状态由文本字符串 + 样式数组 + 光标索引完全描述，便于序列化和调试
- **稀疏样式合并**: 相邻且字体属性相同的样式片段在塑形前合并为一个块，减少 run 数量
- **Toggle 样式**: 样式的 `bold`/`italic`/`underline` 支持 `'toggle'` 值，方便实现工具栏按钮
- **选区即路径**: 选区高亮使用 SkPath 绘制，支持跨行选区的复杂形状
- **Run 与 Style 双遍历**: 绘制时同步遍历两个不同粒度的数组，处理边界交叉

## 性能考量

- `_buildLines()` 在每次文本/样式变更后完全重新塑形，对长文本可能产生显著延迟
- 光标闪烁使用时间戳判断，不创建定时器，但需要外部动画循环驱动重绘
- `drawGlyphs` 是低级 API，比 `drawText` 更高效（跳过文本塑形步骤）
- 下划线使用 `getGlyphIntercepts` 实现字形避让，是计算密集型操作
- 样式数组的分裂和合并操作使用 `splice`，对大量样式片段可能有性能影响

## 相关文件

- `modules/canvaskit/paragraph_bindings.cpp` — `ShapeText` 和 `getShapedLines` 的 C++ 实现
- `modules/canvaskit/paragraph.js` — 段落 JS 辅助层
- `modules/canvaskit/npm_build/types/index.d.ts` — TypeScript 类型定义
