# Transform_inl - 颜色转换操作的 SIMD 实现

> 源文件: `modules/skcms/src/Transform_inl.h`

## 概述

Transform_inl.h 是 skcms 颜色管理系统中最核心的实现文件，包含了所有颜色转换操作的 SIMD 向量化实现。该文件设计为被多次包含（intentionally NO #pragma once），每次包含时在不同的命名空间中以不同的 SIMD 宽度（N=1,4,8,16）生成特化代码。文件涵盖了像素格式加载/存储、传输函数应用（sRGB/PQ/HLG）、色彩空间矩阵变换、Lab<->XYZ 转换、CLUT 多维插值等全部操作。

## 架构位置

Transform_inl.h 是 skcms 转换引擎的具体实现层，位于 skcms_Transform.h（操作枚举定义）的下方。它通过宏 N 和模板 V<T> 参数化 SIMD 宽度，被 skcms.cc（baseline）、skcms_TransformHsw.cc（AVX2）和 skcms_TransformSkx.cc（AVX-512）各包含一次。

**编译时包含链**:
- `skcms.cc`: N=1 (标量) 和 N=4 (SSE/NEON)
- `skcms_TransformHsw.cc`: N=8 (AVX2)
- `skcms_TransformSkx.cc`: N=16 (AVX-512)

## 主要类与结构体

### SIMD 类型别名
```
F   = V<float>      // 浮点向量
I32 = V<int32_t>    // 有符号 32 位整数向量
U64 = V<uint64_t>   // 无符号 64 位整数向量
U32 = V<uint32_t>   // 无符号 32 位整数向量
U16 = V<uint16_t>   // 无符号 16 位整数向量
U8  = V<uint8_t>    // 无符号 8 位整数向量
```

### `Ctx` / `NoCtx`
操作上下文包装器。`Ctx` 持有一个 `const void*` 指针，可隐式转换为任意指针类型或 `NoCtx`。

### `ShapedRun` 相关 (间接)
存储操作中使用的像素数据 r, g, b, a 四个 F 类型通道。

## 公共 API 函数

### `run_program`
管线执行入口，根据是否启用 musttail 选择不同的执行策略：
- **musttail 模式**: 将 Op 数组转换为 StageFn 数组，使用尾调用链式执行
- **普通模式**: 使用 switch-case 循环依次执行每个 Op

## 内部实现细节

### 指令集检测宏
根据编译器预定义宏自动检测并设置：
- `USING_AVX` / `USING_AVX_F16C` / `USING_AVX2` / `USING_AVX512F` (x86)
- `USING_NEON` / `USING_NEON_F16C` (ARM)

### 基础向量工具函数

| 函数 | 说明 |
|------|------|
| `load<T>(ptr)` / `store(ptr, val)` | 通过 memcpy 的类型安全加载/存储 |
| `cast<D>(v)` | 向量类型转换（N=1 用 C 转换，N>1 用 `__builtin_convertvector`） |
| `bit_pun<D>(v)` | 位模式重新解释 |
| `to_fixed(f)` | 浮点转定点（四舍五入到 U32） |
| `if_then_else(cond, t, e)` | 条件选择（N=1 用三元运算，N>1 用位掩码） |

### 数学近似函数

| 函数 | 说明 | 精度 |
|------|------|------|
| `approx_log2(x)` | 对数近似，利用 IEEE 浮点指数位 | 约 3 位有效数字 |
| `approx_exp2(x)` | 指数近似，逆向利用浮点位模式 | 约 3 位有效数字 |
| `approx_pow(x, y)` | 幂运算 `exp2(log2(x) * y)` | 组合近似 |
| `floor_(x)` | 向下取整（平台特化：aarch64/AVX512/AVX/SSE4.1/标量） | 精确 |
| `min_` / `max_` | 最小值/最大值（NEON/LoongArch 特化） | 精确 |

### 传输函数应用

| 函数 | 说明 |
|------|------|
| `apply_tf(tf, x)` | 7 参数分段传输函数（sRGB 类型） |
| `apply_gamma(tf, x)` | 纯 gamma 幂函数 |
| `apply_pq(tf, x)` | PQ (SMPTE ST 2084) 传输函数 |
| `apply_hlg(tf, x)` | HLG 传输函数 |
| `apply_hlginv(tf, x)` | HLG 逆传输函数 |
| `compute_Y_in_xyzd50(x, y, z)` | 在 XYZD50 空间计算 Rec.2020 亮度 Y |

### 像素格式加载/存储操作（STAGE 宏）

共约 38 个 load/store 阶段，覆盖：
- 8 位: a8, g8, ga88, 4444, 565, 888, 8888
- 10 位: 1010102, 101010x_XR, 10101010_XR
- 16 位: 161616LE/BE, 16161616LE/BE
- 半精度浮点: hhh, hhhh
- 单精度浮点: fff, ffff

每个阶段都有 NEON 和通用两种实现路径。

### 颜色操作阶段

| 阶段 | 说明 |
|------|------|
| `swap_rb` | 交换红蓝通道 |
| `clamp` | 将 RGBA 钳位到 [0,1] |
| `invert` | 颜色反转 (1-x) |
| `force_opaque` | 强制 alpha 为 1 |
| `premul` / `unpremul` | 预乘/反预乘 alpha |
| `matrix_3x3` / `matrix_3x4` | 3x3/3x4 矩阵变换 |
| `lab_to_xyz` / `xyz_to_lab` | Lab <-> XYZ 色彩空间转换 |

### Half-Float 转换
- `F_from_Half`: 支持 NEON F16C、AVX-512、AVX F16C 和纯软件实现
- `Half_from_F`: 对应的逆转换，软件路径将 denorm half floats 刷为零

### CLUT 多维插值
`clut` 函数实现 1-4 维色彩查找表的多线性插值：
1. 计算每个维度的低/高索引和权重
2. 遍历所有 2^dim 个组合（最多 16 个采样点）
3. 按权重加权求和

### 管线执行器（`run_program`）
- 主循环每次处理 N 个像素（完整 SIMD 宽度）
- 剩余像素（n < N）通过临时缓冲区处理，避免越界读写

## 依赖关系

- **skcms_Transform.h**: Op 枚举和 Vec 类型定义
- **skcms_internals.h**: SKCMS_FALLTHROUGH、SKCMS_HAS_MUSTTAIL 等宏
- **skcms_public.h**: skcms_TransferFunction、skcms_Matrix3x3 等类型
- **arm_neon.h / immintrin.h**: 平台 SIMD 内联函数（间接通过编译单元引入）

## 设计模式与设计决策

1. **多次包含模式**: 文件故意不使用 `#pragma once`，通过参数化 N 和 V<T> 为每个 SIMD 宽度生成独立的代码，这是模板元编程在 C 风格代码中的等价物。
2. **阶段/管线模式**: 每个操作是一个独立的阶段（STAGE），通过操作数组串联成管线。musttail 模式下使用函数指针数组和尾调用实现零开销分发。
3. **近似数学**: 使用 IEEE 浮点位模式技巧进行对数/指数近似，牺牲少量精度换取巨大的性能提升。
4. **平台特化分支**: 大量使用 `#if defined(USING_NEON)` 等条件编译，为每个平台选择最优指令。

## 性能考量

- **SIMD 并行度**: 每次操作处理 N 个像素（N=1,4,8,16），最大可达 16 路并行
- **内存访问优化**: strided load/store（`load_3`/`load_4`/`store_3`/`store_4`）适配 SoA 数据布局
- **AVX2 gather 指令**: 24 位和 48 位 CLUT 采样利用硬件 gather 指令加速随机访问
- **尾调用优化**: musttail 模式避免函数调用的栈帧开销，将管线执行退化为一系列跳转
- **denorm 处理**: half-float 转换中将非规格化数直接刷零，避免昂贵的 denorm 处理
- **近似函数**: `approx_pow`/`approx_exp2`/`approx_log2` 避免了 libm 调用，适合向量化
- **剩余像素处理**: 使用临时栈缓冲区处理尾部像素，memcpy 确保不会越界访问

### 阶段宏系统详解

#### SKCMS_HAS_MUSTTAIL 模式
```
StageList -> StageFn[0] --musttail--> StageFn[1] --musttail--> ... --return-->
```
每个阶段是一个函数，通过 `[[clang::musttail]]` 属性保证尾调用，消除栈帧增长。
- `STAGE(name, arg)`: 声明中间阶段，尾调用下一个阶段
- `FINAL_STAGE(name, arg)`: 声明最终阶段（store 操作），直接返回

#### 普通模式
```
exec_stages: while(true) { switch(*ops++) { case Op::name: Exec_name(...); break/return; } }
```
使用 switch-case 循环执行操作序列。工作操作用 break 继续循环，存储操作用 return 退出。

### CLUT 多维插值详解
clut 函数支持 1-4 维输入（对应 ICC 的 1-4 通道输入）：
1. 对每个维度 i (从高维到低维)：
   - 计算 `x = input[i] * (grid_points[i] - 1)` 得到采样位置
   - 计算 `lo = trunc(x)`, `hi = min(lo+1, grid-1)` 得到两个网格点
   - 计算 `t = fract(x)` 作为插值权重
   - 将维度步长累乘到索引中
2. 遍历 2^dim 个采样组合：
   - 使用位掩码选择每个维度的 lo/hi
   - 累乘对应权重
   - 从 grid_8 或 grid_16 采样 RGB(A) 值
3. 加权求和得到最终输出

### 大端/小端处理
- 16 位大端格式使用 `swap_endian_16` (NEON) 或手动字节交换
- 64 位格式使用 `swap_endian_16x4` 批量交换

### HLG OOTF 实现
HLG 参考 OOTF（光学-光学传输函数）按 ITU-R BT.2100-3 Table 5 实现：
1. 在 XYZD50 空间计算 Rec.2020 亮度 Y
2. 对 Y 应用 gamma=1.2 的幂函数
3. 将结果乘以各通道
4. 缩放到参考峰值白（1000 nits / 203 nits）

## 相关文件

- `modules/skcms/src/skcms_Transform.h` - 操作枚举和向量类型定义
- `modules/skcms/src/skcms_internals.h` - 内部宏和工具函数
- `modules/skcms/src/skcms_TransformSkx.cc` - AVX-512 编译单元
- `modules/skcms/src/skcms_public.h` - 公共类型定义

## 使用注意事项

1. 该文件故意不使用 `#pragma once`，被设计为多次包含
2. 每次包含前必须定义 N（SIMD 宽度）和 V<T>（向量类型模板）
3. 近似数学函数（approx_*）在极端输入值下精度有限
4. half-float 非规格化数被刷零，可能导致极小值丢失
5. 所有 load/store 阶段假设对齐要求已满足（由调用方保证）
6. 16 位和 32 位格式有特定的对齐要求（分别为 2 字节和 4 字节）
7. gather 操作假设表数据前有安全的可读字节（用于 gather_24 的回退读取）
8. CLUT 采样最多支持 4 维输入
9. musttail 模式下 stages 数组最多容纳 32 个操作
10. 剩余像素处理使用 4*4*N 字节的栈临时缓冲区
