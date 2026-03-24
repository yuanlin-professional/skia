# SkSVGAttributeParser

> 源文件: modules/svg/include/SkSVGAttributeParser.h

## 概述

`SkSVGAttributeParser` 是 SVG 属性值解析器,负责将 SVG 属性字符串解析为类型化的 C++ 对象。这是 SVG DOM 构建的核心工具类。

## 主要功能

- 解析各种 SVG 数据类型(长度、颜色、数字、路径等)
- 支持单位转换(px, em, %, pt 等)
- 处理 SVG 特定语法(逗号分隔、空格分隔)
- 提供类型安全的解析结果

## 核心接口

```cpp
template<typename T>
ParseResult<T> parse();

bool parseLength(SkSVGLength*);
bool parseColor(SkSVGColor*);
bool parseNumber(SkSVGNumberType*);
// ... 更多类型特化方法
```

## 解析的数据类型

- 长度值(SkSVGLength): "10px", "50%", "2em"
- 颜色(SkSVGColor): "red", "#ff0000", "rgb(255,0,0)"
- 数字(SkSVGNumberType): "3.14", "100"
- 路径数据: "M 0 0 L 100 100"
- 变换(SkSVGTransform): "translate(10, 20) rotate(45)"
- 点列表: "0,0 100,100 100,0"

## 设计特点

使用模板和类型特化提供统一的解析接口,同时保持类型安全。支持 SVG 规范中的宽松语法(空格、逗号可选)。

## 相关文件

- `modules/svg/src/SkSVGAttributeParser.cpp`: 实现
- `modules/svg/include/SkSVGTypes.h`: SVG 类型定义

该解析器是 SVG 文档加载的基础,确保属性值的正确解析和类型转换。
