# 渐变模糊测试

> 源文件: `fuzz/FuzzGradients.cpp`

## 概述

此文件对 Skia 的四种渐变类型进行模糊测试：线性渐变、径向渐变、双点锥形渐变和扫描渐变。每种渐变都测试了颜色数组、位置数组、平铺模式、本地矩阵和全局矩阵的随机组合。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，针对 `include/effects/SkGradient.h`。

## 公共 API 函数

- `DEF_FUZZ(Gradients, fuzz)` - 随机选择一种渐变类型并测试

### 渐变函数
- `fuzzLinearGradient` - 线性渐变
- `fuzzRadialGradient` - 径向渐变
- `fuzzTwoPointConicalGradient` - 双点锥形渐变
- `fuzzSweepGradient` - 扫描渐变

### 辅助函数
- `initGradientParams` - 初始化颜色、位置和平铺模式
- `makeMatrix` - 创建随机 3x3 矩阵
- `fuzz_interp` - 创建随机插值参数
- `logLinearGradient` - 详细日志输出（--verbose 模式）

## 内部实现细节

- 最多 400 个颜色停止点
- 位置数组排序并归一化到 [0, 1]
- 支持三种平铺模式（Clamp/Repeat/Mirror）
- 可选本地矩阵和全局矩阵变换
- 支持预乘插值模式
- Surface 大小 50x50
- 详细的 verbose 日志用于调试发现的问题

## 依赖关系

- `include/effects/SkGradient.h` - 渐变 API
- `src/base/SkTLazy.h` - 惰性初始化

## 设计模式与设计决策

**全参数空间随机化**：每个渐变参数（颜色数量、位置、矩阵、平铺模式）都被独立随机化。

## 性能考量

颜色停止点数量上限 400，Surface 50x50，平衡覆盖和速度。

## 相关文件

- `include/effects/SkGradient.h` - 渐变 API
