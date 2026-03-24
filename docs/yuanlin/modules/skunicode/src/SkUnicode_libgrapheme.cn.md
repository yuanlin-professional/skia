# SkUnicode_libgrapheme

> 源文件: modules/skunicode/src/SkUnicode_libgrapheme.cpp

## 概述

`SkUnicode_libgrapheme` 是基于 libgrapheme 库实现的轻量级 Unicode 处理类。libgrapheme 是一个专注于 Unicode 文本分割的小型 C 库,提供字素簇、单词和换行分割功能,二进制大小远小于完整的 ICU 库。该实现继承自 `SkUnicodeHardCodedCharProperties`,结合硬编码的字符属性和 libgrapheme 的文本分割能力,为 Skia 提供了适合资源受限环境的 Unicode 支持。

这个实现特别适用于对二进制大小敏感的场景,如嵌入式系统、WebAssembly 应用等,在提供基本 Unicode 功能的同时保持最小的依赖。

## 架构位置

该文件位于 Skia Unicode 模块中,作为轻量级 Unicode 后端:

```
skia/
└── modules/
    └── skunicode/
        ├── include/
        │   ├── SkUnicode.h               # Unicode 接口
        │   └── SkUnicode_libgrapheme.h   # Libgrapheme 接口
        └── src/
            ├── SkUnicode_libgrapheme.cpp # 本文件
            ├── SkUnicode_hardcoded.h     # 硬编码字符属性基类
            ├── SkUnicode_icu_bidi.h      # BiDi 接口
            └── SkBidiFactory_icu_subset.h # ICU 子集 BiDi 工厂
```

## 主要类与结构体

### SkUnicode_libgrapheme

主要实现类,继承自 `SkUnicodeHardCodedCharProperties`:

```cpp
class SkUnicode_libgrapheme : public SkUnicodeHardCodedCharProperties {
public:
    SkUnicode_libgrapheme() { }
    ~SkUnicode_libgrapheme() override = default;

private:
    sk_sp<SkBidiFactory> fBidiFact = sk_make_sp<SkBidiSubsetFactory>();
};
```

**继承的字符属性方法:**
- `isControl()`, `isWhitespace()`, `isSpace()` - 来自 `SkUnicodeHardCodedCharProperties`
- `isTabulation()`, `isHardBreak()`, `isIdeographic()` - 来自硬编码基类

**新实现的方法:**
- `makeBidiIterator()` - 创建双向文本迭代器
- `makeBreakIterator()` - 创建换行迭代器
- `getBidiRegions()` - 提取双向区域
- `computeCodeUnitFlags()` - 计算代码单元标志
- `getWords()` - 提取单词边界
- `getUtf8Words()` - 提取 UTF-8 单词边界
- `toUpper()` - 大写转换
- `reorderVisual()` - 视觉重排序

### SkBreakIterator_libgrapheme

换行迭代器实现:

```cpp
class SkBreakIterator_libgrapheme : public SkBreakIterator {
    SkUnicode_libgrapheme* fUnicode;
    std::vector<SkUnicode::LineBreakBefore> fLineBreaks;
    Position fLineBreakIndex;
    static constexpr const SkUnicode::Position kDone = -1;

public:
    Position first() override;
    Position current() override;
    Position next() override;
    Status status() override;
    bool isDone() override;
    bool setText(const char utftext8[], int utf8Units) override;
    bool setText(const char16_t utftext16[], int utf16Units) override;
};
```

## 公共 API 函数

### computeCodeUnitFlags (UTF-8 版本)

计算文本中每个代码单元的属性标志:

```cpp
bool computeCodeUnitFlags(
    char utf8[], int utf8Units,
    bool replaceTabs,
    skia_private::TArray<SkUnicode::CodeUnitFlags, true>* results) override;
```

**实现步骤:**

1. **初始化标志数组**
   ```cpp
   results->clear();
   results->push_back_n(utf8Units + 1, CodeUnitFlags::kNoCodeUnitFlag);
   ```

2. **标记软换行位置**
   ```cpp
   size_t lineBreak = 0;
   (*results)[lineBreak] |= CodeUnitFlags::kSoftLineBreakBefore;
   while (lineBreak < utf8Units) {
       lineBreak += grapheme_next_line_break_utf8(utf8 + lineBreak, utf8Units - lineBreak);
       (*results)[lineBreak] |= isHardBreak(utf8[lineBreak - 1])
           ? CodeUnitFlags::kHardLineBreakBefore
           : CodeUnitFlags::kSoftLineBreakBefore;
   }
   ```

3. **标记字素簇起始**
   ```cpp
   size_t graphemeBreak = 0;
   (*results)[graphemeBreak] |= CodeUnitFlags::kGraphemeStart;
   while (graphemeBreak < utf8Units) {
       graphemeBreak += grapheme_next_character_break_utf8(
           utf8 + graphemeBreak, utf8Units - graphemeBreak);
       (*results)[graphemeBreak] |= CodeUnitFlags::kGraphemeStart;
   }
   ```

4. **标记字符属性**
   - 制表符、空格、空白字符、控制字符

### getWords

提取单词边界,结果为 UTF-16 位置:

```cpp
bool getWords(
    const char utf8[], int utf8Units,
    const char* locale,
    std::vector<Position>* results) override;
```

**实现逻辑:**
1. 构建 UTF-8 到 UTF-16 的位置映射
2. 使用 `grapheme_next_word_break_utf8()` 查找单词边界
3. 将 UTF-8 位置转换为 UTF-16 位置

```cpp
std::unordered_map<Position, Position> mapping;
getUtf8To16Mapping(utf8, utf8Units, &mapping);

size_t wordBreak = 0;
while (wordBreak < utf8Units) {
    wordBreak += grapheme_next_word_break_utf8(utf8 + wordBreak, utf8Units - wordBreak);
    results->emplace_back(mapping[wordBreak]);
}
```

### getUtf8Words

提取单词边界,结果为 UTF-8 位置:

```cpp
bool getUtf8Words(
    const char utf8[], int utf8Units,
    const char* locale,
    std::vector<Position>* results) override;
```

**实现策略:**

该方法不使用 libgrapheme 的单词分割,而是基于以下规则:
1. 软换行位置
2. 空白字符边界
3. CJK 表意字符边界

```cpp
std::vector<CodeUnitFlags> breaks(utf8Units + 1, CodeUnitFlags::kNoCodeUnitFlag);

// 标记换行
size_t lineBreak = 0;
while (lineBreak < utf8Units) {
    lineBreak += grapheme_next_line_break_utf8(utf8 + lineBreak, utf8Units - lineBreak);
    breaks[lineBreak] = CodeUnitFlags::kSoftLineBreakBefore;
}

// 标记空白和表意字符
const char* current = utf8;
while (current < end) {
    auto index = current - utf8;
    SkUnichar unichar = SkUTF::NextUTF8(&current, end);
    if (isWhitespace(unichar)) {
        breaks[index] = CodeUnitFlags::kPartOfWhiteSpaceBreak;
    } else if (isIdeographic(unichar)) {
        breaks[index] = CodeUnitFlags::kIdeographic;
    }
}

// 生成单词边界
for (size_t i = 0; i < breaks.size(); ++i) {
    if (breaks[i] == CodeUnitFlags::kSoftLineBreakBefore ||
        breaks[i] == CodeUnitFlags::kIdeographic ||
        (breaks[i] == CodeUnitFlags::kPartOfWhiteSpaceBreak && !whitespaces)) {
        results->emplace_back(i);
    }
}
```

### toUpper

使用 libgrapheme 的大写转换:

```cpp
SkString toUpper(const SkString& str, const char* locale) override {
    SkString res(" ", str.size());
    grapheme_to_uppercase_utf8(str.data(), str.size(), res.data(), res.size());
    return res;
}
```

### getBidiRegions

委托给 ICU 子集工厂:

```cpp
bool getBidiRegions(
    const char utf8[], int utf8Units,
    TextDirection dir,
    std::vector<BidiRegion>* results) override {
    return fBidiFact->ExtractBidi(utf8, utf8Units, dir, results);
}
```

### reorderVisual

委托给 ICU 子集工厂的 BiDi 重排序:

```cpp
void reorderVisual(
    const BidiLevel runLevels[], int levelsCount,
    int32_t logicalFromVisual[]) override {
    if (levelsCount == 0) return;
    SkASSERT(runLevels != nullptr);
    fBidiFact->bidi_reorderVisual(runLevels, levelsCount, logicalFromVisual);
}
```

## 内部实现细节

### SkBreakIterator_libgrapheme 实现

**setText 方法:**

```cpp
bool setText(const char utftext8[], int utf8Units) override {
    fLineBreaks.clear();
    // first() 必须总是从文本开始
    fLineBreaks.emplace_back(0, SkUnicode::LineBreakType::kHardLineBreak);

    for (size_t pos = 0; pos < utf8Units;) {
        pos += grapheme_next_line_break_utf8(utftext8 + pos, utf8Units - pos);
        auto codePoint = utftext8[pos];
        fLineBreaks.emplace_back(
            pos,
            fUnicode->isHardBreak(codePoint)
                ? SkUnicode::LineBreakType::kHardLineBreak
                : SkUnicode::LineBreakType::kSoftLineBreak);
    }

    // 总是有一个 "结束" 标记表示完成
    fLineBreaks.emplace_back(kDone, SkUnicode::LineBreakType::kHardLineBreak);
    fLineBreakIndex = 0;
    return true;
}
```

**迭代器方法:**

```cpp
Position first() override {
    return fLineBreaks[(fLineBreakIndex = 0)].pos;
}

Position next() override {
    return fLineBreaks[++fLineBreakIndex].pos;
}

Status status() override {
    return fLineBreaks[fLineBreakIndex].breakType == SkUnicode::LineBreakType::kHardLineBreak
        ? SkUnicode::CodeUnitFlags::kHardLineBreakBefore
        : SkUnicode::CodeUnitFlags::kSoftLineBreakBefore;
}

bool isDone() override {
    return fLineBreaks[fLineBreakIndex].pos == kDone;
}
```

### UTF-8 到 UTF-16 映射

```cpp
bool getUtf8To16Mapping(
    const char utf8[], int utf8Units,
    std::unordered_map<Position, Position>* results) {
    int utf16Units = 0;
    const char* ptr8 = utf8;
    const char* end8 = utf8 + utf8Units;

    while (ptr8 < end8) {
        results->emplace(ptr8 - utf8, utf16Units);
        SkUnichar uni = SkUTF::NextUTF8(&ptr8, end8);
        if (uni < 0) return false;

        uint16_t utf16[2];
        size_t count = SkUTF::ToUTF16(uni, utf16);
        if (count == 0) return false;
        utf16Units += count;
    }

    results->emplace(utf8Units, utf16Units);
    return true;
}
```

## 依赖关系

**外部库:**
- `<grapheme.h>` - libgrapheme 文本分割库

**Skia 依赖:**
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `modules/skunicode/include/SkUnicode_libgrapheme.h` - 公共接口
- `modules/skunicode/src/SkUnicode_hardcoded.h` - 字符属性基类
- `modules/skunicode/src/SkUnicode_icu_bidi.h` - BiDi 接口
- `modules/skunicode/src/SkBidiFactory_icu_subset.h` - BiDi 工厂

**标准库:**
- `<memory>`, `<vector>`, `<unordered_map>`

## 设计模式与设计决策

### 继承 vs 组合

该类使用**多重策略**:
- **继承** `SkUnicodeHardCodedCharProperties` 获取字符属性
- **组合** `SkBidiSubsetFactory` 处理双向文本
- **组合** libgrapheme 函数处理文本分割

### 混合实现

结合多个库的优势:
- 硬编码数据提供字符属性(无需额外库)
- libgrapheme 提供文本分割(轻量级)
- ICU 子集提供双向文本支持(最小 ICU 依赖)

### 性能与功能的权衡

某些方法有简化实现:
- `getSentences()` 未实现
- `getUtf8Words()` 使用启发式规则而非完整分词
- UTF-16 支持有限(`computeCodeUnitFlags` 对 UTF-16 断言失败)

### 向量 vs 缓存

`SkBreakIterator_libgrapheme` 预先计算所有换行位置并存储在向量中,而不是按需计算:

**优点:**
- 简化迭代器实现
- 支持随机访问
- `setText` 后所有信息都已准备好

**缺点:**
- 对大文本需要更多内存
- 无法增量处理

## 性能考量

### 内存占用

对于 N 个字符的文本:
- `computeCodeUnitFlags`: O(N) 标志数组
- `getWords`: O(M) UTF-8 到 UTF-16 映射,M 为单词数
- `SkBreakIterator`: O(L) 换行位置向量,L 为换行数

### 时间复杂度

- `computeCodeUnitFlags`: O(N) - 三次遍历(换行、字素、字符)
- `getWords`: O(N) - 两次遍历(映射构建、分词)
- `getUtf8Words`: O(N) - 两次遍历(标记、生成边界)
- `toUpper`: O(N) - libgrapheme 大写转换

### libgrapheme 性能特点

libgrapheme 函数都是 **O(n)** 复杂度,使用查表法和状态机:
- `grapheme_next_line_break_utf8()` - 行分割
- `grapheme_next_word_break_utf8()` - 词分割
- `grapheme_next_character_break_utf8()` - 字素分割

这些函数不分配内存,开销很小。

### 二进制大小

libgrapheme 非常小:
- 完整库 < 100KB
- 比 ICU (数 MB) 小得多
- 非常适合 WebAssembly 和嵌入式环境

## 相关文件

**基类:**
- `/modules/skunicode/src/SkUnicode_hardcoded.h` - 字符属性基类

**接口:**
- `/modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `/modules/skunicode/include/SkUnicode_libgrapheme.h` - 公共接口

**BiDi 支持:**
- `/modules/skunicode/src/SkUnicode_icu_bidi.h` - BiDi 工厂接口
- `/modules/skunicode/src/SkBidiFactory_icu_subset.h` - ICU 子集实现

**工厂方法:**
- `SkUnicodes::Libgrapheme::Make()` - 创建实例

**替代实现:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - 完整 ICU 实现
- `/modules/skunicode/src/SkUnicode_icu4x.cpp` - ICU4X 实现
