# SkDOM - XML 文档对象模型

> 源文件:
> - `src/xml/SkDOM.h`
> - `src/xml/SkDOM.cpp`

## 概述

SkDOM 是 Skia 中的 XML 文档对象模型 (DOM) 实现。它将 XML 文档解析为内存中的树形结构，并提供遍历节点、查找属性、解析各种数据类型等功能。SkDOM 使用 `SkArenaAllocWithReset` 进行高效的内存管理，所有节点和属性数据都在同一个内存池中分配。

## 架构位置

```
Skia XML 子系统
├── SkXMLParser (SAX 解析)
│   └── SkDOMParser (内部类 - SAX 到 DOM 转换)
├── SkDOM (本模块 - DOM 树管理)
│   ├── SkDOMNode (节点结构)
│   └── SkDOMAttr (属性结构)
├── SkXMLWriter (XML 输出)
└── SVG 模块 / 动画模块
```

## 主要类与结构体

### `SkDOM`
- 管理 XML 文档树的主类，继承自 `SkNoncopyable`。
- **成员变量**:
  - `fAlloc` (SkArenaAllocWithReset): 内存池，初始块大小 4096 字节。
  - `fRoot` (Node*): 根节点指针。
  - `fParser` (unique_ptr\<SkDOMParser\>): 增量解析器实例。
- **类型别名**: `Node = SkDOMNode`, `Attr = SkDOMAttr`。

### `SkDOMNode` (内部结构)
```cpp
struct SkDOMNode {
    const char* fName;         // 节点名称
    SkDOMNode*  fFirstChild;   // 第一个子节点
    SkDOMNode*  fNextSibling;  // 下一个兄弟节点
    SkDOMAttr*  fAttrs;        // 属性数组指针
    uint16_t    fAttrCount;    // 属性数量
    uint8_t     fType;         // 节点类型
};
```

### `SkDOMAttr` (内部结构)
```cpp
struct SkDOMAttr {
    const char* fName;   // 属性名
    const char* fValue;  // 属性值
};
```

### `SkDOM::Type` 枚举
- `kElement_Type`: 元素节点。
- `kText_Type`: 文本节点。

### `SkDOM::AttrIter`
- 属性迭代器，用于遍历节点的所有属性。

### `SkDOMParser` (内部类)
- 继承自 `SkXMLParser`，实现 SAX 到 DOM 的转换。
- 将 XML 事件转换为 `SkDOMNode` 和 `SkDOMAttr` 对象。

## 公共 API 函数

### 构建/解析
- `build(SkStream&, int* errorOnLineNumber)`: 从流解析并构建 DOM 树。
- `copy(const SkDOM&, const Node*)`: 从另一个 DOM 复制子树。
- `beginParsing()` / `finishParsing()`: 增量解析接口。

### 节点遍历
- `getRootNode()`: 获取根节点。
- `getType(Node*)`: 获取节点类型。
- `getName(Node*)`: 获取节点名称。
- `getFirstChild(Node*, elem)`: 获取第一个子节点，可按名称过滤。
- `getNextSibling(Node*, elem)`: 获取下一个兄弟节点，可按名称过滤。
- `countChildren(Node*, elem)`: 计算子节点数量。

### 属性访问
- `findAttr(Node*, name)`: 查找属性值（字符串形式）。
- `getFirstAttr(Node*)` / `getNextAttr(Node*, Attr*)`: 属性迭代。
- `getAttrName(Node*, Attr*)` / `getAttrValue(Node*, Attr*)`: 获取属性名/值。

### 类型化属性查找
- `findS32(Node*, name, int32_t*)`: 查找并解析 32 位整数。
- `findScalars(Node*, name, SkScalar[], count)`: 查找并解析浮点数组。
- `findHex(Node*, name, uint32_t*)`: 查找并解析十六进制值。
- `findBool(Node*, name, bool*)`: 查找并解析布尔值。
- `findList(Node*, name, list)`: 在列表中查找匹配项。

### 属性匹配
- `hasAttr(Node*, name, value)`: 检查属性是否等于指定值。
- `hasS32/hasScalar/hasHex/hasBool(Node*, name, target)`: 类型化的属性值匹配。

## 内部实现细节

### SkDOMParser 的工作机制
1. **延迟刷新**: 属性在 `flushAttributes()` 时才被写入节点，允许在元素开始和属性添加之间累积。
2. **反向兄弟链接**: 子节点在构建时以反向顺序链接（`node->fNextSibling = parent->fFirstChild`），在 `onEndElement()` 中翻转为正向顺序。
3. **字符串复制**: 所有字符串通过 `dupstr()` 复制到 arena 分配器中，确保生命周期与 DOM 一致。
4. **文本节点处理**: 文本节点被创建为特殊的叶节点，立即调用 `onEndElement` 闭合。

### 内存管理
- 所有 `SkDOMNode`、`SkDOMAttr` 和字符串都分配在 `SkArenaAllocWithReset` 中。
- 重新解析时调用 `fAlloc.reset()` 释放所有之前分配的内存。
- 没有单独节点释放的能力——整个 DOM 只能作为整体释放。

### 属性查找
`findAttr()` 使用线性扫描节点的属性数组。由于 XML 元素的属性数量通常很少，线性扫描效率足够。

### 类型化解析
使用 `SkParse` 工具类将字符串属性值解析为各种类型：
- `SkParse::FindS32` / `FindScalar` / `FindHex` / `FindBool` / `FindList`。

## 依赖关系

- `include/core/SkScalar.h`: 浮点类型。
- `include/private/base/SkNoncopyable.h`: 不可复制基类。
- `include/private/base/SkTemplates.h`: 模板工具。
- `include/private/base/SkTDArray.h`: 动态数组。
- `src/base/SkArenaAlloc.h`: Arena 内存分配器。
- `src/xml/SkXMLParser.h`: XML SAX 解析器基类。
- `src/xml/SkXMLWriter.h`: XML 写入器。
- `include/core/SkStream.h`: 流输入。
- `include/utils/SkParse.h`: 字符串到数值的解析工具。

## 设计模式与设计决策

1. **Arena 分配**: 所有 DOM 数据使用同一个 arena 分配器，支持一次性释放所有内存，避免了逐个释放节点的开销。
2. **链表树结构**: 使用 firstChild/nextSibling 链表而非数组表示树结构，节省了子节点数组的管理开销。
3. **增量解析**: `beginParsing()`/`finishParsing()` 接口支持渐进式 DOM 构建。
4. **SAX 到 DOM 转换**: 内部 `SkDOMParser` 将 SAX 事件流转换为 DOM 树，复用了 SkXMLParser 的解析能力。
5. **反向构建后翻转**: 子节点先反向添加再翻转，避免了在链表头部插入后需要遍历到尾部的开销。

## 性能考量

1. **Arena 分配的高效性**: 分配操作是简单的指针移动，无碎片化问题。
2. **线性属性查找**: 对于属性数量少的 XML 元素，线性扫描比哈希表更高效（减少内存开销和构建成本）。
3. **字符串去重缺失**: 相同的属性名和值会被重复复制，可能增加内存使用。
4. **一次性释放**: `reset()` 可以立即释放整个 DOM 的内存，比逐个节点释放快得多。
5. **内存映射优化**: `build()` 通过底层 expat 可以直接使用内存映射流，减少数据复制。

## 相关文件

- `src/xml/SkXMLParser.h/.cpp`: SAX 解析器基类。
- `src/xml/SkXMLWriter.h/.cpp`: XML 写入器，可从 DOM 树输出。
- `include/utils/SkParse.h`: 字符串解析工具。
- `src/base/SkArenaAlloc.h`: Arena 内存分配器。
- `modules/svg/src/SkSVGDOM.cpp`: SVG DOM 解析器，使用 SkDOM 和 SkXMLParser。
