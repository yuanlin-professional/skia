# word_boundaries

> 源文件: modules/skplaintexteditor/src/word_boundaries.h, modules/skplaintexteditor/src/word_boundaries.cpp

## 概述

`word_boundaries` 模块提供了一个简单的工具函数,用于识别 UTF-8 文本中的单词边界。该模块封装了 Skia 的 Unicode 库(SkUnicode),支持多种 Unicode 实现(ICU、libgrapheme、ICU4X),为文本编辑器等应用提供单词断点检测功能。

这是一个轻量级的实用工具,主要用于 `skplaintexteditor` 模块中实现双击选词、按单词移动光标等编辑功能。

## 架构位置

该模块位于 `skplaintexteditor` 纯文本编辑器模块中,作为辅助工具存在:

```
skia/modules/
├── skplaintexteditor/
│   └── src/
│       ├── word_boundaries.h/.cpp    # 单词边界检测
│       ├── editor.h/.cpp             # 文本编辑器主类(使用word_boundaries)
│       └── shape.h/.cpp              # 文本整形
└── skunicode/
    ├── include/SkUnicode.h           # Unicode抽象接口
    ├── include/SkUnicode_icu.h       # ICU实现
    ├── include/SkUnicode_libgrapheme.h  # libgrapheme实现
    └── include/SkUnicode_icu4x.h     # ICU4X实现
```

**依赖关系:**
- 依赖 `SkUnicode` 接口进行实际的单词断点检测
- 被文本编辑器用于实现单词级别的文本操作

## 主要类与结构体

该模块非常简单,只包含一个公共函数,没有定义类或结构体。

## 公共 API 函数

### GetUtf8WordBoundaries
```cpp
std::vector<bool> GetUtf8WordBoundaries(const char* begin,
                                        std::size_t byteLen,
                                        const char* locale)
```
检测 UTF-8 文本中的单词边界位置。

**参数:**
- `begin`: UTF-8 文本的起始指针
- `byteLen`: 文本字节长度
- `locale`: 语言区域设置字符串(如 "en_US", "zh_CN"),用于语言相关的单词分割规则

**返回:**
- `std::vector<bool>`: 布尔数组,长度等于 `byteLen`,每个位置标记是否为单词边界
- 空 vector 表示失败或空文本

**使用示例:**
```cpp
const char* text = "Hello world, this is a test.";
auto boundaries = GetUtf8WordBoundaries(text, strlen(text), "en_US");
// boundaries[0] = true  (起始位置)
// boundaries[5] = true  (空格后)
// boundaries[6] = true  ('w'前)
// ...
```

## 内部实现细节

### Unicode 实现选择
内部使用 `get_unicode()` 函数获取可用的 Unicode 实现:

```cpp
namespace {
sk_sp<SkUnicode> get_unicode() {
#if defined(SK_UNICODE_ICU_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU::Make()) {
        return unicode;
    }
#endif
#if defined(SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::Libgrapheme::Make()) {
        return unicode;
    }
#endif
#if defined(SK_UNICODE_ICU4X_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU4X::Make()) {
        return unicode;
    }
#endif
    SkDEBUGFAIL("Cannot make SkUnicode");
    return nullptr;
}
}
```

**实现优先级:**
1. ICU (International Components for Unicode) - 功能最完整
2. libgrapheme - 轻量级实现
3. ICU4X - 现代化 Rust 实现的 ICU

根据编译时定义的宏选择可用的实现,按顺序尝试,返回第一个成功创建的实例。

### 单词边界检测算法
核心实现委托给 `SkUnicode::getWords()`:

```cpp
std::vector<bool> GetUtf8WordBoundaries(const char* begin, size_t byteCount, const char* locale) {
    auto unicode = get_unicode();
    if (nullptr == unicode) {
        return {};  // 无可用的Unicode实现
    }

    std::vector<SkUnicode::Position> positions;
    if (!unicode->getWords(begin, byteCount, locale, &positions) || byteCount == 0) {
        return {};  // 检测失败或空文本
    }

    // 将位置列表转换为布尔数组
    std::vector<bool> result;
    result.resize(byteCount);
    for (auto& pos : positions) {
        result[pos] = true;
    }

    return result;
}
```

**处理流程:**
1. 获取 Unicode 实现实例
2. 调用 `getWords()` 获取所有单词边界位置
3. 将位置列表转换为布尔数组,方便快速查询
4. 默认所有位置为 `false`,仅边界位置为 `true`

### 单词边界规则
单词边界的定义遵循 Unicode 标准 UAX #29(Unicode Text Segmentation):
- 单词与空格之间
- 单词与标点符号之间
- 不同类型文本之间(如英文与中文)
- 语言相关的特殊规则(通过 `locale` 参数指定)

**语言相关示例:**
- 英文: 空格和标点是主要边界
- 中文: 每个汉字可能是一个单词
- 日文: 平假名、片假名、汉字之间可能有边界
- 泰文: 需要字典辅助的单词分割

## 依赖关系

### 核心依赖
- **SkUnicode**: Unicode 处理抽象接口
- **ICU/libgrapheme/ICU4X**: 具体的 Unicode 实现库(编译时选择)

### 使用者
- **skplaintexteditor**: 纯文本编辑器模块的主要使用者
- 可能被其他需要单词级别操作的模块使用

### 依赖图
```
GetUtf8WordBoundaries
    ↓ (uses)
SkUnicode (抽象接口)
    ↓ (implemented by)
ICU / libgrapheme / ICU4X
```

## 设计模式与设计决策

### 简单封装
提供简单的函数接口而非类接口,降低使用复杂度:
- 单一功能函数
- 无状态设计
- 易于集成和测试

### 策略模式(隐式)
通过编译时宏选择不同的 Unicode 实现,支持多种后端:
- 灵活的实现选择
- 平台特定优化
- 无运行时开销

### 布尔数组返回
返回布尔数组而非位置列表,优化查询性能:
- O(1) 边界查询
- 内存占用与文本长度线性相关
- 适合频繁查询的场景

### 错误处理
简单的错误处理策略:
- 无可用 Unicode 实现时返回空 vector
- 检测失败时返回空 vector
- 调用者需要检查返回值

## 性能考量

### 内存使用
- **输入**: 无内存分配,直接使用输入指针
- **输出**: `std::vector<bool>` 大小等于输入字节数
- **中间结果**: `std::vector<Position>` 大小与单词边界数量成正比(通常远小于文本长度)

**优化特性:**
- `std::vector<bool>` 是位打包的特化版本,每个元素仅占 1 bit
- 对于 1KB 文本,输出仅需约 128 字节

### 时间复杂度
- **getWords() 调用**: O(n),其中 n 是文本字节长度
- **位置到布尔数组转换**: O(m),其中 m 是边界数量(m << n)
- **总体**: O(n),线性时间复杂度

### Unicode 实现性能
不同实现的性能特性:
- **ICU**: 功能最完整,性能优秀,但库体积较大
- **libgrapheme**: 轻量级,启动快,但功能有限
- **ICU4X**: 现代实现,性能优化,二进制体积中等

### 缓存考虑
该函数本身不缓存结果,调用者可根据需要缓存:
- 文本不变时可复用边界数组
- 编辑操作后需要重新计算(或局部更新)

## 相关文件

### Unicode 实现
- `modules/skunicode/include/SkUnicode.h`: Unicode 抽象接口
- `modules/skunicode/include/SkUnicode_icu.h`: ICU 实现
- `modules/skunicode/include/SkUnicode_libgrapheme.h`: libgrapheme 实现
- `modules/skunicode/include/SkUnicode_icu4x.h`: ICU4X 实现

### 使用方
- `modules/skplaintexteditor/src/editor.h/.cpp`: 纯文本编辑器主类
- `modules/skplaintexteditor/src/shape.h/.cpp`: 文本整形工具

### 相关标准
- Unicode UAX #29: Unicode Text Segmentation(单词边界算法标准)
