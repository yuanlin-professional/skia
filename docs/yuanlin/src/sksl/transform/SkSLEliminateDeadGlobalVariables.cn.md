# SkSLEliminateDeadGlobalVariables

> 源文件: src/sksl/transform/SkSLEliminateDeadGlobalVariables.cpp

## 概述

删除从未被使用的全局变量,减少着色器的资源占用。分析全局变量的读写,移除完全未使用的变量。

## 架构位置

在所有优化完成后执行,清理不再需要的全局声明。

## 主要功能

### 使用分析

使用 `ProgramUsage` 统计每个全局变量的读写次数。

### 删除条件

全局变量满足以下条件被删除:
- 没有任何读取或写入
- 不是 uniform/in/out 变量(可能被外部访问)
- 不是接口块成员

## 设计决策

保守处理可能被外部引用的变量。不删除 uniform 等输入输出变量,即使程序内部未使用。

## 相关文件

- `src/sksl/analysis/SkSLProgramUsage.h`: 使用统计
- `src/sksl/ir/SkSLGlobalVarDeclaration.h`: 全局变量
- `SkSLEliminateDeadLocalVariables.cpp`: 局部变量版本
