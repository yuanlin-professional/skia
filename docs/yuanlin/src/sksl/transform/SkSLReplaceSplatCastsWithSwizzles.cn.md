# SkSLReplaceSplatCastsWithSwizzles

> 源文件: src/sksl/transform/SkSLReplaceSplatCastsWithSwizzles.cpp

## 概述

将 splat 类型转换(如 `vec4(x)`)替换为等效的 swizzle 操作(如 `x.xxxx`),在某些后端生成更高效的代码。

## 架构位置

作为代码生成前的优化pass,简化表达式形式。

## 主要功能

### 模式识别

识别形如 `vecN(scalar)` 的构造器,其中 scalar 是单一标量值。

### 替换策略

将构造器替换为 `scalar.xxxx` 形式的 swizzle,减少构造开销。

## 设计决策

仅在后端支持且有性能优势时启用。保持语义等价性,只改变表达形式。

## 相关文件

- `src/sksl/ir/SkSLConstructorSplat.h`: Splat 构造器
- `src/sksl/ir/SkSLSwizzle.h`: Swizzle 表达式
- GLSL/Metal 代码生成器
