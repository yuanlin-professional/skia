# svg/src - SVG 模块实现代码

## 概述

`modules/svg/src/` 目录包含 SVG 模块所有公共接口的实现代码。这里的源文件与 `include/` 目录中的头文件一一对应,实现了 SVG 文档的 XML 解析、DOM 构建、属性解析、节点渲染以及滤镜效果的具体逻辑。

核心实现文件 `SkSVGDOM.cpp` 负责将 XML 流解析为 SVG 节点树,使用标签名到工厂函数的映射表来创建对应的节点对象。`SkSVGRenderContext.cpp` 实现了渲染上下文中的属性继承、Paint 构建、裁剪和遮罩应用等关键逻辑。`SkSVGAttributeParser.cpp` 是一个功能丰富的递归下降解析器,能够解析各种 SVG 属性值格式。

滤镜实现文件 (`SkSVGFe*.cpp`) 将各种 SVG 滤镜原语映射到 Skia 的 `SkImageFilter` API。每个滤镜效果类实现 `onMakeImageFilter()` 方法来创建对应的图像滤镜。

## 目录结构

```
src/
+-- SkSVGDOM.cpp                # XML 解析与 DOM 构建
+-- SkSVGNode.cpp               # 节点基类,属性设置分发
+-- SkSVGRenderContext.cpp      # 渲染上下文完整实现
+-- SkSVGAttributeParser.cpp    # SVG 属性值解析器
+-- SkSVGAttribute.cpp          # 属性类型工具
+-- SkSVGValue.cpp              # 值类型工具
+-- SkSVGShape.cpp              # 形状渲染 (fill + stroke)
+-- SkSVGContainer.cpp          # 容器递归渲染
+-- SkSVGTransformableNode.cpp  # 变换矩阵处理
+-- SkSVGRect.cpp / SkSVGCircle.cpp / SkSVGEllipse.cpp  # 基本形状
+-- SkSVGPath.cpp / SkSVGLine.cpp / SkSVGPoly.cpp       # 路径类形状
+-- SkSVGText.cpp               # 文本整形与渲染 (含 SkSVGTextPriv.h)
+-- SkSVGImage.cpp              # 嵌入式图像
+-- SkSVGUse.cpp                # <use> 引用处理
+-- SkSVGSVG.cpp                # <svg> 根元素 viewport 处理
+-- SkSVGGradient.cpp           # 渐变 stop 收集与 shader 构建
+-- SkSVGLinearGradient.cpp     # 线性渐变
+-- SkSVGRadialGradient.cpp     # 径向渐变
+-- SkSVGPattern.cpp            # 图案填充
+-- SkSVGFilter.cpp             # <filter> 容器
+-- SkSVGFilterContext.cpp      # 滤镜输入/输出管理
+-- SkSVGFe.cpp                 # 滤镜基类公共逻辑
+-- SkSVGFeBlend.cpp            # feBlend
+-- SkSVGFeColorMatrix.cpp      # feColorMatrix
+-- SkSVGFeComponentTransfer.cpp # feComponentTransfer
+-- SkSVGFeComposite.cpp        # feComposite
+-- SkSVGFeDisplacementMap.cpp  # feDisplacementMap
+-- SkSVGFeFlood.cpp            # feFlood
+-- SkSVGFeGaussianBlur.cpp     # feGaussianBlur
+-- SkSVGFeImage.cpp            # feImage
+-- SkSVGFeLighting.cpp         # feDiffuseLighting / feSpecularLighting
+-- SkSVGFeLightSource.cpp      # feDistantLight / fePointLight / feSpotLight
+-- SkSVGFeMerge.cpp            # feMerge
+-- SkSVGFeMorphology.cpp       # feMorphology
+-- SkSVGFeOffset.cpp           # feOffset
+-- SkSVGFeTurbulence.cpp       # feTurbulence
+-- SkSVGClipPath.cpp           # 裁剪路径
+-- SkSVGMask.cpp               # 遮罩
+-- SkSVGStop.cpp               # 渐变 stop 元素
+-- SkSVGOpenTypeSVGDecoder.cpp # OpenType SVG 字体解码
+-- SkSVGRectPriv.h             # 矩形私有辅助
+-- SkSVGTextPriv.h             # 文本私有辅助
```

## 关键类与函数

| 源文件 | 核心功能 |
|--------|---------|
| `SkSVGDOM.cpp` | `Builder::make()` -- 从 `SkStream` 解析 XML,按标签名创建节点,构建 ID 映射 |
| `SkSVGRenderContext.cpp` | `applyPresentationAttributes()` -- 应用继承属性; `fillPaint()/strokePaint()` -- 构建 Paint |
| `SkSVGAttributeParser.cpp` | 解析颜色、长度、变换矩阵、路径数据、点列表等所有 SVG 属性值格式 |
| `SkSVGShape.cpp` | `onRender()` -- 先 fill 后 stroke 的双遍绘制逻辑 |
| `SkSVGText.cpp` | 使用 `SkShaper` 进行文本整形,处理 `<text>/<tspan>/<textPath>` |
| `SkSVGFilter.cpp` | 遍历子滤镜原语,构建 `SkImageFilter` 链 |

## 相关文档与参考

- SVG 模块公共 API: `modules/svg/include/`
- Skia Canvas API: `include/core/SkCanvas.h`
- Skia ImageFilter: `include/core/SkImageFilter.h`
