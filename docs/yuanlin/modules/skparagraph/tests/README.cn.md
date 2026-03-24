# skparagraph/tests - 段落排版单元测试

## 概述

`tests/` 目录包含 skparagraph 模块的完整单元测试套件。`SkParagraphTest.cpp` 是该模块最重要的测试文件,覆盖了段落排版引擎的各个方面:从基本的文本布局到复杂的双向文本处理,从样式应用到查询 API 的正确性验证。

此目录还包含 `SkShaperJSONWriter`,这是一个测试辅助工具,可将文本整形结果序列化为 JSON 格式,便于调试和回归测试。

## 目录结构

```
tests/
|-- BUILD.bazel                    # Bazel 构建规则
|-- SkParagraphTest.cpp            # 段落核心单元测试(数千行)
|-- SkShaperJSONWriter.cpp         # Shaper JSON 序列化工具
|-- SkShaperJSONWriter.h           # JSON 序列化头文件
|-- SkShaperJSONWriterTest.cpp     # JSON 序列化工具的测试
```

## 关键类与函数

### SkParagraphTest.cpp

这是一个大型测试文件,包含数百个测试用例,覆盖以下领域:

| 测试类别 | 测试内容 |
|----------|----------|
| 基础排版 | 简单文本的 layout() 和尺寸验证 |
| 多行排版 | 换行、最大行数限制 |
| 文本对齐 | kLeft, kRight, kCenter, kJustify |
| 双向文本 | LTR/RTL 混合、BiDi 嵌入级别 |
| 文本样式 | 字体大小、粗细、颜色、装饰 |
| 字体回退 | 缺失字形的回退机制 |
| 省略号 | 单行/多行的省略号截断 |
| 占位符 | 行内占位符的对齐和布局 |
| 选区查询 | getRectsForRange 的矩形验证 |
| 命中测试 | getGlyphPositionAtCoordinate 的位置验证 |
| 词边界 | getWordBoundary 的边界检测 |
| 行度量 | getLineMetrics, getLineMetricsAt |
| 字形查询 | getGlyphClusterAt, getClosestGlyphClusterAt |
| 字体查询 | getFontAt, getFonts |
| 支柱样式 | StrutStyle 的行高控制 |
| 间距 | letterSpacing, wordSpacing |
| 阴影 | TextShadow 效果 |
| 动态更新 | updateTextAlign, updateFontSize |
| Unicode | Emoji、CJK 文字、组合字符 |
| 访问者 | visit(), extendedVisit() |
| 缓存 | ParagraphCache 的命中和失效 |

### SkShaperJSONWriter

```cpp
class SkShaperJSONWriter : public SkShaper::RunHandler {
    // 将整形结果序列化为 JSON
    // 记录每个 Run 的字体、字形、位置等信息
    // 用于整形结果的调试和回归测试
};
```

### 典型测试结构

```cpp
DEF_TEST(SkParagraph_SimpleText, reporter) {
    // 1. 创建 TestFontCollection
    auto fontCollection = sk_make_sp<TestFontCollection>(...);

    // 2. 配置样式
    ParagraphStyle paragraphStyle;
    TextStyle textStyle;
    textStyle.setFontSize(50);

    // 3. 构建段落
    auto builder = ParagraphBuilder::make(paragraphStyle, fontCollection, unicode);
    builder->pushStyle(textStyle);
    builder->addText("Hello World");
    auto paragraph = builder->Build();

    // 4. 排版
    paragraph->layout(500);

    // 5. 断言验证
    REPORTER_ASSERT(reporter, paragraph->getHeight() > 0);
    REPORTER_ASSERT(reporter, paragraph->lineNumber() == 1);
}
```

## 依赖关系

```
tests/
  |-- modules/skparagraph/include/ (完整段落API)
  |-- modules/skparagraph/utils/ (TestFontCollection)
  |-- Skia 测试框架 (tests/Test.h, DEF_TEST宏)
  |-- modules/skshaper/ (SkShaper, 用于SkShaperJSONWriter)
  |-- modules/skunicode/ (Unicode支持)
  |-- resources/ (测试字体文件)
```

## 设计模式分析

### 测试夹具模式 (Test Fixture)
多数测试共享相同的初始化模式:创建 `TestFontCollection` -> 构建段落 -> 排版 -> 断言。`TestFontCollection` 提供了一组已知的测试字体,确保测试结果的确定性。

### 数据驱动测试
部分测试使用不同的参数组合运行相同的测试逻辑,验证 API 在各种输入条件下的正确性。

### 回归测试
许多测试用例源于实际发现的 bug,测试名称或注释中包含 bug 跟踪信息,确保问题不会再次出现。

## 数据流

```
测试框架 (DM)
  |
  +-- 发现并运行 SkParagraph_* 测试
  |
  +-- 每个测试:
  |     |-- 创建 TestFontCollection (加载测试字体)
  |     |-- 创建 ParagraphBuilder
  |     |-- 添加文本和样式
  |     |-- Build() -> Paragraph
  |     |-- layout(width) -> 排版
  |     |-- 调用查询 API 或 paint()
  |     |-- REPORTER_ASSERT() 验证结果
  |
  +-- 汇总测试结果 (通过/失败/跳过)
```

## 相关文档与参考

- **被测代码**: `modules/skparagraph/src/` - 核心实现
- **测试工具**: `modules/skparagraph/utils/TestFontCollection.h` - 测试字体集合
- **运行方式**: `dm --match SkParagraph` 运行所有段落测试
- **GM 测试**: `modules/skparagraph/gm/` - 视觉回归测试
- **Skia 测试框架**: `tests/Test.h` - DEF_TEST 和 REPORTER_ASSERT 宏
