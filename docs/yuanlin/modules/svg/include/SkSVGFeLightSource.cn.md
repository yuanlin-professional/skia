# SkSVGFeLightSource

> 源文件: modules/svg/include/SkSVGFeLightSource.h

## 概述

`SkSVGFeLightSource` 是 SVG 光源元素的基类,用于 `<feDiffuseLighting>` 和 `<feSpecularLighting>` 滤镜。定义三种光源类型。

## 主要功能

- 定义光照滤镜的光源
- 支持三种光源类型
- 提供光照计算所需的参数
- 用于3D光照效果模拟

## 光源类型

### feDistantLight (远距离光源)
平行光,通过方位角和仰角定义方向。模拟太阳光等远距离光源。

### fePointLight (点光源)
从特定点向四周发散的光源,通过 x, y, z 坐标定义位置。模拟灯泡等点状光源。

### feSpotLight (聚光灯)
从特定点沿特定方向照射的锥形光源,具有方向和照射角度。模拟手电筒、聚光灯等。

## 使用场景

与光照滤镜配合使用,创建3D浮雕效果、光照渐变、材质质感等高级视觉效果。

## 相关文件

- `modules/svg/src/SkSVGFeLightSource.cpp`: 实现
- `SkSVGFeLighting.h`: 光照滤镜基类

该类提供光照效果的物理模型,支持真实感图形渲染。
