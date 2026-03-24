# SkSVGFe

> 源文件: modules/svg/include/SkSVGFe.h

## 概述

`SkSVGFe` 是所有 SVG 滤镜效果原语的基类,定义滤镜元素的通用接口和属性。继承自 `SkSVGNode`,是 SVG 滤镜系统的核心抽象。

## 核心属性

- `in`: 输入源标识符
- `result`: 输出结果标识符(供后续滤镜使用)
- `x`, `y`, `width`, `height`: 滤镜子区域

## 主要功能

管理滤镜输入/输出,处理滤镜坐标系统,提供滤镜应用接口,支持滤镜链式组合。

## 派生类(滤镜原语)

- `SkSVGFeBlend`: 混合
- `SkSVGFeColorMatrix`: 颜色矩阵
- `SkSVGFeGaussianBlur`: 高斯模糊
- `SkSVGFeComposite`: 合成
- `SkSVGFeMorphology`: 形态学
- 更多滤镜效果...

## 输入源类型

- 具名结果(来自其他滤镜的 `result`)
- 内置源: `SourceGraphic`, `SourceAlpha`, `BackgroundImage`, `FillPaint`, `StrokePaint`

## 相关文件

- `modules/svg/src/SkSVGFe.cpp`: 基类实现
- `SkSVGFilterContext.h`: 滤镜上下文

该基类统一了滤镜原语的接口,支持构建复杂的滤镜效果管线。
