# FuzzCubicRoots (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzCubicRoots.cpp

## 概述

`FuzzCubicRoots.cpp` 测试三次方程求根算法,用于曲线求交、碰撞检测和几何分析。三次方程求根是计算机图形学中的基础运算,涉及复杂的数值分析。

## 架构位置

测试 `src/pathops/` 中的三次方程求根实现。

## 主要类与结构体

**LLVMFuzzerTestOneInput**:
- 最大输入 `4 * sizeof(double)` (32 字节)
- 对应三次方程 ax³ + bx² + cx + d = 0 的四个系数

**fuzz_CubicRoots** (外部定义):
- 解析四个 double 系数
- 调用 Skia 的三次求根算法
- 验证根的正确性(代入原方程验证)

## 内部实现细节

测试涵盖:
- **普通情况**: 三个实根、一个实根两个复根
- **重根**: 二重根、三重根
- **退化情况**: 最高次系数为零(降为二次/一次)
- **极端值**: 巨大或微小的系数
- **数值精度**: 浮点误差累积

### 三次方程求解方法

Skia 可能使用:
- **Cardano 公式**: 精确代数解
- **牛顿法**: 数值迭代
- **分解法**: 因式分解

## 依赖关系

- `src/pathops/SkPathOpsCubic.cpp`: 三次曲线相关算法
- `src/pathops/SkPathOpsTypes.h`: 数值类型定义

## 设计模式与设计决策

**严格输入验证**: 只接受精确 32 字节输入,确保数据对应四个 double。

## 性能考量

- **算法选择**: 不同方法的精度和速度权衡
- **数值稳定性**: 避免灾难性抵消
- **特殊情况优化**: 重根和退化情况的快速路径

## 相关文件

- `fuzz/FuzzCubicRoots.cpp`: 独立 fuzzer 版本
- `tests/PathOpsCubicTest.cpp`: 单元测试
- `src/pathops/SkPathOpsCubic.h`: 三次曲线接口

该 fuzzer(2023 年添加)专注于验证三次求根的数值正确性和稳定性。
