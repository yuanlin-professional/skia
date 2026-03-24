# SkUUID

> 源文件: src/pdf/SkUUID.h

## 概述

`SkUUID` 表示通用唯一标识符(UUID),用于 PDF 文档的唯一标识和版本追踪。生成符合 RFC 4122 标准的 UUID。

## 架构位置

作为 PDF 元数据的一部分,提供文档的唯一标识。

## 主要功能

### UUID 生成

生成随机 UUID(版本 4)或基于时间的 UUID。

### 格式化

将 UUID 格式化为标准字符串表示(如 `550e8400-e29b-41d4-a716-446655440000`)。

## 设计决策

使用简单的结构体存储 128 位 UUID。提供序列化和反序列化方法。

## 相关文件

- `src/pdf/SkPDFDocumentPriv.h`: 在 PDF 元数据中使用
- `src/pdf/SkPDFMetadata.cpp`: 嵌入 UUID 到文档
