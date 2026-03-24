# SkBidiFactory

> 源文件: modules/skunicode/src/SkUnicode_icu_bidi.h, modules/skunicode/src/SkUnicode_icu_bidi.cpp

## 概述

`SkBidiFactory` 是一个抽象基类,为 Skia 提供双向文本(BiDi)处理能力。该类封装了 ICU 库的双向文本算法,支持从左到右(LTR)和从右到左(RTL)的文本排版。它被设计为一个工厂类,能够创建双向文本迭代器,并提取文本的双向区域信息。

双向文本处理对于支持阿拉伯语、希伯来语等从右到左书写的语言至关重要。该类允许 Skia 的某些 Unicode 实现只使用 ICU 的一小部分功能,而不需要链接完整的 ICU 库。

## 架构位置

该类位于 Skia 的 Unicode 模块中,作为双向文本处理的抽象层:

```
skia/
├── modules/
│   └── skunicode/
│       ├── include/
│       │   └── SkUnicode.h          # Unicode 主接口
│       └── src/
│           ├── SkUnicode_icu_bidi.h     # BiDi 工厂接口
│           ├── SkUnicode_icu_bidi.cpp   # BiDi 工厂实现
│           ├── SkBidiFactory_icu_full.h     # 完整 ICU BiDi 实现
│           ├── SkBidiFactory_icu_subset.h   # ICU 子集 BiDi 实现
│           ├── SkUnicode_libgrapheme.cpp    # 使用 BiDi 工厂
│           └── SkUnicode_client.cpp         # 使用 BiDi 工厂
```

## 主要类与结构体

### SkBidiFactory

```cpp
class SkBidiFactory : public SkRefCnt
```

抽象工厂类,定义了双向文本处理的接口。

**核心方法:**

```cpp
// 创建双向迭代器
std::unique_ptr<SkBidiIterator> MakeIterator(
    const uint16_t utf16[], int utf16Units, SkBidiIterator::Direction dir) const;
std::unique_ptr<SkBidiIterator> MakeIterator(
    const char utf8[], int utf8Units, SkBidiIterator::Direction dir) const;

// 提取双向区域
bool ExtractBidi(
    const char utf8[], int utf8Units,
    SkUnicode::TextDirection dir,
    std::vector<SkUnicode::BidiRegion>* bidiRegions) const;
```

**ICU 函数抽象接口:**

该类定义了一组纯虚函数,用于封装 ICU 的 BiDi 函数:

```cpp
virtual const char* errorName(UErrorCode status) const = 0;
virtual BidiCloseCallback bidi_close_callback() const = 0;
virtual UBiDiDirection bidi_getDirection(const UBiDi* bidi) const = 0;
virtual SkBidiIterator::Position bidi_getLength(const UBiDi* bidi) const = 0;
virtual SkBidiIterator::Level bidi_getLevelAt(const UBiDi* bidi, int pos) const = 0;
virtual UBiDi* bidi_openSized(int32_t maxLength, int32_t maxRunCount, UErrorCode* pErrorCode) const = 0;
virtual void bidi_setPara(UBiDi* bidi, const UChar* text, int32_t length,
                          UBiDiLevel paraLevel, UBiDiLevel* embeddingLevels, UErrorCode* status) const = 0;
virtual void bidi_reorderVisual(const SkUnicode::BidiLevel runLevels[], int levelsCount,
                                int32_t logicalFromVisual[]) const = 0;
```

### SkBidiIterator_icu

```cpp
class SkBidiIterator_icu : public SkBidiIterator
```

内部实现类,封装 ICU 的 `UBiDi` 对象,提供双向文本的遍历能力。

**成员:**
- `SkUnicodeBidi fBidi` - ICU BiDi 对象的智能指针
- `sk_sp<SkBidiFactory> fBidiFact` - 工厂的引用计数指针

**方法:**
- `getLength()` - 返回文本长度
- `getLevelAt(Position pos)` - 返回指定位置的嵌套级别

## 公共 API 函数

### MakeIterator (UTF-16 版本)

创建基于 UTF-16 文本的双向迭代器。

```cpp
std::unique_ptr<SkBidiIterator> MakeIterator(
    const uint16_t utf16[], int utf16Units, SkBidiIterator::Direction dir) const;
```

**参数:**
- `utf16[]` - UTF-16 编码的文本
- `utf16Units` - UTF-16 代码单元数量
- `dir` - 文本方向 (kLTR 或 kRTL)

**返回:**
- 成功时返回迭代器,失败时返回 `nullptr`

**实现步骤:**
1. 创建 ICU BiDi 对象
2. 根据方向设置 BiDi 级别
3. 调用 `ubidi_setPara` 设置文本
4. 包装成 `SkBidiIterator_icu` 返回

### MakeIterator (UTF-8 版本)

创建基于 UTF-8 文本的双向迭代器。

```cpp
std::unique_ptr<SkBidiIterator> MakeIterator(
    const char utf8[], int utf8Units, SkBidiIterator::Direction dir) const;
```

**实现逻辑:**
1. 将 UTF-8 转换为 UTF-16 (因为 ICU BiDi 只接受 UTF-16)
2. 调用 UTF-16 版本的 `MakeIterator`

**错误处理:**
- 检查文本长度是否超过 `int32_t` 范围
- 检查 UTF-8 是否有效
- 处理 ICU 错误状态

### ExtractBidi

从文本中提取所有双向区域。

```cpp
bool ExtractBidi(
    const char utf8[], int utf8Units,
    SkUnicode::TextDirection dir,
    std::vector<SkUnicode::BidiRegion>* bidiRegions) const;
```

**参数:**
- `utf8[]` - UTF-8 文本
- `utf8Units` - UTF-8 字节数
- `dir` - 段落的基本方向
- `bidiRegions` - 输出的 BiDi 区域列表

**返回:**
- 成功返回 `true`,失败返回 `false`

**BidiRegion 结构:**
```cpp
struct BidiRegion {
    Position start;  // 区域起始位置 (UTF-8 偏移)
    Position end;    // 区域结束位置 (UTF-8 偏移)
    BidiLevel level; // 嵌套级别
};
```

## 内部实现细节

### UTF-8 到 UTF-16 的转换

由于 ICU 的 BiDi 算法只支持 UTF-16,所有 UTF-8 输入都需要转换:

```cpp
int utf16Units = SkUTF::UTF8ToUTF16(nullptr, 0, utf8, utf8Units);
std::unique_ptr<uint16_t[]> utf16(new uint16_t[utf16Units]);
SkUTF::UTF8ToUTF16(utf16.get(), utf16Units, utf8, utf8Units);
```

### 双向区域提取算法

`ExtractBidi` 的实现使用双指针技术同步遍历 UTF-8 和 UTF-16:

```cpp
const char* start8 = utf8;
const char* end8 = utf8 + utf8Units;
Position pos8 = 0;   // UTF-8 位置
Position pos16 = 0;  // UTF-16 位置
SkUnicode::BidiLevel currentLevel = 0;

while (pos16 < end16) {
    auto level = bidi_getLevelAt(bidi.get(), pos16);
    if (level != currentLevel) {
        // 级别变化,记录前一个区域
        bidiRegions->emplace_back(pos8, start8 - utf8, currentLevel);
        currentLevel = level;
        pos8 = start8 - utf8;
    }
    // 同步前进两个指针
    SkUnichar u = utf8_next(&start8, end8);
    pos16 += SkUTF::ToUTF16(u);
}
```

### 单向文本优化

当整个段落是单向的时,跳过逐字符遍历:

```cpp
if (bidi_getDirection(bidi.get()) != UBIDI_MIXED) {
    // 整个段落是单向的
    bidiRegions->emplace_back(0, utf8Units, bidi_getLevelAt(bidi.get(), 0));
    return true;
}
```

### 智能指针管理

使用自定义删除器管理 ICU 对象:

```cpp
using SkUnicodeBidi = std::unique_ptr<UBiDi, SkBidiFactory::BidiCloseCallback>;
```

这确保了 `UBiDi` 对象在超出作用域时自动调用正确的清理函数。

## 依赖关系

**头文件依赖:**
- `include/core/SkRefCnt.h` - 引用计数支持
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口定义
- `include/private/base/SkDebug.h` - 调试宏
- `src/base/SkUTF.h` - UTF 编码转换

**ICU 依赖:**
- `<unicode/ubidi.h>` - ICU 双向文本算法
- `<unicode/umachine.h>` - ICU 基础类型
- `<unicode/utypes.h>` - ICU 类型定义

**被依赖:**
- `SkUnicode_libgrapheme.cpp` - 使用 `SkBidiSubsetFactory`
- `SkUnicode_client.cpp` - 使用 `SkBidiSubsetFactory`
- `SkUnicode_icu.cpp` - 使用 `SkBidiICUFactory`

## 设计模式与设计决策

### 抽象工厂模式

`SkBidiFactory` 是一个抽象工厂,允许不同的实现:
- `SkBidiICUFactory` - 使用完整的 ICU 库
- `SkBidiSubsetFactory` - 使用 ICU 的最小子集

这种设计使得某些 Unicode 实现可以只链接部分 ICU 功能。

### 策略模式

通过定义虚函数接口,允许子类实现不同的 ICU 函数调用策略。这支持:
- 动态加载 ICU 库
- 静态链接 ICU 库
- 使用不同版本的 ICU API

### 智能指针与 RAII

使用 `std::unique_ptr` 和自定义删除器确保资源安全:

```cpp
SkUnicodeBidi bidi(bidi_openSized(...), bidi_close_callback());
```

即使发生异常,ICU 对象也会被正确释放。

### 错误处理

采用两级错误处理:
1. 返回 `nullptr` 或 `false` 表示失败
2. 使用 `SkDEBUGF` 记录详细错误信息

这使得发布版本不会因为 Unicode 错误而崩溃,同时调试版本能提供足够的信息。

## 性能考量

### UTF-8 到 UTF-16 转换开销

每次处理 UTF-8 文本都需要转换,这是主要的性能开销:
- 需要两次遍历:第一次计算长度,第二次转换
- 需要动态分配内存
- 对于大型文本,可能成为瓶颈

**优化建议:**
- 缓存已转换的 UTF-16 文本
- 对于已知是纯 ASCII 的文本,可以优化转换

### 内存分配

```cpp
std::unique_ptr<uint16_t[]> utf16(new uint16_t[utf16Units]);
```

对于频繁调用,可以考虑:
- 使用对象池
- 使用栈上缓冲区处理小文本
- 复用缓冲区

### BiDi 区域提取的复杂度

- **时间复杂度**: O(n),其中 n 是字符数
- **空间复杂度**: O(m),其中 m 是 BiDi 区域数

对于单向文本,通过早期检查优化为 O(1)。

### 字符迭代优化

使用 `utf8_next` 函数处理无效的 UTF-8 序列:

```cpp
static inline SkUnichar utf8_next(const char** ptr, const char* end) {
    SkUnichar val = SkUTF::NextUTF8(ptr, end);
    return val < 0 ? 0xFFFD : val;  // 替换无效序列为替换字符
}
```

这确保了即使遇到损坏的 UTF-8 也能继续处理。

## 相关文件

**接口定义:**
- `/modules/skunicode/include/SkUnicode.h` - Unicode 主接口

**工厂实现:**
- `/modules/skunicode/src/SkBidiFactory_icu_full.h` - 完整 ICU BiDi 工厂
- `/modules/skunicode/src/SkBidiFactory_icu_subset.h` - ICU 子集 BiDi 工厂

**使用者:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - 完整 ICU Unicode 实现
- `/modules/skunicode/src/SkUnicode_libgrapheme.cpp` - Libgrapheme Unicode 实现
- `/modules/skunicode/src/SkUnicode_client.cpp` - 客户端 Unicode 实现

**工具类:**
- `/src/base/SkUTF.h` - UTF 编码转换工具
- `/include/private/base/SkTFitsIn.h` - 类型范围检查
