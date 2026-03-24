# svg/include - SVG 模块公共头文件

## 概述

`modules/svg/include/` 目录包含 SVG 模块的所有公共头文件,定义了 SVG 文档对象模型的完整类型层次结构。这些头文件可分为以下几大类别:文档入口 (`SkSVGDOM`)、节点基类与属性系统 (`SkSVGNode`、`SkSVGAttribute`、`SkSVGTypes`)、渲染上下文 (`SkSVGRenderContext`)、具体形状元素、渐变与图案、滤镜系统以及辅助容器。

所有 SVG 节点类都继承自 `SkSVGNode`,并通过引用计数 (`SkRefCnt`) 进行内存管理。表现属性 (Presentation Attributes) 通过 `SVG_PRES_ATTR` 宏统一定义在基类中,支持 CSS 属性继承语义。每个具体节点类通过 `SVG_ATTR` 宏定义其特有属性。

滤镜头文件构成了一个独立的子系统,所有滤镜效果都继承自 `SkSVGFe`,通过 `SkSVGFilterContext` 连接滤镜原语的输入输出,最终生成 Skia 的 `SkImageFilter` 对象。

## 架构图

```
SkRefCnt
  +-- SkSVGNode (基类, 表现属性)
       +-- SkSVGTransformableNode (变换支持)
       |    +-- SkSVGContainer (子节点管理)
       |    |    +-- SkSVGSVG         # <svg> 根元素
       |    |    +-- SkSVGG           # <g> 分组
       |    +-- SkSVGShape (绘制接口)
       |         +-- SkSVGRect        # <rect>
       |         +-- SkSVGCircle      # <circle>
       |         +-- SkSVGEllipse     # <ellipse>
       |         +-- SkSVGLine        # <line>
       |         +-- SkSVGPath        # <path>
       |         +-- SkSVGPoly        # <polygon>/<polyline>
       |         +-- SkSVGImage       # <image>
       +-- SkSVGHiddenContainer (不可见容器)
            +-- SkSVGDefs            # <defs>
            +-- SkSVGGradient        # 渐变基类
            |    +-- SkSVGLinearGradient
            |    +-- SkSVGRadialGradient
            +-- SkSVGFe (滤镜基类)
            |    +-- SkSVGFeBlend / FeColorMatrix / FeGaussianBlur ...
            +-- SkSVGClipPath / SkSVGMask / SkSVGFilter / SkSVGPattern
```

## 关键类与函数

| 头文件 | 核心类型 | 说明 |
|--------|---------|------|
| `SkSVGDOM.h` | `SkSVGDOM`, `SkSVGDOM::Builder` | 文档入口,从流解析 SVG 并渲染 |
| `SkSVGNode.h` | `SkSVGNode`, `SkSVGTag` | 节点基类,枚举所有 SVG 标签类型 |
| `SkSVGRenderContext.h` | `SkSVGRenderContext`, `SkSVGLengthContext`, `SkSVGPresentationContext` | 渲染状态管理 |
| `SkSVGTypes.h` | `SkSVGLength`, `SkSVGColor`, `SkSVGPaint` 等 | SVG 值类型定义 |
| `SkSVGAttribute.h` | `SkSVGPresentationAttributes` | 表现属性集合结构体 |
| `SkSVGAttributeParser.h` | `SkSVGAttributeParser` | 字符串到类型值的解析 |
| `SkSVGShape.h` | `SkSVGShape` | 可绘制形状的基类 |
| `SkSVGContainer.h` | `SkSVGContainer` | 具有子节点的容器基类 |
| `SkSVGGradient.h` | `SkSVGGradient` | 线性/径向渐变基类 |
| `SkSVGFe.h` | `SkSVGFe` | 滤镜效果基类 |
| `SkSVGFilterContext.h` | `SkSVGFilterContext` | 滤镜原语间的输入输出路由 |
| `SkSVGText.h` | `SkSVGText` | SVG 文本渲染 |
| `SkSVGIDMapper.h` | `SkSVGIDMapper` | ID 字符串到节点指针的哈希映射 |
| `SkSVGValue.h` | `SkSVGValue` | 属性值基类 (已部分废弃) |

## 依赖关系

- **Skia Core**: `SkRefCnt`, `SkCanvas`, `SkPaint`, `SkPath`, `SkMatrix`, `SkImageFilter`
- **modules/skresources**: `ResourceProvider` 接口
- **modules/skshaper**: `SkShapers::Factory` 文本整形工厂

## 相关文档与参考

- SVG 模块概述: `modules/svg/README.md`
- SVG 1.1 规范: https://www.w3.org/TR/SVG11/
- 滤镜规范: https://www.w3.org/TR/SVG11/filters.html
