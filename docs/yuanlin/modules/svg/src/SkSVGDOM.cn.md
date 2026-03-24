# SkSVGDOM

> 源文件: [modules/svg/src/SkSVGDOM.cpp](../../../../modules/svg/src/SkSVGDOM.cpp)

## 概述

`SkSVGDOM` 是 Skia SVG 模块的核心入口类，负责将 SVG XML 文档解析为内存中的 SVG DOM 树，并提供渲染接口将 SVG 内容绘制到 `SkCanvas` 上。该文件实现了完整的 SVG 解析管线，包括：XML 解析、元素工厂创建、属性解析与分发、style 属性解析，以及最终的渲染流程。

该文件是 SVG 模块中最大的源文件（520 行），包含了大量的属性映射表和标签工厂表，是理解 Skia SVG 模块整体架构的关键入口点。

## 架构位置

```
                      SkStream (输入)
                         │
                     SkDOM (XML 解析)
                         │
                  SkSVGDOM::Builder
                         │
                    construct_svg_node()  ← 递归构建
                         │
                      SkSVGDOM            ← 本文件（SVG DOM 管理器）
                    ┌────┼────┐
                    │    │    │
              fRoot(SVG) │  fIDMapper
                         │
                 SkSVGRenderContext
                         │
                     SkCanvas (输出)
```

`SkSVGDOM` 处于 SVG 模块的最顶层，是用户与 SVG 渲染功能的唯一接口。

## 主要类与结构体

### `SkSVGDOM`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRoot` | `sk_sp<SkSVGSVG>` | 根 SVG 元素 |
| `fFontMgr` | `sk_sp<SkFontMgr>` | 字体管理器（用于文本渲染） |
| `fTextShapingFactory` | `sk_sp<SkShapers::Factory>` | 文本排版工厂 |
| `fResourceProvider` | `sk_sp<skresources::ResourceProvider>` | 资源提供者（图像加载等） |
| `fIDMapper` | `SkSVGIDMapper` | ID 到节点的映射表 |
| `fContainerSize` | `SkSize` | 容器尺寸（用于解析相对单位） |

### `SkSVGDOM::Builder`

构建器模式类，提供链式配置接口：
- `setFontManager()` - 设置字体管理器
- `setResourceProvider()` - 设置资源提供者
- `setTextShapingFactory()` - 设置文本排版回调
- `make()` - 从流中构建 SkSVGDOM

### `ConstructionContext`

内部构建上下文结构体：
- `fParent` - 当前父节点指针
- `fIDMapper` - ID 映射表指针

### `StyleIterator`

CSS 内联样式解析器，将 "foo: bar; baz: qux" 格式的 style 字符串拆分为键值对序列。

### `AttrParseInfo`

属性解析信息结构体，关联 SVG 属性枚举和对应的设置函数指针。

## 公共 API 函数

### `SkSVGDOM::Builder::make(SkStream& str) const`
核心构建方法。从输入流构建 SkSVGDOM：
1. 使用 `SkDOM` 解析 XML
2. 递归构建 SVG 节点树
3. 验证根节点为 `<svg>` 元素
4. 设置资源提供者和文本排版工厂的默认值
5. 返回构建好的 SkSVGDOM 对象

### `MakeFromStream(SkStream& str)`
静态便捷方法，使用默认配置从流构建 SkSVGDOM。

### `render(SkCanvas* canvas) const`
将整个 SVG DOM 渲染到画布上。创建渲染上下文并调用根节点的 render 方法。

### `renderNode(SkCanvas* canvas, SkSVGPresentationContext& pctx, const char* id) const`
渲染指定 ID 的单个节点，如同它是根节点的唯一子元素。主要用于 OpenType SVG 字体中渲染单个字形。

### `setContainerSize(const SkSize& containerSize)`
设置容器尺寸，用于解析根 SVG 元素中百分比和相对单位的尺寸。

### `containerSize() const`
返回当前容器尺寸。

### `findNodeById(const char* id)`
通过 ID 查找 SVG 节点。

### `getRoot() const`
返回根 SVG 元素。

## 内部实现细节

### 属性解析字典 (`gAttributeParseInfo`)

有序字典，将 SVG 属性名映射到解析函数。支持的属性包括：
- 几何属性：`cx`, `cy`, `height`, `width`, `x`, `y`, `x1`, `x2`, `y1`, `y2`, `r`, `rx`, `ry`
- 引用属性：`xlink:href`
- 变换属性：`transform`
- 视口属性：`viewBox`, `preserveAspectRatio`
- 单位属性：`filterUnits`
- 样式属性：`style`（委托给 `SetStyleAttributes` 进行二次解析）
- 文本属性：`text`

使用 `SkStrSearch` 进行二分查找以快速定位属性。

### 标签工厂表 (`gTagFactories`)

有序字典，将 SVG 标签名映射到节点创建工厂 lambda。支持 40+ 种 SVG 元素，包括：
- 基本形状：circle, ellipse, line, path, polygon, polyline, rect
- 容器：g, defs, clipPath, mask, use
- 渐变：linearGradient, radialGradient, stop
- 滤镜：filter 及 16 种 fe* 滤镜基元
- 图像：image
- 文本：text, tspan, textPath
- 图案：pattern

注意：`<svg>` 标签单独处理（区分根/内嵌 SVG），`<a>` 标签映射为 `SkSVGG`（忽略链接语义）。

### 属性设置辅助函数

提供了一组类型特化的属性设置函数：
- `SetIRIAttribute` - IRI 引用属性
- `SetStringAttribute` - 字符串属性
- `SetTransformAttribute` - 变换属性
- `SetLengthAttribute` - 长度属性
- `SetViewBoxAttribute` - viewBox 属性
- `SetObjectBoundingBoxUnitsAttribute` - 边界框单位属性
- `SetPreserveAspectRatioAttribute` - 宽高比属性
- `SetStyleAttributes` - style 属性（二次解析）

### 双重属性解析路径

`set_string_attribute` 函数实现了新旧两条属性解析路径：
1. 首先调用 `node->parseAndSetAttribute()`（新路径，逐步扩展）
2. 如果新路径未处理，则查找 `gAttributeParseInfo` 字典（旧路径）

### 递归节点构建 (`construct_svg_node`)

递归地从 XML DOM 构建 SVG DOM：
1. 处理文本节点（`kText_Type`）为 `SkSVGTextLiteral`
2. 使用工厂表创建元素节点
3. 解析节点属性（`parse_node_attributes`）
4. 递归处理子节点
5. 特殊处理 `id` 属性（注册到 ID 映射表）

### NullResourceProvider

内部匿名类，当用户未提供资源提供者时使用，所有 `load` 调用均返回 nullptr。

### TrimmedString 辅助函数

去除字符串首尾空白字符的辅助函数，用于 style 属性解析。

## 依赖关系

- **Skia Core**: `SkData`, `SkFontMgr`, `SkString`, `SkCanvas`
- **Skia Internal**: `SkTSearch`（二分查找）, `SkTraceEvent`（性能追踪）, `SkDOM`（XML 解析）
- **Skia Modules**: `SkShaper_factory`（文本排版）, `SkResources`（资源加载）
- **SVG 模块**: 几乎所有 SVG 节点类的头文件（40+），以及 `SkSVGAttribute`, `SkSVGAttributeParser`, `SkSVGRenderContext`, `SkSVGTypes`, `SkSVGValue`
- **标准库**: `<stdint.h>`, `<array>`, `<cstring>`, `<tuple>`, `<utility>`

## 设计模式与设计决策

1. **建造者模式 (Builder)**: `SkSVGDOM::Builder` 提供流畅的链式配置接口，将构建过程与表示分离，允许灵活配置字体管理器、资源提供者等。

2. **工厂方法模式**: `gTagFactories` 表使用 lambda 工厂函数创建节点，将节点实例化逻辑与解析逻辑解耦。

3. **有序字典 + 二分查找**: 属性和标签映射表按字母排序，使用 `SkStrSearch` 二分查找，在保持可读性的同时实现 O(log n) 查找效率。

4. **新旧双路径兼容**: 属性解析同时支持新的 `parseAndSetAttribute` 路径（类型安全，节点自行处理）和旧的字典查找路径（基于枚举和值类型），实现渐进式重构。

5. **递归下降构建**: SVG DOM 树通过递归处理 XML DOM 的方式构建，自然映射了 XML 的层次结构。

6. **引用计数所有权**: DOM 中所有节点使用 `sk_sp` 智能指针管理，Builder 创建的 DOM 整体也是引用计数对象。

7. **TRACE_EVENT 性能埋点**: 在关键路径（make、render、renderNode）中添加了性能追踪事件。

## 性能考量

- **XML 解析**: 使用 Skia 内建的 `SkDOM` 解析器，一次性将整个 XML 加载到内存中
- **二分查找**: 属性和标签查找为 O(log n)，对于 20+ 属性和 40+ 标签规模效率足够
- **内存分配**: 每个 SVG 节点都是堆分配的引用计数对象，深层嵌套的 SVG 可能产生大量小对象
- **渲染上下文**: 每次 render 调用创建完整的渲染上下文栈，包括长度上下文和展示上下文
- **ID 映射**: 使用哈希映射存储 ID -> 节点的映射，O(1) 查找效率
- **性能追踪**: `TRACE_EVENT0` 在 release 构建中开销极小
- **容器尺寸**: 构造时即计算初始容器尺寸（通过根元素的 `intrinsicSize`），避免渲染时重复计算

## 相关文件

- `modules/svg/include/SkSVGDOM.h` - 头文件，定义 SkSVGDOM 类和 Builder 接口
- `modules/svg/include/SkSVGNode.h` - 节点基类
- `modules/svg/include/SkSVGSVG.h` - 根 SVG 元素
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
- `modules/svg/include/SkSVGIDMapper.h` - ID 映射器
- `modules/svg/include/SkSVGAttribute.h` - 属性枚举定义
- `modules/svg/include/SkSVGValue.h` - 属性值类型
- `src/xml/SkDOM.h` - Skia XML DOM 解析器
- `modules/skresources/include/SkResources.h` - 资源提供者接口
- `modules/skshaper/include/SkShaper_factory.h` - 文本排版工厂
