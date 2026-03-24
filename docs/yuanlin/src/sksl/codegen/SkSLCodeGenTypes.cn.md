# SkSLCodeGenTypes

> 源文件: src/sksl/codegen/SkSLCodeGenTypes.h

## 概述

`SkSLCodeGenTypes` 定义代码生成器使用的通用类型别名和枚举,统一不同后端的类型表示。

## 主要内容

### 常见类型定义

可能包含:
- 输出流类型别名
- 代码生成选项结构
- 通用的代码片段类型
- 后端特定的配置枚举

## 设计决策

集中定义共享类型,避免重复定义。简化后端实现,提供统一接口。

## 相关文件

- `SkSLCodeGenerator.h`: 使用这些类型的基类
- 各具体代码生成器实现
