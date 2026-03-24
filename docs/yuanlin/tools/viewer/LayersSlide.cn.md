# LayersSlide

> 源文件: `tools/viewer/LayersSlide.cpp`

## 概述

LayersSlide.cpp 包含两个幻灯片。`LayersSlide` 演示了 `SkCanvas::saveLayer` 的各种用法，包括多层 saveLayer 嵌套和渐变淡入淡出效果。`BackdropSlide` 展示了 saveLayer 的背景滤镜（backdrop filter）功能，在旋转椭圆区域应用膨胀（Dilate）图像滤镜。

## 架构位置

属于 `tools/viewer` 模块，演示 Skia 图层合成能力。

## 主要类与结构体

### LayersSlide
- 继承自 `Slide`
- 演示 saveLayer 的 alpha 合成和 SrcOver 混合

### BackdropSlide
- 继承自 `ClickHandlerSlide`
- `fCenter`: 可拖拽的滤镜中心点
- `fAngle`: 旋转动画角度
- `fFilter`: 8 像素膨胀滤镜

### test_fade() 辅助函数
创建上下渐变淡入层，使用 `kDstIn` 混合模式实现渐变透明效果。

## 公共 API 函数

- `LayersSlide::draw()`: 演示 saveLayer + SrcMode 擦除椭圆
- `BackdropSlide::draw()`: 在旋转椭圆裁剪区域应用背景滤镜
- `BackdropSlide::animate()`: 5 秒周期旋转

## 内部实现细节

**LayersSlide**: 在红色矩形上使用 `saveLayer` 然后用 `kSrc` 模式、alpha=0 绘制椭圆实现"挖洞"效果。

**BackdropSlide**: 使用 `SaveLayerRec` 的 backdrop filter 参数，在裁剪区域上应用 `SkImageFilters::Dilate(8,8)` 实现局部滤镜效果。mandrill 图像作为背景。

## 依赖关系

- `include/effects/SkGradient.h`: 渐变着色器
- `include/effects/SkImageFilters.h`: 图像滤镜
- `include/utils/SkCamera.h`: 3D 摄像机

## 设计模式与设计决策

- **多种 saveLayer 用法**: 覆盖 alpha 层、混合模式层、背景滤镜层
- **交互式背景滤镜**: 拖拽移动滤镜位置

## 性能考量

- saveLayer 创建离屏缓冲区，多层嵌套增加内存和渲染开销
- 背景滤镜是高开销操作，需要读回并处理当前画布内容

## 相关文件

- `include/core/SkCanvas.h`: saveLayer API
- `include/effects/SkImageFilters.h`: 图像滤镜
