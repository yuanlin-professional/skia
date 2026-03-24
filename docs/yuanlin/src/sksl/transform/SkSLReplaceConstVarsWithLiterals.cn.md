# SkSLReplaceConstVarsWithLiterals

> 源文件: src/sksl/transform/SkSLReplaceConstVarsWithLiterals.cpp

## 概述

将 `const` 变量的引用替换为其字面量值,实现编译时常量传播。减少变量查找开销,暴露更多优化机会。

## 架构位置

常量折叠优化的一部分,在早期优化阶段执行。

## 主要功能

### 常量识别

找到所有用编译时常量初始化的 `const` 变量。

### 替换策略

将变量引用直接替换为字面量,删除不再需要的变量声明。

## 设计决策

只处理简单的字面量,复杂常量表达式留给常量折叠器。支持迭代传播(替换后可能产生新的常量)。

## 相关文件

- `src/sksl/SkSLConstantFolder.h`: 常量折叠
- `src/sksl/ir/SkSLVariableReference.h`: 变量引用
- `src/sksl/ir/SkSLLiteral.h`: 字面量
