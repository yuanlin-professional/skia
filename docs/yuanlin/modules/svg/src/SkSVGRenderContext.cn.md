# SkSVGRenderContext - SVG 渲染上下文

> 源文件: [`modules/svg/src/SkSVGRenderContext.cpp`](../../../modules/svg/src/SkSVGRenderContext.cpp)

## 概述

SkSVGRenderContext 是 Skia SVG 渲染模块的核心上下文类，负责在 SVG 文档树的遍历过程中管理渲染状态。它包含长度解析上下文（单位换算）、表现属性上下文（可继承的样式属性）、画布状态、字体管理器、资源提供者和 ID 映射等。每个 SVG 节点在渲染时都会创建一个新的 SkSVGRenderContext 副本。

## 架构位置

位于 SVG 模块的核心层：

- **创建者**: SkSVGDOM（根上下文）、SVG 节点渲染方法（子上下文）
- **使用者**: 所有 SkSVGNode 子类的渲染和属性解析方法
- **管理对象**: SkCanvas、SkSVGLengthContext、SkSVGPresentationContext

## 主要类与结构体

### `SkSVGLengthContext` 类
长度解析上下文，负责将 SVG 长度值（带单位）转换为像素值。

支持的单位和乘数：
- px（像素）: 直接值
- %（百分比）: 相对于视口尺寸（水平/垂直/对角线）
- cm, mm, in, pt, pc: 基于 DPI 的绝对单位

`LengthType` 枚举区分三种方向：kHorizontal、kVertical、kOther（视口对角线 / sqrt(2)）。

### `SkSVGPresentationContext` 类
表现属性上下文，包含所有可继承的 SVG 样式属性（fill、stroke、font 等）。

### `SkSVGRenderContext` 类
完整的渲染上下文，组合了画布、长度上下文、表现上下文等。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `resolve(length, type)` | 将 SVG 长度解析为像素值 |
| `resolveRect(x, y, w, h)` | 解析矩形四个长度值 |
| `findNodeById(iri)` | 通过 ID 查找 SVG 节点 |
| `applyPresentationAttributes(attrs, flags)` | 应用表现属性到当前上下文 |
| `applyOpacity(opacity, flags, hasFilter)` | 应用不透明度 |

## 内部实现细节

### 属性继承机制
`applyPresentationAttributes` 使用 `ApplyLazyInheritedAttribute` 宏处理所有可继承属性（24 个），包括：Fill、FillOpacity、FillRule、FontFamily、FontSize、FontStyle、FontWeight、Stroke 相关、TextAnchor、Visibility、Color 等。

惰性更新：仅当新值与当前继承值不同时才更新。

### 非继承属性
不透明度（Opacity）、裁剪路径（ClipPath）、蒙版（Mask）、滤镜（Filter）作为非继承属性单独处理，直接应用到当前上下文。

### 不透明度优化
当目标节点没有子元素、只有 fill 或 stroke（不是两者都有）、且没有滤镜时，可以将不透明度直接作为 paint alpha 应用，避免创建额外的图层。

### 虚线效果
`dash_effect` 从表现属性构建 SkDashPathEffect，处理奇数长度数组的自动复制（SVG 规范要求）。

### 画布状态管理
构造时记录 `fCanvasSaveCount`，析构时 `restoreToCount` 确保画布状态正确恢复。

## 依赖关系

- `modules/svg/include/SkSVGRenderContext.h` - 类声明
- `modules/svg/include/SkSVGAttribute.h` - 表现属性定义
- `modules/svg/include/SkSVGNode.h` - SVG 节点基类
- `modules/svg/include/SkSVGClipPath.h` / `SkSVGFilter.h` / `SkSVGMask.h`
- `include/core/SkCanvas.h` - 绘制画布
- `include/effects/SkDashPathEffect.h` - 虚线效果

## 设计模式与设计决策

### 写时复制 (COW)
`fPresentationContext` 使用惰性写时复制语义（`writable()`），避免在属性未修改时的不必要复制。

### RAII 画布管理
通过构造/析构的 save/restore 配对，确保画布状态在作用域退出时自动恢复。

### 宏驱动的属性应用
使用 `ApplyLazyInheritedAttribute` 宏消除 24 个属性的重复代码。

## 性能考量

- 写时复制避免不必要的属性上下文克隆
- 不透明度在可能时直接应用为 paint alpha，避免图层开销
- 长度解析是简单的乘法运算，内联优化

## 相关文件

- `modules/svg/include/SkSVGRenderContext.h` - 类声明
- `modules/svg/include/SkSVGAttribute.h` - 属性定义
- `modules/svg/include/SkSVGNode.h` - 使用上下文的节点基类
