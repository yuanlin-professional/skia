# ShipSlide

> 源文件: `tools/viewer/ShipSlide.cpp`

## 概述

ShipSlide 是 Skia Viewer 中的一个性能演示幻灯片，通过使用 `drawAtlas` API 在画布上绘制大量旋转的飞船（或企鹅）图像来展示 Atlas 绘制的性能。它在 100x100 的网格中放置 10001 个精灵，每帧对所有精灵进行旋转动画。

## 架构位置

属于 `tools/viewer` 模块，是 Viewer 应用中测试大规模 Atlas 绘制性能的幻灯片。通过 `DEF_SLIDE` 宏注册了两个变体：`DrawShip`（使用原生 drawAtlas）和 `DrawShipSim`（使用模拟的逐个绘制方式）。

## 主要类与结构体

### DrawShipSlide
- 继承自 `Slide`
- 成员:
  - `fProc`: 绘制 Atlas 的函数指针（`DrawAtlasProc`）
  - `fAtlas`: 飞船图片资源（`sk_sp<SkImage>`）
  - `fXform[10001]`: RSXform 变换数组，存储每个精灵的旋转/缩放/位移
  - `fTex[10001]`: 纹理坐标数组

### DrawAtlasProc
函数指针类型，支持两种实现：
- `draw_atlas`: 直接调用 `SkCanvas::drawAtlas`
- `draw_atlas_sim`: 模拟实现，逐个调用 `drawImageRect`

## 公共 API 函数

- `load(SkScalar, SkScalar)`: 加载飞船图片资源，初始化网格位置和变换
- `unload()`: 释放图像资源
- `draw(SkCanvas*)`: 更新旋转变换并绘制所有精灵
- `animate(double)`: 返回 true 以持续刷新

## 内部实现细节

### 旋转动画
每帧通过旋转矩阵乘法更新所有精灵的旋转角度。使用预计算的 `kCosDiff` 和 `kSinDiff` 值（对应约 1 度旋转），避免三角函数调用。旋转公式使用锚点补偿确保绕中心旋转。

### 网格布局
100x100 网格均匀分布在 960x640 的区域内，加上一个位于中心的较大精灵（缩放 0.5 vs 网格中的 0.1），共 10001 个精灵。

### 资源加载
优先加载 `ship.png`，失败后回退到 `baby_tux.png`，二者都失败则不渲染。

## 依赖关系

- `include/core/SkRSXform.h`: RSXform 变换定义
- `include/core/SkCanvas.h`: drawAtlas API
- `tools/DecodeUtils.h` / `tools/Resources.h`: 资源加载
- `tools/viewer/Slide.h`: Slide 基类

## 设计模式与设计决策

- **策略模式**: 通过函数指针 `DrawAtlasProc` 将绘制策略抽象化，注册两个幻灯片变体以对比 Atlas 批处理 vs 逐个绘制的性能
- **预计算优化**: 旋转增量使用固定角度的预计算三角函数值

## 性能考量

- `draw_atlas` 版本将 10001 次绘制批处理为单次 drawAtlas 调用，GPU 可高效处理
- `draw_atlas_sim` 版本逐个调用 drawImageRect，用于基准对比
- 使用线性过滤（`SkFilterMode::kLinear`）进行采样

## 相关文件

- `tools/viewer/AtlasSlide.cpp`: 另一个 Atlas 绘制演示
- `tools/viewer/Slide.h`: Slide 基类
- `include/core/SkRSXform.h`: RSXform 变换
