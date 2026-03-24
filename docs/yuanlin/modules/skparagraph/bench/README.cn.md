# skparagraph/bench - 段落排版性能基准测试

## 概述

`bench/` 目录包含 skparagraph 模块的性能基准测试代码。这些测试用于度量段落排版引擎在不同场景下的性能表现,帮助开发者发现和优化性能瓶颈。

基准测试覆盖了段落排版的核心操作 --- `layout()` 方法的执行时间,这是文本排版中最关键的性能指标。测试场景包括短文本和长文本、不同样式配置以及 Flutter 典型使用模式。

段落排版的性能对于用户体验至关重要,特别是在文本编辑器、即时通讯应用和新闻阅读器等需要频繁重新排版的场景中。通过持续的基准测试,可以在代码提交时及早发现性能回退问题。

## 架构图

```
+-------------------------------------------+
|           Skia Benchmark 框架              |
|  (nanobench / Benchmark 基类)             |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|         ParagraphBench (测试实现)          |
|  onGetName() | onDraw() | onDelayedSetup()|
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|           skparagraph 排版管线             |
|  ParagraphBuilder -> Build -> layout      |
+-------------------------------------------+
```

## 目录结构

```
bench/
|-- BUILD.bazel          # Bazel 构建规则
|-- ParagraphBench.cpp   # 段落性能基准测试
```

## 关键类与函数

### ParagraphBench.cpp

该文件定义了继承自 Skia 基准测试框架的性能测试类:

| 测试场景 | 说明 |
|----------|------|
| 短文本排版 | 测试少量文字的排版性能(单行场景) |
| 长文本排版 | 测试大段文本的排版性能(多行换行场景) |
| 多样式排版 | 测试复杂样式混合(粗体/斜体/不同大小)的排版性能 |
| 缓存命中 | 测试 ParagraphCache 的性能收益(重复排版场景) |
| 字体回退 | 测试包含多种脚本文字时字体回退的性能开销 |

### 核心测量目标

```
layout() 耗时分解:
  |-- computeCodeUnitProperties()  (Unicode属性分析 -- SkUnicode调用)
  |-- shapeTextIntoEndlessLine()   (文本整形 -- 通常最耗时, 调用SkShaper/HarfBuzz)
  |-- breakShapedTextIntoLines()   (换行处理 -- 与文本长度和宽度约束相关)
  |-- formatLines()                (格式化对齐 -- 仅两端对齐时有显著开销)
```

### 性能关键路径

文本整形(`shapeTextIntoEndlessLine`)通常占据 `layout()` 总耗时的 60%-80%,因为它涉及:
- 调用 HarfBuzz 进行 OpenType 整形
- 字体回退查找(遍历 SkFontMgr)
- 字形到 Cluster 的映射构建

## 依赖关系

```
bench/
  |-- modules/skparagraph/include/ (Paragraph, ParagraphBuilder, TextStyle等)
  |-- modules/skparagraph/utils/ (TestFontCollection)
  |-- Skia bench 框架 (bench/Benchmark.h)
  |-- modules/skshaper/ (文本整形)
  |-- modules/skunicode/ (Unicode支持)
```

## 设计模式分析

基准测试采用了 Skia 标准的 `Benchmark` 框架模式:
- `onGetName()` 返回测试名称,用于结果过滤和报告
- `onDelayedSetup()` 执行一次性初始化(创建字体集合等)
- `onDraw()` 执行被测代码,框架自动多轮迭代
- 框架自动进行统计分析(平均值、中位数、标准差)

### 测试隔离
每个基准测试创建独立的 `FontCollection`、`ParagraphBuilder` 和 `Paragraph` 对象,确保测试间互不影响。`TestFontCollection` 使用固定的测试字体,消除系统字体差异对性能的影响。

### 冷启动与热启动
测试可以区分"冷启动"(首次排版,无缓存)和"热启动"(重复排版,缓存命中)两种场景,分别度量不同使用模式下的性能。

## 数据流

```
基准测试框架 (nanobench)
  |
  +-- onDelayedSetup():
  |     创建 TestFontCollection
  |     创建 SkUnicode 实例
  |     创建 ParagraphBuilder
  |     pushStyle / addText / Build
  |
  +-- onDraw() 测量循环 (N 次迭代):
  |     |-- paragraph->markDirty()       <-- 清除缓存(如需冷启动)
  |     |-- paragraph->layout(width)     <-- 核心被测操作
  |     |-- (可选) paragraph->paint()
  |
  +-- 输出统计: 平均耗时, 中位数, 标准差, 吞吐量
```

## 相关文档与参考

- **被测代码**: `modules/skparagraph/src/ParagraphImpl.cpp` - `layout()` 实现
- **测试工具**: `modules/skparagraph/utils/TestFontCollection.h` - 测试字体集合
- **Skia 基准框架**: `bench/Benchmark.h` - 基准测试基类
- **运行方式**: 通过 `nanobench` 工具运行,使用 `--match SkParagraph` 过滤
- **性能监控**: Skia 持续性能监控 (perf.skia.org) 跟踪段落排版性能趋势
