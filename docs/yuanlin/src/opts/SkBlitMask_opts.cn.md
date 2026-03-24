# SkBlitMask_opts

> 源文件: `src/opts/SkBlitMask_opts.h`

## 概述

`SkBlitMask_opts.h` 是 Skia 中遮罩位块传输（mask blit）操作的多平台 SIMD 优化实现。该文件专注于将带有 Alpha 遮罩（A8 格式）的颜色绘制到 32 位预乘 Alpha 目标表面（D32 格式）上。

这是文本渲染和抗锯齿图形绘制中最核心的操作之一。在文本渲染中，字形的灰度遮罩（glyph mask）需要与指定颜色混合后绘制到帧缓冲区，该文件提供的函数正是完成这一步骤的底层实现。

该文件针对三大 CPU 架构提供了优化实现：
- **ARM NEON** - 使用 NEON SIMD 指令的手写优化
- **龙芯 LSX** - 使用 LSX（Loongson SIMD Extension）指令的手写优化
- **通用平台** - 使用 `Sk4px` 抽象层的跨平台实现（包括 x86 SSE）

## 架构位置

```
SkCanvas::drawText / SkCanvas::drawPath (高层绘制 API)
    |
SkBlitter / SkA8_Coverage_Blitter (位块传输器)
    |
blit_mask_d32_a8 (遮罩混合调度)  <-- 本文件提供
    |
    +-- blit_mask_d32_a8_black   (黑色特化)
    +-- blit_mask_d32_a8_opaque  (不透明色特化)
    +-- blit_mask_d32_a8_general (通用半透明色)
    |
CPU SIMD 指令 / Sk4px 抽象层
```

`SkBlitMask_opts.h` 位于 Skia 渲染管线的底层，通过 SkOpts 的函数指针分发机制被上层 blitter 调用。

## 主要类与结构体

该文件不定义独立的类或结构体。实现以静态函数和内联函数的形式提供，全部位于 `SK_OPTS_NS` 命名空间中。

### NEON 平台辅助函数

| 函数名 | 说明 |
|--------|------|
| `SkAlpha255To256_neon8` | 将 8 个 alpha 值从 [0,255] 转换为 [1,256] 范围，便于后续移位除法 |
| `SkAlphaMul_neon8` | 对 8 个 8 位颜色值执行 alpha 乘法：`(color * scale) >> 8` |
| `SkAlphaMulQ_neon8` | 对一个包含 4 通道 x 8 像素的结构体执行 alpha 乘法 |

### LSX 平台辅助函数

| 函数名 | 说明 |
|--------|------|
| `SkAlphaMul_lsx` | 使用 LSX 指令实现的 16 位 alpha 乘法：`(x * y) >> 8`，结果取高字节 |

## 公共 API 函数

### `blit_mask_d32_a8`（调度入口）

```cpp
inline void blit_mask_d32_a8(SkPMColor* dst, size_t dstRB,
                             const SkAlpha* mask, size_t maskRB,
                             SkColor color, int w, int h);
```

- **功能**: 根据颜色类型选择最优的特化路径进行遮罩混合。
- **参数**:
  - `dst` - 目标像素缓冲区（32 位预乘 Alpha 格式）
  - `dstRB` - 目标缓冲区行字节跨度（row bytes）
  - `mask` - Alpha 遮罩缓冲区（8 位灰度）
  - `maskRB` - 遮罩缓冲区行字节跨度
  - `color` - 要绘制的颜色（非预乘的 `SkColor` 格式）
  - `w`, `h` - 区域宽度和高度
- **分发逻辑**:
  - 颜色为 `SK_ColorBLACK` -> `blit_mask_d32_a8_black()`
  - 颜色 alpha 为 0xFF（完全不透明） -> `blit_mask_d32_a8_opaque()`
  - 其他情况 -> `blit_mask_d32_a8_general()`

### `blit_mask_d32_a8_general`

处理最通用的情况：颜色可以是任意半透明值。

**混合公式**:
```
result = color * mask_alpha + dst * (1 - color_alpha * mask_alpha)
       = s * aa + d * (1 - sa * aa)
```

### `blit_mask_d32_a8_opaque`

处理颜色完全不透明（alpha = 255）的优化情况。由于 `sa = 1`，公式简化为：

```
result = s * aa + d * (1 - aa)
```

### `blit_mask_d32_a8_black`

处理颜色为纯黑色的最简化情况。由于 `s = (0, 0, 0, 1)`，公式进一步简化为：

```
alpha_result = aa + d_alpha * (1 - aa)
color_result = d_color * (1 - aa)
```

## 内部实现细节

### NEON 实现 (`blit_mask_d32_a8_neon`)

这是一个模板函数，通过 `isTranslucent` 模板参数区分半透明和不透明两种情况：

```cpp
template <bool isTranslucent>
static void blit_mask_d32_a8_neon(void* dst, size_t dstRB, ...);
```

**处理流程**:
1. 将颜色预乘为 `SkPMColor`，拆分为 ARGB 四个通道的 NEON 向量。
2. 外层循环遍历每行。
3. 内层循环每次处理 8 个像素：
   - 使用 `vld1_u8` 加载 8 个遮罩值
   - 将遮罩值转换为 [1,256] 范围的缩放因子
   - 计算反向缩放因子 `vscale`：
     - 半透明模式: `256 - SkAlphaMul(colorAlpha, mask256)`
     - 不透明模式: `256 - mask`
   - 使用 `vld4_u8` 解交错加载 8 个目标像素
   - 对每个通道执行: `result = color_channel * mask256 + dst_channel * vscale`
   - 使用 `vst4_u8` 交错存储结果
4. 标量处理剩余不足 8 个的像素。

**Nine Patch 特殊处理**: 代码注释指出 Nine Patch 可能将 `maskRB` 设为 0 以重复使用同一行遮罩数据。通过 `mask_adjust = maskRB - width` 计算来兼容这种情况。

### LSX 实现 (`blit_mask_d32_a8_lsx`)

LSX 实现的策略与 NEON 不同，因为 LSX 没有直接的解交错加载指令：

1. 使用 `__lsx_vld` 加载两组 4 个像素（共 8 个像素）。
2. 通过 `__lsx_vshuf_b` shuffle 指令将交错的 BGRA 数据重排为平面格式（分离各通道）。
3. 使用 `__lsx_vilvl_w` / `__lsx_vilvh_w` 交错组合低位和高位。
4. 扩展到 16 位进行乘法运算。
5. 计算完成后，通过逆向的交错操作重新组合为 BGRA 格式。

这个 shuffle + interleave 的过程比较复杂，使用了预定义的 `planar` shuffle 掩码：
```cpp
planar = __lsx_vinsgr2vr_d(planar, 0x0d0905010c080400, 0);  // B G R A 索引
planar = __lsx_vinsgr2vr_d(planar, 0x0f0b07030e0a0602, 1);
```

### 通用平台实现（Sk4px）

在没有专用 NEON 或 LSX 实现的平台上（包括 x86），使用 `Sk4px` 抽象层：

```cpp
auto s = Sk4px::DupPMColor(SkPreMultiplyColor(color));
auto fn = [&](const Sk4px& d, const Sk4px& aa) {
    auto left  = s.approxMulDiv255(aa),
         right = d.approxMulDiv255(left.alphas().inv());
    return left + right;
};
Sk4px::MapDstAlpha(w, dst, mask, fn);
```

`Sk4px` 封装了 4 个像素的 SIMD 操作，`MapDstAlpha` 自动处理循环和尾部像素。代码非常简洁但仍能利用底层 SIMD 指令。

**不透明色优化**: 当 `colorAlpha == 255` 时，`sa * aa = aa`，因此反向缩放因子简化为 `1 - aa`，避免了一次额外的乘法。

**黑色优化**: 当颜色为纯黑时，只有 alpha 通道需要设置为遮罩值，RGB 通道只需缩放目标像素。使用位与操作 `(aa & mask_pattern)` 直接提取 alpha 通道。

### 三级特化策略

```
blit_mask_d32_a8 (调度入口)
    |
    +-- black:   最简单，省略颜色乘法，alpha 直接赋值
    +-- opaque:  较简单，缩放因子简化为 (1 - mask)
    +-- general: 完整计算，缩放因子为 (1 - colorAlpha * mask)
```

这种三级特化利用了文本渲染中的常见模式：黑色文本最为常见，其次是不透明彩色文本，半透明文本较少。

## 依赖关系

### 直接依赖
- `include/private/base/SkFeatures.h` - CPU 特性检测宏
- `src/core/Sk4px.h` - 4 像素 SIMD 抽象层（通用平台实现使用）
- `<arm_neon.h>` - ARM NEON intrinsic（NEON 平台）
- `<lsxintrin.h>` - 龙芯 LSX intrinsic（LSX 平台）

### 间接依赖
- `src/core/SkColorData.h` - 颜色操作函数（`SkPreMultiplyColor`、`SkAlphaMulQ` 等）
- `src/base/SkVx.h` - 底层 SIMD 向量类型（`Sk4px` 基于此）

## 设计模式与设计决策

### 模板特化替代运行时分支
NEON 和 LSX 的实现使用 `template <bool isTranslucent>` 模板参数，在编译时消除半透明/不透明的条件判断分支。编译器可以为两种情况生成完全独立的优化代码路径。

### 平台抽象的分层
- **最高性能层**: NEON 和 LSX 使用平台特定 intrinsic，手动控制每条 SIMD 指令。
- **高性能抽象层**: 通用平台使用 `Sk4px`，代码简洁但仍能利用 SIMD。
- **标量回退**: 每个 SIMD 循环后都有标量处理尾部的代码。

### 特化路径选择
在入口函数 `blit_mask_d32_a8` 中使用简单的 `if-else` 链根据颜色特性选择路径。由于每次调用通常处理大量像素，分支预测开销相对可忽略。

### Nine Patch 兼容设计
通过 `mask_adjust = maskRB - width` 的计算方式，优雅地处理了 `maskRB = 0` 的特殊情况（重复使用同一行遮罩），无需额外的条件判断。

### 注释驱动的公式推导
代码中大量使用注释展示混合公式的数学推导过程，从通用公式到各特化情况的简化步骤都有清晰记录，大大提升了代码的可维护性。

## 性能考量

- **NEON 解交错加载**: `vld4_u8` 在加载时自动将 RGBA 通道分离到 4 个独立向量中，是 ARM 架构的独特优势，避免了 shuffle 操作的开销。
- **LSX 平面化重排**: 由于缺少解交错加载指令，LSX 实现需要额外的 shuffle 和 interleave 步骤，代码复杂度和指令数量都显著高于 NEON 版本。
- **向量宽度**: NEON 每次处理 8 个像素（使用 64 位寄存器对），LSX 也处理 8 个像素（两个 128 位加载），通用 Sk4px 版本每次处理 4 个像素。
- **Alpha 范围转换**: 将 alpha 从 [0,255] 转换为 [1,256]（`SkAlpha255To256`），使得后续可以用移位除以 256 代替除以 255，这是一个经典的性能优化技巧。
- **三级特化的收益**:
  - 黑色路径省略了所有颜色通道的乘法运算
  - 不透明路径省略了 `colorAlpha * mask` 的乘法
  - 在文本渲染场景中，黑色文本占比很高，特化收益显著
- **Sk4px::MapDstAlpha**: 该函数内部自动处理了 SIMD 循环和标量尾部，编译器可以针对具体平台进行自动向量化优化。
- **行间指针调整**: 使用 `(char*)device + dstRB` 进行字节级指针调整，正确处理了目标缓冲区行间可能存在的填充字节。

## 相关文件

- `src/core/Sk4px.h` - 4 像素 SIMD 抽象类，通用平台实现的基础
- `src/opts/SkBlitRow_opts.h` - 行级位块传输优化（类似架构，SrcOver 混合）
- `src/core/SkColorData.h` - 颜色数据操作函数
- `src/core/SkOpts.h` - 优化函数指针注册和运行时分发
- `src/opts/SkOpts_SetTarget.h` - 编译目标设置（`SK_OPTS_NS` 命名空间定义）
- `include/private/base/SkFeatures.h` - CPU 特性检测宏
