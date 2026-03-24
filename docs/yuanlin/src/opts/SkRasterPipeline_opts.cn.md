# SkRasterPipeline_opts

> 源文件: `src/opts/SkRasterPipeline_opts.h`

## 概述

SkRasterPipeline_opts.h 是 Skia 光栅渲染管线的核心性能热点文件，包含了所有管线阶段（pipeline stages）的平台特定 SIMD 优化实现。该文件通过条件编译为不同的 CPU 架构（Scalar、NEON、SSE2、SSE4.1、AVX、HSW/AVX2、SKX/AVX-512、LSX、LASX）生成专门优化的代码。

光栅管线是 Skia 软件渲染器的核心执行引擎。每个绘图操作被分解为一系列简单的"阶段"函数，这些函数按顺序处理像素数据。每个阶段接收一批像素的颜色值（r, g, b, a）和目标颜色值（dr, dg, db, da），执行特定操作后传递给下一个阶段。

该文件约 7029 行，是 Skia 中最大的单一头文件之一。它的设计目标是在保持跨平台可移植性的同时，最大化每个平台的 SIMD 吞吐量。

**注意**：该文件使用了独立的 SIMD 向量类型（基于编译器向量扩展），而非 `skvx::Vec`，因为后者的内存布局不允许值通过寄存器传递，而管线的核心设计原则是让参数通过硬件寄存器传递以获得最优性能。

## 架构位置

```
SkCanvas::drawXxx()
    │
    ▼
SkDevice::drawXxx()
    │
    ▼
SkRasterPipeline (管线构建)
    │
    ├── 附加阶段: seed_shader, matrix, sampler, blend, store
    │
    ▼
SkRasterPipeline_opts.h (阶段执行)    ← 本文件
    │
    ├── Highp 阶段 (浮点精度, 4/8/16 通道)
    └── Lowp 阶段 (8-bit 定点精度, 8/16 通道)
```

SkRasterPipeline_opts.h 位于 Skia 渲染管线的最底层，是 CPU 光栅化的实际执行点。上层的 SkRasterPipeline 负责组装阶段序列，而本文件提供每个阶段的具体实现。

## 主要类与结构体

### 向量类型体系
文件定义了两套平台相关的向量类型系统：

**Highp（高精度）向量类型：**
```cpp
// 平台宽度取决于 CPU 架构
// Scalar: 1 通道, NEON: 4 通道, SSE: 4 通道, AVX: 8 通道, SKX: 16 通道
using F   = Vec<N, float>;       // 浮点向量
using I32 = Vec<N, int32_t>;     // 有符号整数向量
using U32 = Vec<N, uint32_t>;    // 无符号整数向量
using U64 = Vec<N, uint64_t>;    // 64位无符号整数向量
using U16 = Vec<N, uint16_t>;    // 16位无符号整数向量
using U8  = Vec<N, uint8_t>;     // 8位无符号整数向量
```

**Lowp（低精度）向量类型：**
```cpp
// 在 lowp 命名空间中，使用 uint16_t 表示 [0, 255] 范围的颜色值
// SKX/HSW: 16 通道, 其他: 8 通道
using U16 = V<uint16_t>;  // 颜色通道值
using U8  = V<uint8_t>;   // 8-bit 打包值
using I32 = V<int32_t>;   // 坐标等
```

### Vec 模板
```cpp
// 基于编译器向量扩展（而非 skvx::Vec）
template <int N, typename T> using Vec = T __attribute__((ext_vector_type(N)));  // Clang
template <int N, typename T> using Vec = typename VecHelper<N, T>::V;             // GCC
```

### Ctx 结构体
```cpp
struct Ctx {
    SkRasterPipelineStage* fStage;
    template <typename T> operator T*();  // 自动类型转换获取上下文指针
};
```
用于从管线阶段中提取上下文数据指针，支持隐式类型转换以简化阶段函数的参数访问。

### 阶段类型宏
- `HIGHP_STAGE(name, ctx)` — 定义高精度阶段（浮点像素处理）
- `HIGHP_TAIL_STAGE(name, ctx)` — 定义高精度尾部阶段（SkSL 运行时效果）
- `LOWP_STAGE_PP(name, ctx)` — 低精度像素到像素阶段
- `LOWP_STAGE_GP(name, ctx)` — 低精度几何到像素阶段
- `LOWP_STAGE_GG(name, ctx)` — 低精度几何到几何阶段

## 公共 API 函数

该文件不导出公共 API，所有函数都标记为 `static inline`（通过 `SI` 宏），仅在编译单元内可见。阶段函数通过函数指针被 SkRasterPipeline 运行时发现和调用。

### 平台特定基础函数
每个平台实现以下核心操作：

| 函数 | 说明 |
|------|------|
| `min(a, b)` / `max(a, b)` | 逐元素最小/最大值 |
| `mad(f, m, a)` | 融合乘加 (f*m + a) |
| `nmad(f, m, a)` | 融合负乘加 (a - f*m) |
| `abs_(v)` | 绝对值 |
| `floor_(v)` / `ceil_(v)` | 向下/向上取整 |
| `sqrt_(v)` | 平方根 |
| `rcp_approx(v)` | 倒数近似（12 位精度） |
| `rcp_precise(v)` | 倒数精确值 |
| `rsqrt_approx(v)` | 平方根倒数近似 |
| `round(v)` / `iround(v)` | 四舍五入（无符号/有符号） |
| `pack(v)` | 窄化打包（U32→U16, U16→U8） |
| `if_then_else(c, t, e)` | 分通道条件选择 |
| `any(c)` / `all(c)` | 向量化布尔测试 |
| `gather(ptr, ix)` | 聚集加载（根据索引数组加载离散数据） |
| `load2/4(ptr, ...)` | 交错解交错加载 |
| `store2/4(ptr, ...)` | 交错存储 |

### 重要管线阶段

**初始化阶段：**
| 阶段 | 说明 |
|------|------|
| `seed_shader` | 初始化着色器坐标 (r=x+0.5, g=y+0.5, b=1, a=0) |
| `uniform_color` | 加载统一颜色到 r,g,b,a |
| `black_color` / `white_color` | 设置不透明黑色/白色 |

**颜色操作阶段：**
| 阶段 | 说明 |
|------|------|
| `premul` / `unpremul` | 预乘/反预乘 Alpha |
| `clamp_01` / `clamp_gamut` | 将颜色值限制到 [0,1] 或 [0,a] |
| `swap_rb` | 交换红蓝通道 |
| `move_src_dst` / `move_dst_src` / `swap_src_dst` | 源目标寄存器交换 |
| `force_opaque` | 强制 alpha = 1 |
| `set_rgb` | 设置 RGB 值 |

**混合模式阶段：**
使用 `BLEND_MODE` 宏统一定义，每种模式生成一个逐通道处理函数：
| 阶段 | 说明 |
|------|------|
| `clear` | 清除 |
| `srcover` / `dstover` | 源覆盖 / 目标覆盖 |
| `srcin` / `dstin` | 源内 / 目标内 |
| `srcout` / `dstout` | 源外 / 目标外 |
| `srcatop` / `dstatop` | 源上 / 目标上 |
| `xor_` | 异或 |
| `modulate` / `multiply` / `screen` / `plus_` | 调制 / 乘法 / 屏幕 / 加法 |
| `darken` / `lighten` | 变暗 / 变亮 |
| `difference` / `exclusion` | 差值 / 排除 |
| `colorburn` / `colordodge` | 颜色加深 / 颜色减淡 |
| `hardlight` / `softlight` / `overlay` | 强光 / 柔光 / 叠加 |
| `hue` / `saturation` / `color` / `luminosity` | HSL 相关混合模式 |

**优化的复合阶段：**
| 阶段 | 说明 |
|------|------|
| `srcover_rgba_8888` | 融合了 load+srcover+store 的 RGBA8888 快速路径 |
| `bilerp_clamp_8888` | 融合了双线性采样+clamp 的 8888 快速路径 |
| `bicubic_clamp_8888` | 融合了双三次采样+clamp 的 8888 快速路径 |

**颜色空间转换阶段：**
| 阶段 | 说明 |
|------|------|
| `rgb_to_hsl` / `hsl_to_rgb` | RGB 与 HSL 互转 |
| `css_lab_to_xyz` / `css_oklab_to_linear_srgb` | CSS 颜色空间转换 |

**抖动阶段：**
| 阶段 | 说明 |
|------|------|
| `dither` | 8x8 有序抖动 |

**数学运算阶段（SkSL 运行时支持）：**
使用宏批量定义一元、二元、三元浮点和整数运算，支持 1-4 通道和 N 通道变体：
- 一元：`acos`, `asin`, `atan`, `cos`, `sin`, `tan`, `exp`, `log`, `sqrt`, `abs`, `ceil`, `floor`, `round` 等
- 二元：`add`, `sub`, `mul`, `div`, `min`, `max`, `pow`, `atan2`, `mod` 等
- 三元：`mix`（线性插值），`smoothstep`

## 内部实现细节

### 管线执行模型
管线使用"函数指针链"模式执行。每个阶段是一个函数，接收固定的参数集（寄存器中的像素数据），处理后调用下一个阶段的函数指针：

```cpp
// Highp 阶段原型（简化）
void stage_fn(SkRasterPipelineStage* program,
              size_t dx, size_t dy,
              F r, F g, F b, F a,
              F dr, F dg, F db, F da);
```

关键设计：参数通过 CPU 寄存器传递，避免内存往返。在 ARM 上，NEON 有 32 个浮点寄存器，恰好可以容纳 8 个 4-wide 向量。在 x86 AVX 上，有 16 个 YMM 寄存器可用。

### Highp vs Lowp 双精度路径
- **Highp**：使用浮点数处理，精度高，支持所有阶段。宽度随平台变化（1/4/8/16 通道）。
- **Lowp**：使用 `uint16_t` 表示 [0, 255] 的颜色值，精度有限但吞吐量更高。仅支持部分阶段，不支持的阶段函数指针为 nullptr，运行时自动回退到 Highp。

Lowp 阶段进一步分为三类：
- **GG（Geometry→Geometry）**：如矩阵变换，操作浮点坐标
- **GP（Geometry→Pixels）**：如纹理采样，从坐标产生像素
- **PP（Pixels→Pixels）**：如混合模式，操作整数像素

### 尾部处理（Tail Handling）
当处理的像素行不是 N 的整数倍时，剩余像素通过"尾部"机制处理。`start_pipeline` 函数先以 N 步长处理完整批次，然后通过 `tailPointer` 标记剩余宽度，修补内存上下文后处理最后一批。

### 融合阶段优化
`srcover_rgba_8888` 是最重要的融合阶段之一，将加载目标像素、执行 SrcOver 混合和存储结果合并为单个函数，避免了多阶段之间的寄存器保存/恢复开销。类似地，`bilerp_clamp_8888` 和 `bicubic_clamp_8888` 将图像采样与像素格式转换融合。

### Newton-Raphson 精炼
ARM NEON 的 `rcp_approx` 和 `rsqrt_approx` 仅提供约 8 位精度，需要通过 Newton-Raphson 迭代步骤提高精度：
```cpp
// 倒数精炼（ARM）
SI F rcp_precise(F v) {
    auto e = rcp_approx(v);
    return vrecpsq_f32(v, e) * e;  // 一次 NR 步骤
}
```

### 有序抖动
`dither` 阶段实现 8x8 Bayer 矩阵有序抖动。通过位操作从 (x, y) 坐标直接计算抖动矩阵值，避免查表：
```cpp
// 从 X=abc, Y=def 构造 6-bit 索引 fcebda
U32 M = (Y & 1) << 5 | (X & 1) << 4
      | (Y & 2) << 2 | (X & 2) << 1
      | (Y & 4) >> 1 | (X & 4) >> 2;
```

## 依赖关系

- `SkRasterPipeline.h` — 管线构建和阶段定义
- `SkRasterPipelineContextUtils.h` — 上下文数据打包/解包工具
- `modules/skcms/skcms.h` — 颜色管理系统
- `src/base/SkUtils.h` — 未对齐的内存加载/存储
- `src/sksl/tracing/SkSLTraceHook.h` — SkSL 调试跟踪支持
- 平台 SIMD 头文件：`arm_neon.h`、`immintrin.h`、`lsxintrin.h` 等

## 设计模式与设计决策

### 编译时多态（而非运行时多态）
文件通过预处理器宏（`SKRP_CPU_NEON`、`SKRP_CPU_HSW` 等）在编译时选择平台实现，而非使用虚函数或函数指针分发。这保证了每个目标平台的代码完全内联，编译器可以进行最大程度的优化。

### 寄存器传递优先
选择编译器向量扩展而非 `skvx::Vec` 的核心原因是寄存器传递。管线的 8 个颜色参数（r/g/b/a 和 dr/dg/db/da）必须通过硬件寄存器传递以获得最优性能。`skvx::Vec` 的结构体布局会导致参数通过栈传递。

### 宏驱动的阶段定义
使用 `BLEND_MODE`、`DECLARE_UNARY_FLOAT` 等宏批量生成重复的阶段定义，减少代码冗余并确保所有同类阶段的一致性。

### 窄阶段 vs 宽阶段
在寄存器受限的平台（如 ARM32 或 Windows x64），使用"窄阶段"（`SKRP_NARROW_STAGES`）模式，将部分参数放入栈上的 `Params` 结构体中，仅将最常用的 r/g/b/a 通过寄存器传递。

## 性能考量

1. **SIMD 宽度最大化**：SKX 使用 512-bit AVX-512（16 通道），HSW 使用 256-bit AVX2（8 通道），NEON 使用 128-bit（4 通道），每个时钟周期处理更多像素
2. **融合阶段**：`srcover_rgba_8888` 等融合阶段将多步操作合并，减少函数调用和寄存器溢出
3. **Lowp 路径**：对于 8-bit 颜色操作，使用 16-bit 整数运算代替浮点运算，吞吐量翻倍
4. **FMA 指令**：在支持的平台上使用融合乘加（`_mm256_fmadd_ps`、`vfmaq_f32`），减少舍入误差并提高吞吐量
5. **聚集加载**：在 AVX2/AVX-512 上使用 `_mm256_i32gather` / `_mm512_i32gather` 硬件聚集指令
6. **`__attribute__((always_inline))`**：所有函数强制内联，消除函数调用开销
7. **循环展开**：`SK_UNROLL` 宏提示编译器展开关键循环
8. **div255 优化**：NEON 上使用 `vrshrq_n_u16(vrsraq_n_u16(v, v, 8), 8)` 实现精确的除以 255，其他平台使用近似的 `(v+255)/256`
9. **避免分支**：大量使用 `if_then_else` 进行无分支选择，保持 SIMD 通道的并行执行

## 相关文件

- `/Users/yuanlin/workspace/skia/src/opts/SkRasterPipeline_opts.h` — 本文件
- `/Users/yuanlin/workspace/skia/src/core/SkRasterPipeline.h` — 管线构建器定义
- `/Users/yuanlin/workspace/skia/src/core/SkRasterPipeline.cpp` — 管线构建逻辑
- `/Users/yuanlin/workspace/skia/src/core/SkRasterPipelineContextUtils.h` — 上下文工具
- `/Users/yuanlin/workspace/skia/src/core/SkOpts.cpp` — 运行时 CPU 检测和函数指针设置
- `/Users/yuanlin/workspace/skia/src/base/SkVx.h` — 通用 SIMD 向量抽象（与本文件的 Vec 不同）
