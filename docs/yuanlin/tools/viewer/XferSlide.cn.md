# XferSlide

> 源文件: `tools/viewer/XferSlide.cpp`

## 概述

XferSlide.cpp 包含两个独立的演示幻灯片。`XferSlide` 是一个交互式混合模式（Blend Mode）演示，允许用户拖拽彩色圆形并切换 9 种 Porter-Duff 混合模式。`CubicResamplerSlide` 是一个三次重采样参数（B, C）的交互式调节工具，对比不同采样参数下的图像缩放效果。

## 架构位置

属于 `tools/viewer` 模块，均继承自 `ClickHandlerSlide`。

## 主要类与结构体

### ModeDrawable / CircDrawable
- `ModeDrawable`: 可拖拽绘制对象基类，含混合模式和位置
- `CircDrawable`: 使用径向渐变绘制的圆形，继承自 `ModeDrawable`

### ModeButton
混合模式按钮，含标签文本、颜色和矩形边界。

### XferSlide
- 4 个 CircDrawable（红/绿/蓝/黑）
- 9 个混合模式按钮（SrcOver, Src, SrcIn, SrcOut, SrcATop, DstOver, DstIn, DstOut, DstATop）
- 通过 saveLayer 实现正确的混合

### CubicResamplerSlide
- 支持三种图像（mandrill、rle、example_4）
- 三列对比：最近邻、线性过滤、三次重采样
- 拖拽控制点调节 B/C 参数

## 公共 API 函数

### XferSlide
- `draw(SkCanvas*)`: 绘制按钮和混合后的圆形
- `onFindClickHandler`: 点击按钮设置模式或拖拽圆形
- `onClick`: 移动选中圆形或应用选中模式

### CubicResamplerSlide
- `load()`: 加载三张测试图像
- `draw()`: 渲染三列对比和 B/C 坐标显示
- 点击域内拖拽调节 {B, C}

## 内部实现细节

### 混合模式演示
使用 `canvas->saveLayer` 创建独立混合空间，4 个圆形在其中以各自的混合模式叠加。选中圆形后点击模式按钮可更改其混合模式。

### 三次重采样
使用 `SkCubicResampler{B, C}` 参数创建采样选项，通过 `makeShader` 将图像作为着色器以 10x 缩放绘制，便于观察采样质量差异。

## 依赖关系

- `include/effects/SkGradient.h`: 径向渐变
- `include/core/SkDrawable.h`: 可绘制对象
- `include/core/SkSamplingOptions.h`: 采样选项
- `tools/viewer/ClickHandlerSlide.h`: 可点击基类

## 设计模式与设计决策

- **分层混合**: 使用 saveLayer 确保混合模式正确应用
- **交互式参数调节**: CubicResampler 的 B/C 参数通过拖拽实时调节
- **Lambda Click**: CubicResamplerSlide 使用 Lambda 封装的 Click 简化交互逻辑

## 性能考量

- saveLayer 引入额外的离屏缓冲区开销
- 图像作为着色器的 10x 缩放触发高分辨率采样

## 相关文件

- `tools/viewer/ClickHandlerSlide.h`: 可点击基类
- `include/core/SkBlendMode.h`: 混合模式定义
