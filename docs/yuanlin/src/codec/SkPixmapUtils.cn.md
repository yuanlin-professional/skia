# SkPixmapUtils

> 源文件
> - include/codec/SkPixmapUtils.h
> - src/codec/SkPixmapUtils.cpp

## 概述

`SkPixmapUtils` 是 Skia 中提供像素图（`SkPixmap`）实用工具函数的命名空间。主要功能是处理图像方向（orientation）变换，特别是处理 EXIF 元数据中定义的图像旋转和翻转。该工具在图像解码过程中用于将存储的图像数据转换为正确的显示方向。

核心功能包括：
- 根据 EXIF 方向标签应用几何变换（旋转、翻转）
- 交换图像宽度和高度
- 使用高质量的图形管线执行变换

## 架构位置

`SkPixmapUtils` 位于 Skia 的编解码器支持层：

```
图像加载 (SkImage, SkBitmap)
    ↓
编解码器 (SkCodec)
    ↓
方向处理 (SkPixmapUtils)
    ↓
像素数据 (SkPixmap)
```

该工具与以下系统交互：
- **编解码器层**：在解码后应用方向校正
- **图形管线**：使用 `SkCanvas` 和 `SkSurface` 执行变换
- **像素操作层**：直接操作 `SkPixmap` 数据

## 主要类与结构体

### SkPixmapUtils 命名空间

这是一个包含静态工具函数的命名空间，无类实例。

**主要函数**：

| 函数 | 说明 |
|------|------|
| `Orient()` | 应用 EXIF 方向变换 |
| `SwapWidthHeight()` | 交换宽高尺寸 |

## 公共 API 函数

### Orient

```cpp
SK_API bool Orient(
    const SkPixmap& dst,
    const SkPixmap& src,
    SkEncodedOrigin origin
)
```

**功能**：根据 EXIF 方向标签将源像素图变换到目标像素图

**参数**：
- `dst`：目标像素图（需预先分配正确尺寸）
- `src`：源像素图
- `origin`：EXIF 方向枚举值

**返回值**：
- `true`：变换成功
- `false`：输入无效，未执行变换

**校验条件**：
1. 源和目标的 `colorType` 必须相同
2. 根据方向，可能需要交换宽高
3. 如果需要交换，目标尺寸必须为 `(src.height, src.width)`
4. 如果不需要交换，目标尺寸必须为 `(src.width, src.height)`

**特殊处理**：
- 宽度或高度为 0：直接返回成功
- 源和目标地址相同：仅当 `origin == kTopLeft` 时返回成功
- `alphaType` 和 `colorSpace` 被忽略

**实现方式**：
使用 Skia 图形管线执行变换：
1. 从目标 `SkPixmap` 创建 `SkSurface`
2. 从源 `SkPixmap` 创建 `SkBitmap`
3. 根据方向生成变换矩阵
4. 使用 `SkBlendMode::kSrc` 绘制变换后的图像

### SwapWidthHeight

```cpp
SK_API SkImageInfo SwapWidthHeight(const SkImageInfo& info)
```

**功能**：创建宽高交换的新 `SkImageInfo`

**参数**：
- `info`：原始图像信息

**返回值**：
- 新的 `SkImageInfo`，宽高互换

**用途**：
- 在应用 90° 或 270° 旋转前计算目标尺寸
- 与 `SkEncodedOriginSwapsWidthHeight()` 配合使用

## 内部实现细节

### EXIF 方向值

`SkEncodedOrigin` 枚举定义了 8 种可能的方向（基于 EXIF 标准）：

| 值 | 说明 | 变换 |
|----|------|------|
| `kTopLeft` (1) | 默认方向 | 无变换 |
| `kTopRight` (2) | 水平翻转 | 沿 Y 轴镜像 |
| `kBottomRight` (3) | 旋转 180° | 旋转 180° |
| `kBottomLeft` (4) | 垂直翻转 | 沿 X 轴镜像 |
| `kLeftTop` (5) | 转置 | 转置 + 水平翻转 |
| `kRightTop` (6) | 顺时针旋转 90° | 旋转 90° |
| `kRightBottom` (7) | 反转置 | 转置 + 垂直翻转 |
| `kLeftBottom` (8) | 逆时针旋转 90° | 旋转 270° |

值 5-8 会交换宽度和高度。

### 变换矩阵生成

`SkEncodedOriginToMatrix()` 函数根据方向和目标尺寸生成变换矩阵。例如：

- **旋转 90°**：
  ```
  [0  -1  dst.width]
  [1   0  0         ]
  [0   0  1         ]
  ```

- **水平翻转**：
  ```
  [-1  0  dst.width]
  [0   1  0        ]
  [0   0  1        ]
  ```

### 绘制管线

`draw_orientation()` 函数的执行流程：

```
1. SkSurfaces::WrapPixels(dst) → 包装目标为 Surface
2. SkBitmap::installPixels(src) → 包装源为 Bitmap
3. SkEncodedOriginToMatrix() → 生成变换矩阵
4. Canvas::concat(matrix) → 应用变换
5. Canvas::drawImage() → 绘制图像
   - 使用 SkBlendMode::kSrc 完全替换目标
   - 使用 SkSamplingOptions 控制质量
```

### 零拷贝包装

- `SkSurfaces::WrapPixels()`：包装目标像素缓冲区，无内存分配
- `SkBitmap::installPixels()`：包装源像素缓冲区，无内存拷贝
- `SkImages::RasterFromBitmap()`：创建栅格图像引用

这些操作确保高效的内存使用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPixmap` | 像素图数据结构 |
| `SkEncodedOrigin` | EXIF 方向枚举 |
| `SkImageInfo` | 图像格式描述 |
| `SkSurface` | 绘制表面 |
| `SkCanvas` | 2D 绘制接口 |
| `SkBitmap` | 位图数据结构 |
| `SkImage` | 图像对象 |
| `SkMatrix` | 几何变换矩阵 |
| `SkPaint` | 绘制属性 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkCodec` 子类 | 在解码时调用 `Orient()` 校正方向 |
| `SkJpegCodec` | JPEG 解码器应用 EXIF 方向 |
| `SkWebpCodec` | WebP 解码器处理方向 |
| 图像加载工具 | 任何需要处理图像方向的代码 |

## 设计模式与设计决策

### 命名空间设计

使用命名空间而非类：
- 无状态工具函数，不需要实例化
- 清晰的代码组织
- 避免不必要的对象开销

### 分离关注点

将方向处理独立为工具函数：
- 解码器专注于格式解析
- 方向变换可复用
- 便于测试和维护

### 使用高级管线

通过 `SkCanvas` 执行变换而非手动像素操作：
- **正确性**：利用经过充分测试的图形管线
- **性能**：自动利用 SIMD、GPU 加速等优化
- **质量**：支持高质量的重采样
- **维护性**：无需为每种 `colorType` 实现单独代码

### 严格的输入校验

函数在执行前进行多项检查：
- 防止无效操作
- 早期失败，清晰的错误处理
- 避免数据损坏

## 性能考量

### 零拷贝设计

使用包装（wrap）而非拷贝：
- `WrapPixels()` 和 `installPixels()` 不分配新内存
- 直接在原始缓冲区上操作
- 减少内存占用和带宽

### 快速路径优化

1. **空图像检查**：宽度或高度为 0 时立即返回
2. **别名检查**：源和目标相同时特殊处理
3. **无变换路径**：`kTopLeft` 方向可能跳过绘制

### 图形管线优化

Skia 的图形管线提供自动优化：
- **SIMD 指令**：向量化像素操作
- **多线程**：某些操作可并行
- **缓存友好**：优化的内存访问模式

### 混合模式选择

使用 `SkBlendMode::kSrc`：
- 直接替换目标像素，无混合计算
- 最快的混合模式
- 适合完全覆盖场景

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/codec/SkPixmapUtils.h` | 公共接口声明 |
| `src/codec/SkPixmapUtils.cpp` | 实现代码 |
| `include/codec/SkEncodedOrigin.h` | EXIF 方向枚举和工具 |
| `include/core/SkPixmap.h` | 像素图类 |
| `include/core/SkImageInfo.h` | 图像信息结构 |
| `include/core/SkSurface.h` | 绘制表面接口 |
| `include/core/SkCanvas.h` | 2D 绘制接口 |
| `src/codec/SkJpegCodec.cpp` | JPEG 解码器（使用方向处理） |
