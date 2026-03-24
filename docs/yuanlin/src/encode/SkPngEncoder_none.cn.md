# SkPngEncoder_none

> 源文件: src/encode/SkPngEncoder_none.cpp

## 概述

`SkPngEncoder_none` 是当系统未配置 PNG 编码支持时的空实现,与 `SkJpegEncoder_none` 功能类似。

## 主要功能

提供 PNG 编码 API 的空操作实现,所有函数返回失败状态。

## 设计决策

在没有 libpng 依赖时保持编译通过,运行时明确指示不支持 PNG 编码。

## 相关文件

- `src/encode/SkPngEncoderImpl.cpp`: 实际的 PNG 编码器
- 其他 `*_none.cpp` 文件
