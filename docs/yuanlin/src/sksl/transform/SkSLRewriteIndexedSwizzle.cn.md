# SkSLRewriteIndexedSwizzle

> 源文件: src/sksl/transform/SkSLRewriteIndexedSwizzle.cpp

## 概述

将索引访问 swizzle 结果(如 `v.xyz[i]`)重写为直接索引向量(如 `v[remap[i]]`),避免某些后端的临时变量开销。

## 架构位置

代码生成前的优化,针对特定后端(如 Metal)提升性能。

## 主要功能

### 模式检测

识别 `IndexExpression` 的基础是 `Swizzle` 的情况。

### 重写策略

计算索引映射,将 `swizzle[index]` 转换为 `base[swizzle_component[index]]`。

## 设计决策

只在索引为常量或后端支持复杂索引时应用。保持边界检查的安全性。

## 相关文件

- `src/sksl/ir/SkSLSwizzle.h`: Swizzle 表达式
- `src/sksl/ir/SkSLIndexExpression.h`: 索引表达式
- Metal 代码生成器
