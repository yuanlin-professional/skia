# FilterBoundsSlide

> 源文件: tools/viewer/FilterBoundsSlide.cpp

## 概述

`FilterBoundsSlide` 是一个可视化演示工具,用于展示图像滤镜(Image Filter)的边界计算机制。它详细展示了 Skia 如何计算图像滤镜所需的输入边界和产生的输出边界,这对于理解滤镜的性能影响和内存使用至关重要。该 Slide 使用模糊滤镜作为示例,在屏幕上实时绘制各种边界框,并显示缩放因子如何影响边界计算。

该工具将抽象的边界计算过程具象化,通过不同颜色的边界框展示:
- 红色:Layer 空间中的内容边界
- 深灰色:设备空间中的目标输出边界
- 蓝色:带提示的输出边界
- 绿色:不带提示的输入边界

此外还展示了透视变换下的缩放因子分布,帮助开发者理解滤镜在不同区域的采样密度。

## 架构位置

```
skia/
├── tools/viewer/
│   ├── FilterBoundsSlide.cpp       # 本文件
│   └── Slide.h                      # Slide 基类
├── src/core/
│   ├── SkImageFilterTypes.h         # 滤镜类型定义
│   ├── SkImageFilter_Base.h         # 滤镜基类
│   └── SkMatrixPriv.h               # 矩阵私有工具
└── include/effects/
    └── SkImageFilters.h             # 图像滤镜工厂
```

## 主要类与结构体

### FilterBoundsSample 类

```cpp
class FilterBoundsSample : public Slide {
public:
    FilterBoundsSample();
    void load(SkScalar w, SkScalar h) override;
    void draw(SkCanvas* canvas) override;

private:
    sk_sp<SkImageFilter> fBlur;   // 模糊滤镜实例
    sk_sp<SkImage> fImage;        // 用于绘制的测试图像
};
```

### 边界可视化常量

```cpp
static constexpr float kLineHeight = 16.f;  // 文本行高
static constexpr float kLineInset = 8.f;    // 文本缩进
```

## 公共 API 函数

### 构造函数

```cpp
FilterBoundsSample();
```
设置 Slide 名称为 "FilterBounds"。

### load

```cpp
void load(SkScalar w, SkScalar h) override;
```
- 创建 8x8 像素的模糊滤镜:`SkImageFilters::Blur(8.f, 8.f, nullptr)`
- 生成 300x300 的棋盘图像用于可视化

### draw

```cpp
void draw(SkCanvas* canvas) override;
```
执行完整的边界可视化流程:
1. 在本地坐标空间绘制带模糊的图像
2. 分解当前变换矩阵(`decomposeCTM`)
3. 绘制坐标网格展示变换效果
4. 可视化各种边界计算结果
5. 显示缩放因子分布
6. 输出边界信息文本

## 内部实现细节

### 边界计算流程

```cpp
// 1. 定义目标输出区域(设备空间)
skif::DeviceSpace<SkIRect> targetOutput(target);

// 2. 定义内容边界(参数空间)
skif::ParameterSpace<SkRect> contentBounds(localContentRect);

// 3. 分解变换矩阵
skif::Mapping mapping;
mapping.decomposeCTM(ctm, fBlur.get(), contentCenter);

// 4. 计算各种边界
skif::LayerSpace<SkIRect> hintedLayerBounds =
    as_IFB(fBlur)->getInputBounds(mapping, targetOutput, contentBounds);

skif::LayerSpace<SkIRect> unhintedLayerBounds =
    as_IFB(fBlur)->getInputBounds(mapping, targetOutput, {});

std::optional<skif::DeviceSpace<SkIRect>> hintedOutputBounds =
    as_IFB(fBlur)->getOutputBounds(layerOnly, contentBounds);
```

### 缩放因子可视化

使用对数色彩映射展示缩放因子:

```cpp
static const SkColor4f kScaleGradientColors[] = {
    { 0.05f, 0.0f, 6.f,  1.f },   // 严重下采样 s < 1/8
    { 0.6f,  0.6f, 0.8f, 0.6f },  // 正常下采样 s < 1/2
    { 1.f,   1.f,  1.f,  0.2f },  // 无缩放     s = 1
    { 0.95f, 0.6f, 0.5f, 0.6f },  // 正常上采样 s > 2
    { 0.8f,  0.1f, 0.f,  1.f }    // 严重上采样 s > 8
};
```

在矩形的中心和四个角计算微分面积缩放:

```cpp
float scale = SkMatrixPriv::DifferentialAreaScale(
    mapping.layerToDevice().asM33(),
    SkPoint(mapping.paramToLayer(skif::ParameterSpace<SkPoint>(testPoints[i]))));
```

### 坐标空间管理

代码明确区分四种坐标空间:
- **ParameterSpace**: 参数空间(本地绘图坐标)
- **LayerSpace**: 层空间(滤镜计算坐标,可能经过简化变换)
- **DeviceSpace**: 设备空间(屏幕像素坐标)
- 各空间之间通过 `skif::Mapping` 进行转换

### 网格绘制

生成坐标网格以展示透视变换:

```cpp
static SkPath create_axis_path(const SkRect& rect, float axisSpace) {
    SkPathBuilder localSpace;
    // 绘制水平线
    for (float y = rect.fTop + axisSpace; y <= rect.fBottom; y += axisSpace) {
        localSpace.moveTo(rect.fLeft, y);
        localSpace.lineTo(rect.fRight, y);
    }
    // 绘制垂直线
    for (float x = rect.fLeft + axisSpace; x <= rect.fRight; x += axisSpace) {
        localSpace.moveTo(x, rect.fTop);
        localSpace.lineTo(x, rect.fBottom);
    }
    return localSpace.detach();
}
```

### 信息文本格式化

```cpp
static float print_size(SkCanvas* canvas, const char* prefix,
                        std::optional<SkIRect> rect,
                        float x, float y, const SkFont& font, const SkPaint& paint) {
    canvas->drawString(prefix, x, y, font, paint);
    y += kLineHeight;
    SkString sz;
    if (rect) {
        sz.appendf("%d x %d", rect->width(), rect->height());
    } else {
        sz.appendf("infinite");
    }
    canvas->drawString(sz, x, y, font, paint);
    return y + kLineHeight;
}
```

处理无限边界的情况(对于某些滤镜,输入边界可能无限)。

## 依赖关系

### 直接依赖

- `include/effects/SkImageFilters.h`: 图像滤镜创建
- `src/core/SkImageFilterTypes.h`: 滤镜类型系统
- `src/core/SkImageFilter_Base.h`: 访问内部边界计算方法
- `src/core/SkMatrixPriv.h`: 矩阵私有工具函数
- `tools/ToolUtils.h`: 工具函数(如创建棋盘图案)

### 间接依赖

- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkPaint.h`: 绘制样式
- `include/effects/SkDashPathEffect.h`: 虚线效果

## 设计模式与设计决策

### 类型安全的坐标空间

使用模板类型包装器确保坐标空间不会混淆:

```cpp
skif::ParameterSpace<SkRect> contentBounds(localContentRect);
skif::LayerSpace<SkIRect> layerBounds = mapping.paramToLayer(contentBounds);
skif::DeviceSpace<SkIRect> deviceBounds = mapping.layerToDevice(layerBounds);
```

这种设计在编译时捕获坐标空间错误。

### 颜色编码约定

一致的颜色编码帮助快速识别不同边界:
- SK_ColorRED: 内容边界
- SK_ColorDKGRAY: 设备目标边界
- SK_ColorBLUE: 带提示的输出
- SK_ColorGREEN: 不带提示的输入

### 对数色彩映射

缩放因子使用对数刻度,因为:
- 人眼对比例变化的感知接近对数
- 涵盖宽广的缩放范围(1/8 到 8)
- 清晰区分上采样和下采样

### 实时反馈

所有边界计算都在每一帧执行,虽然开销较大,但提供了:
- 准确的实时反馈
- 相机变换时的动态更新
- 真实的性能特征展示

## 性能考量

### 每帧边界计算

虽然该 Slide 每帧都重新计算边界,但这反映了 Skia 实际渲染时的行为。边界计算包括:
- 矩阵分解
- 多次坐标空间转换
- 边界扩展(考虑滤镜半径)

### 矩阵分解成本

`decomposeCTM` 是昂贵的操作:
- 分析变换类型(平移、缩放、旋转、透视)
- 决定最佳的 Layer 变换
- 在精度和性能之间平衡

### 网格绘制开销

绘制坐标网格需要大量线段:
```cpp
canvas->drawPath(create_axis_path(...), line_paint(SK_ColorGRAY));
```
但这是必要的视觉辅助,展示变换的非线性效果。

### 缩放因子采样

在 5 个点(中心+四角)采样缩放因子:
- 足以展示缩放分布
- 避免过度采样
- 快速计算(微分面积缩放)

## 相关文件

### 图像滤镜核心

- `src/core/SkImageFilter_Base.h`: 滤镜基类实现
- `src/effects/imagefilters/SkBlurImageFilter.cpp`: 模糊滤镜实现
- `src/core/SkImageFilterTypes.cpp`: 坐标空间系统

### 边界计算相关

- `include/effects/SkImageFilters.h`: 各种滤镜工厂
- `src/core/SkCanvas.cpp`: `saveLayer` 边界处理
- `src/gpu/ganesh/GrRenderTargetContext.cpp`: GPU 边界优化

### 类似的可视化工具

- `tools/viewer/ImageFilterDAGSlide.cpp`: 滤镜图可视化
- `tools/viewer/PathClipSlide.cpp`: 裁剪边界可视化

### 数学工具

- `src/core/SkMatrixPriv.h`: 矩阵分析工具
- `src/core/SkGeometry.h`: 几何计算
