# SkSLEliminateDeadLocalVariables

> 源文件: src/sksl/transform/SkSLEliminateDeadLocalVariables.cpp

## 概述

删除从未被读取的局部变量,清理优化后产生的无用声明。分析变量的写入和读取,移除只写不读的变量。

## 架构位置

在其他优化(如常量折叠、内联)后执行,清理中间产物。

## 主要功能

### 活跃性分析

跟踪每个局部变量的读写情况,使用 `ProgramUsage` 统计。

### 删除条件

变量满足以下条件被删除:
- 只有写入,没有读取
- 写入的表达式无副作用
- 不是函数参数

## 设计决策

保守处理有副作用的初始化表达式。支持迭代删除(删除后可能产生新的死变量)。

## 相关文件

- `src/sksl/analysis/SkSLProgramUsage.h`: 使用统计
- `src/sksl/ir/SkSLVarDeclarations.h`: 变量声明
- 与死代码消除协同工作
