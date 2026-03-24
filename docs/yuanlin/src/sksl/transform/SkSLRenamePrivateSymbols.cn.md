# SkSLRenamePrivateSymbols

> 源文件: src/sksl/transform/SkSLRenamePrivateSymbols.cpp

## 概述

重命名私有符号(以 `$` 开头)为短名称,减少生成代码的大小。私有符号是编译器内部生成的临时变量和函数。

## 架构位置

代码生成前的最终优化,最小化输出大小。

## 主要功能

### 符号收集

扫描所有以 `$` 开头的符号(变量、函数)。

### 重命名策略

使用短名称(如 `_0`, `_1`)替换长的内部名称,保持唯一性。

## 设计决策

只重命名私有符号,保留用户定义的名称。生成的名称保证不与现有符号冲突。对生成的着色器大小有显著影响。

## 相关文件

- `src/sksl/ir/SkSLVariable.h`: 变量定义
- `src/sksl/ir/SkSLFunctionDeclaration.h`: 函数声明
- `src/sksl/SkSLMangler.h`: 名称修饰
