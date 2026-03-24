# SkICCPriv

> 源文件: src/encode/SkICCPriv.h

## 概述

`SkICCPriv` 包含 ICC 颜色配置文件处理的内部实用函数,用于编码器嵌入颜色配置信息。提供 ICC 配置文件的生成和序列化功能。

## 架构位置

作为编码器的辅助工具,处理颜色管理相关的元数据。

## 主要功能

- 生成标准 ICC 配置文件(sRGB, Display P3等)
- ICC 配置文件序列化
- 颜色空间转换信息编码

## 设计决策

提供预定义的常用配置文件,避免重复生成。支持自定义配置文件的嵌入。

## 相关文件

- `src/encode/SkPngEncoder.cpp`, `SkJpegEncoder.cpp`: 使用 ICC 配置文件
- `include/core/SkColorSpace.h`: Skia 颜色空间
