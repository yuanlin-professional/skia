# SkShaper - 文本塑形器核心接口

> 源文件: `modules/skshaper/include/SkShaper.h`

## 概述

SkShaper.h 定义了 Skia 文本塑形模块的核心接口。SkShaper 是一个抽象基类，负责将 UTF-8 文本转换为定位好的字形序列，包括字体选择、BiDi 处理、脚本检测、换行和字形布局。该文件同时定义了运行迭代器（RunIterator）体系和运行处理器（RunHandler）回调接口，以及便利类 SkTextBlobBuilderRunHandler。

## 架构位置

SkShaper 是 skshaper 模块的核心抽象层。它被 skparagraph（段落排版）和其他需要文本排版的模块使用。具体实现包括 HarfBuzz 后端、CoreText 后端和 Primitive 后端。

**调用流程**: 客户端 -> `SkShaper::shape()` -> RunIterator 系列（字体/BiDi/脚本/语言） -> RunHandler 回调

## 主要类与结构体

### `SkShaper`（抽象基类）
文本塑形器的核心接口，提供多个 `shape()` 方法重载。

### RunIterator 体系

#### `RunIterator`（基类）
运行迭代器接口，用于将文本分割为具有相同属性的运行段：
- `consume()`: 消费当前运行并前进到下一个
- `endOfCurrentRun()`: 当前运行的结束偏移
- `atEnd()`: 是否已到达末尾

#### `FontRunIterator`
字体运行迭代器，提供 `currentFont()` 获取当前运行的字体。

#### `BiDiRunIterator`
双向文本运行迭代器，提供 `currentLevel()` 获取 Unicode BiDi 嵌入级别。

#### `ScriptRunIterator`
脚本运行迭代器，提供 `currentScript()` 获取 ISO 15924 脚本标签。

#### `LanguageRunIterator`
语言运行迭代器，提供 `currentLanguage()` 获取 BCP-47 语言标签。

#### Trivial* 系列
简单迭代器实现，将整个文本视为单一运行：
- `TrivialFontRunIterator`: 固定字体
- `TrivialBiDiRunIterator`: 固定 BiDi 级别
- `TrivialScriptRunIterator`: 固定脚本
- `TrivialLanguageRunIterator`: 固定语言

### `SkShaper::Feature`
OpenType 特性描述：tag、value 和 UTF-8 范围。

### `RunHandler`（回调接口）
接收塑形结果的回调接口，定义了完整的行处理流程：

| 回调 | 说明 |
|------|------|
| `beginLine()` | 开始新行 |
| `runInfo(RunInfo&)` | 报告运行信息（预计算阶段） |
| `commitRunInfo()` | 所有运行信息已报告 |
| `runBuffer(RunInfo&)` -> `Buffer` | 请求输出缓冲区 |
| `commitRunBuffer(RunInfo&)` | 缓冲区已填充 |
| `commitLine()` | 行处理完成 |

#### `RunInfo` 结构体
运行元信息：字体、BiDi 级别、脚本标签、语言、前进量、字形数量和 UTF-8 范围。

#### `Buffer` 结构体
输出缓冲区：glyphs（必需）、positions（必需）、offsets（可选）、clusters（可选）和基点。

### `SkTextBlobBuilderRunHandler`
RunHandler 的便利实现，将塑形结果直接构建为 SkTextBlob，适合简单的文本渲染场景。

## 公共 API 函数

### 工厂方法（部分为旧版 API）

| 函数 | 说明 |
|------|------|
| `MakePrimitive()` | 创建原始塑形器 |
| `MakeShaperDrivenWrapper(fontmgr)` | 创建 HarfBuzz 塑形驱动换行器 |
| `MakeShapeThenWrap(fontmgr)` | 创建 HarfBuzz 先塑形后换行器 |
| `MakeCoreText()` | 创建 CoreText 塑形器 |
| `Make(fontmgr)` | 创建最佳可用塑形器 |
| `PurgeCaches()` | 清理所有缓存 |
| `MakeFontMgrRunIterator(...)` | 创建带字体回退的字体运行迭代器 |
| `MakeStdLanguageRunIterator(...)` | 创建标准语言运行迭代器 |

### 核心塑形方法

```cpp
virtual void shape(const char* utf8, size_t utf8Bytes,
                   FontRunIterator&, BiDiRunIterator&,
                   ScriptRunIterator&, LanguageRunIterator&,
                   const Feature* features, size_t featuresSize,
                   SkScalar width, RunHandler*) const = 0;
```

### Primitive 命名空间

| 函数 | 说明 |
|------|------|
| `SkShapers::Primitive::PrimitiveText()` | 创建原始塑形器 |
| `SkShapers::Primitive::TrivialBiDiRunIterator(...)` | 创建简单 BiDi 迭代器 |
| `SkShapers::Primitive::TrivialScriptRunIterator(...)` | 创建简单脚本迭代器 |

## 内部实现细节

### TrivialRunIterator 模板
使用 CRTP 模式的模板基类，将整个文本视为单一运行。`consume()` 调用后直接标记 `fAtEnd = true`。

### DLL 导出控制
通过 `SKSHAPER_API` 宏支持 DLL 构建，与 skcms 的 `SKCMS_API` 模式一致。

### 旧版 API 守护
`SK_DISABLE_LEGACY_SKSHAPER_FUNCTIONS` 宏控制旧版静态工厂方法的可见性，新代码应使用命名空间级函数。

## 依赖关系

- **SkFont**: 字体描述
- **SkTextBlob / SkTextBlobBuilder**: 文本 blob 构建
- **SkFontMgr**: 字体管理和回退
- **SkFourByteTag**: 四字节标签类型
- **SkPoint / SkScalar**: 几何类型

## 设计模式与设计决策

1. **迭代器模式**: RunIterator 体系将文本属性分割解耦，每种属性（字体、BiDi、脚本、语言）由独立迭代器管理。
2. **回调模式**: RunHandler 采用两阶段回调（runInfo -> commitRunInfo -> runBuffer -> commitRunBuffer），允许处理器在分配缓冲区前预知所有运行信息。
3. **多后端策略**: 通过条件编译宏（SK_SHAPER_HARFBUZZ_AVAILABLE 等）支持多种塑形后端。
4. **向后兼容**: 旧版 API 通过 `SK_DISABLE_LEGACY_SKSHAPER_FUNCTIONS` 逐步淘汰。

## 性能考量

- RunHandler 的两阶段回调允许批量分配缓冲区，减少内存分配次数
- TrivialRunIterator 用于不需要复杂属性分割的场景，几乎零开销
- SkTextBlobBuilderRunHandler 直接构建 SkTextBlob，避免中间数据结构

## 使用示例

### 基本文本塑形
```cpp
auto shaper = SkShaper::Make(fontMgr);
SkTextBlobBuilderRunHandler handler("Hello World", {0, 0});
shaper->shape("Hello World", 11, font, true, width, &handler);
auto blob = handler.makeBlob();
canvas->drawTextBlob(blob, x, y, paint);
```

### 使用运行迭代器
```cpp
auto fontIter = SkShaper::MakeFontMgrRunIterator(utf8, len, font, fontMgr);
auto bidiIter = SkShapers::unicode::BidiRunIterator(unicode, utf8, len, 0);
auto scriptIter = SkShapers::HB::ScriptRunIterator(utf8, len);
auto langIter = SkShaper::MakeStdLanguageRunIterator(utf8, len);

shaper->shape(utf8, len, *fontIter, *bidiIter, *scriptIter, *langIter,
              features, featuresSize, width, &handler);
```

## 相关文件

- `modules/skshaper/src/SkShaper_harfbuzz.cpp` - HarfBuzz 后端实现
- `modules/skshaper/src/SkShaper_primitive.cpp` - Primitive 后端实现
- `modules/skshaper/src/SkShaper_coretext.cpp` - CoreText 后端实现
- `modules/skshaper/include/SkShaper_factory.h` - 工厂接口
- `modules/skshaper/utils/FactoryHelpers.h` - 工厂便利类
