# SkSVGSVG

> 源文件: [modules/svg/src/SkSVGSVG.cpp](../../../../modules/svg/src/SkSVGSVG.cpp)

## 概述

`SkSVGSVG` 实现了 SVG `<svg>` 元素，是 SVG 文档的根元素或内嵌 SVG 元素。它负责建立 SVG 的视口（viewport）和坐标系统，处理 `viewBox` 和 `preserveAspectRatio` 属性，并管理 SVG 文档的固有尺寸（intrinsic size）。

该类区分根 SVG 元素和内嵌 SVG 元素（通过 `Type` 枚举），对 `x`/`y` 属性的处理规则不同：根元素忽略 x/y，内嵌元素则正常应用。

## 架构位置

```
SkSVGNode
  └── SkSVGContainer
        └── SkSVGSVG              ← 本文件（SVG 根/内嵌元素）
              └── children          （所有子 SVG 元素）

与 SkSVGDOM 的关系:
  SkSVGDOM
    ├── fRoot: sk_sp<SkSVGSVG>    （持有根 SVG 元素）
    ├── render() → fRoot->render()
    └── renderNode() → fRoot->renderNode()
```

`SkSVGSVG` 是 SVG DOM 树的顶层节点，由 `SkSVGDOM` 持有并在渲染时首先被调用。它同时也可以作为内嵌 SVG 出现在文档树的任意位置，此时 Type 为 kInner。

### viewBox 与 viewport 的关系

SVG 坐标系统的核心概念：
- **viewport（视口）**: 由 x, y, width, height 定义的物理区域
- **viewBox**: 定义映射到视口的用户坐标系统
- **preserveAspectRatio**: 控制 viewBox 到 viewport 的映射方式

当两者都存在时，viewBox 建立新的用户坐标系，通过 preserveAspectRatio 控制映射。

## 主要类与结构体

### `SkSVGSVG`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fX` | `SkSVGLength` | X 坐标（仅内嵌 SVG 有效） |
| `fY` | `SkSVGLength` | Y 坐标（仅内嵌 SVG 有效） |
| `fWidth` | `SkSVGLength` | SVG 宽度 |
| `fHeight` | `SkSVGLength` | SVG 高度 |
| `fViewBox` | `std::optional<SkSVGViewBoxType>` | viewBox 属性 |
| `fPreserveAspectRatio` | `SkSVGPreserveAspectRatio` | 宽高比保持策略 |
| `fType` | `Type` | 元素类型（kRoot 或 kInner） |

### `Type` 枚举

| 值 | 说明 |
|----|------|
| `kRoot` | 最外层 `<svg>` 元素 |
| `kInner` | 嵌套的 `<svg>` 元素 |

## 公共 API 函数

### `renderNode(const SkSVGRenderContext& ctx, const SkSVGIRI& iri) const`
渲染指定 ID 的子节点。用于 OpenType SVG 字体渲染，只渲染文档中的特定元素：
1. 创建本地渲染上下文
2. 通过 IRI 查找目标节点
3. 如果目标是自身，渲染整个 SVG
4. 否则仅渲染目标节点

### `intrinsicSize(const SkSVGLengthContext& lctx) const`
计算 SVG 的固有尺寸。如果宽度或高度使用百分比单位，对应维度返回 0（表示无固有尺寸）。

## 内部实现细节

### 渲染准备 (`onPrepareToRender`)

核心方法，建立 SVG 的坐标系统：

1. **处理 x/y**: 根元素忽略 x/y（强制为 0），内嵌元素正常使用。这是 SVG 规范的要求——最外层 `<svg>` 的位置由嵌入上下文决定。
2. **解析视口矩形**: 使用长度上下文解析 x, y, width, height 为像素值
3. **计算内容矩阵**: 初始为视口位置的平移矩阵
4. **处理 viewBox**:
   - 空 viewBox 禁止渲染（返回 false）——这是 SVG 规范明确要求的行为
   - 非空 viewBox 覆盖视口尺寸，建立新的用户坐标系
   - 使用 `ComputeViewboxMatrix()` 计算 viewBox 到视口的映射矩阵，支持 preserveAspectRatio 的 meet/slice/none 语义
5. **应用变换**: 如果内容矩阵非单位矩阵，保存上下文并通过 `canvas->concat()` 应用到画布
6. **更新视口**: 如果视口尺寸变化，更新长度上下文的视口。这确保后续子元素中的百分比长度基于新视口计算
7. **调用基类**: 执行基类的 `onPrepareToRender` 处理展示属性和可见性检查

### 属性设置 (`onSetAttribute`)

通过旧的属性设置路径处理六个属性，使用 switch-case 分发：

| 属性枚举 | 值类型 | setter 方法 |
|----------|--------|-------------|
| `kX` | `SkSVGLengthValue` | `setX()` |
| `kY` | `SkSVGLengthValue` | `setY()` |
| `kWidth` | `SkSVGLengthValue` | `setWidth()` |
| `kHeight` | `SkSVGLengthValue` | `setHeight()` |
| `kViewBox` | `SkSVGViewBoxValue` | `setViewBox()` |
| `kPreserveAspectRatio` | `SkSVGPreserveAspectRatioValue` | `setPreserveAspectRatio()` |

其他属性委托给基类处理。每个属性的设置都先通过 `v.as<Type>()` 进行类型安全的向下转换，转换失败时静默跳过（不修改属性值）。

### 固有尺寸计算

百分比单位的特殊处理：SVG 规范规定，当根元素的 width/height 使用百分比时，其固有尺寸无法确定（返回 0），需要外部容器提供实际尺寸（通过 `SkSVGDOM::setContainerSize()`）。这对于嵌入在 HTML 中的 SVG 尤为重要。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkMatrix`, `SkRect`
- **SVG 模块**: `SkSVGAttribute`, `SkSVGRenderContext`, `SkSVGValue`, `SkSVGContainer`

## 设计模式与设计决策

1. **Root/Inner 区分**: 通过 `Type` 枚举区分根和内嵌 SVG，仅在 `onPrepareToRender` 中体现差异（x/y 处理），其余逻辑完全共享。这种设计避免了创建两个独立的类。

2. **viewBox 优先级**: 当 viewBox 存在时，它覆盖视口的尺寸信息，实现了 SVG 规范中 viewBox 建立新坐标系的语义。viewBox 为空时完全禁止渲染，这是规范要求的行为。

3. **条件保存**: 仅在内容矩阵非单位矩阵时保存上下文（`ctx->saveOnce()`），避免不必要的画布状态压栈。这对简单的、没有 viewBox 偏移的 SVG 文档是一个有效的优化。

4. **条件视口更新**: 仅在视口实际变化时更新长度上下文，减少不必要的重新计算。这在嵌套 SVG 中尤为重要。

5. **按需渲染**: `renderNode` 支持只渲染指定 ID 的节点，这是 OpenType SVG 字体渲染的核心需求。该方法先在自身的上下文中查找目标节点，然后区分"渲染自身"和"渲染子节点"两种情况。

6. **旧属性路径**: `onSetAttribute` 通过 switch-case 分发 6 种属性，属于旧的属性设置路径。新路径通过 `parseAndSetAttribute`（在子类或基类中定义）直接处理。

7. **百分比固有尺寸**: SVG 规范规定百分比尺寸不提供固有尺寸，`intrinsicSize` 对此返回 0，调用者需要通过 `setContainerSize` 提供外部尺寸信息。

## 性能考量

- viewBox 矩阵计算仅在渲染准备阶段执行一次，包含缩放和平移的矩阵乘法
- `saveOnce()` 的条件检查避免了不必要的画布状态操作，对于无变换的简单 SVG 有优化效果
- 固有尺寸计算为纯浮点运算，代价极小
- 百分比尺寸的检查在 `intrinsicSize` 中使用简单的枚举比较
- 空 viewBox 检查提供了快速的渲染终止路径，避免不必要的子树遍历
- `onSetAttribute` 使用 switch-case 分发 6 个属性，编译器通常会优化为跳转表
- 视口尺寸更新检查（`viewPort != ctx->lengthContext().viewPort()`）避免了不必要的长度上下文重建
- `renderNode` 中的节点查找通过 `SkSVGIDMapper` 的哈希映射实现，O(1) 复杂度
- 条件渲染逻辑（区分 self 和 child 渲染）避免了 OpenType SVG 场景下的全树遍历
- 内容矩阵的 `preConcat` 操作比创建新矩阵后相乘更高效

## 相关文件

- `modules/svg/include/SkSVGSVG.h` - 头文件定义，包含 Type 枚举和属性声明
- `modules/svg/src/SkSVGDOM.cpp` - 创建 SkSVGSVG 并管理其生命周期，区分 Root 和 Inner 类型
- `modules/svg/src/SkSVGNode.cpp` - `ComputeViewboxMatrix` 实现，处理 preserveAspectRatio 语义
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文和长度上下文，提供视口信息
- `modules/svg/include/SkSVGContainer.h` - 容器基类，提供子节点管理
- `modules/svg/include/SkSVGValue.h` - 属性值类型，用于旧的 onSetAttribute 路径
- `modules/svg/include/SkSVGAttribute.h` - 属性枚举定义
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义，包括 SkSVGLength、SkSVGPreserveAspectRatio 等
- `modules/svg/src/SkSVGOpenTypeSVGDecoder.cpp` - OpenType SVG 解码器，调用 renderNode 渲染字形
