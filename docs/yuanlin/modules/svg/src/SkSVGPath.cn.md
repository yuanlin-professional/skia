# SkSVGPath

> 源文件: [modules/svg/src/SkSVGPath.cpp](../../../../modules/svg/src/SkSVGPath.cpp)

## 概述

`SkSVGPath` 实现了 SVG `<path>` 元素，是 SVG 中最通用和强大的形状元素。它通过 `d` 属性接受 SVG 路径数据字符串，可以描述任意复杂的形状，包括直线、曲线、弧线及其组合。

该实现将 SVG 路径语法解析委托给 Skia 的 `SkParsePath` 工具，然后在绘制时正确应用填充规则和裁剪规则。

## 架构位置

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGShape
              └── SkSVGPath        ← 本文件
```

## 主要类与结构体

### `SkSVGPath`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fPath` | `SkPath` | 解析后的路径数据 |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析 `d` 属性，将 SVG 路径数据字符串转换为 `SkPath` 对象。

## 内部实现细节

### SVG 路径数据解析

通过特化 `SkSVGAttributeParser::parse<SkPath>` 模板函数，使用 `SkParsePath::FromSVGString()` 将 SVG 路径语法（如 "M10 20 L30 40 Z"）解析为 `SkPath` 对象。

### 绘制 (`onDraw`)

1. 复制路径对象（利用 SkPath 的 CoW 语义，仅复制句柄而非数据）
2. 设置继承的 `fillType`（因为填充规则通过继承链传播，需要在绘制时应用）
3. 调用 `SkCanvas::drawPath()` 绘制

### 路径转换 (`onAsPath`)

1. 复制路径
2. 设置 `clip-rule` 的填充类型（裁剪时使用 `clip-rule` 而非 `fill-rule`）
3. 应用父级变换

### 对象边界框 (`onTransformableObjectBoundingBox`)

使用 `SkPath::computeTightBounds()` 计算精确的路径边界框。

### 填充规则的延迟应用

SVG 中 `fill-rule` 和 `clip-rule` 是继承的展示属性，其值在渲染时才最终确定。因此路径的填充类型不在解析时设置，而是在每次绘制/裁剪时从渲染上下文中获取并应用。

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkPathTypes`
- **Skia Utils**: `SkParsePath`（SVG 路径字符串解析器）
- **SVG 模块**: `SkSVGAttribute`, `SkSVGAttributeParser`, `SkSVGRenderContext`, `SkSVGTypes`

## 设计模式与设计决策

1. **CoW 路径复制**: `SkPath` 的 Copy-on-Write 机制确保 `SkPath path = fPath` 仅复制引用，只有在修改 fillType 时才触发真正的数据复制。

2. **分离解析与填充规则**: 路径数据在 `parseAndSetAttribute` 时解析并缓存，fillType 在绘制时动态设置。这符合 SVG 的属性继承模型，因为 `fill-rule` 可能在 DOM 的任意层级被覆盖。

3. **clip-rule vs fill-rule**: `onAsPath()` 使用 `clip-rule`（因为路径转换主要用于裁剪），`onDraw()` 使用 `fill-rule`（因为绘制使用填充规则），体现了对 SVG 规范的精确遵循。

4. **委托解析**: SVG 路径语法的解析完全委托给 `SkParsePath`，避免重复实现复杂的路径命令解析器。

## 性能考量

- SVG 路径字符串解析（`SkParsePath::FromSVGString`）是一次性操作，结果缓存在 `fPath` 中
- `computeTightBounds()` 会遍历所有路径段，对于复杂路径可能较慢
- `SkPath` 的 CoW 机制在大多数情况下避免了不必要的路径数据复制
- 路径对象的内存由 Skia 核心管理，支持高效的共享和复制

## 相关文件

- `modules/svg/include/SkSVGPath.h` - 头文件定义
- `include/utils/SkParsePath.h` - SVG 路径字符串解析器
- `modules/svg/include/SkSVGShape.h` - 形状基类
- `modules/svg/include/SkSVGRenderContext.h` - 提供 fill-rule 和 clip-rule
