# SkPictureImageFilter

> 源文件: `src/effects/imagefilters/SkPictureImageFilter.cpp`

## 概述

`SkPictureImageFilter` 实现了将 `SkPicture`（录制的绘制命令序列）作为图像滤镜输出的功能。它是一个叶子滤镜,将录制的图片在指定的裁剪矩形(cullRect)内进行回放,生成滤镜输出图像。该滤镜适用于需要将预录制的复杂绘制操作嵌入到图像滤镜链中的场景。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkPictureImageFilter (本文件)
            └─ 叶子滤镜,无输入子滤镜
            └─ 持有 sk_sp<SkPicture>

工厂方法: SkImageFilters::Picture(pic, targetRect)
```

## 主要类与结构体

### `SkPictureImageFilter`
- 继承自 `SkImageFilter_Base`，构造时传递 `nullptr, 0`（无子滤镜输入）
- **成员变量**:
  - `fPicture` (`sk_sp<SkPicture>`): 录制的图片对象
  - `fCullRect` (`skif::ParameterSpace<SkRect>`): 图片的裁剪矩形（参数空间）

## 公共 API 函数

### `SkImageFilters::Picture(pic, targetRect) -> sk_sp<SkImageFilter>`
创建图片滤镜。处理逻辑:
- 将 `targetRect` 与图片自身的 `cullRect` 取交集
- 若图片为 null 或交集为空,返回 `SkImageFilters::Empty()`
- 使用交集后的 cullRect 构造滤镜

### `computeFastBounds(const SkRect&) const -> SkRect`
忽略输入边界,直接返回 `fCullRect`,因为输出仅取决于图片的裁剪矩形。

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 委托给 `FilterResult::MakeFromPicture(ctx, fPicture, fCullRect)`。该方法在裁剪矩形范围内回放 SkPicture 的绘制命令。

### 边界计算
- `onGetInputLayerBounds()`: 返回空矩形(叶子滤镜,不需要输入)
- `onGetOutputLayerBounds()`: 将 `fCullRect` 从参数空间映射到图层空间并圆整

### 矩阵能力
声明 `MatrixCapability::kComplex`,支持任意变换矩阵。SkPicture 可以在任意变换下正确回放。

### 序列化
- `flatten()`: 先写入 bool 标记 picture 是否存在,然后通过 `SkPicturePriv::Flatten` 序列化图片数据,最后写入 cullRect
- `CreateProc()`: 读取 bool + 图片 + cullRect,通过工厂方法重建

### 裁剪矩形的交集
构造时断言外部 cullRect 已与图片内部 cullRect 取过交集。工厂方法负责执行此交集操作,确保滤镜不会尝试渲染图片内容范围之外的区域。

## 依赖关系

- `include/core/SkPicture.h` - SkPicture 录制的绘制命令
- `src/core/SkPicturePriv.h` - 图片序列化工具
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类

## 设计模式与设计决策

### 叶子滤镜模式
与 `SkImageImageFilter` 和 `SkShaderImageFilter` 类似,作为滤镜 DAG 的叶子节点,不接受任何子滤镜输入。

### 参数空间裁剪矩形
`fCullRect` 使用 `ParameterSpace` 标注,确保在不同缩放级别下正确映射到图层空间。

### 工厂方法承担验证
工厂方法执行图片有效性检查和裁剪矩形交集,确保构造出的滤镜始终有效。

## 性能考量

- 作为叶子滤镜,输入边界为空,不会触发子树求值
- SkPicture 的回放在裁剪矩形内进行,避免处理不可见内容
- SkPicture 本身支持延迟回放和缓存
- 序列化包含完整的 SkPicture 数据,可能较大

## 使用场景

1. **录制绘制操作嵌入**: 将预先录制的复杂绘制命令(如矢量图标)作为图像滤镜源
2. **SVG 滤镜**: 对应 SVG 中将绘制内容作为滤镜输入的模式
3. **缓存复用**: SkPicture 可以被多次回放,适合重复使用的图案
4. **跨画布共享**: 在一个画布上录制,在另一个画布上通过图像滤镜回放

## 与 SkImageImageFilter 的对比

| 特性 | PictureImageFilter | ImageImageFilter |
|------|-------------------|-----------------|
| 数据源 | 录制的绘制命令 | 栅格化图像 |
| 分辨率 | 回放时决定(矢量) | 固定(位图) |
| 序列化大小 | 取决于命令复杂度 | 取决于图像大小 |
| 输出边界 | cullRect | dstRect |
| 空间映射 | 无(直接回放) | srcRect -> dstRect |
| 采样选项 | 无(矢量回放) | 需指定 |

## 序列化格式

```
[bool] picture_exists
[SkPicture data] (if exists, via SkPicturePriv::Flatten)
[SkRect] cullRect
```

序列化时 SkPicture 的完整数据被写入缓冲区,包括所有绘制操作、图像引用和子图片。这可能导致 SKP 文件较大。反序列化时通过 `SkPicturePriv::MakeFromBuffer` 重建图片。

## cullRect 的双重约束

构造时的断言 `fPicture->cullRect().contains(cullRect)` 确保:
- `fCullRect` 不超出图片自身的裁剪范围
- 工厂方法通过 `cullRect.intersect(targetRect)` 保证了这一条件
- 这避免了回放时渲染图片范围外的无效内容

## 与 SkImage 的差异

SkPicture 和 SkImage 作为图像滤镜源的关键差异:

| 特性 | SkPicture | SkImage |
|------|-----------|---------|
| 内容类型 | 矢量绘制命令 | 栅格化像素 |
| 分辨率依赖 | 按需栅格化,适应当前缩放 | 固定分辨率 |
| 内存模型 | 存储命令序列 | 存储像素数据 |
| 回放开销 | 需要执行绘制命令 | 直接使用像素 |
| 缩放质量 | 始终清晰(矢量) | 放大时模糊 |

## 版本兼容性

- 旧版名称: `SkPictureImageFilterImpl` -> `SkPictureImageFilter`
- 序列化格式: bool(是否有picture) + SkPicture数据(可选) + cullRect
- SkPicture 通过 `SkPicturePriv::Flatten/MakeFromBuffer` 序列化,包含完整的绘制命令数据

## 边界计算详解

作为叶子滤镜,边界计算非常简单:

输入边界: 始终为空(不需要任何输入数据)
输出边界: `mapping.paramToLayer(fCullRect).roundOut()`

`computeFastBounds()` 忽略输入边界参数,直接返回 `fCullRect`,因为输出完全由图片内容和裁剪矩形决定。

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `include/core/SkPicture.h` - SkPicture API
- `src/core/SkPicturePriv.h` - 图片序列化工具
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkImageImageFilter.cpp` - 类似的叶子滤镜(基于图像)
