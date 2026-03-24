# SkSLEliminateUnreachableCode

> 源文件: src/sksl/transform/SkSLEliminateUnreachableCode.cpp

## 概述

删除永远不会执行的不可达代码,如 `return` 后的语句、常量为假的 `if` 分支等。改善生成代码的质量并减少大小。

## 架构位置

在常量折叠后执行,利用已知的控制流信息移除死代码。

## 主要功能

### 不可达性分析

检测以下不可达模式:
- return/break/continue 后的语句
- 常量条件为假的分支
- 无限循环后的代码

### 删除策略

移除不可达语句,简化控制流结构。可能触发其他优化(如死变量消除)。

## 设计决策

保守处理可能有副作用的代码。支持迭代删除(删除后可能暴露新的不可达代码)。

## 相关文件

- `src/sksl/SkSLAnalysis.h`: 控制流分析
- `src/sksl/ir/SkSLStatement.h`: 语句节点
- 与常量折叠协同工作
