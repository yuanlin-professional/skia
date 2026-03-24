# SkWebpEncoder_none

> 源文件: src/encode/SkWebpEncoder_none.cpp

## 概述

`SkWebpEncoder_none` 是当系统未配置 WebP 编码支持时的空实现。

## 主要功能

提供 WebP 编码 API 的占位符实现,所有函数返回失败。

## 设计决策

允许在没有 libwebp 的环境下编译,保持 API 一致性。

## 相关文件

- `src/encode/SkWebpEncoderImpl.cpp`: 实际的 WebP 编码器
