# SkBitmapProcState_opts

> 源文件: `src/opts/SkBitmapProcState_opts.h`

## 概述

`SkBitmapProcState_opts.h` 是 Skia 图形库中位图处理状态（SkBitmapProcState）的平台优化实现头文件。该文件主要提供了 **双线性插值滤波（Bilinear Filtering）** 的 SIMD 优化版本，用于在位图缩放、旋转等变换操作中对像素进行高质量的重采样。

本文件包含了针对 5 种不同指令集架构的优化实现：

1. **SSSE3**（Intel/AMD x86，128 位 + `_mm_maddubs_epi16`）
2. **SSE2**（Intel/AMD x86，基线 128 位）
3. **LASX**（龙芯 LoongArch，256 位）
4. **LSX**（龙芯 LoongArch，128 位）
5. **NEON**（ARM，128 位）
6. **便携式 C++ 标量实现**（回退方案）

核心函数 `S32_alpha_D32_filter_DX` 处理的是 32 位 ARGB 格式像素在 X 方向上的双线性插值滤波，同时支持可选的 alpha 缩放。这是位图渲染管线中最性能关键的路径之一。

## 架构位置

该文件位于 `src/opts/` 目录，属于 Skia 的 **像素处理优化层**，介于核心位图绘制逻辑与底层 SIMD 指令之间：

```
SkCanvas::drawBitmap() / drawImage()
  -> SkDraw::drawBitmap()
       -> SkBitmapProcShader
            -> SkBitmapProcState（位图采样状态机）
                 -> S32_alpha_D32_filter_DX()   <-- 本文件中的优化函数
                      -> SIMD 双线性插值计算
```

`SkBitmapProcState` 是位图采样的核心状态类，它根据变换矩阵和滤波模式选择合适的采样函数。本文件中的优化函数通过 SkOpts 机制被注册为采样回调。

## 主要类与结构体

### 坐标编码方案

本文件中最重要的数据结构概念是 **打包坐标格式**（Packed Coordinates）。每个 32 位 `uint32_t` 值编码了两个整数坐标和一个插值权重：

```
位布局（32位）:
  [31:18]  v0 - 整数坐标 0（14 位）
  [17:14]  w  - 插值权重（4 位，范围 0-15）
  [13:0]   v1 - 整数坐标 1（14 位）
```

这种紧凑的编码方式减少了数据传输量，并允许使用 SIMD 位操作高效地批量解码。

### 辅助模板函数

#### `decode_packed_coordinates_and_weight`

```cpp
template <typename U32, typename Out>
static void decode_packed_coordinates_and_weight(U32 packed, Out* v0, Out* v1, Out* w);
```

从打包的 32 位值中解码出两个整数坐标和一个插值权重。该函数被所有平台实现共享。

| 参数 | 说明 |
|------|------|
| `packed` | 打包的坐标值 |
| `v0` | 输出: 整数坐标 0（源像素左/上方） |
| `v1` | 输出: 整数坐标 1（源像素右/下方） |
| `w` | 输出: 插值权重（0-15，用于 v1 方向） |

## 公共 API 函数

### `S32_alpha_D32_filter_DX`

```cpp
void S32_alpha_D32_filter_DX(const SkBitmapProcState& s,
                              const uint32_t* xy, int count, uint32_t* colors);
```

核心的双线性插值滤波函数，沿 X 方向（DX = 仅在 X 方向有变化）处理 32 位像素数据。

**参数**:

| 参数 | 说明 |
|------|------|
| `s` | 位图处理状态，包含源像素数据、行字节数、alpha 缩放因子等 |
| `xy` | 打包坐标数组。第一个元素编码 Y 坐标对和 Y 权重，后续元素编码 X 坐标对和 X 权重 |
| `count` | 需要输出的像素数量 |
| `colors` | 输出像素缓冲区 |

**前置条件**（断言）:
- `count > 0 && colors != nullptr`
- `s.fBilerp == true`（双线性插值模式）
- 像素格式为 `kN32_SkColorType`（32 位本机颜色类型）
- `s.fAlphaScale <= 256`

### `S32_alpha_D32_filter_DXDY`

```cpp
void S32_alpha_D32_filter_DXDY(const SkBitmapProcState& s,
                                const uint32_t* xy, int count, SkPMColor* colors);
```

在 X 和 Y 方向都有变化的双线性插值滤波函数。仅在 ARM NEON 平台上有专门的优化实现，其他平台设置为 `nullptr`。

**与 `_DX` 版本的区别**: `_DXDY` 版本中每个像素的 Y 坐标可以不同（例如在旋转或透视变换中），因此 `xy` 数组中每个像素需要两个打包值（一个 Y 坐标对 + 一个 X 坐标对）。

## 内部实现细节

### SSSE3 实现（x86，最快路径）

SSSE3 实现是最精细的优化版本，利用了 `_mm_maddubs_epi16()` 指令的独特能力。

#### 核心思路

`_mm_maddubs_epi16` 接受两个交错排列的字节数组，对每对字节执行乘法并将相邻对的乘积相加，生成 16 位结果。这非常适合双线性插值的加权求和操作。

#### 批处理优化（4 像素一批）

SSSE3 版本中，主循环一次处理 4 个像素：

1. 使用 `_mm_loadu_si128` 一次加载 4 个打包坐标
2. 使用 SIMD 位操作批量解码坐标和权重
3. 利用 `_mm_shuffle_epi8`（SSSE3 独有指令）将权重广播到每个颜色通道
4. 使用 `interpolate_in_x` Lambda 函数进行 X 方向插值（`_mm_maddubs_epi16`）
5. 使用 `interpolate_in_x_and_y` Lambda 函数完成 Y 方向插值（移位和乘法组合）
6. `_mm_packus_epi16` 打包回 8 位并存储

#### 插值公式优化

Y 方向插值使用了代数优化：

```
result = top * (16 - wy) + bot * wy
       = 16 * top + (bot - top) * wy    // 减少一次乘法
```

#### 尾部处理

不足 4 个的剩余像素逐个处理，使用与批处理相同的插值函数，但 B 像素位置填零。

### SSE2 实现（x86 基线）

SSE2 版本采用逐像素处理策略，没有批处理优化。

#### 数据布局

将 4 个插值像素（左上 tl、右上 tr、左下 bl、右下 br）排列为 "左组" L 和 "右组" R：

```
L = [bl, tl]（128 位寄存器的低 64 位和高 64 位）
R = [br, tr]
```

#### 插值公式

```
sum = allY * (16*L + (R-L)*wx)
```

其中 `allY` 是预先计算好的 Y 方向权重向量 `[wy, 16-wy]`。然后通过 128 位寄存器内的水平加法完成最终求和。

### LASX 实现（龙芯 256 位）

使用龙芯的 LASX（256 位向量）指令集，算法结构与 SSE2 版本相似。主要差异在于使用 `__lasx_xv*` 系列内建函数：

- `__lasx_xvreplgr2vr_h` - 标量广播到向量
- `__lasx_xvilvl_b` / `__lasx_xvilvl_w` - 交错排列
- `__lasx_xvadd_h` / `__lasx_xvmul_h` / `__lasx_xvsub_h` - 向量算术
- `__lasx_xvpickev_b` / `__lasx_xvsat_hu` - 打包和饱和

### LSX 实现（龙芯 128 位）

与 LASX 版本结构完全一致，但使用 128 位的 `__lsx_v*` 系列指令而非 256 位的 `__lasx_xv*` 指令。

### NEON 实现（ARM）

ARM NEON 版本通过独立的 `filter_and_scale_by_alpha` 辅助函数实现，利用 NEON 特有的指令：

- `vmull_u8` - 无符号 8 位乘法扩展为 16 位
- `vmla_u16` - 乘法累加
- `vshrn_n_u16` - 窄化移位

NEON 版本同时提供了 `S32_alpha_D32_filter_DXDY` 的优化实现。

### 便携式 C++ 标量实现

当没有可用的 SIMD 指令集时，使用纯 C++ 标量代码实现。利用 `0xFF00FF` 掩码技巧同时处理两个颜色通道：

```cpp
const uint32_t mask = 0xFF00FF;
uint32_t lo = (a00 & mask) * scale;      // 同时处理 R 和 B 通道
uint32_t hi = ((a00 >> 8) & mask) * scale; // 同时处理 G 和 A 通道
```

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `src/base/SkMSAN.h` | Memory Sanitizer 支持 |
| `src/base/SkVx.h` | Skia 跨平台向量抽象（本文件中未直接使用 skvx，但作为通用依赖包含） |
| `src/core/SkBitmapProcState.h` | 位图处理状态类定义 |
| `<immintrin.h>` | Intel SSE/AVX 内建函数（x86 平台） |
| `<arm_neon.h>` | ARM NEON 内建函数（ARM 平台） |
| `<lasxintrin.h>` | 龙芯 LASX 内建函数（LoongArch 平台） |
| `<lsxintrin.h>` | 龙芯 LSX 内建函数（LoongArch 平台） |

## 设计模式与设计决策

### 条件编译多路实现

文件使用 `#if / #elif / #else` 预处理器链来选择编译路径，确保每个编译单元只包含一种实现。优先级顺序为：

```
SSSE3 > SSE2 > LASX > LSX > NEON/Portable
```

这种设计意味着在 x86 平台上，如果编译器支持 SSSE3，则会使用 SSSE3 版本（即使 AVX2 可用时也如此，因为 AVX2 隐含 SSSE3 支持）。

### DX vs DXDY 分离

将仅 X 方向变化（`_DX`，对应仅缩放变换）和 X/Y 双方向变化（`_DXDY`，对应旋转/透视变换）分开优化。`_DX` 版本可以在循环外预计算 Y 坐标和权重，减少每像素的计算量。

### Lambda 函数封装（SSSE3）

SSSE3 版本使用 Lambda 函数 `interpolate_in_x` 和 `interpolate_in_x_and_y` 封装插值逻辑，使代码层次清晰。编译器会将这些 Lambda 内联，不会产生函数调用开销。

### 代数优化

所有实现都使用了相同的代数优化，将 `a*(16-w) + b*w` 重写为 `16*a + (b-a)*w`，用移位替代一次乘法。这在 SIMD 代码中尤其有价值，因为移位操作的延迟通常低于乘法。

### 测试辅助命名空间

文件末尾提供了 `sktests` 命名空间中的 `decode_packed_coordinates_and_weight` 转发函数，允许单元测试直接验证坐标解码逻辑，而无需绕过 `SK_OPTS_NS` 的命名空间隔离。

### DXDY 的选择性优化

`S32_alpha_D32_filter_DXDY` 仅在 ARM NEON 上有优化实现，其他平台设置为 `nullptr`。代码注释说明 "暂不清楚为其他架构做特化是否值得"。这反映了一种实用主义的优化策略：只在性能分析证明有价值的地方投入优化工作。

## 性能考量

### 批处理 vs 逐像素

| 实现 | 批处理大小 | 每像素吞吐量 |
|------|-----------|-------------|
| SSSE3 | 4 像素/批 | 最高（利用 `_mm_maddubs_epi16` 并行度） |
| SSE2 | 1 像素 | 中等 |
| LASX | 1 像素 | 中等（256 位寄存器未充分利用） |
| LSX | 1 像素 | 中等 |
| NEON | 1 像素 | 中等 |
| 标量 | 1 像素 | 最低 |

SSSE3 版本通过 4 像素批处理获得了最高的单指令吞吐量。其他平台的 SIMD 版本虽然也使用了向量化，但每次循环迭代只产生一个像素，向量寄存器并未被充分利用。

### 内存访问模式

- **DX 模式**: Y 坐标固定，每个像素只需访问两行数据。两行的基地址在循环外预计算，循环内只需使用 X 坐标索引
- **DXDY 模式**: 每个像素可能访问不同的两行，缓存局部性较差

### Alpha 缩放优化

Alpha 缩放（`s.fAlphaScale`）使用条件判断避免在 `fAlphaScale == 256`（完全不透明）时执行不必要的乘法操作：

```cpp
if (s.fAlphaScale < 256) {
    // 仅在需要时执行 alpha 乘法
}
```

### 权重范围

插值权重范围为 [0, 15]（4 位），总权重为 16x16 = 256，恰好可以通过右移 8 位（除以 256）来归一化。这个选择使得归一化操作可以用移位代替除法。

### 数值精度

16 位中间结果对于 8 位输入的双线性插值是足够的：最大中间值为 255 * 16 * 16 = 65280，不超过 16 位无符号整数的范围（65535）。

## 相关文件

- `src/core/SkBitmapProcState.h` - `SkBitmapProcState` 类定义
- `src/core/SkBitmapProcState.cpp` - 位图处理状态的核心实现
- `src/core/SkBitmapProcState_matrixProcs.cpp` - 矩阵变换相关的采样函数
- `src/base/SkVx.h` - Skia 跨平台 SIMD 向量抽象
- `src/base/SkMSAN.h` - Memory Sanitizer 辅助
- `src/core/SkOpts.h` - SkOpts 函数指针声明
- `src/core/SkOpts.cpp` - 优化函数指针的默认初始化
- `include/core/SkColorType.h` - `kN32_SkColorType` 等颜色类型定义
