# TextShaper.h

> 源文件: `modules/skottie/include/TextShaper.h`

## 概述

`TextShaper.h` 定义了 Skottie 动画引擎中的文本排版（text shaping）系统。`Shaper` 类是一个工具类，在 SkShaper 的基础上实现了 After Effects 的文本排版语义，包括文本对齐、自动缩放、换行策略、文本方向、大小写转换等功能。该文件是 Skottie 文本图层渲染的核心排版接口，负责将文本字符串转换为可绘制的字形布局结果。

## 架构位置

该文件位于 `modules/skottie/include/` 目录下，属于 Skottie 模块的公共 API 层。在文本处理管线中，Shaper 位于中间位置：

```
Lottie JSON -> TextAdapter -> Shaper::Shape() -> ShapedGlyphs -> SkCanvas 渲染
                                  |
                            SkShaper (底层排版)
                            SkFontMgr (字体管理)
                            SkUnicode (Unicode 支持)
```

## 主要类与结构体

### `Shaper`
```cpp
class Shaper final
```
- **性质**: 纯工具类（构造函数已删除），仅通过静态方法使用。
- **职责**: 实现 After Effects 文本排版语义。

### `Shaper::RunRec`
```cpp
struct RunRec
```
- **成员**: `fFont`（字体）、`fSize`（该运行的字形数量）
- **特性**: 标记为 `sk_is_trivially_relocatable`，支持高效的内存移动。

### `Shaper::ShapedGlyphs`
```cpp
struct ShapedGlyphs
```
- **职责**: 存储排版后的字形数据。
- **成员**:
  - `fRuns`: 运行记录列表
  - `fGlyphIDs`: 所有运行的字形 ID（合并存储）
  - `fGlyphPos`: 所有运行的字形位置
  - `fClusters`: 字形到原始文本的簇映射（可选）
- **方法**:
  - `computeBounds(BoundsType)`: 计算边界（保守或紧凑）
  - `draw(SkCanvas*, const SkPoint&, const SkPaint&)`: 绘制字形

### `Shaper::Fragment`
```cpp
struct Fragment
```
- **职责**: 排版片段，包含字形数据和位置信息。
- **成员**: `fGlyphs`（字形数据）、`fOrigin`（原点）、`fAdvance`（步进）、`fAscent`（上升高度）、`fLineIndex`（行索引）、`fIsWhitespace`（是否空白）

### `Shaper::Result`
```cpp
struct Result
```
- **职责**: 排版结果。
- **成员**: `fFragments`（片段列表）、`fMissingGlyphCount`（缺失字形数）、`fScale`（自动缩放比例）

### `Shaper::TextDesc`
```cpp
struct TextDesc
```
- **职责**: 排版输入描述，包含字体、尺寸、对齐、换行、方向等所有排版参数。

## 公共 API 函数

### 排版方法

#### `Shaper::Shape`（点文本版本）
```cpp
static Result Shape(const SkString& text, const TextDesc& desc, const SkPoint& point,
                    const sk_sp<SkFontMgr>&, const sk_sp<SkShapers::Factory>&);
```
- **功能**: 沿无限水平线进行文本布局，仅处理显式换行符（`\r`）。
- **适用于**: After Effects 点文本（Point Text）。

#### `Shaper::Shape`（框文本版本）
```cpp
static Result Shape(const SkString& text, const TextDesc& desc, const SkRect& box,
                    const sk_sp<SkFontMgr>&, const sk_sp<SkShapers::Factory>&);
```
- **功能**: 在指定矩形框内进行文本布局，自动注入换行以确保水平适配。
- **注意**: 结果不保证垂直适配（可能超出框底部）。
- **适用于**: After Effects 框文本（Box Text）。

### 辅助函数

#### `MakeStrictLinebreakUnicode`
```cpp
sk_sp<SkUnicode> SK_API MakeStrictLinebreakUnicode(sk_sp<SkUnicode>);
```
- **功能**: 创建一个 SkUnicode 包装器，抑制词内换行，仅在词边界断行。

## 枚举类型

### `VAlign`（垂直对齐）
- `kTop`: 首行排版顶部对齐文本框顶部（AE 框文本）
- `kTopBaseline`: 首行基线对齐文本框顶部（AE 点文本）
- `kHybridTop/Center/Bottom`: 混合模式（排版与视觉范围的较大值）
- `kVisualTop/Center/Bottom`: 视觉对齐模式（使用紧凑视觉边界）

### `ResizePolicy`（缩放策略）
- `kNone`: 使用指定字号
- `kScaleToFit`: 自动缩放以适配文本框
- `kDownscaleToFit`: 仅在超出时缩小

### `LinebreakPolicy`（换行策略）
- `kParagraph`: 自动断行以适配段落框宽度
- `kExplicit`: 仅在显式 `\r` 处断行

### `Direction`（文本方向）
- `kLTR`: 从左到右
- `kRTL`: 从右到左

### `Capitalization`（大小写）
- `kNone`: 不转换
- `kUpperCase`: 转为大写

### `Flags`（功能标志）
- `kFragmentGlyphs`: 将字形拆分为独立片段
- `kTrackFragmentAdvanceAscent`: 计算每个片段的步进和上升
- `kClusters`: 返回簇信息

## 内部实现细节

- **合并存储**: `ShapedGlyphs` 将所有运行的字形 ID 和位置合并到连续数组中，通过 `RunRec.fSize` 来分段读取，减少内存分配次数。
- **BoundsType 双模式**: `computeBounds` 支持保守边界（快速但可能较大）和紧凑边界（精确但可能较慢）两种模式。
- **TextDesc 引用语义**: `fTypeface` 使用 `const sk_sp<SkTypeface>&` 引用而非值传递，避免引用计数操作的开销。

## 依赖关系

- **Skia 核心**: `SkFont`, `SkPoint`, `SkRefCnt`, `SkScalar`, `SkTypes`, `SkCanvas`, `SkFontMgr`, `SkPaint`, `SkString`, `SkTypeface`, `SkRect`
- **`include/utils/SkTextUtils.h`**: `SkTextUtils::Align` 水平对齐枚举
- **`modules/skunicode/include/SkUnicode.h`**: Unicode 支持接口
- **`modules/skshaper`**: `SkShapers::Factory` 底层排版引擎工厂

## 设计模式与设计决策

- **静态工具类**: Shaper 删除了构造函数，所有功能通过静态方法提供，表明它是一个纯函数式工具。
- **值类型结果**: `Result` 和 `ShapedGlyphs` 都是值类型，排版结果通过值返回，简化了所有权管理。
- **AE 语义忠实**: 枚举值和排版行为忠实地对应 After Effects 的文本图层设置，确保 Lottie 动画的视觉一致性。
- **两种 Shape 重载**: 分别对应 AE 的点文本和框文本两种文本类型，这是 AE 文本系统的基本区分。
- **可选功能标志**: 通过 `Flags` 按需启用额外计算（如簇映射），避免不必要的开销。

## 性能考量

- **排版缓存**: Shaper 本身不提供缓存，每次调用 `Shape()` 都会重新排版。缓存逻辑在上层（如 TextAdapter）中实现。
- **自动缩放的迭代**: `kScaleToFit` 和 `kDownscaleToFit` 可能需要多次排版迭代来找到合适的字号，对长文本可能有明显开销。
- **片段化模式**: `kFragmentGlyphs` 会将每个字形拆分为独立片段，增加片段数量但允许逐字形动画（如 AE 的文本动画器效果）。
- **合并存储的局部性**: 将所有字形 ID 和位置合并到连续数组中提高了缓存局部性。

## 相关文件

- `modules/skottie/include/SkottieProperty.h` -- `TextPropertyValue` 使用了 Shaper 的枚举类型
- `modules/skottie/src/text/TextAdapter.h` -- 文本适配器，调用 Shaper::Shape()
- `modules/skottie/include/Skottie.h` -- `Animation::Builder::setTextShapingFactory()`
- `modules/skunicode/include/SkUnicode.h` -- Unicode 支持接口
- `modules/skshaper/include/SkShaper_factory.h` -- 底层排版引擎工厂
