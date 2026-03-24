# SkImageEncoderPriv

> 源文件: src/encode/SkImageEncoderPriv.h

## 概述

`SkImageEncoderPriv` 包含图像编码的内部定义和工具函数,为各编码器实现提供共享的基础设施。

## 架构位置

作为编码器私有接口的集合,隔离实现细节。

## 主要内容

- 编码选项的内部表示
- 错误处理辅助函数
- 编码进度回调机制
- 内存管理工具

## 设计决策

将通用逻辑提取到共享头文件,减少代码重复。提供类型安全的辅助函数。

## 相关文件

- 所有 `Sk*EncoderImpl.cpp` 文件
- `include/encode/SkEncoder.h`: 公共编码器 API
