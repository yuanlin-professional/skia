# SkMultiPictureDocument

> 源文件: src/utils/SkMultiPictureDocument.cpp

## 概述

`SkMultiPictureDocument` 实现多页 Picture 文档格式,将多个 `SkPicture` 序列化到单个文件中。用于 Skia 的测试和调试,支持快速的页面记录和回放。

## 架构位置

作为 `SkDocument` 的一种实现,提供基于 Picture 的文档格式。

## 主要功能

### 多页支持

管理多个页面的 Picture 对象,每个页面独立记录。

### 序列化

将 Picture 序列化为紧凑的二进制格式,支持快速加载。

### 元数据

存储页面尺寸、版本信息等元数据。

## 设计决策

优先考虑速度而非文件大小,适合临时文件和测试。提供简单的格式,易于解析和调试。

## 相关文件

- `include/docs/SkMultiPictureDocument.h`: 公共 API
- `include/core/SkPicture.h`: Picture 定义
- `include/docs/SkDocument.h`: 文档基类
- `tools/skp_parser.cpp`: 解析工具
