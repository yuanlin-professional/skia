# docs - 文档输出 API

## 概述

`include/docs` 目录定义了 Skia 文档输出框架的公共 API。该框架支持将 Skia 的绘制
操作序列化为多种文档格式，目前主要支持 PDF、XPS（仅限 Windows）和多图片文档
（SkMultiPictureDocument）三种格式。

PDF 文档支持是该模块最核心和最完善的功能。`SkPDF` 命名空间提供了功能丰富的 PDF
生成能力，包括文档元数据（标题、作者、主题等）、结构化标记（用于 PDF/A 可访问性）、
压缩控制、JPEG 编解码集成、以及线程化输出支持。PDF 输出基于 `SkDocument` 抽象，
通过 `SkCanvas` 接口进行页面绘制，使得 PDF 生成过程与普通绘制操作完全一致。

`SkMultiPictureDocument` 是 Skia 自定义的多页文档格式，基于 `SkPicture` 序列化
机制。它可以将多个 SkPicture（每个代表一页）保存为一个文件，并支持读回。这种格式
主要用于 Skia 内部测试和调试场景，特别是在记录和回放绘制操作时非常有用。

XPS 文档输出是 Windows 平台特有的功能，通过 `SkXPS::MakeDocument` 创建，依赖于
Windows 的 `IXpsOMObjectFactory` COM 接口。

`SkPDFJpegHelpers` 提供了 PDF 文档中 JPEG 编解码的便捷集成，将 `SkJpegDecoder`
和 `SkJpegEncoder` 封装为 PDF 元数据中所需的回调函数。

## 架构图

```
+------------------------------------------------------------------+
|                       应用层                                       |
|  使用 SkCanvas 进行绘制，输出为文档格式                              |
+------------------------------------------------------------------+
         |
         v
+-------------------+
|   SkDocument       |     (include/core/SkDocument.h)
|   文档抽象基类      |
|   - beginPage()   |---> 返回 SkCanvas*
|   - endPage()     |
|   - close()       |
+-------------------+
         |
    +----+----+--------------------+
    |         |                    |
    v         v                    v
+--------+ +--------+    +------------------+
| SkPDF  | | SkXPS  |    | SkMultiPicture   |
| PDF    | | XPS    |    | Document         |
| 文档    | | 文档    |    | 多图片文档        |
+--------+ +--------+    +------------------+
| Metadata |  Options |   | Make()           |
|  - 标题   |  - dpi   |   | ReadPageCount()  |
|  - 作者   |  - PNG   |   | Read()           |
|  - 主题   |  编码器   |   +------------------+
|  - 关键字 |          |
|  - DPI   +----------+
|  - PDF/A |
|  - 压缩  |
|  - 结构树 |
|  - JPEG  |
+----------+
    |
    v
+-------------------+
| SkPDF::SetNodeId  |   结构化标记，关联节点与绘制内容
| AttributeList     |   节点属性列表
| StructureElement  |   结构元素树
|   Node            |
+-------------------+
```

## 目录结构

```
include/docs/
  BUILD.bazel               # Bazel 构建配置
  SkPDFDocument.h           # PDF 文档生成 API（元数据/结构树/压缩等）
  SkPDFJpegHelpers.h        # PDF 中 JPEG 编解码的便捷集成
  SkMultiPictureDocument.h  # 多图片文档格式（基于 SkPicture）
  SkXPSDocument.h           # XPS 文档生成（仅 Windows）
```

## 关键类与函数

### SkPDF - PDF 文档生成

**核心函数：**
- `SkPDF::MakeDocument(SkWStream*, const Metadata&)` - 创建 PDF 文档
- `SkPDF::SetNodeId(SkCanvas*, int nodeID)` - 关联结构化标记

**Metadata - PDF 元数据：**
- `fTitle` / `fAuthor` / `fSubject` / `fKeywords` - 文档信息
- `fCreator` / `fProducer` - 生产工具信息
- `fCreation` / `fModified` - 日期时间（`DateTime` 结构体）
- `fRasterDPI` - 光栅化 DPI（默认 72）
- `fPDFA` - 是否生成 PDF/A-2b 合规文档
- `fEncodingQuality` - 图像编码质量（101 为无损）
- `fCompressionLevel` - 压缩级别（None/Low/Average/High）
- `fStructureElementTreeRoot` - 文档结构元素树根节点
- `fOutline` - 文档大纲模式
- `fExecutor` - 多线程执行器（用于并行压缩）
- `jpegDecoder` / `jpegEncoder` - JPEG 编解码回调

**AttributeList - 结构属性：**
- `appendInt()` / `appendFloat()` / `appendName()` - 添加各类型属性
- `appendTextString()` / `appendFloatArray()` / `appendNodeIdArray()` - 复杂属性

**StructureElementNode - 结构元素节点：**
- `fTypeString` - 元素类型（如 "H1"、"P"、"Table" 等）
- `fChildVector` - 子节点列表
- `fNodeId` - 节点标识
- `fAttributes` - 属性列表
- `fAlt` / `fLang` - 替代文本和语言标记

### SkMultiPictureDocument - 多图片文档

- `Make(SkWStream*, const SkSerialProcs*)` - 创建文档写入器
- `ReadPageCount(SkStreamSeekable*)` - 读取页面数量
- `Read(SkStreamSeekable*, SkDocumentPage*, int)` - 读取文档页面
- `SkDocumentPage` 结构体包含 `fPicture`（页面内容）和 `fSize`（页面尺寸）

### SkXPS - XPS 文档（Windows）

- `SkXPS::MakeDocument(SkWStream*, IXpsOMObjectFactory*, Options)` - 创建 XPS 文档
- `Options` 包含 `dpi`、`pngEncoder` 回调和 `allowNoPngs` 开关

### SkPDF::JPEG - JPEG 便捷集成

- `Decode()` - 封装 `SkJpegDecoder::Decode` 的解码回调
- `Encode()` - 封装 `SkJpegEncoder::Encode` 的编码回调
- `MetadataWithCallbacks()` - 返回预配置了 JPEG 回调的 Metadata

## 依赖关系

- **内部依赖**：`include/core`（SkDocument、SkCanvas、SkPicture、SkData 等）
- **内部依赖**：`include/codec`（JPEG 解码器）、`include/encode`（JPEG 编码器）
- **外部依赖**：zlib（PDF 压缩）、HarfBuzz（字体子集化）
- **平台依赖**：Windows COM 接口（XPS 输出）

## 相关文档与参考

- PDF 标准 PDF32000_2008（ISO 32000-1:2008）
- PDF/A-2b 可访问性标准
- XPS 文档格式规范
- SkPicture 序列化格式
- 源码实现位于 `src/pdf/` 目录
