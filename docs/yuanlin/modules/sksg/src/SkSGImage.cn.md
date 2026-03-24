# SkSGImage

> 源文件: modules/sksg/src/SkSGImage.cpp

## 概述

SkSGImage 是 Skia Scene Graph 中的图像渲染节点实现，用于在场景图中绘制位图图像。该文件包含 50 行代码，提供了将 Skia 的 `SkImage` 对象集成到场景图系统的能力。Image 节点支持抗锯齿、采样选项和所有标准的渲染上下文修改（透明度、混合模式、遮罩着色器等）。

## 架构位置

Image 节点在场景图层次中的位置：

```
RenderNode (可渲染节点基类)
    ├── Draw (组合几何与绘制)
    ├── Group (容器)
    └── Image (图像节点) ← 当前文件
```

## 主要类与结构体

### Image

```cpp
class Image final : public RenderNode {
public:
    static sk_sp<Image> Make(sk_sp<SkImage> image);

    SG_ATTRIBUTE(Image, sk_sp<SkImage>, fImage)
    SG_ATTRIBUTE(SamplingOptions, SkSamplingOptions, fSamplingOptions)
    SG_ATTRIBUTE(AntiAlias, bool, fAntiAlias)

protected:
    explicit Image(sk_sp<SkImage>);

    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    sk_sp<SkImage> fImage;                         // 图像对象
    SkSamplingOptions fSamplingOptions;            // 采样选项
    bool fAntiAlias = false;                       // 抗锯齿
};
```

## 公共 API 函数

### Image::Make()

```cpp
static sk_sp<Image> Make(sk_sp<SkImage> image);
```

创建图像节点。

**使用示例**：
```cpp
sk_sp<SkImage> bitmap = SkImages::RasterFromBitmap(...);
auto image_node = Image::Make(bitmap);
image_node->setAntiAlias(true);
image_node->setSamplingOptions(SkSamplingOptions(SkFilterMode::kLinear));
```

## 内部实现细节

### onRender()

```cpp
void Image::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    if (!fImage) {
        return;  // 无图像，跳过绘制
    }

    SkPaint paint;
    paint.setAntiAlias(fAntiAlias);

    // 创建局部渲染上下文
    sksg::RenderNode::ScopedRenderContext local_ctx(canvas, ctx);

    if (ctx) {
        // 遮罩着色器需要图层隔离
        if (ctx->fMaskShader) {
            local_ctx.setIsolation(this->bounds(), canvas->getTotalMatrix(), true);
        }
        // 应用上下文修改（透明度、着色器等）
        local_ctx->modulatePaint(canvas->getTotalMatrix(), &paint);
    }

    // 绘制图像（在原点）
    canvas->drawImage(fImage, 0, 0, fSamplingOptions, &paint);
}
```

**关键点**：
- 遮罩着色器需要图层隔离（通过 `saveLayer`）
- 图像绘制在原点 (0, 0)，位置由外部变换控制
- 采样选项控制缩放质量（最近邻/双线性/双三次）

### onNodeAt()

```cpp
const RenderNode* Image::onNodeAt(const SkPoint& p) const {
    SkASSERT(this->bounds().contains(p.x(), p.y()));
    return this;
}
```

简单的点击测试：边界内的所有点都命中。

### onRevalidate()

```cpp
SkRect Image::onRevalidate(InvalidationController*, const SkMatrix& ctm) {
    return fImage ? SkRect::Make(fImage->bounds()) : SkRect::MakeEmpty();
}
```

边界为图像的像素尺寸。

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGImage.h"  // 公共头文件
#include "include/core/SkCanvas.h"           // 画布
#include "include/core/SkImage.h"            // 图像对象
#include "include/core/SkPaint.h"            // 绘制属性
#include "include/core/SkPoint.h"            // 点坐标
#include "include/private/base/SkAssert.h"   // 断言
```

## 设计模式与设计决策

### 遮罩着色器的特殊处理

```cpp
if (ctx->fMaskShader) {
    local_ctx.setIsolation(this->bounds(), canvas->getTotalMatrix(), true);
}
```

遮罩着色器不能直接通过 `drawImage` 应用，需要图层隔离。这是 Skia API 的限制。

### 原点绘制策略

图像总是绘制在 (0, 0)，位置通过外部变换矩阵控制。这简化了实现并与场景图的变换系统一致。

## 性能考量

### 图像缓存

`SkImage` 是不可变的共享对象，多个节点可以安全地共享同一图像而无需复制像素数据。

### 采样选项

```cpp
SkSamplingOptions options(SkFilterMode::kLinear);  // 双线性，平衡质量和速度
SkSamplingOptions options(SkCubicResampler::Mitchell());  // 双三次，高质量但慢
```

## 相关文件

- **modules/sksg/include/SkSGImage.h** - Image 节点公共接口
- **include/core/SkImage.h** - Skia 图像类
- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点基类
