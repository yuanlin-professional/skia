# SkShaper_coretext 实现 - CoreText 文本塑形器

> 源文件: `modules/skshaper/src/SkShaper_coretext.cpp`

## 概述

SkShaper_coretext.cpp 实现了基于 Apple CoreText 框架的文本塑形器 SkShaper_CoreText。它利用 macOS/iOS 平台的原生排版引擎进行文本塑形和换行，支持字体回退、字形定位和按宽度换行。CoreText 内部处理了 BiDi、脚本检测和复杂文字排版，因此该实现不需要外部的 BiDi 或脚本迭代器。

## 架构位置

该文件是 skshaper 模块的 Apple 平台后端，仅在 macOS 和 iOS 上可用。它处于 SkShaper 抽象接口和 Apple CoreText/CoreGraphics 框架之间的桥接层。

**调用流程**: `SkShaper::shape()` -> `SkShaper_CoreText::shape()` -> `CTTypesetter` -> `CTLine` -> RunHandler 回调

## 主要类与结构体

### `SkShaper_CoreText`
继承自 SkShaper，使用 CoreText 进行塑形。无构造参数，所有 CoreText 对象在 `shape()` 调用内创建。

### `LineBreakIter`
基于 CTTypesetter 的换行迭代器：
- 使用 `CTTypesetterSuggestLineBreak` 建议换行位置
- 使用 `CTTypesetterCreateLine` 创建行对象
- 自动推进起始位置

### `UTF16ToUTF8IndicesMap`
UTF-16 到 UTF-8 索引映射器：
- `setUTF8()`: 构建映射表
- `mapIndex()`: 单个索引转换
- `mapRange()`: 范围转换
- CoreText 使用 UTF-16 索引，SkShaper 使用 UTF-8，需要此映射

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkShapers::CT::CoreText()` | 创建 CoreText 塑形器实例 |

## 内部实现细节

### 塑形流程
1. **准备阶段**:
   - 从 FontRunIterator 获取初始字体
   - 将 UTF-8 转换为 CFString
   - 构建 UTF16ToUTF8IndicesMap 索引映射
   - 从 SkFont 创建 CTFont（`create_ctfont_from_font`）
   - 创建 CFAttributedString 并关联字体属性
   - 创建 CTTypesetter

2. **逐行处理**:
   - 使用 LineBreakIter 获取 CTLine
   - 获取 CTLine 中的所有 CTRun
   - **第一遍（runInfo）**: 遍历所有 run，收集字形数量、前进量和 UTF-8 范围
   - 调用 `commitRunInfo()`
   - **第二遍（runBuffer）**: 遍历所有 run，填充字形 ID、位置、偏移和簇映射

### CTFont 创建（`create_ctfont_from_font`）
从 SkFont -> SkTypeface -> CTFontRef -> 带正确大小的 CTFont 副本。

### 字体回退（`run_to_font`）
从 CTRun 的属性字典中提取 CTFont，通过 `SkMakeTypefaceFromCTFont` 转换回 SkTypeface，创建新的 SkFont。这支持 CoreText 的自动字体回退（如中文字符自动使用 CJK 字体）。

### 坐标系映射
- CoreText 使用 CFRange（UTF-16 偏移）标识文本范围
- 通过 `UTF16ToUTF8IndicesMap` 转换为 UTF-8 偏移
- CoreText 的字形位置直接映射到 SkShaper 的 positions

### 已知限制
- TODO: 不支持 BiDi 级别传递（`fBidiLevel` 硬编码为 0）
- TODO: 不支持脚本和语言标签传递
- 不使用外部 BiDi 和脚本迭代器参数

### 追踪（Tracking）
代码中有已禁用的 kCTTracking_AttributeName 和 kCTKernAttributeName 实验代码。

## 依赖关系

- **CoreText / CoreGraphics / CoreFoundation**: Apple 平台框架
- **SkTypeface_mac.h**: SkTypeface 与 CTFont 互转
- **SkUniqueCFRef**: CoreFoundation 对象的 RAII 包装
- **SkCGBase**: CoreGraphics 类型兼容
- **SkFont / SkFontPriv**: 字体访问
- **SkUTF**: UTF-8/UTF-16 转换
- **SkShaper**: 基类和 RunHandler

## 设计模式与设计决策

1. **委托排版引擎**: 将所有复杂排版逻辑（BiDi、脚本检测、字体回退、换行）委托给 CoreText，减少自身复杂度。
2. **两遍输出**: 第一遍收集信息（runInfo），第二遍填充数据（runBuffer），符合 RunHandler 的两阶段协议。
3. **索引映射桥接**: UTF16ToUTF8IndicesMap 解决了 CoreText（UTF-16）和 SkShaper（UTF-8）之间的编码不匹配问题。
4. **字体信息恢复**: 通过 `run_to_font` 从 CTRun 恢复字体信息，支持 CoreText 的自动字体回退。

## 性能考量

- **CoreText 高度优化**: 作为系统框架，CoreText 经过 Apple 深度优化，包括字形缓存和硬件加速
- **UTF-16 索引映射**: O(n) 预处理，后续查询 O(1)
- **字体存储优化**: `fontStorage` 使用 `reserve(runCount)` 确保引用不失效
- **CTTypesetter 换行**: 比手动计算更准确，支持连字符断行
- **单 CTTypesetter**: 对整个文本创建一个 typesetter，CoreText 内部优化塑形缓存

### CoreText 排版管线详解

完整的排版流程：
```
UTF-8 -> CFString -> CFAttributedString -> CTTypesetter -> CTLine -> CTRun
```

1. **CFString 创建**: `CFStringCreateWithBytes` 从 UTF-8 创建 CoreFoundation 字符串
2. **属性字符串**: `CFAttributedStringCreate` 关联字体属性
3. **排版器**: `CTTypesetterCreateWithAttributedString` 创建排版器
4. **行迭代**: `LineBreakIter` 使用 `CTTypesetterSuggestLineBreak` 建议换行位置
5. **行创建**: `CTTypesetterCreateLine` 根据建议创建 CTLine
6. **运行提取**: `CTLineGetGlyphRuns` 获取一行中的所有 CTRun

### CTRun 数据提取
从每个 CTRun 中提取的数据：
- `CTRunGetGlyphCount`: 字形数量
- `CTRunGetGlyphs`: 字形 ID 数组
- `CTRunGetPositions`: 字形位置数组
- `CTRunGetAdvances`: 字形前进量数组
- `CTRunGetStringIndices`: UTF-16 索引到字形的映射
- `CTRunGetAttributes -> kCTFontAttributeName`: 该 run 使用的字体

### UTF16ToUTF8IndicesMap 实现
该映射器的工作原理：
1. 分配 `utf16Size + 1` 大小的数组
2. 逐字符扫描 UTF-8 文本
3. 对每个字符，记录其 UTF-8 起始偏移到对应的 UTF-16 索引位置
4. 利用 `SkUTF::ToUTF16` 计算每个字符占用的 UTF-16 单元数
5. 最后一个位置存储文本总大小

### 已知局限性
1. 仅使用第一个字体运行的字体作为基础字体
2. BiDi 级别信息未从 CoreText 提取（硬编码为 0）
3. 脚本和语言标签未传递
4. 不支持 OpenType 特性参数（Feature 数组被忽略）
5. 字形位置相对于行起始，需要手动减去 `lineAdvance` 偏移

### 与 HarfBuzz 后端的对比
| 特性 | CoreText | HarfBuzz |
|------|----------|----------|
| 平台 | Apple 专用 | 跨平台 |
| 换行 | CTTypesetter (高质量) | SkUnicode 行断行 |
| 字体回退 | 系统自动 | SkFontMgr |
| BiDi | 系统处理 | SkUnicode |
| 连字符断行 | 支持 | 不支持 |
| OpenType 特性 | 部分支持 | 完整支持 |

## 相关文件

- `modules/skshaper/include/SkShaper_coretext.h` - 公共接口
- `modules/skshaper/include/SkShaper.h` - SkShaper 基类
- `include/ports/SkTypeface_mac.h` - macOS 字体互操作
- `src/utils/mac/SkUniqueCFRef.h` - CF 对象 RAII 包装
- `src/utils/mac/SkCGBase.h` - CG 类型兼容
