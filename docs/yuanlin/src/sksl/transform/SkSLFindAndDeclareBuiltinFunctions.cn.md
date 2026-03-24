# SkSLFindAndDeclareBuiltinFunctions

> 源文件: src/sksl/transform/SkSLFindAndDeclareBuiltinFunctions.cpp

## 概述

扫描程序找出使用的内置函数,并在生成代码前声明它们。某些后端需要显式声明所有使用的内置函数。

## 架构位置

代码生成准备阶段,在最终输出前确保所有依赖已声明。

## 主要功能

### 函数扫描

遍历所有函数调用,收集内置函数的引用。

### 声明生成

为每个使用的内置函数生成适当的声明语句。

## 设计决策

只声明实际使用的函数,避免不必要的代码膨胀。处理函数重载,选择正确的签名。

## 相关文件

- `src/sksl/SkSLBuiltinFunctions.h`: 内置函数定义
- `src/sksl/ir/SkSLFunctionCall.h`: 函数调用
- WGSL 等需要显式声明的后端
