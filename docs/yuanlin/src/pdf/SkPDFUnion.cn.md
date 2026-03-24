# SkPDFUnion

> 源文件: src/pdf/SkPDFUnion.h

## 概述

`SkPDFUnion` 是类型安全的联合体,表示 PDF 对象的各种类型(整数、实数、布尔值、名称、字符串、数组、字典等)。提供统一的接口存储和访问不同类型的 PDF 值。

## 架构位置

作为 PDF 类型系统的基础,被字典、数组和其他复合对象使用。

## 主要内容

### 支持的类型

- 整数 (int)
- 实数 (SkScalar)
- 布尔值 (bool)
- 名称 (Name)
- 字符串 (String)
- 对象引用 (ObjRef)
- 数组 (Array)
- 字典 (Dict)

### 类型安全

使用枚举标记类型,提供类型检查的访问器。

## 设计决策

避免虚函数开销,使用标记联合体。支持原地构造,减少内存分配。提供流式序列化接口。

## 相关文件

- `src/pdf/SkPDFTypes.h`: PDF 基础类型定义
- `src/pdf/SkPDFDocument.cpp`: 使用 SkPDFUnion 构建文档
