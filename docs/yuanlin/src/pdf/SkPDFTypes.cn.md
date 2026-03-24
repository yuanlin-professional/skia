# SkPDFTypes (PDF 基础类型)

> 源文件:
> - `src/pdf/SkPDFTypes.h`
> - `src/pdf/SkPDFTypes.cpp`

## 概述

`SkPDFTypes` 模块定义了 Skia PDF 生成器中的基础 PDF 对象类型：`SkPDFObject`（抽象基类）、`SkPDFArray`（PDF 数组）和 `SkPDFDict`（PDF 字典）。这些类对应 PDF 规范中的核心数据结构，是构建 PDF 文档所有内容（页面、字体、图像、元数据等）的基石。此外还定义了间接引用类型 `SkPDFIndirectReference`、流输出函数 `SkPDFStreamOut`，以及多种字符串写入工具。

## 架构位置

```
PDF 文档结构:
  SkPDFDocument
    |-- 使用 SkPDFDict 表示页面、字体、图形状态等
    |-- 使用 SkPDFArray 表示坐标数组、颜色数组等
    |-- 使用 SkPDFIndirectReference 建立对象间的引用关系
    |-- 使用 SkPDFStreamOut 输出压缩数据流
```

## 主要类与结构体

### `SkPDFIndirectReference`

PDF 间接对象引用，包含一个整数值。用于在 PDF 对象间建立引用关系。值为 -1 表示无效引用，通过 `explicit operator bool()` 检查有效性。

### `SkPDFParentTreeKey`

PDF 结构树的父树键，类似于 `SkPDFIndirectReference` 但用于标签树结构。

### `SkPDFObject`

所有 PDF 对象的抽象基类。

**关键接口：**
- `emitObject(SkWStream*)` -- 纯虚方法，将对象序列化输出到流中。
- 禁止拷贝和移动。

### `SkPDFArray`

PDF 数组对象，继承自 `SkPDFObject`。最大长度为 8191。

**Append 方法：**
- `appendInt(int32_t)` / `appendBool(bool)` / `appendScalar(SkScalar)`
- `appendColorComponent(uint8_t)` / `appendColorComponentF(float)`
- `appendName(const char[])` / `appendName(SkString)`
- `appendByteString(const char[])` / `appendTextString(const char[])`
- `appendObject(unique_ptr<SkPDFObject>)` / `appendRef(SkPDFIndirectReference)`

### `SkPDFOptionalArray`

特殊数组，当只有一个元素时不输出数组语法。用于 PDF 规范中的 "or an array" 场景。

### `SkPDFDict`

PDF 字典对象，继承自 `SkPDFObject`。

**Insert 方法：**
- `insertBool/Int/Scalar(key, value)` -- 插入基本类型
- `insertName(key, nameValue)` -- 插入名称
- `insertByteString/TextString(key, value)` -- 插入字符串
- `insertObject(key, unique_ptr<SkPDFObject>)` -- 插入子对象
- `insertRef(key, SkPDFIndirectReference)` -- 插入间接引用
- `insertColorComponentF(key, value)` -- 插入颜色分量
- `insertUnion(key, SkPDFUnion&&)` -- 插入联合类型

## 公共 API 函数

### 工厂函数

- **`SkPDFMakeArray(args...)`** -- 可变参数模板函数，创建并填充 PDF 数组。
- **`SkPDFMakeDict(type)`** -- 创建 PDF 字典，可选地设置 `/Type` 条目。

### 流输出

- **`SkPDFStreamOut(dict, stream, doc, compress)`** -- 将字典和关联的数据流作为 PDF 流对象输出到文档。支持可选的 deflate 压缩。

### 字符串写入

- **`SkPDFWriteTextString(wStream, cin, len)`** -- 将 UTF-8 文本写为 PDF 文本字符串。
- **`SkPDFWriteByteString(wStream, cin, len)`** -- 将二进制数据写为 PDF 字节字符串。

## 内部实现细节

### PDF 字符串编码

字节字符串有两种编码方式：
- **字面形式** `(...)` -- 使用转义处理特殊字符（`\`, `(`, `)` 和控制字符）
- **十六进制形式** `<...>` -- 每字节编码为两位十六进制数

`write_optimized_byte_string()` 自动选择更短的编码方式。

### PDF 文本字符串编码

文本字符串处理更复杂：
- 如果输入是有效 UTF-8 且所有字符在 PDFDocEncoding 范围内，使用 PDFDocEncoding 字节串
- 否则转换为 UTF-16BE 编码并添加 BOM 标记
- 同样会选择字面形式或十六进制形式中较短的一种

### SkPDFUnion

`SkPDFArray` 和 `SkPDFDict` 内部使用 `SkPDFUnion` 联合类型存储值。`SkPDFUnion` 是一个带标签的联合体，支持以下类型：
- `kInt` -- 32 位整数
- `kBool` -- 布尔值
- `kScalar` -- 浮点数
- `kColorComponent` -- 颜色分量（整数）
- `kColorComponentF` -- 颜色分量（浮点）
- `kRef` -- 间接引用
- `kName` / `kNameSkS` -- PDF 名称（静态/动态字符串）
- `kByteString` / `kByteStringSkS` -- 字节字符串
- `kTextString` / `kTextStringSkS` -- 文本字符串
- `kObject` -- 子 PDF 对象

移动构造通过 placement new 实现，析构通过标签分发处理。

### SkPDFStreamOut

`SkPDFStreamOut` 将字典和数据流组合为 PDF 流对象：
1. 获取流数据的长度
2. 如果启用压缩，使用 deflate 压缩数据
3. 在字典中设置 `/Length` 和可选的 `/Filter /FlateDecode`
4. 通过 `SkPDFDocument::emit` 输出对象

### SK_PDF_MASK_QUALITY

宏定义了 JPEG 编码质量（默认 50），用于模糊阴影等掩码图像。低质量对模糊阴影效果影响不大，但可以显著减小文件大小。

## 依赖关系

**内部依赖：**
- `SkPDFUnion` -- 联合类型基础
- `SkPDFDocument` -- 文档上下文
- `SkDeflate` -- zlib 压缩
- `SkPDFUtils` -- PDF 工具函数
- `SkStreamPriv` -- 流工具

**外部依赖：**
- `SkScalar`, `SkString`, `SkStream` -- Skia 基础类型
- `<vector>`, `<memory>` -- 标准库

## 设计模式与设计决策

1. **类型安全的值插入**：为每种 PDF 值类型提供专门的 append/insert 方法，编译时保证类型正确。

2. **SkPDFUnion 联合存储**：使用带标签的联合体而非 `std::variant`，允许更精细的内存控制和移动语义。

3. **可选数组优化**：`SkPDFOptionalArray` 在单元素时不输出数组括号，节省 PDF 文件空间。

4. **延迟压缩**：`SkPDFStreamOut` 的压缩是可选的，允许调用者在特定场景下跳过压缩。

5. **不可拷贝设计**：`SkPDFObject` 禁止拷贝和移动，强制使用指针/引用，避免对象切片问题。

## 性能考量

- **字符串编码优化**：自动选择字面形式或十六进制形式中较短的一种，减小 PDF 文件大小。
- **数组预分配**：`reserve()` 方法允许预分配数组和字典空间，减少重分配。
- **流式输出**：对象直接序列化到输出流，无需构建中间文本表示。
- **JPEG 掩码压缩**：对模糊阴影掩码使用 JPEG 压缩，显著减小文件大小。

## 相关文件

- `src/pdf/SkPDFUnion.h` -- SkPDFUnion 定义
- `src/pdf/SkPDFDocumentPriv.h` -- PDF 文档内部接口
- `src/pdf/SkPDFUtils.h` -- PDF 工具函数
- `src/pdf/SkDeflate.h` -- zlib 压缩封装
- `include/docs/SkPDFDocument.h` -- PDF 文档公共接口
- `src/pdf/SkPDFFont.h` -- 字体管理（使用 Dict 和 Array）
- `src/pdf/SkPDFDevice.h` -- 绘制设备（使用 Dict 和 Stream）
- `src/pdf/SkPDFTag.h` -- 标签结构（使用 Dict 和 Array）
- `src/pdf/SkPDFGraphicState.h` -- 图形状态（使用 Dict）
- `src/pdf/SkPDFBitmap.h` -- 位图（使用 Stream）
