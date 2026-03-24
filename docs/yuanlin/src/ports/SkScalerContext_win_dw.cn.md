# SkScalerContext_DW - Windows DirectWrite 字形缩放上下文

> 源文件:
> - `src/ports/SkScalerContext_win_dw.h`
> - `src/ports/SkScalerContext_win_dw.cpp`

## 概述

`SkScalerContext_DW` 是 Skia 在 Windows 平台上通过 DirectWrite API 实现的字形缩放上下文。它负责字形度量计算、字形图像光栅化、路径生成和字体度量提取。该类支持多种渲染模式（别名、GDI 经典、自然对称等），并能处理彩色字体（COLR、COLRv1、SVG、PNG 等格式）。

该实现是 Skia 在 Windows 上最核心的文本渲染后端之一，处理了 DirectWrite 各版本间的兼容性问题以及与 GDI 传统行为的协调。

## 架构位置

```
SkScalerContext (基类, src/core/)
  |
  v
SkScalerContext_DW (本类, src/ports/)
  |
  v
DWriteFontTypeface (字体类型, src/ports/)
  |
  v
IDWriteFontFace / IDWriteFactory (DirectWrite COM 接口)
```

## 主要类与结构体

### `SkScalerContext_DW`

继承自 `SkScalerContext`，为 Windows DirectWrite 的字形缩放实现。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fBits` | `SkTDArray<uint8_t>` | 字形位图缓冲区 |
| `fSkXform` | `SkMatrix` | 不含文本大小的完整矩阵 |
| `fXform` | `DWRITE_MATRIX` | DirectWrite 格式的变换矩阵 |
| `fTextSizeRender` | `SkScalar` | 渲染用文本大小 |
| `fTextSizeMeasure` | `SkScalar` | 测量用文本大小 |
| `fGlyphCount` | `int` | 字形数量 |
| `fRenderingMode` | `DWRITE_RENDERING_MODE` | 渲染模式 |
| `fTextureType` | `DWRITE_TEXTURE_TYPE` | 纹理类型 |
| `fMeasuringMode` | `DWRITE_MEASURING_MODE` | 测量模式 |
| `fAntiAliasMode` | `DWRITE_TEXT_ANTIALIAS_MODE` | 抗锯齿模式 |
| `fGridFitMode` | `DWRITE_GRID_FIT_MODE` | 网格适配模式 |

### `ScalerContextBits`

用于标识字形数据格式的位标志：

| 常量 | 值 | 说明 |
|------|-----|------|
| `NONE` | 0 | 无数据 |
| `DW` | 1 | DirectWrite 标准光栅 |
| `DW_1` | 2 | DirectWrite 1.0 光栅 |
| `PNG` | 3 | PNG 嵌入位图 |
| `SVG` | 4 | SVG 字形 |
| `COLR` | 5 | COLR 彩色字形 |
| `COLRv1` | 6 | COLRv1 彩色字形 |
| `PATH` | 7 | 路径字形 |

## 公共 API 函数

### 构造函数

```cpp
SkScalerContext_DW(DWriteFontTypeface&,
                   const SkScalerContextEffects&,
                   const SkDescriptor*);
```

复杂的初始化逻辑，决定渲染模式：

1. 计算实际设备大小和 GDI 兼容大小
2. 检查是否请求嵌入位图，以及是否存在位图点阵
3. 根据条件选择渲染模式（按优先级）：
   - BW 格式 -> `ALIASED` + GDI 经典测量
   - 有位图且轴对齐 -> `GDI_CLASSIC`
   - 有位图但有旋转 -> `NATURAL_SYMMETRIC` + GDI 经典测量
   - gasp 表版本 >= 1 -> 根据 SymmetricSmoothing 标志选择
   - 大文本(>20px)或无 hint -> `NATURAL_SYMMETRIC`
   - 有 hint 的小文本 -> `NATURAL`（兼容 GDI ClearType 经典行为）

### 受保护的虚函数

```cpp
GlyphMetrics generateMetrics(const SkGlyph&, SkArenaAlloc*) override;
void generateImage(const SkGlyph&, void* imageBuffer) override;
std::optional<GeneratedPath> generatePath(const SkGlyph&) override;
sk_sp<SkDrawable> generateDrawable(const SkGlyph&) override;
void generateFontMetrics(SkFontMetrics*) override;
```

## 内部实现细节

### 线程安全

Windows 8/8.1 中 DirectWrite 的某些调用不是线程安全的。使用 `maybe_dw_mutex()` 返回互斥锁（如果 `fDWriteFontFace4` 不可用则需要锁）。提供 `Exclusive` 和 `Shared` RAII 锁封装。

### 位图点阵检测

`has_bitmap_strike()` 检查 EBLC（嵌入位图位置表）和 EBSC（嵌入位图缩放表）以确定给定大小是否有可用的位图点阵。

### gasp 表解析

`get_gasp_range()` 解析 gasp（网格适配和扫描过程）表，确定给定像素大小的渲染行为标志（对称平滑、网格适配等）。

### 彩色字形支持

支持多种彩色字形格式：
- **COLRv1**：通过 `IDWritePaintReader` 读取绘制树，支持渐变、混合等
- **COLR**：通过 `IDWriteColorGlyphRunEnumerator` 枚举彩色字形运行
- **SVG**：使用 `SkOpenTypeSVGDecoder` 解码
- **PNG**：解码嵌入的 PNG 位图

### 像素格式转换

提供模板化的像素格式转换函数：
- `BilevelToBW` - 二值转 BW
- `GrayscaleToA8` - 灰度转 A8
- `RGBToA8` - RGB 转 A8
- `RGBToLcd16` - RGB 转 LCD16（支持 BGR/RGB 两种子像素顺序）

### CBDT 字体特殊处理

对于 CBDT（颜色位图数据表）字体，GDI 测量模式工作不正常，强制使用 `NATURAL` 测量模式。

## 依赖关系

### DirectWrite 接口

- `IDWriteFontFace`/1/2/3/4/5/7 - 字体面接口的各版本
- `IDWriteFactory`/2 - 工厂接口
- `IDWritePaintReader` - COLRv1 绘制读取器
- `IDWriteColorGlyphRunEnumerator` - COLR 枚举器

### Skia 内部

- `SkScalerContext` - 基类
- `DWriteFontTypeface` - 关联的字体类型
- `SkDWriteGeometrySink` - 路径转换
- `SkMatrix22` - 2x2 矩阵工具
- sfnt 表解析: `SkOTTable_EBLC`, `SkOTTable_EBSC`, `SkOTTable_gasp`, `SkOTTable_maxp`

## 设计模式与设计决策

1. **渲染模式自适应**：构造函数根据字体特性、大小和请求自动选择最佳渲染模式
2. **分离渲染和测量大小**：`fTextSizeRender` 和 `fTextSizeMeasure` 分离，允许用位图测量但以高质量渲染
3. **渐进式接口查询**：通过 QueryInterface 按需获取 DirectWrite 的新版接口
4. **COLRv1 绘制树遍历**：使用递归方式遍历绘制元素树以渲染复杂彩色字形
5. **RAII 线程安全**：使用 `Exclusive`/`Shared` RAII 封装处理条件性互斥锁

## 性能考量

1. **互斥锁按需使用**：仅在旧版 Windows（无 IDWriteFontFace4）上使用互斥锁
2. **共享锁优化**：在可能的地方使用 `Shared`（读锁）而非 `Exclusive`（写锁）
3. **gasp 表缓存**：gasp 表解析结果影响渲染模式选择，只在构造时读取一次
4. **位图点阵优先**：当检测到合适的位图点阵时优先使用，避免不必要的矢量渲染
5. **GDI 文本大小量化**：GDI 兼容大小量化到 1/64 像素精度以避免浮点误差

### 渲染模式决策树详细说明

构造函数中的渲染模式决策是该类最复杂的部分。以下是完整的决策逻辑：

```
输入请求格式
  |
  +-- BW (kBW_Format)
  |     -> ALIASED + GDI_CLASSIC 测量 + gdiTextSize
  |
  +-- 非 BW
        |
        +-- 有位图 + 轴对齐
        |     -> GDI_CLASSIC + GDI_CLASSIC 测量 + gdiTextSize
        |
        +-- 有位图 + 有旋转
        |     -> NATURAL_SYMMETRIC + GDI_CLASSIC 测量 + gdiTextSize
        |
        +-- gasp v1+ 且有 SymmetricSmoothing
        |     -> NATURAL_SYMMETRIC + NATURAL 测量 + realTextSize
        |
        +-- gasp v1+ 且无 SymmetricSmoothing
        |     -> NATURAL + NATURAL 测量 + realTextSize
        |
        +-- 大文本(>20px) 或无 hint
        |     -> NATURAL_SYMMETRIC + NATURAL 测量 + realTextSize
        |
        +-- 有 hint 的小文本
              -> NATURAL + NATURAL 测量 + realTextSize (渲染用 gdiTextSize)
```

之后还有额外修正：
- A8 格式 + Factory2 可用 -> 灰度抗锯齿模式
- hinting 禁用 -> 禁用网格适配
- 线性度量 -> 强制 NATURAL 测量
- CBDT 字体 -> 强制 NATURAL 测量

### COLRv1 绘制树结构

COLRv1 是 OpenType 1.9 引入的高级彩色字形格式。`drawColorV1Paint()` 递归遍历绘制元素树：

- **Layers**：多层叠加绘制
- **Solid**：纯色填充（可引用调色板）
- **LinearGradient** / **RadialGradient** / **SweepGradient**：渐变填充
- **Glyph**：嵌套字形引用
- **Transform**：仿射变换
- **Composite**：混合模式合成

### 类型转换辅助函数

文件中定义了多个 DirectWrite/Direct2D 类型到 Skia 类型的转换函数：

| 函数 | 转换方向 |
|------|---------|
| `sk_color_from()` | DWRITE_COLOR_F -> SkColor4f |
| `dw_color_from()` | SkColor4f -> DWRITE_COLOR_F |
| `sk_rect_from()` | D2D_RECT_F -> SkRect |
| `sk_matrix_from()` | DWRITE_MATRIX -> SkMatrix |
| `sk_tile_mode_from()` | D2D1_EXTEND_MODE -> SkTileMode |
| `sk_blend_mode_from()` | DWRITE_COLOR_COMPOSITE_MODE -> SkBlendMode |

### 字形度量生成策略

`generateMetrics()` 根据 `ScalerContextBits` 选择不同的度量生成路径：

1. 首先尝试 COLRv1 (`generateColorV1Metrics`)
2. 然后尝试 SVG (`generateSVGMetrics`)
3. 然后尝试 PNG (`generatePngMetrics`)
4. 然后尝试 COLR (`generateColorMetrics`)
5. 最后使用 DirectWrite 标准路径 (`generateDWMetrics`)

每种格式都会设置对应的 `ScalerContextBits` 标志，以便 `generateImage()` 使用相同的路径。

## 相关文件

- `src/ports/SkTypeface_win_dw.h` - DirectWrite 字体类型
- `src/core/SkScalerContext.h` - 缩放上下文基类
- `src/utils/win/SkDWrite.h` - DirectWrite 工具函数
- `src/utils/win/SkDWriteGeometrySink.h` - 路径转换接收器
- `src/sfnt/SkOTTable_gasp.h` - gasp 表定义
- `src/sfnt/SkOTTable_EBLC.h` - 嵌入位图位置表
- `src/sfnt/SkOTTable_EBSC.h` - 嵌入位图缩放表
- `src/sfnt/SkOTTable_maxp.h` - 最大配置表
