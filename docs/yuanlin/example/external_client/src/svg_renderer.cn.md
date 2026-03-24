# svg_renderer.cpp - SVG 渲染示例

> 源文件: `example/external_client/src/svg_renderer.cpp`

## 概述

`svg_renderer.cpp` 是一个示例程序，演示了如何使用 Skia 的 SVG 模块将 SVG 内容解析并渲染为 PNG 图像。该示例展示了 SkSVGDOM 的使用方法，包括字体管理器的配置、文本排版引擎（text shaping）的集成，以及最终的光栅化输出。

示例中使用了一个包含文本的内联 SVG，以验证字体排版（如字距调整/kerning）能够正确工作。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── svg_renderer.cpp        <-- 本文件：SVG 渲染示例
│   └── ...
├── modules/svg/                <-- SVG 解析和渲染模块
├── modules/skshaper/           <-- 文本排版模块
└── include/ports/              <-- 平台字体管理器
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的 SVG 和字体相关 API。

### 使用的核心类型
- `SkSVGDOM` - SVG 文档对象模型，解析和渲染 SVG
- `SkFontMgr` - 字体管理器抽象接口
- `SkSurface` - 渲染表面

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。用法：`svg_renderer <name.png>`

执行流程：
1. 根据平台创建字体管理器（FontConfig/FreeType 或 CoreText）
2. 将内联 SVG 字符串解析为 `SkSVGDOM`
3. 创建光栅化 Surface
4. 设置容器尺寸并渲染 SVG
5. 编码为 PNG 输出

## 内部实现细节

### 平台字体管理器选择

```cpp
#if defined(SK_FONTMGR_FONTCONFIG_AVAILABLE) && defined(SK_TYPEFACE_FACTORY_FREETYPE)
    fontMgr = SkFontMgr_New_FontConfig(nullptr, SkFontScanner_Make_FreeType());
#elif defined(SK_FONTMGR_CORETEXT_AVAILABLE)
    fontMgr = SkFontMgr_New_CoreText(nullptr);
#endif
```

通过条件编译选择平台适当的字体管理器：
- Linux：FontConfig + FreeType
- macOS：Core Text

### SVG 构建器模式

```cpp
auto svg_dom = SkSVGDOM::Builder()
                       .setFontManager(fontMgr)
                       .setTextShapingFactory(SkShapers::BestAvailable())
                       .make(svgStream);
```

使用 Builder 模式配置 SVG DOM：
- 设置字体管理器用于文本渲染
- 设置文本排版工厂（`BestAvailable` 使用系统最佳可用的排版引擎，通常是 HarfBuzz）
- 从内存流中解析 SVG

### 测试 SVG 内容

```cpp
const char* svg = "<svg viewBox=\"0 0 150 40\" xmlns=\"http://www.w3.org/2000/svg\">"
  "<style>text { font: 13px sans-serif; }</style>"
  "<text x=\"10\" y=\"30\">VAVAVAVA</text>"
"</svg>";
```

使用 "VAVAVAVA" 文本测试字距调整（kerning）：V 和 A 字符在正确排版时应略微重叠。

### 渲染流程

```cpp
auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(kWidth, kHeight));
svg_dom->setContainerSize(SkSize::Make(kWidth, kHeight));
svg_dom->render(surface->getCanvas());
```

SVG 容器尺寸决定了 viewBox 的映射关系。渲染直接绘制到光栅 Surface 的 Canvas 上。

## 依赖关系

- **Skia 核心**：`SkCanvas`, `SkSurface`, `SkStream`, `SkFontMgr`, `SkPixmap`
- **SVG 模块**：`modules/svg/include/SkSVGDOM.h`
- **文本排版**：`modules/skshaper/utils/FactoryHelpers.h`
- **编码器**：`SkPngEncoder`
- **平台字体**（条件编译）：`SkFontMgr_fontconfig.h`, `SkFontScanner_FreeType.h`, `SkFontMgr_mac_ct.h`

## 设计模式与设计决策

1. **Builder 模式**：`SkSVGDOM::Builder` 提供了流式配置接口，清晰表达了 SVG DOM 的构建选项。

2. **条件编译的平台适配**：字体管理器通过编译时宏选择，无运行时分支开销。

3. **内联 SVG 测试**：将 SVG 内容硬编码在源文件中，使示例自包含，无需外部文件依赖。

4. **文本排版验证**：选择 "VAVAVAVA" 作为测试字符串，因为这些字符的字距调整效果最为明显。

## 性能考量

- **光栅化渲染**：使用 CPU 光栅化，适合小尺寸图像。对于大尺寸或复杂 SVG，GPU 渲染会更高效。
- **字体加载**：字体管理器初始化会扫描系统字体目录，是一次性的开销。
- **PNG 编码**：CPU 编码，对于 450x120 的小图像几乎无感知延迟。

## 相关文件

- `modules/svg/include/SkSVGDOM.h` - SVG DOM API
- `modules/skshaper/include/SkShaper.h` - 文本排版器
- `include/ports/SkFontMgr_fontconfig.h` - FontConfig 字体管理器
- `include/ports/SkFontMgr_mac_ct.h` - CoreText 字体管理器
- `include/encode/SkPngEncoder.h` - PNG 编码器
