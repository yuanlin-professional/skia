# shape

> 源文件: modules/skplaintexteditor/src/shape.h, modules/skplaintexteditor/src/shape.cpp

## 概述

`shape` 模块为 `skplaintexteditor` 纯文本编辑器提供文本整形(text shaping)功能。该模块使用 HarfBuzz 整形引擎将 UTF-8 文本转换为可绘制的字形,并处理自动换行、单词边界检测、字形边界计算等编辑器所需的功能。

与段落布局系统的 `OneLineShaper` 不同,该整形器更简单直接,专注于纯文本编辑场景,不处理复杂的样式和段落布局。

## 架构位置

该模块位于 `skplaintexteditor` 纯文本编辑器模块中:

```
skia/modules/
├── skplaintexteditor/
│   └── src/
│       ├── shape.h/.cpp              # 文本整形
│       ├── editor.h/.cpp             # 文本编辑器(使用shape)
│       └── word_boundaries.h/.cpp    # 单词边界检测
└── skshaper/
    └── include/
        ├── SkShaper.h                # 整形器接口
        └── SkShaper_harfbuzz.h       # HarfBuzz实现
```

## 主要类与结构体

### ShapeResult
```cpp
struct ShapeResult {
    sk_sp<SkTextBlob> blob;                    // 整形后的文本块
    std::vector<std::size_t> lineBreakOffsets; // 换行位置(UTF-8字节偏移)
    std::vector<SkRect> glyphBounds;           // 字形边界框数组
    std::vector<bool> wordBreaks;              // 单词边界标记
    int verticalAdvance;                       // 垂直前进距离
};
```
整形结果结构体,包含所有编辑器需要的信息。

### RunHandler
```cpp
class RunHandler final : public SkShaper::RunHandler
```
内部类,实现 HarfBuzz 的 `RunHandler` 接口,接收整形结果并构建 `SkTextBlob`。

**核心成员:**
- `fBuilder`: `SkTextBlobBuilder`,构建最终的文本块
- `fLineEndOffsets`: 记录每行的结束位置
- `fCurrentPosition`: 当前字形位置
- `fOffset`: 当前行的起始偏移
- `fMaxRunAscent/fMaxRunDescent/fMaxRunLeading`: 行度量

## 公共 API 函数

### Shape
```cpp
ShapeResult Shape(const char* utf8text,
                  size_t textByteLen,
                  const SkFont& font,
                  sk_sp<SkFontMgr> fontMgr,
                  const char* locale,
                  float width)
```
对文本进行整形,生成可绘制的字形和布局信息。

**参数:**
- `utf8text`: UTF-8 文本指针
- `textByteLen`: 文本字节长度
- `font`: 字体对象
- `fontMgr`: 字体管理器(用于字体回退)
- `locale`: 语言区域(如 "en_US", "zh_CN")
- `width`: 最大行宽,超出会自动换行

**返回:** `ShapeResult` 包含所有整形和布局结果

**功能:**
- 使用 HarfBuzz 进行文本整形
- 自动换行(基于宽度限制)
- 计算字形边界
- 检测单词边界
- 生成可绘制的 `SkTextBlob`

## 内部实现细节

### RunHandler 回调实现
作为 `SkShaper::RunHandler`,实现整形过程的回调:

```cpp
void RunHandler::beginLine() {
    fCurrentPosition = fOffset;
    fMaxRunAscent = 0;
    fMaxRunDescent = 0;
    fMaxRunLeading = 0;
}

void RunHandler::runInfo(const RunInfo& info) {
    SkFontMetrics metrics;
    info.fFont.getMetrics(&metrics);
    fMaxRunAscent = std::min(fMaxRunAscent, metrics.fAscent);
    fMaxRunDescent = std::max(fMaxRunDescent, metrics.fDescent);
    fMaxRunLeading = std::max(fMaxRunLeading, metrics.fLeading);
}

void RunHandler::commitRunInfo() {
    fCurrentPosition.fY -= fMaxRunAscent;  // 调整到基线
}

Buffer RunHandler::runBuffer(const RunInfo& info) {
    const auto& runBuffer = fBuilder.allocRunTextPos(info.fFont, glyphCount, utf8RangeSize);
    fCurrentGlyphs = runBuffer.glyphs;
    fCurrentPoints = runBuffer.points();

    // 复制 UTF-8 文本
    if (runBuffer.utf8text && fUtf8Text) {
        memcpy(runBuffer.utf8text, fUtf8Text + info.utf8Range.begin(), utf8RangeSize);
    }

    fClusters = runBuffer.clusters;
    return {runBuffer.glyphs, runBuffer.points(), nullptr, runBuffer.clusters, fCurrentPosition};
}

void RunHandler::commitRunBuffer(const RunInfo& info) {
    // 调整簇索引为相对偏移
    for (int i = 0; i < fGlyphCount; ++i) {
        fClusters[i] -= fClusterOffset;
    }
    fCurrentPosition += info.fAdvance;
    fTextOffset = std::max(fTextOffset, info.utf8Range.end());
}

void RunHandler::commitLine() {
    fLineEndOffsets.push_back(fTextOffset);
    fOffset.fY += fMaxRunDescent - fMaxRunAscent + fMaxRunLeading;
}
```

### Unicode 实现选择
与 `word_boundaries` 模块类似,按优先级选择 Unicode 实现:

```cpp
sk_sp<SkUnicode> get_unicode() {
#if defined(SK_UNICODE_ICU_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU::Make()) {
        return unicode;
    }
#endif
#if defined(SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::Libgrapheme::Make()) {
        return unicode;
    }
#endif
#if defined(SK_UNICODE_ICU4X_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU4X::Make()) {
        return unicode;
    }
#endif
    return nullptr;
}
```

### 整形主流程
`Shape()` 函数协调整形过程(具体实现在未展示的代码部分):
1. 创建 `RunHandler` 接收整形结果
2. 创建 HarfBuzz 整形器
3. 配置换行参数(宽度限制)
4. 执行整形操作
5. 检测单词边界
6. 计算字形边界
7. 构建并返回 `ShapeResult`

### 字形边界计算
每个字形的边界矩形用于:
- 光标定位(点击位置转文本位置)
- 文本选择高亮
- 字形级别的编辑操作

### 换行处理
自动换行基于:
- 指定的最大行宽
- 软换行点(空格、标点等)
- 硬换行符(换行符)

## 依赖关系

### 核心依赖
- **SkShaper**: HarfBuzz 整形器接口
- **SkUnicode**: Unicode 属性查询
- **SkTextBlob**: 整形结果的存储格式
- **word_boundaries**: 单词边界检测

### 使用者
- **skplaintexteditor**: 纯文本编辑器主类

### 依赖图
```
Shape()
    ↓ (uses)
RunHandler + SkShaper (HarfBuzz) + SkUnicode
    ↓ (produces)
ShapeResult (SkTextBlob + 布局信息)
    ↓ (used by)
纯文本编辑器
```

## 设计模式与设计决策

### 结果聚合
`ShapeResult` 将所有整形和布局结果聚合到一个结构体:
- 简化接口,一次调用获取所有信息
- 减少多次函数调用开销
- 便于结果缓存

### 回调模式
`RunHandler` 实现 `SkShaper::RunHandler` 回调接口:
- 与 HarfBuzz 整形器集成
- 逐步接收整形结果
- 支持流式处理大文本

### 简化设计
相比段落布局系统,该整形器更简单:
- 单一字体(无字体回退复杂逻辑)
- 单一样式(无样式合并)
- 固定宽度换行(无复杂对齐)

适合纯文本编辑器的需求。

## 性能考量

### 内存使用
- **ShapeResult**: 存储完整的整形和布局结果
- **字形边界数组**: 与字形数量线性相关
- **单词边界数组**: 与文本字节长度线性相关

### 时间复杂度
- **整形**: O(n),由 HarfBuzz 决定
- **单词边界**: O(n)
- **字形边界计算**: O(m),m 为字形数量
- **总体**: O(n),线性时间复杂度

### 优化机会
- 缓存整形结果,文本不变时复用
- 增量更新:仅重新整形修改的部分
- 延迟计算:仅在需要时计算字形边界

## 相关文件

### 整形相关
- `modules/skshaper/include/SkShaper.h`: 整形器接口
- `modules/skshaper/include/SkShaper_harfbuzz.h`: HarfBuzz 实现

### Unicode 处理
- `modules/skunicode/include/SkUnicode.h`: Unicode 接口
- `modules/skplaintexteditor/src/word_boundaries.h`: 单词边界检测

### 使用方
- `modules/skplaintexteditor/src/editor.h/.cpp`: 纯文本编辑器

### 核心依赖
- `include/core/SkTextBlob.h`: 文本块
- `include/core/SkFont.h`: 字体对象
