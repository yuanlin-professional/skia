# SkSVGDevice - SVG 渲染设备

> 源文件：[src/svg/SkSVGDevice.h](../../../../src/svg/SkSVGDevice.h)、[src/svg/SkSVGDevice.cpp](../../../../src/svg/SkSVGDevice.cpp)

## 概述

`SkSVGDevice` 是 Skia 图形库中用于将绘制操作序列化为 SVG（可缩放矢量图形）格式的渲染设备。它继承自 `SkClipStackDevice`，通过拦截各种 Canvas 绘制调用（如绘制矩形、椭圆、路径、图像、文本等），将其转换为对应的 SVG XML 元素输出到 `SkXMLWriter`。该类实现了 Skia 2D 绘图 API 到 SVG 标准的完整映射，支持渐变、图案填充、颜色滤镜、裁剪路径、变换矩阵等高级 SVG 特性。

## 架构位置

```
SkCanvas
  └── SkDevice (抽象基类)
        └── SkClipStackDevice (提供裁剪栈管理)
              └── SkSVGDevice (SVG 输出设备)
```

`SkSVGDevice` 位于 Skia 设备层的最末端。用户通过 `SkSVGCanvas` 公共 API 创建一个绑定了 SVG 设备的 Canvas。所有通过该 Canvas 执行的绘制操作都会被 `SkSVGDevice` 捕获并转化为 SVG 标记语言输出。

## 主要类与结构体

### `SkSVGDevice`
核心设备类，继承自 `SkClipStackDevice`。管理 SVG 文档的生命周期，从构造时写入 `<svg>` 根元素到析构时自动关闭。

**关键成员变量：**
- `fWriter`：`std::unique_ptr<SkXMLWriter>`，负责实际的 XML 输出。
- `fResourceBucket`：`std::unique_ptr<ResourceBucket>`，管理资源（渐变、路径、图像、图案）的唯一 ID 分配。
- `fOpts`：`SkSVGCanvas::Options`，控制输出选项（如路径编码方式、文本转路径标志等）。
- `fRootElement`：根 `<svg>` 元素的 RAII 管理器。
- `fClipStack`：`TArray<ClipRec>`，维护裁剪状态的栈。

### `SkSVGDevice::AutoElement`（内部类）
RAII 风格的 XML 元素管理器。构造时调用 `fWriter->startElement()`，析构时调用 `fWriter->endElement()`，确保 XML 元素正确嵌套和关闭。该类还负责处理绘制属性（填充、描边、变换等）到 SVG 属性的转换，以及管理着色器资源（渐变定义、图案定义等）。

### `SkSVGDevice::ResourceBucket`（内部类）
资源 ID 生成器，为渐变（`gradient_N`）、路径（`path_N`）、图像（`img_N`）、图案（`pattern_N`）和颜色滤镜（`cfilter_N`）生成递增的唯一标识符。

### `SkSVGDevice::MxCp`（内部结构体）
矩阵与裁剪栈的组合结构，用于在绘制方法中传递当前的变换矩阵和裁剪状态。

### `SkSVGDevice::ClipRec`（内部结构体）
裁剪栈记录，保存裁剪路径元素和对应的 GenID，用于裁剪栈同步时的增量更新。

### `SVGTextBuilder`（匿名命名空间）
文本绘制辅助类。将字形运行（GlyphRun）转换为 SVG `<text>` 元素所需的文本内容和位置属性（`x`、`y` 坐标列表）。处理空白合并、XML 特殊字符转义，并优化 Y 坐标为常量时的输出。

### `Resources`（匿名命名空间）
保存当前绘制操作的 SVG 资源引用，包括画笔服务器引用（颜色或 `url(#id)` 引用）和颜色滤镜引用。

## 公共 API 函数

### `Make(const SkISize& size, std::unique_ptr<SkXMLWriter>, SkSVGCanvas::Options)`
静态工厂方法。创建并返回一个 `SkSVGDevice` 实例。如果传入的 `writer` 为空，则返回 `nullptr`。

### `drawPaint(const SkPaint& paint)`
用指定画笔填充整个设备区域。实现方式为绘制一个覆盖整个视口的 `<rect>` 元素。

### `drawRect(const SkRect& r, const SkPaint& paint)`
绘制矩形。输出 SVG `<rect>` 元素。如果画笔包含路径效果，则退化为 `drawPath`。如果画笔着色器需要重复图案，则在外层包裹 `<svg>` 元素以重置视口。

### `drawOval(const SkRect& oval, const SkPaint& paint)`
绘制椭圆。输出 SVG `<ellipse>` 元素，设置 `cx`、`cy`、`rx`、`ry` 属性。

### `drawRRect(const SkRRect& rr, const SkPaint& paint)`
绘制圆角矩形。输出 SVG `<path>` 元素（因为 SVG 的 `<rect>` 不支持每个角不同的圆角半径）。

### `drawPath(const SkPath& path, const SkPaint& paint)`
绘制路径。输出 SVG `<path>` 元素。如果画笔包含路径效果，先应用效果再输出。支持 `evenodd` 填充规则。不支持反向填充类型。

### `drawPoints(SkCanvas::PointMode, SkSpan<const SkPoint>, const SkPaint&)`
绘制点、线段或多边形。将不同的点模式转换为相应的路径操作后调用 `drawPath`。

### `drawImageRect(const SkImage*, const SkRect*, const SkRect&, const SkSamplingOptions&, const SkPaint&, SkCanvas::SrcRectConstraint)`
绘制图像。将图像编码为 Base64 格式的 data URI，嵌入到 SVG `<image>` 元素中。支持源矩形裁剪。

### `drawAnnotation(const SkRect& rect, const char key[], SkData* value)`
绘制注释。将 URL 注释转换为 SVG `<a>` 超链接元素。

### `drawVertices` / `drawMesh`
顶点和网格绘制。目前未实现（标记为 `// todo`）。

## 内部实现细节

### SVG 颜色表示
`svg_color()` 函数将 `SkColor` 转换为 SVG 颜色字符串。优先使用 CSS 命名颜色（如 `black`、`red`、`blue` 等 16 种 HTML4 标准颜色），否则使用十六进制表示。当 RGB 各通道的高低 4 位相同时，使用缩写形式（如 `#ABC`）以减小输出体积。

### 变换矩阵转换
`svg_transform()` 函数将 `SkMatrix` 转换为 SVG `transform` 属性。针对纯平移和纯缩放使用简化形式（`translate()`、`scale()`），其他情况使用通用 `matrix()` 形式。不支持透视矩阵。

### 着色器资源处理
`AutoElement` 类的 `addShaderResources` 方法处理三种着色器类型：
1. **颜色着色器**：直接使用颜色值。
2. **渐变着色器**：生成 `<linearGradient>` 或 `<radialGradient>` 定义，支持线性、径向和锥形（双焦点径向）渐变。
3. **图像着色器**：生成 `<pattern>` 定义，将图像作为 Base64 data URI 嵌入，支持平铺模式。

### 裁剪栈同步
`syncClipStack()` 方法通过比较内部裁剪栈与当前设备裁剪栈的 GenID 实现增量更新。它保留两个栈的公共底部，丢弃过期的顶部元素，然后重建新增的裁剪元素。每个裁剪元素生成一个 `<clipPath>` 定义，并将后续绘制包裹在设置了 `clip-path` 属性的 `<g>` 元素中。

### 图像编码
图像通过 `AsDataUri()` 函数转换为 data URI。支持 JPEG 和 PNG 格式的直通（如果图像已编码），否则使用提供的 PNG 编码器重新编码。编码后的数据通过 Base64 编码嵌入 SVG。

### 文本处理
文本绘制有两种模式：
- **路径模式**：当设置了 `kConvertTextToPaths_Flag` 选项或画笔包含路径效果时，将字形转换为路径轮廓后绘制。
- **文本模式**：生成 SVG `<text>` 元素，包含字体大小、字体族、字体样式、字体粗细、字体拉伸等属性，以及每个字符的精确位置。

### 画笔属性转换
`addPaint()` 方法将 `SkPaint` 的样式转换为 SVG 属性：
- 填充样式设置 `fill`、`fill-opacity`。
- 描边样式设置 `stroke`、`stroke-width`、`stroke-linecap`、`stroke-linejoin`、`stroke-miterlimit`、`stroke-opacity`。
- 发丝描边（宽度为 0）设置 `vector-effect: non-scaling-stroke`。

## 依赖关系

- **SkClipStackDevice**：基类，提供裁剪栈管理。
- **SkXMLWriter**：底层 XML 序列化。
- **SkSVGCanvas**：公共 API 入口，提供 `Options` 和 `EncodePngCallback`。
- **SkParsePath**：路径到 SVG `d` 属性字符串的转换。
- **SkClipStack**：裁剪操作管理。
- **SkShaderBase**：着色器类型检测和渐变信息提取。
- **SkBase64**：Base64 编码，用于图像嵌入。
- **SkAnnotationKeys**：注释键定义（URL、命名目标）。
- **SkFontPriv**：字形到 Unicode 字符的转换。
- **sktext::GlyphRunList**：文本字形运行列表。

## 设计模式与设计决策

### RAII 模式
`AutoElement` 类使用 RAII 模式管理 XML 元素的开始和结束。构造函数调用 `startElement`，析构函数调用 `endElement`，保证元素在任何退出路径（包括异常）下都能正确关闭。

### 工厂模式
`Make()` 静态方法作为唯一的公共构造入口，私有化了构造函数，确保对象创建的一致性和参数验证。

### 资源桶（Resource Bucket）设计
使用简单的计数器为每种资源类型生成唯一 ID。这种设计简单高效，但当前不支持资源去重——注释中提到未来将进化为跟踪和去重资源。

### 增量裁剪栈同步
通过 GenID 比较实现增量同步，避免每次绘制操作都完全重建裁剪栈。这在裁剪栈变化不频繁的常见场景中效率更高。

### 路径效果前置处理
对于包含路径效果的画笔，所有几何图元（矩形、椭圆等）都退化为路径绘制，先应用路径效果再生成 SVG 输出。这保证了路径效果在 SVG 中的正确表现。

## 性能考量

- **图像编码开销**：图像嵌入需要 PNG 编码和 Base64 转换，这是计算密集型操作。对于大量图像的场景可能成为瓶颈。
- **SVG 输出体积**：Base64 编码的图像会显著增大 SVG 文件大小（约增加 33%）。
- **颜色名称优化**：使用 CSS 命名颜色和简写十六进制减少输出字符数。
- **Y 坐标优化**：`SVGTextBuilder` 检测所有字符是否共享相同 Y 坐标，如果是则仅输出一个 Y 值而非完整列表。
- **无资源去重**：相同的渐变或图案会被重复定义，可能导致输出冗余。

## 相关文件

- `include/svg/SkSVGCanvas.h`：公共 API 头文件，定义 `SkSVGCanvas::Make()` 和选项。
- `src/xml/SkXMLWriter.h`：XML 写入器抽象接口。
- `src/core/SkClipStackDevice.h`：基类定义。
- `src/core/SkClipStack.h`：裁剪栈实现。
- `include/utils/SkParsePath.h`：路径到 SVG 字符串的转换工具。
- `src/shaders/SkShaderBase.h`：着色器基类，提供渐变类型查询。
- `src/base/SkBase64.h`：Base64 编解码工具。
- `src/text/GlyphRun.h`：字形运行数据结构。
