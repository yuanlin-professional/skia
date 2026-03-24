# SkXMLWriter - XML 写入器

> 源文件:
> - `src/xml/SkXMLWriter.h`
> - `src/xml/SkXMLWriter.cpp`

## 概述

SkXMLWriter 是 Skia 中用于生成 XML 文档的写入器类层次结构。它提供了一个抽象基类 `SkXMLWriter`，以及两个具体实现：`SkXMLStreamWriter`（写入到 SkWStream 字节流）和 `SkXMLParserWriter`（写入到 SkXMLParser，用于 DOM 转换）。该模块主要用于 SVG 输出和 XML 格式的文档序列化。

## 架构位置

```
Skia XML 子系统
├── SkDOM (DOM 树) <-> SkXMLParser (解析)
│                  <-> SkXMLWriter (本模块 - 写入)
│                       ├── SkXMLStreamWriter (流输出)
│                       └── SkXMLParserWriter (解析器输出)
├── SVG 输出模块
└── SkWStream (字节流)
```

## 主要类与结构体

### `SkXMLWriter` (基类)
- 抽象基类，定义了 XML 写入的通用接口。
- **成员变量**:
  - `fElems` (SkTDArray\<Elem*\>): 元素栈，跟踪嵌套的 XML 元素。
  - `fDoEscapeMarkup` (bool): 是否对属性值中的特殊字符进行转义。
- **内部结构 `Elem`**: 存储元素名称 (`fName`)、是否有子元素 (`fHasChildren`)、是否有文本内容 (`fHasText`)。

### `SkXMLStreamWriter`
- 将 XML 写入到 `SkWStream`，支持格式化输出。
- **标志**: `kNoPretty_Flag` (0x01) - 禁用缩进和换行的紧凑输出。
- **成员**: `fStream` (SkWStream&)、`fFlags` (uint32_t)。

### `SkXMLParserWriter`
- 将 XML 写入到 `SkXMLParser`，实现 DOM 到 DOM 的转换。
- **成员**: `fParser` (SkXMLParser&)。
- 构造时关闭 markup 转义 (`fDoEscapeMarkup = false`)。

## 公共 API 函数

### SkXMLWriter 基类方法
- `startElement(elem)` / `startElementLen(elem, length)`: 开始一个 XML 元素。
- `endElement()`: 结束当前 XML 元素。
- `addAttribute(name, value)`: 添加字符串属性。
- `addS32Attribute(name, value)`: 添加 32 位整数属性。
- `addHexAttribute(name, value, minDigits)`: 添加十六进制属性。
- `addScalarAttribute(name, value)`: 添加浮点数属性。
- `addText(text, length)`: 添加文本内容。
- `writeDOM(dom, node, skipRoot)`: 将 SkDOM 子树写入。
- `flush()`: 关闭所有未关闭的元素。
- `writeHeader()`: 写入 XML 声明头。

### 受保护的虚方法
- `onStartElementLen()`: 处理元素开始。
- `onAddAttributeLen()`: 处理属性添加。
- `onAddText()`: 处理文本添加。
- `onEndElement()`: 处理元素结束。

## 内部实现细节

### 标记转义
`escape_markup` 函数处理 XML 特殊字符的转义：
- `<` -> `&lt;`
- `>` -> `&gt;`
- `&` -> `&amp;`
- 注意：`"` 和 `'` 的转义被注释掉了，未启用。

### SkXMLStreamWriter 输出格式
- 元素以 `<name` 开头，属性以 ` name="value"` 追加。
- 无子元素和文本时使用自闭合标签 `/>`。
- 有子元素时使用 `>...</name>`。
- 缩进使用制表符 (`\t`)，层级等于元素嵌套深度。
- `kNoPretty_Flag` 可禁用所有缩进和换行。

### DOM 递归写入
`writeDOM` 方法使用内部 `write_dom` 函数递归遍历 SkDOM 树：
1. 对于文本节点：直接调用 `addText`。
2. 对于元素节点：调用 `startElement`，遍历属性调用 `addAttribute`，递归处理子节点，最后 `endElement`。
3. `skipRoot` 参数允许跳过根节点本身，只写入其子树。

### 元素栈管理
- `doStart()`: 将新元素压入栈，标记父元素 `fHasChildren = true`。
- `getEnd()`: 弹出栈顶元素。
- `doEnd()`: 删除弹出的元素对象。
- `flush()`: 循环调用 `endElement()` 直到栈为空。

## 依赖关系

- `include/core/SkString.h`: 字符串操作。
- `include/core/SkStream.h`: SkWStream 字节流。
- `include/private/base/SkTDArray.h`: 动态数组。
- `include/private/base/SkTo.h`: 安全类型转换。
- `src/xml/SkDOM.h`: DOM 树结构。
- `src/xml/SkXMLParser.h`: XML 解析器（SkXMLParserWriter 使用）。

## 设计模式与设计决策

1. **模板方法模式**: 基类定义写入流程（转义、栈管理），子类实现具体输出。
2. **流式写入**: 不缓存完整 DOM，而是边构建边输出，适合大文档。
3. **可选格式化**: 通过 `kNoPretty_Flag` 在可读性和文件大小之间选择。
4. **DOM 桥接**: `writeDOM` 方法和 `SkXMLParserWriter` 提供了 DOM 读取和写入之间的桥接。

## 性能考量

1. **最小化缓冲**: 数据直接写入底层流，不需要大量内存缓冲。
2. **元素栈**: 使用动态数组管理栈，支持任意深度嵌套。
3. **转义的两遍处理**: `addAttributeLen` 中的转义先计算额外长度，再一次性分配并填充，避免多次重分配。

## 相关文件

- `src/xml/SkDOM.h/.cpp`: DOM 树结构和操作。
- `src/xml/SkXMLParser.h/.cpp`: XML 解析器。
- `modules/svg/src/SkSVGDevice.cpp`: SVG 输出设备，使用 SkXMLStreamWriter。
- `include/core/SkStream.h`: 字节流接口。
