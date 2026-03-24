# SkSVGFeImage

> 源文件: [modules/svg/src/SkSVGFeImage.cpp](../../../../modules/svg/src/SkSVGFeImage.cpp)

## 概述

`SkSVGFeImage` 实现了 SVG `<feImage>` 滤镜基元，用于在滤镜效果中引入外部图像或引用 SVG 文档中的其他元素。它将图像加载并映射到滤镜效果子区域中，支持通过 `preserveAspectRatio` 属性控制图像的缩放和对齐方式。

## 架构位置

```
SkSVGNode
  └── SkSVGFe                    （滤镜基元基类）
        └── SkSVGFeImage          ← 本文件
```

`SkSVGFeImage` 依赖 `SkSVGImage` 的图像加载能力，将加载的图像包装为 `SkImageFilter` 参与滤镜 DAG。

## 主要类与结构体

### `SkSVGFeImage`

| 属性 | 类型 | 说明 |
|------|------|------|
| `fHref` | `SkSVGIRI` | 图像资源的 IRI 引用（通过 `xlink:href` 设置） |
| `fPreserveAspectRatio` | `SkSVGPreserveAspectRatio` | 宽高比保持策略 |

## 公共 API 函数

### `parseAndSetAttribute(const char* n, const char* v)`
解析 `<feImage>` 元素的属性：
- `xlink:href` - 图像资源引用
- `preserveAspectRatio` - 宽高比保持设置

## 内部实现细节

### 图像滤镜生成 (`onMakeImageFilter`)

1. **确定视口**: 调用 `resolveFilterSubregion()` 获取滤镜效果子区域作为目标视口
2. **加载图像**: 通过 `SkSVGImage::LoadImage()` 加载图像，传入资源提供者、IRI 引用、视口和宽高比设置
3. **验证结果**: 如果图像加载失败，返回 nullptr
4. **创建图像滤镜**: 使用 `SkImageFilters::Image()` 将图像从源矩形映射到目标矩形，采用线性滤波 + 最近 mipmap 采样
5. **裁剪处理**: 通过 `SkImageFilters::Merge()` 将图像滤镜限定在滤镜效果区域内，防止宽高比映射导致内容超出边界

### 宽高比映射与裁剪

由于 `preserveAspectRatio` 的映射可能导致图像绘制到滤镜效果区域之外（例如 `slice` 模式），因此使用 `SkImageFilters::Merge` 配合 `filterEffectsRegion()` 进行显式裁剪。

## 依赖关系

- **Skia Core**: `SkImage`, `SkImageFilter`, `SkRect`, `SkSamplingOptions`
- **Skia Effects**: `SkImageFilters`
- **SVG 模块**: `SkSVGAttributeParser`, `SkSVGFilterContext`, `SkSVGImage`（图像加载）, `SkSVGRenderContext`

## 设计模式与设计决策

1. **委托加载**: 图像加载逻辑委托给 `SkSVGImage::LoadImage()`，复用了 `<image>` 元素的图像加载和宽高比处理能力。

2. **显式裁剪**: 使用 Merge 滤镜作为裁剪机制，是一种巧妙的做法——Merge 滤镜的输出区域自然受限于指定的区域。

3. **采样质量**: 使用 `SkFilterMode::kLinear` + `SkMipmapMode::kNearest` 作为采样选项，在质量和性能之间取得平衡。代码中标注了 TODO，表明未来可能支持 SVG 的 `image-rendering` 属性来控制插值质量。

4. **空图像保护**: 当图像加载失败时返回 nullptr 而非错误，上层滤镜 DAG 构建能够优雅地处理缺失的滤镜基元。

## 性能考量

- 图像加载在滤镜构建时执行，每次滤镜应用都会触发，对于远程资源可能有 I/O 延迟
- 图像缩放使用 `SkFilterMode::kLinear` + `SkMipmapMode::kNearest` 采样，在质量和性能之间取平衡
- Merge 裁剪操作增加了一层图像滤镜节点，但开销较小
- `SkSVGImage::LoadImage` 处理了 preserveAspectRatio 的映射计算，这是纯 CPU 浮点运算
- 图像滤镜节点创建后由 Skia 渲染管线延迟求值，实际图像处理在渲染时由 GPU 执行
- 对于大尺寸图像，线性滤波的采样质量已足够，但 SVG 规范中的 `image-rendering` 属性尚未支持

## 相关文件

- `modules/svg/include/SkSVGFeImage.h` - 头文件定义
- `modules/svg/include/SkSVGImage.h` - 图像加载辅助类，提供 `LoadImage()` 静态方法
- `modules/svg/src/SkSVGFilter.cpp` - 滤镜容器，调用 `makeImageFilter()`
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文，提供 `filterEffectsRegion()`
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文，提供资源提供者
