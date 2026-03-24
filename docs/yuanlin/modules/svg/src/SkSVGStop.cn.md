# SkSVGStop

> 源文件: [modules/svg/src/SkSVGStop.cpp](../../../../modules/svg/src/SkSVGStop.cpp)

## 概述

`SkSVGStop` 实现了 SVG `<stop>` 元素，该元素用于定义渐变（`<linearGradient>` 和 `<radialGradient>`）中的颜色停止点。每个 `<stop>` 元素通过 `offset` 属性指定其在渐变路径上的位置（0.0 到 1.0 之间的值或百分比）。本文件代码极为简洁（仅 17 行源代码），仅包含构造函数和属性解析逻辑，颜色相关的属性（`stop-color`、`stop-opacity`）由基类的呈现属性系统处理。

## 架构位置

```
SkSVGNode (SVG 节点基类)
  └── SkSVGHiddenContainer 或 SkSVGNode
        └── SkSVGStop  ← 本文件实现
```

`SkSVGStop` 是渐变元素的子节点，在渐变构建过程中被父节点（如 `SkSVGLinearGradient`、`SkSVGRadialGradient`）遍历以收集颜色停止点信息。渐变父节点通过迭代其子节点列表，提取每个 `SkSVGStop` 的 `offset` 值以及从呈现属性系统继承的 `stop-color` 和 `stop-opacity`，然后组装成 Skia 的 `SkGradientShader` 所需的参数。

## 主要类与结构体

### SkSVGStop
- 对应 SVG `<stop>` 元素
- 通过 `SkSVGTag::kStop` 标识
- 核心属性为 `offset`（类型 `SkSVGLength`），表示渐变位置
- 属于不可见节点类型，不直接参与渲染，仅作为数据源供父渐变节点使用

## 公共 API 函数

### 构造函数
```cpp
SkSVGStop::SkSVGStop() : INHERITED(SkSVGTag::kStop) {}
```
使用 `kStop` 标签初始化基类。这是一个无参构造函数，所有属性通过后续的 `parseAndSetAttribute` 设置。

### `parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* n, const char* v);
```
解析 `offset` 属性（`SkSVGLength` 类型），同时委托基类处理其他通用属性（如 `stop-color`、`stop-opacity` 等呈现属性）。函数返回 `true` 表示成功解析了某个属性。

属性解析使用短路求值链式调用：
```cpp
return INHERITED::parseAndSetAttribute(n, v) ||
       this->setOffset(SkSVGAttributeParser::parse<SkSVGLength>("offset", n, v));
```

## 内部实现细节

- 该文件仅 17 行，是 SVG 模块中最精简的实现之一。`offset` 属性通过 `SkSVGAttributeParser::parse<SkSVGLength>` 解析，支持百分比（如 `"50%"`）和纯数值（如 `"0.5"`）两种格式。
- `stop-color` 和 `stop-opacity` 等视觉属性不在此文件中处理，而是通过 SVG 呈现属性继承机制在基类中统一管理。这些属性可以在 `<stop>` 元素上直接设置，也可以通过 CSS 样式表或父元素继承。
- 链式调用模式：`INHERITED::parseAndSetAttribute(n, v)` 先尝试基类解析，如果基类成功处理则短路返回 `true`，否则尝试本类的 `offset` 属性解析。
- `setOffset` 方法由头文件中的 `SVG_ATTR` 宏自动生成，返回 `bool` 值表示是否成功设置。

## 依赖关系

- **SVG 模块**: `SkSVGStop.h`（头文件，包含类声明和 `SVG_ATTR` 宏生成的属性方法）、`SkSVGAttributeParser`（属性解析工具类）
- **基类**: `INHERITED`（通过头文件中的继承链确定，提供通用属性解析能力）

## 设计模式与设计决策

1. **最小职责原则**: `SkSVGStop` 仅负责 `offset` 属性的解析，将颜色和透明度的处理委托给 SVG 呈现属性系统，保持了职责单一。这种设计使得 `stop-color` 可以通过 CSS 样式表设置，无需特殊处理。

2. **链式属性解析**: 使用短路求值的 `||` 链式调用，先尝试基类解析，再尝试子类特有属性，这是 SVG 模块的标准属性解析模式。这种模式确保了属性名称匹配的唯一性和优先级正确性。

3. **数据节点模式**: `SkSVGStop` 作为纯数据节点存在，不参与渲染流程。它的唯一作用是持有 `offset` 值，供父渐变节点在构建 `SkShader` 时查询。

4. **SVG_ATTR 宏自动生成**: `offset` 属性的存储、getter 和 setter 方法由宏自动生成，减少了样板代码。

## 性能考量

- 作为一个仅存储属性值的轻量级节点，`SkSVGStop` 没有性能相关的特殊考量。
- 属性解析在 SVG 文档加载时一次性完成，不影响渲染性能。
- 渐变父节点在构建着色器时遍历所有 stop 子节点，但 stop 数量通常很少（典型为 2-5 个），不构成性能瓶颈。

## 相关文件

- `modules/svg/include/SkSVGStop.h` - 类声明与属性定义
- `modules/svg/include/SkSVGAttributeParser.h` - 属性解析器
- `modules/svg/src/SkSVGLinearGradient.cpp` - 线性渐变（遍历 stop 节点构建着色器）
- `modules/svg/src/SkSVGRadialGradient.cpp` - 径向渐变（遍历 stop 节点构建着色器）
- `modules/svg/src/SkSVGGradient.cpp` - 渐变基类（处理 stop 节点收集逻辑）
- `modules/svg/include/SkSVGTypes.h` - `SkSVGLength` 类型定义
