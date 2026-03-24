# SkSLEliminateUnnecessaryBraces

> 源文件: src/sksl/transform/SkSLEliminateUnnecessaryBraces.cpp

## 概述

删除不必要的花括号和嵌套代码块,简化 IR 结构。将单语句的代码块展开,减少嵌套层次。

## 架构位置

作为清理优化,在主要优化完成后执行,改善生成代码的可读性。

## 主要功能

### 模式识别

识别以下可简化的模式:
- 只包含单个语句的 Block
- 嵌套的空 Block
- if/while 的单语句分支

### 展开策略

将单语句 Block 替换为语句本身,保持语义不变。

## 设计决策

保留必要的作用域(有变量声明的 Block)。某些控制流结构需要保留 Block。

## 相关文件

- `src/sksl/ir/SkSLBlock.h`: 代码块
- `src/sksl/ir/SkSLStatement.h`: 语句基类
- 生成更简洁的输出代码
