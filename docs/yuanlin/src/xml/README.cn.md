# src/xml - XML 解析与写入模块

## 概述

`src/xml` 目录是 Skia 图形库中负责 XML 文档解析与生成的核心模块。该模块提供了一套完整的 XML 处理基础设施，包括 XML 解析器（Parser）、XML 写入器（Writer）以及 DOM（文档对象模型）树的构建与遍历功能。这些功能是 Skia SVG 渲染和文档生成管线中不可或缺的基础组件。

Skia 的 XML 模块采用了经典的 SAX（Simple API for XML）事件驱动模型作为底层解析机制，同时在此基础上构建了轻量级的 DOM 树结构。底层解析依赖于广泛使用的 expat 库，通过回调函数将 XML 解析事件转发给 Skia 内部的处理逻辑。这种分层设计使得模块既能高效处理大型 XML 文档，又能方便地进行 DOM 树操作。

XML 写入功能通过抽象基类 `SkXMLWriter` 及其子类提供，支持将 XML 数据输出到流（Stream）或转发给另一个解析器。写入器会自动处理 XML 标记转义、缩进格式化等细节，确保生成的 XML 文档符合规范。该模块被 SVG 导出（`src/svg`）和 SVG 渲染（`modules/svg`）等上层模块广泛使用。

整个 XML 模块通过 `SkArenaAlloc` 内存分配器来管理 DOM 节点和字符串的内存，避免了大量的小对象堆分配，提升了解析大型 XML 文档时的性能表现。

## 架构图

```
+------------------------------------------------------------------+
|                        外部调用层                                 |
|  (src/svg, modules/svg, 测试代码等)                               |
+------------------------------------------------------------------+
        |                    |                    |
        v                    v                    v
+----------------+  +------------------+  +------------------+
|    SkDOM       |  |  SkXMLParser     |  |  SkXMLWriter     |
| (DOM树构建/    |  | (SAX事件驱动     |  | (XML输出抽象     |
|  遍历/查询)    |  |  解析器基类)     |  |  基类)           |
+-------+--------+  +--------+---------+  +--------+---------+
        |                    |                      |
        v                    |                      v
+----------------+           |            +------------------+
|  SkDOMParser   |           |            | SkXMLStream-     |
| (DOM解析器     |           |            |   Writer         |
|  继承自        |           |            | (输出到流)       |
|  SkXMLParser)  |           |            +------------------+
+----------------+           |            +------------------+
                             |            | SkXMLParser-     |
                             v            |   Writer         |
                    +------------------+  | (输出到解析器)   |
                    |     expat库      |  +------------------+
                    | (底层XML解析引擎)|
                    +------------------+
```

## 目录结构

```
src/xml/
  BUILD.bazel          -- Bazel 构建配置，定义 xml 库目标
  SkDOM.h              -- SkDOM 类声明，DOM 树管理接口
  SkDOM.cpp            -- SkDOM 类实现，包含 SkDOMParser、SkDOMNode、SkDOMAttr 定义
  SkXMLParser.h        -- SkXMLParser 基类声明，SAX 事件接口
  SkXMLParser.cpp      -- SkXMLParser 实现，基于 expat 库的 XML 解析
  SkXMLWriter.h        -- SkXMLWriter 抽象基类及子类声明
  SkXMLWriter.cpp      -- SkXMLWriter 及其子类实现
```

## 关键类与函数

### SkXMLParser（XML 解析器基类）
- **位置**: `src/xml/SkXMLParser.h`
- **职责**: 提供 SAX 风格的 XML 解析事件回调接口
- **核心方法**:
  - `parse(SkStream&)` -- 从流解析 XML 文档
  - `parse(const char*, size_t)` -- 从内存缓冲区解析
  - `onStartElement(const char[])` -- 元素开始回调（子类重写）
  - `onEndElement(const char[])` -- 元素结束回调（子类重写）
  - `onAddAttribute(const char[], const char[])` -- 属性回调（子类重写）
  - `onText(const char[], int)` -- 文本内容回调（子类重写）
- **实现细节**: 使用 expat 库作为底层解析引擎，通过 `ParsingContext` 结构体将 expat 回调桥接到 Skia 的 `SkXMLParser` 虚函数调用

### SkXMLParserError（解析错误信息）
- **位置**: `src/xml/SkXMLParser.h`
- **职责**: 封装 XML 解析过程中的错误信息
- **错误类型**: `kNoError`, `kEmptyFile`, `kUnknownElement`, `kUnknownAttributeName`, `kErrorInAttributeValue`, `kDuplicateIDs`, `kUnknownError`

### SkDOM（文档对象模型）
- **位置**: `src/xml/SkDOM.h`, `src/xml/SkDOM.cpp`
- **职责**: 将 XML 文档解析为内存中的树形结构，并提供遍历和查询 API
- **核心方法**:
  - `build(SkStream&)` -- 从流构建 DOM 树，返回根节点
  - `getRootNode()` -- 获取根节点
  - `getFirstChild(node, name)` -- 获取第一个子节点（可按名称过滤）
  - `getNextSibling(node, name)` -- 获取下一个兄弟节点
  - `findAttr(node, name)` -- 查找属性值
  - `findS32()`, `findScalars()`, `findHex()`, `findBool()` -- 类型化属性查询
  - `beginParsing()` / `finishParsing()` -- 增量式解析支持

### SkDOMNode / SkDOMAttr（DOM 节点结构）
- **位置**: `src/xml/SkDOM.cpp`（内部结构体）
- **SkDOMNode 字段**: `fName`, `fFirstChild`, `fNextSibling`, `fAttrs`, `fAttrCount`, `fType`
- **SkDOMAttr 字段**: `fName`, `fValue`
- **设计特点**: 使用 `SkArenaAllocWithReset` 进行内存管理，子节点通过链表连接

### SkDOMParser（DOM 解析器，内部类）
- **位置**: `src/xml/SkDOM.cpp`
- **职责**: 继承 `SkXMLParser`，在 SAX 事件中构建 DOM 树
- **实现细节**: 使用父节点栈（`fParentStack`）跟踪嵌套层级，子节点在 `onEndElement` 中反转链表顺序以恢复文档顺序

### SkXMLWriter（XML 写入器抽象基类）
- **位置**: `src/xml/SkXMLWriter.h`
- **核心方法**:
  - `startElement()` / `endElement()` -- 元素标签操作
  - `addAttribute()` -- 添加属性
  - `addText()` -- 添加文本内容
  - `writeDOM()` -- 从 DOM 树写入 XML
  - `flush()` -- 刷新所有未关闭的元素
  - `writeHeader()` -- 写入 XML 声明头

### SkXMLStreamWriter（流输出写入器）
- **位置**: `src/xml/SkXMLWriter.h`
- **职责**: 将 XML 输出到 `SkWStream`
- **特性**: 支持 `kNoPretty_Flag` 标志控制是否格式化输出（缩进和换行）

### SkXMLParserWriter（解析器桥接写入器）
- **位置**: `src/xml/SkXMLWriter.h`
- **职责**: 将 XML 写入操作转发为 `SkXMLParser` 的回调调用，实现写入器到解析器的桥接

## 依赖关系

### 外部依赖
- **expat** -- 开源 XML 解析库，提供底层 SAX 解析功能。通过 `XML_ParserCreate_MM` 使用自定义内存分配器（`sk_malloc_throw`, `sk_realloc_throw`, `sk_free`）

### 内部依赖
- `src/base` -- 基础工具（`SkArenaAlloc`, `SkUtils`）
- `src/core` -- 核心类型（`SkStream`, `SkString`, `SkScalar`）
- `include/utils/SkParse.h` -- 字符串到数值的转换工具

### 被依赖
- `src/svg` -- SVG 导出模块使用 `SkXMLWriter` 生成 SVG 标记
- `modules/svg` -- SVG 渲染模块使用 `SkDOM` 和 `SkXMLParser` 解析 SVG 文件

## 设计模式分析

### 模板方法模式（Template Method）
`SkXMLParser` 定义了解析框架，子类通过重写 `onStartElement`、`onEndElement`、`onAddAttribute`、`onText` 等虚函数来定制行为。`SkDOMParser` 利用此模式在解析事件中构建 DOM 树。

### 策略模式（Strategy）
`SkXMLWriter` 定义了 XML 输出的抽象接口，`SkXMLStreamWriter` 和 `SkXMLParserWriter` 分别实现了不同的输出策略（流输出 vs 解析器转发）。

### 访问者模式（Visitor）
`walk_dom` 和 `write_dom` 函数实现了对 DOM 树的递归遍历，将遍历逻辑与具体操作解耦。

### 竞技场分配（Arena Allocation）
DOM 节点和字符串通过 `SkArenaAllocWithReset` 统一分配，当 DOM 被销毁或重置时，所有内存一次性释放，避免了逐个对象释放的开销。

## 数据流

```
XML 输入数据
    |
    v
SkXMLParser::parse(SkStream&)
    |
    v
expat 库解析 (XML_Parse / XML_ParseBuffer)
    |
    v
expat 回调 (start_element_handler, end_element_handler, text_handler)
    |
    v
ParsingContext::flushText() --> SkXMLParser::startElement/endElement/text
    |
    v
SkDOMParser (继承 SkXMLParser) 的回调实现
    |
    v
SkDOMParser::flushAttributes() --> 创建 SkDOMNode/SkDOMAttr (SkArenaAlloc)
    |
    v
SkDOM 树结构 (fRoot -> fFirstChild -> fNextSibling)
    |
    v
DOM 查询 API (getFirstChild, findAttr, findS32 等)
    |
    v
上层消费者 (SVG 渲染、属性提取等)
```

### XML 写入数据流
```
SkCanvas 绘制调用 (如 SkSVGDevice)
    |
    v
SkXMLWriter::startElement / addAttribute / endElement
    |
    v
SkXMLStreamWriter --> SkWStream (文件/内存流)
    或
SkXMLParserWriter --> SkXMLParser (另一个解析器)
```

## 相关文档与参考

- **expat 库文档**: https://libexpat.github.io/ -- Skia XML 解析的底层引擎
- **Skia SVG 模块**: `src/svg/` -- XML 模块的主要消费者，用于 SVG 导出
- **Skia SVG 渲染模块**: `modules/svg/` -- 使用 DOM 和 Parser 解析 SVG 文件
- **构建配置**: `src/xml/BUILD.bazel` -- 定义了 `SK_XML` 宏和对 expat 的依赖
- **SkArenaAlloc**: `src/base/SkArenaAlloc.h` -- DOM 节点使用的内存分配器
- **SkParse**: `include/utils/SkParse.h` -- DOM 属性值的数值解析工具
