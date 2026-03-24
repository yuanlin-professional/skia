# SkSVGFeTurbulence

> 源文件: modules/svg/include/SkSVGFeTurbulence.h

## 概述

`SkSVGFeTurbulence` 实现 SVG `<feTurbulence>` 滤镜原语,使用 Perlin 噪声函数生成湍流纹理。继承自 `SkSVGFe`,用于创建云彩、大理石、火焰等自然纹理效果。

## 核心属性

- `type`: 噪声类型(turbulence 湍流或 fractalNoise 分形噪声)
- `baseFrequency`: 基础频率(X 和 Y 方向)
- `numOctaves`: 倍频数(噪声叠加层数)
- `seed`: 随机种子
- `stitchTiles`: 是否无缝平铺

## 主要功能

生成程序化纹理,支持分形噪声算法,可创建自然效果(云、木纹、大理石),支持动画(改变种子值)。

## 噪声类型

**turbulence**: 更剧烈的变化,适合云彩、火焰
**fractalNoise**: 更平滑的过渡,适合地形、木纹

## 使用场景

自然纹理生成,背景效果,与其他滤镜组合创建复杂材质,动态纹理动画。

## 相关文件

- `modules/svg/src/SkSVGFeTurbulence.cpp`: 实现
- Perlin 噪声算法实现

该滤镜提供强大的程序化纹理生成能力,是创建自然效果的核心工具。
