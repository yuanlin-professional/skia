# SkSLFindAndDeclareBuiltinStructs

> 源文件: src/sksl/transform/SkSLFindAndDeclareBuiltinStructs.cpp

## 概述

扫描程序找出使用的内置结构体类型,并在生成代码前声明它们。确保所有使用的结构体定义在使用前可见。

## 架构位置

代码生成准备阶段,与 `FindAndDeclareBuiltinFunctions` 和 `FindAndDeclareBuiltinVariables` 并列。

## 主要功能

### 结构体扫描

遍历所有类型引用,收集使用的结构体类型。

### 声明生成

为每个使用的内置结构体生成完整的类型定义。

## 设计决策

只声明实际使用的结构体,避免不必要的定义。处理结构体的依赖关系,确保声明顺序正确。

## 相关文件

- `src/sksl/ir/SkSLStructDefinition.h`: 结构体定义
- `src/sksl/ir/SkSLType.h`: 类型系统
- 需要显式声明的代码生成后端
