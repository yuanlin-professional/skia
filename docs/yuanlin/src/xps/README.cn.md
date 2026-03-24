# src/xps - XPS 文档生成模块

## 概述

`src/xps` 目录是 Skia 图形库中负责生成 XPS（XML Paper Specification）文档的模块。XPS 是微软开发的一种固定版式文档格式，类似于 PDF，主要用于 Windows 平台的文档打印和共享。该模块仅在 Windows 平台（`SK_BUILD_FOR_WIN`）上编译和使用。

XPS 模块的核心是 `SkXPSDevice` 类，它继承自 `SkClipStackDevice`，将 Skia 的所有绘制操作（路径、矩形、文本、图像等）转换为 XPS 对象模型中的对应元素。这种设计遵循了 Skia 的"设备后端"（Device Backend）架构模式，使得上层的 `SkCanvas` API 可以无缝地将绘制指令输出为 XPS 格式。

该模块通过 Windows COM 接口与 XPS 对象模型（XPS Object Model, XpsOM）交互。它使用 `IXpsOMObjectFactory` 创建各种 XPS 元素，如页面、画布、路径、画刷和字体资源。Skia 的颜色、渐变、图像和字体等概念被精确映射到 XPS 规范定义的相应元素中。

XPS 文档的生成过程按照 "Portfolio -> Sheet -> Drawing Operations -> EndSheet -> EndPortfolio" 的生命周期进行管理。文档导出时还支持字体子集化（Font Subsetting），通过 `CreateFontPackage` API 仅将文档中实际使用的字形嵌入最终文件，减小输出文件的体积。

## 架构图

```
+------------------------------------------------------------------+
|                      SkCanvas API 层                              |
|    drawRect / drawPath / drawImage / drawText / ...              |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                      SkXPSDevice                                  |
|  (继承 SkClipStackDevice, 实现所有绘制虚函数)                     |
|  +-----------------------+  +---------------------------+        |
|  | 画刷系统              |  | 几何系统                   |        |
|  | createXpsBrush()      |  | addXpsPathGeometry()      |        |
|  | createXpsSolidColor   |  | createXpsRect()           |        |
|  |   Brush()             |  | createXpsQuad()           |        |
|  | createXpsLinear       |  | clipToPath()              |        |
|  |   Gradient()          |  |                           |        |
|  | createXpsRadial       |  +---------------------------+        |
|  |   Gradient()          |  +---------------------------+        |
|  | createXpsImageBrush() |  | 文字系统                   |        |
|  +-----------------------+  | CreateTypefaceUse()       |        |
|                             | AddGlyphs()               |        |
|                             | subset_typeface()          |        |
|                             +---------------------------+        |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|               Windows XPS Object Model (COM)                      |
|   IXpsOMObjectFactory / IXpsOMPackageWriter / IXpsOMPage         |
|   IXpsOMCanvas / IXpsOMPath / IXpsOMBrush / IXpsOMGlyphs        |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                     SkXPSDocument                                  |
|   (继承 SkDocument, 管理文档生命周期)                              |
|   onBeginPage / onEndPage / onClose                               |
+------------------------------------------------------------------+
                             |
                             v
+------------------------------------------------------------------+
|                    SkWStream (输出流)                              |
|                  .xps 文件 / 内存缓冲区                           |
+------------------------------------------------------------------+
```

## 目录结构

```
src/xps/
  BUILD.bazel          -- Bazel 构建配置
  SkXPSDevice.h        -- SkXPSDevice 类声明，XPS 绘制设备接口
  SkXPSDevice.cpp      -- SkXPSDevice 类实现（约 2000 行），核心绘制逻辑
  SkXPSDocument.cpp    -- SkXPSDocument 类实现，文档级生命周期管理

相关头文件:
  include/docs/SkXPSDocument.h  -- 公共 API，SkXPS::MakeDocument() 工厂函数
```

## 关键类与函数

### SkXPSDevice（XPS 绘制设备）
- **位置**: `src/xps/SkXPSDevice.h`, `src/xps/SkXPSDevice.cpp`
- **继承**: `SkClipStackDevice`
- **平台限制**: 仅 `SK_BUILD_FOR_WIN`
- **构造参数**: `SkISize`（画布尺寸）, `SkXPS::Options`（DPI、PNG 编码器等选项）
- **文档生命周期方法**:
  - `beginPortfolio(SkWStream*, IXpsOMObjectFactory*)` -- 开始文档
  - `beginSheet(unitsPerMeter, pixelsPerMeter, trimSize, ...)` -- 开始页面，支持设置介质盒、出血盒、内容盒、裁切盒
  - `endSheet()` -- 结束页面，执行坐标缩放（XPS 固定 96 DPI）
  - `endPortfolio()` -- 结束文档，执行字体子集化
- **绘制方法**: `drawPaint`, `drawRect`, `drawOval`, `drawRRect`, `drawPath`, `drawImageRect`, `drawPoints`, `drawVertices`, `drawMesh`, `drawDevice`
- **文字渲染**: `onDrawGlyphRunList` -- 处理字形序列绘制

### SkXPSDevice::TypefaceUse（字体使用记录）
- **位置**: `src/xps/SkXPSDevice.h`（私有内部类）
- **字段**: `typefaceId`, `ttcIndex`, `fontData`, `xpsFont`, `glyphsUsed`
- **职责**: 跟踪文档中使用的每种字体及其实际使用的字形，用于后续字体子集化

### SkXPSDocument（XPS 文档对象）
- **位置**: `src/xps/SkXPSDocument.cpp`
- **继承**: `SkDocument`
- **核心方法**:
  - `onBeginPage(width, height)` -- 创建新页面并返回 SkCanvas
  - `onEndPage()` -- 完成当前页面
  - `onClose()` -- 关闭文档，触发字体子集化和输出

### SkXPS::MakeDocument（工厂函数）
- **位置**: `include/docs/SkXPSDocument.h`
- **签名**: `sk_sp<SkDocument> MakeDocument(SkWStream*, IXpsOMObjectFactory*, Options)`
- **职责**: 创建 XPS 文档的入口点

### 关键内部函数
- `createXpsBrush()` -- 根据 SkPaint 的着色器类型创建对应的 XPS 画刷（纯色/线性渐变/径向渐变/图像）
- `createXpsImageBrush()` -- 处理图像平铺模式（Repeat/Mirror/Clamp），XPS 不原生支持 Clamp 模式，需要通过扩展边缘像素来模拟
- `addXpsPathGeometry()` -- 将 SkPath 转换为 XPS 几何图形，处理 Move/Line/Quad/Cubic/Conic 等路径命令
- `subset_typeface()` -- 使用 `CreateFontPackage` API 对嵌入字体进行子集化
- `shadePath()` -- 根据 SkPaint 样式设置路径的填充和描边画刷
- `clip()` -- 将当前裁剪栈应用到 XPS 视觉元素

## 依赖关系

### 外部依赖
- **Windows SDK**: `XpsObjectModel.h`, `ObjBase.h`, `T2EmbApi.h`, `FontSub.h`
- **COM 接口**: `IXpsOMObjectFactory`, `IXpsOMPackageWriter`, `IXpsOMPage` 等
- **字体子集化**: `CreateFontPackage` (T2Embed API)

### 内部依赖
- `src/core` -- `SkClipStackDevice`, `SkDraw`, `SkGeometry`, `SkPathPriv`, `SkStrikeCache` 等
- `src/shaders` -- `SkColorShader`, `SkImageShader`, `SkShaderBase`（着色器分析）
- `src/sfnt` -- `SkSFNTHeader`, `SkTTCFHeader`（字体格式处理）
- `src/image` -- `SkImage_Base`, `SkImage_Raster`
- `src/utils/win` -- `SkTScopedComPtr`, `SkHRESULT`, `SkIStream`, `SkAutoCoInitialize`
- `src/text` -- `GlyphRun`（文字渲染）
- `include/pathops` -- `SkPathOps`（路径简化，用于反向填充）

## 设计模式分析

### 设备后端模式（Device Backend）
`SkXPSDevice` 继承自 `SkClipStackDevice`，实现了 Skia 的绘制设备接口。上层 `SkCanvas` 调用绘制方法时，`SkXPSDevice` 将这些操作翻译为 XPS 对象模型的 COM 调用。

### 工厂模式（Factory）
`SkXPS::MakeDocument` 作为入口工厂函数，封装了 COM 对象的创建和初始化逻辑。`IXpsOMObjectFactory` 本身也是工厂模式的体现，用于创建各种 XPS 元素。

### RAII 与智能指针
使用 `SkTScopedComPtr` 管理 COM 对象的生命周期，确保 COM 引用计数的正确释放。所有 COM 接口指针均通过此智能指针包装。

### 延迟子集化（Lazy Subsetting）
字体子集化延迟到 `endPortfolio()` 时执行。在绘制过程中，`TypefaceUse::glyphsUsed` (SkBitSet) 持续记录使用到的字形索引，最终只将这些字形嵌入输出文件。

## 数据流

```
SkCanvas::drawXXX()
    |
    v
SkXPSDevice::drawXXX() -- 将 Skia 绘制命令转换为 XPS 元素
    |
    +---> createXpsBrush() -- 分析 SkPaint::getShader()
    |       |
    |       +---> 纯色 --> createXpsSolidColorBrush()
    |       +---> 线性渐变 --> createXpsLinearGradient()
    |       +---> 径向渐变 --> createXpsRadialGradient()
    |       +---> 图像 --> createXpsImageBrush()
    |
    +---> addXpsPathGeometry() -- 将 SkPath 转为 XPS 几何
    |       |
    |       +---> Line/Quad/Cubic/Conic 段类型转换
    |
    +---> shadePath() -- 设置填充和描边画刷
    +---> clip() -- 应用裁剪几何
    |
    v
IXpsOMVisualCollection::Append() -- 添加到 XPS 画布
    |
    v
endSheet() -- 缩放到物理单位(96 DPI)，创建页面
    |
    v
endPortfolio() -- 字体子集化 + IXpsOMPackageWriter::Close()
    |
    v
SkWStream -- 输出 .xps 文件
```

## 相关文档与参考

- **XPS 规范**: https://docs.microsoft.com/en-us/windows/win32/printdocs/documents -- 微软 XPS 文档规范
- **XPS Object Model API**: https://docs.microsoft.com/en-us/windows/win32/printdocs/xps-object-model -- Windows XPS OM API
- **Skia 文档导出**: `include/core/SkDocument.h` -- SkDocument 基类
- **SkClipStackDevice**: `src/core/SkClipStackDevice.h` -- 设备基类
- **COM 工具**: `src/utils/win/SkTScopedComPtr.h` -- COM 智能指针
- **字体子集化**: `T2EmbApi.h` -- Windows 字体嵌入和子集化 API
