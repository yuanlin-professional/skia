# SkShaper_coretext - CoreText 文本塑形接口

> 源文件: `modules/skshaper/include/SkShaper_coretext.h`

## 概述

SkShaper_coretext.h 声明了基于 Apple CoreText 框架的文本塑形器创建函数。CoreText 是 macOS 和 iOS 平台的原生文本排版引擎，提供高质量的字形选择和定位功能。该接口作为 HarfBuzz 的平台替代方案，在 Apple 平台上使用系统原生排版能力。

## 架构位置

位于 `SkShapers::CT` 命名空间，是 skshaper 模块的 Apple 平台后端。仅在 `SK_SHAPER_CORETEXT_AVAILABLE` 定义时可用。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CoreText()` | 创建 CoreText 塑形器实例 |

## 依赖关系

- **SkShaper**: 塑形器基类
- **CoreText / CoreGraphics / CoreFoundation**: Apple 平台框架

## 设计模式与设计决策

1. **平台适配**: 利用 Apple 原生排版引擎，确保在 macOS/iOS 上获得与系统一致的排版效果。
2. **极简接口**: 仅需一个无参工厂函数，CoreText 自行处理字体选择和 BiDi。

## 性能考量

- CoreText 由操作系统高度优化，在 Apple 平台上通常性能优于 HarfBuzz
- 无需额外的 Unicode 库依赖（系统内置）

## 相关文件

- `modules/skshaper/src/SkShaper_coretext.cpp` - CoreText 后端实现
- `modules/skshaper/include/SkShaper.h` - SkShaper 基类
- `modules/skshaper/src/SkShaper_coretext.cpp` - 实现文件

## 使用示例

```cpp
// 创建 CoreText 塑形器
auto shaper = SkShapers::CT::CoreText();

// 配合 SkTextBlobBuilderRunHandler 使用
SkTextBlobBuilderRunHandler handler(utf8, {0, 0});
SkFont font(typeface, fontSize);
SkShaper::TrivialFontRunIterator fontIter(font, utf8Bytes);
SkShaper::TrivialBiDiRunIterator bidiIter(0, utf8Bytes);
SkShaper::TrivialScriptRunIterator scriptIter(0, utf8Bytes);
SkShaper::TrivialLanguageRunIterator langIter("en", utf8Bytes);
shaper->shape(utf8, utf8Bytes, fontIter, bidiIter, scriptIter, langIter,
              nullptr, 0, width, &handler);
```

## 使用注意事项

1. 仅在 macOS 和 iOS 平台上可用
2. 需要编译时定义 `SK_SHAPER_CORETEXT_AVAILABLE`
3. CoreText 自行处理 BiDi 和脚本，传入的迭代器参数被忽略
4. 不支持 OpenType Feature 参数
5. 字体回退由 CoreText 系统自动处理
6. 排版结果可能与 HarfBuzz 后端略有差异，取决于平台版本

### CoreText vs HarfBuzz 选择指南
| 场景 | 推荐后端 |
|------|---------|
| Apple 平台，需要与系统 UI 一致 | CoreText |
| 跨平台一致性 | HarfBuzz |
| 需要完整 OpenType Feature 控制 | HarfBuzz |
| 最小依赖 | CoreText（Apple 平台） |
| 复杂文字排版精确控制 | HarfBuzz |
| 连字符断行支持 | CoreText |

### 内部处理的排版特性
CoreText 塑形器内部自动处理以下特性，无需外部迭代器：
- Unicode 双向文本（BiDi）分析
- 脚本检测和切换
- 字体回退（对缺失字形自动选择系统字体）
- 按宽度换行（使用 CTTypesetterSuggestLineBreak）
- 基本的 OpenType 特性应用
