# SkTiledImageUtils

> 源文件: `include/core/SkTiledImageUtils.h`

## 概述
SkTiledImageUtils 提供了一组工具函数,用于智能处理大型 SkBitmap 支持的图像的绘制。当图像过大无法直接上传到 GPU 时,这些函数会自动将图像分割成小块(tiles)进行绘制;对于已经在 GPU 上的图像或小图像,则直接调用标准 SkCanvas 绘制方法,实现性能最优化。

## 架构位置
该工具位于 Skia 核心(core)模块的图像绘制层,是 SkCanvas 绘制 API 的增强版本。它处于应用层 API 和 GPU 资源管理之间,负责将大图像的绘制请求转换为多个小块的绘制操作,解决 GPU 纹理大小限制问题。

## 命名空间: SkTiledImageUtils

### 设计目标
提供与 SkCanvas::drawImage/drawImageRect 完全兼容的接口,但在内部处理大图像的分块逻辑。用户可以直接替换现有的 Canvas 调用,无需修改其他代码。

## 公共 API 函数

### `DrawImageRect()` - 完整版本
```cpp
SK_API void DrawImageRect(SkCanvas* canvas,
                          const SkImage* image,
                          const SkRect& src,
                          const SkRect& dst,
                          const SkSamplingOptions& sampling = {},
                          const SkPaint* paint = nullptr,
                          SkCanvas::SrcRectConstraint constraint =
                                  SkCanvas::kFast_SrcRectConstraint);
```
- **功能**: 绘制图像的指定源矩形区域到目标矩形,如需要则自动分块
- **参数**:
  - `canvas`: 绘制目标画布
  - `image`: 要绘制的图像(可能被分块)
  - `src`: 源图像中的采样区域
  - `dst`: 画布上的目标矩形
  - `sampling`: 采样选项(滤波模式)
  - `paint`: 可选的绘制属性
  - `constraint`: 源矩形约束(快速模式或严格模式)
- **返回值**: 无
- **说明**: 核心实现函数,其他重载版本最终都会调用此函数

### `DrawImageRect()` - sk_sp 重载
```cpp
inline void DrawImageRect(SkCanvas* canvas,
                          const sk_sp<SkImage>& image,
                          const SkRect& src,
                          const SkRect& dst,
                          const SkSamplingOptions& sampling = {},
                          const SkPaint* paint = nullptr,
                          SkCanvas::SrcRectConstraint constraint =
                                  SkCanvas::kFast_SrcRectConstraint)
```
- **功能**: 接受智能指针的便利重载
- **说明**: 内联函数,直接调用原始指针版本

### `DrawImageRect()` - 无源矩形版本
```cpp
inline void DrawImageRect(SkCanvas* canvas,
                          const SkImage* image,
                          const SkRect& dst,
                          const SkSamplingOptions& sampling = {},
                          const SkPaint* paint = nullptr,
                          SkCanvas::SrcRectConstraint constraint =
                                  SkCanvas::kFast_SrcRectConstraint)
```
- **功能**: 绘制完整图像到目标矩形
- **说明**: 自动创建覆盖整个图像的源矩形 `SkRect::MakeIWH(image->width(), image->height())`

### `DrawImage()` - 基础版本
```cpp
inline void DrawImage(SkCanvas* canvas,
                      const SkImage* image,
                      SkScalar x, SkScalar y,
                      const SkSamplingOptions& sampling = {},
                      const SkPaint* paint = nullptr,
                      SkCanvas::SrcRectConstraint constraint =
                              SkCanvas::kFast_SrcRectConstraint)
```
- **功能**: 在指定位置绘制图像(保持原始尺寸)
- **参数**:
  - `x, y`: 图像左上角的画布坐标
  - 其他参数同 DrawImageRect
- **说明**: 内部构建 `src` 和 `dst` 矩形后调用 DrawImageRect

### `DrawImage()` - sk_sp 重载
```cpp
inline void DrawImage(SkCanvas* canvas,
                      const sk_sp<SkImage>& image,
                      SkScalar x, SkScalar y,
                      const SkSamplingOptions& sampling = {},
                      const SkPaint* paint = nullptr,
                      SkCanvas::SrcRectConstraint constraint =
                              SkCanvas::kFast_SrcRectConstraint)
```
- **功能**: 接受智能指针的便利重载

### `GetImageKeyValues()`
```cpp
SK_API void GetImageKeyValues(const SkImage* image,
                              uint32_t keyValues[kNumImageKeyValues]);
```
- **功能**: 为图像生成可用于缓存键的值集合
- **参数**:
  - `image`: 需要生成键值的图像
  - `keyValues`: 输出数组,必须能容纳 kNumImageKeyValues(6) 个 uint32_t 值
- **返回值**: 通过 keyValues 数组返回
- **说明**: SkImage::uniqueID() 不足以作为缓存键,因为 SkBitmap 支持的 SkImage 可能共享同一 SkBitmap 但引用不同子区域

**常量**:
```cpp
static constexpr int kNumImageKeyValues = 6;
```

## 内部实现细节

### 分块策略
当检测到图像满足以下条件时触发分块:
1. 图像是 SkBitmap 支持的(非 GPU 纹理)
2. 图像尺寸超过 GPU 的最大纹理尺寸限制

分块算法会:
- 计算合适的瓦片大小(通常接近 GPU 纹理大小限制)
- 将源图像和目标矩形按比例分割
- 逐个绘制瓦片,确保边界对齐

### 快速路径优化
对于以下情况直接调用 SkCanvas 原生方法,避免额外开销:
- 图像已经是 GPU 支持的(SkImage::isTextureBacked())
- 图像尺寸在 GPU 限制内
- 图像为 null(提前返回)

### 缓存键生成逻辑
`GetImageKeyValues()` 的复杂性源于不同类型的 SkImage:
- **Bitmap-backed**: 使用 SkBitmap 的 generationID + 子区域信息
- **Picture-backed**: 尝试生成基于 Picture ID、矩阵、尺寸的简洁键;对于复杂情况回退到 image->uniqueID()
- **GPU-backed**: 可以直接使用 uniqueID

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkCanvas.h | 画布绘制 API |
| include/core/SkImage.h | 图像对象定义 |
| include/core/SkRect.h | 矩形几何定义 |
| include/core/SkSamplingOptions.h | 采样/滤波选项 |
| include/core/SkRefCnt.h | 智能指针 sk_sp |
| include/core/SkScalar.h | 浮点类型定义 |

### 被依赖的模块
该工具主要被应用层代码使用:
- **Chromium Blink**: 在 Web 渲染中绘制大图像
- **Android Framework**: 处理高分辨率壁纸和图片
- **Skia 示例和工具**: 测试和演示大图像处理

## 设计模式与设计决策

### 透明代理模式
SkTiledImageUtils 对 SkCanvas 的绘制方法进行透明代理,用户无需知道内部是否进行了分块,API 保持完全一致。

### 策略模式
内部根据图像类型和尺寸选择不同的绘制策略:
- 直接绘制策略(GPU 纹理或小图像)
- 分块绘制策略(大型 Bitmap)

### 内联优化
所有重载函数都声明为 inline,确保在编译时展开,避免函数调用开销。

## 性能考量

### 内存效率
分块绘制避免了一次性将巨大的 Bitmap 上传到 GPU,防止:
- GPU 内存溢出
- 纹理上传超时
- 系统内存压力

### 绘制开销权衡
分块绘制会增加:
- 多次 GPU 状态切换
- 瓦片边界的潜在可见接缝(在某些滤波模式下)

但相比无法绘制或崩溃,这是可接受的代价。

### 缓存优化
`GetImageKeyValues()` 允许实现方为分块结果建立缓存,避免重复的分块计算和绘制。

## 使用场景

### Web 浏览器
在 Chromium 中渲染超大图片(如高分辨率照片、canvas 元素)时,避免超过 GPU 纹理大小限制(通常 8192x8192 或 16384x16384)。

### 图片查看器
显示超高分辨率图像(如医学影像、卫星图片)时,在不降低分辨率的情况下实现平滑绘制。

### 游戏引擎
处理大型地图或背景纹理时,自动分块管理,简化资源管理逻辑。

## 注意事项

### 滤波边界问题
在使用高质量滤波(如 bicubic)时,瓦片边界可能出现细微的不连续。建议在对质量要求极高的场景中:
- 预先调整图像大小到 GPU 可接受范围
- 或使用较低质量的滤波模式

### 变换限制
当前实现假设简单的矩形到矩形映射。复杂的 Canvas 变换(如旋转、透视)可能影响分块质量。

## 相关文件
| 文件 | 关系 |
|------|------|
| src/utils/SkTiledImageUtils.cpp | 实现文件(DrawImageRect 和 GetImageKeyValues 的实际逻辑) |
| include/core/SkCanvas.h | 被代理的原始绘制 API |
| include/core/SkImage.h | 图像对象接口 |
| src/gpu/ganesh/GrCaps.h | GPU 能力查询(最大纹理尺寸) |
| src/image/SkImage_Lazy.cpp | Lazy 图像的分块支持 |
