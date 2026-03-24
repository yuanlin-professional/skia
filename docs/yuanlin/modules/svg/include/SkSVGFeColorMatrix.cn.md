# SkSVGFeColorMatrix

> 源文件: modules/svg/include/SkSVGFeColorMatrix.h

## 概述

`SkSVGFeColorMatrix` 实现 SVG `<feColorMatrix>` 滤镜原语,通过矩阵变换或预定义操作修改图像颜色。继承自 `SkSVGFe`(滤镜效果基类)。

## 主要功能

- 支持 5x4 颜色变换矩阵
- 预定义操作: saturate, hueRotate, luminanceToAlpha
- 应用于滤镜管线
- 转换为 Skia `SkColorFilter`

## 核心属性

- `type`: 矩阵类型(matrix, saturate, hueRotate, luminanceToAlpha)
- `values`: 矩阵值或操作参数
- 继承的滤镜属性(in, result 等)

## 使用示例

```xml
<feColorMatrix type="saturate" values="0.5"/>
<feColorMatrix type="hueRotate" values="90"/>
<feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/>
```

## 相关文件

- `modules/svg/src/SkSVGFeColorMatrix.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类
- `include/core/SkColorFilter.h`: Skia 颜色滤镜

该滤镜原语提供强大的颜色操作能力,用于图像特效和颜色校正。
