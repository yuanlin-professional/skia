# ToolUtils - Skia 测试与工具通用工具集

> 源文件:
> - [tools/ToolUtils.h](../../tools/ToolUtils.h)
> - [tools/ToolUtils.cpp](../../tools/ToolUtils.cpp)

## 概述

ToolUtils 是 Skia 测试基础设施中最核心的通用工具命名空间，提供了大量用于 GM 测试、基准测试和工具程序的辅助函数和类。功能涵盖颜色类型/透明度类型名称转换、棋盘格图案生成、像素比较、路径构造、法线贴图生成、文本 Blob 构建、变量字体 UI 控制等。

## 架构位置

位于 `tools/` 目录下，是几乎所有 Skia 测试和工具程序的基础依赖。它封装了常用的绘图和测试模式，使得 GM、测试用例和查看器能够复用标准化的辅助代码。

## 主要类与结构体

### `HilbertGenerator`
Hilbert 曲线生成器，用于绘制带有颜色渐变的空间填充曲线。
- 基于 "海龟画图" 状态机（位置、方向）递归生成曲线
- 使用彩虹色渐变沿曲线长度变化

### `TopoTestNode`
拓扑排序测试节点，继承自 `SkRefCnt`。
- 提供拓扑排序算法所需的完整接口（临时标记、输出位置、依赖关系）
- 包含 `AllocNodes`、`Shuffle` 等辅助静态方法

### `PixelIter`
逐像素迭代器，用于遍历 SkSurface 的像素数据。

### `VariationSliders`
变量字体变化轴 UI 控制器，管理字体变化参数的滑块状态。
- 从 SkTypeface 读取变化轴参数
- 通过 SkMetaData 与 UI 交互（writeControls/readControls）

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `alphatype_name()` / `colortype_name()` / `colortype_depth()` | 枚举值到字符串转换 |
| `tilemode_name()` | 平铺模式名称 |
| `color_to_565()` | 将不透明颜色从 8888 映射到 565 |
| `get_text_path()` | 获取文本的路径表示 |
| `equal_pixels()` | 像素级比较（支持 SkPixmap、SkBitmap、SkImage） |
| `create_checkerboard_shader/bitmap/image()` | 创建棋盘格图案 |
| `draw_checkerboard()` | 绘制棋盘格到画布 |
| `make_pixmaps()` | 创建含/不含 mipmap 的 pixmap 数组 |
| `makeSurface()` | 创建 Surface，fallback 到光栅 |
| `add_to_text_blob()` | 向 SkTextBlobBuilder 添加文本 |
| `make_star()` | 通过正多边形步进构造星形路径 |
| `create_hemi/frustum/tetra_normal_map()` | 生成不同形状的法线贴图 |
| `copy_to()` / `copy_to_g8()` | 位图颜色类型转换 |
| `ExtractPathsFromSKP()` | 从 SKP 文件中提取所有路径 |
| `A8ComparePaths()` | 通过 A8 抗锯齿渲染比较两条路径 |

## 内部实现细节

- **棋盘格实现**：创建 2x2 单元的位图，使用 `SkTileMode::kRepeat` 平铺创建着色器。
- **文本路径**：通过 `SkFont::getPaths` 获取每个字形路径，应用位置偏移后合并。
- **星形构造**：使用 `numPts` 和 `step` 参数在正多边形顶点间步进连线，`EvenOdd` 填充规则。
- **法线贴图**：通过数学公式为每个像素计算法线向量，转换为 RGB 编码。
- **像素比较**：逐行 `memcmp` 比较，SkImage 版本先通过 `makeRasterImage` 确保可直接访问像素。
- **Hilbert 曲线**：递归生成，每段线段使用线性渐变着色器实现彩虹效果。
- **SKP 路径提取**：通过自定义 `PathSniffer` 画布拦截 `onDrawPath` 回调。

## 依赖关系

- **Skia 核心**：SkCanvas、SkBitmap、SkImage、SkPath、SkPaint、SkFont、SkSurface、SkShader、SkPicture
- **效果**：SkGradient（线性渐变）
- **内部**：SkColorData、SkColorPriv、SkFontPriv、SkMetaData
- **标准库**：cmath、cstring、vector、functional

## 设计模式与设计决策

- **命名空间组织**：使用 `ToolUtils` 命名空间而非类，适合松散相关的工具函数集合。
- **多重载**：`equal_pixels` 提供三种重载，适配不同的图像容器类型。
- **回退策略**：`makeSurface` 先尝试画布的 makeSurface，失败则回退到光栅模式。
- **元数据通信**：VariationSliders 通过 SkMetaData 与查看器 UI 通信，实现松耦合。

## 性能考量

- `equal_pixels` 使用 `memcmp` 逐行比较，对于大图像是线性时间复杂度。
- `make_pixmaps` 在非紧凑行（非偶数层级）添加额外行字节以测试行字节处理。
- HilbertGenerator 递归深度由 `desiredDepth` 控制，较深的曲线会产生大量绘制调用。
- `ExtractPathsFromSKP` 需要完整回放 SKP，对大文件可能较慢。

## 相关文件

- `tools/SkMetaData.h` - UI 元数据通信
- `gm/*.cpp` - 大量 GM 测试使用这些工具函数
- `tests/*.cpp` - 单元测试中的像素比较等
- `tools/viewer/Viewer.cpp` - 使用 VariationSliders
