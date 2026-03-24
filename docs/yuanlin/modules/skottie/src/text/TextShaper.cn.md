# TextShaper - Skottie 文本排版引擎

> 源文件: `modules/skottie/src/text/TextShaper.cpp`

## 概述

TextShaper 是 Skottie 文本渲染管线的核心排版引擎，实现了完整的文本塑形（shaping）、布局和对齐功能。该文件包含基于 SkShaper 的文本处理管线，支持多行文本、水平/垂直对齐、自动换行、文本大小自适应（scale-to-fit）、RTL/BiDi 文本方向、字体回退、字形片段化输出等功能。它是连接 Lottie 文本属性与 Skia 渲染系统的桥梁，忠实地复现 After Effects 的文本排版行为。

## 架构位置

TextShaper 位于 Skottie 文本子系统的中间层，接收来自 TextAdapter 的排版请求，输出可渲染的字形片段。

```
TextAdapter (文本属性管理)
  |
  +-> Shaper::Shape() [入口]
  |     +-> AdjustedText (大小写转换)
  |     +-> ShapeImpl() / ShapeToFit() [排版实现]
  |           +-> ResultBuilder (SkShaper::RunHandler 实现)
  |           |     +-> SkShaper (文本塑形引擎)
  |           |     +-> shapeLine() [逐行塑形]
  |           |     +-> commitLine() -> commitFragmentedRun / commitConsolidatedRun
  |           |     +-> finalize() [垂直对齐调整]
  |           |
  |           +-> result_fits() [尺寸检测]
  |
  +-> Shaper::Result [输出]
        +-> ShapedGlyphs (字形数据)
        +-> Fragment (位置、索引信息)
```

## 主要类与结构体

### ResultBuilder
- 实现 `SkShaper::RunHandler` 接口，是文本塑形的核心处理器
- 缓冲 SkShaper 输出的运行数据（runs），执行逐行位置调整
- 主要职责：
  - 水平对齐（左、居中、右）
  - 尾部空白字符处理
  - 片段化/合并模式输出
  - 垂直对齐计算
- 关键成员：
  - `fFont` - 主字体对象
  - `fShaper` - SkShaper 实例
  - `fLineGlyphs/fLinePos/fLineClusters` - 当前行缓冲
  - `fResult` - 累积的排版结果
  - `fOffset` - 当前行偏移

### AdjustedText
- 应用大写化规则的文本包装器
- 支持 `kNone` 和 `kUpperCase` 两种模式
- 使用 `SkUnicode::toUpper()` 进行 Unicode 感知的大写转换

### Shaper::Result（在 TextShaper.h 中定义）
- 排版结果容器
- `fFragments` - 字形片段列表
- `fScale` - 缩放因子（scale-to-fit 模式）
- `fMissingGlyphCount` - 缺失字形计数

### Shaper::ShapedGlyphs
- 字形数据容器
- `fRuns` - 运行记录列表
- `fGlyphIDs` / `fGlyphPos` - 字形 ID 和位置
- `fClusters` - 字形到 UTF-8 偏移的映射
- `computeBounds()` / `draw()` - 边界计算和绘制

## 公共 API 函数

### `Shaper::Shape`（点模式）
```cpp
static Result Shape(const SkString& text, const TextDesc& desc, const SkPoint& point,
                    const sk_sp<SkFontMgr>& fontmgr, const sk_sp<SkShapers::Factory>& shapingFactory);
```
- 在指定点处排版文本（无边界框约束）
- Scale-to-fit 在点模式下无意义，直接返回空结果

### `Shaper::Shape`（框模式）
```cpp
static Result Shape(const SkString& text, const TextDesc& desc, const SkRect& box,
                    const sk_sp<SkFontMgr>& fontmgr, const sk_sp<SkShapers::Factory>& shapingFactory);
```
- 在指定矩形框内排版文本
- 根据 `ResizePolicy` 选择策略：
  - `kNone` - 直接排版
  - `kScaleToFit` - 二分搜索最佳尺寸
  - `kDownscaleToFit` - 先尝试原尺寸，超出则缩小

### `ShapedGlyphs::computeBounds`
```cpp
SkRect computeBounds(BoundsType btype) const;
```
- `BoundsType::kConservative` - 使用字体边界快速估算
- `BoundsType::kTight` - 逐字形精确计算

### `ShapedGlyphs::draw`
```cpp
void draw(SkCanvas* canvas, const SkPoint& origin, const SkPaint& paint) const;
```
- 按运行（run）绘制字形到画布

### `Shaper::Result::computeVisualBounds`
```cpp
SkRect computeVisualBounds() const;
```
- 计算所有片段的紧密视觉边界

## 内部实现细节

### 文本塑形流程（shapeLine）
1. 创建运行迭代器：语言（TrivialLanguageRunIterator）、字体（FontMgrRunIterator 或 TrivialFontRunIterator）、BiDi、脚本
2. Chrome Linux/CrOS 特殊路径：使用 `SKOTTIE_TRIVIAL_FONTRUN_ITER` 避免字体回退崩溃
3. 调用 `SkShaper::shape()` 执行塑形
4. 通过 RunHandler 回调收集结果

### 水平对齐与尾部空白处理
- 对齐因子：左 = 0.0，居中 = -0.5，右 = -1.0
- 尾部空白仅检查最后一个 run（SkShaper 通常不会拆分空白）
- 计算空白累积宽度，按对齐因子偏移整行

### 垂直对齐（finalize）
支持 8 种垂直对齐模式：
- `kTop` - 顶部对齐（减去 ascent）
- `kTopBaseline` - 基线对齐（默认）
- `kHybridTop/Center/Bottom` - 混合排版+视觉边界对齐
- `kVisualTop/Center/Bottom` - 纯视觉边界对齐

混合模式使用排版范围（ascent 到 descent + 行高 * 行数）与视觉边界的并集，确保文本不溢出且空行被正确计入。

### Scale-to-Fit（ShapeToFit）
- 使用混合指数/二分搜索算法寻找最佳文本尺寸
- 搜索范围：`[minTextSize/textSize, maxTextSize/textSize]`
- 最多 16 次迭代
- 每次迭代同步缩放 textSize、lineHeight、lineShift、ascent
- `result_fits()` 检查几何约束和可选的最大行数约束

### 输出模式
- **片段化模式**（`kFragmentGlyphs`）：每个字形一个片段，支持逐字形动画（范围选择器）
  - 可选跟踪每字形的 advance 和 ascent（`kTrackFragmentAdvanceAscent`）
  - 空行也生成空片段用于行索引跟踪
- **合并模式**：所有字形合并到单个片段中

### 空行处理
- SkShaper 不处理空行，ResultBuilder 手动调用 `beginLine()`/`commitLine()`
- 片段化模式下为空行注入空片段以保持行索引准确

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkShaper.h` / `SkShaper_factory.h` | 文本塑形引擎 |
| `SkUnicode.h` | Unicode 操作（大写转换等） |
| `SkFont.h` / `SkFontMgr.h` / `SkFontMetrics.h` | 字体和度量 |
| `SkCanvas.h` | 字形绘制 |
| `SkUTF.h` | UTF-8 遍历 |
| `SkFontPriv.h` | GetFontBounds 保守边界 |
| `SkTArray.h` / `SkTemplates.h` | 容器和临时缓冲 |
| `TextShaper.h` | Shaper 公共接口定义 |

## 设计模式与设计决策

- **RunHandler 回调模式**：ResultBuilder 实现 SkShaper::RunHandler 接口，通过回调模式接收塑形结果，避免中间数据拷贝。
- **策略模式（输出模式）**：片段化/合并两种输出模式通过函数指针（`commit_proc`）在 `commitLine` 中动态选择。
- **二分搜索优化**：Scale-to-fit 使用混合指数+二分搜索，在未知范围时指数探索，已知范围后二分精确搜索。
- **AE 行为兼容**：多处注释标注了对 After Effects 行为的忠实复现（尾部空白处理、基线裁切等）。
- **Chrome 兼容性**：通过编译宏 `SKOTTIE_TRIVIAL_FONTRUN_ITER` 为缺少字体回退能力的平台提供安全路径。
- **混合边界计算**：垂直对齐使用排版范围与视觉边界的并集，兼顾了排版精确性和视觉效果。

## 性能考量

- `AutoSTMalloc<64, ...>` 用于行级缓冲，小行在栈上分配避免堆分配。
- `STArray<16, ...>` 用于运行列表和宽度缓冲，减少小规模场景的内存分配。
- `incReserve` 为 SkPathBuilder（间接通过字形绘制）预分配空间。
- Scale-to-fit 最多 16 次迭代，每次需完整排版，复杂文本场景下可能较慢。
- `computeBounds` 的保守模式使用字体全局边界，避免逐字形查询。
- 缺失字形计数（`kMissingGlyphID == 0`）在输出阶段累计，无额外遍历。
- 字形宽度查询（`getWidths`）仅在需要时执行（`kTrackFragmentAdvanceAscent`）。

### 边界计算详解

`ShapedGlyphs::computeBounds` 提供两种精度模式：

**保守模式（kConservative）：**
- 使用 `SkFontPriv::GetFontBounds` 获取字体的全局包围框
- 对每个 run 计算字形位置的范围，然后扩展字体边界
- 当字体边界为空（可能是字体 bug）时自动回退到紧密模式
- 优点：无需逐字形查询，速度快
- 缺点：过估计，可能浪费渲染区域

**紧密模式（kTight）：**
- 使用 `run.fFont.getBounds()` 获取每个字形的精确包围框
- 逐字形偏移并合并，得到精确的视觉边界
- 使用 `AutoSTArray<16, SkRect>` 避免小 run 的堆分配
- 优点：精确
- 缺点：每个字形需要单独查询

### 缩放搜索算法详解

`ShapeToFit` 使用的搜索算法是混合指数-二分搜索：

1. 初始尝试 `try_scale = 1.0`（原始大小）
2. 如果不适合（太大）：
   - 如果还没找到可行的 `in_scale`，则指数缩小：`try_scale *= 0.5`
   - 如果已找到 `in_scale`，则二分：`try_scale = (in + out) / 2`
3. 如果适合（记录为最佳结果）：
   - 如果还没找到不可行的 `out_scale`，则指数放大：`try_scale *= 2`
   - 如果已找到 `out_scale`，则二分：`try_scale = (in + out) / 2`
4. 当 `try_scale` 不再变化时终止

这种设计在搜索初期快速定位范围（指数步长），在精确阶段快速收敛（二分步长）。

## 相关文件

- `modules/skottie/include/TextShaper.h` - Shaper 公共接口定义
- `modules/skottie/src/text/TextAdapter.h` - 文本适配器（调用方）
- `modules/skottie/src/text/Unicode.cpp` - 严格换行 Unicode 包装
- `modules/skshaper/include/SkShaper.h` - SkShaper 塑形引擎
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `modules/skottie/src/layers/TextLayer.cpp` - 文本图层入口
