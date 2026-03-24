# SkSVGFeMerge

> 源文件: [modules/svg/src/SkSVGFeMerge.cpp](../../../../modules/svg/src/SkSVGFeMerge.cpp)

## 概述

`SkSVGFeMerge` 实现了 SVG `<feMerge>` 滤镜效果，用于将多个滤镜输入按照顺序叠合（compositing）为单一输出。每个输入由子节点 `<feMergeNode>` 指定。该实现将 SVG 的合并操作映射为 Skia 的 `SkImageFilters::Merge` 图像滤镜。

## 架构位置

```
SkSVGNode
  └── SkSVGFe (滤镜效果基类)
        └── SkSVGFeMerge  ← 本文件实现
              └── 子节点: SkSVGFeMergeNode
```

位于 SVG 模块的滤镜效果子系统，在滤镜图构建阶段将 DOM 节点转换为 `SkImageFilter` 对象。

## 主要类与结构体

### SkSVGFeMergeNode
- 代表 `<feMergeNode>` SVG 元素
- 仅有一个 `in` 属性（`SkSVGFeInputType`），指定该节点的输入源
- 通过 `parseAndSetAttribute` 解析 `in` 属性

### SkSVGFeMerge
- 继承自 `SkSVGFe`，对应 SVG `<feMerge>` 元素
- 遍历所有 `SkSVGFeMergeNode` 子节点收集输入滤镜
- 使用 `SkImageFilters::Merge` 合并所有输入

## 公共 API 函数

### `SkSVGFeMergeNode::parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* name, const char* value);
```
解析 `in` 属性，指定滤镜输入源。

### `SkSVGFeMerge::onMakeImageFilter`
```cpp
sk_sp<SkImageFilter> onMakeImageFilter(const SkSVGRenderContext& ctx,
                                       const SkSVGFilterContext& fctx) const;
```
核心方法：遍历所有 `SkSVGFeMergeNode` 子节点，解析各自的输入滤镜，调用 `SkImageFilters::Merge` 合并。

### `SkSVGFeMerge::getInputs`
```cpp
std::vector<SkSVGFeInputType> getInputs() const;
```
收集所有子节点的输入类型，用于滤镜依赖分析。

## 内部实现细节

- 使用 `skia_private::STArray<8, sk_sp<SkImageFilter>>` 作为栈上预分配的小数组优化，预期多数场景下合并节点不超过 8 个。
- `forEachChild<SkSVGFeMergeNode>` 模板方法仅遍历特定类型的子节点，忽略其他类型。
- 颜色空间通过 `resolveColorspace` 统一解析，确保所有输入在同一颜色空间中合并。
- 滤镜子区域（crop rect）通过 `resolveFilterSubregion` 确定。

## 依赖关系

- **Skia 核心**: `SkImageFilter`、`SkImageFilters`
- **Skia 私有工具**: `SkTArray`（栈上小数组优化）
- **SVG 模块**: `SkSVGFe`（基类）、`SkSVGAttributeParser`、`SkSVGFilterContext`

## 设计模式与设计决策

1. **组合模式**: `SkSVGFeMerge` 作为容器遍历其 `SkSVGFeMergeNode` 子节点，每个子节点独立指定输入源，父节点负责合并。

2. **类型安全遍历**: 使用 `forEachChild<SkSVGFeMergeNode>` 模板方法确保仅处理正确类型的子节点，避免类型转换错误。

3. **输入收集与滤镜构建分离**: `getInputs()` 和 `onMakeImageFilter()` 分别用于依赖分析和实际构建，职责清晰。

## 性能考量

- `STArray<8>` 为少量合并节点场景避免堆分配。
- `reserve(fChildren.size())` 预分配容量，减少动态扩展。
- 合并操作的计算复杂度由 Skia 底层 `SkImageFilters::Merge` 决定。

## 相关文件

- `modules/svg/include/SkSVGFeMerge.h` - 类声明
- `modules/svg/include/SkSVGFe.h` - 滤镜效果基类
- `modules/svg/include/SkSVGFilterContext.h` - 滤镜上下文
- `include/effects/SkImageFilters.h` - Skia 图像滤镜工厂
