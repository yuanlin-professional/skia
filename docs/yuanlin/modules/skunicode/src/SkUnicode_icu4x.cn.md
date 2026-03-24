# SkUnicode_icu4x

> 源文件: modules/skunicode/src/SkUnicode_icu4x.cpp

## 概述

`SkUnicode_icu4x` 是基于 ICU4X 库实现的 Unicode 处理类。ICU4X 是 ICU (International Components for Unicode) 的现代化重写版本,使用 Rust 编写,提供更小的二进制大小和更好的性能。该实现为 Skia 提供了完整的 Unicode 字符属性查询、文本分词、双向文本处理等功能。

相比传统的 ICU 库,ICU4X 采用数据驱动的设计,支持按需加载功能模块,非常适合对二进制大小敏感的应用场景,如移动端和 Web 环境。

## 架构位置

该文件位于 Skia Unicode 模块中,作为 ICU4X 后端的实现:

```
skia/
└── modules/
    └── skunicode/
        ├── include/
        │   ├── SkUnicode.h          # Unicode 接口基类
        │   └── SkUnicode_icu4x.h    # ICU4X 实现头文件
        └── src/
            ├── SkUnicode_icu4x.cpp  # 本文件
            ├── SkUnicode_icu.cpp    # 传统 ICU 实现
            ├── SkUnicode_libgrapheme.cpp # Libgrapheme 实现
            └── SkUnicode_hardcoded.h     # 硬编码字符属性基类
```

## 主要类与结构体

### SkUnicode_icu4x

主要实现类,继承自 `SkUnicode` 接口:

```cpp
class SkUnicode_icu4x : public SkUnicode {
private:
    ICU4XLocale fLocale;                    // 区域设置
    ICU4XDataProvider fDataProvider;        // 数据提供者
    ICU4XCaseMapper fCaseMapper;            // 大小写转换器
    ICU4XCodePointSetData fWhitespaces;     // 空白字符集
    ICU4XCodePointSetData fSpaces;          // 空格字符集
    ICU4XCodePointSetData fBlanks;          // Blank 字符集
    ICU4XCodePointSetData fEmoji;           // Emoji 字符集
    ICU4XCodePointSetData fEmojiComponent;  // Emoji 组件集
    ICU4XCodePointSetData fEmojiModifier;   // Emoji 修饰符集
    ICU4XCodePointSetData fEmojiModifierBase; // Emoji 修饰基础集
    ICU4XCodePointSetData fRegionalIndicator; // 区域指示符集
    ICU4XCodePointSetData fIdeographic;     // 表意字符集
    ICU4XCodePointSetData fControls;        // 控制字符集
    ICU4XCodePointMapData8 fLineBreaks;     // 换行属性映射
    std::shared_ptr<std::vector<SkUnicode::BidiRegion>> fRegions; // BiDi 区域缓存
};
```

### SkBreakIterator_icu4x

断点迭代器的存根实现:

```cpp
class SkBreakIterator_icu4x : public SkBreakIterator {
    // 所有方法都返回断言失败,表示未完全实现
};
```

### SkBidiIterator_icu4x

双向文本迭代器实现:

```cpp
class SkBidiIterator_icu4x : public SkBidiIterator {
    std::shared_ptr<std::vector<SkUnicode::BidiRegion>> fRegions;
public:
    Position getLength() override;
    Level getLevelAt(Position pos) override;
};
```

## 公共 API 函数

### 字符属性查询

所有字符属性查询方法都基于 ICU4X 的 `CodePointSetData`:

```cpp
bool isControl(SkUnichar utf8) override { return fControls.contains(utf8); }
bool isWhitespace(SkUnichar utf8) override { return fWhitespaces.contains(utf8); }
bool isSpace(SkUnichar utf8) override { return fBlanks.contains(utf8); }
bool isEmoji(SkUnichar utf8) override { return fEmoji.contains(utf8); }
bool isEmojiComponent(SkUnichar utf8) override { return fEmojiComponent.contains(utf8); }
bool isEmojiModifierBase(SkUnichar utf8) override { return fEmojiModifierBase.contains(utf8); }
bool isEmojiModifier(SkUnichar utf8) override { return fEmojiModifier.contains(utf8); }
bool isRegionalIndicator(SkUnichar utf8) override { return fRegionalIndicator.contains(utf8); }
bool isIdeographic(SkUnichar utf8) override { return fIdeographic.contains(utf8); }
bool isTabulation(SkUnichar utf8) override { return utf8 == '\t'; }
```

### isHardBreak(SkUnichar utf8)

检查字符是否为硬换行符,使用 ICU4X 的换行属性:

```cpp
bool isHardBreak(SkUnichar utf8) override {
    auto value = fLineBreaks.get(utf8);
    return (value == 6) ||   // MandatoryBreak
           (value == 10) ||  // CarriageReturn
           (value == 17) ||  // LineFeed
           (value == 29);    // NextLine
}
```

### getBidiRegions

提取文本的双向区域信息:

```cpp
bool getBidiRegions(
    const char utf8[], int utf8Units,
    TextDirection dir,
    std::vector<BidiRegion>* results) override;
```

**实现逻辑:**
1. 创建 ICU4X Bidi 对象
2. 使用 `for_text()` 分析文本方向
3. 遍历所有位置,检测级别变化
4. 记录每个双向区域的起止位置和级别

### computeCodeUnitFlags

计算每个代码单元的标志位:

```cpp
bool computeCodeUnitFlags(
    char utf8[], int utf8Units,
    bool replaceTabs,
    skia_private::TArray<SkUnicode::CodeUnitFlags, true>* results) override;
```

**处理步骤:**
1. `markLineBreaks()` - 标记软换行位置
2. `markHardLineBreaksHack()` - 标记硬换行位置
3. `markGraphemes()` - 标记字素簇起始位置
4. `markCharacters()` - 标记字符属性(空格、控制符等)

### getWords

使用 ICU4X 的词语分割器提取单词边界:

```cpp
bool getWords(
    const char utf8[], int utf8Units,
    const char* locale,
    std::vector<Position>* results) override;
```

**实现:**
1. 将 UTF-8 转换为 UTF-16
2. 创建 `ICU4XWordSegmenter` 分词器
3. 使用 `segment_utf16()` 迭代单词边界
4. 将结果添加到 `results` 向量

### toUpper

字符串大写转换:

```cpp
SkString toUpper(const SkString& str, const char* localeStr) override;
```

使用 `ICU4XCaseMapper` 进行区域相关的大写转换。

### reorderVisual

双向文本的视觉重排序:

```cpp
void reorderVisual(
    const BidiLevel runLevels[], int levelsCount,
    int32_t logicalFromVisual[]) override;
```

使用 ICU4X 的 `bidi.reorder_visual()` 方法。

## 内部实现细节

### 初始化序列

构造函数中初始化所有 ICU4X 数据结构:

```cpp
SkUnicode_icu4x() {
    fLocale = ICU4XLocale::create_from_string("tr").ok().value();
    fDataProvider = ICU4XDataProvider::create_compiled();
    fCaseMapper = ICU4XCaseMapper::create(fDataProvider).ok().value();

    // 加载字符属性数据
    const auto general = ICU4XCodePointMapData8::load_general_category(fDataProvider).ok().value();
    fControls = general.get_set_for_value(15);  // Control category
    fWhitespaces = general.get_set_for_value(12); // SpaceSeparator

    // 加载二进制属性
    fEmoji = ICU4XCodePointSetData::load_emoji(fDataProvider).ok().value();
    fIdeographic = ICU4XCodePointSetData::load_ideographic(fDataProvider).ok().value();
    // ... 更多属性加载
}
```

### markLineBreaks 实现

使用 ICU4X 的换行分割器:

```cpp
bool markLineBreaks(char utf8[], int utf8Units, bool hardLineBreaks,
                    TArray<CodeUnitFlags, true>* results) {
    const auto lineBreakingOptions = hardLineBreaks
        ? ICU4XLineBreakOptionsV1{ICU4XLineBreakStrictness::Strict,
                                   ICU4XLineBreakWordOption::Normal, false}
        : ICU4XLineBreakOptionsV1{ICU4XLineBreakStrictness::Loose,
                                   ICU4XLineBreakWordOption::Normal, false};

    const auto segmenter = ICU4XLineSegmenter::create_auto_with_options_v1(
        fDataProvider, lineBreakingOptions).ok().value();

    std::string_view string_view(utf8, utf8Units);
    auto iterator = segmenter.segment_utf8(string_view);

    while (true) {
        int32_t lineBreak = iterator.next();
        if (lineBreak == -1) break;
        (*results)[lineBreak] |= hardLineBreaks
            ? CodeUnitFlags::kHardLineBreakBefore
            : CodeUnitFlags::kSoftLineBreakBefore;
    }
    return true;
}
```

### markGraphemes 实现

使用字素簇分割器:

```cpp
bool markGraphemes(const char utf8[], int utf8Units,
                   TArray<CodeUnitFlags, true>* results) {
    const auto segmenter = ICU4XGraphemeClusterSegmenter::create(fDataProvider).ok().value();
    std::string_view string_view(utf8, utf8Units);
    auto iterator = segmenter.segment_utf8(string_view);

    while (true) {
        int32_t graphemeStart = iterator.next();
        if (graphemeStart == -1) break;
        (*results)[graphemeStart] |= CodeUnitFlags::kGraphemeStart;
    }
    return true;
}
```

### markCharacters 实现

逐字符标记属性:

```cpp
bool markCharacters(char utf8[], int utf8Units, bool replaceTabs,
                    TArray<CodeUnitFlags, true>* results) {
    const char* current = utf8;
    const char* end = utf8 + utf8Units;

    while (current < end) {
        auto before = current - utf8;
        SkUnichar unichar = SkUTF::NextUTF8(&current, end);
        if (unichar < 0) unichar = 0xFFFD;
        auto after = current - utf8;

        // 处理制表符替换
        if (replaceTabs && isTabulation(unichar)) {
            results->at(before) |= SkUnicode::kTabulation;
            utf8[before] = ' ';
            unichar = ' ';
        }

        // 标记字符属性
        for (auto i = before; i < after; ++i) {
            if (isSpace(unichar)) {
                results->at(i) |= SkUnicode::kPartOfIntraWordBreak;
            }
            if (isWhitespace(unichar)) {
                results->at(i) |= SkUnicode::kPartOfWhiteSpaceBreak;
            }
            if (isControl(unichar)) {
                results->at(i) |= SkUnicode::kControl;
            }
        }
    }
    return true;
}
```

## 依赖关系

**ICU4X 头文件:**
- `<ICU4XBidi.hpp>` - 双向文本处理
- `<ICU4XCaseMapper.hpp>` - 大小写转换
- `<ICU4XCodePointMapData8.hpp>` - 字符属性映射
- `<ICU4XCodePointSetData.hpp>` - 字符集合
- `<ICU4XDataProvider.hpp>` - 数据提供者
- `<ICU4XGraphemeClusterSegmenter.hpp>` - 字素簇分割
- `<ICU4XLineSegmenter.hpp>` - 换行分割
- `<ICU4XWordSegmenter.hpp>` - 单词分割

**Skia 依赖:**
- `modules/skunicode/include/SkUnicode.h` - 基类接口
- `modules/skunicode/src/SkUnicode_hardcoded.h` - 硬编码字符属性
- `src/base/SkUTF.h` - UTF 编码处理

## 设计模式与设计决策

### 组合模式

使用组合而非继承处理字符属性,每个属性类型都有独立的 `CodePointSetData`:

```cpp
ICU4XCodePointSetData fEmoji;
ICU4XCodePointSetData fEmojiComponent;
ICU4XCodePointSetData fEmojiModifier;
```

### 懒加载 vs 预加载

当前实现采用预加载策略,在构造时加载所有数据。ICU4X 支持按需加载,但为简化代码选择了预加载。

### 魔数使用

使用魔数表示 Unicode 属性值:

```cpp
fControls = general.get_set_for_value(15);  // Control = 15
```

这些值对应 Unicode General Category 枚举,但缺少符号常量。

### 未实现方法

某些方法标记为未实现:

```cpp
bool getUtf8Words(...) override {
    SkDEBUGF("Method 'getUtf8Words' is not implemented\n");
    return false;
}
```

这表明 ICU4X 实现还在开发中,某些功能暂未完成。

## 性能考量

### 内存占用

- 每个 `CodePointSetData` 对象包含压缩的字符集数据
- `CodePointMapData8` 包含属性值映射
- 预加载所有数据增加了内存占用,但避免了运行时查找开销

### 查询性能

- 字符属性查询通过 `contains()` 方法,使用位集合或范围查找
- 时间复杂度通常为 O(log n) 或 O(1)
- 比传统 ICU 的函数调用开销更低

### UTF-8 vs UTF-16

许多操作需要 UTF-8 到 UTF-16 的转换:

```cpp
auto utf16 = SkUnicode::convertUtf8ToUtf16(utf8, utf8Units);
```

这增加了额外开销,但 ICU4X 的某些分词器只支持 UTF-16。

### 迭代器效率

使用 ICU4X 的迭代器接口:

```cpp
while (true) {
    int32_t breakpoint = iterator.next();
    if (breakpoint == -1) break;
    results->emplace_back(breakpoint);
}
```

避免了多次函数调用,提供了良好的缓存局部性。

## 相关文件

**接口定义:**
- `/modules/skunicode/include/SkUnicode.h` - Unicode 基类
- `/modules/skunicode/include/SkUnicode_icu4x.h` - ICU4X 公共接口

**相关实现:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - 传统 ICU 实现
- `/modules/skunicode/src/SkUnicode_libgrapheme.cpp` - Libgrapheme 实现
- `/modules/skunicode/src/SkUnicode_hardcoded.h` - 硬编码基类

**工具类:**
- `/src/base/SkUTF.h` - UTF 编码转换
- `/include/private/base/SkTArray.h` - 动态数组

**工厂方法:**
- `SkUnicodes::ICU4X::Make()` - 创建 ICU4X Unicode 实例
