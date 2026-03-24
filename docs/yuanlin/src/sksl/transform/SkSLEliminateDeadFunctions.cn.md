# SkSLEliminateDeadFunctions

> 源文件: src/sksl/transform/SkSLEliminateDeadFunctions.cpp

## 概述

`EliminateDeadFunctions` 优化器删除程序中未被调用的函数,减少生成代码的大小。通过分析函数调用图,识别并移除无法从入口点到达的函数。

## 架构位置

位于 SkSL 优化流程,在内联和其他优化后执行,清理不再需要的函数。

## 主要功能

### 死函数检测

从入口函数(vertex、fragment、main)开始,标记所有可达函数。未标记的函数即为死函数。

### 删除策略

移除未被调用的函数定义,保留必要的函数声明(如果有外部引用)。

## 设计决策

采用保守策略,确保不删除可能被外部调用的函数。使用 `ProgramUsage` 统计函数调用次数。

## 相关文件

- `src/sksl/analysis/SkSLProgramUsage.h`: 使用统计
- `src/sksl/transform/SkSLTransform.h`: 转换接口
- 优化器在内联后调用此pass
