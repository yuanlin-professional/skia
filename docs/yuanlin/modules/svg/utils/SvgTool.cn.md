# SvgTool

> 源文件: modules/svg/utils/SvgTool.cpp

## 概述

`SvgTool` 是一个命令行实用工具，用于将 SVG 文件渲染为 PNG 图像。该工具提供了一个简单的接口来测试和验证 Skia 的 SVG 渲染能力，支持自定义输出尺寸、字体管理、资源加载和文本整形。它集成了 Skia 的 SVG DOM 解析器、图像编码器和资源提供程序，是开发和调试 SVG 功能的实用工具。

## 架构位置

`SvgTool` 在 Skia 项目中的定位：

- **模块路径**: `modules/svg/utils/`
- **角色**: 独立的命令行工具，不是库代码
- **依赖关系**: 使用 SVG 模块、编码模块、资源模块和字体管理
- **用途**: 测试、验证、调试 SVG 渲染功能

该工具处于应用层，位于 Skia 库之上，为开发者提供快速测试 SVG 文件的能力。

## 主要类与结构体

该文件没有定义类，只包含一个 `main` 函数和相关的命令行标志。

### 命令行标志定义

```cpp
static DEFINE_string2(input , i, nullptr, "Input SVG file.");
static DEFINE_string2(output, o, nullptr, "Output PNG file.");

static DEFINE_int(width , 1024, "Output width.");
static DEFINE_int(height, 1024, "Output height.");
```

**标志说明**:
- **-i/--input**: 指定输入的 SVG 文件路径（必需）
- **-o/--output**: 指定输出的 PNG 文件路径（必需）
- **--width**: 输出图像的宽度，默认 1024 像素
- **--height**: 输出图像的高度，默认 1024 像素

## 公共 API 函数

### int main(int argc, char** argv)

程序入口点，执行 SVG 到 PNG 的转换流程。

**参数**:
- `argc`: 命令行参数数量
- `argv`: 命令行参数数组

**返回值**:
- `0`: 成功完成转换
- `1`: 发生错误（缺少参数、文件无效、解析失败等）

**执行流程**:
1. 解析命令行参数
2. 验证输入参数的有效性
3. 初始化字体管理器
4. 注册所有可用的图像编解码器
5. 创建资源提供程序（支持文件和 Data URI）
6. 解析 SVG 文件构建 DOM 树
7. 创建光栅化表面
8. 设置 SVG 容器尺寸并渲染
9. 将渲染结果编码为 PNG 并写入文件

## 内部实现细节

### 参数验证

```cpp
if (FLAGS_input.isEmpty() || FLAGS_output.isEmpty()) {
    std::cerr << "Missing required 'input' and 'output' args.\n";
    return 1;
}

if (FLAGS_width <= 0 || FLAGS_height <= 0) {
    std::cerr << "Invalid width/height.\n";
    return 1;
}
```

确保必需参数存在且尺寸值合法。

### 文件输入流

```cpp
SkFILEStream in(FLAGS_input[0]);
if (!in.isValid()) {
    std::cerr << "Could not open " << FLAGS_input[0] << "\n";
    return 1;
}
```

使用 `SkFILEStream` 打开 SVG 文件，支持流式读取。

### 字体管理器初始化

```cpp
#if defined(SK_BUILD_FOR_MAC)
    sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_CoreText(nullptr);
#else
    sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Empty();
#endif
```

**平台差异**:
- **macOS**: 使用 CoreText 字体管理器，可以访问系统字体
- **其他平台**: 使用空字体管理器，不加载任何字体

这种设计保证了工具在 macOS 上有更好的文本渲染效果，同时在其他平台保持基本功能。

### 编解码器注册

```cpp
CodecUtils::RegisterAllAvailable();
```

注册所有可用的图像编解码器，使 SVG 中的嵌入图像（如 PNG、JPEG）可以正确解码。

### 资源提供程序

```cpp
auto predecode = skresources::ImageDecodeStrategy::kPreDecode;
auto rp = skresources::DataURIResourceProviderProxy::Make(
        skresources::FileResourceProvider::Make(
            SkOSPath::Dirname(FLAGS_input[0]), predecode),
        predecode,
        fontMgr);
```

**资源提供程序链**:
1. **FileResourceProvider**: 从文件系统加载资源（相对于 SVG 文件所在目录）
2. **DataURIResourceProviderProxy**: 支持 Data URI（`data:image/png;base64,...`）
3. **预解码策略**: 立即解码图像，而非延迟解码

### SVG DOM 构建

```cpp
auto svg_dom = SkSVGDOM::Builder()
                       .setFontManager(fontMgr)
                       .setResourceProvider(std::move(rp))
                       .setTextShapingFactory(SkShapers::BestAvailable())
                       .make(in);

if (!svg_dom) {
    std::cerr << "Could not parse " << FLAGS_input[0] << "\n";
    return 1;
}
```

**构建器模式**:
- 设置字体管理器：用于文本渲染
- 设置资源提供程序：用于加载外部资源
- 设置文本整形工厂：选择最佳的文本布局引擎
- 从输入流构建 DOM 树

如果解析失败（无效的 SVG 语法），返回空指针并报错。

### 光栅化表面创建

```cpp
auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(FLAGS_width, FLAGS_height));
```

**表面配置**:
- **类型**: 光栅化（CPU）表面
- **颜色格式**: N32（平台原生 32 位格式）
- **Alpha 类型**: 预乘 alpha（Premultiplied）
- **尺寸**: 用户指定的宽度和高度

### SVG 渲染

```cpp
svg_dom->setContainerSize(SkSize::Make(FLAGS_width, FLAGS_height));
svg_dom->render(surface->getCanvas());
```

**两步渲染**:
1. **设置容器尺寸**: 告诉 SVG DOM 目标画布的大小，影响百分比单位和视口计算
2. **渲染到画布**: 将 SVG 内容绘制到表面的画布上

### PNG 编码和写入

```cpp
SkPixmap pixmap;
surface->peekPixels(&pixmap);

SkFILEWStream out(FLAGS_output[0]);
if (!out.isValid()) {
    std::cerr << "Could not open " << FLAGS_output[0] << " for writing.\n";
    return 1;
}

SkPngEncoder::Options png_options;  // 使用默认编码选项

if (!SkPngEncoder::Encode(&out, pixmap, png_options)) {
    std::cerr << "PNG encoding failed.\n";
    return 1;
}
```

**编码流程**:
1. 从表面获取像素数据（`SkPixmap`）
2. 打开输出文件流
3. 使用默认选项编码 PNG
4. 将编码后的数据写入文件

## 依赖关系

### Skia 核心模块

- **include/core/SkMatrix.h**: 矩阵变换（虽然未直接使用）
- **include/core/SkStream.h**: 文件流输入输出
- **include/core/SkSurface.h**: 绘图表面
- **include/encode/SkPngEncoder.h**: PNG 编码器

### SVG 模块

- **modules/svg/include/SkSVGDOM.h**: SVG 文档对象模型，核心解析和渲染类

### 资源模块

- **modules/skresources/include/SkResources.h**: 资源加载抽象，支持文件和 Data URI

### 文本整形模块

- **modules/skshaper/utils/FactoryHelpers.h**: 文本整形工厂，选择最佳的文本布局引擎

### 工具模块

- **tools/CodecUtils.h**: 编解码器注册工具
- **tools/flags/CommandLineFlags.h**: 命令行参数解析
- **tools/fonts/FontToolUtils.h**: 字体工具（虽然包含但未直接使用）
- **src/utils/SkOSPath.h**: 跨平台路径操作

### 平台特定依赖

- **include/ports/SkFontMgr_mac_ct.h** (macOS): CoreText 字体管理
- **include/ports/SkFontMgr_empty.h** (其他): 空字体管理

## 设计模式与设计决策

### 命令行工具模式

采用传统的 Unix 命令行工具设计：

- **单一职责**: 只做一件事（SVG 转 PNG）
- **管道友好**: 可以与其他工具组合使用
- **错误报告**: 使用标准错误流（stderr）报告错误
- **返回码**: 0 表示成功，1 表示失败

### 构建器模式

使用 `SkSVGDOM::Builder` 构建 SVG DOM：

```cpp
auto svg_dom = SkSVGDOM::Builder()
                       .setFontManager(fontMgr)
                       .setResourceProvider(std::move(rp))
                       .setTextShapingFactory(SkShapers::BestAvailable())
                       .make(in);
```

**优势**:
- **可读性**: 配置选项清晰
- **灵活性**: 可以选择性设置选项
- **类型安全**: 编译期检查参数类型

### 依赖注入

通过构建器注入依赖：

- **字体管理器**: 允许不同平台使用不同的字体后端
- **资源提供程序**: 支持自定义资源加载策略
- **文本整形工厂**: 选择最佳的文本布局引擎

这种设计使得 SVG 渲染具有高度可配置性。

### 平台抽象

通过条件编译处理平台差异：

```cpp
#if defined(SK_BUILD_FOR_MAC)
    // macOS 特定代码
#else
    // 通用代码
#endif
```

这种方式在保持代码简洁的同时支持平台特定优化。

## 性能考量

### 光栅化 vs GPU

该工具使用光栅化（CPU）渲染：

**优势**:
- **简单性**: 无需 GPU 上下文初始化
- **兼容性**: 在任何平台上都能工作
- **调试**: 更容易调试和验证结果

**劣势**:
- **性能**: 对于大尺寸图像，CPU 渲染可能较慢
- **并行性**: 无法利用 GPU 的并行计算能力

对于命令行工具，简单性和兼容性比性能更重要。

### 预解码策略

使用 `kPreDecode` 策略：

```cpp
auto predecode = skresources::ImageDecodeStrategy::kPreDecode;
```

**含义**: 立即解码所有图像资源，而非延迟解码。

**权衡**:
- **优势**: 避免渲染时的解码延迟，渲染速度更快
- **劣势**: 初始化时间更长，内存使用更多

对于一次性渲染，预解码是合理的选择。

### 内存使用

输出图像的内存占用：

```
内存 = width × height × 4 bytes (RGBA)
```

对于默认的 1024×1024，约需 4MB 内存。对于超大尺寸（如 4096×4096），需要 64MB，可能对某些系统造成压力。

## 相关文件

### SVG 核心

- **modules/svg/include/SkSVGDOM.h**: SVG 文档对象模型
- **modules/svg/src/SkSVGDOM.cpp**: DOM 实现，包括解析和渲染逻辑

### 资源管理

- **modules/skresources/include/SkResources.h**: 资源提供程序接口
- **modules/skresources/src/SkResources.cpp**: 文件和 Data URI 资源提供程序实现

### 文本整形

- **modules/skshaper/include/SkShaper.h**: 文本整形接口
- **modules/skshaper/utils/FactoryHelpers.h**: 整形工厂辅助函数

### 编码器

- **include/encode/SkPngEncoder.h**: PNG 编码器接口
- **src/encode/SkPngEncoder.cpp**: PNG 编码实现

### 工具基础设施

- **tools/flags/CommandLineFlags.h**: 命令行解析库
- **tools/CodecUtils.h**: 编解码器注册工具

### 使用示例

**基本用法**:
```bash
./svgtool -i input.svg -o output.png
```

**自定义尺寸**:
```bash
./svgtool -i logo.svg -o logo.png --width 512 --height 512
```

**处理复杂 SVG**:
```bash
./svgtool -i chart.svg -o chart.png --width 2048 --height 1536
```

该工具是 Skia SVG 模块的实用前端，为开发者提供了快速测试和验证 SVG 渲染能力的途径。
