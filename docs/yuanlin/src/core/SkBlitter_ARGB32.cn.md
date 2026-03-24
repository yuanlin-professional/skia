# SkBlitter_ARGB32

> 源文件: src/core/SkBlitter_ARGB32.cpp

## 概述

`SkBlitter_ARGB32.cpp` 实现了针对 32 位 ARGB 颜色格式（`kN32_SkColorType`）的像素绘制优化。该文件包含多个 blitter 类的实现，每个类针对特定场景进行了优化：纯色绘制、不透明绘制、纯黑色绘制、以及带 shader 的绘制。此外，还包含了 LCD 子像素渲染的专门实现，并使用 SSE2 和 NEON 等 SIMD 指令集进行向量化优化。该模块是 Skia legacy blitter 系统中最常用和性能最关键的部分。

## 架构位置

该模块位于 Skia 核心光栅化层（`src/core`），是 `SkBlitter` 系统针对 32 位颜色格式的具体实现：

```
SkBlitter (抽象基类)
    ↓
SkRasterBlitter (光栅设备基类)
    ↓
SkARGB32_Blitter (32 位 ARGB 通用实现) ← 本模块
    ├── SkARGB32_Opaque_Blitter (不透明优化)
    │   └── SkARGB32_Black_Blitter (纯黑优化)
    └── SkARGB32_Shader_Blitter (shader 绘制)
```

该模块与以下组件协同工作：

- **SkBlitRow**: 提供行级别的像素混合优化函数
- **SkBlitMask**: 提供遮罩混合的专门实现
- **SkShaderBase**: 为 shader blitter 提供颜色生成
- **SkOpts**: 提供 CPU 特定的 SIMD 优化

## 主要类与结构体

### SkARGB32_Blitter

32 位 ARGB 格式的通用 blitter，处理带有 alpha 的纯色绘制。

**继承关系:**
```
SkBlitter
  └── SkRasterBlitter
      └── SkARGB32_Blitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fDevice` | `const SkPixmap` | 目标设备像素映射（继承自 SkRasterBlitter） |
| `fColor` | `SkColor` | 未预乘的源颜色 |
| `fPMColor` | `SkPMColor` | 预乘后的源颜色 |
| `fSrcA` | `SkAlpha` | 源 alpha 值 |

### SkARGB32_Opaque_Blitter

不透明（alpha = 255）颜色绘制的优化版本。

**继承关系:**
```
SkBlitter
  └── SkRasterBlitter
      └── SkARGB32_Blitter
          └── SkARGB32_Opaque_Blitter
```

**优化特性:**
- 跳过 alpha 混合计算
- 支持直接像素写入（`canDirectBlit`）
- 针对 LCD 遮罩的专门优化路径

### SkARGB32_Black_Blitter

纯黑色（color = 0xFF000000）绘制的特殊优化。

**继承关系:**
```
SkBlitter
  └── SkRasterBlitter
      └── SkARGB32_Blitter
          └── SkARGB32_Opaque_Blitter
              └── SkARGB32_Black_Blitter
```

**优化特性:**
- 使用更简单的混合公式（只需混合 alpha）
- 针对抗锯齿文本渲染高度优化

### SkARGB32_Shader_Blitter

使用 shader 生成颜色的 blitter，支持渐变、位图等复杂填充模式。

**继承关系:**
```
SkBlitter
  └── SkRasterBlitter
      └── SkShaderBlitter
          └── SkARGB32_Shader_Blitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fShader` | `sk_sp<SkShader>` | Shader 对象引用（继承） |
| `fShaderContext` | `SkShaderBase::Context*` | Shader 上下文，用于生成颜色（继承） |
| `fBuffer` | `SkPMColor*` | 临时颜色缓冲区，存储 shader 生成的颜色 |
| `fProc32` | `SkBlitRow::Proc32` | 不透明像素行混合函数指针 |
| `fProc32Blend` | `SkBlitRow::Proc32` | 带 alpha 混合的行混合函数指针 |
| `fShadeDirectlyIntoDevice` | `bool` | 是否可以直接将 shader 输出写入设备（不需要混合） |

## 公共 API 函数

### SkARGB32_Blitter 虚函数实现

#### blitH
```cpp
void blitH(int x, int y, int width) override;
```
绘制水平不透明像素行。使用 `SkOpts::memset32` 快速填充颜色。

#### blitAntiH
```cpp
void blitAntiH(int x, int y, const SkAlpha antialias[],
               const int16_t runs[]) override;
```
绘制抗锯齿水平像素行。根据 alpha 值选择不同的混合路径：
- alpha = 255: 直接写入颜色
- alpha = 0: 跳过
- 其他: 调用混合函数

#### blitV
```cpp
void blitV(int x, int y, int height, SkAlpha alpha) override;
```
绘制垂直像素列。针对不同 alpha 值优化。

#### blitRect
```cpp
void blitRect(int x, int y, int width, int height) override;
```
绘制矩形区域。使用行优化函数 `SkOpts::memset32` 逐行填充。

#### blitMask
```cpp
void blitMask(const SkMask& mask, const SkIRect& clip) override;
```
根据遮罩绘制像素。支持 BW、A8、LCD16 和 ARGB32 遮罩格式。

#### blitAntiH2 / blitAntiV2
```cpp
void blitAntiH2(int x, int y, U8CPU a0, U8CPU a1) override;
void blitAntiV2(int x, int y, U8CPU a0, U8CPU a1) override;
```
优化的 2 像素抗锯齿绘制，避免构造 runs 数组。

### SkARGB32_Opaque_Blitter 专门优化

#### canDirectBlit
```cpp
std::optional<DirectBlit> canDirectBlit() override;
```
返回直接写入优化信息，允许调用者直接填充像素值而不调用 blit 方法。

#### blitMask
针对不透明颜色的遮罩绘制优化，特别是 LCD16 格式使用专门的 `blend_lcd16_opaque` 路径。

### SkARGB32_Black_Blitter 黑色优化

所有抗锯齿方法使用简化的黑色混合算法：
```cpp
dst = (dst * (255 - alpha)) >> 8
```
这比通用的颜色混合快得多。

### SkARGB32_Shader_Blitter 虚函数实现

#### blitH
```cpp
void blitH(int x, int y, int width) override;
```
从 shader 生成颜色行，然后使用 `fProc32` 或 `fProc32Blend` 混合到目标设备。

#### blitRect
```cpp
void blitRect(int x, int y, int width, int height) override;
```
针对矩形优化的 shader 绘制，逐行生成和混合颜色。

#### blitAntiH
```cpp
void blitAntiH(int x, int y, const SkAlpha aa[],
               const int16_t runs[]) override;
```
生成 shader 颜色并应用抗锯齿 alpha 值。

#### blitMask
```cpp
void blitMask(const SkMask& mask, const SkIRect& clip) override;
```
结合 shader 颜色和遮罩 alpha 值进行绘制。

## 内部实现细节

### 像素混合算法

#### 基础混合公式（blend_32）
```cpp
static inline int blend_32(int src, int dst, int scale) {
    return dst + ((src - dst) * scale >> 5);
}
```
使用 5 位缩放因子（0-32）进行线性插值。右移 5 位等价于除以 32。

#### LCD 子像素混合（blend_lcd16）
```cpp
static inline SkPMColor blend_lcd16(int srcA, int srcR, int srcG, int srcB,
                                     SkPMColor dst, uint16_t mask);
```

LCD 渲染为 R、G、B 通道使用不同的覆盖率值：

1. 从 16 位遮罩提取 RGB 通道（通常为 565 格式）
2. 将每个通道从 5 位扩展到 5 位（0-31 范围）
3. 使用 `upscale_31_to_32` 扩展到 0-32 范围
4. 与源 alpha 相乘
5. 对每个通道独立应用 `blend_32`
6. **Alpha 通道处理**: 根据 `srcA < dstA` 条件，使用 RGB 覆盖率的最小值或最大值

#### LCD 不透明混合优化（blend_lcd16_opaque）
```cpp
static inline SkPMColor blend_lcd16_opaque(int srcR, int srcG, int srcB,
                                           SkPMColor dst, uint16_t mask,
                                           SkPMColor opaqueDst);
```

不透明源的优化版本：
- 检测完全不透明遮罩（0xFFFF）时直接返回 `opaqueDst`
- Alpha 通道始终使用 RGB 覆盖率的最大值
- 跳过源 alpha 的乘法操作

### SIMD 优化

#### SSE2 实现（blend_lcd16_sse2）

一次处理 4 个像素的向量化 LCD 混合：

1. **解包**: 将 16 位遮罩解包为 32 位，将 8 位源/目标解包为 16 位
2. **通道分离**: 使用位掩码提取 R、G、B 通道
3. **Alpha 计算**: 使用 `_mm_min_epu8` 和 `_mm_max_epu8` 计算条件 alpha
4. **扩展**: 使用 `(x + (x >> 4))` 将 31 扩展到 32
5. **混合**: 向量化乘法和移位操作
6. **打包**: 使用 `_mm_packus_epi16` 将结果打包回 8 位

**关键优化**:
- 16 字节对齐检测，确保 SSE load/store 操作高效
- 使用 `_mm_movemask_epi8` 和 `_mm_cmpeq_epi16` 快速检测全零遮罩，跳过不必要的混合
- 一次处理 4 个像素，减少循环开销

#### NEON 实现

ARM 平台的对应优化，使用 NEON 指令集实现类似的向量化混合。

### Shader Blitter 缓冲策略

`SkARGB32_Shader_Blitter` 使用临时缓冲区存储 shader 生成的颜色：

1. **缓冲区分配**: 在 `allocBlitMemory` 中分配 `fBuffer`
2. **Shader 调用**: `shadeSpan(x, y, fBuffer, width)` 生成颜色
3. **混合应用**: 使用 `fProc32` 或 `fProc32Blend` 将缓冲区颜色混合到设备

**直接写入优化**: 如果 paint alpha 为 255 且混合模式为 SrcOver，且 shader 输出不透明，设置 `fShadeDirectlyIntoDevice = true`，跳过混合直接写入设备。

### 遮罩格式处理

#### BW 遮罩（1 位）
委托给基类 `SkBlitter::blitMask` 的默认实现。

#### A8 遮罩（8 位 alpha）
使用 `SkBlitMask::BlitColor` 进行优化的颜色和遮罩混合。

#### LCD16 遮罩（RGB 子像素）
使用专门的 `blit_row_lcd16` 或 `blit_row_lcd16_opaque` 函数：
- 对齐到 16 字节边界
- 使用 SSE2/NEON 向量化处理
- 处理边缘像素的标量代码

#### ARGB32 遮罩（32 位颜色）
少见的格式，使用完整的颜色混合。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 基类定义 |
| `SkRasterBlitter` | 光栅设备基类 |
| `SkShaderBlitter` | Shader blitter 基类 |
| `SkPixmap` | 设备像素访问 |
| `SkPaint` | 绘制参数 |
| `SkMask` | 遮罩数据结构 |
| `SkBlitRow` | 行级别混合函数 |
| `SkBlitMask` | 遮罩混合函数 |
| `SkShaderBase` | Shader 内部接口 |
| `SkColorData` / `SkColorPriv` | 颜色格式转换工具 |
| `SkOpts` | CPU 优化函数（memset32 等） |
| `SkVx` | 向量化辅助工具 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkBlitter::Choose` | 根据条件选择和创建 ARGB32 blitter |
| `SkDraw` | 使用 blitter 执行绘制 |
| `SkScan` | 扫描转换后调用 blitter |

## 设计模式与设计决策

### 继承层次优化

三层继承结构逐步特化，每层添加约束以启用更多优化：
- `SkARGB32_Blitter`: 通用带 alpha 纯色
- `SkARGB32_Opaque_Blitter`: 不透明纯色
- `SkARGB32_Black_Blitter`: 纯黑色

这种设计避免了运行时分支判断，通过虚函数多态实现编译时特化。

### 模板方法模式

基类提供通用实现，子类覆盖特定方法以优化。例如 `blitAntiH` 在三个类中都有不同的实现。

### 策略模式

`SkARGB32_Shader_Blitter` 使用函数指针（`fProc32`、`fProc32Blend`）选择混合策略，由 `SkBlitRow` 模块根据 CPU 特性提供优化实现。

### 设计决策

1. **SIMD 优化集成**: 将 SSE2 和 NEON 代码直接嵌入 cpp 文件，而非独立的 opts 文件，因为这些是热路径中的关键函数

2. **LCD 渲染的复杂性**: LCD 子像素渲染需要为 RGB 通道独立混合，且 alpha 通道的处理依赖于源和目标 alpha 的关系，这导致了复杂的实现

3. **缓冲区策略**: Shader blitter 使用临时缓冲区而非直接写入设备，因为 shader 需要连续的输出空间，且可能需要后续混合

4. **对齐处理**: SSE2/NEON 代码明确处理未对齐的像素，先用标量代码对齐到 16 字节边界，然后使用向量化代码，最后处理尾部

5. **全零遮罩检测**: LCD 混合前检测全零遮罩，避免不必要的混合计算，这在文本渲染中很常见（字符间的空白）

## 性能考量

### 内存访问模式

- **行优先处理**: 所有 blit 操作按行处理，利用缓存行的空间局部性
- **对齐优化**: SSE2 代码要求 16 字节对齐以使用 `_mm_load_si128` 和 `_mm_store_si128`，避免未对齐访问的性能损失
- **预乘颜色**: 使用预乘 alpha（`fPMColor`），避免在每个像素处理时重复计算

### SIMD 向量化

- **批处理**: LCD 混合一次处理 4 个像素（SSE2）或 8 个像素（NEON），显著减少循环开销
- **减少分支**: 使用 SSE2 比较指令（`_mm_cmplt_epi32`）和位操作（`_mm_andnot_si128`）实现无分支的条件选择
- **寄存器利用**: 最大化 SSE/NEON 寄存器使用，减少内存读写

### 快速路径优化

- **不透明快速路径**: `SkARGB32_Opaque_Blitter` 跳过 alpha 混合，直接写入或使用简化混合
- **黑色快速路径**: `SkARGB32_Black_Blitter` 使用简化公式，仅混合 alpha 通道
- **直接 blit**: `canDirectBlit` 允许调用者直接 memset 像素值，完全跳过 blitter 调用
- **全覆盖检测**: `blitAntiH` 中检测 alpha = 255，使用不透明路径

### 循环展开和内联

- 辅助函数（`blend_32`、`upscale_31_to_32`）声明为 `static inline`，编译器可内联
- SSE2 循环手动展开，一次处理 4 个像素
- 使用宏（`WRAP`、`DEFINE_BLIT_MASK`）减少代码重复，便于编译器优化

### 遮罩处理优化

- **格式特化**: 为不同遮罩格式提供专门函数，避免运行时格式检查
- **LCD16 全覆盖检测**: 检测 `mask == 0xFFFF`，直接返回预计算的不透明结果
- **全零跳过**: LCD 混合前检测全零遮罩，跳过混合操作

### 分支预测友好

- 常见情况（不透明、全覆盖）放在 if 分支的前面
- 使用 `SkASSERT` 提供编译器优化提示
- 避免在内层循环中使用复杂条件判断

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitter.h` | 基类定义 |
| `src/core/SkBlitter.cpp` | Blitter 选择逻辑 |
| `src/core/SkCoreBlitters.h` | ARGB32 blitter 类声明 |
| `src/core/SkBlitRow.h` | 行混合函数接口 |
| `src/core/SkBlitRow.cpp` | 行混合函数实现 |
| `src/core/SkBlitMask.h` | 遮罩混合函数接口 |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `src/core/SkColorData.h` | 颜色打包/解包宏 |
| `src/core/SkColorPriv.h` | 颜色格式转换 |
| `src/shaders/SkShaderBase.h` | Shader 内部接口 |
| `include/core/SkPixmap.h` | 像素映射接口 |
| `include/core/SkPaint.h` | 绘制参数 |
| `src/base/SkVx.h` | 向量化辅助工具 |
| `src/opts/SkOpts.h` | CPU 优化函数 |
