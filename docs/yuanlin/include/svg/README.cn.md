# svg - SVG 输出 API

## 概述

`include/svg` 目录定义了 Skia 的 SVG（Scalable Vector Graphics，可缩放矢量图形）
输出 API。该目录仅包含一个头文件 `SkSVGCanvas.h`，提供了将 Skia 绘制操作转换为
SVG 格式输出的能力。

`SkSVGCanvas` 通过创建一个特殊的 `SkCanvas` 实例来工作。当应用程序在这个画布上
进行绘制操作（如绘制路径、矩形、文本、图像等）时，所有的绘制命令会被转换为对应的
SVG 元素并写入到提供的输出流中。这种设计使得任何已经使用 Skia 进行绘制的代码，
只需简单地替换画布对象，就可以生成 SVG 输出。

SVG 画布支持多种输出选项：文本可以转换为 `<path>` 元素以确保在没有字体的环境下
也能正确显示；XML 输出可以选择是否包含美化格式（换行和缩进）；路径编码可以选择
使用绝对坐标或相对坐标。画布还支持嵌入位图图像，需要提供 PNG 编码器回调函数。

需要注意的是，SVG 输出可能会缓冲部分绘制调用，因此在删除画布实例之前，输出流
中的内容可能不是完整的。`bounds` 参数定义了 SVG 根元素的 `viewBox` 属性，
决定了输出的初始视口大小。

此目录仅提供 SVG 输出功能。SVG 解析和渲染功能位于 `modules/svg/` 模块中。

## 架构图

```
+------------------------------------------------------------------+
|                        应用层                                      |
|  使用 SkCanvas API 进行绘制                                        |
+------------------------------------------------------------------+
         |
         v
+-------------------+
| SkSVGCanvas::Make |
|  创建 SVG 画布     |
+-------------------+
| 参数:              |
|  bounds - viewBox  |
|  stream - 输出流   |
|  Options:          |
|    flags           |
|    pngEncoder      |
+-------------------+
         |
         v
+-------------------+     +------------------+
|  SkCanvas (SVG)   |     |   SkWStream      |
|  绘制操作 -->      |---->|  SVG XML 输出     |
|  SVG 元素          |     +------------------+
+-------------------+          |
| 绘制操作映射:       |         v
|  drawRect  -> <rect>|    <?xml ...?>
|  drawPath  -> <path>|    <svg viewBox="...">
|  drawText  -> <text>|      <rect .../>
|  drawImage -> <image|      <path d="..."/>
|  drawCircle-> <circle     <text>...</text>
+-------------------+      </svg>
```

## 目录结构

```
include/svg/
  BUILD.bazel       # Bazel 构建配置
  SkSVGCanvas.h     # SVG 画布工厂，将 SkCanvas 绘制转换为 SVG 输出
```

## 关键类与函数

### SkSVGCanvas - SVG 画布工厂

**创建方法：**

```cpp
static std::unique_ptr<SkCanvas> Make(const SkRect& bounds,
                                       SkWStream* stream,
                                       Options opts);
```

创建一个将绘制操作转换为 SVG 的画布。`bounds` 定义 SVG 的 `viewBox` 属性，
`stream` 接收 SVG XML 输出（不转移所有权，必须在画布生命周期内保持有效）。

**Flags - 输出选项标志：**

```cpp
enum Flags {
    kConvertTextToPaths_Flag   = 0x01,  // 将文本转换为 <path> 元素
    kNoPrettyXML_Flag          = 0x02,  // 不输出换行和缩进
    kRelativePathEncoding_Flag = 0x04,  // 路径使用相对坐标命令
};
```

- `kConvertTextToPaths_Flag` - 将文本渲染为路径而非 `<text>` 元素，确保在
  任何环境下都能正确显示
- `kNoPrettyXML_Flag` - 压缩输出格式，减小文件体积
- `kRelativePathEncoding_Flag` - 使用相对路径命令（如 `m`、`l` 而非 `M`、`L`），
  可能产生更紧凑的路径数据

**Options - 配置结构体：**

```cpp
struct Options {
    Flags flags = static_cast<Flags>(0x00);
    EncodePngCallback pngEncoder = nullptr;
};
```

`pngEncoder` 回调用于将位图图像嵌入到 SVG 中。当绘制操作涉及位图时，SVG 画布
需要将位图编码为 PNG 格式并以 Base64 的形式嵌入到 `<image>` 元素中。

**EncodePngCallback 类型：**

```cpp
using EncodePngCallback = bool (*)(SkWStream* dst, const SkPixmap& src);
```

### 使用示例

```cpp
// 创建输出流
SkFILEWStream stream("output.svg");

// 配置选项
SkSVGCanvas::Options opts;
opts.flags = SkSVGCanvas::kConvertTextToPaths_Flag;
opts.pngEncoder = myPngEncodeFunction;

// 创建 SVG 画布
SkRect bounds = SkRect::MakeWH(800, 600);
auto canvas = SkSVGCanvas::Make(bounds, &stream, opts);

// 使用标准 SkCanvas API 进行绘制
SkPaint paint;
paint.setColor(SK_ColorRED);
canvas->drawRect(SkRect::MakeXYWH(10, 10, 100, 100), paint);

// 删除画布以完成 SVG 输出
canvas.reset();
```

## 依赖关系

- **内部依赖**：`include/core`（SkCanvas、SkWStream、SkRect）
- **可选依赖**：`include/encode`（PNG 编码器，用于嵌入位图图像）
- **相关模块**：`modules/svg/`（SVG 解析和渲染，与此目录互补）

## 相关文档与参考

- SVG 规范：https://www.w3.org/TR/SVG2/
- SVG 路径数据规范：https://www.w3.org/TR/SVG/paths.html
- SVG 模块（解析和渲染）：`modules/svg/`
- 源码实现位于 `src/svg/` 目录
