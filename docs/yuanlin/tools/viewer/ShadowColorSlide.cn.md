# ShadowColorSlide

> 源文件: `tools/viewer/ShadowColorSlide.cpp`

## 概述

ShadowColorSlide 是 Skia Viewer 中的一个演示幻灯片，用于展示色调颜色阴影（tonal color shadows）的渲染效果。该幻灯片在一个网格中绘制 30 个不同颜色的矩形，每个矩形带有阴影效果，支持单通道和双通道两种颜色阴影模式，允许用户通过键盘交互切换各种渲染选项。

## 架构位置

该文件属于 Skia 的 `tools/viewer` 模块，是 Viewer 应用程序的一个幻灯片（Slide）实现。它继承自 `Slide` 基类，通过 `DEF_SLIDE` 宏注册到幻灯片注册表中，可在 Viewer 中浏览和交互。

## 主要类与结构体

### ShadowColorSlide
- 继承自 `Slide`
- 成员变量:
  - `fRectPath`: 用于阴影投射的矩形路径（100x100 像素）
  - `fZIndex`: Z 轴高度索引（0-9），控制阴影深度
  - `fShowAmbient/fShowSpot`: 控制环境光和聚光阴影的显隐
  - `fUseAlt`: 切换几何模式阴影标志
  - `fShowObject`: 控制是否显示投射阴影的物体
  - `fTwoPassColor`: 切换单通道/双通道颜色阴影模式
  - `fDarkBackground`: 切换亮/暗背景

## 公共 API 函数

- `load(SkScalar w, SkScalar h)`: 初始化矩形路径
- `onChar(SkUnichar uni)`: 处理键盘输入（W/S/T/O/X/Z/>/<）
- `draw(SkCanvas* canvas)`: 绘制 3 行 10 列的彩色阴影矩形网格

## 内部实现细节

### 双通道颜色阴影模式 (fTwoPassColor)
分三步绘制阴影：
1. 使用纯黑色绘制环境光阴影
2. 根据颜色亮度计算聚光阴影颜色（使用亮度公式 `0.5*(max+min)/255`）
3. 使用灰度聚光阴影叠加

### 单通道模式
调用 `SkShadowUtils::ComputeTonalColors()` 一次性计算色调环境光和聚光颜色，然后在单次 `DrawShadow` 调用中完成渲染。

### 颜色方案
使用 3 组各 10 个渐变色：紫色系、橙色系、青色系，共 30 种颜色展示不同色调下的阴影效果。

### Z 值系统
预定义 10 个 Z 高度值 `{1, 2, 3, 4, 6, 8, 9, 12, 16, 24}`，通过 `<` 和 `>` 键调节。

## 依赖关系

- `include/core/SkCanvas.h`: 画布绑定
- `include/core/SkPath.h`: 路径构建
- `include/core/SkPoint3.h`: 3D 光源位置
- `include/utils/SkShadowUtils.h`: 核心阴影绘制 API
- `tools/viewer/Slide.h`: Slide 基类

## 设计模式与设计决策

- **交互式演示模式**: 通过键盘快捷键切换多种渲染选项，使开发者能够直观比较不同阴影算法的效果差异
- **单/双通道对比**: 双通道模式将亮度计算和阴影绘制分离，提供更精细的色调控制；单通道模式依赖 `ComputeTonalColors` 内部优化

## 性能考量

- 每帧绘制 30 个带阴影的矩形，双通道模式下每个矩形需要 3 次 `DrawShadow` 调用
- 固定光源宽度（600）和固定光源位置，避免逐帧计算光源参数

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类定义
- `tools/viewer/ShadowUtilsSlide.cpp`: 另一个阴影演示幻灯片
- `include/utils/SkShadowUtils.h`: 阴影工具 API
