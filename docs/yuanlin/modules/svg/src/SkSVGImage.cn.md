# SkSVGImage

> 源文件: [modules/svg/src/SkSVGImage.cpp](../../../../modules/svg/src/SkSVGImage.cpp)

## 概述

`SkSVGImage` 实现了 SVG `<image>` 元素的解析和渲染逻辑，支持将外部位图图像（通过 data URI 或非本地 URL 引用）嵌入到 SVG 文档中。该类负责属性解析（x、y、width、height、href、preserveAspectRatio）、图像加载（通过 `skresources::ResourceProvider`）、宽高比保持的视口映射以及最终渲染到 `SkCanvas` 上。

## 架构位置

该类位于 Skia SVG 模块的可变换节点层级中，是一个叶子节点（不支持子节点）：

```
SkSVGNode
  └── SkSVGTransformableNode
        └── SkSVGImage  ← 本文件实现
```

在渲染管线中，`SkSVGImage` 在 `onRender` 阶段加载图像并使用 `SkCanvas::drawImageRect` 进行绘制。

## 主要类与结构体

### SkSVGImage
- 继承自 `SkSVGTransformableNode`，对应 SVG `<image>` 元素
- 使用 `SVG_ATTR` 宏声明属性：`X`、`Y`、`Width`、`Height`、`Href`、`PreserveAspectRatio`
- 不支持子节点（`appendChild` 直接输出调试警告）

### SkSVGImage::ImageInfo（结构体）
- `fImage`: 加载后的 `sk_sp<SkImage>` 对象
- `fDst`: 经过宽高比变换后的目标矩形

## 公共 API 函数

### `parseAndSetAttribute`
```cpp
bool parseAndSetAttribute(const char* n, const char* v);
```
解析 SVG 属性 `x`、`y`、`width`、`height`、`xlink:href`、`preserveAspectRatio`。

### `onPrepareToRender`
```cpp
bool onPrepareToRender(SkSVGRenderContext* ctx) const;
```
渲染前检查：href 非空且 width/height 大于 0 时才允许渲染（符合 SVG 1.1 规范）。

### `LoadImage`（静态方法）
```cpp
static ImageInfo LoadImage(const sk_sp<skresources::ResourceProvider>& rp,
                           const SkSVGIRI& iri,
                           const SkRect& viewPort,
                           SkSVGPreserveAspectRatio par);
```
加载图像并计算最终绘制矩形。根据图像尺寸创建隐式 viewBox `(0, 0, width, height)`，通过 `ComputeViewboxMatrix` 结合 `preserveAspectRatio` 计算变换矩阵。

### `onRender`
```cpp
void onRender(const SkSVGRenderContext& ctx) const;
```
核心渲染方法：解析视口矩形，加载图像，使用线性过滤绘制到画布。

### `onAsPath`
```cpp
SkPath onAsPath(const SkSVGRenderContext&) const;
```
返回空路径（图像元素不产生路径表示）。

### `onTransformableObjectBoundingBox`
```cpp
SkRect onTransformableObjectBoundingBox(const SkSVGRenderContext& ctx) const;
```
返回由 x、y、width、height 定义的边界矩形。

## 内部实现细节

### 图像加载机制

文件内部定义了一个静态辅助函数 `::LoadImage`，支持两种 IRI 类型：
- **kDataURI**: 直接将整个 IRI 字符串作为 data 传递给 `ResourceProvider::loadImageAsset`
- **kNonlocal**: 将 URL 拆分为目录路径（`SkOSPath::Dirname`）和文件名（`SkOSPath::Basename`），分别传递给资源提供者

加载成功后，从 `ImageAsset` 获取第 0 帧的图像数据。

### 视口映射

`LoadImage` 静态方法中：
1. 根据光栅图像尺寸创建隐式 viewBox
2. 使用 `ComputeViewboxMatrix`（继承自基类）根据 `preserveAspectRatio` 计算变换矩阵
3. 将变换后的 viewBox 偏移到视口位置（`viewPort.fLeft, viewPort.fTop`）

### 渲染细节

使用 `SkSamplingOptions(SkFilterMode::kLinear)` 进行线性采样绘制，对应中等质量的图像缩放。文件中有 TODO 注释标记尚未实现 `image-rendering` CSS 属性。

## 依赖关系

- **Skia 核心**: `SkCanvas`、`SkImage`、`SkMatrix`、`SkSamplingOptions`、`SkString`
- **Skia 资源模块**: `skresources::ResourceProvider`、`skresources::ImageAsset`
- **SVG 模块**: `SkSVGTransformableNode`（基类）、`SkSVGAttributeParser`、`SkSVGRenderContext`、`SkSVGTypes`
- **Skia 工具**: `SkOSPath`（路径分割）

## 设计模式与设计决策

1. **资源提供者模式**: 图像加载不直接访问文件系统，而是委托给 `skresources::ResourceProvider`，允许客户端自定义资源加载策略（如内存缓存、网络加载等）。

2. **叶子节点设计**: `appendChild` 被重写为无操作并输出调试信息，确保 `<image>` 元素不接受子节点，符合 SVG 规范。

3. **宽高比保持**: 复用基类的 `ComputeViewboxMatrix` 方法处理 `preserveAspectRatio`，与其他 SVG 元素共享相同的视口映射逻辑。

4. **渲染条件守卫**: `onPrepareToRender` 在 href 为空或尺寸为 0 时阻止渲染，这是 SVG 1.1 规范的要求（参见 https://www.w3.org/TR/SVG11/struct.html#ImageElement）。

5. **静态与成员函数分离**: 文件包含两个 `LoadImage` 函数——一个是文件作用域的静态辅助函数（处理 IRI 解析和资源加载），另一个是 `SkSVGImage` 的静态成员方法（处理视口映射和宽高比）。成员方法调用辅助函数，形成了清晰的职责分层。

6. **空路径返回**: `onAsPath` 返回空路径 `{}`，这表明 `<image>` 元素不能被转换为路径表示，在需要路径操作（如裁剪或布尔运算）时会被忽略。

### SVG 属性映射

| SVG 属性 | Skia 内部类型 | 默认值 | 说明 |
|----------|-------------|--------|------|
| `x` | `SkSVGLength` | 0 | 视口左边缘 |
| `y` | `SkSVGLength` | 0 | 视口上边缘 |
| `width` | `SkSVGLength` | 0 | 视口宽度 |
| `height` | `SkSVGLength` | 0 | 视口高度 |
| `xlink:href` | `SkSVGIRI` | 空 | 图像资源引用 |
| `preserveAspectRatio` | `SkSVGPreserveAspectRatio` | 默认 | 宽高比保持设置 |

## 性能考量

- 图像在每次渲染时重新加载（通过 `ResourceProvider`），依赖外部缓存机制避免重复 I/O。若 `ResourceProvider` 未实现缓存，在动画场景中会导致严重的性能问题。
- 使用 `SkFilterMode::kLinear` 提供合理的图像缩放质量，但未支持高质量三次插值或最近邻采样。文件中的 TODO 注释表明 `image-rendering` CSS 属性支持尚在计划中。
- 视口计算涉及矩阵变换（`ComputeViewboxMatrix` 和 `SkMatrix::mapRect`），但仅在渲染时执行一次，开销可忽略。
- `onPrepareToRender` 中的快速检查（href 非空、宽高大于 0）可以在不满足条件时提前终止，避免不必要的图像加载和绘制。
- `drawImageRect` 是 Skia 高度优化的核心绘制操作，在 GPU 后端利用纹理采样实现，性能很高。

### IRI 类型对性能的影响

- **Data URI**: 图像数据直接嵌入 SVG 文档中（Base64 编码），加载时需要解码，但避免了外部文件 I/O。适合小型图标等场景。
- **非本地 URL**: 需要通过 `ResourceProvider` 从文件系统或网络加载，I/O 延迟可能显著影响渲染性能。

### preserveAspectRatio 计算

`ComputeViewboxMatrix` 涉及宽高比比较和矩阵构建，但由于仅处理简单的缩放和平移（不涉及旋转或倾斜），计算量极小。

## 相关文件

- `modules/svg/include/SkSVGImage.h` - 类声明与属性定义
- `modules/svg/include/SkSVGTransformableNode.h` - 可变换节点基类
- `modules/svg/include/SkSVGRenderContext.h` - SVG 渲染上下文
- `modules/skresources/include/SkResources.h` - 资源提供者接口
- `src/utils/SkOSPath.h` - 操作系统路径工具（Dirname/Basename）
- `modules/svg/include/SkSVGTypes.h` - SVG 类型定义（SkSVGLength、SkSVGIRI、SkSVGPreserveAspectRatio）
- `modules/svg/include/SkSVGNode.h` - SVG 节点基类
