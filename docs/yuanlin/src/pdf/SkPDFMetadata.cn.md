# SkPDFMetadata - PDF 元数据处理模块

> 源文件：
> - `src/pdf/SkPDFMetadata.h`
> - `src/pdf/SkPDFMetadata.cpp`

## 概述

`SkPDFMetadata` 是 Skia PDF 后端中负责处理 PDF 文档元数据的命名空间模块。它提供了创建 PDF 文档信息字典（Document Information Dictionary）、生成唯一文档标识符（UUID）以及构建符合 XMP（Extensible Metadata Platform）标准的元数据对象的功能。该模块确保生成的 PDF 文档包含符合 PDF/A-2b 标准的元数据信息，包括标题、作者、主题、关键词、创建者、生产者以及创建和修改日期等字段。

## 架构位置

`SkPDFMetadata` 位于 Skia PDF 渲染后端（`src/pdf/`）中，属于 PDF 文档生成管线的辅助模块。它被 `SkPDFDocument` 在文档最终写出阶段调用，用于嵌入元数据信息。

```
SkPDFDocument
  └── SkPDFMetadata (元数据生成)
        ├── MakeDocumentInformationDict → PDF Info 字典
        ├── CreateUUID → 文档/实例唯一标识
        ├── MakePdfId → PDF /ID 数组
        └── MakeXMPObject → XMP XML 元数据流
```

## 主要类与结构体

### 命名空间 `SkPDFMetadata`

该模块以命名空间（namespace）形式组织，而非类。包含四个公共静态函数，分别负责不同维度的元数据生成。

### 内部类 `PDFXMLObject`

```cpp
class PDFXMLObject final : public SkPDFObject {
public:
    PDFXMLObject(SkString xml);
    void emitObject(SkWStream* stream) const override;
private:
    const SkString fXML;
};
```

继承自 `SkPDFObject`，用于将 XMP XML 字符串封装为 PDF 流对象。在 `emitObject()` 中生成带有 `/Type /Metadata`、`/Subtype /XML` 标记的 PDF 字典，并以非压缩方式写出 XML 内容（PDF 标准要求 XMP 数据不压缩，以便外部工具通过文本搜索 `<?xpacket` 来提取）。

## 公共 API 函数

### `MakeDocumentInformationDict`

```cpp
std::unique_ptr<SkPDFObject> MakeDocumentInformationDict(const SkPDF::Metadata&);
```

创建 PDF 文档信息字典（对应 PDF 规范中的 Document Information Dictionary）。遍历 `gMetadataKeys` 表中的六个字段（Title、Author、Subject、Keywords、Creator、Producer），将非空字段以文本字符串形式插入字典。同时处理 `CreationDate` 和 `ModDate` 字段，使用 `pdf_date()` 将 `SkPDF::DateTime` 转换为 PDF 日期格式字符串（`D:YYYYMMDDHHmmSS+ZZ'ZZ'`）。

### `CreateUUID`

```cpp
SkUUID CreateUUID(const SkPDF::Metadata&);
```

基于元数据内容和当前时间生成 Version 3 风格的 UUID。使用 MD5 哈希算法，输入包括命名空间字符串 `"org.skia.pdf\n"`、当前毫秒时间戳、当前日期时间、创建/修改时间以及所有元数据文本字段。生成的哈希按照 RFC 4122 标准设置版本号（第 6 字节高 4 位设为 0x3）和变体位（第 8 字节高 2 位设为 0b10）。

### `MakePdfId`

```cpp
std::unique_ptr<SkPDFObject> MakePdfId(const SkUUID& doc, const SkUUID& instance);
```

创建 PDF 文件的 `/ID` 数组，包含两个 16 字节的字节字符串，分别代表文档永久 ID 和实例 ID。该数组用于 PDF 文件的唯一标识。

### `MakeXMPObject`

```cpp
SkPDFIndirectReference MakeXMPObject(const SkPDF::Metadata& metadata,
                                     const SkUUID& doc,
                                     const SkUUID& instance,
                                     SkPDFDocument*);
```

创建符合 XMP 标准的 XML 元数据对象。生成的 XML 包含 RDF/XML 格式的元数据，涵盖 Dublin Core（dc）、XMP 基本（xmp）、XMP Media Management（xmpMM）和 PDF 特定（pdf）命名空间。输出声明符合 PDF/A-2b 标准（`pdfaid:part=2, conformance=B`）。返回间接引用（`SkPDFIndirectReference`），流以非压缩方式写出。

## 内部实现细节

### 日期格式转换

`pdf_date()` 函数将 `SkPDF::DateTime` 转为 PDF 标准日期格式：`D:YYYYMMDDHHmmSS+ZZ'ZZ'`。时区通过 `fTimeZoneMinutes` 字段表示，正值为东时区，负值为西时区。

### XML 转义处理

`escape_xml()` 函数处理 XML 特殊字符的转义：`&` 转为 `&amp;`，`<` 转为 `&lt;`。支持在转义文本前后插入 XML 标签包装。`count_xml_escape_size()` 预先计算转义后的额外字节数以一次性分配正确大小的缓冲区。

### UUID 字符串转换

`uuid_to_string()` 将 16 字节的 UUID 数据转换为标准的 `8-4-4-4-12` 十六进制格式字符串，使用 `hexify()` 辅助函数逐字节转换。

### XMP 模板字符串

`MakeXMPObject` 使用一个包含 11 个 `%s` 占位符的 XML 模板字符串，各占位符通过 `SkStringPrintf` 填充对应的元数据字段。模板遵循 Adobe XMP Core 5.4 格式标准。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkPDFTypes.h` | PDF 基本类型（SkPDFObject, SkPDFDict, SkPDFArray）|
| `SkUUID.h` | UUID 数据结构 |
| `SkPDFDocument.h` | SkPDF::Metadata 结构体定义及文档类 |
| `SkMD5.h` | MD5 哈希算法用于 UUID 生成 |
| `SkTime.h` | 获取当前时间戳 |
| `SkPDFUtils.h` | PDF 工具函数（GetDateTime 等）|
| `SkStream.h` | 流写出支持 |
| `SkString.h` | 字符串操作 |

## 设计模式与设计决策

1. **命名空间而非类**：由于所有函数均为无状态的工厂函数，采用命名空间组织比静态类更加自然。

2. **数据驱动的字段映射**：使用 `gMetadataKeys` 数组将 PDF 键名与 `SkPDF::Metadata` 结构体中的成员指针关联，避免为每个字段编写重复的条件逻辑。

3. **PDF/A-2b 合规性**：XMP 元数据明确声明 `pdfaid:part=2` 和 `pdfaid:conformance=B`，表明目标兼容 PDF/A-2b 存档标准。

4. **非压缩 XMP 流**：根据 PDF 标准要求，XMP 流不进行压缩（`SkPDFSteamCompressionEnabled::No`），以便不理解 PDF 格式的工具也能通过搜索 `<?xpacket` 标记提取元数据。

5. **基于内容的 UUID**：UUID 生成不仅依赖时间戳，还融合了所有元数据内容，使相同元数据在相近时间内产生可区分的标识。

## 性能考量

- XML 转义预先计算额外空间（`count_xml_escape_size`），避免多次内存分配和字符串拼接。
- MD5 哈希运算对于 UUID 生成而言开销极低，适用于文档级别的一次性操作。
- XMP 模板字符串使用 `SkStringPrintf` 一次性格式化，避免逐段拼接的开销。
- 整体模块仅在 PDF 文档写出时调用一次，不构成性能瓶颈。

## 相关文件

- `src/pdf/SkPDFDocument.h` / `src/pdf/SkPDFDocument.cpp` — 调用方，在文档输出时调用元数据生成
- `src/pdf/SkPDFTypes.h` — PDF 对象类型基础设施
- `src/pdf/SkUUID.h` — UUID 数据结构定义
- `include/docs/SkPDFDocument.h` — `SkPDF::Metadata` 结构体的公共定义
- `src/core/SkMD5.h` — MD5 哈希实现
- `src/pdf/SkPDFUtils.h` — PDF 工具函数集合
