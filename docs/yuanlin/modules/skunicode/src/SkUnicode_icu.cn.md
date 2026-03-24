# SkUnicode_icu

> 源文件: modules/skunicode/src/SkUnicode_icu.cpp

## 概述

`SkUnicode_icu` 是基于完整 ICU (International Components for Unicode) 库实现的 Unicode 处理类,为 Skia 提供全功能的 Unicode 支持。ICU 是成熟的、工业级的 Unicode 和国际化库,被广泛应用于各种软件系统。该实现提供了字符属性查询、文本分割(单词、行、句子、字素)、双向文本处理、大小写转换等完整功能。

这是 Skia Unicode 模块的标准实现,适用于对 Unicode 支持有完整需求的场景,如桌面应用、服务器端渲染等。

## 架构位置

```
skia/modules/skunicode/
├── include/
│   ├── SkUnicode.h        # Unicode 接口
│   └── SkUnicode_icu.h    # ICU 实现接口
└── src/
    ├── SkUnicode_icu.cpp  # 本文件:完整实现
    ├── SkUnicode_icupriv.h           # ICU 私有接口
    ├── SkBidiFactory_icu_full.h      # BiDi 工厂
    └── SkIcuBreakIteratorCache.h     # 迭代器缓存
```

## 主要类与结构体

### SkUnicode_icu

主实现类:

```cpp
class SkUnicode_icu : public SkUnicode {
private:
    sk_sp<SkBidiFactory> fBidiFact = sk_make_sp<SkBidiICUFactory>();
    // 所有方法通过 ICU 函数实现
};
```

### SkBreakIterator_icu

ICU 断点迭代器包装类:

```cpp
class SkBreakIterator_icu : public SkBreakIterator {
    ICUBreakIterator fBreakIterator;
    Position fLastResult;
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

### SkIcuBreakIteratorCache

断点迭代器缓存系统,避免重复创建昂贵的 ICU 对象:

```cpp
class SkIcuBreakIteratorCache final {
    struct Request { /* 缓存键 */ };
    class BreakIteratorRef { /* 迭代器引用计数包装 */ };
    THashMap<Request, sk_sp<BreakIteratorRef>, Request::Hash> fRequestCache;
    SkMutex fCacheMutex;

public:
    static SkIcuBreakIteratorCache& get();
    ICUBreakIterator makeBreakIterator(SkUnicode::BreakType type, const char* bcp47);
};
```

## 公共 API 函数

### 字符属性查询

所有字符属性通过 ICU 函数查询:

```cpp
bool isControl(SkUnichar utf8) override {
    return sk_u_iscntrl(utf8);
}

bool isWhitespace(SkUnichar utf8) override {
    return sk_u_isWhitespace(utf8);
}

bool isSpace(SkUnichar utf8) override {
    return sk_u_isspace(utf8);
}

bool isEmoji(SkUnichar unichar) override {
    return sk_u_hasBinaryProperty(unichar, UCHAR_EMOJI);
}

bool isEmojiComponent(SkUnichar unichar) override {
    return sk_u_hasBinaryProperty(unichar, UCHAR_EMOJI_COMPONENT);
}

bool isIdeographic(SkUnichar unichar) override {
    return sk_u_hasBinaryProperty(unichar, UCHAR_IDEOGRAPHIC);
}
```

### isHardLineBreak

检测硬换行符:

```cpp
static bool isHardLineBreak(SkUnichar utf8) {
    auto property = sk_u_getIntPropertyValue(utf8, UCHAR_LINE_BREAK);
    return property == U_LB_LINE_FEED || property == U_LB_MANDATORY_BREAK;
}
```

### makeBreakIterator

创建文本断点迭代器:

```cpp
std::unique_ptr<SkBreakIterator> makeBreakIterator(
    const char locale[], BreakType type) override {
    ICUBreakIterator iterator = SkIcuBreakIteratorCache::get().makeBreakIterator(type, locale);
    if (!iterator) {
        return nullptr;
    }
    return std::unique_ptr<SkBreakIterator>(new SkBreakIterator_icu(std::move(iterator)));
}
```

### computeCodeUnitFlags (UTF-8)

计算每个代码单元的属性标志:

```cpp
bool computeCodeUnitFlags(
    char utf8[], int utf8Units, bool replaceTabs,
    TArray<SkUnicode::CodeUnitFlags, true>* results) override {

    results->clear();
    results->push_back_n(utf8Units + 1, CodeUnitFlags::kNoCodeUnitFlag);

    // 标记行断点
    extractPositions(utf8, utf8Units, BreakType::kLines, nullptr,
        [&](int pos, int status) {
            (*results)[pos] |= status == UBRK_LINE_HARD
                ? CodeUnitFlags::kHardLineBreakBefore
                : CodeUnitFlags::kSoftLineBreakBefore;
        });

    // 标记字素簇
    extractPositions(utf8, utf8Units, BreakType::kGraphemes, nullptr,
        [&](int pos, int status) {
            (*results)[pos] |= CodeUnitFlags::kGraphemeStart;
        });

    // 标记字符属性
    const char* current = utf8;
    const char* end = utf8 + utf8Units;
    while (current < end) {
        auto before = current - utf8;
        SkUnichar unichar = SkUTF::NextUTF8(&current, end);
        // ... 标记空格、空白、控制符、表意字
    }

    return true;
}
```

### getWords

提取单词边界:

```cpp
bool getWords(
    const char utf8[], int utf8Units, const char* locale,
    std::vector<Position>* results) override {

    auto utf16 = convertUtf8ToUtf16(utf8, utf8Units);
    return SkUnicode_icu::extractWords(
        reinterpret_cast<uint16_t*>(utf16.data()),
        utf16.size(), locale, results);
}
```

### toUpper

大写转换:

```cpp
SkString toUpper(const SkString& str, const char* locale) override {
    auto str16 = SkUnicode::convertUtf8ToUtf16(str.c_str(), str.size());

    UErrorCode icu_err = U_ZERO_ERROR;
    const auto upper16len = sk_u_strToUpper(
        nullptr, 0,
        reinterpret_cast<const UChar*>(str16.c_str()), str16.size(),
        locale, &icu_err);

    AutoSTArray<128, uint16_t> upper16(upper16len);
    icu_err = U_ZERO_ERROR;
    sk_u_strToUpper(
        reinterpret_cast<UChar*>(upper16.get()), SkToS32(upper16.size()),
        reinterpret_cast<const UChar*>(str16.c_str()), str16.size(),
        locale, &icu_err);

    return convertUtf16ToUtf8((char16_t*)upper16.get(), upper16.size());
}
```

## 内部实现细节

### ICU 函数包装

使用宏生成包装函数:

```cpp
#define SKICU_FUNC(funcname)                                                                \
    template <typename... Args>                                                             \
    auto sk_##funcname(Args&&... args) -> decltype(funcname(std::forward<Args>(args)...)) { \
        return SkGetICULib()->f_##funcname(std::forward<Args>(args)...);                    \
    }

SKICU_EMIT_FUNCS
#undef SKICU_FUNC
```

这生成类似 `sk_u_errorName`, `sk_ubrk_open` 等包装函数。

### BreakIterator 缓存机制

**缓存键:**

```cpp
struct Request final {
    Request(SkUnicode::BreakType type, const char* icuLocale)
        : fType(type)
        , fIcuLocale(icuLocale)
        , hash(SkGoodHash()(type) ^ SkGoodHash()(fIcuLocale))
    {}
    const SkUnicode::BreakType fType;
    const SkString fIcuLocale;
    const uint32_t hash;
};
```

**缓存查找:**

```cpp
const sk_sp<BreakIteratorRef>* ref = fRequestCache.find(request);
if (ref) {
    if (!(*ref)->breakIterator) {
        (*ref)->breakIterator = make(request);
    }
    return clone((*ref)->breakIterator);
}
```

**缓存清理:**

```cpp
void purgeIfNeeded() {
    if (fRequestCache.count() > 100) {
        fRequestCache.reset();
    }
    if (BreakIteratorRef::GetInstanceCount() > 4) {
        for (auto&& [key, value] : fRequestCache) {
            if (value->breakIterator) {
                sk_ubrk_close(value->breakIterator);
                value->breakIterator = nullptr;
            }
        }
    }
}
```

### extractPositions 辅助函数

通用的断点提取函数:

```cpp
static bool extractPositions(
    const char utf8[], int utf8Units,
    BreakType type, const char* locale,
    const std::function<void(int, int)>& setBreak) {

    ICUUText text(sk_utext_openUTF8(nullptr, &utf8[0], utf8Units, &status));
    ICUBreakIterator iterator = SkIcuBreakIteratorCache::get().makeBreakIterator(type, locale);

    sk_ubrk_setUText(iterator.get(), text.get(), &status);

    int32_t pos = sk_ubrk_first(iter);
    while (pos != UBRK_DONE) {
        int s = type == SkUnicode::BreakType::kLines
            ? UBRK_LINE_SOFT
            : sk_ubrk_getRuleStatus(iter);
        setBreak(pos, s);
        pos = sk_ubrk_next(iter);
    }

    // 硬换行 hack
    if (type == SkUnicode::BreakType::kLines) {
        const char* end = utf8 + utf8Units;
        const char* ch = utf8;
        while (ch < end) {
            auto unichar = utf8_next(&ch, end);
            if (SkUnicode_icu::isHardLineBreak(unichar)) {
                setBreak(ch - utf8, UBRK_LINE_HARD);
            }
        }
    }
    return true;
}
```

### 智能指针管理

使用自定义删除器管理 ICU 对象:

```cpp
static void ubrk_close_wrapper(UBreakIterator* bi) {
    sk_ubrk_close(bi);
}

static UText* utext_close_wrapper(UText* ut) {
    return sk_utext_close(ut);
}

using ICUUText = std::unique_ptr<UText, SkFunctionObject<utext_close_wrapper>>;
using ICUBreakIterator = std::unique_ptr<UBreakIterator, SkFunctionObject<ubrk_close_wrapper>>;
```

## 依赖关系

**ICU 头文件:**
- `<unicode/ubrk.h>`, `<unicode/uchar.h>`, `<unicode/uloc.h>`, etc.

**Skia 依赖:**
- `modules/skunicode/include/SkUnicode.h`
- `modules/skunicode/include/SkUnicode_icu.h`
- `modules/skunicode/src/SkUnicode_icupriv.h`
- `modules/skunicode/src/SkBidiFactory_icu_full.h`

## 设计模式

### 单例模式

缓存使用单例:

```cpp
static SkIcuBreakIteratorCache& get() {
    static SkIcuBreakIteratorCache instance;
    return instance;
}
```

### 对象池模式

BreakIterator 缓存实现了对象池,复用昂贵的 ICU 对象。

### RAII

所有 ICU 对象使用智能指针管理,确保资源释放。

### 策略模式

不同的 BreakType 使用不同的 ICU 迭代器类型。

## 性能考量

### 缓存效率

- 避免重复创建 BreakIterator
- 限制缓存大小(100 个请求,4 个实例)
- 使用克隆而非重新创建

### UTF 转换开销

许多操作需要 UTF-8 到 UTF-16 转换,因为 ICU 主要使用 UTF-16。

### 硬换行 Hack

由于 ICU 的泰语换行 bug,需要额外遍历检测硬换行,增加开销。

## 相关文件

- `/modules/skunicode/include/SkUnicode.h`
- `/modules/skunicode/src/SkUnicode_icupriv.h`
- `/modules/skunicode/src/SkBidiFactory_icu_full.h`
- `/modules/skunicode/src/SkUnicode_icu_runtime.cpp`
- `/modules/skunicode/src/SkUnicode_icu_builtin.cpp`
