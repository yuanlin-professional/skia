# SkSLHoistSwitchVarDeclarationsAtTopLevel.md

> 源文件: src/sksl/transform/SkSLHoistSwitchVarDeclarationsAtTopLevel.cpp

## 概述

将 switch 语句顶层的变量声明提升到 switch 之前,避免某些后端(如 GLSL ES2)的作用域问题。

## 架构位置

代码生成前的兼容性转换,针对旧版 GLSL 的限制。

## 主要功能

### 模式识别

识别直接位于 switch case 标签下的变量声明。

### 提升策略

将变量声明移到 switch 语句之前,保留原位置的赋值语句。

## 设计决策

只提升顶层声明,不影响嵌套块中的变量。保持语义等价,通过拆分声明和初始化实现。

## 相关文件

- `src/sksl/ir/SkSLSwitchStatement.h`: Switch 语句
- `src/sksl/ir/SkSLVarDeclarations.h`: 变量声明
- GLSL ES2 代码生成器
