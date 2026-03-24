# bridge - Unicode 实现比较桥接层

> 源文件:
> - [tools/unicode_comparison/cpp/bridge.h](../../../../tools/unicode_comparison/cpp/bridge.h)
> - [tools/unicode_comparison/cpp/bridge.cpp](../../../../tools/unicode_comparison/cpp/bridge.cpp)

## 概述

bridge 提供了一个 C 语言接口层，用于在不同 Unicode 实现（ICU、ICU4X、libgrapheme）之间进行性能和功能比较。它封装了 SkUnicode 的核心功能（大小写转换、文本属性计算、句子/单词分割），通过 `extern "C"` 接口暴露给其他语言（如用于 Web 前端的 WASM）。

## 架构位置

位于 `tools/unicode_comparison/cpp/` 目录下，属于 Unicode 实现评估工具。桥接 Skia 的 SkUnicode 模块与外部比较测试框架。

## 主要类与结构体

无类定义，使用全局静态变量管理状态。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `init_skunicode_impl(impl)` | 初始化 Unicode 实现（"icu"/"icu4x"/"libgrapheme"） |
| `cleanup_unicode_impl()` | 清理 Unicode 实例 |
| `toUpper(str)` | 将字符串转换为大写 |
| `print(str)` | 打印 SkString |
| `perf_compute_codeunit_flags(text)` | 计算代码单元标志并返回耗时（纳秒） |
| `getFlags(index)` | 获取指定索引的代码单元标志 |
| `getSentences(text, length)` | 获取文本中的句子边界位置 |
| `trimSentence(text, sentence, wordLimit)` | 在单词限制内截断句子 |

## 内部实现细节

- **全局状态**：使用 `gUnicode`（sk_sp）、`gCodeUnitFlags`、`gSentences`、`gWords` 全局变量。
- **性能测量**：`perf_compute_codeunit_flags` 使用 `SkTime::GetNSecs` 精确计时。
- **工厂选择**：通过字符串比较选择 `SkUnicode::ICU::Make()`、`ICU4X::Make()` 或 `Libgrapheme::Make()`。
- **单词断点标记**：在计算代码单元标志后，额外调用 `getUtf8Words` 并将单词断点合并到标志中。

## 依赖关系

- **SkUnicode 模块**：SkUnicode 接口及其 ICU/ICU4X/libgrapheme 实现
- **Skia 基础**：SkString、SkTime、SkBitmaskEnum

## 设计模式与设计决策

- **C ABI**：使用 `extern "C"` 确保跨语言可调用。
- **全局单例状态**：简化 FFI 接口，不需要传递上下文对象。

## 性能考量

- `perf_compute_codeunit_flags` 专为性能基准测试设计，返回纳秒级精确计时。
- 全局变量避免重复分配，但不支持多线程。

## 相关文件

- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
