# SkBlitter_A8

> 源文件: src/core/SkBlitter_A8.h, src/core/SkBlitter_A8.cpp

## 概述

`SkBlitter_A8` 模块为 Alpha 8 位颜色类型（`kAlpha_8_SkColorType`）提供专门的像素绘制实现。该模块包含两个主要的 blitter 类：`SkA8_Coverage_Blitter` 用于覆盖率绘制，`SkA8_Blitter` 用于带有混合模式的 Alpha 通道绘制。这些 blitter 针对仅包含 Alpha 通道的位图进行了优化，通常用于文本渲染、遮罩和阴影等场景。

## 架构位置

该模块位于 Skia 的核心光栅化层（`src/core`），是 `SkBlitter` 系统的一个专门化实现。在 Skia 的绘制流水线中，`SkBlitter_A8` 负责将渲染结果写入到仅包含 Alpha 通道的目标设备中。它与以下组件交互：

- **上游**: 由 `SkDraw` 和 `SkScan` 调用以执行实际的像素写入操作
- **下游**: 直接操作 `SkPixmap` 中的 Alpha 8 格式像素数据
- **平行**: 与 `SkBlitter_ARGB32`、`SkRasterPipelineBlitter` 等其他颜色类型的 blitter 并行存在

## 主要类与结构体

### SkA8_Coverage_Blitter

专用于覆盖率绘制的 blitter，不执行混合操作，直接将覆盖率值写入 Alpha 通道。

**继承关系:**
```
SkBlitter (基类)
  └── SkA8_Coverage_Blitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fDevice` | `const SkPixmap` | 目标设备的像素映射，包含 Alpha 8 格式的图像数据 |

### SkA8_Blitter

支持混合模式的 Alpha 通道 blitter，可以执行 SrcOver 和 Src 等混合操作。

**继承关系:**
```
SkBlitter (基类)
  └── SkA8_Blitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fDevice` | `const SkPixmap` | 目标设备的像素映射 |
| `fOneProc` | `AlphaProc` | 单像素 Alpha 处理函数指针 |
| `fBWProc` | `A8_RowBlitBW` | 不透明行绘制函数指针 |
| `fAAProc` | `A8_RowBlitAA` | 抗锯齿行绘制函数指针 |
| `fSrc` | `SkAlpha` | 源 Alpha 值（来自 paint） |

### A8_RowBlitBWPair

混合模式与处理函数的映射结构。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `mode` | `SkBlendMode` | 混合模式（SrcOver 或 Src） |
| `oneProc` | `AlphaProc` | 单像素处理函数 |
| `bwProc` | `A8_RowBlitBW` | 不透明行处理函数 |
| `aaProc` | `A8_RowBlitAA` | 抗锯齿行处理函数 |

## 公共 API 函数

### SkChooseA8Blitter

```cpp
SkBlitter* SkChooseA8Blitter(const SkPixmap& dst,
                             const SkMatrix& ctm,
                             const SkPaint& paint,
                             SkArenaAlloc* alloc,
                             SkDrawCoverage drawCoverage,
                             sk_sp<SkShader> clipShader);
```

为 Alpha 8 设备选择合适的 blitter。如果 paint 包含 shader 或 color filter，或者设备不是 Alpha 8 格式，则返回 `nullptr`。

### SkA8Blitter_Choose

```cpp
SkBlitter* SkA8Blitter_Choose(const SkPixmap& dst,
                              const SkMatrix& ctm,
                              const SkPaint& paint,
                              SkArenaAlloc* alloc,
                              SkDrawCoverage coverage,
                              sk_sp<SkShader> clipShader,
                              const SkSurfaceProps& props,
                              const SkRect& devBounds);
```

与 `SkBlitter::Choose` 签名兼容的选择函数，内部委托给 `SkChooseA8Blitter`。

### SkA8_Coverage_Blitter 虚函数

- **`blitH`**: 绘制水平不透明像素行，使用 `memset` 填充 0xFF
- **`blitAntiH`**: 绘制抗锯齿水平像素行，根据 run-length 编码填充不同的 Alpha 值
- **`blitV`**: 绘制垂直像素列，跳过 Alpha 为 0 的像素
- **`blitRect`**: 绘制矩形区域，逐行填充 0xFF
- **`blitMask`**: 从遮罩复制 Alpha 值到目标设备

### SkA8_Blitter 虚函数

与 `SkA8_Coverage_Blitter` 相同的接口，但使用混合模式函数指针处理像素。

## 内部实现细节

### Alpha 混合算法

模块实现了两种核心 Alpha 混合算法：

1. **SrcOver 模式** (`srcover_p`):
   ```cpp
   result = src + div255((255 - src) * dst)
   ```
   这是标准的 Porter-Duff SrcOver 混合。

2. **Src 模式** (`src_p`):
   ```cpp
   result = src
   ```
   直接覆盖目标像素。

### 快速除法优化

```cpp
static inline uint8_t div255(unsigned prod) {
    return (prod + 128) * 257 >> 16;
}
```

该函数使用位运算优化除以 255 的操作，避免昂贵的整数除法指令。公式 `(x + 128) * 257 >> 16` 等价于 `x / 255`，但在现代 CPU 上快得多。

### 插值函数

```cpp
static inline unsigned u8_lerp(uint8_t a, uint8_t b, uint8_t t) {
    return div255((255 - t) * a + t * b);
}
```

线性插值用于实现部分透明的抗锯齿混合。

### 模板化行处理

模块使用模板函数 `A8_row_bw` 和 `A8_row_aa` 来处理不同混合模式的行绘制，通过函数指针实现运行时多态，避免虚函数调用开销。

### 抗锯齿处理优化

对于可以折叠 Alpha 的混合模式（如 SrcOver），代码会预先计算 `src * aa`，然后应用混合函数。对于不能折叠的模式（如 Src），则使用插值在原始值和混合后值之间。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 基类，定义 blitter 接口 |
| `SkPixmap` | 提供像素数据访问 |
| `SkPaint` | 提供绘制参数（Alpha、混合模式） |
| `SkMask` | 用于遮罩绘制 |
| `SkArenaAlloc` | 用于 blitter 对象的内存分配 |
| `SkBlendMode` | 定义混合模式枚举 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkBlitter` | 作为 Alpha 8 设备的专门化实现被 blitter 选择逻辑调用 |
| `SkDraw` | 使用 blitter 执行绘制操作 |
| `SkScan` | 扫描转换后调用 blitter 填充像素 |

## 设计模式与设计决策

### 策略模式

通过函数指针（`AlphaProc`、`A8_RowBlitBW`、`A8_RowBlitAA`）实现不同混合模式的策略，避免在热路径上使用虚函数或 switch 语句。

### 工厂模式

`SkChooseA8Blitter` 和 `SkA8Blitter_Choose` 函数作为工厂方法，根据绘制参数选择合适的 blitter 实现。

### 不可变对象设计

`fDevice` 成员被声明为 `const SkPixmap`，确保设备信息在 blitter 生命周期内不可变。

### 专门化设计决策

1. **仅支持简单场景**: 不支持 shader、color filter 或 clip shader，这些情况返回 `nullptr` 由调用者选择 fallback 路径
2. **有限的混合模式支持**: 仅支持 SrcOver 和 Src 两种混合模式，其他模式需要使用 raster pipeline blitter
3. **覆盖率模式分离**: 将覆盖率绘制（`SkA8_Coverage_Blitter`）与混合模式绘制（`SkA8_Blitter`）分离，前者更简单高效

## 性能考量

### 内存访问优化

- 使用 `memset` 和 `memcpy` 进行批量像素操作，利用编译器和 CPU 的优化实现
- 逐行处理减少缓存未命中，利用空间局部性

### 分支消除

- 在 `blitAntiH` 中，仅在 `antialias[0]` 非零时执行写入操作
- 在 `blitV` 中提前返回处理 Alpha 为 0 的情况

### 函数内联

通过 `static inline` 声明辅助函数（`div255`、`u8_lerp`），编译器可以在调用点内联这些函数，减少函数调用开销。

### 专门化路径

- `blitRect` 和 `blitH` 针对不透明情况优化，直接使用 `memset` 填充 0xFF
- 覆盖率 blitter 避免混合计算，直接写入 Alpha 值

### 行处理模板化

使用模板函数和 lambda 表达式生成特定混合模式的处理代码，避免运行时类型检查和虚函数调用开销。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitter.h` | 基类定义 |
| `src/core/SkBlitter.cpp` | Blitter 选择逻辑和基类实现 |
| `src/core/SkBlitter_ARGB32.cpp` | 32 位 ARGB 格式的对应实现 |
| `src/core/SkCoreBlitters.h` | 核心 blitter 类型声明 |
| `src/core/SkDraw.h` | 高层绘制接口，调用 blitter |
| `src/core/SkScan.h` | 扫描转换，生成 blitter 输入 |
| `src/core/SkMask.h` | 遮罩数据结构定义 |
| `include/core/SkPixmap.h` | 像素映射接口 |
| `include/core/SkPaint.h` | 绘制参数定义 |
