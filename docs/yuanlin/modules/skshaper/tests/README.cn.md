# skshaper/tests - 文本整形单元测试

## 概述

`tests/` 目录包含 skshaper 模块的单元测试。`ShaperTest.cpp` 验证文本整形引擎的核心功能,确保各种整形后端(HarfBuzz、CoreText、Primitive)能够正确地将 Unicode 文本转换为字形序列。

测试覆盖了整形器的基本功能,包括简单文本整形、字体回退、BiDi 双向文本处理、复杂脚本(如阿拉伯文、天城文)的连字和上下文替换,以及 RunHandler 回调的正确性。

文本整形是文本渲染管线中最关键的环节之一,它决定了最终文本渲染的视觉正确性。整形测试确保从字符到字形的映射在各种语言和脚本下都是正确的。

## 架构图

```
+-------------------------------------------+
|           Skia 测试框架 (DM)               |
|  DEF_TEST 宏 | REPORTER_ASSERT            |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|         ShaperTest.cpp (测试用例)          |
|  创建整形器 -> 整形 -> 验证结果            |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|           SkShaper 后端                    |
|  HarfBuzz | CoreText | Primitive          |
+-------------------------------------------+
```

## 目录结构

```
tests/
|-- BUILD.bazel          # Bazel 构建规则
|-- ShaperTest.cpp       # 文本整形单元测试
```

## 关键类与函数

### ShaperTest.cpp

| 测试类别 | 验证内容 |
|----------|----------|
| 基础整形 | 简单 Latin 文本的字形输出和位置 |
| 字体回退 | 缺失字形时自动使用回退字体 |
| BiDi 文本 | LTR/RTL 混合文本的正确排序 |
| 脚本分段 | 不同脚本(Latin/CJK/Arabic)的正确分段和整形 |
| 连字 | OpenType 连字(如 "fi" -> 单字形)的正确处理 |
| 空文本 | 空字符串输入的安全处理(不崩溃) |
| 换行 | 宽度约束下的正确换行行为 |
| 多后端 | 不同整形后端产生一致的基本行为 |
| RunHandler 回调 | 回调顺序和数据正确性 |
| 特性(Features) | OpenType 特性的正确应用 |

### 典型测试模式

```cpp
DEF_TEST(Shaper_BasicTest, reporter) {
    // 创建最佳可用整形器
    auto shaper = SkShaper::Make();
    if (!shaper) return;  // 优雅处理无可用后端

    // 配置字体
    SkFont font(SkTypeface::MakeDefault(), 12);

    // 使用 SkTextBlobBuilderRunHandler 收集结果
    SkTextBlobBuilderRunHandler handler("Hello", {0, 0});
    shaper->shape("Hello", 5, font, true /*LTR*/, 1000 /*宽度*/, &handler);

    // 验证结果
    auto blob = handler.makeBlob();
    REPORTER_ASSERT(reporter, blob != nullptr);
    // 进一步验证字形数量、位置等
}
```

### 自定义 RunHandler 测试

```cpp
// 部分测试使用自定义 RunHandler 精确验证整形过程:
class TestRunHandler : public SkShaper::RunHandler {
    // 记录每个回调的调用信息
    // 验证 beginLine/commitLine 的配对
    // 验证 runInfo 中的字形数量和 UTF-8 范围
    // 验证 runBuffer 中的字形 ID 和位置数据
};
```

## 依赖关系

```
tests/
  |-- modules/skshaper/include/ (SkShaper, RunHandler等)
  |-- Skia 测试框架 (tests/Test.h)
  |-- SkFont, SkTypeface, SkFontMgr
  |-- SkTextBlob, SkTextBlobBuilder
  |-- modules/skunicode/ (Unicode支持, 可选)
  |-- resources/ (测试字体文件)
```

## 设计模式分析

测试采用 Skia 的标准 `DEF_TEST` 宏框架:
- 每个测试函数独立运行,互不影响
- 使用 `REPORTER_ASSERT` 进行断言
- 整形结果通过 `SkTextBlobBuilderRunHandler` 或自定义 RunHandler 收集

### 平台感知测试
部分测试使用条件编译,在特定平台上测试特定后端:
- HarfBuzz 测试仅在 `SK_SHAPER_HARFBUZZ_AVAILABLE` 时编译
- CoreText 测试仅在 `SK_SHAPER_CORETEXT_AVAILABLE` 时编译
- Primitive 测试始终可用(无外部依赖)

### 后端独立验证
每种后端都有独立的测试用例,验证其特定行为:
- HarfBuzz: 连字、字距调整、复杂脚本整形
- CoreText: Apple 平台特定的排版行为
- Primitive: 简单映射的基本正确性

## 数据流

```
测试框架 (DM)
  |
  +-- 枚举所有 Shaper_* 测试
  |
  +-- 每个测试:
  |     |-- 创建整形器: SkShaper::Make() 或特定后端
  |     |-- 创建字体: SkFont + SkTypeface
  |     |-- 创建 RunHandler (Blob Builder 或自定义)
  |     |
  |     +-- shaper->shape(text, font, width, handler)
  |     |     |-- handler->beginLine()
  |     |     |-- handler->runInfo(info)
  |     |     |-- handler->commitRunInfo()
  |     |     |-- handler->runBuffer(info) -> 填充字形数据
  |     |     |-- handler->commitRunBuffer(info)
  |     |     |-- handler->commitLine()
  |     |
  |     +-- 验证: blob 非空, 字形数量正确, 位置合理
  |
  +-- 汇总测试结果
```

## 相关文档与参考

- **被测代码**: `modules/skshaper/src/` - 整形器实现
- **运行方式**: `dm --match Shaper` 运行所有整形测试
- **skparagraph 测试**: `modules/skparagraph/tests/` - 段落级整形测试
- **SkTextBlobBuilderRunHandler**: `modules/skshaper/include/SkShaper.h` - 便捷结果收集器
