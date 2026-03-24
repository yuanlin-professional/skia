# SkSVGFeComposite

> 源文件: modules/svg/include/SkSVGFeComposite.h

## 概述

`SkSVGFeComposite` 实现 SVG `<feComposite>` 滤镜原语,使用 Porter-Duff 合成操作或算术运算合成两个输入图像。继承自 `SkSVGFe`。

## 主要功能

- Porter-Duff 合成操作(over, in, out, atop, xor)
- 算术合成(result = k1*i1*i2 + k2*i1 + k3*i2 + k4)
- 支持复杂的图像合成效果
- 映射到 Skia 合成操作

## 核心属性

- `operator`: 合成操作类型(over, in, out, atop, xor, arithmetic)
- `k1, k2, k3, k4`: 算术运算系数(仅用于 arithmetic 模式)
- `in`, `in2`: 输入源

## Porter-Duff 操作

标准的图形合成操作,根据源和目标的 alpha 通道确定合成结果。广泛用于图层混合和遮罩效果。

## 算术模式

通过线性组合实现自定义合成效果,公式: `result = k1*i1*i2 + k2*i1 + k3*i2 + k4`,提供最大的灵活性。

## 相关文件

- `modules/svg/src/SkSVGFeComposite.cpp`: 实现
- `SkSVGFe.h`: 滤镜效果基类
- `include/core/SkBlendMode.h`: Skia 混合模式

该滤镜原语是实现复杂合成效果的核心工具,支持多种合成策略。
