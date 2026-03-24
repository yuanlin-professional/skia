# svg - SVG 渲染模块

## 概述

`modules/svg` 是 Skia 图形库中的 SVG (Scalable Vector Graphics) 渲染模块,提供了完整的 SVG 文档解析和渲染能力。该模块能够将 SVG 格式的矢量图形文件解析为内部节点树结构,并通过 Skia 的 Canvas API 进行高质量渲染。

SVG 模块采用 DOM (Document Object Model) 架构,将 SVG 文档映射为一棵由 `SkSVGNode` 派生类组成的节点树。每个 SVG 元素(如 `<rect>`、`<circle>`、`<path>` 等)都有对应的 C++ 类表示。模块支持 SVG 1.1 规范中的大部分特性,包括基本形状、路径、渐变、滤镜、裁剪、遮罩和文本渲染。

滤镜子系统是该模块的一大亮点,实现了包括高斯模糊、颜色矩阵、混合、合成、位移映射、形态学操作、湍流效果等在内的多种 SVG 滤镜原语。滤镜通过 `SkSVGFilterContext` 管理输入输出链,最终映射到 Skia 的 `SkImageFilter` 系统。

渲染上下文 `SkSVGRenderContext` 是整个渲染流程的核心,它管理着继承的表现属性(如填充色、描边宽度、字体等)、长度解析上下文、裁剪路径以及资源查找等功能。渲染过程采用自顶向下的遍历方式,每个节点在渲染前会将自身的属性应用到上下文中。

## 架构图

```
                        +-----------------+
                        |    SkSVGDOM     |
                        | (文档根入口)    |
                        +--------+--------+
                                 |
                        +--------v--------+
                        |   SkSVGSVG      |
                        | (SVG 根元素)    |
                        +--------+--------+
                                 |
              +------------------+------------------+
              |                  |                  |
     +--------v------+  +-------v-------+  +-------v-------+
     | SkSVGContainer|  |  SkSVGShape   |  |SkSVGHidden    |
     | (G, Defs等)   |  | (形状元素)    |  |Container      |
     +--------+------+  +-------+-------+  +-------+-------+
              |                  |                  |
     +--------+------+  +-------+-------+  +-------+-------+
     | 子节点树      |  | Rect/Circle/  |  | Gradient/     |
     |               |  | Path/Line/    |  | Filter/       |
     |               |  | Poly/Ellipse  |  | ClipPath/Mask |
     +---------------+  +---------------+  +---------------+
              |
     +--------v------------------+
     |  SkSVGRenderContext       |
     |  - LengthContext          |
     |  - PresentationContext    |
     |  - Canvas                 |
     |  - IDMapper               |
     |  - FilterContext          |
     +---------------------------+
```

## 目录结构

```
modules/svg/
+-- BUILD.gn                    # GN 构建配置
+-- BUILD.bazel                 # Bazel 构建配置
+-- svg.gni                     # GNI 源文件列表
+-- include/                    # 公共头文件
|   +-- SkSVGDOM.h              # SVG 文档对象模型入口
|   +-- SkSVGNode.h             # 节点基类与表现属性宏
|   +-- SkSVGRenderContext.h    # 渲染上下文
|   +-- SkSVGShape.h            # 形状基类
|   +-- SkSVGContainer.h        # 容器节点基类
|   +-- SkSVGTypes.h            # SVG 类型定义
|   +-- SkSVGAttribute.h        # 属性定义
|   +-- SkSVGAttributeParser.h  # 属性解析器
|   +-- SkSVGGradient.h         # 渐变基类
|   +-- SkSVGFilter.h           # 滤镜容器
|   +-- SkSVGFilterContext.h    # 滤镜上下文
|   +-- SkSVGFe.h               # 滤镜效果基类
|   +-- SkSVGFe*.h              # 各滤镜原语 (Blend/Blur/ColorMatrix等)
|   +-- SkSVGRect.h / SkSVGCircle.h / SkSVGEllipse.h  # 基本形状
|   +-- SkSVGPath.h / SkSVGLine.h / SkSVGPoly.h       # 路径与线段
|   +-- SkSVGText.h             # 文本渲染
|   +-- SkSVGImage.h            # 图像嵌入
|   +-- SkSVGUse.h              # <use> 元素引用
|   +-- SkSVGClipPath.h         # 裁剪路径
|   +-- SkSVGMask.h             # 遮罩
|   +-- SkSVGPattern.h          # 图案填充
|   +-- SkSVGIDMapper.h         # ID 到节点的映射
+-- src/                        # 实现文件
|   +-- SkSVGDOM.cpp            # DOM 解析与构建
|   +-- SkSVGNode.cpp           # 节点基类实现
|   +-- SkSVGRenderContext.cpp  # 渲染上下文实现
|   +-- SkSVGAttributeParser.cpp # 属性值解析实现
|   +-- SkSVG*.cpp              # 各元素类型实现
+-- tests/                      # 单元测试
|   +-- Text.cpp                # 文本测试
|   +-- Filters.cpp             # 滤镜测试
+-- utils/                      # 工具程序
    +-- SvgTool.cpp             # SVG 命令行工具
```

## 关键类与函数

| 类/函数 | 文件 | 说明 |
|---------|------|------|
| `SkSVGDOM` | `include/SkSVGDOM.h` | SVG 文档入口,提供 Builder 模式创建和 `render(SkCanvas*)` 渲染接口 |
| `SkSVGDOM::Builder` | `include/SkSVGDOM.h` | 构建器,可设置字体管理器、资源提供者和文本整形工厂 |
| `SkSVGNode` | `include/SkSVGNode.h` | 所有 SVG 节点的基类,定义继承/非继承表现属性 (SVG_PRES_ATTR 宏) |
| `SkSVGRenderContext` | `include/SkSVGRenderContext.h` | 渲染上下文,管理 Canvas/长度解析/属性继承/资源查找 |
| `SkSVGLengthContext` | `include/SkSVGRenderContext.h` | 长度解析器,将 SVG 长度单位 (px/em/%) 转换为画布坐标 |
| `SkSVGShape` | `include/SkSVGShape.h` | 形状元素基类,提供 `onDraw()` 虚方法由具体形状实现 |
| `SkSVGContainer` | `include/SkSVGContainer.h` | 容器节点基类,管理子节点列表和递归渲染 |
| `SkSVGGradient` | `include/SkSVGGradient.h` | 渐变基类,收集 stop 颜色并创建 SkShader |
| `SkSVGFe` | `include/SkSVGFe.h` | 滤镜效果基类,生成 `SkImageFilter` |
| `SkSVGFilterContext` | `include/SkSVGFilterContext.h` | 管理滤镜原语之间的输入/输出连接 |
| `SkSVGAttributeParser` | `include/SkSVGAttributeParser.h` | 解析 SVG 属性字符串为类型化的值 |

## 依赖关系

- **Skia Core**: `SkCanvas`, `SkPaint`, `SkPath`, `SkMatrix`, `SkImageFilter`, `SkShader` 等核心绘图 API
- **modules/skresources**: 通过 `ResourceProvider` 加载外部资源(图片等)
- **modules/skshaper**: 文本整形支持,处理 `<text>` 元素的复杂文本布局
- **include/core/SkFontMgr.h**: 字体管理,用于文本渲染

## 设计模式分析

1. **组合模式 (Composite)**: SVG 节点树采用经典的组合模式。`SkSVGContainer` 可以包含任意 `SkSVGNode` 子节点,`SkSVGShape` 作为叶子节点。渲染通过递归遍历实现。

2. **建造者模式 (Builder)**: `SkSVGDOM::Builder` 提供流式 API 来配置字体管理器、资源提供者等依赖,最终调用 `make()` 构建 DOM 实例。

3. **访问者/双分派 (Visitor)**: 通过 `SkSVGTag` 枚举和虚函数实现类型安全的节点处理。

4. **上下文对象 (Context Object)**: `SkSVGRenderContext` 在渲染树遍历过程中传递和累积状态,采用 Copy-on-Write 策略 (`SkTCopyOnFirstWrite`) 优化属性继承。

5. **代理模式 (Proxy)**: `BorrowedNode` 内部类通过临时"借用"节点引用来打破循环引用,实现安全的 `<use>` 元素处理。

## 数据流

```
SVG 文件 (SkStream)
       |
       v
  SkSVGDOM::Builder::make()  -- XML 解析 --> 节点树构建
       |
       v
  SkSVGDOM (持有 SkSVGSVG 根节点 + SkSVGIDMapper)
       |
       v
  render(SkCanvas*) ------> SkSVGRenderContext 创建
       |                          |
       v                          v
  递归遍历节点树            属性继承与解析
       |                     (Fill/Stroke/Font/Transform)
       v                          |
  SkSVGShape::onDraw()           v
  SkSVGContainer::onRender()  长度单位转换 (SkSVGLengthContext)
       |                          |
       v                          v
  SkCanvas 绑定操作         滤镜链构建 (SkSVGFilterContext)
  (drawRect/drawPath/        --> SkImageFilter
   drawTextBlob 等)
```

## 相关文档与参考

- SVG 1.1 规范: https://www.w3.org/TR/SVG11/
- Skia SVG 模块源码: `modules/svg/`
- SkSVGDOM Builder API: `modules/svg/include/SkSVGDOM.h`
- SVG 滤镜规范: https://www.w3.org/TR/SVG11/filters.html
- 资源加载接口: `modules/skresources/include/SkResources.h`
- 文本整形接口: `modules/skshaper/include/SkShaper_factory.h`
