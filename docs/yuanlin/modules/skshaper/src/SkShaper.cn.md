# SkShaper.cpp - 文本整形核心实现

> 源文件: `modules/skshaper/src/SkShaper.cpp`

## 概述

`SkShaper.cpp` 是 Skia 文本整形（text shaping）模块的核心实现文件。它提供了将 UTF-8 文本转换为可渲染字形（glyph）序列的功能，包括字体回退（font fallback）机制、双向文本（BiDi）迭代、脚本检测迭代，以及基于 `SkTextBlobBuilder` 的运行处理器（RunHandler）实现。该文件通过条件编译支持 HarfBuzz、CoreText 和原始（Primitive）三种整形后端。

## 架构位置

该文件位于 `modules/skshaper/` 模块中，是 Skia 文本处理管线的关键环节。在整体架构中：

- **上层**：由 `SkShaper.h` 定义的公共接口供外部调用
- **同层**：与 `SkShaper_harfbuzz.h`、`SkShaper_coretext.h` 等平台特定实现并列
- **下层**：依赖 `SkFont`、`SkFontMgr`、`SkTypeface` 等 Skia 核心字体基础设施
- **下游**：`SkTextBlobBuilderRunHandler` 将整形结果输出为 `SkTextBlob` 用于渲染

## 主要类与结构体

### `FontMgrRunIterator`
- 继承自 `SkShaper::FontRunIterator`
- 核心职责：遍历 UTF-8 文本，为每个字符段（run）选择合适的字体
- 关键成员：
  - `fFont`：主字体，优先尝试
  - `fFallbackFont`：回退字体，当主字体缺少字形时使用
  - `fFallbackMgr`：`SkFontMgr` 实例，用于查找回退字体
  - `fLanguage`：语言迭代器指针，影响回退字体选择
- `consume()` 方法实现了复杂的字体选择逻辑：先尝试主字体，再尝试当前回退字体，最后通过 `matchFamilyStyleCharacter` 搜索新的回退字体

### `SkTextBlobBuilderRunHandler`
- 继承自 `SkShaper::RunHandler`
- 核心职责：将整形结果收集为 `SkTextBlob`
- 实现了完整的行处理生命周期：`beginLine` -> `runInfo` -> `commitRunInfo` -> `runBuffer` -> `commitRunBuffer` -> `commitLine`
- 管理行内度量（ascent、descent、leading）和当前位置

## 公共 API 函数

### `SkShaper::Make(sk_sp<SkFontMgr> fallback)`
创建最佳可用的整形器实例。优先选择 HarfBuzz（`MakeShapeThenWrap`），其次 CoreText，最后回退到 `PrimitiveText`。通过条件编译宏控制可用后端。

### `SkShaper::PurgeCaches()`
清除 HarfBuzz 整形器缓存（如果 HarfBuzz 可用）。

### `SkShaper::MakeBiDiRunIterator(...)`
创建双向文本迭代器。优先使用 ICU 实现，否则回退到 `TrivialBiDiRunIterator`。

### `SkShaper::MakeScriptRunIterator(...)`
创建脚本运行迭代器。优先使用 HarfBuzz 实现，否则回退到 `TrivialScriptRunIterator`。

### `SkShaper::MakeFontMgrRunIterator(...)` (两个重载)
创建 `FontMgrRunIterator` 实例。简单版本自动推断请求名称和样式；完整版本接受显式的请求字体名称、样式和语言迭代器。

### `SkShaper::MakeStdLanguageRunIterator(...)`
创建基于系统 locale 的语言运行迭代器。

### `SkTextBlobBuilderRunHandler::makeBlob()`
将收集的所有运行构建为最终的 `SkTextBlob`。

## 内部实现细节

### 字体回退策略（FontMgrRunIterator::consume）
1. 读取下一个 Unicode 字符
2. 按优先级尝试字体：主字体 > 当前回退字体 > 通过 `SkFontMgr` 搜索新回退字体 > 使用主字体（即使缺少字形）
3. 继续消费后续字符，遇到以下情况中断当前 run：
   - 当前使用回退字体但主字体可以处理新字符（偏好回到主字体）
   - 当前字体无法处理新字符且存在其他可用字体

### UTF-8 容错处理
`utf8_next` 函数将无效 UTF-8 序列替换为 Unicode 替换字符 U+FFFD，确保即使输入数据损坏也不会崩溃。

### SkTextBlobBuilderRunHandler 行布局
- `beginLine`：重置当前位置为行起始偏移，清零三个行度量变量
- `runInfo`：遍历行内所有 run，使用 `std::min`/`std::max` 累积最大 ascent（向上偏移，负值）、descent（向下偏移，正值）和 leading（行间距）
- `commitRunInfo`：将当前 Y 位置调整为基线（减去 ascent，因为 ascent 为负值所以实际是加上绝对值）
- `runBuffer`：通过 `SkTextBlobBuilder::allocRunTextPos` 一次性分配字形 ID、位置和 cluster 映射的内存。如果源 UTF-8 文本可用，还会拷贝对应范围的文本数据
- `commitRunBuffer`：将 cluster 数组中的偏移量从全局偏移转换为 run 内局部偏移（减去 `fClusterOffset`），然后将当前位置沿水平方向推进 `info.fAdvance`
- `commitLine`：将全局偏移量的 Y 分量推进一整行的高度（descent + leading - ascent），为下一行做准备

### FontMgrRunIterator 的 endOfCurrentRun 与 atEnd
- `endOfCurrentRun()` 返回当前游标位置相对于文本起始的字节偏移
- `atEnd()` 判断游标是否已到达文本末尾
- 这两个方法配合 `consume()` 实现了 `RunIterator` 的状态机协议

### FontMgrRunIterator 的成员变量布局
- `fCurrent`：当前解析位置的指针，随 `consume()` 前进
- `fBegin`：文本起始指针（const），用于计算偏移量
- `fEnd`：文本结束指针（const），用于边界检查
- `fFallbackMgr`：字体管理器（const），在整个迭代过程中不变
- `fFont`：主字体，类型面由构造函数设置
- `fFallbackFont`：回退字体，类型面随回退查找结果动态变化
- `fCurrentFont`：指向当前活跃字体（`fFont` 或 `fFallbackFont`）的指针
- `fRequestName`/`fRequestStyle`：回退查找的请求参数
- `fLanguage`：可选的语言迭代器指针，影响回退选择

## 依赖关系

- **核心 Skia**：`SkFont`、`SkFontMgr`、`SkFontMetrics`、`SkFontStyle`、`SkTypeface`、`SkTextBlobBuilder`
- **内部工具**：`SkUTF`（UTF-8 解码）、`SkTFitsIn`（安全整数范围检查）
- **条件依赖**：
  - `SkShaper_harfbuzz.h`（当 `SK_SHAPER_HARFBUZZ_AVAILABLE` 定义时）
  - `SkShaper_coretext.h`（当 `SK_SHAPER_CORETEXT_AVAILABLE` 定义时）
- **标准库**：`<algorithm>`、`<cstring>`、`<locale>`、`<string>`

## 设计模式与设计决策

### 策略模式
通过 `RunIterator` 接口族（FontRunIterator、BiDiRunIterator、ScriptRunIterator、LanguageRunIterator）实现策略模式，允许整形器使用不同的文本分析策略。

### 工厂方法模式
`SkShaper::Make` 和各个 `MakeXxxRunIterator` 静态方法均为工厂方法，根据编译配置和运行时可用性选择最佳实现。

### 优雅降级
所有工厂方法在高级后端不可用时均提供 Trivial（简单）回退实现，确保功能完整性。

### 遗留兼容性
通过 `SK_DISABLE_LEGACY_SKSHAPER_FUNCTIONS` 宏控制旧 API 的可用性，支持渐进式 API 迁移。当该宏定义时，`Make`、`PurgeCaches`、`MakeBiDiRunIterator`、`MakeScriptRunIterator` 等遗留静态方法将被禁用，客户端应迁移到基于 `SkShapers::Factory` 的新 API。

### 条件编译多后端架构
文件顶部的 `#if defined(SK_SHAPER_HARFBUZZ_AVAILABLE)` 和 `#if defined(SK_SHAPER_CORETEXT_AVAILABLE)` 保护块实现了编译期后端选择。这种设计允许在不同平台上构建不同能力的整形器，同时保持统一的 API 表面。

### 两阶段构造
`FontMgrRunIterator` 的两个构造函数体现了便利构造和完整构造的分层设计。简单构造函数委托给完整构造函数，传入从字体对象推导的默认值（`nullptr` 作为请求名称，字体的 fontStyle 作为请求样式）。

## 性能考量

- **字体缓存回退**：`FontMgrRunIterator` 保持当前回退字体（`fFallbackFont`），避免对连续相同语言/脚本的字符重复进行字体搜索。当连续多个字符需要同一回退字体时，仅在首次查找时调用 `matchFamilyStyleCharacter`
- **主字体优先**：即使回退字体可以处理字符，当主字体也能处理时优先回到主字体，减少不必要的 run 切分。这减少了下游字形缓冲区分配次数
- **SkTextBlobBuilder**：使用预分配的 `allocRunTextPos` 减少内存分配次数。一次分配即可获得字形 ID、位置和 cluster 映射所需的全部内存
- **整数溢出保护**：通过 `SkTFitsIn` 在 `runBuffer` 中进行安全的 size_t 到 int 转换，当值超出 int 范围时使用 INT_MAX 作为安全上限
- **Run 合并优化**：`consume()` 方法在内部循环中尽可能延长当前 run，只有在字体切换不可避免时才中断。这最大限度减少了 run 数量
- **条件编译零开销**：未启用的后端（如 HarfBuzz、CoreText）在编译后完全不存在，不产生任何运行时开销
- **UTF-8 顺序遍历**：文本始终以前向顺序遍历，友好于 CPU 缓存预取机制

## 相关文件

- `modules/skshaper/include/SkShaper.h` - 公共接口定义，包含 SkShaper 基类、RunIterator 接口族、RunHandler 接口以及 SkTextBlobBuilderRunHandler
- `modules/skshaper/include/SkShaper_harfbuzz.h` - HarfBuzz 后端接口，提供 `SkShapers::HB` 命名空间的工厂函数
- `modules/skshaper/include/SkShaper_coretext.h` - CoreText 后端接口，提供 `SkShapers::CT` 命名空间的工厂函数
- `modules/skshaper/include/SkShaper_factory.h` - `SkShapers::Factory` 抽象工厂接口
- `modules/skshaper/src/SkShaper_factory.cpp` - 原始工厂实现（PrimitiveFactory）
- `modules/skshaper/src/SkShaper_primitive.cpp` - 原始文本整形器实现
- `include/core/SkFont.h` - SkFont 字体类定义
- `include/core/SkFontMgr.h` - SkFontMgr 字体管理器接口，提供 `matchFamilyStyleCharacter` 字体回退
- `include/core/SkFontMetrics.h` - SkFontMetrics 字体度量结构体（ascent、descent、leading）
- `include/core/SkTypeface.h` - SkTypeface 字体面接口
- `include/core/SkTextBlob.h` - SkTextBlob 和 SkTextBlobBuilder 定义
- `include/core/SkFontStyle.h` - SkFontStyle 字体样式（weight、width、slant），用于字体回退匹配
- `src/base/SkUTF.h` - UTF-8 编解码工具，提供 `SkUTF::NextUTF8` 函数
- `include/private/base/SkTFitsIn.h` - 安全整数范围检查模板
- `<locale>` - 标准库，`MakeStdLanguageRunIterator` 使用 `std::locale().name()` 获取系统语言
