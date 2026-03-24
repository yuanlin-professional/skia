# write_to_pdf.cpp - PDF 文档生成示例

> 源文件: `example/external_client/src/write_to_pdf.cpp`

## 概述

`write_to_pdf.cpp` 是一个示例程序，演示了如何使用 Skia 的 PDF 文档生成 API 创建包含文本的 PDF 文件。该示例覆盖了 PDF 生成的完整流程：配置文档元数据、创建 PDF 文档、获取页面 Canvas、绘制文本内容、结束页面和关闭文档。

此示例是将 Skia 用作 PDF 渲染引擎的基本参考，展示了 SkDocument 接口在 PDF 生成场景中的使用。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── write_to_pdf.cpp        <-- 本文件：PDF 生成示例
│   ├── write_text_to_png.cpp   <-- PNG 文本渲染示例
│   └── ...
├── include/docs/
│   ├── SkPDFDocument.h         <-- PDF 文档 API
│   └── SkPDFJpegHelpers.h      <-- PDF JPEG 辅助
└── include/core/
    └── SkDocument.h            <-- 文档基类
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的 PDF API。

### 使用的核心类型
- `SkDocument` - 文档基类，PDF 实现通过 `SkPDF::MakeDocument` 创建
- `SkPDF::Metadata` - PDF 元数据（标题、作者、语言等）
- `SkCanvas` - 页面绘制画布
- `SkFont` / `SkTypeface` / `SkFontMgr` - 字体相关类型

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。用法：`write_to_pdf <name.pdf>`

执行流程：
1. 配置 PDF 元数据（标题、作者、语言、编码质量、JPEG 编解码器）
2. 创建 PDF 文档对象
3. 开始页面（100x50 点大小）
4. 配置字体管理器并匹配 "Roboto" 字体
5. 绘制黄色背景和绿色 "Hello world!" 文本
6. 结束页面并关闭文档

## 内部实现细节

### PDF 元数据配置

```cpp
SkPDF::Metadata metadata;
metadata.fTitle = "Test PDF";
metadata.fAuthor = "Skia Demo Writer";
metadata.fLang = "eng";
metadata.fEncodingQuality = 90;
metadata.jpegDecoder = SkPDF::JPEG::Decode;
metadata.jpegEncoder = SkPDF::JPEG::Encode;
```

元数据对应 PDF 文档的 XMP 信息，其中：
- `fEncodingQuality`：控制嵌入图像的 JPEG 压缩质量（0-100）
- `jpegDecoder`/`jpegEncoder`：JPEG 编解码回调，用于 PDF 中图像的处理

### PDF 文档创建和页面管理

```cpp
sk_sp<SkDocument> pdf = SkPDF::MakeDocument(&output, metadata);
SkCanvas* canvas = pdf->beginPage(100, 50);

// 绘制操作...

pdf->endPage();
pdf->close();
```

`SkDocument` 接口提供了流式的页面创建模式：
- `beginPage(width, height)` 开始新页面并返回该页面的 Canvas
- `endPage()` 结束当前页面
- `close()` 完成文档写入

页面尺寸单位为 PDF 点（1/72 英寸）。

### 字体嵌入

PDF 生成时 Skia 自动处理字体嵌入。通过 `drawString` 绘制的文本会被转换为 PDF 文本操作，相关的字体子集会嵌入到 PDF 文件中。

### 平台字体管理器

```cpp
#if defined(SK_FONTMGR_FONTCONFIG_AVAILABLE) && defined(SK_TYPEFACE_FACTORY_FREETYPE)
    mgr = SkFontMgr_New_FontConfig(nullptr, SkFontScanner_Make_FreeType());
#elif defined(SK_FONTMGR_CORETEXT_AVAILABLE)
    mgr = SkFontMgr_New_CoreText(nullptr);
#endif
```

与其他文本示例一样，通过条件编译选择平台字体管理器。

## 依赖关系

- **Skia 核心**：`SkDocument`, `SkCanvas`, `SkFont`, `SkTypeface`, `SkFontMgr`, `SkPaint`, `SkStream`
- **PDF 模块**：`SkPDFDocument.h`, `SkPDFJpegHelpers.h`
- **平台字体**（条件编译）：`SkFontMgr_fontconfig.h` + `SkFontScanner_FreeType.h`（Linux）, `SkFontMgr_mac_ct.h`（macOS）

## 设计模式与设计决策

1. **SkDocument 抽象**：PDF 生成通过 `SkDocument` 接口实现，用户通过标准的 `SkCanvas` API 绘制内容。同样的 Canvas 代码可以用于 PNG、SVG 或 PDF 输出，只需切换 Document 实现。

2. **JPEG 编解码注入**：通过 `metadata.jpegDecoder/jpegEncoder` 回调注入 JPEG 处理能力，避免 PDF 模块直接依赖 JPEG 库。

3. **流式写入**：PDF 数据通过 `SkFILEWStream` 流式写入文件，不需要将整个 PDF 缓存在内存中。

4. **自动字体子集化**：Skia 的 PDF 生成器自动提取并嵌入所需的字体子集，减小输出文件大小。

## 性能考量

- **字体子集化开销**：在 `close()` 时进行字体子集化和 PDF 结构写入，是主要的计算开销。
- **流式输出**：PDF 数据流式写入文件，内存使用量与页面复杂度相关而非文档总大小。
- **JPEG 编码质量**：`fEncodingQuality = 90` 在图像质量和文件大小之间取得平衡。更低的值会减小文件大小但降低图像质量。
- **单页文档**：此示例仅有一页，多页文档需要重复 `beginPage`/`endPage` 周期。

## 相关文件

- `include/docs/SkPDFDocument.h` - PDF 文档 API
- `include/docs/SkPDFJpegHelpers.h` - PDF JPEG 辅助函数
- `include/core/SkDocument.h` - 文档基类
- `example/external_client/src/write_text_to_png.cpp` - 类似的 PNG 输出示例
- `example/external_client/src/shape_text.cpp` - 更高级的文本排版示例
