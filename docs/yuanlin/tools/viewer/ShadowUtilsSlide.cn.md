# ShadowUtilsSlide

> 源文件: `tools/viewer/ShadowUtilsSlide.cpp`

## 概述

ShadowUtilsSlide 是 Skia Viewer 中演示 `SkShadowUtils::DrawShadow` API 的幻灯片。它对多种凸面和凹面路径施加阴影效果，支持不同的变换矩阵和阴影标志，用红色渲染环境光阴影、蓝色渲染聚光阴影。

## 架构位置

属于 `tools/viewer` 模块，展示 Skia 阴影渲染 API 的全面用法。

## 主要类与结构体

### ShadowUtilsSlide
- 继承自 `Slide`
- 成员:
  - `fConvexPaths`: 凸面路径集合（圆角矩形、矩形、圆形、贝塞尔曲线、椭圆等 6 种）
  - `fConcavePaths`: 凹面路径集合（星形、哑铃形 2 种）
  - `fZDelta`: Z 轴偏移量
  - 布尔控制标志: `fShowAmbient`, `fShowSpot`, `fUseAlt`, `fShowObject`, `fIgnoreShadowAlpha`

## 公共 API 函数

- `load(SkScalar w, SkScalar h)`: 构建凸面和凹面测试路径
- `onChar(SkUnichar)`: 键盘交互（W/S/T/O/>/</? 键）
- `draw(SkCanvas*)`: 渲染所有路径及其阴影

## 内部实现细节

### 路径构建
- 凸面路径: RRect、不规则 RRect、矩形、圆形、贝塞尔曲线、椭圆
- 凹面路径: 六角星和哑铃形（使用 `SkPathBuilder`）

### 渲染布局
- 使用两个变换矩阵（单位矩阵和旋转+非均匀缩放矩阵）
- 凸面路径分别以 `kNone_ShadowFlag` 和 `kTransparentOccluder_ShadowFlag` 两种模式绘制
- 光源位置以黑色圆点可视化

### 阴影颜色
- 环境光: `SkColorSetARGB(ambientAlpha * 255, 255, 0, 0)` (红色)
- 聚光: `SkColorSetARGB(spotAlpha * 255, 0, 0, 255)` (蓝色)

## 依赖关系

- `include/utils/SkShadowUtils.h`: 核心阴影 API
- `include/core/SkPoint3.h`: 3D 点/光源
- `include/utils/SkCamera.h`: 摄像机工具
- `src/core/SkBlurMask.h`: 模糊掩码

## 设计模式与设计决策

- **全面性测试**: 覆盖凸面/凹面、透明/不透明遮挡物、不同变换组合
- **颜色编码**: 红蓝分色清晰区分环境光和聚光阴影

## 性能考量

- 每帧绘制约 30+ 个带阴影的路径，适合中等复杂度的性能测试
- 支持动态调整 Z 高度观察阴影变化

## 相关文件

- `tools/viewer/ShadowColorSlide.cpp`: 色调阴影演示
- `include/utils/SkShadowUtils.h`: 阴影 API
