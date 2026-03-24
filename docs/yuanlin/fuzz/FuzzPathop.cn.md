# 路径操作模糊测试

> 源文件: `fuzz/FuzzPathop.cpp`

## 概述

此文件对 Skia 的路径操作（PathOps）模块进行模糊测试，覆盖路径布尔运算（Op）、路径简化（Simplify）、绕数转换（AsWinding）和紧密边界框计算（ComputeTightBounds）。同时包含 Chromium 兼容的旧版模糊测试目标。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，针对 `include/pathops/SkPathOps.h`。

## 公共 API 函数

- `DEF_FUZZ(Pathop, fuzz)` - 随机选择并执行 5 种路径操作之一
- `DEF_FUZZ(LegacyChromiumPathop, fuzz)` - Chromium 兼容的路径操作测试

### 路径操作类型
- case 0: `SkOpBuilder` 累积多个路径操作并 resolve
- case 1: `Simplify` 简化路径
- case 2: `Op` 两路径布尔运算
- case 3: `AsWinding` 转换填充规则
- case 4: `ComputeTightBounds` 计算紧密边界框

## 内部实现细节

- 使用 `FuzzEvilPath` 生成可能含有极端值的路径
- 支持所有 `SkPathFillType`（非零、奇偶、反转）
- 支持所有 `SkPathOp`（差集、交集、并集、异或、反向差集）
- `BuildPath` 从模糊数据逐字节构建路径，最大化路径变体覆盖
- LegacyChromiumPathop 使用 `SkOpBuilder` 批量添加路径

## 依赖关系

- `include/pathops/SkPathOps.h` - PathOps API
- `src/pathops/SkPathOpsCommon.h` - ComputeTightBounds
- `fuzz/FuzzCommon.h` - FuzzEvilPath

## 设计模式与设计决策

**多策略覆盖**：5 种不同的操作模式确保 PathOps 的每个入口点都被测试。

## 性能考量

最多 20 个路径操作，路径复杂度受模糊数据量限制。

## 相关文件

- `include/pathops/SkPathOps.h` - PathOps API
- `src/pathops/` - PathOps 实现
