# TextLayer - Skottie 文本图层

> 源文件: `modules/skottie/src/layers/TextLayer.cpp`

## 概述

TextLayer 实现了 Skottie 中文本图层的完整字体解析、字体匹配和渲染节点构建。该文件是 Skottie 文本渲染管线的核心入口，负责从 Lottie JSON 中解析字体列表和字形数据，通过多级字体回退策略（外部加载 -> 系统字体 -> 嵌入字形 -> 默认字体）解析字体，并最终将文本图层委托给 TextAdapter 进行渲染。该文件还支持变体字体（Variable Fonts）坐标和自定义字形组合（Glyph Compositions）。

## 架构位置

TextLayer 处于 Skottie 图层管线与文本渲染子系统的交汇处，承担字体基础设施的初始化和文本图层节点的创建。

```
Lottie JSON
  |
  +-> parseFonts() [字体列表解析]
  |     |
  |     +-> resolveNativeTypefaces() [原生字体解析]
  |     |     +-> fResourceProvider->loadTypeface()
  |     |     +-> fFontMgr->matchFamilyStyle()
  |     |     +-> 变体字体坐标应用
  |     |
  |     +-> resolveEmbeddedTypefaces() [嵌入字形解析]
  |           +-> CustomFont::Builder::parseGlyph()
  |           +-> CustomFont::GlyphCompMapper
  |
  +-> attachTextLayer() [渲染节点创建]
        +-> TextAdapter [文本渲染适配器]
```

## 主要类与结构体

### AnimationBuilder::FontInfo
- 存储单个字体的完整信息
- 成员：`fFamily`（字体族名）、`fStyle`（样式）、`fPath`（路径/URL）、`fAscent`（上升度）、`fTypeface`（已解析的字体对象）、`fCustomFontBuilder`（自定义字体构建器）、`fVariation`（变体坐标列表）
- `matches(family, style)` 方法用于按族名和样式匹配字体

### VariationInstance
- 类型为 `std::vector<SkFontArguments::VariationPosition::Coordinate>`
- 存储变体字体的设计坐标（axis tag + value 对）

## 公共 API 函数

### `AnimationBuilder::attachTextLayer`
```cpp
sk_sp<sksg::RenderNode> attachTextLayer(const skjson::ObjectValue& jlayer,
                                         LayerInfo*) const;
```
- 将文本图层的构建委托给 `TextAdapter`
- 传递 `fFontMgr`、`fCustomGlyphMapper`、`fLogger`、`fShapingFactory` 等依赖

### `AnimationBuilder::parseFonts`
```cpp
void parseFonts(const skjson::ObjectValue* jfonts,
                const skjson::ArrayValue* jchars);
```
- 解析 Lottie JSON 中的 `"fonts"` 对象和 `"chars"` 字形数组
- 第一遍：收集所有字体信息（名称、族、样式、路径、上升度、变体坐标）
- 根据 `kPreferEmbeddedFonts` 标志和字形组合（composition）的存在决定字体解析优先级
- 按优先级调用嵌入字体或原生字体解析

### `AnimationBuilder::resolveNativeTypefaces`
```cpp
bool resolveNativeTypefaces();
```
- 原生字体解析回退链：
  1. 外部加载（`fResourceProvider->loadTypeface()`）
  2. 旧版 API（`fResourceProvider->loadFont()` + `fFontMgr->makeFromData()`）
  3. 系统字体匹配（`fFontMgr->matchFamilyStyle()`）
  4. 默认字体（`fFontMgr->legacyMakeTypeface(nullptr, ...)`）
- 对有变体坐标的字体，调用 `fTypeface->makeClone(SkFontArguments)` 应用坐标
- 返回 `true` 表示所有字体已解析

### `AnimationBuilder::resolveEmbeddedTypefaces`
```cpp
bool resolveEmbeddedTypefaces(const skjson::ArrayValue& jchars);
```
- 解析 `"chars"` 数组中的字形数据，按 `(fFamily, style)` 关联到已声明的字体
- 使用 `CustomFont::Builder` 解析每个字形
- 最终通过 `CustomFont::Builder::detach()` 提交自定义字体
- 含字形组合的自定义字体被收集到 `fCustomGlyphMapper` 中

### `AnimationBuilder::findFont`
```cpp
const FontInfo* findFont(const SkString& font_name) const;
```
- 按字体名称在 `fFonts` 哈希表中查找字体信息

## 内部实现细节

### 字体样式解析
- `FontStyle()` 函数解析样式字符串（如 "Bold Italic"），不区分大小写
- 支持 23 种字重映射（regular, medium, bold, light, black, thin, extra, semibold 等）
- 支持 italic 和 oblique 斜体映射
- 使用 `parse_map` 模板函数进行字符串到枚举的查表映射

### 变体字体坐标解析
- `ParseVariation()` 从 `"fVariation"` JSON 对象解析变体坐标
- 每个坐标的轴标签必须是 4 个可打印 ASCII 字符（0x20-0x7E）
- 使用 `SkSetFourByteTag` 将字符串转换为 `SkFourByteTag`

### 字形匹配策略
- 嵌入字形通过 `(family, style)` 而非 `name` 匹配字体（与文本节点不同）
- 使用缓存的 `current_font` 指针优化相邻字形的字体查找（字形定义通常按字体聚集）
- 当前实现为线性搜索，注释建议如有性能问题可重构为两级哈希表

### 字体优先级决策
- 历史默认：原生字体优先于嵌入字形（因嵌入字形曾仅是系统字体的路径表示）
- 当存在字形组合（`type == 1`）或设置了 `kPreferEmbeddedFonts` 时，优先使用嵌入字体
- `has_comp_glyphs` lambda 检测是否存在组合字形

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkFont.h` / `SkFontMgr.h` / `SkFontStyle.h` | 字体创建与匹配 |
| `SkFontArguments.h` / `SkFourByteTag.h` | 变体字体坐标 |
| `SkTypeface.h` | 字体对象 |
| `SkTSearch.h` / `SkTHash.h` | 哈希表字体存储 |
| `TextAdapter.h` | 文本渲染适配器 |
| `Font.h` | CustomFont 自定义字体 |
| `SkResources.h` | 外部字体资源加载 |
| `SkJSONReader.h` / `SkottieJson.h` | JSON 解析 |
| `SkSGGroup.h` / `SkSGRenderNode.h` | Scene Graph 渲染节点 |

## 设计模式与设计决策

- **策略模式（字体回退链）**：多级字体解析策略形成回退链，每一级失败后自动尝试下一级，确保尽可能解析所有字体。
- **建造者模式**：`CustomFont::Builder` 逐步收集字形数据，最终一次性构建自定义字体对象。
- **缓存优化**：字形解析使用 `current_font` 缓存最近匹配的字体，利用字形数据按字体聚集的特性减少查找开销。
- **关注点分离**：字体基础设施（解析、匹配、回退）与文本渲染（TextAdapter）严格分离，TextLayer 仅负责前者。
- **外部化字体管理**：字体加载通过 `ResourceProvider` 和 `SkFontMgr` 两个抽象层实现外部化，支持不同平台和嵌入场景。
- **双通道字体解析**：嵌入字体和原生字体可按优先级调整解析顺序，通过 `kPreferEmbeddedFonts` 标志控制。

## 性能考量

- 字体解析在动画加载时一次性完成（`parseFonts`），不影响播放时性能。
- 字体哈希表 `fFonts` 提供 O(1) 的按名称查找。
- 嵌入字形的字体匹配为线性搜索（O(N) 其中 N 为字体数量），通常字体数量较少（< 10）。
- 变体字体的 `makeClone` 可能涉及字体表的重新构建，但仅在加载时执行一次。
- `attachTextLayer` 使用 `attachDiscardableAdapter` 模式，支持不再可见时的自动回收。
- 字形组合映射器 `fCustomGlyphMapper` 使用 `shrink_to_fit()` 减少内存占用。

## 相关文件

- `modules/skottie/src/text/TextAdapter.h` - 文本渲染适配器
- `modules/skottie/src/text/Font.h` - CustomFont 自定义字体构建
- `modules/skottie/src/text/TextShaper.cpp` - 文本排版引擎
- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder 定义及 FontInfo
- `modules/skresources/include/SkResources.h` - 资源提供者接口
- `modules/skottie/src/layers/FootageLayer.cpp` - 类似的资源加载模式
