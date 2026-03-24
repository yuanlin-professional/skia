# skunicode - Unicode 支持模块

## 概述

skunicode 是 Skia 图形库的 Unicode 支持模块,为文本排版提供了统一的 Unicode 属性查询和文本分析接口。该模块抽象了底层 Unicode 库的差异,使得上层模块(skshaper、skparagraph)可以通过统一的 `SkUnicode` 接口访问 Unicode 功能,而无需关心使用的是 ICU、ICU4X、libgrapheme 还是其他实现。

skunicode 提供的核心功能包括:字符属性分类(空格、控制字符、表意文字、Emoji 等)、双向文本(BiDi)分析、文本分割(行断点、词边界、字素簇边界、句子边界)、大小写转换以及 UTF-8/UTF-16 编码转换。这些功能是现代文本排版不可或缺的基础设施。

模块采用了多后端架构,支持五种 Unicode 实现:ICU(完整版和运行时加载版)、ICU4X(Rust 实现的现代 Unicode 库)、libgrapheme(轻量级 C 实现)、Client(客户端预计算数据)以及 Bidi(仅双向文本支持)。这种设计允许根据目标平台的约束(如二进制大小、可用库)选择最合适的 Unicode 后端。

所有后端都继承自 `SkUnicode` 基类,并通过命名空间工厂函数(如 `SkUnicodes::ICU::Make()`)创建。模块还提供了 `SkUnicodeHardCodedCharProperties` 基类,为字符属性分类提供了不依赖外部库的硬编码实现,减少了部分后端的实现负担。

## 架构图

```
+------------------------------------------------------------------+
|                     上层模块                                      |
|  skparagraph (段落排版)          skshaper (文本整形)               |
|  - computeCodeUnitFlags          - BiDiRunIterator                |
|  - getBidiRegions                - ScriptRunIterator              |
|  - getWords / getSentences                                        |
+----------------------------+-------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                       SkUnicode                                   |
|  (统一抽象接口 - include/SkUnicode.h)                             |
|  字符分类 | BiDi分析 | 断行/断词 | 字素簇 | 编码转换              |
+---------+--------+--------+--------+---------+-------------------+
          |        |        |        |         |
          v        v        v        v         v
+------+ +------+ +------+ +------+ +------+ +------+
| ICU  | | ICU  | |ICU4X | |libgr | |Client| | Bidi |
|内置  | |运行时 | |      | |apheme| |      | |      |
+------+ +------+ +------+ +------+ +------+ +------+
   |        |        |        |        |        |
   v        v        v        v        v        v
+------+ +------+ +------+ +------+ +------+ +------+
|ICU库 | |ICU库 | |ICU4X | |libgr | |预计算 | |ICU   |
|静态  | |动态  | |Rust  | |C库   | |数据  | |BiDi  |
+------+ +------+ +------+ +------+ +------+ +------+

+------------------------------------------------------------------+
|           SkUnicodeHardCodedCharProperties (硬编码基类)            |
|  isControl / isWhitespace / isEmoji / isIdeographic 等            |
|  不依赖外部库,通过 Unicode 码点范围判断                           |
+------------------------------------------------------------------+
```

## 目录结构

```
modules/skunicode/
|-- BUILD.bazel              # Bazel 构建配置
|-- BUILD.gn                 # GN 构建配置
|-- skunicode.gni            # GNI 源文件清单(自动生成)
|-- include/                 # 公共头文件
|   |-- BUILD.bazel
|   |-- SkUnicode.h          # 核心抽象接口
|   |-- SkUnicode_icu.h      # ICU 后端工厂
|   |-- SkUnicode_icu4x.h    # ICU4X 后端工厂
|   |-- SkUnicode_libgrapheme.h  # libgrapheme 后端工厂
|   |-- SkUnicode_client.h   # Client 后端工厂
|   |-- SkUnicode_bidi.h     # Bidi 后端工厂
|-- src/                     # 实现代码
|   |-- BUILD.bazel
|   |-- SkUnicode.cpp        # 通用静态方法实现
|   |-- SkUnicode_hardcoded.cpp/h  # 硬编码字符属性
|   |-- SkUnicode_icu.cpp    # ICU 通用实现
|   |-- SkUnicode_icupriv.h  # ICU 内部头文件
|   |-- SkUnicode_icu_builtin.cpp  # ICU 静态链接版
|   |-- SkUnicode_icu_runtime.cpp  # ICU 运行时加载版
|   |-- SkUnicode_icu_bidi.cpp/h   # ICU BiDi 功能封装
|   |-- SkBidiFactory_icu_full.cpp/h    # 完整ICU BiDi工厂
|   |-- SkBidiFactory_icu_subset.cpp/h  # 精简ICU BiDi工厂
|   |-- SkUnicode_icu4x.cpp  # ICU4X 后端实现
|   |-- SkUnicode_libgrapheme.cpp  # libgrapheme 后端实现
|   |-- SkUnicode_client.cpp # Client 后端实现
|   |-- SkUnicode_bidi.cpp   # Bidi 后端实现
|-- tests/                   # 测试
    |-- BUILD.bazel
    |-- SkUnicodeTest.cpp    # Unicode 功能测试
```

## 关键类与函数

### SkUnicode - 核心抽象接口

```cpp
class SkUnicode : public SkRefCnt {
    // 字符属性分类
    virtual bool isControl(SkUnichar) = 0;      // 控制字符
    virtual bool isWhitespace(SkUnichar) = 0;    // 空格类字符
    virtual bool isSpace(SkUnichar) = 0;         // 空格
    virtual bool isTabulation(SkUnichar) = 0;    // 制表符
    virtual bool isHardBreak(SkUnichar) = 0;     // 硬换行符
    virtual bool isEmoji(SkUnichar) = 0;         // Emoji
    virtual bool isEmojiComponent(SkUnichar) = 0;// Emoji组件
    virtual bool isEmojiModifierBase(SkUnichar) = 0; // Emoji修饰基
    virtual bool isEmojiModifier(SkUnichar) = 0; // Emoji修饰符
    virtual bool isRegionalIndicator(SkUnichar) = 0; // 区域指示符
    virtual bool isIdeographic(SkUnichar) = 0;   // 表意文字(CJK)

    // 迭代器创建
    virtual std::unique_ptr<SkBidiIterator> makeBidiIterator(...) = 0;
    virtual std::unique_ptr<SkBreakIterator> makeBreakIterator(...) = 0;

    // 文本分析(用于段落排版)
    virtual bool getBidiRegions(utf8, dir, results) = 0;  // BiDi区域
    virtual bool getWords(utf8, locale, results) = 0;     // 词边界(UTF-16)
    virtual bool getUtf8Words(utf8, locale, results) = 0; // 词边界(UTF-8)
    virtual bool getSentences(utf8, locale, results) = 0; // 句子边界
    virtual bool computeCodeUnitFlags(utf8, replaceTabs, results) = 0; // 代码单元标志

    // 大小写转换
    virtual SkString toUpper(const SkString&) = 0;
    virtual SkString toUpper(const SkString&, const char* locale) = 0;

    // BiDi 视觉重排序
    virtual void reorderVisual(const BidiLevel[], int, int32_t[]) = 0;

    // 编码转换(静态方法)
    static SkString convertUtf16ToUtf8(const char16_t*, int);
    static std::u16string convertUtf8ToUtf16(const char*, int);
};
```

### CodeUnitFlags - 代码单元标志位

```cpp
enum CodeUnitFlags {
    kNoCodeUnitFlag        = 0x00,
    kPartOfWhiteSpaceBreak = 0x01,   // 空格断行
    kGraphemeStart         = 0x02,   // 字素簇起始
    kSoftLineBreakBefore   = 0x04,   // 软换行点
    kHardLineBreakBefore   = 0x08,   // 硬换行点
    kPartOfIntraWordBreak  = 0x10,   // 词内断点
    kControl               = 0x20,   // 控制字符
    kTabulation            = 0x40,   // 制表符
    kGlyphClusterStart     = 0x80,   // 字形簇起始
    kIdeographic           = 0x100,  // 表意文字
    kEmoji                 = 0x200,  // Emoji
    kWordBreak             = 0x400,  // 词断点
    kSentenceBreak         = 0x800,  // 句子断点
};
```

### SkBidiIterator - 双向文本迭代器

```cpp
class SkBidiIterator {
    enum Direction { kLTR, kRTL };
    struct Region { Position start, end; Level level; };
    virtual Position getLength() = 0;
    virtual Level getLevelAt(Position) = 0;
};
```

### SkBreakIterator - 文本断点迭代器

```cpp
class SkBreakIterator {
    virtual Position first() = 0;
    virtual Position current() = 0;
    virtual Position next() = 0;
    virtual Status status() = 0;
    virtual bool isDone() = 0;
    virtual bool setText(const char*, int) = 0;
    virtual bool setText(const char16_t*, int) = 0;
};
```

### 后端工厂函数

| 命名空间 | 函数 | 说明 |
|----------|------|------|
| `SkUnicodes::ICU` | `Make()` | ICU 后端(完整 Unicode 支持) |
| `SkUnicodes::ICU4X` | `Make()` | ICU4X 后端(Rust 实现) |
| `SkUnicodes::Libgrapheme` | `Make()` | libgrapheme 后端(轻量级) |
| `SkUnicodes::Client` | `Make(text, words, graphemes, lineBreaks)` | 客户端预计算数据 |
| `SkUnicodes::Bidi` | `Make()` | 仅 BiDi 支持 |

## 依赖关系

```
skunicode
  |-- Skia Core
  |   |-- SkRefCnt, SkString, SkSpan, SkTypes
  |   |-- SkTArray (内部数组)
  |   |-- SkUTF (UTF编码工具)
  |
  |-- ICU (可选,当 SK_UNICODE_ICU_IMPLEMENTATION 定义时)
  |   |-- 完整 ICU 库 (uchar.h, ubidi.h, ubrk.h, utext.h)
  |   |-- 静态链接或运行时动态加载
  |
  |-- ICU4X (可选,当 SK_UNICODE_ICU4X_IMPLEMENTATION 定义时)
  |   |-- ICU4X C FFI 绑定
  |
  |-- libgrapheme (可选,当 SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION 定义时)
  |   |-- grapheme.h (轻量级 Unicode 分割库)
  |
  |-- 无外部依赖 (Client 后端 / Bidi 后端 / 硬编码字符属性)
```

## 设计模式分析

### 1. 抽象工厂模式 (Abstract Factory)
每个后端通过独立的命名空间工厂函数(`SkUnicodes::ICU::Make()` 等)创建 `SkUnicode` 实例。客户端根据需要选择后端,所有后端返回相同的 `sk_sp<SkUnicode>` 类型。

### 2. 策略模式 (Strategy Pattern)
不同的 Unicode 后端实现了相同的 `SkUnicode` 接口,上层代码可以透明地切换后端而不影响功能。这在构建配置(如嵌入式平台需要小二进制)中尤为有用。

### 3. 模板方法模式 (Template Method)
`SkUnicodeHardCodedCharProperties` 提供了字符属性分类的硬编码实现,各后端继承它以获得不依赖外部库的基本字符分类能力,仅需实现更复杂的断行和 BiDi 等功能。

### 4. 模板编程 (Template Programming)
`SkUnicode` 提供了几个模板方法用于高效遍历:
- `forEachCodepoint()`: 遍历每个 Unicode 码点
- `forEachBidiRegion()`: 遍历 BiDi 区域
- `forEachBreak()`: 遍历断点
- `extractUtfConversionMapping()`: 构建 UTF-8/UTF-16 转换映射

### 5. 位掩码枚举 (Bitmask Enum)
`CodeUnitFlags` 使用位掩码设计,允许单个代码单元同时具有多个标志(如同时是字素簇起始和软换行点)。通过 `sknonstd::is_bitmask_enum` 特化支持位运算操作符。

## 数据流

```
文本输入 (UTF-8 或 UTF-16)
  |
  v
SkUnicode 接口
  |
  +-- 字符属性查询 (逐字符)
  |   isControl(ch) / isWhitespace(ch) / isEmoji(ch) / isIdeographic(ch)
  |   -> 硬编码实现(快速路径) 或 后端库查询
  |
  +-- 代码单元标志计算 (批量)
  |   computeCodeUnitFlags(utf8, replaceTabs, results[])
  |   -> 遍历文本,为每个代码单元设置 CodeUnitFlags 标志位
  |   -> 使用 BreakIterator 分析: 行断点/词边界/字素簇/句子
  |   -> 使用字符分类: 空格/控制字符/制表符/表意文字/Emoji
  |   输出: CodeUnitFlags[] 数组
  |
  +-- BiDi 分析
  |   getBidiRegions(utf8, direction, regions[])
  |   -> 使用 ICU ubidi / ICU4X BiDi 分析算法
  |   输出: BidiRegion[] (start, end, level)
  |
  +-- 词边界检测
  |   getWords(utf8, locale, positions[])
  |   -> 使用 BreakIterator(kWords) 分割
  |   输出: Position[] (词起始偏移)
  |
  +-- 视觉重排序
  |   reorderVisual(levels[], count, logicalFromVisual[])
  |   -> 将 BiDi 级别映射为视觉显示顺序
  |
  +-- 编码转换
      convertUtf8ToUtf16() / convertUtf16ToUtf8()
      extractUtfConversionMapping() -> 建立 UTF-8/UTF-16 索引映射

输出: 标志位数组 / BiDi 区域 / 断点位置 / 编码映射
  |
  v
上层模块使用:
  skparagraph: 换行决策、样式分割、字素导航
  skshaper: BiDi 分段、脚本分段
```

## 相关文档与参考

- **skparagraph 模块**: `modules/skparagraph/` - 主要消费者(段落排版)
- **skshaper 模块**: `modules/skshaper/` - 消费者(文本整形中的 BiDi 分析)
- **ICU 项目**: https://icu.unicode.org/ - International Components for Unicode
- **ICU4X 项目**: https://github.com/unicode-org/icu4x - Rust 实现的 Unicode 库
- **libgrapheme**: https://libs.suckless.org/libgrapheme/ - 轻量级 Unicode 分割库
- **Unicode UAX #9**: 双向算法 (Unicode Bidirectional Algorithm)
- **Unicode UAX #14**: 换行算法 (Unicode Line Breaking Algorithm)
- **Unicode UAX #29**: 文本分割 (Unicode Text Segmentation)
- **Unicode UAX #11**: 东亚文字宽度 (East Asian Width)
- **Unicode TR #51**: Emoji 规范
