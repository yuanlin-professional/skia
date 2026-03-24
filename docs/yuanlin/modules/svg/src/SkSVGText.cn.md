# SkSVGText - SVG 文本渲染

> 源文件: [`modules/svg/src/SkSVGText.cpp`](../../../modules/svg/src/SkSVGText.cpp)

## 概述

SkSVGText 实现了 SVG 文本元素（`<text>`、`<tspan>`、`<textPath>`）的渲染逻辑。它处理字体解析、文本整形（通过 SkShaper）、字符位置属性（x, y, dx, dy, rotate）的级联解析、文本对齐（text-anchor）以及沿路径排列文本等功能。

该模块是 SVG 文本排版的核心实现，遵循 SVG 1.1 文本布局规范。

## 架构位置

位于 SVG 模块的内部实现层：

- **调用者**: SkSVGDOM 渲染流水线
- **核心依赖**: SkSVGTextContext（文本上下文/整形管理）、SkSVGRenderContext（渲染上下文）
- **整形引擎**: SkShaper（可选 HarfBuzz + ICU 后端）

## 主要类与结构体

### `ResolveFont` 函数
从 SVG 渲染上下文中解析字体，处理字体族、粗细（100-900/normal/bold）、样式（normal/italic/oblique）和大小。使用 `legacyMakeTypeface` 创建字体。

### `SkSVGTextContext::ScopedPosResolver` 类（在 SkSVGTextPriv.h 中定义）
位置属性的级联解析器。SVG 文本的 x/y/dx/dy/rotate 属性可以在任意层级指定，并按层级关系级联。

### `SkSVGTextContext::ShapeBuffer` 类
形状缓冲区，积累 UTF-8 字符和对应的位置调整，直到需要触发整形。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ResolveFont(ctx)` | 从渲染上下文解析字体 |
| `ResolveLengths(lctx, lengths, type)` | 批量解析长度数组 |
| `ComputeAlignmentFactor(pctx)` | 计算文本对齐因子（start=0, middle=-0.5, end=-1） |

## 内部实现细节

### 字体解析流程
1. 从表现属性提取字体族名、粗细、样式
2. 将 SVG 粗细/样式映射到 SkFontStyle
3. 使用 SkFontMgr 查找匹配的字体
4. 配置抗锯齿、亚像素、线性度量等字体选项

### 位置属性级联（ScopedPosResolver）
SVG 文本位置属性的解析规则：
- x/y/dx/dy: 按字符索引查找，如果本地没有值则查询父级
- rotate: 非累积，最近祖先的显式值优先；无显式值时使用最后指定的值（隐式旋转）
- 一旦某个索引不再产生任何位置数据，缓存该索引以加速后续查找

### 文本整形
`shapePendingBuffer` 使用 SkShaper 进行文本整形：
1. 优先使用完整的 HarfBuzz + ICU 整形（BiDi、Script、Language 迭代器）
2. 如果回调失败，退回到简单的 Trivial 整形
3. 整形结果通过 RunHandler 回调收集

### ShapeBuffer
逐字符追加 UTF-8 编码和累积位置调整。位置调整是累积的（每个字符的调整包含所有前序字符的调整之和），简化了最终定位计算。

### 文本对齐
通过 `ComputeAlignmentFactor` 计算对齐因子，在文本块刷新时应用到整个块的水平偏移：
- start: 0（左对齐）
- middle: -0.5（居中）
- end: -1（右对齐）

## 依赖关系

- `modules/svg/src/SkSVGTextPriv.h` - SkSVGTextContext 和内部类
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `modules/svg/include/SkSVGText.h` - 文本节点声明
- `modules/skshaper/include/SkShaper.h` - 文本整形引擎
- `include/core/SkFont.h` - 字体
- `include/core/SkTextBlob.h` - 文本块

## 设计模式与设计决策

### 作用域位置解析器
ScopedPosResolver 使用 RAII 模式自动管理父子关系链，作用域退出时自动恢复父级解析器。

### 渐进式整形
ShapeBuffer 积累字符直到需要整形时才触发，允许跨 tspan 元素的连续文本作为整体整形。

### 双重整形后端
优先使用高级整形（HarfBuzz/ICU），失败时退回简单整形，确保在不同构建配置下都能工作。

## 性能考量

- ScopedPosResolver 使用 `fLastPosIndex` 缓存优化，避免对无位置数据的高索引进行无效查找
- ShapeBuffer 使用 STArray（栈上 128 字符）减少小文本的堆分配
- 字体解析缓存在渲染上下文中，避免每个文本片段重复查找

## 相关文件

- `modules/svg/src/SkSVGTextPriv.h` - SkSVGTextContext 完整定义
- `modules/svg/include/SkSVGText.h` - 文本节点类声明
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `modules/skshaper/include/SkShaper.h` - 文本整形接口
