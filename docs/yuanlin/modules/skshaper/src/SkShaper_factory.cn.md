# SkShaper_factory.cpp - 原始文本整形器工厂实现

> 源文件: `modules/skshaper/src/SkShaper_factory.cpp`

## 概述

`SkShaper_factory.cpp` 实现了 Skia 文本整形模块的原始（Primitive）工厂类。该文件提供了 `SkShapers::Primitive::Factory()` 函数，返回一个基于最简单文本整形策略的工厂实例。此工厂是整形器工厂层次结构中的基础实现，当 HarfBuzz 或 CoreText 等高级后端不可用时作为兜底方案。

## 架构位置

该文件位于 `modules/skshaper/` 模块中，是 `SkShapers::Factory` 抽象接口的一个具体实现：

- **上层接口**：`SkShapers::Factory`（定义于 `SkShaper_factory.h`）
- **同层实现**：与 HarfBuzz 工厂、CoreText 工厂并列
- **下层依赖**：`SkShapers::Primitive::PrimitiveText()` 创建原始整形器
- **消费者**：需要通过工厂模式创建整形器的上层代码

## 主要类与结构体

### `PrimitiveFactory`（匿名命名空间内）
- 继承自 `SkShapers::Factory`
- 使用 `final` 修饰，禁止进一步继承
- 实现了工厂接口的三个核心虚函数和一个 Unicode 访问器
- 所有创建方法均返回最简（Trivial）实现

## 公共 API 函数

### `SkShapers::Primitive::Factory()`
返回一个 `sk_sp<SkShapers::Factory>` 智能指针，指向 `PrimitiveFactory` 实例。这是该文件唯一暴露的公共 API。

## 内部实现细节

### `PrimitiveFactory::makeShaper(sk_sp<SkFontMgr>)`
忽略传入的 `SkFontMgr` 参数，直接调用 `SkShapers::Primitive::PrimitiveText()` 创建原始文本整形器。原始整形器不执行复杂的字形替换或连字处理。

### `PrimitiveFactory::makeBidiRunIterator(...)`
返回 `TrivialBiDiRunIterator(0, 0)`，忽略所有输入参数。这意味着所有文本被视为单一方向（LTR），不进行双向文本分析。

### `PrimitiveFactory::makeScriptRunIterator(...)`
返回 `TrivialScriptRunIterator(0, 0)`，忽略所有输入参数。不进行脚本检测，所有文本被视为同一脚本。

### `PrimitiveFactory::getUnicode()`
返回 `nullptr`，表示无 Unicode 处理能力可用。

## 依赖关系

- `modules/skshaper/include/SkShaper_factory.h` - 工厂基类定义
- `include/core/SkFontMgr.h` - 字体管理器（仅作 IWYU 保留）
- `modules/skshaper/include/SkShaper.h` - `TrivialBiDiRunIterator` 和 `TrivialScriptRunIterator` 的定义

## 设计模式与设计决策

### 抽象工厂模式
`PrimitiveFactory` 是抽象工厂 `SkShapers::Factory` 的具体实现，遵循抽象工厂模式。客户端代码通过统一的工厂接口创建整形器及其相关迭代器，无需了解具体实现。

### 空对象模式
所有方法返回的都是"空"或"平凡"实现（Trivial 迭代器、nullptr），这是空对象模式的体现。即使没有高级文本处理能力，系统仍然可以正常运行。

### 匿名命名空间封装
`PrimitiveFactory` 定义在匿名命名空间中，确保该实现类对外不可见，仅通过 `Factory()` 函数暴露。

### 引用计数管理
`PrimitiveFactory` 继承自 `SkRefCnt`（通过 `SkShapers::Factory`），使用 `sk_sp` 智能指针管理生命周期。工厂函数通过 `sk_make_sp<PrimitiveFactory>()` 创建实例，确保正确的引用计数初始化。

### IWYU 注释
`#include "include/core/SkFontMgr.h"` 带有 `// IWYU pragma: keep` 注释，表明该头文件虽然在当前文件中没有直接使用其类型定义，但 Include-What-You-Use 工具需要保留它以确保 `sk_sp<SkFontMgr>` 参数类型的完整性。

## 性能考量

- 该工厂创建的所有对象都是轻量级的，没有复杂初始化开销
- `TrivialBiDiRunIterator` 和 `TrivialScriptRunIterator` 以零参数构造，内部状态极为精简，仅包含一个计数器和一个标志位
- 作为兜底方案，此实现牺牲了文本整形质量以换取最小的性能开销和依赖
- `PrimitiveFactory` 本身是无状态的（不持有任何成员变量），因此多次调用 `Factory()` 创建的实例在行为上完全等价
- `makeShaper` 忽略 `SkFontMgr` 参数，不触发任何字体枚举或加载操作
- 整个原始工厂的内存占用极小：仅 `SkRefCnt` 基类的引用计数开销

## 相关文件

- `modules/skshaper/include/SkShaper_factory.h` - 工厂接口定义
- `modules/skshaper/include/SkShaper.h` - SkShaper 核心接口和 Trivial 迭代器定义
- `modules/skshaper/src/SkShaper.cpp` - SkShaper 核心实现
- `modules/skshaper/src/SkShaper_harfbuzz.cpp` - HarfBuzz 工厂实现（高级替代方案）
