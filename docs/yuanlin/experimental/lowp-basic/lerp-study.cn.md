# Lerp Study - 低精度线性插值研究

> 源文件: `experimental/lowp-basic/lerp-study.cpp`

## 概述

`lerp-study.cpp` 是一个实验性研究程序，比较多种定点数（fixed-point）线性插值算法的精度。它测试了 NEON `vqrdmulhq_s16`、SSSE3 `mm_mulhrs_epi16`、全精度整数和平衡区间等不同实现方案在 8 位颜色值插值中的误差表现。

## 架构位置

位于 `experimental/lowp-basic/` 目录，属于 Skia 低精度渲染管线的前期研究。该研究为 Skia 的 SkRasterPipeline 中低精度路径的设计提供了实验数据支持。

## 主要类与结构体

- **`Stats`**: 统计结构体，记录差异计数、最大/最小偏差和总测试数
  - `log(golden, candidate)`: 记录单次测试结果
  - `print()`: 输出统计摘要

## 公共 API 函数

- `main()`: 依次运行四种插值方法的全面测试

## 内部实现细节

1. **golden_lerp**: 浮点参考实现 `(1-t)*a + t*b`
2. **saturating_lerp<logPixelScale>**: 模拟 ARM NEON `vqrdmulhq_s16` 饱和乘法
3. **ssse3_lerp<logPixelScale>**: 模拟 x86 SSSE3 `_mm_mulhrs_epi16`
4. **full_res_lerp**: 使用 32 位整数运算的全精度版本
5. **balanced_lerp<logPixelScale>**: 将 t 参数域从 [0,1) 变换到 [-1,1)，将误差减半
6. **check_lerp**: 模板函数，遍历所有 t (65536 步) x a (0-255) x b (0-255) 的组合进行穷举测试

## 依赖关系

- `experimental/lowp-basic/QMath.h`: Q15 定点数类型和 SIMD 模拟函数
- C++ 标准库: `<algorithm>`, `<cmath>`, `<cstdio>`, `<cstdint>`

## 设计模式与设计决策

- 使用 Q1.15 定点格式（`logPixelScale = 7`）模拟 8 位像素在 SIMD 寄存器中的表示
- 穷举测试策略：遍历所有可能的 (t, a, b) 组合以获得完整的误差统计
- 参数域变换技术：balanced_lerp 将 t 映射到 [-1,1) 来减少乘法舍入偏差

## 性能考量

- 测试本身是 O(65536 * 256 * 256) 的穷举搜索，约 4.3 亿次测试
- 研究目的是找到精度与 SIMD 吞吐量的最佳平衡点
- 最终选择的算法将应用于每像素的颜色混合运算中

## 相关文件

- `experimental/lowp-basic/QMath.h`: Q15 定点数学运算库
- `experimental/lowp-basic/bilerp-study.cpp`: 双线性插值的类似研究
- `experimental/lowp-basic/lowp_experiments.cpp`: SIMD 指令模拟验证
- `src/core/SkRasterPipeline_opts.h`: Skia 实际的光栅管线低精度实现
