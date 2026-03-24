# SkPDFDocument

> 源文件: src/pdf/SkPDFDocument.cpp

## 概述

`SkPDFDocument` 实现 PDF 文档的创建和序列化,是 Skia PDF 后端的核心类。管理 PDF 对象、页面、资源字典和文档结构,将 Skia 绘图操作转换为 PDF 格式输出。

## 架构位置

作为 SkDocument 的 PDF 实现,连接 Skia 绘图 API 和 PDF 文件格式。

## 主要功能

- PDF 对象管理和引用
- 页面流生成
- 字体和图像资源嵌入
- PDF 文档结构树构建
- 多页文档支持
- 元数据设置(标题、作者等)

## 设计决策

采用流式写入,减少内存占用。支持 PDF/A 等标准。延迟对象序列化,优化交叉引用表。

## 相关文件

- `include/docs/SkPDFDocument.h`: 公共 API
- `src/pdf/SkPDFDocumentPriv.h`: 内部实现
- `src/pdf/SkPDFDevice.h`: PDF 绘图设备
- `src/pdf/SkPDFGraphicState.h`: 图形状态
