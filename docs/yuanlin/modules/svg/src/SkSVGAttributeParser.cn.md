# SkSVGAttributeParser - SVG 属性解析器

> 源文件: [`modules/svg/src/SkSVGAttributeParser.cpp`](../../../modules/svg/src/SkSVGAttributeParser.cpp)

## 概述

SkSVGAttributeParser 是 Skia SVG 模块的核心属性值解析器，负责将 SVG 属性字符串解析为强类型的 Skia SVG 值类型。它是一个手写的递归下降解析器，支持 SVG 1.1 规范中定义的几乎所有属性值格式，包括颜色（hex、命名、rgb/rgba、CSS 变量）、长度（各种单位）、变换矩阵、绘制（fill/stroke）、路径数据、点列表等。

## 架构位置

位于 SVG 模块的内部实现层：

- **调用者**: SkSVGNode 及其子类（在解析 XML 属性时调用）
- **输入**: SVG 属性字符串（如 `"rgb(255, 0, 0)"`、`"translate(10, 20) rotate(45)"` 等）
- **输出**: 强类型的 SkSVG* 值类型

## 主要类与结构体

### `SkSVGAttributeParser` 类（在 .h 中定义）
基于字符串指针的前向解析器，使用 `fCurPos` 和 `fEndPos` 标记解析范围。

### `RestoreCurPos` 内部辅助类
RAII 保护，在回溯解析失败时恢复解析位置。成功时调用 `clear()` 取消恢复。

## 公共 API 函数（模板特化）

| 解析目标类型 | 说明 |
|-------------|------|
| `SkSVGColorType` | 颜色值（hex #RGB/#RRGGBB、命名颜色、rgb()、rgba()） |
| `SkSVGColor` | 颜色值 + currentColor + CSS var() 变量 |
| `SkSVGIRI` | IRI 引用（本地 #id、数据 URI、非本地 URL） |
| `SkSVGFuncIRI` | 函数式 IRI（url(...)） |
| `SkSVGStringType` | 原始字符串 |
| `SkSVGNumberType` | 数值 |
| `SkSVGLength` | 带单位的长度（px, em, %, cm, mm, in, pt, pc） |
| `SkSVGTransformType` | 变换矩阵（matrix, translate, scale, rotate, skewX, skewY） |
| `SkSVGPaint` | 绘制值（颜色/none/url()） |
| `SkSVGLineCap` | 线帽（butt/round/square） |
| `SkSVGLineJoin` | 连接方式（miter/round/bevel） |
| `SkSVGFillRule` | 填充规则（nonzero/evenodd） |
| `SkSVGVisibility` | 可见性（visible/hidden/collapse） |
| `SkSVGDashArray` | 虚线数组 |
| `SkSVGFontFamily` | 字体族名 |
| `SkSVGFontSize` | 字体大小 |
| `SkSVGPointsType` | 点列表（polygon/polyline 用） |
| `SkSVGObjectBoundingBoxUnits` | 边界框单位 |

## 内部实现细节

### 解析器结构
使用经典的手写递归下降模式：
- `parseExpectedStringToken()`: 精确匹配字符串
- `parseScalarToken()` / `parseInt32Token()`: 数值解析（委托给 SkParse）
- `advanceWhile(predicate)`: 跳过满足条件的字符
- `parseParenthesized(prefix, func, result)`: 解析 `prefix(...)` 形式

### 颜色解析优先级
`parseColorToken` 按以下顺序尝试：hex -> 命名颜色 -> rgba() -> rgb()

### CSS 变量支持
`parseSVGColor` 支持递归解析 `var(--name, fallback)` 语法，最多 32 层嵌套。

### 变换矩阵解析
`parse<SkSVGTransformType>` 在循环中依次尝试六种变换类型（matrix/translate/scale/rotate/skewX/skewY），多个变换通过 `preConcat` 组合。

### 长度单位解析
支持 9 种 SVG/CSS 长度单位：%, em, ex, px, cm, mm, in, pt, pc。无单位默认为 kNumber。

### CSS escape 处理
`parseEscape` 支持 CSS 转义序列（`\XXXX` 十六进制和 `\char` 字面量），用于标识符解析。

### 回溯机制
使用 `RestoreCurPos` RAII 类实现安全回溯：解析方法开始时保存位置，成功时 `clear()` 取消恢复，失败时自动回退。

## 依赖关系

- `modules/svg/include/SkSVGAttributeParser.h` - 类声明
- `modules/svg/include/SkSVGTypes.h` - SVG 值类型
- `include/utils/SkParse.h` - 底层数值和颜色名解析
- `src/base/SkUTF.h` - UTF-8 处理
- `include/core/SkMatrix.h` - 变换矩阵

## 设计模式与设计决策

### 模板特化 parse<T>
每种 SVG 类型通过 `parse<T>` 模板特化实现解析，提供统一的调用接口。

### 前向解析
不构建 AST 或中间表示，直接将字符串转换为最终类型，减少内存分配。

### 宽松解析
对分隔符的处理比较宽松（空格、逗号、分号），兼容不同 SVG 生成器的输出。

## 性能考量

- 纯前向解析，无正则表达式
- 字符分类使用内联函数（is_ws, is_sep, is_hex）
- 回溯使用栈上 RAII 对象，无堆分配
- 命名颜色查找委托给 SkParse 的高效实现

## 相关文件

- `modules/svg/include/SkSVGAttributeParser.h` - 类声明和公共接口
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义
- `include/utils/SkParse.h` - 底层解析工具
