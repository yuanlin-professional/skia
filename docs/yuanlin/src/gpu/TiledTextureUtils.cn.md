# TiledTextureUtils

> 源文件: src/gpu/TiledTextureUtils.h, src/gpu/TiledTextureUtils.cpp

## 概述

`TiledTextureUtils` 是 Skia GPU 模块中专门处理大尺寸图像分块渲染的工具类。当图像尺寸超过 GPU 纹理大小限制，或者为了优化缓存使用和减少内存占用时，该类提供了将大图像分割成多个小瓦片（tiles）进行渲染的功能。这种分块策略能够有效避免上传过大纹理导致的内存压力，同时提高渲染性能。

该工具类提供了一系列静态方法，用于判断是否需要分块、优化采样区域、禁用 mipmap、以及执行实际的分块渲染。它支持多种图像类型（位图、Picture 等），并能智能处理抗锯齿、过滤模式等渲染参数。

## 架构位置

```
skia/
├── include/core/
│   └── SkCanvas.h          # Canvas 绘制接口
├── src/gpu/
│   ├── TiledTextureUtils.h  # 本模块头文件
│   └── TiledTextureUtils.cpp # 本模块实现
└── src/image/
    └── SkImage_Base.h       # 图像基类
```

`TiledTextureUtils` 位于 `src/gpu/` 目录下，属于 Skia GPU 渲染管线的通用工具层。它不依赖于特定的 GPU 后端（Ganesh 或 Graphite），而是提供跨后端的图像分块处理能力。该类与 `SkCanvas`、`SkImage` 等核心绘图类紧密协作，在图像渲染路径中充当优化中间层。

## 主要类与结构体

### TiledTextureUtils 类

**继承关系**: 无继承，纯静态工具类

**关键成员**:

| 成员类型 | 名称 | 说明 |
|---------|------|------|
| enum | `ImageDrawMode` | 图像绘制模式：kOptimized（优化模式）、kDecal（镶边模式）、kSkip（跳过绘制） |
| static | `kBmpSmallTileSize` (1024) | 小瓦片尺寸常量 |

### ImageDrawMode 枚举

定义了图像采样优化后的绘制模式：

| 枚举值 | 说明 |
|--------|------|
| `kOptimized` | src 和 dst 已被限制在图像内容内，可能需要 clamp，无需 decal |
| `kDecal` | src 和 dst 保持原始尺寸，需要使用 decal 而非简单 clamp |
| `kSkip` | src 或 dst 为空或不与图像内容相交，跳过绘制 |

## 公共 API 函数

### 1. ShouldTileImage

```cpp
static bool ShouldTileImage(
    SkIRect conservativeClipBounds,
    const SkISize& imageSize,
    const SkMatrix& ctm,
    const SkMatrix& srcToDst,
    const SkRect* src,
    int maxTileSize,
    size_t cacheSize,
    int* tileSize,
    SkIRect* clippedSubset)
```

**功能**: 判断是否应该对图像进行分块渲染
**返回**: 如果需要分块则返回 `true`，并输出 `tileSize` 和 `clippedSubset`
**决策因素**:
- 图像尺寸是否超过 `maxTileSize`
- 图像面积与缓存大小的比例
- 实际使用的图像区域（考虑裁剪和变换）

### 2. OptimizeSampleArea

```cpp
static ImageDrawMode OptimizeSampleArea(
    const SkISize& imageSize,
    const SkRect& origSrcRect,
    const SkRect& origDstRect,
    const SkPoint dstClip[4],
    SkRect* outSrcRect,
    SkRect* outDstRect,
    SkMatrix* outSrcToDst)
```

**功能**: 优化图像采样区域，确保 `outSrcRect` 完全包含在图像边界内
**返回**: 返回优化后的绘制模式
**用途**: 在实际渲染前调整 src 和 dst 矩形，避免超出图像边界导致的采样问题

### 3. CanDisableMipmap

```cpp
static bool CanDisableMipmap(
    const SkMatrix& viewM,
    const SkMatrix& localM,
    bool sharpenMipmappedTextures)
```

**功能**: 判断是否可以禁用 mipmap
**返回**: 如果最小缩放比例大于等于阈值则返回 `true`
**原理**: 当 sharp mipmap 模式下，如果缩放比例 >= `SK_ScalarRoot2Over2`（约 0.707），则不需要使用 mipmap 的较高层级

### 4. ClampedOutsetWithOffset

```cpp
static void ClampedOutsetWithOffset(
    SkIRect* iRect,
    int outset,
    SkPoint* offset,
    const SkIRect& clamp)
```

**功能**: 将矩形向外扩展指定像素，同时限制在 `clamp` 范围内，并调整偏移量
**用途**: 用于处理过滤模式下的边界扩展（如双立方过滤需要额外的 texel padding）

### 5. DrawAsTiledImageRect

```cpp
static std::tuple<bool, size_t> DrawAsTiledImageRect(
    SkCanvas* canvas,
    const SkImage* image,
    const SkRect& srcRect,
    const SkRect& dstRect,
    SkCanvas::QuadAAFlags aaFlags,
    const SkSamplingOptions& sampling,
    const SkPaint* paint,
    SkCanvas::SrcRectConstraint constraint,
    bool sharpenMM,
    size_t cacheSize,
    size_t maxTextureSize,
    bool renderLazyPictureTilesOnGPU)
```

**功能**: 主入口函数，执行分块图像矩形绘制
**返回**: `tuple<是否已处理, 绘制的瓦片数量>`
**处理流程**:
1. 优化采样区域
2. 判断是否需要分块
3. 如果需要，则创建瓦片并逐个绘制
4. 使用 `experimental_DrawEdgeAAImageSet` 批量提交

## 内部实现细节

### 分块决策算法

**决定是否分块的三个阶段**:

1. **强制分块**: 如果图像任一维度超过 `maxTileSize`，必须分块
2. **尺寸过滤**: 如果图像面积小于 `4 * kBmpSmallTileSize²`，不分块
3. **缓存效率分析**:
   - 估算完整上传的纹理大小
   - 计算实际使用的瓦片大小
   - 如果使用的瓦片总大小 < 完整纹理的 50%，则分块

### 瓦片尺寸确定

```cpp
int determine_tile_size(const SkIRect& src, int maxTileSize)
```

**策略**:
- 如果 `maxTileSize <= 1024`，直接使用该值
- 否则比较使用 `maxTileSize` 和 `kBmpSmallTileSize` 的瓦片总面积
- 如果大瓦片总面积 > 2 × 小瓦片总面积，选择小瓦片（减少浪费）

### 瓦片绘制实现

`draw_tiled_image` 函数的核心逻辑：

1. **瓦片迭代**: 按网格遍历所有瓦片位置
2. **相交测试**: 跳过与裁剪区域不相交的瓦片
3. **边界处理**:
   - 使用 `ClampedOutsetWithOffset` 处理过滤边界
   - 双立方过滤需要 `kBicubicFilterTexelPad` 像素扩展
   - 线性过滤需要 1 像素扩展
4. **AA 标志保留**: 保留原始矩形外边缘的抗锯齿标志
5. **图像提取**: 调用 `imageProc` 获取瓦片图像
6. **批量提交**: 使用 `ImageSetEntry` 批量绘制所有瓦片

### Picture 图像特殊处理

对于 `SkImage_Picture` 类型：
- 优先在 GPU 上渲染瓦片（如果 `renderLazyPictureTilesOnGPU` 为 true）
- 使用 `makeSubset` 直接提取子矩形
- 否则退回到 CPU 位图提取路径

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkCanvas` | 提供绘制接口和 `experimental_DrawEdgeAAImageSet` |
| `SkImage` | 图像基类，提供 `makeSubset` 等方法 |
| `SkBitmap` | 位图处理，`extractSubset` 提取子位图 |
| `SkSamplingOptions` | 采样选项（过滤模式、mipmap 等） |
| `SkMatrix` | 变换矩阵计算 |
| `SkCanvasPriv` | 访问 Canvas 的内部设备信息 |
| `SkSafeMath` | 安全的整数乘法，避免溢出 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrRecordingContext` | Ganesh 后端使用该工具类进行大图像渲染 |
| `SkDevice` | 设备层调用分块绘制优化大图像 |
| Canvas 绘制路径 | 在 drawImageRect 等方法中作为优化路径 |

## 设计模式与设计决策

### 设计模式

1. **静态工具类模式**: 所有方法都是静态的，无需实例化，体现了纯函数式工具库的设计
2. **策略模式**: `ImageDrawMode` 枚举定义不同的绘制策略
3. **模板方法模式**: `DrawAsTiledImageRect` 定义了分块绘制的总体流程，具体图像提取通过 lambda 回调实现

### 设计决策

**为什么不总是分块？**
- 分块会增加绘制调用次数和状态切换开销
- 小图像分块反而会降低性能
- 只有在内存压力大或纹理尺寸限制时才有必要

**为什么使用 1024 作为小瓦片尺寸？**
- 平衡了瓦片数量和单个瓦片大小
- 1024² = 1MB（RGBA8），适合大多数 GPU 纹理上传单元
- 与常见的 GPU 纹理缓存行大小对齐

**为什么 Picture 图像优先 GPU 渲染？**
- `SkPicture` 可能包含矢量图形和 GPU 加速的绘制命令
- CPU 光栅化会丧失这些优势
- 但对于超大图像，GPU 坐标精度可能不足，需退回 CPU

**边界扩展策略**:
- 双立方过滤 (cubic) 需要 `kBicubicFilterTexelPad` (通常为 2) 像素
- 线性过滤需要 1 像素
- 最近邻过滤不需要扩展

## 性能考量

### 优化点

1. **裁剪优化**: 只渲染与视口相交的瓦片，减少不必要的纹理上传和绘制
2. **缓存效率**: 通过 `SkImage_Raster::MakeFromBitmap(..., kNever)` 保持与原始 `SkPixelRef` 的关联，利用纹理缓存
3. **批量绘制**: 使用 `experimental_DrawEdgeAAImageSet` 一次提交所有瓦片，减少状态切换
4. **Mipmap 禁用**: 对于接近 1:1 缩放的情况禁用 mipmap，减少纹理大小
5. **智能瓦片尺寸**: 根据实际使用情况在大小瓦片间选择，避免过度分割

### 性能权衡

| 场景 | 不分块 | 分块 |
|------|--------|------|
| 小图像 | 最优 | 额外开销 |
| 大图像全显示 | 内存压力大 | 分散上传，性能略降 |
| 大图像部分显示 | 浪费带宽 | 显著节省 |
| 缓存命中率 | 低（大纹理易被驱逐） | 高（小瓦片更持久） |

### 典型性能数据

根据代码注释和常量设置：
- **小瓦片阈值**: 4 × 1024² = 4MB（假设 RGBA8）
- **缓存比例阈值**: 图像大小 > 缓存的 50% 时考虑分块
- **节省阈值**: 实际使用 < 完整纹理的 50% 时启用分块

### 线程安全

`draw_tiled_image` 中的 `imageProc` 回调是同步调用的，不涉及多线程问题。但如果 `SkImage` 本身是惰性的（如 Picture），其内部渲染可能使用多线程。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkCanvas.h` | 使用 | 提供绘制接口 |
| `src/core/SkCanvasPriv.h` | 使用 | 访问 Canvas 内部设备 |
| `src/core/SkDevice.h` | 使用 | 设备层接口 |
| `src/core/SkSamplingPriv.h` | 使用 | 采样选项私有辅助函数 |
| `src/image/SkImage_Base.h` | 使用 | 图像基类和类型判断 |
| `src/image/SkImage_Picture.h` | 使用 | Picture 图像特殊处理 |
| `src/image/SkImage_Raster.h` | 使用 | 从位图创建光栅图像 |
| `src/base/SkSafeMath.h` | 使用 | 安全整数运算 |
| `include/core/SkBitmap.h` | 使用 | 位图操作 |
| `include/core/SkSamplingOptions.h` | 使用 | 采样配置 |
