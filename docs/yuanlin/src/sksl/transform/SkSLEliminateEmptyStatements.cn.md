# SkSLEliminateEmptyStatements

> 源文件: src/sksl/transform/SkSLEliminateEmptyStatements.cpp

## 概述

删除程序中的空语句(Nop)和空代码块,清理优化器产生的无用节点,简化 IR 结构。

## 架构位置

作为清理pass,在所有实质性优化完成后执行,准备最终的代码生成。

## 主要功能

### 空语句识别

找出所有 `Nop` 语句和空 `Block`(不包含任何语句的代码块)。

### 删除策略

从语句列表中移除空语句,将空 Block 替换为 Nop 或完全删除。

## 设计决策

保持控制流结构的完整性,某些位置可能需要保留空语句(如 for 循环的空体)。与 `EliminateUnnecessaryBraces` 协同工作。

## 相关文件

- `src/sksl/ir/SkSLNop.h`: Nop 语句
- `src/sksl/ir/SkSLBlock.h`: 代码块
- `src/sksl/ir/SkSLStatement.h`: 语句基类
