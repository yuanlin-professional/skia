# src/svg - SVG 导出模块

## 概述

`src/svg` 目录是 Skia 图形库中负责将绘制操作导出为 SVG（Scalable Vector Graphics）格式的模块。SVG 是一种基于 XML 的矢量图形格式，广泛应用于 Web 图形、图标和可缩放的图形内容。该模块的核心目标是将 Skia 的 `SkCanvas` 绘制命令忠实地转换为标准 SVG 标记。

模块的核心架构基于 Skia 的设备后端（Device Backend）机制。`SkSVGDevice` 继承自 `SkClipStackDevice`，将所有绘制操作（矩形、椭圆、路径、文本、图像等）转换为对应的 SVG XML 元素。每个绘制调用都会生成适当的 SVG 标签（如 `<rect>`、`<ellipse>`、`<path>`、`<text>`、`<image>` 等），并通过 `SkXMLWriter`（来自 `src/xml` 模块）输出到目标流。

SVG 导出模块支持多种高级特性，包括：线性和径向渐变的导出（转换为 `<linearGradient>` 和 `<radialGradient>`）、图像模式填充（`<pattern>`）、颜色滤镜（`<filter>`）、裁剪路径（`<clipPath>`）、文本属性（字体系列、大小、样式）以及 URL 注解（`<a>` 链接）。此外还支持将文本转换为路径的模式。

该模块提供了 `SkSVGCanvas::Make()` 工厂函数作为公共 API，用户只需提供一个输出流和画布尺寸，即可获得一个将所有绘制操作导出为 SVG 的 `SkCanvas` 实例。输出选项包括文本路径化、XML 美化、相对路径编码等。

## 架构图

```
+------------------------------------------------------------------+
|                    公共 API 层                                     |
|              SkSVGCanvas::Make()                                  |
|              (include/svg/SkSVGCanvas.h)                          |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                    SkSVGDevice                                    |
|   (继承 SkClipStackDevice, src/svg/SkSVGDevice.h)                |
|                                                                   |
|   +---------------------+  +-------------------------+           |
|   | 绘制方法            |  | 资源管理                 |           |
|   | drawRect()          |  | ResourceBucket          |           |
|   | drawOval()          |  |   addGradient()         |           |
|   | drawRRect()         |  |   addPath()             |           |
|   | drawPath()          |  |   addImage()            |           |
|   | drawImageRect()     |  |   addPattern()          |           |
|   | drawPaint()         |  |   addColorFilter()      |           |
|   | drawPoints()        |  +-------------------------+           |
|   | drawAnnotation()    |                                         |
|   | onDrawGlyphRunList()|  +-------------------------+           |
|   +---------------------+  | 裁剪管理                 |           |
|                             | syncClipStack()         |           |
|   +---------------------+  | ClipRec                  |           |
|   | AutoElement         |  +-------------------------+           |
|   | (RAII XML元素管理)  |                                         |
|   | addPaint()          |                                         |
|   | addResources()      |                                         |
|   | addShaderResources()|                                         |
|   | addGradientDef()    |                                         |
|   | addImageShader      |                                         |
|   |   Resources()       |                                         |
|   +---------------------+                                         |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                    SkXMLWriter (src/xml)                          |
|              SkXMLStreamWriter --> SkWStream                      |
+------------------------------------------------------------------+
```

## 目录结构

```
src/svg/
  BUILD.bazel          -- Bazel 构建配置
  SkSVGCanvas.cpp      -- SkSVGCanvas::Make() 工厂函数实现
  SkSVGDevice.h        -- SkSVGDevice 类声明
  SkSVGDevice.cpp      -- SkSVGDevice 类实现（约 1230 行）

相关公共头文件:
  include/svg/SkSVGCanvas.h  -- SkSVGCanvas 公共 API 和选项定义
```

## 关键类与函数

### SkSVGCanvas（公共 API）
- **位置**: `include/svg/SkSVGCanvas.h`, `src/svg/SkSVGCanvas.cpp`
- **职责**: 提供创建 SVG 导出画布的工厂方法
- **工厂方法**: `Make(const SkRect& bounds, SkWStream*, Options opts)`
- **Options 结构体**:
  - `flags` -- 标志位，支持：
    - `kConvertTextToPaths_Flag` (0x01) -- 将文本转换为路径输出
    - `kNoPrettyXML_Flag` (0x02) -- 不生成格式化（缩进/换行）的 XML
    - `kRelativePathEncoding_Flag` (0x04) -- 使用相对路径命令编码
  - `pngEncoder` -- PNG 编码回调函数，用于嵌入的位图图像

### SkSVGDevice（SVG 绘制设备）
- **位置**: `src/svg/SkSVGDevice.h`
- **继承**: `SkClipStackDevice`
- **工厂方法**: `Make(SkISize, std::unique_ptr<SkXMLWriter>, Options)`
- **核心成员**:
  - `fWriter` -- XML 写入器（`unique_ptr<SkXMLWriter>`）
  - `fResourceBucket` -- 资源 ID 生成器
  - `fOpts` -- 导出选项
  - `fRootElement` -- SVG 根元素 `<svg>`
  - `fClipStack` -- 裁剪记录栈
- **绘制方法**: `drawPaint`, `drawRect`, `drawOval`, `drawRRect`, `drawPath`, `drawPoints`, `drawImageRect`, `drawAnnotation`

### SkSVGDevice::AutoElement（RAII XML 元素管理器）
- **位置**: `src/svg/SkSVGDevice.cpp`
- **职责**: RAII 方式管理 XML 元素的开始和结束标签，析构时自动关闭元素
- **核心方法**:
  - `addPaint()` -- 将 SkPaint 转换为 SVG fill/stroke 属性
  - `addResources()` -- 处理着色器、颜色滤镜等资源定义
  - `addShaderResources()` -- 分析着色器类型（颜色/渐变/图像）
  - `addGradientShaderResources()` -- 生成 `<linearGradient>` 或 `<radialGradient>` 定义
  - `addImageShaderResources()` -- 生成 `<pattern>` 和 `<image>` 定义
  - `addColorFilterResources()` -- 生成 `<filter>` 定义
  - `addGradientDef()` -- 生成渐变 `<stop>` 元素
  - `addRectAttributes()` -- 设置矩形的 x/y/width/height 属性
  - `addPathAttributes()` -- 将 SkPath 转为 SVG `d` 属性
  - `addTextAttributes()` -- 设置字体相关的 SVG 属性

### SkSVGDevice::ResourceBucket（资源 ID 管理器）
- **位置**: `src/svg/SkSVGDevice.cpp`
- **职责**: 生成唯一的资源标识符（gradient_0, path_1, img_2, pattern_3 等）
- **方法**: `addGradient()`, `addPath()`, `addImage()`, `addPattern()`, `addColorFilter()`

### SVGTextBuilder（文本构建器）
- **位置**: `src/svg/SkSVGDevice.cpp`
- **职责**: 将字形序列转换为 SVG `<text>` 元素所需的文本内容和位置数据
- **特性**: 处理空白合并、XML 特殊字符转义（`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`）、恒定 Y 坐标优化

### 辅助函数
- `svg_color()` -- SkColor 转 SVG 颜色字符串（支持命名颜色和十六进制）
- `svg_opacity()` -- 提取透明度值
- `svg_cap()` / `svg_join()` -- SkPaint 线帽/接合方式转 SVG 属性
- `svg_transform()` -- SkMatrix 转 SVG transform 属性（translate/scale/matrix）
- `AsDataUri()` -- 将图像编码为 data URI（`data:image/png;base64,...`）
- `RequiresViewportReset()` -- 检测重复图像模式是否需要视口重置

## 依赖关系

### 内部依赖
- `src/xml` -- `SkXMLWriter`, `SkXMLStreamWriter`（XML 标记生成）
- `src/core` -- `SkClipStackDevice`, `SkClipStack`, `SkDevice`, `SkAnnotationKeys`
- `src/base` -- `SkBase64`（图像 Base64 编码）, `SkTLazy`
- `src/shaders` -- `SkShaderBase`, `SkColorShader`（着色器分析）
- `src/text` -- `GlyphRun`（文字渲染）
- `src/image` -- `SkImage_Base`（图像像素访问）
- `include/utils/SkParsePath.h` -- SkPath 转 SVG 路径字符串
- `include/encode/SkPngEncoder.h` 或 `SkPngRustEncoder.h` -- PNG 编码

### 被依赖
- 用户代码通过 `include/svg/SkSVGCanvas.h` 接口使用
- 测试代码

## 设计模式分析

### 设备后端模式（Device Backend）
`SkSVGDevice` 实现了 Skia 设备接口，通过多态将 `SkCanvas` 绘制操作重定向为 SVG XML 输出。

### RAII 模式
`AutoElement` 类在构造时调用 `fWriter->startElement()`，在析构时调用 `fWriter->endElement()`，确保 XML 标签的正确嵌套。这种模式在处理复杂的嵌套元素（`<defs>` 中的 `<linearGradient>` 内的 `<stop>` 等）时尤为重要。

### 资源引用模式
SVG 中渐变、图案等资源定义在 `<defs>` 中，通过 `url(#id)` 引用。`ResourceBucket` 负责生成唯一 ID，`AutoElement::addResources()` 先在 `<defs>` 中定义资源，然后通过引用使用。

### 访问者模式
裁剪栈的同步（`syncClipStack`）通过遍历 `SkClipStack` 并对每个元素生成对应的 `<clipPath>` 定义和 `<g clip-path="url(#...)">` 包装来实现。

## 数据流

```
SkCanvas::drawXXX() 调用
    |
    v
SkSVGDevice::drawXXX()
    |
    +---> syncClipStack() -- 同步裁剪栈到 SVG <clipPath>/<g>
    |
    +---> AutoElement 构造 -- 开始 SVG 元素
    |       |
    |       +---> addResources() -- 分析 SkPaint
    |       |       |
    |       |       +---> addShaderResources()
    |       |       |       +---> 颜色着色器 --> svg_color()
    |       |       |       +---> 渐变着色器 --> addGradientDef() --> <linearGradient>/<radialGradient>
    |       |       |       +---> 图像着色器 --> addImageShaderResources() --> <pattern>/<image>
    |       |       |
    |       |       +---> addColorFilterResources() --> <filter>
    |       |
    |       +---> addPaint() -- 设置 fill/stroke/opacity 等 SVG 属性
    |       +---> addAttribute("transform", ...) -- 变换矩阵
    |
    +---> 元素特定属性
    |       +---> addRectAttributes() (rect)
    |       +---> addPathAttributes() (path)  -- 使用 SkParsePath::ToSVGString()
    |       +---> addTextAttributes() (text)
    |
    v (AutoElement 析构)
SkXMLWriter::endElement() -- 关闭 SVG 标签
    |
    v
SkXMLStreamWriter --> SkWStream --> SVG 文件输出
```

### SVG 输出结构示例
```xml
<?xml version="1.0" encoding="utf-8" ?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="800" height="600">
  <defs>
    <linearGradient id="gradient_0" gradientUnits="userSpaceOnUse"
                    x1="0" y1="0" x2="100" y2="100">
      <stop offset="0" stop-color="red"/>
      <stop offset="1" stop-color="blue"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#cl_xxx)">
    <rect x="10" y="20" width="100" height="50"
          fill="url(#gradient_0)" transform="translate(5 10)"/>
    <path d="M 0 0 L 100 100 L 200 0 Z" fill="green" fill-opacity="0.5"/>
    <text font-size="16" font-family="Arial" x="10" y="30">Hello</text>
  </g>
</svg>
```

## 相关文档与参考

- **SVG 规范**: https://www.w3.org/TR/SVG2/ -- W3C SVG 标准
- **SVG 颜色名称**: https://www.w3.org/TR/css-color-3/#html4 -- CSS/SVG 命名颜色
- **SVG 变换**: https://www.w3.org/TR/SVG/coords.html#TransformMatrixDefined -- SVG 变换矩阵
- **Skia XML 模块**: `src/xml/` -- SVG 输出依赖的 XML 写入器
- **SkParsePath**: `include/utils/SkParsePath.h` -- SkPath 与 SVG 路径字符串相互转换
- **SVG 渲染模块**: `modules/svg/` -- SVG 的解析和渲染（与导出方向相反）
