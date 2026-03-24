# SkSLFindAndDeclareBuiltinVariables

> 源文件: src/sksl/transform/SkSLFindAndDeclareBuiltinVariables.cpp

## 概述

扫描程序找出使用的内置变量(如 `gl_Position`, `sk_FragCoord`),并在生成代码前声明它们。类似于 `FindAndDeclareBuiltinFunctions`,针对变量。

## 架构位置

代码生成准备阶段,确保所有使用的内置变量已正确声明。

## 主要功能

### 变量扫描

遍历所有变量引用,识别内置变量的使用。

### 声明生成

为每个使用的内置变量生成适当的声明,包括必要的修饰符(如 `in`, `out`)。

## 设计决策

处理不同着色器阶段(vertex、fragment)的特定内置变量。某些后端(如 WGSL)需要显式声明所有内置变量。

## 相关文件

- `src/sksl/SkSLBuiltinVariables.h`: 内置变量定义
- `src/sksl/ir/SkSLVariableReference.h`: 变量引用
- 特定后端的代码生成器
