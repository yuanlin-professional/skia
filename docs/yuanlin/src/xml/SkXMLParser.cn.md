# SkXMLParser - XML 解析器

> 源文件:
> - `src/xml/SkXMLParser.h`
> - `src/xml/SkXMLParser.cpp`

## 概述

SkXMLParser 是 Skia 中基于 SAX (Simple API for XML) 模式的 XML 解析器。它使用 expat 库作为底层解析引擎，通过回调函数将 XML 元素、属性和文本事件分发给子类处理。该模块是 Skia 的 SVG 解析、DOM 构建等 XML 处理功能的基础。

## 架构位置

```
Skia XML 子系统
├── SkXMLParser (本模块 - SAX 式解析)
│   ├── SkDOMParser (构建 DOM 树)
│   └── SVG 解析器
├── SkDOM (DOM 树)
├── SkXMLWriter (XML 写入)
└── expat (底层 XML 解析库)
```

## 主要类与结构体

### `SkXMLParserError`
- 封装 XML 解析错误信息。
- **成员变量**:
  - `fCode` (ErrorCode): 错误代码枚举。
  - `fLineNumber` (int): 错误发生的行号。
  - `fNativeCode` (int): expat 原生错误代码。
  - `fNoun` (SkString): 错误相关的名词（元素名、属性名等）。
- **ErrorCode 枚举**: `kNoError`, `kEmptyFile`, `kUnknownElement`, `kUnknownAttributeName`, `kErrorInAttributeValue`, `kDuplicateIDs`, `kUnknownError`。

### `SkXMLParser`
- SAX 式 XML 解析器基类。
- **成员变量**:
  - `fParser` (void*): 内部使用的解析器状态（实际类型为 `ParsingContext*`）。
  - `fError` (SkXMLParserError*): 可选的错误接收器。

### `ParsingContext` (内部结构)
- 连接 expat 回调和 SkXMLParser 的上下文。
- 管理文本缓冲，将分散的文本事件合并后再分发。
- 使用 `SkAutoTCallVProc` 自动释放 `XML_Parser`。

## 公共 API 函数

### SkXMLParser 解析方法
```cpp
bool parse(const char doc[], size_t len);
bool parse(SkStream& docStream);
bool parse(const SkDOM&, const SkDOMNode*);
```
- **功能**: 从字符串、流或 DOM 树解析 XML。
- **返回值**: 成功返回 true，失败返回 false。

### 受保护的虚回调方法
```cpp
virtual bool onStartElement(const char elem[]);
virtual bool onAddAttribute(const char name[], const char value[]);
virtual bool onEndElement(const char elem[]);
virtual bool onText(const char text[], int len);
```
- 子类覆盖这些方法来处理 XML 事件。
- 默认实现均返回 false。

### 公共事件分发方法
```cpp
bool startElement(const char elem[]);
bool addAttribute(const char name[], const char value[]);
bool endElement(const char elem[]);
bool text(const char text[], int len);
```
- 由 expat 回调或 `SkXMLParserWriter` 调用，转发到对应的 `on*` 虚方法。

### SkXMLParserError 方法
- `getErrorCode()`: 获取错误代码。
- `getErrorString(SkString*)`: 获取格式化的错误描述字符串。
- `getLineNumber()`: 获取错误行号。
- `hasError()`: 判断是否有错误。
- `reset()`: 重置错误状态。

## 内部实现细节

### expat 集成
`parse(SkStream&)` 方法的核心流程：
1. 创建 `ParsingContext`，内含 expat `XML_Parser`。
2. 使用 Skia 的内存分配器 (`sk_malloc_throw`, `sk_realloc_throw`, `sk_free`) 初始化 expat。
3. 设置 hash salt 防止 DOS 攻击（使用栈地址的哈希）。
4. 注册四个 expat 回调：`start_element_handler`, `end_element_handler`, `text_handler`, `entity_decl_handler`。
5. **两种解析模式**:
   - 内存映射流: 直接传递 `getMemoryBase()` 指针给 `XML_Parse`。
   - 普通流: 使用 4096 字节的缓冲区循环调用 `XML_ParseBuffer`。

### 文本合并
expat 可能将连续文本分多次回调。`ParsingContext` 使用 `std::vector<char>` 缓冲文本，在下一个元素事件前通过 `flushText()` 一次性分发合并后的文本。

### 实体声明安全
`entity_decl_handler` 回调在检测到实体声明时调用 `XML_StopParser` 停止解析，防止内部实体扩展导致的安全问题 (参见 expat CVE-2013-0340)。

### DOM 解析
`parse(const SkDOM&, const SkDOMNode*)` 方法递归遍历 DOM 树，将其事件序列化为 SAX 事件流，可用于 DOM 到 DOM 的转换。

## 依赖关系

- `<expat.h>`: expat XML 解析库。
- `include/core/SkStream.h`: 流输入。
- `include/core/SkString.h`: 字符串。
- `include/private/base/SkTemplates.h`: `SkAutoTCallVProc` 自动清理。
- `include/private/base/SkTo.h`: 安全类型转换。

## 设计模式与设计决策

1. **SAX 模式**: 基于事件的解析，无需在内存中构建完整树结构，适合大文档。
2. **模板方法模式**: 基类驱动解析流程，子类通过覆盖 `on*` 方法处理具体事件。
3. **自定义内存管理**: expat 使用 Skia 的内存分配器，确保内存跟踪和错误处理的一致性。
4. **安全防护**: 禁用实体处理以防止 XML bomb 攻击；使用地址 hash 作为 seed 防止哈希碰撞 DOS。

## 性能考量

1. **零拷贝路径**: 内存映射流直接传递指针给 expat，避免数据复制。
2. **缓冲读取**: 非内存映射流使用 4096 字节的缓冲区分块读取。
3. **文本合并**: 避免对碎片化的文本事件产生多次回调开销。
4. **expat 效率**: expat 是经过高度优化的 C 库，解析速度快且内存使用低。

## 相关文件

- `src/xml/SkDOM.h/.cpp`: 使用 SkXMLParser 构建 DOM 树。
- `src/xml/SkXMLWriter.h/.cpp`: XML 写入器，可通过 `SkXMLParserWriter` 与解析器交互。
- `modules/svg/src/SkSVGDOM.cpp`: SVG DOM 解析器，继承 SkXMLParser。
