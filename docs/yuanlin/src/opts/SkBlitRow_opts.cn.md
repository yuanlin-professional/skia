# SkBlitRow_opts

> 源文件: `src/opts/SkBlitRow_opts.h`

## 概述

`SkBlitRow_opts.h` 是 Skia 中像素行级别位块传输（blit）操作的多平台 SIMD 优化实现。它提供了两个核心函数：

1. **`blit_row_s32a_opaque`** - 将源行中的预乘 Alpha 像素以 SrcOver 混合模式绘制到目标行上（假设源完全不透明的上下文）。
2. **`blit_row_color32`** - 将一个常量预乘颜色混合到目标行的每个像素上。

这些函数是 Skia 2D 渲染引擎中最常被调用的底层像素操作之一，针对 x86（SSE2/AVX2）、ARM（NEON）和龙芯（LSX/LASX）架构都提供了专门的 SIMD 优化版本。

该文件通过 `SK_OPTS_NS` 命名空间机制，可以被编译为多个指令集版本。

## 架构位置

```
SkCanvas / SkDraw (高层绘制 API)
    |
SkBlitter (位块传输器)
    |
SkBlitRow (行级位块传输调度)
    |
blit_row_s32a_opaque / blit_row_color32  <-- 本文件提供
    |
CPU SIMD 指令 (SSE2/AVX2/NEON/LSX/LASX)
```

`SkBlitRow_opts.h` 位于 Skia 渲染管线的最底层，直接操作像素数据。它通过 SkOpts 的函数指针机制被上层的 `SkBlitRow` 调用，运行时根据 CPU 能力选择最优实现。

## 主要类与结构体

该文件不定义独立的类或结构体。所有实现以自由函数和辅助内联函数的形式提供。

### 平台特定辅助函数

| 函数名 | 平台 | 说明 |
|--------|------|------|
| `SkPMSrcOver_AVX2` | x86 AVX2 | 使用 256 位寄存器的 SrcOver 混合，一次处理 8 个像素 |
| `SkPMSrcOver_SSE2` | x86 SSE2 | 使用 128 位寄存器的 SrcOver 混合，一次处理 4 个像素 |
| `SkPMSrcOver_neon8` | ARM NEON | 使用 NEON 128 位寄存器的 SrcOver 混合，一次处理 8 个像素 |
| `SkPMSrcOver_neon2` | ARM NEON | NEON 版本，一次处理 2 个像素 |
| `SkMulDiv255Round_neon8` | ARM NEON | NEON 优化的 `(x * y + 127) / 255` 近似计算 |
| `SkPMSrcOver_LASX` | 龙芯 LASX | 使用 LASX 256 位寄存器的 SrcOver 混合 |
| `SkPMSrcOver_LSX` | 龙芯 LSX | 使用 LSX 128 位寄存器的 SrcOver 混合 |

## 公共 API 函数

### `blit_row_s32a_opaque(SkPMColor* dst, const SkPMColor* src, int len, U8CPU alpha)`

```cpp
inline void blit_row_s32a_opaque(SkPMColor* dst, const SkPMColor* src, int len, U8CPU alpha);
```

- **功能**: 以 SrcOver 混合模式将源像素行绘制到目标像素行上。
- **参数**:
  - `dst` - 目标像素缓冲区（32 位预乘 Alpha 格式）
  - `src` - 源像素缓冲区（32 位预乘 Alpha 格式）
  - `len` - 要处理的像素数量
  - `alpha` - 必须为 `0xFF`（完全不透明），在函数入口处断言检查
- **混合公式**: `result = src + dst * (1 - srcAlpha)`
- **安全注意事项**: 代码注释特别指出，为了抵御时序攻击（timing attacks），不得根据像素数据进行分支判断，禁止使用 `vptest`、`pmovmskb` 等指令跳过透明像素。

**执行流程**:
1. 优先使用当前平台最高级别的 SIMD 指令处理大块像素
2. 逐级降级到较低级别的 SIMD 指令处理剩余像素
3. 最后使用标量 `SkPMSrcOver()` 处理尾部像素

### `blit_row_color32(SkPMColor* dst, int count, SkPMColor color)`

```cpp
inline void blit_row_color32(SkPMColor* dst, int count, SkPMColor color);
```

- **功能**: 将一个常量预乘颜色以 SrcOver 模式混合到目标行的每个像素上。
- **参数**:
  - `dst` - 目标像素缓冲区
  - `count` - 要处理的像素数量
  - `color` - 要混合的常量颜色（预乘 Alpha 格式）
- **实现**: 使用 `skvx`（Skia 的跨平台 SIMD 向量库）实现，向量宽度为 4 个像素。

## 内部实现细节

### SrcOver 混合算法

所有平台的实现都采用相同的数学近似：

```
精确公式:   b = s + d * (255 - srcA) / 255
              = s + (d * (255 - srcA) + 127) / 255

近似公式:   b = s + (d * (256 - srcA)) >> 8
              = s + (d * (256 - srcA)) / 256
```

这种近似在结果上至多有 1 bit 的误差，但用移位代替了昂贵的除法运算。

### x86 SSE2 实现策略

```cpp
static inline __m128i SkPMSrcOver_SSE2(const __m128i& src, const __m128i& dst) {
    // 1. 提取 srcAlpha 并计算 scale = 256 - srcAlpha
    // 2. 将 scale 复制到每个 16 位半字
    // 3. 分离 R/B 通道（偶数字节）和 G/A 通道（奇数字节）
    // 4. 分别进行 16 位乘法和移位
    // 5. 合并结果并与 src 相加
}
```

关键优化点：将 32 位像素的 4 个 8 位通道分为两组（R+B 和 G+A），利用 16 位乘法指令一次处理两个通道，将乘法次数减半。

### x86 AVX2 实现策略

AVX2 版本与 SSE2 版本的算法原理相同，但使用 256 位寄存器，一次处理 8 个像素而非 4 个。与 SSE2 版本的主要区别在于 alpha 值的广播方式：

```cpp
// AVX2 使用 shuffle 将每个像素的 alpha 广播到两个 16 位半字
__m256i srcA_x2 = _mm256_shuffle_epi8(src,
        _mm256_setr_epi8(3,_,3,_, 7,_,7,_, 11,_,11,_, 15,_,15,_,
                         3,_,3,_, 7,_,7,_, 11,_,11,_, 15,_,15,_));
```

其中 `_` 表示填充零字节（`-1` 在 `_mm256_shuffle_epi8` 中会产生零值）。这种方式比 SSE2 版本中使用移位和 OR 组合的方式更加高效，因为 AVX2 提供了更强大的字节级 shuffle 指令。

### ARM NEON 实现策略

NEON 版本采用不同的策略：
- 使用 `vld4_u8` 以解交错方式加载像素（分离 RGBA 通道），这是 NEON 特有的高效操作。
- 使用 `vmull_u8` + `vraddhn_u16` 实现更精确的 `(x * y + 127) / 255` 计算。
- 提供 8 像素（`SkPMSrcOver_neon8`）和 2 像素（`SkPMSrcOver_neon2`）两个版本，后者处理尾部数据。

### 龙芯 LSX/LASX 实现

LSX（128 位）和 LASX（256 位）版本的算法与 x86 SSE2/AVX2 类似，使用龙芯特有的 SIMD 指令集实现相同的数学运算。具体使用的核心指令包括：

- `__lasx_xvsub_w` / `__lsx_vsub_w` - 32 位整数减法，用于计算 `256 - srcAlpha`
- `__lasx_xvmul_h` / `__lsx_vmul_h` - 16 位整数乘法，用于通道缩放
- `__lasx_xvsadd_bu` / `__lsx_vsadd_bu` - 8 位无符号饱和加法，用于最终合并
- `__lasx_xvor_v` / `__lsx_vor_v` - 按位 OR，用于合并红蓝和绿透通道

LASX 一次处理 8 个像素（256 位），LSX 一次处理 4 个像素（128 位），与 x86 的 AVX2/SSE2 吞吐量对应。

### blit_row_color32 的 skvx 实现

该函数使用 Skia 的跨平台向量库 `skvx`，不依赖平台特定的 intrinsic：

```cpp
constexpr int N = 4;
using U32 = skvx::Vec<N, uint32_t>;
using U16 = skvx::Vec<4*N, uint16_t>;
using U8  = skvx::Vec<4*N, uint8_t>;
```

通过 `sk_bit_cast` 在 `U32`（4 个像素）和 `U8`（16 个字节通道）之间重新解释，然后使用 `mull`（乘法扩展到 16 位）和移位实现混合运算。该实现自动受益于编译器的 SIMD 自动向量化。

核心混合内核使用 lambda 表达式实现：

```cpp
auto kernel = [color](U32 src) {
    unsigned invA = SkAlpha255To256(255 - SkGetPackedA32(color));
    U8 s = sk_bit_cast<U8>(src), a = U8(invA);
    U16 c = skvx::cast<uint16_t>(sk_bit_cast<U8>(U32(color))),
        r = (mull(s, a) >> 8) + c;
    return sk_bit_cast<U32>(skvx::cast<uint8_t>(r));
};
```

该 lambda 将目标像素按反向 alpha 缩放后加上颜色值，实现 SrcOver 混合。`invA` 使用 `SkAlpha255To256` 转换到 [1,256] 范围以启用移位除法优化。

### 分层降级模式

`blit_row_s32a_opaque` 在同一函数体内实现了逐级降级：

```
x86:  AVX2 (8px) -> SSE2 (4px) -> 标量 (1px)
ARM:  NEON 8px -> NEON 2px -> NEON 1px (使用2px版本)
龙芯: LASX (8px) -> LSX (4px) -> 标量 (1px)
```

每级处理后更新指针和计数器，剩余像素交给下一级处理。

## 依赖关系

- `src/base/SkMSAN.h` - MemorySanitizer 断言（`sk_msan_assert_initialized`）
- `src/base/SkVx.h` - Skia 跨平台 SIMD 向量库（`skvx`）
- `src/core/SkColorData.h` - 颜色数据操作函数（`SkPMSrcOver`、`SkAlpha255To256`、`SkGetPackedA32` 等）
- `<immintrin.h>` - x86 SIMD intrinsic（SSE2/AVX2）
- `<arm_neon.h>` - ARM NEON intrinsic
- `<lasxintrin.h>` / `<lsxintrin.h>` - 龙芯 SIMD intrinsic

## 设计模式与设计决策

### 抗时序攻击设计
文件开头的注释明确要求"不要基于像素数据进行分支"。这意味着即使源像素完全透明（alpha=0），也不能跳过混合计算。这种设计防止了通过测量渲染时间来推断图像内容的侧信道攻击。

### 近似而非精确
选择 `(d * (256 - srcA)) >> 8` 而非精确的 `(d * (255 - srcA) + 127) / 255`，用极小的精度损失换取了显著的性能提升（移位替代除法）。

### 平台特定与跨平台混合
低级辅助函数使用平台特定的 intrinsic，而 `blit_row_color32` 使用跨平台的 `skvx` 库。这体现了 Skia 在性能关键路径上使用手写 SIMD，在次关键路径上使用抽象层的务实策略。

### 命名空间隔离
所有函数都在 `SK_OPTS_NS` 命名空间内定义，确保不同指令集版本不会产生符号冲突。

## 性能考量

- **向量宽度**: AVX2/LASX 一次处理 8 个像素（256 位），SSE2/LSX 处理 4 个像素（128 位），NEON 处理 8 个像素（128 位，但使用解交错加载）。
- **16 位乘法优化**: 将 32 位像素通道拆分为两组 16 位通道，乘法吞吐量提升一倍。
- **内存对齐**: 使用 unaligned load/store（`_mm_loadu_si128`、`_mm256_loadu_si256`），避免对齐要求带来的额外处理开销，现代 CPU 上非对齐访问惩罚已很小。
- **NEON 解交错**: ARM NEON 的 `vld4_u8` 指令可以在加载时自动将 RGBA 分离到独立向量中，这是 NEON 架构的独特优势。
- **尾部处理**: 各平台通过逐级降级到更窄的向量或标量处理，避免了对齐填充和掩码操作的复杂性。
- **blit_row_color32 的 N=4**: 向量宽度选择 4 像素，注释中提到 8 和 16 也是合理选择，但 4 在代码大小和性能之间取得了较好平衡。

## 相关文件

- `src/core/SkBlitRow.h` - 行级位块传输的公共接口声明
- `src/core/SkColorData.h` - 颜色数据操作和标量 `SkPMSrcOver` 实现
- `src/base/SkVx.h` - Skia 跨平台 SIMD 向量库
- `src/opts/SkBlitMask_opts.h` - 遮罩位块传输的优化实现（类似架构）
- `src/opts/SkOpts_SetTarget.h` - 编译目标设置
- `src/core/SkOpts.h` - 优化函数指针注册
