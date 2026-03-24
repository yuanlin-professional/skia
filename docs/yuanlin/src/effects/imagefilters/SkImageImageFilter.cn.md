# SkImageImageFilter

> 源文件: `src/effects/imagefilters/SkImageImageFilter.cpp`

## 概述

`SkImageImageFilter` 实现了将一张 `SkImage` 作为图像滤镜输出的功能。它是一个叶子滤镜(不依赖其他输入滤镜),将指定图像的源矩形区域映射并绘制到目标矩形区域。该滤镜是所有基于图像源的图像滤镜效果的基础,常用于图像合成和叠加场景。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkImageImageFilter (本文件)
            └─ 叶子滤镜,无输入子滤镜

工厂方法: SkImageFilters::Image()
```

该滤镜位于 Skia 图像滤镜效果层,通过 `SkImageFilters::Image()` 工厂方法创建,是滤镜 DAG(有向无环图)中的叶子节点。

## 主要类与结构体

### `SkImageImageFilter`
- 继承自 `SkImageFilter_Base`
- **构造参数**: `sk_sp<SkImage> image`, `SkRect srcRect`, `SkRect dstRect`, `SkSamplingOptions sampling`
- **成员变量**:
  - `fImage` (`sk_sp<SkImage>`): 源图像
  - `fSrcRect` (`SkRect`): 源图像的采样区域(相对于图像坐标)
  - `fDstRect` (`skif::ParameterSpace<SkRect>`): 目标矩形(参数空间坐标)
  - `fSampling` (`SkSamplingOptions`): 采样选项(如双线性、最近邻等)

## 公共 API 函数

### `SkImageFilters::Image(image, srcRect, dstRect, sampling) -> sk_sp<SkImageFilter>`
工厂方法,创建图像滤镜。包含以下验证和调整逻辑:
- 空的 srcRect/dstRect 或空图像返回 `SkImageFilters::Empty()`
- 当 srcRect 超出图像边界时,自动裁剪 srcRect 并按比例调整 dstRect
- 使用 `SkMatrix::RectToRectOrIdentity` 计算源到目标的映射

### `computeFastBounds(const SkRect&) const -> SkRect`
忽略输入边界,直接返回 `fDstRect`,因为输出仅取决于目标矩形。

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 直接委托给 `FilterResult::MakeFromImage()`,传递图像、源矩形、目标矩形和采样选项。这是最简单的图像滤镜实现之一。

### 边界计算
- `onGetInputLayerBounds()`: 返回空矩形,因为这是叶子滤镜,不需要任何输入
- `onGetOutputLayerBounds()`: 将 `fDstRect` 从参数空间映射到图层空间并圆整到像素边界

### 矩阵能力
声明 `MatrixCapability::kComplex`,表示该滤镜支持任意复杂的变换矩阵,因为图像本身可以被任意变换。

### 序列化兼容性
- `SkRegisterImageImageFilterFlattenable()` 同时注册了旧名称 `SkImageSourceImpl` 的反序列化回调,确保旧版 SKP 文件的向后兼容
- `CreateProc` 处理版本差异:旧版使用 FilterQuality,新版使用 `SkSamplingOptions`

### 源矩形裁剪
工厂方法中对 srcRect 超出图像边界的情况进行了精确处理:
1. 计算 srcRect 到 dstRect 的映射矩阵
2. 将 srcRect 裁剪到图像边界
3. 将裁剪后的 srcRect 通过映射矩阵得到对应的 dstRect

## 依赖关系

- `include/core/SkImage.h` - 源图像类型
- `include/core/SkSamplingOptions.h` - 采样配置
- `src/core/SkImageFilterTypes.h` - `skif::FilterResult`, `skif::Context`, 空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkReadBuffer.h` / `SkWriteBuffer.h` - 序列化支持
- `src/core/SkPicturePriv.h` - SKP 版本常量
- `src/core/SkSamplingPriv.h` - 采样选项的版本兼容转换

## 设计模式与设计决策

### 叶子滤镜模式
作为滤镜 DAG 的叶子节点,不接受任何子滤镜输入(构造时传递 `nullptr, 0`)。这与 `SkShaderImageFilter` 和 `SkPictureImageFilter` 共享相同的设计理念。

### 参数空间标注
`fDstRect` 使用 `skif::ParameterSpace<SkRect>` 类型标注,明确该矩形位于参数空间(即用户坐标系)而非图层空间。`fSrcRect` 则是普通 `SkRect`,因为它相对于图像自身坐标系。

### 工厂方法验证
工厂方法承担了输入验证和边界调整的职责,确保构造出的滤镜对象始终处于有效状态。

## 性能考量

- 作为叶子滤镜,输入边界计算为空,不会触发递归子树求值
- `MakeFromImage` 可能延迟实际的图像处理到绘制时
- 采样选项的选择影响渲染质量和性能的平衡

## 使用示例

典型使用场景:
1. **图像叠加**: 将一张纹理图像叠加到画布上,指定源区域和目标位置
2. **缩放裁剪**: 从大图中选取一个子区域,并缩放到不同尺寸的目标区域
3. **合成管线**: 作为 Blend 滤镜的输入,与其他效果合成

工厂方法的边界处理确保即使用户传入超出图像范围的 srcRect,也能正确裁剪:
```
srcRect 超出图像边界 -> imageBounds.intersect(srcRect) -> 按比例调整 dstRect
```

## 与其他叶子滤镜的对比

| 特性 | ImageImageFilter | ShaderImageFilter | PictureImageFilter |
|------|-----------------|-------------------|-------------------|
| 数据源 | sk_sp<SkImage> | sk_sp<SkShader> | sk_sp<SkPicture> |
| 输出边界 | 有界(dstRect) | 无界 | 有界(cullRect) |
| 影响透明黑色 | 否 | 是 | 否 |
| 矩阵能力 | kComplex | kComplex | kComplex |
| 空间映射 | srcRect -> dstRect | 全域 | cullRect |

## 版本历史

- 旧版名称: `SkImageSourceImpl`
- 采样选项从 FilterQuality 迁移到 SkSamplingOptions (`kImageFilterImageSampling_Version`)
- 工厂方法在旧版与新版之间保持了完全的向后兼容性

### 序列化格式

写入顺序:
1. `SkSamplingOptions` - 采样配置
2. `SkRect srcRect` - 源矩形
3. `SkRect dstRect` - 目标矩形
4. `SkImage` - 图像数据

读取时根据 SKP 版本选择 FilterQuality 或 SkSamplingOptions 反序列化路径。

### 源矩形裁剪算法

工厂方法中的裁剪处理保证了构造出的滤镜的有效性:
1. 计算 srcRect 到 dstRect 的映射矩阵 (`RectToRectOrIdentity`)
2. 将 srcRect 与图像边界取交集
3. 通过映射矩阵变换裁剪后的 srcRect 得到新的 dstRect
4. 若新 dstRect 为空则返回 Empty 滤镜

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkShaderImageFilter.cpp` - 类似的叶子滤镜
- `src/effects/imagefilters/SkPictureImageFilter.cpp` - 类似的叶子滤镜
- `src/core/SkPicturePriv.h` - SKP 版本管理
- `src/core/SkSamplingPriv.h` - 采样选项兼容工具
- `include/core/SkImage.h` - SkImage 类定义
- `include/core/SkSamplingOptions.h` - 采样选项定义
- `include/core/SkMatrix.h` - srcRect 到 dstRect 的映射矩阵计算
