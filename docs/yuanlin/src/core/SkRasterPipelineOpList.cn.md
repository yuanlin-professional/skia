# SkRasterPipelineOpList

> 源文件: src/core/SkRasterPipelineOpList.h

## 概述

`SkRasterPipelineOpList.h` 定义了 Skia Raster Pipeline 系统中所有可用操作的枚举列表。这是一个纯定义文件，使用宏技巧将 200 多个管道操作分为三个主要类别：低精度操作（lowp）、高精度专用操作（highp-only）和 SkSL 专用操作。该文件是 Raster Pipeline 架构的核心接口定义，决定了管道能够执行的所有原子操作，并在编译时确保操作分类的一致性。

## 架构位置

`SkRasterPipelineOpList` 是 Raster Pipeline 系统的基础定义层：

- **基础地位**: 定义了所有管道操作的"词汇表"
- **编译期依赖**: 许多文件通过宏展开使用这些定义
- **分类作用**: 区分低精度/高精度路径，优化性能
- **被引用者**: `SkRasterPipeline`、操作实现文件、SkSL 编译器、调试工具

## 主要类与结构体

### 核心枚举

| 枚举名 | 定义方式 | 说明 |
|-------|---------|------|
| `SkRasterPipelineOp` | 宏展开 | 包含所有操作的枚举类型 |

### 宏定义分类

| 宏名 | 操作数量 | 用途 |
|------|---------|------|
| `SK_RASTER_PIPELINE_OPS_LOWP(M)` | ~57 个 | 定义具有低精度和高精度双实现的操作 |
| `SK_RASTER_PIPELINE_OPS_SKSL(M)` | ~93 个 | 定义 SkSL 专用操作 |
| `SK_RASTER_PIPELINE_OPS_HIGHP_ONLY(M)` | ~84 个 | 定义仅高精度实现的操作（包含 SkSL） |
| `SK_RASTER_PIPELINE_OPS_ALL(M)` | ~141 个 | 所有操作的并集 |

### 常量定义

| 常量名 | 值 | 说明 |
|-------|-----|------|
| `kNumRasterPipelineLowpOps` | 低精度操作计数 | 编译期计算的低精度操作数量 |
| `kNumRasterPipelineHighpOps` | 全部操作计数 | 编译期计算的高精度操作数量 |

## 公共 API 函数

该文件不包含函数，仅定义宏和枚举。

## 内部实现细节

### 宏展开技巧

使用"X-宏"（X-Macro）模式实现：

```cpp
// 定义操作列表
#define SK_RASTER_PIPELINE_OPS_LOWP(M) \
    M(load_8888) M(store_8888) M(clamp_01) ...

// 生成枚举
enum class SkRasterPipelineOp {
#define M(op) op,
    SK_RASTER_PIPELINE_OPS_ALL(M)
#undef M
};

// 这会展开为:
// enum class SkRasterPipelineOp {
//     load_8888, store_8888, clamp_01, ...
// };
```

### 操作计数自动化

```cpp
#define M(st) +1
static constexpr int kNumRasterPipelineLowpOps = SK_RASTER_PIPELINE_OPS_LOWP(M);
#undef M

// 展开为: 1 + 1 + 1 + ... (57 个 1)
```

### 操作分类详解

#### 1. 低精度操作 (SK_RASTER_PIPELINE_OPS_LOWP)

**数据传输操作**：
- `load_8888`, `load_a8`, `load_565`, `load_4444`, `load_rg88`
- `store_8888`, `store_a8`, `store_565`, `store_4444`, `store_rg88`, `store_r8`
- `gather_8888`, `gather_a8`, `gather_565`, `gather_4444`, `gather_rg88`
- `load_src`, `load_dst`, `store_src`, `store_dst`, `store_src_a`

**颜色操作**：
- `move_src_dst`, `move_dst_src`, `swap_src_dst`, `swap_rb`, `swap_rb_dst`
- `premul`, `premul_dst`, `unpremul`（注：unpremul 在高精度专用中）
- `force_opaque`, `force_opaque_dst`
- `clamp_01`, `clamp_a_01`, `clamp_gamut`
- `set_rgb`, `black_color`, `white_color`, `uniform_color`, `uniform_color_dst`

**通道转换**：
- `alpha_to_gray`, `alpha_to_gray_dst`
- `alpha_to_red`, `alpha_to_red_dst`
- `bt709_luminance_or_luma_to_alpha`
- `bt709_luminance_or_luma_to_rgb`

**混合模式**（Porter-Duff + 扩展）：
- Porter-Duff: `clear`, `src`, `dst`, `srcover`, `dstover`, `srcin`, `dstin`, `srcout`, `dstout`, `srcatop`, `dstatop`, `xor_`, `plus_`
- 扩展混合: `modulate`, `multiply`, `screen`, `darken`, `lighten`, `difference`, `exclusion`, `hardlight`, `overlay`
- 优化路径: `srcover_rgba_8888`

**变换操作**：
- `matrix_translate`, `matrix_scale_translate`, `matrix_2x3`, `matrix_perspective`
- `seed_shader`（生成初始坐标）

**平铺模式**：
- `clamp_x_1`, `clamp_x_and_y`, `mirror_x_1`, `repeat_x_1`
- `decal_x`, `decal_y`, `decal_x_and_y`, `check_decal_mask`

**采样**：
- `bilerp_clamp_8888`

**渐变**：
- `evenly_spaced_gradient`, `gradient`, `evenly_spaced_2_stop_gradient`
- `xy_to_unit_angle`, `xy_to_radius`

**缩放与插值**：
- `scale_u8`, `scale_565`, `scale_1_float`, `scale_native`
- `lerp_u8`, `lerp_565`, `lerp_1_float`, `lerp_native`

**特效**：
- `emboss`, `swizzle`

**调试操作**：
- `debug_x`, `debug_y`, `debug_r`, `debug_g`, `debug_b`, `debug_a`
- `debug_r_255`, `debug_g_255`, `debug_b_255`, `debug_a_255`

#### 2. 高精度专用操作 (SK_RASTER_PIPELINE_OPS_HIGHP_ONLY)

**高精度数据传输**：
- 16 位: `load_16161616`, `load_a16`, `load_r16`, `load_rg1616`
- 浮点16: `load_f16`, `load_af16`, `load_rgf16`
- 浮点32: `load_f32`
- 10位: `load_1010102`, `load_1010102_xr`, `load_10x6`, `load_10101010_xr`
- 对应的 store 和 gather 操作

**颜色空间转换**：
- `rgb_to_hsl`, `hsl_to_rgb`
- `css_lab_to_xyz`, `css_oklab_to_linear_srgb`, `css_oklab_gamut_map_to_linear_srgb`
- `css_hcl_to_lab`, `css_hsl_to_srgb`, `css_hwb_to_srgb`

**高级混合模式**：
- `colorburn`, `colordodge`, `softlight`
- `hue`, `saturation`, `color`, `luminosity`

**变换与伽马**：
- `matrix_3x3`, `matrix_3x4`, `matrix_4x5`, `matrix_4x3`
- `parametric`, `gamma_`, `PQish`, `HLGish`, `HLGinvish`, `ootf`

**高级采样**：
- `bilinear_setup`, `bilinear_nx`, `bilinear_px`, `bilinear_ny`, `bilinear_py`
- `bicubic_setup`, `bicubic_n3x`, `bicubic_n1x`, `bicubic_p1x`, `bicubic_p3x`
- `bicubic_n3y`, `bicubic_n1y`, `bicubic_p1y`, `bicubic_p3y`
- `bicubic_clamp_8888`, `bilerp_clamp_8888_force_highp`
- `mipmap_linear_init`, `mipmap_linear_update`, `mipmap_linear_finish`

**特殊着色器**：
- `perlin_noise`
- 二点锥形渐变: `xy_to_2pt_conical_*` 系列（6 个变体）
- `gauss_a_to_rgba`

**其他高精度操作**：
- `unpremul`, `unpremul_polar`, `dither`
- `unbounded_set_rgb`, `unbounded_uniform_color`
- `byte_tables`
- `stack_checkpoint`, `stack_rewind`
- `callback`
- `accumulate`

#### 3. SkSL 操作 (SK_RASTER_PIPELINE_OPS_SKSL)

**初始化与设备坐标**：
- `init_lane_masks`, `store_device_xy01`, `exchange_src`

**掩码管理**：
- 条件掩码: `load_condition_mask`, `store_condition_mask`, `merge_condition_mask`, `merge_inv_condition_mask`
- 循环掩码: `load_loop_mask`, `store_loop_mask`, `mask_off_loop_mask`, `reenable_loop_mask`, `merge_loop_mask`
- 返回掩码: `load_return_mask`, `store_return_mask`, `mask_off_return_mask`

**控制流**：
- 分支: `branch_if_all_lanes_active`, `branch_if_any_lanes_active`, `branch_if_no_lanes_active`, `branch_if_no_active_lanes_eq`
- 跳转: `jump`
- Case: `case_op`, `continue_op`

**数据拷贝与移动**：
- Uniform: `copy_uniform`, `copy_2_uniforms`, `copy_3_uniforms`, `copy_4_uniforms`
- 常量: `copy_constant`, `splat_2_constants`, `splat_3_constants`, `splat_4_constants`
- 槽位（有掩码）: `copy_slot_masked`, `copy_2_slots_masked`, `copy_3_slots_masked`, `copy_4_slots_masked`
- 槽位（无掩码）: `copy_slot_unmasked`, `copy_2_slots_unmasked`, `copy_3_slots_unmasked`, `copy_4_slots_unmasked`
- 不可变: `copy_immutable_unmasked`, `copy_2_immutables_unmasked`, `copy_3_immutables_unmasked`, `copy_4_immutables_unmasked`
- 间接: `copy_from_indirect_unmasked`, `copy_from_indirect_uniform_unmasked`, `copy_to_indirect_masked`

**Swizzle 操作**：
- `swizzle_1`, `swizzle_2`, `swizzle_3`, `swizzle_4`
- `swizzle_copy_slot_masked`, `swizzle_copy_2_slots_masked`, `swizzle_copy_3_slots_masked`, `swizzle_copy_4_slots_masked`
- `swizzle_copy_to_indirect_masked`
- `shuffle`

**数学运算**（支持 1-4 分量，float/int/uint）：
- 算术: `add`, `sub`, `mul`, `div`, `mod`, `mix`
- 比较: `cmplt`, `cmple`, `cmpeq`, `cmpne`
- 范围: `min`, `max`
- 位运算: `bitwise_and`, `bitwise_or`, `bitwise_xor`
- 立即数优化: `add_imm_float`, `add_imm_int`, `mul_imm_float`, `mul_imm_int`, 等

**高级数学函数**：
- 标量: `abs_int`, `floor_float`, `ceil_float`, `invsqrt_float`, `sqrt_float`
- 三角函数: `sin_float`, `cos_float`, `tan_float`, `asin_float`, `acos_float`, `atan_float`, `atan2_n_floats`
- 指数: `pow_n_floats`, `exp_float`, `exp2_float`, `log_float`, `log2_float`
- 矢量: `dot_2_floats`, `dot_3_floats`, `dot_4_floats`, `refract_4_floats`, `smoothstep_n_floats`

**矩阵运算**：
- `matrix_multiply_2`, `matrix_multiply_3`, `matrix_multiply_4`
- `inverse_mat2`, `inverse_mat3`, `inverse_mat4`

**类型转换**：
- Float ↔ Int: `cast_to_float_from_int`, `cast_to_int_from_float`（支持 1-4 分量）
- Float ↔ Uint: `cast_to_float_from_uint`, `cast_to_uint_from_float`（支持 1-4 分量）

**调试追踪**：
- `trace_line`, `trace_var`, `trace_enter`, `trace_exit`, `trace_scope`

## 依赖关系

### 依赖的模块

该文件是纯定义文件，不依赖其他模块（除了 C++ 标准）。

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkRasterPipeline.h` | 使用 `SkRasterPipelineOp` 枚举 |
| `src/opts/SkRasterPipeline_opts.h` | 实现各操作的 SIMD 版本 |
| `SkRasterPipelineBlitter.cpp` | 使用操作构建绘制管道 |
| `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.cpp` | 生成 SkSL 操作 |
| 各种着色器实现 | 使用渐变、采样等操作 |
| 调试工具 | 使用 debug_* 操作 |

## 设计模式与设计决策

### 1. X-宏模式（X-Macro Pattern）

核心设计模式，允许单一定义多种用途：

```cpp
// 定义列表
#define MY_OPS(M) M(op1) M(op2) M(op3)

// 用途1: 生成枚举
#define M(op) op,
enum Ops { MY_OPS(M) };
#undef M

// 用途2: 生成字符串数组
#define M(op) #op,
const char* names[] = { MY_OPS(M) };
#undef M

// 用途3: 生成函数指针数组
#define M(op) &op##_impl,
void (*funcs[])() = { MY_OPS(M) };
#undef M
```

### 2. 精度分层策略

将操作分为 lowp 和 highp 两层：

- **lowp 路径**: U16 数据类型，快速但精度有限
- **highp 路径**: float 数据类型，精度高但较慢

编译期决定使用哪条路径，无运行时开销。

### 3. 操作命名约定

- **前缀**: `load_`, `store_`, `gather_` 表示内存操作
- **后缀**: `_dst` 表示操作目标（destination）而非源
- **数字**: `_8888`, `_565`, `_f16` 表示像素格式
- **向量化**: `_2_floats`, `_4_ints` 表示操作的分量数

### 4. 立即数优化

```cpp
M(add_imm_float)    // 一个操作数是立即数，优化为单指令
M(add_n_floats)     // 两个操作数都是变量
```

立即数版本避免从内存加载常数。

### 5. 编译期计数

```cpp
static constexpr int kNumRasterPipelineLowpOps = SK_RASTER_PIPELINE_OPS_LOWP(M);
```

使用宏计数而非手工维护，确保准确性。

## 性能考量

### 1. 低精度优化

lowp 操作使用 U16（16 位无符号整数）而非 float：
- **内存带宽**: 减半（2 字节 vs 4 字节）
- **缓存利用**: 更好（一个缓存行可容纳更多数据）
- **SIMD 效率**: AVX2 可同时处理 16 个 U16，但只能处理 8 个 float

### 2. 操作融合

某些操作是融合版本：
- `srcover_rgba_8888`: 融合 SrcOver 混合和 8888 存储
- `matrix_scale_translate`: 融合缩放和平移

减少中间数据传递。

### 3. 格式专用化

每种像素格式都有专门的加载/存储操作：
- 避免通用代码的分支
- 允许格式特定的优化（如 565 的位操作）

### 4. SkSL 的细粒度操作

SkSL 提供了大量细粒度操作（如 `add_2_floats` 而非通用的 `add`），因为：
- 编译器可以生成最优代码
- 避免运行时分发
- 更好地利用 SIMD

### 5. 调试操作的低开销

`debug_*` 操作在发布版本中可以完全跳过（通过条件编译），零性能影响。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkRasterPipeline.h` | 使用者 | 管道主类 |
| `src/core/SkRasterPipelineOpContexts.h` | 配对文件 | 操作的上下文数据结构 |
| `src/opts/SkRasterPipeline_opts.h` | 实现文件 | 操作的 SIMD 实现 |
| `src/core/SkRasterPipelineBlitter.cpp` | 使用者 | 构建绘制管道 |
| `src/core/SkOpts.h` | 基础设施 | CPU 特性检测和调度 |
| `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.cpp` | 生成器 | SkSL 编译到管道 |

## 典型使用场景

### 场景 1: 使用 X-宏生成函数分发表

```cpp
// 在实现文件中
#define M(op) &rp_##op,
static void (*g_highp_stages[])(void) = {
    SK_RASTER_PIPELINE_OPS_ALL(M)
};
#undef M

// 调度
void execute_stage(SkRasterPipelineOp op, void* ctx) {
    g_highp_stages[static_cast<int>(op)](ctx);
}
```

### 场景 2: 根据精度选择操作

```cpp
if (use_lowp) {
    pipeline.append(SkRasterPipelineOp::load_8888, ctx);
} else {
    pipeline.append(SkRasterPipelineOp::load_f32, ctx);
}
```

### 场景 3: SkSL 编译器生成操作序列

```cpp
// SkSL: float x = a + b * 2.0;
// 编译为:
pipeline.append(SkRasterPipelineOp::mul_imm_float, {b_slot, 2.0f});
pipeline.append(SkRasterPipelineOp::add_float, {result_slot, a_slot, temp_slot});
```

### 场景 4: 调试可视化

```cpp
// 在每个阶段后查看红色通道
pipeline.append(SkRasterPipelineOp::some_transform, ctx);
pipeline.append(SkRasterPipelineOp::debug_r_255, debug_ctx);
```
