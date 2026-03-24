# skshaper/include - 文本整形公共接口

## 概述

`include/` 目录包含 skshaper 模块的所有公共头文件,定义了文本整形的完整 API 接口。核心头文件 `SkShaper.h` 定义了整形器基类、迭代器体系和结果处理器(RunHandler),其余头文件提供了不同整形后端的工厂函数。

这些接口设计遵循了高度的抽象和可组合性原则:整形器本身是可替换的(策略模式),输入通过迭代器提供(迭代器模式),输出通过回调传递(回调模式)。这种设计使得 skshaper 可以在不同平台和配置下灵活适配。

## 架构图

```
+----------------------------------------------------------+
|                    SkShaper.h (核心)                      |
|  +------------+  +------------+  +----------+            |
|  | SkShaper   |  | RunIterator|  |RunHandler|            |
|  | (整形器)    |  | (迭代器)   |  |(结果处理) |            |
|  +-----+------+  +-----+------+  +----+-----+           |
|        |               |              |                  |
+--------+---------------+--------------+------------------+
         |               |              |
  +------+------+  +-----+------+  +---+---+
  |             |  |            |  |       |
  v             v  v            v  v       v
+--------+ +--------+ +--------+ +--------+ +--------+
|harfbuzz| |coretext| |skunicode| |factory | |Blob    |
|  .h    | |  .h    | |  .h     | |  .h    | |Builder |
|(HB工厂)| |(CT工厂)| |(BiDi)   | |(抽象)  | |(便捷)  |
+--------+ +--------+ +--------+ +--------+ +--------+
```

## 目录结构

```
include/
|-- BUILD.bazel              # Bazel 构建规则
|-- SkShaper.h               # 核心接口: SkShaper, RunIterator, RunHandler
|-- SkShaper_factory.h       # 整形器工厂抽象: SkShapers::Factory
|-- SkShaper_harfbuzz.h      # HarfBuzz 后端工厂函数
|-- SkShaper_coretext.h      # CoreText 后端工厂函数
|-- SkShaper_skunicode.h     # SkUnicode BiDi 迭代器工厂
```

## 关键类与函数

### SkShaper.h - 核心接口

**SkShaper** - 整形器抽象基类:

```cpp
class SkShaper {
    // 核心整形方法
    virtual void shape(const char* utf8, size_t utf8Bytes,
                       FontRunIterator&, BiDiRunIterator&,
                       ScriptRunIterator&, LanguageRunIterator&,
                       const Feature* features, size_t featuresSize,
                       SkScalar width, RunHandler*) const = 0;

    // OpenType 特性结构
    struct Feature {
        SkFourByteTag tag;   // 特性标签 (如 "liga", "kern")
        uint32_t value;       // 特性值
        size_t start, end;    // 应用范围
    };
};
```

**RunIterator 体系** - 文本分段迭代器:

| 类 | 方法 | 说明 |
|----|------|------|
| `RunIterator` | `consume()`, `endOfCurrentRun()`, `atEnd()` | 基类 |
| `FontRunIterator` | `currentFont()` | 当前区段的字体 |
| `BiDiRunIterator` | `currentLevel()` | BiDi 嵌入级别 |
| `ScriptRunIterator` | `currentScript()` | ISO 15924 脚本标签 |
| `LanguageRunIterator` | `currentLanguage()` | BCP-47 语言标签 |

**Trivial 迭代器** - 将整个文本视为单一区段的简单实现:

| 类 | 用途 |
|----|------|
| `TrivialFontRunIterator` | 全文使用同一字体 |
| `TrivialBiDiRunIterator` | 全文同一 BiDi 级别 |
| `TrivialScriptRunIterator` | 全文同一脚本 |
| `TrivialLanguageRunIterator` | 全文同一语言 |

**RunHandler** - 整形结果回调接口:

```cpp
class RunHandler {
    struct RunInfo {
        const SkFont& fFont;     // 使用的字体
        uint8_t fBidiLevel;       // BiDi级别
        SkFourByteTag fScript;    // 脚本标签
        const char* fLanguage;    // 语言标签
        SkVector fAdvance;        // 总前进量
        size_t glyphCount;        // 字形数量
        Range utf8Range;          // 对应的UTF-8范围
    };
    struct Buffer {
        SkGlyphID* glyphs;       // 字形ID(必需)
        SkPoint* positions;       // 位置(必需)
        SkPoint* offsets;         // 偏移(可选)
        uint32_t* clusters;       // 簇映射(可选)
        SkPoint point;            // 基准偏移
    };
    // 回调生命周期
    virtual void beginLine() = 0;
    virtual void runInfo(const RunInfo&) = 0;
    virtual void commitRunInfo() = 0;
    virtual Buffer runBuffer(const RunInfo&) = 0;
    virtual void commitRunBuffer(const RunInfo&) = 0;
    virtual void commitLine() = 0;
};
```

**SkTextBlobBuilderRunHandler** - 便捷 RunHandler 实现:

```cpp
class SkTextBlobBuilderRunHandler final : public SkShaper::RunHandler {
    SkTextBlobBuilderRunHandler(const char* utf8Text, SkPoint offset);
    sk_sp<SkTextBlob> makeBlob();  // 获取构建的文本Blob
    SkPoint endPoint();             // 获取文本结束位置
};
```

### SkShaper_factory.h - 工厂抽象

```cpp
namespace SkShapers {
class Factory : public SkRefCnt {
    virtual std::unique_ptr<SkShaper> makeShaper(sk_sp<SkFontMgr>) = 0;
    virtual std::unique_ptr<SkShaper::BiDiRunIterator> makeBidiRunIterator(...) = 0;
    virtual std::unique_ptr<SkShaper::ScriptRunIterator> makeScriptRunIterator(...) = 0;
    virtual SkUnicode* getUnicode() = 0;
};
namespace Primitive {
    sk_sp<Factory> Factory();  // Primitive 工厂
}
}
```

### SkShaper_harfbuzz.h - HarfBuzz 后端

```cpp
namespace SkShapers::HB {
    std::unique_ptr<SkShaper> ShaperDrivenWrapper(sk_sp<SkUnicode>, sk_sp<SkFontMgr>);
    std::unique_ptr<SkShaper> ShapeThenWrap(sk_sp<SkUnicode>, sk_sp<SkFontMgr>);
    std::unique_ptr<SkShaper> ShapeDontWrapOrReorder(sk_sp<SkUnicode>, sk_sp<SkFontMgr>);
    std::unique_ptr<SkShaper::ScriptRunIterator> ScriptRunIterator(const char*, size_t);
    void PurgeCaches();
}
```

### SkShaper_coretext.h - CoreText 后端

```cpp
namespace SkShapers::CT {
    std::unique_ptr<SkShaper> CoreText();  // 仅 Apple 平台可用
}
```

### SkShaper_skunicode.h - BiDi 迭代器

```cpp
namespace SkShapers::unicode {
    std::unique_ptr<SkShaper::BiDiRunIterator> BidiRunIterator(
        sk_sp<SkUnicode>, const char* utf8, size_t utf8Bytes, uint8_t bidiLevel);
}
```

## 依赖关系

```
include/
  |-- Skia Core
  |   |-- SkFont, SkFontMgr, SkFontStyle
  |   |-- SkTextBlob, SkTextBlobBuilder
  |   |-- SkPoint, SkScalar, SkString, SkFourByteTag
  |   |-- SkRefCnt, SkTypes
  |-- skunicode (SkShaper_harfbuzz.h, SkShaper_skunicode.h)
  |   |-- SkUnicode (BiDi 分析)
```

## 设计模式分析

### 接口隔离
每个头文件只暴露特定后端的接口,客户端只需包含所需的头文件。例如只使用 HarfBuzz 后端时,只需包含 `SkShaper.h` 和 `SkShaper_harfbuzz.h`。

### 条件编译
后端可用性通过预处理宏控制:
- `SK_SHAPER_HARFBUZZ_AVAILABLE` - HarfBuzz 可用
- `SK_SHAPER_CORETEXT_AVAILABLE` - CoreText 可用
- `SK_SHAPER_UNICODE_AVAILABLE` - Unicode 支持可用

### 向后兼容
`SkShaper` 类中用 `SK_DISABLE_LEGACY_SKSHAPER_FUNCTIONS` 宏保护的遗留方法正在逐步迁移到命名空间工厂函数。

## 数据流

```
客户端
  |
  +-- 选择后端: SkShapers::HB / CT / Primitive
  +-- 创建 SkShaper 实例
  +-- 创建 RunIterator (Font/BiDi/Script/Language)
  +-- 创建 RunHandler (自定义 或 SkTextBlobBuilderRunHandler)
  |
  +-- shaper->shape(utf8, iterators, features, width, handler)
  |     |
  |     +-- handler->beginLine()
  |     +-- handler->runInfo(info)    // 报告每个 Run
  |     +-- handler->commitRunInfo()
  |     +-- buf = handler->runBuffer(info)  // 获取缓冲区
  |     +-- [填充 glyphs/positions/clusters]
  |     +-- handler->commitRunBuffer(info)
  |     +-- handler->commitLine()
  |
  +-- 使用整形结果 (SkTextBlob 或自定义格式)
```

## 相关文档与参考

- **实现代码**: `modules/skshaper/src/` - 各后端的具体实现
- **工厂辅助**: `modules/skshaper/utils/FactoryHelpers.h` - BestAvailable 等便捷函数
- **skparagraph**: `modules/skparagraph/` - 主要消费者
- **skunicode**: `modules/skunicode/` - Unicode 属性提供
