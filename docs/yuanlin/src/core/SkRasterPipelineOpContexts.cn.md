# SkRasterPipelineOpContexts

> 源文件: src/core/SkRasterPipelineOpContexts.h

## 概述

`SkRasterPipelineOpContexts` 命名空间定义了 Skia Raster Pipeline 中各种操作所需的上下文数据结构。这些结构体为管道操作提供了状态信息、配置参数和临时存储空间。该文件是 Raster Pipeline 的核心数据定义文件，包含了从简单的内存指针到复杂的采样器状态的 40 多种上下文结构体。每个结构体都精心设计以适应 SIMT（Single Instruction Multiple Threads）执行模型，支持同时处理最多 16 个像素。

## 架构位置

`SkRasterPipelineOpContexts` 位于 Raster Pipeline 架构的中心：

- **核心地位**: 是 Raster Pipeline 操作和执行引擎之间的数据契约
- **被使用者**: `SkRasterPipeline`、`SkRasterPipelineBlitter`、各种着色器和特效类
- **定义约束**: 影响管道的内存布局、对齐要求和并行度

该文件不包含任何实现代码，纯粹是数据结构定义。

## 主要类与结构体

### 全局常量

| 常量名 | 值 | 说明 |
|-------|-----|------|
| `kMaxStride` | 16 | 每次处理的最大像素数（通用） |
| `kMaxStride_highp` | 16 | 高精度管道的最大步长 |
| `kMaxScratchPerPatch` | max(256, 64) | 每个补丁的临时缓冲区大小（字节） |

### 基础上下文结构

#### MemoryCtx - 内存访问上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `pixels` | `void*` | 像素数据指针 |
| `stride` | `int` | 行跨度（像素数） |

**用途**: 所有加载/存储操作的基础结构，指向源/目标像素缓冲区。

#### MemoryCtxInfo - 内存上下文元信息

| 成员 | 类型 | 说明 |
|------|------|------|
| `context` | `MemoryCtx*` | 指向实际的内存上下文 |
| `bytesPerPixel` | `int` | 每像素字节数 |
| `load` | `bool` | 是否需要加载 |
| `store` | `bool` | 是否需要存储 |

#### MemoryCtxPatch - 尾部像素处理补丁

| 成员 | 类型 | 说明 |
|------|------|------|
| `scratch` | `std::byte[kMaxScratchPerPatch]` | 临时缓冲区 |
| `info` | `MemoryCtxInfo` | 关联的内存上下文信息 |
| `backup` | `void*` | 备份的原始指针 |

**用途**: 处理不能被 N 整除的尾部像素，避免越界访问。

### 采样与纹理上下文

#### GatherCtx - 纹理采集上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `pixels` | `const void*` | 纹理数据指针 |
| `stride` | `int` | 纹理行跨度 |
| `width` | `float` | 纹理宽度 |
| `height` | `float` | 纹理高度 |
| `weights[16]` | `float` | 双三次插值权重 |
| `roundDownAtInteger` | `bool` | 整数位置的舍入控制 |

#### SamplerCtx - 采样器状态

| 成员 | 类型 | 说明 |
|------|------|------|
| `x[kMaxStride_highp]` | `float` | X 坐标数组 |
| `y[kMaxStride_highp]` | `float` | Y 坐标数组 |
| `fx[kMaxStride_highp]` | `float` | 小数部分 X |
| `fy[kMaxStride_highp]` | `float` | 小数部分 Y |
| `scalex[kMaxStride_highp]` | `float` | X 方向缩放 |
| `scaley[kMaxStride_highp]` | `float` | Y 方向缩放 |
| `weights[16]` | `float` | 双三次权重 |
| `wx[4][kMaxStride_highp]` | `float` | X 方向权重矩阵 |
| `wy[4][kMaxStride_highp]` | `float` | Y 方向权重矩阵 |

#### TileCtx - 平铺模式上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `scale` | `float` | 缩放因子 |
| `invScale` | `float` | 1/scale 的缓存值 |
| `mirrorBiasDir` | `int` | 镜像模式的偏向方向 (+1 或 -1) |

#### DecalTileCtx - 边缘裁剪上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `mask[kMaxStride]` | `uint32_t` | 掩码数组（标记越界像素） |
| `limit_x` | `float` | X 方向上限 |
| `limit_y` | `float` | Y 方向上限 |
| `inclusiveEdge_x` | `float` | X 闭区间边界控制 |
| `inclusiveEdge_y` | `float` | Y 闭区间边界控制 |

#### MipmapCtx - Mipmap 线性插值上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `x[kMaxStride_highp]` | `float` | 原始 X 坐标 |
| `y[kMaxStride_highp]` | `float` | 原始 Y 坐标 |
| `r/g/b/a[kMaxStride_highp]` | `float` | 基础层颜色 |
| `scaleX` | `float` | 向低层转换的 X 缩放 |
| `scaleY` | `float` | 向低层转换的 Y 缩放 |
| `lowerWeight` | `float` | 低层级的混合权重 |

### 渐变与颜色上下文

#### GradientCtx - 通用渐变上下文

| 成员 | 类型 | 说明 |
|------|------|------|
| `stopCount` | `size_t` | 色标数量 |
| `factors[4]` | `float*` | 各通道的斜率数组 |
| `biases[4]` | `float*` | 各通道的偏移数组 |
| `ts` | `float*` | 色标位置数组 |

#### EvenlySpaced2StopGradientCtx - 两色均匀渐变

| 成员 | 类型 | 说明 |
|------|------|------|
| `factor[4]` | `float` | 线性插值斜率 (color1 - color0) |
| `bias[4]` | `float` | 起始颜色 (color0) |

#### UniformColorCtx - 统一颜色

| 成员 | 类型 | 说明 |
|------|------|------|
| `r, g, b, a` | `float` | 浮点颜色分量 |
| `rgba[4]` | `uint16_t` | 16 位通道表示（[0,255] 范围） |

### SkSL 专用上下文

#### BranchCtx - 分支控制

| 成员 | 类型 | 说明 |
|------|------|------|
| `offset` | `int` | 标签 ID（编译期）或程序偏移量（运行期） |

#### CaseOpCtx - Switch 语句

| 成员 | 类型 | 说明 |
|------|------|------|
| `expectedValue` | `int` | 期望的 case 值 |
| `offset` | `SkRPOffset` | 指向 {actualValue, defaultMask} 的偏移 |

#### CopyIndirectCtx - 间接拷贝

| 成员 | 类型 | 说明 |
|------|------|------|
| `dst` | `int32_t*` | 目标指针 |
| `src` | `const int32_t*` | 源指针 |
| `indirectOffset` | `const uint32_t*` | 间接偏移量 |
| `indirectLimit` | `uint32_t` | 偏移量上限（用于钳位） |
| `slots` | `uint32_t` | 拷贝的槽位数量 |

#### SwizzleCtx - 通道重排

| 成员 | 类型 | 说明 |
|------|------|------|
| `dst` | `SkRPOffset` | 目标偏移量 |
| `offsets[4]` | `uint8_t` | 字节偏移数组（预乘 4 * stride） |

**静态断言**: `kMaxStride_highp <= 16` 确保 8 位偏移量足够。

### 调试与追踪上下文

#### TraceFuncCtx - 函数追踪

| 成员 | 类型 | 说明 |
|------|------|------|
| `traceMask` | `const int*` | 追踪掩码（哪些通道被追踪） |
| `traceHook` | `SkSL::TraceHook*` | 追踪钩子对象 |
| `funcIdx` | `int` | 函数索引 |

#### TraceVarCtx - 变量追踪

| 成员 | 类型 | 说明 |
|------|------|------|
| `traceMask` | `const int*` | 追踪掩码 |
| `traceHook` | `SkSL::TraceHook*` | 追踪钩子 |
| `slotIdx` | `int` | 槽位索引 |
| `numSlots` | `int` | 槽位数量 |
| `data` | `const int*` | 变量数据 |
| `indirectOffset` | `const uint32_t*` | 间接偏移（可为 null） |
| `indirectLimit` | `uint32_t` | 偏移上限 |

### 其他专用上下文

#### PerlinNoiseCtx - Perlin 噪声

| 成员 | 类型 | 说明 |
|------|------|------|
| `noiseType` | `SkPerlinNoiseShaderType` | 噪声类型 |
| `baseFrequencyX/Y` | `float` | 基础频率 |
| `stitchDataInX/Y` | `float` | 拼接数据 |
| `stitching` | `bool` | 是否启用拼接 |
| `numOctaves` | `int` | 八度数量 |
| `latticeSelector` | `const uint8_t*` | 格子选择器（256 值） |
| `noiseData` | `const uint16_t*` | 噪声数据（4 通道 × 256 × 2） |

#### CallbackCtx - 自定义回调

| 成员 | 类型 | 说明 |
|------|------|------|
| `fn` | `void (*)(CallbackCtx*, int)` | 回调函数指针 |
| `rgba[4*kMaxStride_highp]` | `float` | 传入/传出的颜色数据 |
| `read_from` | `float*` | 读取位置指针（默认指向 rgba） |

## 公共 API 函数

该文件不包含函数，仅定义数据结构。所有结构体都是 POD（Plain Old Data）类型，用于被管道操作直接访问。

## 内部实现细节

### SIMT 执行模型的数组设计

许多上下文使用 `[kMaxStride]` 或 `[kMaxStride_highp]` 数组，对应 SIMT 模型中的"通道"：

```cpp
struct SamplerCtx {
    float x[kMaxStride_highp];  // 同时处理 16 个像素的 X 坐标
    float y[kMaxStride_highp];  // 同时处理 16 个像素的 Y 坐标
};
```

这种设计允许：
- SIMD 指令并行处理多个像素
- 减少分支和循环开销
- 更好的缓存局部性

### 尾部像素处理机制

`MemoryCtxPatch` 实现了复杂的尾部像素处理策略：

```
正常处理: [pixel0][pixel1]...[pixel15]
尾部情况: [pixel0][pixel1][pixel2][xxx][xxx]...
         ↓ 复制到 scratch
         [pixel0][pixel1][pixel2][0][0]...[0]
         ↓ 处理 16 个像素
         ↓ 复制回前 3 个
```

### 高精度 vs 低精度分离

```cpp
inline static constexpr int kMaxStride = 16;       // 低精度（U16）
inline static constexpr int kMaxStride_highp = 16; // 高精度（float）
```

某些操作仅在高精度模式下可用，可以使用更小的步长节省内存。

### 偏移量类型设计

```cpp
using SkRPOffset = uint32_t;  // 可以表示更大的槽位偏移
```

但在 `SwizzleCtx` 中使用 `uint8_t`：

```cpp
uint8_t offsets[4];  // 假设 kMaxStride_highp <= 16，8 位足够
```

这是空间优化：对于已知小范围的偏移，使用更小的类型。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkSL::TraceHook` | SkSL 调试追踪 |
| `SkRasterPipelineStage` | 堆栈检查点/回退操作 |
| `SkPerlinNoiseShaderType` | 噪声着色器类型枚举 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkRasterPipeline` | 创建和传递上下文给操作 |
| `SkRasterPipelineBlitter` | 设置各种绘制上下文 |
| 所有着色器和特效类 | 配置渐变、噪声、采样等参数 |
| SkSL 编译器 | 生成 SkSL 操作的上下文 |

## 设计模式与设计决策

### 1. 结构化编程风格

所有上下文都是纯数据结构（POD），不包含任何方法或虚函数，确保：
- 内存布局可预测
- 无虚函数表开销
- 易于在不同地址空间间传递

### 2. 缓存优化设计

```cpp
struct TileCtx {
    float scale;
    float invScale;  // 预计算 1/scale，避免除法
};
```

预计算和缓存昂贵的操作结果。

### 3. 分层设计

```cpp
struct SwizzleCopyIndirectCtx : public CopyIndirectCtx {
    uint16_t offsets[4];  // 扩展基础拷贝上下文
};
```

通过继承复用通用功能，同时保持 POD 特性。

### 4. 显式对齐控制

```cpp
std::byte scratch[kMaxScratchPerPatch];  // 确保足够的对齐
```

使用 `std::byte` 而非 `char` 明确表示原始内存。

### 5. 常量表达式计算

```cpp
inline static constexpr size_t kMaxScratchPerPatch =
    std::max(kMaxStride_highp * 16,   // 最大高精度需求
             kMaxStride * 4);         // 最大低精度需求
```

编译期计算，零运行时开销。

## 性能考量

### 1. 内存对齐

所有上下文结构体设计为缓存行友好，关键数据紧密排列：

```cpp
struct UniformColorCtx {
    float r, g, b, a;      // 连续 16 字节，单个缓存行
    uint16_t rgba[4];      // 额外的 8 字节
};
```

### 2. 数组大小选择

`kMaxStride = 16` 的选择基于：
- SIMD 寄存器宽度（AVX-512 可处理 16 个 float）
- 缓存行大小（通常 64 字节）
- 指令级并行度

### 3. 避免间接访问

大多数上下文使用直接数组而非指针，减少内存访问延迟：

```cpp
// 快速：直接访问
float x[kMaxStride_highp];

// 慢速：需要额外解引用
float* x;
```

### 4. 小对象优化

```cpp
template <typename T>
using UnpackedType = typename std::conditional<
    sizeof(T) <= sizeof(void*), T, const T&>::type;
```

小于指针大小的上下文直接按值传递（在 `SkRasterPipelineContextUtils.h` 中使用）。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkRasterPipeline.h` | 使用者 | 管道创建和执行 |
| `src/core/SkRasterPipelineOpList.h` | 配对文件 | 定义操作枚举 |
| `src/core/SkRasterPipelineBlitter.cpp` | 使用者 | 创建和配置上下文 |
| `src/core/SkRasterPipelineContextUtils.h` | 工具类 | 上下文的打包/解包工具 |
| `src/opts/SkRasterPipeline_opts.h` | 使用者 | 具体操作的 SIMD 实现 |
| `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.cpp` | 使用者 | SkSL 到管道的编译 |

## 典型使用场景

### 场景 1: 配置纹理采样

```cpp
SkRasterPipelineContexts::GatherCtx* ctx = alloc->make<GatherCtx>();
ctx->pixels = image.getPixels();
ctx->stride = image.rowBytes() / image.bytesPerPixel();
ctx->width = image.width();
ctx->height = image.height();
ctx->roundDownAtInteger = false;

pipeline.append(SkRasterPipelineOp::gather_8888, ctx);
```

### 场景 2: 设置渐变颜色

```cpp
auto ctx = alloc->make<EvenlySpaced2StopGradientCtx>();
ctx->bias[0] = color0.fR;
ctx->bias[1] = color0.fG;
ctx->bias[2] = color0.fB;
ctx->bias[3] = color0.fA;
ctx->factor[0] = color1.fR - color0.fR;
ctx->factor[1] = color1.fG - color0.fG;
ctx->factor[2] = color1.fB - color0.fB;
ctx->factor[3] = color1.fA - color0.fA;

pipeline.append(SkRasterPipelineOp::evenly_spaced_2_stop_gradient, ctx);
```

### 场景 3: SkSL 分支

```cpp
auto branchCtx = alloc->make<BranchIfAllLanesActiveCtx>();
branchCtx->offset = labelID;  // 编译时填充
branchCtx->tail = tailMaskPtr;

pipeline.append(SkRasterPipelineOp::branch_if_all_lanes_active, branchCtx);

// 编译后，labelID 会被替换为实际的程序偏移量
```
