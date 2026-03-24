# Unicode - Skottie 严格换行 Unicode 包装

> 源文件: `modules/skottie/src/text/Unicode.cpp`

## 概述

该文件实现了两个 Unicode 相关的包装类，用于为 Skottie 文本排版提供更严格的换行语义。核心目标是确保文本换行时不会在单词中间断开。`StrictLinebreakUnicode` 通过将行断迭代器与词断迭代器取交集来实现这一目标，而 `IntersectingBreakIterator` 则是实现迭代器交集运算的通用工具。

## 架构位置

该文件位于 Skottie 文本子系统中，作为 SkUnicode 接口的装饰器层，介入文本塑形引擎的换行决策过程。

```
TextShaper (文本排版)
  |
  +-> SkShaper (塑形引擎)
        |
        +-> SkShapers::Factory::makeBidiRunIterator()
        +-> makeBreakIterator() [通过 SkUnicode]
              |
              +-> StrictLinebreakUnicode (装饰器)
                    |
                    +-> IntersectingBreakIterator
                    |     +-> 行断迭代器 (BreakType::kLines)
                    |     +-> 词断迭代器 (BreakType::kWords)
                    |
                    +-> 原始 SkUnicode (代理其他方法)
```

## 主要类与结构体

### IntersectingBreakIterator
- 继承自 `SkBreakIterator`
- 执行两个断点迭代器的交集运算：仅返回两者都同意的断点位置
- 持有两个 `std::unique_ptr<SkBreakIterator>` 成员 `fA` 和 `fB`
- `fCurrent` 跟踪当前位置，`fDone` 标记是否完成
- `next()` 方法交替推进较小位置的迭代器，直到两者位置相等或某一方结束
- `status()` 方法标记为 `SkUNREACHABLE`（该功能不被使用）

### StrictLinebreakUnicode
- 继承自 `SkUnicode`，装饰器模式包装原始 Unicode 实例
- 持有 `sk_sp<SkUnicode> fUnicode` 成员
- 重写 `makeBreakIterator(locale, breakType)` 方法：
  - 对非行断请求直接透传
  - 对行断请求（`BreakType::kLines`）创建复合迭代器
- 所有其他 SkUnicode 方法直接代理到原始实例

## 公共 API 函数

### `skottie::MakeStrictLinebreakUnicode`
```cpp
sk_sp<SkUnicode> SK_API MakeStrictLinebreakUnicode(sk_sp<SkUnicode> uc);
```
- 工厂函数，创建 `StrictLinebreakUnicode` 包装
- 输入为 nullptr 时返回 nullptr（空安全）
- 返回增强了严格换行语义的 SkUnicode 实例

### `skottie::MakeIntersectingBreakIteratorForTesting`
```cpp
std::unique_ptr<SkBreakIterator> MakeIntersectingBreakIteratorForTesting(
    std::unique_ptr<SkBreakIterator> a, std::unique_ptr<SkBreakIterator> b);
```
- 测试用工厂函数，直接创建 IntersectingBreakIterator
- 暴露内部实现以支持单元测试

## 内部实现细节

### 交集迭代算法（IntersectingBreakIterator::next）
```
while (!fDone):
    if pos_a < pos_b:
        pos_a = fA->next()   // 推进较小的迭代器
    else:
        pos_b = fB->next()   // 推进较小的迭代器
    if pos_a == pos_b:
        break                // 找到交集点
```
- 两个迭代器保持同步推进，始终推进位置较小的那个
- 当两者位置相等时找到有效的交集断点
- 当任一迭代器结束时标记 `fDone = true`
- 结束时返回两个位置中较小的（负数表示结束状态）

### 代理方法覆盖
StrictLinebreakUnicode 代理了 SkUnicode 的所有公共方法，包括：
- 字符分类：`isControl`、`isWhitespace`、`isSpace`、`isTabulation`、`isHardBreak`
- Emoji 检测：`isEmoji`、`isEmojiComponent`、`isEmojiModifierBase`、`isEmojiModifier`
- 文本处理：`toUpper`、`isIdeographic`、`isRegionalIndicator`
- 迭代器创建：`makeBidiIterator`（两个重载）、`makeBreakIterator`（无 locale 版本直接透传）
- 分析方法：`getBidiRegions`、`getWords`、`getUtf8Words`、`getSentences`、`computeCodeUnitFlags`
- 排序方法：`reorderVisual`

### 断行语义增强
- 标准 Unicode 行断规则可能允许在某些非空白字符处断行
- 通过与词断迭代器取交集，确保断行仅发生在词边界
- 词断迭代器创建失败时回退到原始行断迭代器

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `SkUnicode.h` | SkUnicode / SkBreakIterator 基类 |
| `TextShaper.h` | 公共 API 声明 |
| `SkTypes.h` | SkUNREACHABLE 宏 |
| `SkAssert.h` | SkASSERT / SkAssertResult |

## 设计模式与设计决策

- **装饰器模式**：`StrictLinebreakUnicode` 包装原始 `SkUnicode` 实例，仅修改行断迭代器的行为，其余功能透传。这是经典的装饰器模式。
- **组合迭代器**：`IntersectingBreakIterator` 将两个迭代器组合成一个新的迭代器，实现了迭代器的代数运算（交集）。
- **优雅降级**：词断迭代器创建失败时回退到标准行断行为，确保不会因增强功能导致排版失败。
- **空安全工厂**：`MakeStrictLinebreakUnicode` 对 nullptr 输入返回 nullptr，简化调用方的空值处理。
- **测试友好**：通过 `MakeIntersectingBreakIteratorForTesting` 暴露内部类的创建能力，支持独立测试。

## 性能考量

- 交集迭代的时间复杂度为 O(N + M)，其中 N 和 M 分别是两个迭代器的断点数量。
- 每次 `next()` 调用可能触发两个底层迭代器的多次推进，但断点通常稀疏分布，实际开销不大。
- 代理方法为直接函数调用转发，无额外开销（虚函数调用除外）。
- `StrictLinebreakUnicode` 仅在请求行断迭代器时创建复合对象，其他断迭代器零额外开销。
- `fUnicode` 使用 `sk_sp` 引用计数，避免不必要的拷贝。

### 换行语义的差异说明

标准 Unicode 换行算法（UAX #14）定义了多种换行机会，包括：
- 空白字符后的断点
- 标点符号前后的断点
- CJK 字符间的断点
- 连字符后的断点

这些规则在某些情况下可能导致词中断行（例如在连字符处或某些语言的特殊规则下）。Skottie 的严格换行模式通过额外约束将断行限制在词边界，更接近 After Effects 的文本换行行为。

### setText 方法的同步语义

`IntersectingBreakIterator::setText` 方法同时将文本设置到两个底层迭代器，并重置内部状态（`fDone = false`, `fCurrent = 0`）。两个 `setText` 调用必须都成功才返回 `true`，确保两个迭代器处于一致的初始状态。

### IntersectingBreakIterator 的正确性保证

交集迭代器的正确性基于以下不变量：
1. `first()` 时两个迭代器必须返回相同的初始位置（通常为 0）
2. 两个迭代器的断点序列都是单调递增的
3. 当任一迭代器完成时，交集迭代也完成
4. `current()` 始终返回最近一次 `next()` 或 `first()` 的结果

`status()` 方法标记为 `SkUNREACHABLE`，表明在 Skottie 的使用场景中该方法不应被调用。行断/词断迭代器的 status 信息（如 hard break vs soft break）在交集操作中没有明确的语义。

## 相关文件

- `modules/skottie/include/TextShaper.h` - 公共 API 声明
- `modules/skottie/src/text/TextShaper.cpp` - 文本排版引擎（使用者）
- `modules/skunicode/include/SkUnicode.h` - SkUnicode 基类定义
- `modules/skshaper/include/SkShaper.h` - SkShaper 塑形引擎（最终消费者）
