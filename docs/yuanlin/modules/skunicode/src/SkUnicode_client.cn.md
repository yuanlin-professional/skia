# SkUnicode_client

> 源文件: modules/skunicode/src/SkUnicode_client.cpp

## 概述

`SkUnicode_client` 是一个客户端提供数据的 Unicode 实现类。与其他 Unicode 实现不同,该类不自己计算文本的分割和属性,而是接受客户端预先计算好的单词边界、字素簇边界和换行信息。这种设计允许应用程序使用自己的 Unicode 处理逻辑,或者在不同环境(如浏览器、操作系统)中复用已有的文本分析结果。

该实现特别适用于需要与外部文本处理系统集成的场景,避免了重复计算,提高了性能,同时保持了与 Skia 文本处理管道的兼容性。

## 架构位置

```
skia/
└── modules/
    └── skunicode/
        ├── include/
        │   ├── SkUnicode.h           # Unicode 接口
        │   └── SkUnicode_client.h    # Client 接口
        └── src/
            ├── SkUnicode_client.cpp  # 本文件
            ├── SkUnicode_hardcoded.h # 字符属性基类
            └── SkBidiFactory_icu_subset.h # BiDi 工厂
```

## 主要类与结构体

### SkUnicode_client::Data

存储客户端提供的文本分析数据:

```cpp
struct Data {
    SkSpan<const char> fText8;           // UTF-8 文本
    SkSpan<const char16_t> fText16;      // UTF-16 文本
    std::vector<Position> fWords;        // 单词边界
    std::vector<Position> fGraphemeBreaks;  // 字素簇边界
    std::vector<LineBreakBefore> fLineBreaks;  // 换行位置

    Data(SkSpan<char> text,
         std::vector<Position> words,
         std::vector<Position> graphemeBreaks,
         std::vector<LineBreakBefore> lineBreaks);

    void reset();
};
```

### SkUnicode_client

主实现类,继承自 `SkUnicodeHardCodedCharProperties`:

```cpp
class SkUnicode_client : public SkUnicodeHardCodedCharProperties {
public:
    SkUnicode_client(
        SkSpan<char> text,
        std::vector<Position> words,
        std::vector<Position> graphemeBreaks,
        std::vector<LineBreakBefore> lineBreaks);

    ~SkUnicode_client() override = default;

    void reset();

private:
    std::shared_ptr<Data> fData;
    sk_sp<SkBidiFactory> fBidiFact = sk_make_sp<SkBidiSubsetFactory>();
};
```

### SkBreakIterator_client

客户端提供数据的换行迭代器:

```cpp
class SkBreakIterator_client : public SkBreakIterator {
    std::shared_ptr<SkUnicode_client::Data> fData;
    Position fLastResult;
    Position fStart;
    Position fEnd;

public:
    explicit SkBreakIterator_client(std::shared_ptr<SkUnicode_client::Data> data);
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

### 构造函数

```cpp
SkUnicode_client(
    SkSpan<char> text,
    std::vector<Position> words,
    std::vector<Position> graphemeBreaks,
    std::vector<LineBreakBefore> lineBreaks);
```

**参数:**
- `text` - 文本数据的 span
- `words` - 预计算的单词边界位置
- `graphemeBreaks` - 预计算的字素簇边界
- `lineBreaks` - 预计算的换行位置及类型

**初始化:**
```cpp
: fData(std::make_shared<Data>(
    text,
    std::move(words),
    std::move(graphemeBreaks),
    std::move(lineBreaks))) { }
```

### computeCodeUnitFlags (UTF-8 版本)

使用客户端提供的数据计算代码单元标志:

```cpp
bool computeCodeUnitFlags(
    char utf8[], int utf8Units,
    bool replaceTabs,
    TArray<SkUnicode::CodeUnitFlags, true>* results) override;
```

**实现逻辑:**

1. 初始化标志数组
2. 应用换行标志
3. 应用字素簇标志
4. 遍历字符应用字符属性

```cpp
results->clear();
results->push_back_n(utf8Units + 1, CodeUnitFlags::kNoCodeUnitFlag);

// 应用换行标志
for (auto& lineBreak : fData->fLineBreaks) {
    (*results)[lineBreak.pos] |=
        lineBreak.breakType == LineBreakType::kHardLineBreak
            ? CodeUnitFlags::kHardLineBreakBefore
            : CodeUnitFlags::kSoftLineBreakBefore;
}

// 应用字素簇标志
for (auto& grapheme : fData->fGraphemeBreaks) {
    (*results)[grapheme] |= CodeUnitFlags::kGraphemeStart;
}

// 遍历字符
const char* current = utf8;
const char* end = utf8 + utf8Units;
while (current < end) {
    auto before = current - utf8;
    SkUnichar unichar = SkUTF::NextUTF8(&current, end);
    if (unichar < 0) unichar = 0xFFFD;
    auto after = current - utf8;

    if (replaceTabs && isTabulation(unichar)) {
        results->at(before) |= SkUnicode::kTabulation;
        unichar = ' ';
        utf8[before] = ' ';
    }

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
        if (isIdeographic(unichar)) {
            results->at(i) |= SkUnicode::kIdeographic;
        }
    }
}
```

### computeCodeUnitFlags (UTF-16 版本)

UTF-16 版本的实现,不需要 UTF 解码:

```cpp
bool computeCodeUnitFlags(
    char16_t utf16[], int utf16Units,
    bool replaceTabs,
    TArray<SkUnicode::CodeUnitFlags, true>* results) override;
```

**实现特点:**
- 直接应用预计算的标志
- 逐个字符检查属性(空格、空白、控制符、表意字)
- 不支持制表符替换为多字节序列

### getWords

直接返回客户端提供的单词边界:

```cpp
bool getWords(
    const char utf8[], int utf8Units,
    const char* locale,
    std::vector<Position>* results) override {
    *results = fData->fWords;
    return true;
}
```

### toUpper

返回预先存储的文本(假设已是大写):

```cpp
SkString toUpper(const SkString& str, const char* locale) override {
    return SkString(fData->fText8.data(), fData->fText8.size());
}
```

**注意:** 这是一个简化实现,实际上不进行大写转换。

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

### reset

清除所有缓存数据:

```cpp
void reset() {
    fData->reset();
}
```

## 内部实现细节

### SkBreakIterator_client 实现

**setText 方法:**

```cpp
bool setText(const char utftext8[], int utf8Units) override {
    SkASSERT(utftext8 >= fData->fText8.data() &&
             utf8Units <= SkToS16(fData->fText8.size()));
    fStart = utftext8 - fData->fText8.data();
    fEnd = fStart + utf8Units;
    fLastResult = 0;
    return true;
}
```

**迭代方法:**

```cpp
Position first() override {
    return fData->fLineBreaks[fStart + (fLastResult = 0)].pos;
}

Position current() override {
    return fData->fLineBreaks[fStart + fLastResult].pos;
}

Position next() override {
    return fData->fLineBreaks[fStart + fLastResult + 1].pos;
}

Status status() override {
    return fData->fLineBreaks[fStart + fLastResult].breakType ==
            SkUnicode::LineBreakType::kHardLineBreak
        ? SkUnicode::CodeUnitFlags::kHardLineBreakBefore
        : SkUnicode::CodeUnitFlags::kSoftLineBreakBefore;
}

bool isDone() override {
    return fStart + fLastResult == fEnd;
}
```

### Data 结构管理

`Data` 结构使用 `shared_ptr` 共享:

```cpp
std::shared_ptr<Data> fData;
```

这允许多个对象(Unicode 实例和迭代器)引用同一数据,避免复制。

**reset 方法:**

```cpp
void Data::reset() {
    fText8 = SkSpan<const char>(nullptr, 0);
    fText16 = SkSpan<const char16_t>(nullptr, 0);
    fGraphemeBreaks.clear();
    fLineBreaks.clear();
}
```

### 工厂方法

在命名空间中提供工厂函数:

```cpp
namespace SkUnicodes::Client {
sk_sp<SkUnicode> Make(
    SkSpan<char> text,
    std::vector<SkUnicode::Position> words,
    std::vector<SkUnicode::Position> graphemeBreaks,
    std::vector<SkUnicode::LineBreakBefore> lineBreaks) {
    return sk_make_sp<SkUnicode_client>(
        text,
        std::move(words),
        std::move(graphemeBreaks),
        std::move(lineBreaks));
}
}
```

## 依赖关系

**Skia 依赖:**
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `modules/skunicode/include/SkUnicode_client.h` - 公共接口
- `modules/skunicode/src/SkUnicode_hardcoded.h` - 字符属性基类
- `modules/skunicode/src/SkBidiFactory_icu_subset.h` - BiDi 工厂

**标准库:**
- `<memory>` - 智能指针
- `<vector>` - 容器
- `<utility>` - move 语义

**ICU 依赖:**
- 通过 `SkBidiSubsetFactory` 间接依赖 ICU BiDi 功能

## 设计模式与设计决策

### 依赖注入模式

客户端在创建时注入所有需要的数据:

```cpp
SkUnicode_client(text, words, graphemeBreaks, lineBreaks)
```

这是典型的依赖注入,将计算责任从类中移出。

### 享元模式

使用 `shared_ptr<Data>` 共享数据:
- 多个迭代器可以引用同一数据
- 避免数据复制
- 减少内存占用

### 适配器模式

该类是一个适配器,将客户端数据格式适配到 Skia 的 Unicode 接口:

```
Client Data → SkUnicode_client → SkUnicode Interface
```

### 策略模式

字符属性查询通过继承获得:
- 继承 `SkUnicodeHardCodedCharProperties` 获取基本字符属性
- 组合 `SkBidiSubsetFactory` 获取 BiDi 处理能力

### 简化实现

某些方法有简化或存根实现:
- `getUtf8Words()` 未实现,返回 false
- `getSentences()` 未实现,返回 false
- `toUpper()` 不做实际转换

这表明该实现专注于核心用例,不提供完整功能。

## 性能考量

### 零计算开销

该实现的主要优势是**不进行文本分析计算**:
- 单词边界已预计算
- 字素簇边界已预计算
- 换行位置已预计算

这使得创建和使用非常快速。

### 内存占用

需要存储所有边界信息:
- 单词边界向量: O(M),M 为单词数
- 字素簇边界向量: O(G),G 为字素数
- 换行位置向量: O(L),L 为可能换行位置数

对于长文本,这可能占用大量内存。

### 迭代器效率

`SkBreakIterator_client` 直接索引预计算的向量:
- `first()`, `current()`, `next()`: O(1)
- `isDone()`: O(1)
- `setText()`: O(1)

非常高效,无需重新计算。

### 共享数据的开销

使用 `shared_ptr` 有轻微开销:
- 引用计数原子操作
- 额外的内存指针

但避免了数据复制,总体是高效的。

## 相关文件

**接口:**
- `/modules/skunicode/include/SkUnicode.h` - Unicode 基类
- `/modules/skunicode/include/SkUnicode_client.h` - 公共接口

**基类:**
- `/modules/skunicode/src/SkUnicode_hardcoded.h` - 字符属性

**BiDi 支持:**
- `/modules/skunicode/src/SkBidiFactory_icu_subset.h` - ICU 子集

**工厂:**
- `SkUnicodes::Client::Make()` - 工厂方法

**其他实现:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - ICU 实现
- `/modules/skunicode/src/SkUnicode_icu4x.cpp` - ICU4X 实现
- `/modules/skunicode/src/SkUnicode_libgrapheme.cpp` - Libgrapheme 实现
