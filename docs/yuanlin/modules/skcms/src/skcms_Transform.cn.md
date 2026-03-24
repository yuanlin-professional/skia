# skcms_Transform - 颜色转换操作定义

> 源文件: `modules/skcms/src/skcms_Transform.h`

## 概述

skcms_Transform.h 是 skcms 颜色管理系统的内部头文件，定义了颜色转换管线中所有操作（Op）的枚举、SIMD 向量类型模板以及不同指令集下的 `run_program` 函数接口。该文件是颜色转换引擎的核心调度层，将像素格式加载/存储、颜色空间变换、传输函数应用等操作统一编排为一个可执行的操作序列。

## 架构位置

该文件位于 skcms 库的内部实现层（`skcms_private` 命名空间），不面向外部用户。它处于 skcms_public.h（公共 API）和 Transform_inl.h（具体实现）之间，定义了连接两者的操作接口和类型系统。

**层级**: `skcms_public.h` (API) -> `skcms_Transform.h` (Op 定义) -> `Transform_inl.h` (Op 实现)

## 主要类与结构体

### `Op` 枚举
通过宏 `SKCMS_WORK_OPS` 和 `SKCMS_STORE_OPS` 展开生成的操作枚举，分为两类：
- **工作操作（Work Ops）**: 加载像素、颜色空间变换、传输函数等，共约 50 个操作
- **存储操作（Store Ops）**: 将处理后的像素写入目标缓冲区，共约 18 个操作

### SIMD 向量类型 `Vec<N, T>`
基于编译器扩展的 SIMD 向量类型模板：
- **Clang**: 使用 `ext_vector_type(N)` 属性
- **GCC**: 使用 `vector_size(N * sizeof(T))` 属性包装

## 公共 API 函数

### `run_program`
在三个不同的指令集命名空间中声明：

| 命名空间 | 指令集 | SIMD 宽度 |
|----------|--------|-----------|
| `baseline` | 通用（SSE2/NEON/标量） | 1/4 |
| `hsw` | AVX2 + F16C (Haswell) | 8 |
| `skx` | AVX-512F + DQ (Skylake-X) | 16 |

函数签名：
```cpp
void run_program(const Op* program, const void** contexts, ptrdiff_t programSize,
                 const char* src, char* dst, int n,
                 size_t src_bpp, size_t dst_bpp);
```

## 内部实现细节

### 操作宏系统
使用 X 宏（X-Macro）模式，通过 `M(op)` 展开生成操作列表。这使得操作可以在枚举定义、函数分发表、阶段声明等多处复用同一列表。

### 操作分类
- **加载操作**: `load_a8`, `load_g8`, `load_8888`, `load_fff`, `load_hhhh` 等，覆盖从 8 位到浮点的各种像素格式
- **颜色变换**: `swap_rb`, `premul`, `unpremul`, `matrix_3x3`, `matrix_3x4`
- **色彩空间转换**: `lab_to_xyz`, `xyz_to_lab`
- **传输函数**: `tf_r/g/b/a/rgb`, `gamma_*`, `pq_*`, `hlg_*`, `hlginv_*`
- **查找表**: `table_r/g/b/a`, `clut_A2B`, `clut_B2A`
- **存储操作**: `store_a8`, `store_8888`, `store_ffff` 等

### 无穷大常量
为跨编译器兼容性提供两种 `INFINITY_` 定义：
- Clang/GCC: 使用 `__builtin_inff()`
- MSVC: 使用联合体的位模式 `0x7f800000`

### 操作详细分类

#### 加载操作（18 种）
| 操作 | 像素格式 | 每像素字节 |
|------|----------|-----------|
| `load_a8` | 8 位 Alpha | 1 |
| `load_g8` | 8 位灰度 | 1 |
| `load_ga88` | 8 位灰度+Alpha | 2 |
| `load_4444` | ARGB 4444 | 2 |
| `load_565` | RGB 565 | 2 |
| `load_888` | RGB 888 | 3 |
| `load_8888` | RGBA 8888 | 4 |
| `load_1010102` | RGBA 10-10-10-2 | 4 |
| `load_101010x_XR` | RGB XR 10 位 | 4 |
| `load_10101010_XR` | RGBA XR 10 位 | 8 |
| `load_161616LE/BE` | RGB 16 位（小端/大端） | 6 |
| `load_16161616LE/BE` | RGBA 16 位 | 8 |
| `load_hhh` | RGB 半精度浮点 | 6 |
| `load_hhhh` | RGBA 半精度浮点 | 8 |
| `load_fff` | RGB 单精度浮点 | 12 |
| `load_ffff` | RGBA 单精度浮点 | 16 |

#### 颜色操作（8 种）
`swap_rb`, `clamp`, `invert`, `force_opaque`, `premul`, `unpremul`, `matrix_3x3`, `matrix_3x4`

#### 色彩空间转换（2 种）
`lab_to_xyz`, `xyz_to_lab` - CIE Lab 与 XYZ D50 之间的转换

#### 传输函数操作（约 22 种）
- sRGB 类型: `gamma_r/g/b/a/rgb`, `tf_r/g/b/a/rgb`
- PQ 类型: `pq_r/g/b/a/rgb`
- HLG 类型: `hlg_r/g/b/a/rgb`, `hlg_ootf_scale`
- HLG 逆: `hlginv_r/g/b/a/rgb`, `hlginv_ootf_scale`

#### 查找表操作（6 种）
`table_r/g/b/a`, `clut_A2B`, `clut_B2A`

### run_program 参数说明
- `program`: Op 操作序列数组
- `contexts`: 每个操作的上下文指针数组（如矩阵、传输函数）
- `programSize`: 操作序列长度
- `src`/`dst`: 源和目标像素缓冲区
- `n`: 要处理的像素数量
- `src_bpp`/`dst_bpp`: 源和目标每像素字节数

## 依赖关系

- **skcms_public.h**: 公共类型定义（skcms_TransferFunction, skcms_Matrix3x3 等）
- **Transform_inl.h**: 各操作的具体 SIMD 实现
- **skcms_TransformHsw.cc / skcms_TransformSkx.cc**: HSW/SKX 特化编译单元

## 设计模式与设计决策

1. **操作序列化模式**: 将颜色转换分解为原子操作序列，通过解释器逐步执行，灵活支持任意源/目标格式组合。
2. **X 宏枚举**: 操作列表只定义一次，通过宏在多处展开，消除列表不一致的风险。
3. **多指令集分发**: 同一接口在 baseline/hsw/skx 三个命名空间中声明，运行时根据 CPU 能力选择最优路径。
4. **向量类型抽象**: `Vec<N, T>` 模板统一了不同 SIMD 宽度的向量操作，使 Transform_inl.h 可以被多次包含以生成不同宽度的代码。

## 性能考量

- **SIMD 宽度分层**: baseline (1-4), hsw (8), skx (16) 三级，充分利用现代 CPU 的向量单元
- **操作融合**: 工作操作和存储操作的分离允许管线中尽量长地保持数据在寄存器中
- **编译时特化**: 每个指令集编译为独立翻译单元，编译器可针对目标指令集进行最优化

## 相关文件

- `modules/skcms/src/skcms_public.h` - skcms 公共 API
- `modules/skcms/src/Transform_inl.h` - 操作的具体实现
- `modules/skcms/src/skcms_internals.h` - 内部工具函数和宏
- `modules/skcms/src/skcms_TransformSkx.cc` - AVX-512 特化编译单元
- `modules/skcms/src/skcms_TransformHsw.cc` - AVX2 特化编译单元

## 使用注意事项

1. 该头文件仅供 skcms 内部使用，不应被外部代码包含
2. Op 枚举的值由宏展开顺序决定，修改宏列表会改变枚举值
3. 三个命名空间（baseline/hsw/skx）的 run_program 函数签名完全一致，运行时通过函数指针选择
4. Vec 类型模板仅在 Clang 和 GCC 上可用，MSVC 不支持向量扩展
5. 存储操作（store_*）是管线的终止操作，一个程序必须以存储操作结尾
6. 工作操作和存储操作的分离使得管线可以在寄存器中保持中间结果
7. 操作序列中上下文指针的顺序必须与操作序列严格一一对应
8. `INFINITY_` 常量在不同编译器上的定义方式不同，确保使用宏而非直接写 INFINITY
9. baseline 命名空间在所有平台上可用，hsw 和 skx 可能被禁用
10. GCC 的 Vec 辅助类型需要通过 VecHelper 结构体间接定义

### 管线执行示例
一个典型的 sRGB RGBA_8888 到线性 RGBA_ffff 的转换管线：
```
Op::load_8888 -> Op::tf_rgb (sRGB EOTF) -> Op::store_ffff
```
对应三个上下文：nullptr (load 不需要), &sRGB_tf, nullptr (store 不需要)
