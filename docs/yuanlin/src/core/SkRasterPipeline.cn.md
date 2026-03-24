# SkRasterPipeline

> 源文件: src/core/SkRasterPipeline.h, src/core/SkRasterPipeline.cpp

## 概述

`SkRasterPipeline` 是 Skia 中用于构建和执行像素处理管道的核心组件，提供了一种廉价且灵活的方式来链接多个像素处理阶段。它专门设计用于处理极端组合性的场景，例如 {N 种目标格式} × {M 种源格式} × {K 种遮罩格式} × {C 种混合模式} 等。

该系统通过在运行时动态组装管道阶段，避免了为所有可能的组合编写专门的优化例程，从而将问题从组合爆炸（指数级）简化为线性增长。每个阶段由一个符合通用接口的函数和任意的上下文指针表示，管道可以自动选择使用低精度（lowp）或高精度（highp）实现以平衡性能和质量。

## 架构位置

`SkRasterPipeline` 位于 Skia 渲染架构的核心层，是像素处理的基础设施：

- **上层客户端**：`SkShader`、`SkColorFilter`、`SkBlender`、`SkImageShader` 等使用 RasterPipeline 构建处理逻辑
- **中间层**：`SkRasterPipeline` 提供管道构建和执行接口
- **底层实现**：`SkOpts` 提供平台特定的优化阶段函数（SIMD 实现）

RasterPipeline 是 Skia CPU 后端的关键组件，也被 SkSL（Skia Shading Language）的 Raster Pipeline 代码生成器使用。

## 主要类与结构体

### SkRasterPipelineStage 结构体

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fn` | `void (*)()` | 函数指针，指向 `SkOpts::ops_lowp` 或 `ops_highp` 中的阶段函数 |
| `ctx` | `void*` | 阶段上下文数据，通常指向 `SkRasterPipelineOpContexts.h` 中定义的结构体 |

### SkRasterPipeline 类

**继承关系：**
- 无继承关系（独立类）
- `SkRasterPipeline_<bytes>` 模板类继承自 `SkRasterPipeline`，提供内建内存分配器

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAlloc` | `SkArenaAlloc*` | 内存分配器指针 |
| `fRewindCtx` | `RewindCtx*` | 栈回退上下文（用于循环和 SkSL） |
| `fStages` | `StageList*` | 阶段链表（逆序存储） |
| `fTailPointer` | `uint8_t*` | 尾指针，用于 SIMD 车道掩码 |
| `fNumStages` | `int` | 阶段总数 |
| `fMemoryCtxInfos` | `STArray<2, MemoryCtxInfo>` | 内存上下文信息数组 |

### StageList 结构体

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `prev` | `StageList*` | 指向前一个阶段的指针 |
| `stage` | `SkRasterPipelineOp` | 阶段操作类型枚举 |
| `ctx` | `void*` | 阶段上下文指针 |

## 公共 API 函数

### 构造与管理

```cpp
explicit SkRasterPipeline(SkArenaAlloc*);
void reset();
```

构造管道并关联内存分配器；`reset()` 重置管道但保留分配器。

### 添加阶段

```cpp
void append(SkRasterPipelineOp, void* = nullptr);
void append(SkRasterPipelineOp op, const void* ctx);
void append(SkRasterPipelineOp, uintptr_t ctx);
void extend(const SkRasterPipeline&);
```

添加单个阶段或合并另一个管道。支持指针和整数上下文。

### 特殊阶段追加

```cpp
void appendMatrix(SkArenaAlloc*, const SkMatrix&);
void appendConstantColor(SkArenaAlloc*, const float rgba[4]);
void appendSetRGB(SkArenaAlloc*, const float rgb[3]);
void appendLoad(SkColorType, const MemoryCtx*);
void appendLoadDst(SkColorType, const MemoryCtx*);
void appendStore(SkColorType, const MemoryCtx*);
void appendTransferFunction(const skcms_TransferFunction&);
void appendClampIfNormalized(const SkImageInfo&);
void appendStackRewind();
```

这些方法根据参数特性自动选择最优的阶段实现。

### 执行管道

```cpp
void run(size_t x, size_t y, size_t w, size_t h) const;
std::function<void(size_t, size_t, size_t, size_t)> compile() const;
```

`run()` 立即执行管道；`compile()` 预编译管道返回可重用的闭包，摊销设置成本。

### 调试与查询

```cpp
static const char* GetOpName(SkRasterPipelineOp op);
const StageList* getStageList() const;
int getNumStages() const;
void dump() const;
bool empty() const;
```

获取阶段信息和打印管道内容。

## 内部实现细节

### 双精度模式选择

`buildLowpPipeline()` 尝试构建低精度管道：
- 检查全局标志 `gForceHighPrecisionRasterPipeline`
- 检查是否有 `fRewindCtx`（SkSL 循环需要高精度）
- 验证所有阶段都有 lowp 实现

失败则回退到 `buildHighpPipeline()`。

### 阶段链表逆序存储

阶段以逆序链表形式存储（`fStages` 指向最后添加的阶段），构建管道时从后向前遍历，这样可以高效地追加阶段而无需维护尾指针。

### 内存上下文补丁机制

`fMemoryCtxInfos` 跟踪所有内存加载/存储上下文，运行时可以动态修改内存地址而无需重建管道。这对于处理不同行的像素非常重要。

### 优化的矩阵追加

`appendMatrix()` 根据矩阵类型选择最优阶段：
1. **恒等矩阵**：跳过（无操作）
2. **平移矩阵**：使用 `matrix_translate`
3. **缩放+平移**：使用 `matrix_scale_translate`
4. **仿射变换**：使用 `matrix_2x3`（6 个参数）
5. **透视变换**：使用 `matrix_perspective`（9 个参数）

### 颜色加载/存储优化

`appendLoad()` 和 `appendStore()` 针对不同的 `SkColorType` 选择合适的操作序列：
- 某些格式需要组合操作（如 `load_a8` + `alpha_to_red` 处理 R8 格式）
- 自动处理字节序转换（`swap_rb` 用于 BGRA 格式）
- 特殊处理 sRGB 传输函数

### musttail 优化

头文件中检测 `[[clang::musttail]]` 属性支持（`SK_HAS_MUSTTAIL`），用于优化尾调用，减少调用栈开销，提高管道执行效率。

### 传输函数识别

`appendTransferFunction()` 使用 skcms 库识别传输函数类型：
- sRGB 类型：`gamma_` 或 `parametric`
- PQ（感知量化）：`PQish`
- HLG（混合对数伽马）：`HLGish` / `HLGinvish`

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkArenaAlloc` | 快速内存分配器 |
| `SkOpts` | 平台优化的阶段函数实现 |
| `SkRasterPipelineOpList.h` | 操作枚举定义 |
| `SkRasterPipelineOpContexts.h` | 上下文结构体定义 |
| `skcms` | 颜色空间转换库 |
| `SkColorType` | 颜色类型枚举 |
| `SkMatrix` | 变换矩阵 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkShader` | 着色器使用管道生成像素 |
| `SkColorFilter` | 颜色过滤器构建管道 |
| `SkBlender` | 混合器使用管道执行混合 |
| `SkRasterPipelineBlitter` | 光栅化 Blitter |
| `SkSL` Raster Pipeline 生成器 | SkSL 编译到管道 |

## 设计模式与设计决策

### 责任链模式

RasterPipeline 本质上是责任链模式的实现，每个阶段处理像素数据并传递给下一个阶段。通过链式组合简单操作实现复杂功能。

### 策略模式

通过 lowp/highp 双实现策略，根据精度需求和平台能力动态选择执行路径。

### 构建器模式

`SkRasterPipeline` 使用构建器模式逐步添加阶段，最终通过 `run()` 或 `compile()` 执行。提供链式调用的友好 API。

### 线性增长而非组合爆炸

设计的核心哲学是避免组合爆炸。通过运行时组装阶段，将 O(N×M×K×C...) 的代码复杂度降低到 O(N+M+K+C...)。

### 内存分配策略

使用 `SkArenaAlloc` 进行快速内存分配，所有阶段和上下文数据在同一内存池中分配，提高缓存局部性并简化内存管理。

### 平台优化抽象

通过 `SkOpts` 层抽象平台特定的 SIMD 优化，核心逻辑保持平台无关，实际执行时自动使用最佳实现（SSE、AVX、NEON 等）。

## 性能考量

### Lowp vs Highp

- **Lowp（8-16位整数）**：更快，更少内存带宽，适合归一化颜色
- **Highp（32位浮点）**：必需场景包括 SkSL、栈回退、超出 [0,1] 范围的颜色
- 统计数据：CPU 后端只有 1/200 万管道使用超过 2 个 `MemoryCtx`

### 编译（compile）优化

`compile()` 方法预先构建管道并返回闭包，适合重复执行同一管道的场景，摊销设置成本。

### 阶段内联和 SIMD

通过 `[[clang::musttail]]` 和 SIMD 指令，阶段函数可以高效内联执行，处理多个像素（车道）的向量化操作。

### 内存访问模式

- `MemoryCtx` 补丁机制允许动态修改内存地址，无需重建管道
- 连续内存访问提高缓存性能
- `tailPointer` 用于 SIMD 车道掩码，处理不完整的向量

### 特殊优化

- **常量颜色**：黑色和白色有专门的快速路径
- **恒等矩阵**：完全跳过变换阶段
- **整数坐标**：某些操作可以避免浮点计算
- **归一化检测**：只在需要时插入 clamp 操作

### 避免虚函数

使用函数指针而非虚函数，减少间接调用开销，更易于编译器优化。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkRasterPipelineOpList.h` | 操作枚举列表 |
| `src/core/SkRasterPipelineOpContexts.h` | 上下文结构体定义 |
| `src/core/SkOpts.h` | 平台优化函数接口 |
| `src/opts/SkRasterPipeline_opts.h` | SIMD 优化实现 |
| `src/base/SkArenaAlloc.h` | 快速内存分配器 |
| `include/core/SkColorType.h` | 颜色类型定义 |
| `include/core/SkMatrix.h` | 矩阵变换 |
| `modules/skcms/skcms.h` | 颜色管理库 |
| `src/core/SkImageInfo.h` | 图像信息 |
| `include/private/base/SkSpan_impl.h` | Span 容器 |
