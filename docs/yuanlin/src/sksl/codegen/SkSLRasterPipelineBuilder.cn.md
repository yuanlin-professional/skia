# SkSL Raster Pipeline 构建器 (SkSLRasterPipelineBuilder)

> 源文件:
> - `src/sksl/codegen/SkSLRasterPipelineBuilder.h`
> - `src/sksl/codegen/SkSLRasterPipelineBuilder.cpp`

## 概述

Raster Pipeline Builder 模块定义了 SkSL Raster Pipeline (RP) 代码生成的底层基础设施，包括指令表示（`Instruction`）、操作码枚举（`ProgramOp`/`BuilderOp`）、指令构建器（`Builder`）和可执行程序（`Program`）。Builder 提供高层 API 来构建 RP 指令序列，Program 负责将这些指令转换为可由 `SkRasterPipeline` 执行的原生阶段（stage）序列。该模块是连接 SkSL IR 层与 Skia CPU 光栅化引擎的桥梁，源文件超过 4500 行。

## 架构位置

```
SkSL IR -> RasterPipelineCodeGenerator (Generator)
              |
              |-- 使用 RP::Builder 构建指令序列
              |
              v
           RP::Program (指令列表)
              |
              |-- makeStages() 将指令转换为 Stage 序列
              |-- appendStages() 追加到 SkRasterPipeline
              |
              v
           SkRasterPipeline (CPU SIMD 执行)
```

## 主要类与结构体

### `SlotRange`

表示连续槽位范围，包含起始索引和数量。用于描述变量、向量、矩阵在槽位空间中的位置。

### `Instruction`

单条 RP 指令的表示：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fOp` | `BuilderOp` | 操作码 |
| `fSlotA` / `fSlotB` | `Slot` | 槽位参数 |
| `fImmA` ~ `fImmD` | `int` | 立即数参数 |
| `fStackID` | `int` | 所属逻辑栈 ID |

### `ProgramOp` 枚举

最终程序中使用的操作码，是原生 `SkRasterPipelineOps` 的超集，额外包含：
- `label` -- 分支目标标签
- `invoke_shader` / `invoke_color_filter` / `invoke_blender` -- 子效果调用
- `invoke_to_linear_srgb` / `invoke_from_linear_srgb` -- 色彩空间转换

### `BuilderOp` 枚举

构建器使用的操作码，是 `ProgramOp` 的超集，额外包含大量栈操作：
- `push_*` 系列 -- 将值压入临时栈（常量、槽位、uniform 等）
- `copy_stack_to_*` 系列 -- 从栈复制到槽位
- `discard_stack` / `pad_stack` -- 栈大小管理
- `select` -- 基于执行掩码选择值
- `push_condition_mask` / `pop_condition_mask` -- 条件掩码栈
- `push_loop_mask` / `pop_loop_mask` -- 循环掩码栈
- `push_return_mask` / `pop_return_mask` -- 返回掩码栈
- `push_src_rgba` / `pop_src_rgba` -- 源色栈操作
- `push_dst_rgba` / `pop_dst_rgba` -- 目标色栈操作

### `Callbacks`

子效果调用的回调接口，由外部实现：
- `appendShader(index)` -- 调用子着色器
- `appendColorFilter(index)` -- 调用子颜色滤镜
- `appendBlender(index)` -- 调用子混合器
- `toLinearSrgb(color)` / `fromLinearSrgb(color)` -- 色彩空间转换

### `Program`

编译后的 RP 程序，包含指令列表和执行所需的元数据。

**关键方法：**
- `appendStages(pipeline, alloc, callbacks, uniforms)` -- 将程序追加到 SkRasterPipeline
- `dump(out, writeInstructionCount)` -- 将程序以可读文本形式输出（用于调试）
- `numUniforms()` -- 返回 uniform 槽位数

### `Builder`

指令序列的构建器，提供丰富的高层 API。

## 公共 API 函数

### Builder 核心方法

**程序控制：**
- `finish()` -- 完成构建，返回 `Program`
- `nextLabelID()` -- 分配新标签 ID

**执行掩码管理：**
- `enableExecutionMaskWrites()` / `disableExecutionMaskWrites()` -- 开启/关闭掩码写入追踪

**分支跳转：**
- `label(id)` -- 放置标签
- `jump(id)` -- 无条件跳转
- `branch_if_all_lanes_active(id)` -- 全通道活跃时跳转
- `branch_if_any_lanes_active(id)` -- 任意通道活跃时跳转
- `branch_if_no_lanes_active(id)` -- 无活跃通道时跳转
- `branch_if_no_active_lanes_on_stack_top_equal(value, id)` -- 条件跳转

**栈操作：**
- `push_constant_i/f/u()` -- 压入常量
- `push_slots()` / `push_immutable()` / `push_uniform()` -- 压入槽位/不可变/uniform 值
- `push_clone()` / `push_duplicates()` -- 克隆栈顶值
- `pop_slots()` / `pop_slots_unmasked()` -- 弹出到槽位
- `discard_stack()` / `pad_stack()` -- 管理栈大小

**算术运算：**
- `unary_op()` / `binary_op()` / `ternary_op()` -- 通用运算
- `dot_floats()` / `refract_floats()` / `inverse_matrix()` -- 特殊数学运算

**矩阵操作：**
- `transpose()` / `diagonal_matrix()` / `matrix_resize()` / `matrix_multiply()`

**掩码操作：**
- `push/pop_condition_mask()` / `merge_condition_mask()` / `merge_inv_condition_mask()`
- `push/pop_loop_mask()` / `merge_loop_mask()` / `mask_off_loop_mask()`
- `push/pop_return_mask()` / `mask_off_return_mask()`

**调试追踪：**
- `trace_line()` / `trace_var()` / `trace_enter()` / `trace_exit()` / `trace_scope()`

## 内部实现细节

### 指令简化

Builder 内部包含指令简化逻辑：
- `simplifyPopSlotsUnmasked()` -- 简化无掩码的弹出操作
- `simplifyImmediateUnmaskedOp()` -- 将 n-way 操作转换为立即数操作
- `lastInstruction()` -- 获取最近的指令以进行窥孔优化

### N-way 到立即数转换

`convert_n_way_op_to_immediate()` 将通用的 n-slot 操作转换为更高效的立即数版本。例如 `add_n_ints` + 常量可转换为 `add_imm_int`。对于减法，通过取反转换为加法的立即数版本。

### Stage 生成

`Program::makeStages()` 将 Builder 指令转换为原生 RP Stage：
- 将 `push_*`/`pop_*` 等栈操作翻译为实际的内存复制操作
- 分配临时栈空间
- 解析标签引用为实际偏移
- 为多槽位操作选择最优的特化版本（1-4 槽位）

### 槽位数据分配

`allocateSlotData()` 在 `SkArenaAlloc` 中分配所有槽位内存：
- Value slots -- 程序变量
- Uniform slots -- uniform 值（由外部提供）
- Immutable slots -- 编译时常量
- Stack slots -- 临时栈空间

## 依赖关系

**内部依赖：**
- `SkRasterPipelineOpList` -- 原生 RP 操作码
- `SkRasterPipeline` -- RP 执行引擎
- `SkArenaAlloc` -- 内存分配器
- `SkSLDebugTracePriv` / `SkSLTraceHook` -- 调试追踪
- `SkRasterPipelineOpContexts` -- RP 操作上下文结构

**外部依赖：**
- `SkTArray` -- 动态数组
- `SkStream` -- 输出流（dump）

## 设计模式与设计决策

1. **Builder/Program 分离**：Builder 负责指令构建和简化，Program 负责执行。这种分离允许在构建阶段进行优化，而执行阶段专注于性能。

2. **两级操作码**：`BuilderOp` 包含高层栈操作，`ProgramOp` 只包含可直接执行的低层操作。`makeStages()` 负责降级。

3. **逻辑栈**：多个逻辑栈通过 `stackID` 区分，允许在不同计算上下文间隔离临时值。

4. **掩码栈**：条件、循环和返回掩码各维护独立的栈，支持嵌套控制流。

5. **特化指令**：对于 1-4 槽位的操作提供特化版本，避免循环开销。

## 性能考量

- **立即数操作优先**：当操作数为常量时，优先使用立即数版本的指令，避免将常量压入栈的开销。
- **无掩码优化**：当已知执行掩码未被修改时，使用 `unmasked` 版本的复制操作，跳过掩码应用。
- **窥孔优化**：Builder 在添加指令时检查相邻指令，进行局部优化。
- **栈重绕**：在没有尾调用优化支持的平台上插入 `stack_rewind` 操作，防止栈溢出。
- **Arena 分配**：所有执行期间的临时内存通过 `SkArenaAlloc` 分配，避免频繁的 malloc/free。

## 相关文件

- `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.h` -- RP 代码生成器
- `src/core/SkRasterPipeline.h` -- RP 执行引擎
- `src/core/SkRasterPipelineOpList.h` -- RP 操作码定义
- `src/core/SkRasterPipelineOpContexts.h` -- RP 操作上下文
- `src/sksl/tracing/SkSLDebugTracePriv.h` -- 调试追踪
- `src/sksl/tracing/SkSLTraceHook.h` -- 追踪钩子
