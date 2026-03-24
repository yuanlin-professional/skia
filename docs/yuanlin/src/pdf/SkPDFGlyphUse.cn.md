# SkPDFGlyphUse

> 源文件: src/pdf/SkPDFGlyphUse.h

## 概述

`SkPDFGlyphUse` 跟踪 PDF 文档中使用的字形集合,用于字体子集化。记录每个字体使用的字形 ID,在文档序列化时只嵌入实际使用的字形,减少文件大小。

## 架构位置

作为 PDF 字体管理的辅助工具,与字体嵌入流程协同工作。

## 主要功能

### 字形追踪

记录每个字体的字形使用情况,使用位集或哈希表存储。

### 子集化支持

为字体子集化提供使用信息,只嵌入必要的字形。

## 设计决策

使用高效的数据结构(位图或稀疏集合)记录字形 ID。支持增量更新,在绘图过程中动态添加字形。

## 相关文件

- `src/pdf/SkPDFFont.h`: PDF 字体处理
- `src/pdf/SkPDFSubsetFont.h`: 字体子集化
- `src/core/SkGlyphSet.h`: Skia 字形集合
