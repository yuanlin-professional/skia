# SkSVGFeLighting

> 源文件: modules/svg/include/SkSVGFeLighting.h

## 概述

`SkSVGFeLighting` 是光照滤镜的基类,包括 `<feDiffuseLighting>` 漫反射光照和 `<feSpecularLighting>` 镜面反射光照。使用输入图像的 alpha 通道作为凹凸贴图,模拟3D光照效果。继承自 `SkSVGFe`。

## 主要功能

模拟3D表面的光照效果,使用 alpha 通道作为高度图,支持多种光源类型(远距离光、点光源、聚光灯),创建浮雕和材质效果。

## 派生类

### feDiffuseLighting (漫反射)
模拟无光泽表面的光照,创建柔和的3D效果,适用于哑光材质。

### feSpecularLighting (镜面反射)
模拟有光泽表面的光照,创建高光和反射效果,适用于金属或光滑表面。

## 核心属性

- `surfaceScale`: 表面高度缩放因子
- `diffuseConstant` / `specularConstant`: 反射系数
- `specularExponent`: 镜面反射指数(仅镜面光照)
- `kernelUnitLength`: 采样单元长度
- `lighting-color`: 光照颜色

## 光源元素

需要包含光源子元素: `<feDistantLight>`, `<fePointLight>`, 或 `<feSpotLight>`。

## 使用场景

创建浮雕文字、3D按钮、材质质感、高光效果等。

## 相关文件

- `modules/svg/src/SkSVGFeLighting.cpp`: 实现
- `SkSVGFeLightSource.h`: 光源定义
- `SkSVGFe.h`: 滤镜效果基类

光照滤镜提供了在2D环境中模拟3D光照的强大能力,是创建真实感图形的重要工具。
