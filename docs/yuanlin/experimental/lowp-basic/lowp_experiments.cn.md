# Lowp Experiments - SIMD 指令模拟验证实验

> 源文件: `experimental/lowp-basic/lowp_experiments.cpp`

## 概述

`lowp_experiments.cpp` 是一个验证性实验程序，用于确保纯 C 实现的 SIMD 指令模拟函数与实际硬件 intrinsic 指令输出完全一致。它测试了 x86 SSSE3 `_mm_mulhrs_epi16` 和 ARM NEON `vqrdmulhq_s16` 指令的模拟正确性，以及使用 SSSE3 模拟 NEON 饱和乘法的交叉模拟方案。

## 架构位置

位于 `experimental/lowp-basic/` 目录，属于 Skia 低精度 SIMD 渲染管线的验证测试。为跨平台 SIMD 模拟方案提供正确性保证。

## 主要类与结构体

无类定义。使用 Clang 扩展向量类型：
- `V<N, T>`: 模板别名，使用 `__attribute__((ext_vector_type(N)))` 定义 SIMD 向量
- `Q15`: 8 路 16 位无符号整数向量 `V<8, uint16_t>`

## 公共 API 函数

- `main()`: 根据编译目标架构运行对应的验证测试

## 内部实现细节

1. **`test_mm_mulhrs_epi16_simulation`** (SSSE3): 穷举 [-32768, 32767] x [-32768, 32767] 验证 `simulate_ssse3_mm_mulhrs_epi16` 与实际 `_mm_mulhrs_epi16` intrinsic 一致
2. **`ssse3_vqrdmulhq_s16`**: 使用 SSSE3 指令模拟 ARM NEON 的饱和舍入加倍乘高位操作
   - 使用 `_mm_mulhrs_epi16` 计算乘积
   - 检测 0x8000 溢出并通过 XOR 修正
3. **`test_ssse3_vqrdmulhq_s16`**: 验证上述 SSSE3 跨架构模拟的正确性
4. **`test_neon_vqrdmulhq_s16_simulation`** (ARM NEON): 验证纯 C 模拟与 NEON `vqrdmulhq_s16` intrinsic 一致

## 依赖关系

- `experimental/lowp-basic/QMath.h`: 纯 C 的 SIMD 模拟函数
- 平台相关: `<immintrin.h>` (SSSE3), `<arm_neon.h>` (ARM NEON)
- 仅支持 Clang 编译器（`ext_vector_type` 特性）

## 设计模式与设计决策

- 条件编译（`__SSSE3__`, `__ARM_NEON`）实现平台相关测试
- 穷举测试策略确保所有 2^32 种输入组合均被验证
- 使用 `constexpr` 限定 `limit` 向量常量优化编译器生成
- XOR 技巧处理饱和溢出：当乘积恰好为 0x8000 时需要钳位

## 性能考量

- 测试循环为 O(2^32)，运行时间较长，仅用于验证目的
- 验证结果确保模拟函数可以安全替代硬件 intrinsic 用于跨平台代码

## 相关文件

- `experimental/lowp-basic/QMath.h`: 被验证的模拟函数定义
- `experimental/lowp-basic/lerp-study.cpp`: 使用这些模拟函数进行插值研究
- `experimental/lowp-basic/bilerp-study.cpp`: 双线性插值研究
