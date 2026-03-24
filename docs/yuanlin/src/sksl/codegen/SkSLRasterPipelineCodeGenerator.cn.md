# SkSL Raster Pipeline 代码生成器 (SkSLRasterPipelineCodeGenerator)

> 源文件:
> - `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.h`
> - `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.cpp`

## 概述

Raster Pipeline 代码生成器将 SkSL 程序转换为 Skia 的 Raster Pipeline（RP）指令序列。这是 SkSL 在 CPU 端执行的核心路径，用于 blend（混合）、shader（着色器）和 color filter（颜色滤镜）的 CPU 实现。与 GLSL/WGSL 生成文本代码不同，RP 生成器产出的是直接可执行的低级指令序列。该文件超过 4100 行，包含完整的 SkSL IR 到 RP 指令的翻译逻辑。

## 架构位置

RP 代码生成器位于 SkSL 编译器的代码生成层，但与文本代码生成器有本质区别 -- 它生成的是可由 `SkRasterPipeline` 直接执行的二进制指令。

```
SkSL Program (IR)
  |
  |-- MakeRasterPipelineProgram() [入口函数]
        |
        |-- Generator (内部类)
        |     |-- 遍历 IR 节点
        |     |-- 使用 RP::Builder 构建指令
        |     |
        |     v
        |-- RP::Program [输出]
              |-- appendStages() -> SkRasterPipeline (CPU 执行)
```

## 主要类与结构体

### `Generator`（内部类）

RP 代码生成的核心类，定义在 `.cpp` 文件中，不对外暴露。

**关键成员：**
- `fProgram` -- 输入的 SkSL 程序
- `fContext` -- 编译上下文
- `fDebugTrace` -- 调试追踪信息
- `fProgramSlots` / `fUniformSlots` / `fImmutableSlots` -- 槽位管理器
- `fBuilder` -- `RP::Builder` 指令构建器

### `SlotManager`（内部类）

管理变量到槽位（slot）的映射。每个标量值占一个槽位，向量和矩阵占连续多个槽位。

**功能：**
- `createSlots()` -- 为变量或返回值创建槽位
- `getVariableSlots()` -- 查找或创建变量的槽位
- `getFunctionSlots()` -- 查找或创建函数返回值的槽位
- `mapVariableToSlots()` / `unmapVariableSlots()` -- 变量到槽位的映射管理

### `AutoStack`（内部类）

临时栈的 RAII 管理器。RP 使用多个逻辑栈来管理临时值。

### `LValue`（内部抽象类）

左值抽象，支持变量引用、swizzle、数组索引等各种赋值目标。

## 公共 API 函数

### 入口函数

```cpp
std::unique_ptr<RP::Program> MakeRasterPipelineProgram(
    const Program& program,
    const FunctionDefinition& function,
    DebugTracePriv* debugTrace = nullptr,
    bool writeTraceOps = false);
```

**参数说明：**
- `program` -- 编译后的 SkSL 程序
- `function` -- 要执行的入口函数
- `debugTrace` -- 可选的调试追踪对象
- `writeTraceOps` -- 是否生成调试跟踪指令

**返回值：** RP::Program 对象，可通过 `appendStages()` 追加到 SkRasterPipeline 中执行。

**函数参数传递规则：**
- 着色器（shader）：坐标在 `src.rg` 中
- 颜色滤镜（color filter）：颜色在 `src.rgba` 中
- 混合器（blender）：源色在 `src.rgba`，目标色在 `dst.rgba`

## 内部实现细节

### 槽位模型

RP 使用扁平的槽位数组来存储所有变量值。每个标量值占一个 `float` 大小的槽位。变量、uniform 和不可变值（immutable）使用独立的槽位空间。

### 栈机模型

表达式求值使用基于栈的模型。临时值被压入临时栈，运算消耗栈顶值并将结果压回。多个逻辑栈通过 `stackID` 区分，用于不同的计算上下文。

### 执行掩码

RP 使用 SIMD 风格的执行掩码来处理控制流：
- **条件掩码**（condition mask）：if/else 分支控制
- **循环掩码**（loop mask）：循环中的 break/continue
- **返回掩码**（return mask）：提前返回

### 子效果调用

通过 `invoke_shader`、`invoke_color_filter`、`invoke_blender` 指令调用子着色器/颜色滤镜/混合器，支持效果树的递归组合。

### 调试追踪

当启用 `writeTraceOps` 时，生成器在适当位置插入 `trace_line`、`trace_var`、`trace_enter`、`trace_exit`、`trace_scope` 等调试指令。

### 控制流实现

RP 使用执行掩码实现控制流，这与 GPU 着色器的 SIMD 执行模型一致：

**if-else 语句：**
1. 压入条件掩码
2. 将条件结果合并到条件掩码
3. 执行 if-true 分支
4. 取反条件掩码
5. 执行 if-false 分支
6. 弹出条件掩码

**for 循环：**
1. 压入循环掩码
2. 评估循环条件，更新循环掩码
3. 如果无活跃通道，跳出循环
4. 执行循环体
5. 处理 continue/break（修改掩码）
6. 执行循环增量表达式
7. 跳回步骤 2
8. 弹出循环掩码

**switch 语句：**
1. 将 switch 值压入栈
2. 对每个 case 值使用 `case_op` 比较
3. 匹配的通道启用循环掩码
4. 执行 case 体
5. break 通过 `mask_off_loop_mask` 实现

### 函数调用

函数调用将参数复制到被调函数的参数槽位，执行函数体，然后将返回值从函数返回槽位复制出来。由于不支持递归，所有函数的槽位都是静态分配的。

### 间接索引

数组和矩阵的动态索引通过 `push_slots_indirect` 和 `copy_stack_to_slots_indirect` 实现。使用一个动态栈来存储偏移量，然后使用带边界检查的间接寻址操作。

## 依赖关系

**内部依赖：**
- `SkSLRasterPipelineBuilder` -- RP 指令构建器和 Program 类
- SkSL IR 体系 -- 所有 IR 节点类型
- `SkSLAnalysis` -- 程序分析
- `SkSLConstantFolder` -- 常量折叠
- `SkSLTransform` -- IR 变换
- `SkSLDebugTracePriv` -- 调试追踪
- `SkSLProgramUsage` -- 程序使用分析

**外部依赖：**
- `SkTHash` -- 哈希容器
- `<vector>`, `<optional>` -- 标准库

## 设计模式与设计决策

1. **栈机架构**：使用栈来管理临时值，简化了表达式求值的代码生成。运算符消耗栈顶的操作数并推送结果。

2. **执行掩码实现控制流**：SIMD 并行执行模型中，所有分支都会被执行，通过掩码选择活跃的通道。这与 GPU 着色器的执行模型一致。

3. **槽位映射分离**：变量值、uniform 值和不可变值使用独立的槽位空间，允许不同的内存管理策略。

4. **LValue 抽象**：统一处理各种赋值场景（直接赋值、swizzle 赋值、间接索引赋值），简化代码生成逻辑。

5. **不支持递归**：函数返回值使用静态分配的槽位，无需维护调用栈，这也意味着不支持递归调用。

## 性能考量

- **不可变槽位优化**：编译时常量存储在不可变槽位中，程序创建时一次性初始化，执行时直接读取。
- **执行掩码跟踪**：当已知执行掩码未被修改时，可以生成更简单的无掩码操作（unmasked），避免不必要的掩码应用开销。
- **栈操作合并**：Builder 层会尝试合并相邻的栈操作，减少指令数量。
- **立即数操作**：对于常量操作数，使用立即数版本的指令（如 `add_imm_int`），避免将常量压入栈。

## 相关文件

- `src/sksl/codegen/SkSLRasterPipelineBuilder.h` -- RP 指令构建器和 Program
- `src/sksl/tracing/SkSLDebugTracePriv.h` -- 调试追踪
- `src/core/SkRasterPipeline.h` -- Raster Pipeline 执行引擎
- `src/core/SkRasterPipelineOpList.h` -- RP 操作码列表
- `src/sksl/SkSLAnalysis.h` -- 程序分析工具
- `src/sksl/SkSLCompiler.h` -- 编译器
- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义
- `src/sksl/ir/SkSLVariable.h` -- 变量
- `src/sksl/ir/SkSLSwizzle.h` -- Swizzle 表达式
- `src/sksl/transform/SkSLTransform.h` -- IR 变换
