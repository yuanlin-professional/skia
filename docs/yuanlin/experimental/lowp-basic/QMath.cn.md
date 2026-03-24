# QMath - Q15 定点数学运算库

> 源文件: `experimental/lowp-basic/QMath.h`

## 概述

`QMath.h` 是一个头文件库，提供 Q1.15 定点数格式的数学运算，包括 SIMD 指令的纯 C 模拟实现。它定义了关键的向量类型和两个核心定点乘法函数：SSSE3 `_mm_mulhrs_epi16` 和 ARM NEON `vqrdmulhq_s16` 的模拟版本。

## 架构位置

位于 `experimental/lowp-basic/` 目录，作为低精度渲染管线实验的基础数学库。被同目录下的 `lerp-study.cpp`、`bilerp-study.cpp` 和 `lowp_experiments.cpp` 共同引用。

## 主要类与结构体

### 类型别名
- **`V<N, T>`**: Clang 扩展向量类型模板，`T __attribute__((ext_vector_type(N)))`
- **`Q15`**: `V<8, uint16_t>` - 8 路 Q1.15 定点数向量
- **`I16`**: `V<8, int16_t>` - 8 路有符号 16 位整数向量
- **`U16`**: `V<8, uint16_t>` - 8 路无符号 16 位整数向量

## 公共 API 函数

- **`constrained_add(I16 a, U16 b) -> U16`**: 带约束的有符号加无符号运算，断言结果在 [0, UINT16_MAX] 范围内
- **`simulate_ssse3_mm_mulhrs_epi16(I16 a, I16 b) -> I16`**: 纯 C 模拟 x86 SSSE3 的 `_mm_mulhrs_epi16` 指令
- **`simulate_neon_vqrdmulhq_s16(Q15 a, Q15 b) -> Q15`**: 纯 C 模拟 ARM NEON 的 `vqrdmulhq_s16` 指令

## 内部实现细节

1. **SSSE3 模拟** (`simulate_ssse3_mm_mulhrs_epi16`):
   - 计算: `(r * s + (1 << 14)) >> 15`
   - 带 14 位舍入的 15 位右移乘高位操作
   - 使用 32 位中间结果避免溢出

2. **NEON 模拟** (`simulate_neon_vqrdmulhq_s16`):
   - 计算: `saturate((2 * r * s + (1 << 15)) >> 16)`
   - 加倍乘积后带舍入的 16 位右移
   - 64 位中间结果避免溢出
   - 结果饱和到 [-32768, 32767]

3. **`constrained_add`**: 通过 assert 在 debug 模式下验证加法不会溢出 uint16_t 范围

## 依赖关系

- 仅支持 Clang 编译器（`ext_vector_type` 扩展）
- 可选: `<immintrin.h>` (SSSE3), `<arm_neon.h>` (NEON)
- `<cassert>`, `<cstdint>`

## 设计模式与设计决策

- 头文件库模式（header-only），所有函数为 `static inline` 确保内联
- 纯 C 实现确保跨平台可移植性，同时可与硬件 intrinsic 进行对比验证
- 使用 lambda 封装单元素运算逻辑，循环应用到向量的 8 个通道
- Include guard 使用传统 `#ifndef` 宏

## 性能考量

- `static inline` 修饰确保编译器内联，避免函数调用开销
- 实际使用时应优先使用硬件 intrinsic，此模拟版本主要用于验证和不支持 SIMD 的平台
- 向量宽度固定为 8（对应 128 位 SIMD 寄存器中 16 位元素的数量）

## 相关文件

- `experimental/lowp-basic/lowp_experiments.cpp`: 验证模拟函数正确性
- `experimental/lowp-basic/lerp-study.cpp`: 使用这些函数研究线性插值
- `experimental/lowp-basic/bilerp-study.cpp`: 使用这些函数研究双线性插值
