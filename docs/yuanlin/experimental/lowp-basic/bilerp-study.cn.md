# Bilerp Study - 低精度双线性插值研究

> 源文件: `experimental/lowp-basic/bilerp-study.cpp`

## 概述

`bilerp-study.cpp` 是一个实验性研究程序，评估定点数双线性插值（bilinear interpolation）算法的精度。它比较了基于 SSSE3 `mm_mulhrs_epi16` 模拟的定点实现与全精度整数实现在 8 位颜色值四点插值中的误差表现。

## 架构位置

位于 `experimental/lowp-basic/` 目录，属于 Skia 低精度纹理采样管线的前期研究。双线性插值是纹理采样中最常用的操作之一，该研究直接影响 Skia 渲染管线的精度与性能权衡。

## 主要类与结构体

- **`Stats`**: 统计结构体，记录 64 位精度的差异计数、最大/最小偏差和总测试数
  - `log(golden, candidate)`: 记录单次测试结果
  - `print()`: 输出统计摘要

## 公共 API 函数

- `main()`: 依次运行两种双线性插值方法的测试

## 内部实现细节

1. **`golden_bilerp`**: 单精度浮点参考实现（有舍入问题）
2. **`golden_bilerp2`**: 双精度浮点参考实现，作为真正的黄金标准
   - 使用 double 避免低位舍入误差
   - 先沿 x 方向插值 top/bottom，再沿 y 方向插值
3. **`full_res_bilerp`**: 全精度 64 位整数实现
   - 使用 65536 级量化步长
   - 中间结果在 64 位空间计算，最终 32 位右移
4. **`bilerp_1`**: 基于 SSSE3 模拟的定点实现
   - 使用平衡区间 [-1,1) 技术（来自 lerp-study 的研究结论）
   - 分两步进行：先水平插值 top/bottom，再垂直插值
   - 使用 `constrained_add` 确保中间结果不溢出
5. **`check_bilerp`**: 模板测试函数，使用"有趣值"子集（边界值和中间值）进行采样测试

## 依赖关系

- `experimental/lowp-basic/QMath.h`: Q15 定点运算和 SIMD 模拟
- C++ 标准库: `<algorithm>`, `<cmath>`, `<cstdio>`, `<cstdint>`

## 设计模式与设计决策

- 使用"有趣值"策略代替完全穷举：选择 44 个关键值（边界附近和中间值），5 个 t 值
- 测试规模为 5 * 5 * 44^4 = ~93M 次，比完全穷举 (256^4) 小得多
- `golden_bilerp2` 使用 double 精度作为参考，避免 float 的累积舍入误差
- 使用 `constrained_add` 在调试模式下检测溢出

## 性能考量

- bilerp_1 的实现目标是可用 SIMD 指令高效并行化
- 两步分离的 x/y 插值允许 SIMD 向量化水平计算
- logPixelScale=7 在精度和寄存器利用率之间取得平衡

## 相关文件

- `experimental/lowp-basic/QMath.h`: 定点数学基础库
- `experimental/lowp-basic/lerp-study.cpp`: 一维线性插值研究（前置研究）
- `experimental/lowp-basic/lowp_experiments.cpp`: SIMD 模拟验证
- `src/core/SkRasterPipeline_opts.h`: 最终的光栅管线实现
