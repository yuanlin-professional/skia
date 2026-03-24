# skunicode/include - Unicode 支持公共接口

## 概述

`include/` 目录包含 skunicode 模块的所有公共头文件。核心头文件 `SkUnicode.h` 定义了 Unicode 功能的统一抽象接口,其余头文件为各个 Unicode 后端提供工厂函数。客户端只需包含 `SkUnicode.h` 和所需后端的工厂头文件即可使用完整的 Unicode 功能。

接口设计遵循了"接口与实现分离"和"按需引入"的原则:`SkUnicode.h` 定义了与后端无关的通用接口,各后端工厂头文件独立存在,客户端只需链接实际使用的后端库。

## 架构图

```
+-----------------------------------------------------------+
|                    SkUnicode.h (核心接口)                   |
|  SkUnicode     | SkBidiIterator | SkBreakIterator          |
|  CodeUnitFlags | BidiRegion     | LineBreakBefore           |
+--------+-------+--------+-------+--------+----------------+
         |                |                |
   +-----+-----+  +------+------+  +------+------+
   |           |  |            |  |            |
   v           v  v            v  v            v
+-------+ +-------+ +-------+ +-------+ +-------+
|_icu.h | |_icu4x | |_libgr | |_client| |_bidi  |
|       | |.h     | |apheme | |.h     | |.h     |
|       | |       | |.h     | |       | |       |
+-------+ +-------+ +-------+ +-------+ +-------+
```

## 目录结构

```
include/
|-- BUILD.bazel              # Bazel 构建规则
|-- SkUnicode.h              # 核心抽象接口 (SkUnicode, SkBidiIterator, SkBreakIterator)
|-- SkUnicode_icu.h          # ICU 后端工厂
|-- SkUnicode_icu4x.h        # ICU4X 后端工厂
|-- SkUnicode_libgrapheme.h  # libgrapheme 后端工厂
|-- SkUnicode_client.h       # Client 后端工厂
|-- SkUnicode_bidi.h         # Bidi 后端工厂
```

## 关键类与函数

### SkUnicode.h - 核心接口

**SkBidiIterator** - 双向文本迭代器:

```cpp
class SkBidiIterator {
    typedef int32_t Position;
    typedef uint8_t Level;
    enum Direction { kLTR, kRTL };
    struct Region { Position start, end; Level level; };

    virtual Position getLength() = 0;        // 文本长度
    virtual Level getLevelAt(Position) = 0;   // 指定位置的BiDi级别
};
```

**SkBreakIterator** - 文本断点迭代器:

```cpp
class SkBreakIterator {
    typedef int32_t Position;
    typedef int32_t Status;

    virtual Position first() = 0;     // 第一个断点
    virtual Position current() = 0;   // 当前断点
    virtual Position next() = 0;      // 下一个断点
    virtual Status status() = 0;      // 断点类型状态
    virtual bool isDone() = 0;        // 是否遍历完毕
    virtual bool setText(const char*, int) = 0;     // 设置UTF-8文本
    virtual bool setText(const char16_t*, int) = 0; // 设置UTF-16文本
};
```

**SkUnicode** - Unicode 功能主接口:

| 方法类别 | 方法 | 说明 |
|----------|------|------|
| 字符分类 | `isControl(ch)` | 是否为控制字符 |
| 字符分类 | `isWhitespace(ch)` | 是否为空格类字符 |
| 字符分类 | `isSpace(ch)` | 是否为空格 |
| 字符分类 | `isTabulation(ch)` | 是否为制表符 |
| 字符分类 | `isHardBreak(ch)` | 是否为硬换行符 |
| 字符分类 | `isEmoji(ch)` | 是否可能开始 Emoji 序列 |
| 字符分类 | `isEmojiComponent(ch)` | 是否为 Emoji 组件 |
| 字符分类 | `isEmojiModifierBase(ch)` | 是否为 Emoji 修饰基字符 |
| 字符分类 | `isEmojiModifier(ch)` | 是否为 Emoji 修饰符 |
| 字符分类 | `isRegionalIndicator(ch)` | 是否为区域指示符(国旗) |
| 字符分类 | `isIdeographic(ch)` | 是否为表意文字(CJK) |
| 迭代器 | `makeBidiIterator(text, dir)` | 创建 BiDi 迭代器 |
| 迭代器 | `makeBreakIterator(locale, type)` | 创建断点迭代器 |
| 文本分析 | `getBidiRegions(utf8, dir, results)` | 获取 BiDi 区域 |
| 文本分析 | `getWords(utf8, locale, results)` | 获取词边界 |
| 文本分析 | `getUtf8Words(utf8, locale, results)` | 获取词边界(UTF-8索引) |
| 文本分析 | `getSentences(utf8, locale, results)` | 获取句子边界 |
| 文本分析 | `computeCodeUnitFlags(utf8, flags[])` | 批量计算代码单元标志 |
| 大小写 | `toUpper(str, locale)` | 转换为大写 |
| 重排序 | `reorderVisual(levels, logicalFromVisual)` | BiDi 视觉重排序 |

**CodeUnitFlags** - 代码单元标志位枚举:

```cpp
enum CodeUnitFlags {
    kPartOfWhiteSpaceBreak = 0x01,   // 空格断行
    kGraphemeStart         = 0x02,   // 字素簇起始
    kSoftLineBreakBefore   = 0x04,   // 软换行点(此处可以断行)
    kHardLineBreakBefore   = 0x08,   // 硬换行点(必须断行)
    kPartOfIntraWordBreak  = 0x10,   // 词内断点
    kControl               = 0x20,   // 控制字符
    kTabulation            = 0x40,   // 制表符
    kGlyphClusterStart     = 0x80,   // 字形簇起始
    kIdeographic           = 0x100,  // 表意文字
    kEmoji                 = 0x200,  // Emoji 字符
    kWordBreak             = 0x400,  // 词断点
    kSentenceBreak         = 0x800,  // 句子断点
};
```

**模板方法** - 高效遍历工具:

```cpp
// 遍历每个 Unicode 码点(UTF-8 输入)
template <typename Callback>
void forEachCodepoint(const char* utf8, int32_t utf8Units, Callback&& callback);

// 遍历 BiDi 区域
template <typename Callback>
void forEachBidiRegion(const uint16_t utf16[], int utf16Units, Direction, Callback&&);

// 遍历断点
template <typename Callback>
void forEachBreak(const char16_t utf16[], int utf16Units, BreakType, Callback&&);

// 构建 UTF-8/UTF-16 转换映射
template <typename Appender8, typename Appender16>
static bool extractUtfConversionMapping(SkSpan<const char> utf8, Appender8&&, Appender16&&);
```

### 后端工厂头文件

**SkUnicode_icu.h**:
```cpp
namespace SkUnicodes::ICU {
    sk_sp<SkUnicode> Make();  // 完整 ICU 后端
}
```

**SkUnicode_icu4x.h**:
```cpp
namespace SkUnicodes::ICU4X {
    sk_sp<SkUnicode> Make();  // ICU4X 后端
}
```

**SkUnicode_libgrapheme.h**:
```cpp
namespace SkUnicodes::Libgrapheme {
    sk_sp<SkUnicode> Make();  // libgrapheme 后端
}
```

**SkUnicode_client.h**:
```cpp
namespace SkUnicodes::Client {
    sk_sp<SkUnicode> Make(
        SkSpan<char> text,
        std::vector<SkUnicode::Position> words,           // 预计算词边界
        std::vector<SkUnicode::Position> graphemeBreaks,   // 预计算字素簇
        std::vector<SkUnicode::LineBreakBefore> lineBreaks // 预计算行断点
    );
}
```

**SkUnicode_bidi.h**:
```cpp
namespace SkUnicodes::Bidi {
    sk_sp<SkUnicode> Make();  // 仅BiDi支持(用于最小化构建)
}
```

## 依赖关系

```
include/
  |-- Skia Core
  |   |-- SkRefCnt (SkUnicode 基类)
  |   |-- SkString (字符串类型)
  |   |-- SkSpan (范围视图)
  |   |-- SkTypes, SkTArray, SkTo
  |   |-- SkUTF (src/base/SkUTF.h - UTF编码工具)
  |-- 无外部库依赖 (仅定义接口)
```

## 设计模式分析

### 接口隔离原则
`SkUnicode.h` 定义了完整的接口,但各后端只需实现其能力范围内的方法。例如 `Client` 后端不实现字符分类方法(使用硬编码回退),`Bidi` 后端仅关注双向文本分析。

### 位掩码设计
`CodeUnitFlags` 使用位掩码(bitmask)设计,单个标志变量可同时表示多个属性。`sknonstd::is_bitmask_enum` 特化使得可以直接使用 `|`、`&` 运算符组合和测试标志。

### 便捷静态方法
`SkUnicode` 提供了静态辅助方法用于标志位检测:
```cpp
static bool hasTabulationFlag(CodeUnitFlags flags);
static bool hasHardLineBreakFlag(CodeUnitFlags flags);
static bool hasSoftLineBreakFlag(CodeUnitFlags flags);
static bool hasGraphemeStartFlag(CodeUnitFlags flags);
```

## 数据流

```
客户端代码
  |
  +-- 选择后端: SkUnicodes::ICU / ICU4X / Libgrapheme / Client / Bidi
  +-- auto unicode = SkUnicodes::XXX::Make(...)
  |
  +-- 使用字符分类:
  |   unicode->isEmoji(ch)          -> true/false
  |   unicode->isIdeographic(ch)    -> true/false
  |
  +-- 使用文本分析:
  |   unicode->computeCodeUnitFlags(utf8, flags[])
  |     -> flags[i] 包含第i个代码单元的所有属性标志
  |
  +-- 使用 BiDi 分析:
  |   unicode->getBidiRegions(utf8, dir, regions[])
  |     -> regions[] = [{start, end, level}, ...]
  |
  +-- 使用断点迭代:
  |   auto iter = unicode->makeBreakIterator(locale, kLines)
  |   iter->setText(text, len)
  |   while (!iter->isDone()) { pos = iter->next(); }
  |
  +-- 使用编码转换:
      SkUnicode::convertUtf8ToUtf16(utf8, len)
      SkUnicode::convertUtf16ToUtf8(utf16, len)
```

## 相关文档与参考

- **实现代码**: `modules/skunicode/src/` - 各后端的具体实现
- **skparagraph**: `modules/skparagraph/` - 使用 computeCodeUnitFlags/getBidiRegions
- **skshaper**: `modules/skshaper/` - 使用 makeBidiIterator
- **Unicode 标准**: https://unicode.org/
- **ICU 文档**: https://unicode-org.github.io/icu/
