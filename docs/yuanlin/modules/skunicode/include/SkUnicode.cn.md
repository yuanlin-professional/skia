# SkUnicode - Unicode 抽象接口

> 源文件: `modules/skunicode/include/SkUnicode.h`

## 概述

`SkUnicode.h` 定义了 Skia 的 Unicode 功能抽象接口层，包含三个核心类：`SkBidiIterator`（双向文本迭代器）、`SkBreakIterator`（文本分割迭代器）和 `SkUnicode`（统一的 Unicode 操作接口）。该文件是 `skunicode` 模块的核心头文件，提供了与底层 Unicode 库无关的统一 API，支持文本方向分析、行分割、词分割、字素簇分割、字符属性查询和编码转换等功能。多个后端实现（ICU4X、libgrapheme、Client、Bidi）通过此接口提供具体功能。

## 架构位置

`SkUnicode` 位于 Skia 文本处理架构的核心抽象层，向上为 `SkShaper`（文本排版器）和 `SkParagraph`（段落布局引擎）提供 Unicode 功能，向下由具体后端实现（ICU4X、libgrapheme 等）提供功能。它是 Skia 文本处理管线中连接排版引擎和 Unicode 数据库的桥梁。

## 主要类与结构体

### `SkBidiIterator`
```cpp
class SKUNICODE_API SkBidiIterator {
public:
    typedef int32_t Position;
    typedef uint8_t Level;
    struct Region {
        Position start, end;
        Level level;
    };
    enum Direction { kLTR, kRTL };
    virtual Position getLength() = 0;
    virtual Level getLevelAt(Position) = 0;
};
```
双向文本迭代器，用于分析文本的书写方向（从左到右/从右到左）。每个位置有一个嵌入级别 (level)，奇数级别表示 RTL，偶数表示 LTR。

### `SkBreakIterator`
```cpp
class SKUNICODE_API SkBreakIterator {
public:
    typedef int32_t Position;
    typedef int32_t Status;
    virtual Position first() = 0;
    virtual Position current() = 0;
    virtual Position next() = 0;
    virtual Status status() = 0;
    virtual bool isDone() = 0;
    virtual bool setText(const char utftext8[], int utf8Units) = 0;
    virtual bool setText(const char16_t utftext16[], int utf16Units) = 0;
};
```
通用文本分割迭代器，支持 UTF-8 和 UTF-16 输入，用于词分割、行分割、句子分割和字素簇分割。

### `SkUnicode`
```cpp
class SKUNICODE_API SkUnicode : public SkRefCnt {
public:
    enum CodeUnitFlags { /* 12 种标志 */ };
    enum class TextDirection { kLTR, kRTL };
    enum class LineBreakType { kSoftLineBreak = 0, kHardLineBreak = 100 };
    enum class BreakType { kWords, kGraphemes, kLines, kSentences };
    struct BidiRegion { Position start, end; BidiLevel level; };
    struct LineBreakBefore { Position pos; LineBreakType breakType; };
    // ... 纯虚方法和模板方法
};
```

### `CodeUnitFlags` 枚举（位掩码）
```cpp
enum CodeUnitFlags {
    kNoCodeUnitFlag       = 0x00,
    kPartOfWhiteSpaceBreak= 0x01,
    kGraphemeStart        = 0x02,
    kSoftLineBreakBefore  = 0x04,
    kHardLineBreakBefore  = 0x08,
    kPartOfIntraWordBreak = 0x10,
    kControl              = 0x20,
    kTabulation           = 0x40,
    kGlyphClusterStart    = 0x80,
    kIdeographic          = 0x100,
    kEmoji                = 0x200,
    kWordBreak            = 0x400,
    kSentenceBreak        = 0x800,
};
```
使用位掩码编码每个代码单元的多种属性，支持通过 `sknonstd::is_bitmask_enum` 启用位运算操作符。

## 公共 API 函数

### 字符属性查询

| 方法 | 说明 |
|------|------|
| `virtual bool isControl(SkUnichar)` | 是否为控制字符 |
| `virtual bool isWhitespace(SkUnichar)` | 是否为空白字符 |
| `virtual bool isSpace(SkUnichar)` | 是否为空格 |
| `virtual bool isTabulation(SkUnichar)` | 是否为制表符 |
| `virtual bool isHardBreak(SkUnichar)` | 是否为硬换行 |
| `virtual bool isEmoji(SkUnichar)` | 是否可能开始 emoji 序列 |
| `virtual bool isEmojiComponent(SkUnichar)` | 是否为 emoji 组件 |
| `virtual bool isEmojiModifierBase(SkUnichar)` | 是否为 emoji 修饰基字符 |
| `virtual bool isEmojiModifier(SkUnichar)` | 是否为 emoji 修饰符 |
| `virtual bool isRegionalIndicator(SkUnichar)` | 是否为区域指示符（国旗） |
| `virtual bool isIdeographic(SkUnichar)` | 是否为表意文字 |

### 迭代器工厂

| 方法 | 说明 |
|------|------|
| `virtual makeBidiIterator(uint16_t[], int, Direction)` | 创建 UTF-16 双向迭代器 |
| `virtual makeBidiIterator(char[], int, Direction)` | 创建 UTF-8 双向迭代器 |
| `virtual makeBreakIterator(const char* locale, BreakType)` | 创建带区域设置的分割迭代器 |
| `virtual makeBreakIterator(BreakType)` | 创建默认分割迭代器 |

### 文本分析（用于 SkParagraph）

| 方法 | 说明 |
|------|------|
| `virtual getBidiRegions(utf8, units, dir, results)` | 获取双向文本区域 |
| `virtual getWords(utf8, units, locale, results)` | 获取词边界（UTF-16） |
| `virtual getUtf8Words(utf8, units, locale, results)` | 获取词边界（UTF-8） |
| `virtual getSentences(utf8, units, locale, results)` | 获取句子边界 |
| `virtual computeCodeUnitFlags(utf8, ..., results)` | 计算每个代码单元的属性标志 |
| `virtual computeCodeUnitFlags(utf16, ..., results)` | 计算每个代码单元的属性标志（UTF-16） |
| `virtual reorderVisual(levels, count, logicalFromVisual)` | 视觉重排序 |

### 静态工具方法

| 方法 | 说明 |
|------|------|
| `static hasTabulationFlag(flags)` | 检查制表符标志 |
| `static hasHardLineBreakFlag(flags)` | 检查硬换行标志 |
| `static hasSoftLineBreakFlag(flags)` | 检查软换行标志 |
| `static hasGraphemeStartFlag(flags)` | 检查字素簇起始标志 |
| `static hasControlFlag(flags)` | 检查控制字符标志 |
| `static hasPartOfWhiteSpaceBreakFlag(flags)` | 检查空白分割标志 |
| `static extractBidi(utf8, units, dir, regions)` | 提取双向文本区域 |
| `static convertUtf16ToUtf8(utf16, units)` | UTF-16 转 UTF-8 |
| `static convertUtf8ToUtf16(utf8, units)` | UTF-8 转 UTF-16 |

### 模板方法（非虚拟，内联实现）

| 方法 | 说明 |
|------|------|
| `extractUtfConversionMapping<A8, A16>(utf8, app8, app16)` | 提取 UTF-8/UTF-16 索引映射 |
| `forEachCodepoint(utf8, units, callback)` | 遍历 UTF-8 中的每个码点 |
| `forEachCodepoint(utf16, units, callback)` | 遍历 UTF-16 中的每个码点 |
| `forEachBidiRegion(utf16, units, dir, callback)` | 遍历双向文本区域 |
| `forEachBreak(utf16, units, type, callback)` | 遍历文本分割点 |

## 内部实现细节

### DLL 导出宏系统
```cpp
#if defined(SKUNICODE_DLL)
    #if defined(_MSC_VER)
        #if SKUNICODE_IMPLEMENTATION
            #define SKUNICODE_API __declspec(dllexport)
        #else
            #define SKUNICODE_API __declspec(dllimport)
        #endif
    #else
        #define SKUNICODE_API __attribute__((visibility("default")))
    #endif
#else
    #define SKUNICODE_API
#endif
```
支持 Windows (MSVC) 和 Unix (GCC/Clang) 两种 DLL 导出方式。

### UTF 索引映射 (`extractUtfConversionMapping`)
这是最复杂的模板方法，建立 UTF-8 字节索引和 UTF-16 代码单元索引之间的双向映射：
```cpp
template <typename Appender8, typename Appender16>
static bool extractUtfConversionMapping(SkSpan<const char> utf8, Appender8&& appender8, Appender16&& appender16) {
    while (ptr < end) {
        SkUnichar u = SkUTF::NextUTF8(&ptr, end);
        // 所有 UTF-8 代码单元映射到同一个 UTF-16 位置
        for (auto i = index; i < next; ++i) {
            appender16(size8);
        }
        // 一个或两个 UTF-16 代码单元映射到同一个 UTF-8 位置
        size_t count = SkUTF::ToUTF16(u, buffer);
        appender8(index);
        if (count > 1) { appender8(index); }
    }
}
```

### 双向文本区域遍历 (`forEachBidiRegion`)
使用 `SkBidiIterator` 遍历文本，在嵌入级别变化时触发回调：
```cpp
while (pos16 <= iter->getLength()) {
    auto level = iter->getLevelAt(nextPos16);
    if (level != currentLevel) {
        callback(pos16, nextPos16, currentLevel);
        currentLevel = level;
    }
    SkUTF::NextUTF16(&start16, end16);
}
```

### 码点遍历 (`forEachCodepoint`)
提供 UTF-8 和 UTF-16 两个重载版本，对每个 Unicode 码点调用回调，提供码点值、在原始编码中的起始和结束偏移。UTF-8 版本还计算等效的 UTF-16 代码单元数。

### 位掩码枚举支持
```cpp
namespace sknonstd {
template <> struct is_bitmask_enum<SkUnicode::CodeUnitFlags> : std::true_type {};
}
```
启用 `CodeUnitFlags` 的 `|`、`&`、`~` 等位运算操作符。

## 依赖关系

- **直接依赖**: `SkRefCnt.h`（引用计数）、`SkSpan.h`（数据切片）、`SkString.h`、`SkTypes.h`、`SkTArray.h`、`SkTo.h`、`SkUTF.h`（UTF 编解码）
- **被实现**: `SkUnicode_icu4x.h`、`SkUnicode_libgrapheme.h`、`SkUnicode_client.h`、`SkUnicode_bidi.h`
- **被使用**: `SkShaper`（文本排版）、`SkParagraph`（段落布局）、`skplaintexteditor`（文本编辑器）

## 设计模式与设计决策

- **策略模式/接口模式**: `SkUnicode` 定义纯虚接口，具体 Unicode 功能由后端实现提供，允许在不同大小/功能/许可证约束之间选择
- **引用计数**: 继承 `SkRefCnt`，通过 `sk_sp` 管理生命周期，支持多个使用者共享同一实例
- **双编码支持**: 许多 API 同时提供 UTF-8 和 UTF-16 版本，适应不同使用场景（UTF-8 用于存储和 Skia 内部，UTF-16 用于与 ICU 等库交互）
- **回调式 API**: `forEachCodepoint`、`forEachBidiRegion`、`forEachBreak` 使用回调模式而非迭代器，避免了迭代器生命周期管理的复杂性
- **CodeUnitFlags 位掩码**: 将多种字符属性编码在一个整数中，允许一次计算同时获取所有属性，减少对 Unicode 数据库的重复查询
- **`toUpper` 标记弃用**: 注释中标记为 deprecated，表明大小写转换功能可能会从接口中移除
- **Emoji 检测注意事项**: `isEmoji` 的文档明确说明 `#`、`*`、`0-9` 也会返回 true（因为它们可以开始键帽 emoji 序列），需要 `getEmojiSequence` 进行完整判断

## 性能考量

- **批量属性计算**: `computeCodeUnitFlags` 一次性计算所有代码单元的全部属性标志，避免逐属性逐字符查询的开销
- **UTF 索引映射预计算**: `extractUtfConversionMapping` 通过模板回调（appender）将映射结果直接写入目标容器，避免中间分配
- **迭代器复用**: `SkBreakIterator` 的 `setText` 方法允许复用迭代器实例处理多段文本
- **静态方法优化**: 标志检查方法和编码转换方法为静态方法，不需要虚函数调用开销
- **`TArray` 用于结果**: `computeCodeUnitFlags` 使用 `skia_private::TArray` 而非 `std::vector`，利用 Skia 的优化数组实现
- **整数溢出防护**: `forEachBidiRegion` 中使用 `static_assert` 验证位置类型的范围安全性

## 相关文件

- `modules/skunicode/include/SkUnicode_icu4x.h` — ICU4X 后端工厂
- `modules/skunicode/include/SkUnicode_libgrapheme.h` — libgrapheme 后端工厂
- `modules/skunicode/include/SkUnicode_client.h` — 客户端数据后端工厂
- `modules/skunicode/include/SkUnicode_bidi.h` — 双向文本后端工厂
- `src/base/SkUTF.h` — UTF 编解码基础工具
- `include/core/SkRefCnt.h` — 引用计数基类
- `modules/skshaper/` — 文本排版器，主要使用方
- `modules/skparagraph/` — 段落布局引擎，主要使用方
