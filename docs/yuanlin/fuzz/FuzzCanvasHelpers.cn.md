# FuzzCanvasHelpers - Canvas 模糊测试辅助工具

> 源文件:
> - `fuzz/FuzzCanvasHelpers.h`
> - `fuzz/FuzzCanvasHelpers.cpp`

## 概述

FuzzCanvasHelpers 是 Skia 模糊测试框架中最庞大的辅助模块（超过 1500 行），提供了从模糊数据中生成完整 Canvas 绘制操作序列的能力。它能够生成随机但结构有效的 SkPaint、SkShader、SkImageFilter、SkColorFilter、SkPathEffect、SkMaskFilter、SkTextBlob 等对象，并将它们组合成对 SkCanvas 的绘制调用序列。该模块是对 Canvas API 进行全面模糊测试的核心引擎。

## 架构位置

```
Skia 模糊测试基础设施
├── Fuzz (核心模糊数据读取器)
├── FuzzCommon (基础图形对象生成器)
├── FuzzCanvasHelpers (Canvas 操作生成器)  <── 本模块
│   ├── 绘制对象生成 (Paint, Shader, Filter 等)
│   ├── Canvas 操作序列生成 (63 种操作)
│   └── 辅助对象生成 (TextBlob, Image, Picture)
└── 各种具体 fuzzer
```

此模块在 FuzzCommon 之上构建，依赖其提供的路径、矩阵等基础对象生成能力，进一步组合出完整的绘制命令。

## 主要类与结构体

### `GradStorage` (内部结构体)

辅助渐变着色器创建的存储结构：
- `kMaxColors = 12`: 最大渐变色数量
- `m_colors[kMaxColors]`: `SkColor4f` 颜色数组
- `m_pos[kMaxColors]`: 位置数组
- `grad(...)`: 将 `SkColor` 转换为 `SkColor4f` 并构建 `SkGradient`

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `FuzzCanvas(Fuzz*, SkCanvas*, int depth)` | 生成对 Canvas 的随机绘制操作序列（默认深度 9）|
| `FuzzPaint(Fuzz*, SkPaint*, int depth)` | 生成随机但有效的 SkPaint 对象 |
| `MakeFuzzImageFilter(Fuzz*, int depth)` | 生成随机的图像滤镜（可递归组合）|

## 内部实现细节

### Canvas 操作生成（FuzzCanvas）

`FuzzCanvas` 生成 0~2000 次随机绘制操作（共 63 种操作码 0~62），涵盖：

**状态管理操作 (0-18)**:
- GPU 刷新 (0)、save/restore (1, 9, 10)
- saveLayer 的多种变体 (2-8)
- 变换操作：translate、scale、rotate、skew、concat、setMatrix、resetMatrix (11-18)

**裁剪操作 (19-22)**:
- clipRect、clipRRect、clipPath、clipRegion

**绘制操作 (23-62)**:
- drawPaint (23)、drawPoints (24)
- drawRect (25)、drawRegion (26)、drawOval (27)、drawRRect (29)、drawDRRect (30)
- drawArc (31)、drawPath (32)
- drawImage 系列 (33, 35, 37, 44)
- drawSimpleText (45)、drawTextBlob (51)、drawString (61)
- drawPicture (52)、drawVertices (53)
- drawColor (54, 55)、drawLine (56)、drawIRect (57)、drawCircle (58)
- drawRoundRect (60)、drawPatch (62)

### 着色器生成（make_fuzz_shader）

支持 15 种着色器类型（深度限制递归）：
- 空着色器 (0, 4)、Empty 着色器 (1)、纯色 (2)
- 图片着色器 (3)、局部矩阵包装 (5)、颜色滤镜包装 (6)
- 混合着色器 (7)、图片着色器 (8)
- 线性渐变 (10)、径向渐变 (11)、两点锥形渐变 (12)、扫描渐变 (13)
- Perlin 噪声/湍流 (14)

### 图像滤镜生成（MakeFuzzImageFilter）

支持 23 种图像滤镜（0-22），每种都可递归嵌套：
- Blur (1)、MatrixTransform (2)、Arithmetic (3)
- ColorFilter (4)、Compose (5)、DisplacementMap (6)
- DropShadow/DropShadowOnly (7)、Image (8, 9)
- 光照效果 (10, 含 6 个子类型)
- Magnifier (11)、MatrixConvolution (12)
- Merge (13, 14)、Dilate (15)、Erode (16)、Offset (17)
- Picture (18, 19)、Tile (20)、Blend (21)、Shader (22)

### 颜色滤镜生成（make_fuzz_colorfilter）

支持 9 种颜色滤镜（0-8）：Blend、Composed、Matrix、Lighting、HighContrast、Luma、Table、TableARGB

### 路径效果生成（make_fuzz_patheffect）

支持 9 种路径效果（0-8）：Sum、Compose、1DPath、Line2D、Path2D、Corner、Dash、Discrete

### 文本生成

- `make_fuzz_text`: 支持 UTF-8/UTF-16/UTF-32/GlyphID 四种编码
- `make_fuzz_textblob`: 生成含 1~8 个 run 的 TextBlob，每个 run 可以是固定位置、水平位置或完全自定义位置
- Unicode 范围覆盖 ASCII、拉丁补充和西里尔字母

### 递归深度控制

所有生成器函数都接受 `depth` 参数，每次递归调用使用 `depth - 1`，在 `depth <= 0` 时返回 `nullptr`，防止无限递归导致栈溢出。

## 依赖关系

- **模糊测试基础**: `Fuzz`、`FuzzCommon`
- **Skia 核心**: `SkCanvas`、`SkPaint`、`SkFont`、`SkBitmap`、`SkImage`
- **效果系统**: `SkImageFilters`、`SkColorFilters`、`SkPathEffect`（及各子类）、`SkMaskFilter`、`SkGradient`、`SkPerlinNoiseShader`
- **文本**: `SkTextBlob`、`SkTypeface`、`SkFontMgr`
- **文档**: `SkPDFDocument`、`SkSVGCanvas`
- **GPU（条件依赖）**: `GrDirectContext`（SK_GANESH）、`GrGLGpu`（SK_GL）
- **调试工具**: `DebugCanvas`、`UrlDataManager`、`SkJSONWriter`

## 设计模式与设计决策

- **组合器模式**: 各种对象生成器可自由组合，通过递归深度限制避免无限组合
- **深度优先生成**: 递归生成树状结构的效果链，深度从外到内递减
- **消耗检查**: 在循环中定期检查 `fuzz->exhausted()`，模糊数据耗尽时优雅退出
- **make_fuzz_t 模板**: 泛型辅助模板简化了从模糊数据中生成任意 POD 类型的代码
- **已废弃操作保留**: drawCommand 中保留了部分空的 case（如 28, 46-50），这些是历史上移除的绘制操作，保留占位以维持操作码的稳定性

## 性能考量

- 每个 Canvas 操作最多执行 2000 次迭代，配合深度限制（默认 9），有效控制单次模糊测试的执行时间
- `make_fuzz_image` 分配 w*h 大小的像素数据（最大 1024x1024），在模糊测试中可能产生较大的内存分配
- 渐变颜色数量限制为 12，卷积核大小限制为 5x5，vertex 数量限制为 100，确保操作的计算量可控
- 文本 glyph 数量限制为 30 (`kMaxGlyphCount`)，文本 blob 最多 8 个 run，避免文本处理的过度开销
- `AutoTMalloc` 用于图像数据的分配，并通过 `data.release()` 转移所有权给 `SkImage`

## 相关文件

- `fuzz/Fuzz.h` - 模糊数据读取器
- `fuzz/FuzzCommon.h` - 基础模糊工具函数
- `include/core/SkCanvas.h` - Canvas API
- `include/core/SkPaint.h` - Paint 定义
- `include/effects/SkImageFilters.h` - 图像滤镜工厂
- `include/effects/SkGradient.h` - 渐变着色器
