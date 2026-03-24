# GlyphRun - 字形运行与构建器

> 源文件: `src/text/GlyphRun.h`, `src/text/GlyphRun.cpp`

## 概述

GlyphRun 模块定义了 Skia 文本渲染管线中的核心数据结构：GlyphRun（单次字形运行）、GlyphRunList（字形运行列表）和 GlyphRunBuilder（构建器）。这些类将上层的文本 API（drawText、drawTextBlob）转换为统一的字形 ID + 位置数据格式，供下游的 GPU 文本渲染子系统（SubRunContainer、TextBlob）消费。

## 架构位置

```
sktext 命名空间
  ├── GlyphRun      — 单个字形运行（字体 + 字形ID + 位置）
  ├── GlyphRunList   — 字形运行的有序集合
  └── GlyphRunBuilder — 从文本/Blob 构建 GlyphRunList
```

- **上层输入**: SkCanvas::drawText / drawTextBlob、SkTextBlob
- **下层输出**: SubRunContainer、TextBlob、SlugImpl

## 主要类与结构体

### GlyphRun
表示一个连续的字形运行，所有字形使用相同的字体。

**关键成员**:
- `fSource` (SkZip<const SkGlyphID, const SkPoint>): 字形 ID 和位置的配对数组
- `fText` (SkSpan<const char>): 原始文本数据（来自 TextBlob，可选）
- `fClusters` (SkSpan<const uint32_t>): 字形到文本的映射（可选）
- `fScaledRotations` (SkSpan<const SkVector>): RSXForm 旋转缩放信息（可选）
- `fFont` (SkFont): 此运行的字体

### GlyphRunList
字形运行的有序集合，可能关联到 SkTextBlob。

**关键成员与方法**:
- `fOriginalTextBlob` — 原始 TextBlob 指针（用于缓存回调，可为 null）
- `fSourceBounds` — 源空间边界矩形
- `fOrigin` — 绘制原点
- `canCache()` — 是否可缓存（有 TextBlob 时为 true）
- `uniqueID()` — 唯一标识符（来自 TextBlob）
- `anyRunsLCD()` — 是否包含 LCD 渲染的运行
- `makeBlob()` — 反向构造 SkTextBlob

支持迭代器模式，可用 range-for 遍历。

### GlyphRunBuilder
负责从各种输入源构建 GlyphRunList。

**主要方法**:
- `textToGlyphRunList()` — 从原始文本编码转换
- `blobToGlyphRunList()` — 从 SkTextBlob 转换
- `makeGlyphRunList()` — 从单个 GlyphRun 构建
- `convertRSXForm()` — 转换 RSXForm 数据

## 公共 API 函数

```cpp
// 从文本构建
const GlyphRunList& textToGlyphRunList(
    const SkFont& font, const SkPaint& paint,
    const void* bytes, size_t byteLength, SkPoint origin,
    SkTextEncoding encoding);

// 从 TextBlob 构建
const GlyphRunList& blobToGlyphRunList(const SkTextBlob& blob, SkPoint origin);
```

## 内部实现细节

### 文本到字形转换（textToGlyphRunList）
1. 通过 `textToGlyphIDs` 将文本编码（UTF-8/16/32/GlyphID）转换为字形 ID 数组
2. 通过 `draw_text_positions` 使用 Strike 计算每个字形的水平位置
3. 构建 GlyphRun 并计算源边界

### TextBlob 转换（blobToGlyphRunList）
处理四种定位模式：
- **kDefault_Positioning**: 按字形前进宽度自动布局
- **kHorizontal_Positioning**: X 坐标由用户指定，Y 使用偏移
- **kFull_Positioning**: 完全由用户指定 X/Y 位置
- **kRSXform_Positioning**: RSXform 定位（旋转/缩放/平移）

### 边界计算（glyphrun_source_bounds）
两种策略：
1. **保守边界**: 使用字体级别的 fontBounds + 位置范围（快速但可能偏大）
2. **精确边界**: 当 fontBounds 为空时（字体 bug），逐字形计算精确边界。支持 RSXForm 的任意变换。

### 缓冲区管理
GlyphRunBuilder 使用 `AutoTMalloc` 管理位置和旋转缓冲区，只在需要更大空间时才重新分配（高水位标记策略）。

## 依赖关系

- `SkFont` / `SkFontPriv` — 字体信息和字形指标
- `SkTextBlob` / `SkTextBlobPriv` — TextBlob 内部接口
- `SkStrikeSpec` / `SkBulkGlyphMetrics` — Strike 查找和批量字形指标
- `SkZip` — 配对数组视图
- `SkRSXform` — RSXform 表示

## 设计模式与设计决策

1. **Builder 模式**: GlyphRunBuilder 封装了复杂的构建逻辑，支持多种输入源
2. **零拷贝**: 对 kFull_Positioning 直接引用 TextBlob 中的位置数据
3. **高水位缓冲**: 位置缓冲区只增不减，避免频繁重分配
4. **可选数据**: text/clusters/scaledRotations 使用空 Span 表示不存在
5. **不可变设计**: GlyphRun 创建后不可修改

## 性能考量

- kFull_Positioning 模式零拷贝，是最快的路径
- kDefault_Positioning 需要逐字形计算位置（通过 Strike 获取前进宽度）
- 边界计算使用保守策略时 O(n)，精确策略时需要 Strike 访问
- GlyphRunBuilder 复用缓冲区避免了重复的堆分配

## 相关文件

- `include/core/SkFont.h` — 字体类
- `include/core/SkTextBlob.h` — TextBlob 公共 API
- `src/core/SkStrikeSpec.h` — Strike 规范
- `src/text/gpu/SubRunContainer.h` — SubRun 容器（GlyphRunList 的消费者）
- `src/text/gpu/TextBlob.h` — GPU TextBlob（GlyphRunList 的消费者）
