---
title: '文本属性 API（Text Properties API）'
linkTitle: '文本属性 API（Text Properties API）'
---

各种（国际化正确的）文本处理需要了解 Unicode 字符的*属性*。例如，字符串中的单词边界在哪里（用于换行），哪些需要从右到左或从左到右排列？

我们提议一个批量调用来**表征（characterize）**字符串中的码位。该方法将返回一个 32 位无符号长整数的位字段数组，包含所有选项的结果。

## 功能需求

衡量 API 价值/完整性的一个标准如下：

*对于需要以下功能的复杂应用或框架（例如 Flutter 或 Lottie）……
- 文本塑形（text shaping）
- 换行（line breaking）
- 单词和字素边界（word and grapheme boundaries）

当然，此 API 可以包含**超出**这些用例严格所需的内容，但重要的是它至少包含**足够**的功能，使它们无需通过包含 ICU（或其等效物）的副本来增加其（WASM）下载大小即可运行。

## 人机工程学

除了上述功能需求外，API 形态的另一个驱动因素是效率，尤其是被 **WASM** 客户端调用时。每次 JS <--> WASM 调用都有实际开销，比 JS 和浏览器之间的等效序列开销更大。
- 最小化一个文本块所需的调用次数
- 使用同构数组而非对象序列

鉴于此，建议实现使用 **Uint32Array** 类型化数组缓冲区作为结果。

```WebIDL
//  Bulk call to characterize the code-points in a string.
//  This can return a number of different properties per code-point, so to maximize performance,
//  it will only compute the requested properties requested (see optional boolean request fields).
//
interface TextProperties {
    const unsigned long BidiLevelMask   = 31,       // 0..31 bidi level

    const unsigned long GraphemeBreak   = 1 << 5,
    const unsigned long IntraWordBreak  = 1 << 6,
    const unsigned long WordBreak       = 1 << 7,
    const unsigned long SoftLineBreak   = 1 << 8,
    const unsigned long HardLineBreak   = 1 << 9,

    const unsigned long IsControl       = 1 << 10,
    const unsigned long IsSpace         = 1 << 11,
    const unsigned long IsWhiteSpace    = 1 << 12,

    attribute boolean bidiLevel?;
    attribute boolean graphemeBreak?;
    attribute boolean wordBreak?;       // returns Word and IntraWord break properties
    attribute boolean lineBreak?;       // returns Soft and Hard linebreak properties

    attribute boolean isControl?;
    attribute boolean isSpace?;
    attribute boolean isWhiteSpace?;

    // Returns an array the same length as the input string. Each returned value contains the
    // bitfield results for the corresponding code-point in the string. For surrogate pairs
    // in the input, the results will be in the first output value, and the 2nd output value
    // will be zero.
    //
    // Bitfields that are currently unused, or which correspond to an Option attribute that
    // was not requested, will be set to zero.
    //
    sequence<unsigned long> characterize(DOMString inputString,
                                         DOMString bcp47?);
}
```

## 示例

```js
const properties = {
    isWhiteSpace: true,
    lineBreak: true,
};

const text = "Because I could not stop for Death\nHe kindly stopped for me";

const results = properties.characterize(text);

// expected results

results[7,9,15,19,24,28,37,44,52,65] --> IsWhiteSpace | SoftLineBreak
results[34] --> HardLineBreak
```

## 相关内容

一些用于表征 Unicode 的功能已经存在，要么作为 EcmaScript 的一部分，要么作为 Web API。参见 [intl segmenter](https://github.com/tc39/proposal-intl-segmenter)。本提案承认这些现有方案，但建议功能上的任何潜在重叠是可以接受的，因为在 [人机工程学](#ergonomics) 部分阐述了设计约束。

类似于 canvas2d 和 webgl 之间的对比，本提案旨在提供非常高效的、底层的 Unicode 属性访问，特别针对复杂的（可能是从原生移植到 wasm 的）框架和应用。它无意取代现有设施（即 Segmenter），而是为高性能客户端提供一种更合适的替代接口。

我们还提议了一个专门针对[文本塑形（Text Shaping）](/docs/dev/design/text_overview)的更高级接口。

## 贡献者：
 [mikerreed](https://github.com/mikerreed),
