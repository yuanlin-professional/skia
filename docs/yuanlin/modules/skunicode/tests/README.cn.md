# skunicode/tests - Unicode 支持单元测试

## 概述

`tests/` 目录包含 skunicode 模块的单元测试。`SkUnicodeTest.cpp` 验证各个 Unicode 后端的功能正确性,确保不同后端(ICU、ICU4X、libgrapheme、Client、Bidi)在相同输入下产生一致的结果,并且所有 Unicode 分析功能(字符分类、断行、BiDi、词边界等)符合 Unicode 规范。

由于 skunicode 支持多个后端,测试的一个重要目标是验证后端间的一致性。相同的文本输入在不同后端下应产生相同(或在规范允许范围内等价)的分析结果。

## 目录结构

```
tests/
|-- BUILD.bazel              # Bazel 构建规则
|-- SkUnicodeTest.cpp        # Unicode 功能单元测试
```

## 关键类与函数

### SkUnicodeTest.cpp

| 测试类别 | 验证内容 |
|----------|----------|
| 字符分类 | isControl, isWhitespace, isEmoji, isIdeographic 等 |
| 行断点 | computeCodeUnitFlags 中的 kSoftLineBreakBefore, kHardLineBreakBefore |
| 字素簇 | computeCodeUnitFlags 中的 kGraphemeStart |
| 词边界 | getWords, getUtf8Words 的边界位置 |
| 句子边界 | getSentences 的句子分割 |
| BiDi 分析 | getBidiRegions 的区域和级别 |
| 大小写转换 | toUpper 的正确性(locale 相关) |
| 编码转换 | convertUtf8ToUtf16, convertUtf16ToUtf8 |
| Emoji 处理 | Emoji 序列、组合 Emoji、肤色修饰等 |
| CJK 文本 | 表意文字标记、CJK 断行规则 |
| 后端一致性 | 不同后端对同一输入的结果比对 |

### 典型测试结构

```cpp
DEF_TEST(SkUnicode_CharacterProperties, reporter) {
    auto unicode = SkUnicodes::ICU::Make();
    if (!unicode) return;

    // 测试空格分类
    REPORTER_ASSERT(reporter, unicode->isWhitespace(0x0020));  // SPACE
    REPORTER_ASSERT(reporter, unicode->isWhitespace(0x00A0));  // NBSP
    REPORTER_ASSERT(reporter, !unicode->isWhitespace(0x0041)); // 'A'

    // 测试 Emoji
    REPORTER_ASSERT(reporter, unicode->isEmoji(0x1F600));      // 笑脸
    REPORTER_ASSERT(reporter, !unicode->isEmoji(0x0041));      // 'A'

    // 测试表意文字
    REPORTER_ASSERT(reporter, unicode->isIdeographic(0x4E00)); // CJK '一'
    REPORTER_ASSERT(reporter, !unicode->isIdeographic(0x0041));// 'A'
}

DEF_TEST(SkUnicode_LineBreaking, reporter) {
    auto unicode = SkUnicodes::ICU::Make();
    if (!unicode) return;

    const char* text = "Hello World\nNew line";
    skia_private::TArray<SkUnicode::CodeUnitFlags, true> flags;
    unicode->computeCodeUnitFlags(text, strlen(text), false, &flags);

    // 验证硬换行点
    REPORTER_ASSERT(reporter,
        SkUnicode::hasHardLineBreakFlag(flags[11])); // '\n' 位置

    // 验证软换行点(空格后)
    REPORTER_ASSERT(reporter,
        SkUnicode::hasSoftLineBreakFlag(flags[6])); // "World" 前
}
```

### 多后端测试

```cpp
DEF_TEST(SkUnicode_BackendConsistency, reporter) {
    // 创建所有可用后端
    auto icu = SkUnicodes::ICU::Make();
    auto icu4x = SkUnicodes::ICU4X::Make();
    auto libg = SkUnicodes::Libgrapheme::Make();

    const char* text = "Hello, World! 你好世界";

    // 比较各后端的 computeCodeUnitFlags 结果
    // 验证关键断点位置一致
}
```

## 依赖关系

```
tests/
  |-- modules/skunicode/include/ (SkUnicode 等接口)
  |-- Skia 测试框架 (tests/Test.h)
  |-- 各 Unicode 后端 (条件编译)
  |   |-- SkUnicodes::ICU (当 SK_UNICODE_ICU_IMPLEMENTATION 时)
  |   |-- SkUnicodes::ICU4X (当 SK_UNICODE_ICU4X_IMPLEMENTATION 时)
  |   |-- SkUnicodes::Libgrapheme (当 SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION 时)
```

## 设计模式分析

### 条件编译测试
测试使用条件编译适配可用的 Unicode 后端:
```cpp
#if defined(SK_UNICODE_ICU_IMPLEMENTATION)
    auto unicode = SkUnicodes::ICU::Make();
#elif defined(SK_UNICODE_ICU4X_IMPLEMENTATION)
    auto unicode = SkUnicodes::ICU4X::Make();
#endif
```

### 参数化测试
部分测试对多种文本输入(Latin、CJK、Arabic、Emoji、混合文本)运行相同的验证逻辑,确保 Unicode 分析在各种真实文本上正确工作。

### 边界条件测试
测试覆盖了多种边界条件:
- 空字符串
- 单字符字符串
- 纯 ASCII 文本
- 多字节 UTF-8 序列
- 代理对(surrogate pairs)
- 组合字符和修饰符序列
- 双向文本混合

## 数据流

```
测试框架
  |
  +-- 创建 Unicode 后端: SkUnicodes::XXX::Make()
  |
  +-- 字符属性测试:
  |   unicode->isXxx(codepoint)
  |   -> REPORTER_ASSERT(expected)
  |
  +-- 文本分析测试:
  |   unicode->computeCodeUnitFlags(text, flags[])
  |   -> 检查特定位置的标志位
  |   -> REPORTER_ASSERT(flags[pos] & expected_flag)
  |
  +-- BiDi 测试:
  |   unicode->getBidiRegions(text, dir, regions[])
  |   -> 验证区域数量、范围、级别
  |
  +-- 一致性测试:
      比较不同后端的输出结果
      -> 断言关键位置一致
```

## 相关文档与参考

- **被测代码**: `modules/skunicode/src/` - Unicode 后端实现
- **运行方式**: `dm --match SkUnicode` 运行所有 Unicode 测试
- **Unicode 一致性测试**: Unicode 组织提供的标准一致性测试数据
- **UAX #29 测试数据**: 官方字素簇/词/句子分割测试用例
- **UAX #14 测试数据**: 官方行断点测试用例
- **UAX #9 测试数据**: 官方 BiDi 测试用例
