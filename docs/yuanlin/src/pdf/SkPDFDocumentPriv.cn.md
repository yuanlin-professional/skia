# SkPDFDocumentPriv

> 源文件: src/pdf/SkPDFDocumentPriv.h

## 概述

`SkPDFDocumentPriv` 包含 PDF 文档生成的内部接口和辅助类,为 `SkPDFDocument` 提供实现细节,包括对象序列化、资源管理和文档结构构建。

## 架构位置

作为 PDF 实现的私有头文件,隔离内部细节与公共 API。

## 主要内容

### 对象序列化器

管理 PDF 对象的序列化和引用解析。

### 资源规范器

去重和规范化资源(字体、图像、图形状态)。

### UUID 生成

为 PDF 文档生成唯一标识符。

## 设计决策

将复杂的实现逻辑封装在私有类中,简化公共 API。提供灵活的扩展点,支持不同的 PDF 特性。

## 相关文件

- `src/pdf/SkPDFDocument.cpp`: 使用这些私有接口
- `src/pdf/SkPDFTypes.h`: PDF 基础类型
- `src/pdf/SkUUID.h`: UUID 定义
