# SkSLAddConstToVarModifiers

> 源文件: src/sksl/transform/SkSLAddConstToVarModifiers.cpp

## 概述

为可以标记为 `const` 的变量自动添加 `const` 修饰符。识别初始化后从未被修改的变量,将其标记为常量,暴露更多优化机会。

## 架构位置

早期优化阶段,在常量传播前执行,最大化常量优化的效果。

## 主要功能

### 常量候选识别

找到满足以下条件的变量:
- 有初始值
- 从不作为赋值的左值
- 从不作为 out/inout 参数

### 修饰符添加

将 `ModifierFlag::kConst` 添加到变量的修饰符中。

## 设计决策

采用保守策略,只标记明确不变的变量。为后续的常量折叠和传播提供输入。

## 相关文件

- `src/sksl/ir/SkSLModifierFlags.h`: 修饰符定义
- `src/sksl/analysis/SkSLProgramUsage.h`: 使用分析
- `SkSLReplaceConstVarsWithLiterals.cpp`: 使用 const 信息优化
