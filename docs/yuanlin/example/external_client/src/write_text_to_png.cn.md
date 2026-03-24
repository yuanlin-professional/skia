# write_text_to_png.cpp - 文本渲染到 PNG 示例

> 源文件: `example/external_client/src/write_text_to_png.cpp`

## 概述

`write_text_to_png.cpp` 是一个简洁的示例程序，演示了如何使用 Skia 的核心 API 将文本渲染到光栅化 Surface 并编码为 PNG 文件。该示例覆盖了 Skia 文本渲染的基本流程：字体管理器配置、字体匹配、文本绘制和图像编码输出。

这是 Skia 外部客户端集成最基础的文本渲染示例之一，适合作为入门参考。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── write_text_to_png.cpp   <-- 本文件：文本到 PNG 示例
│   ├── write_to_pdf.cpp        <-- 文本到 PDF 示例
│   ├── shape_text.cpp          <-- 段落排版示例
│   └── ...
```

## 主要类与结构体

本文件不定义新类，使用 Skia 的核心文本渲染 API。

### 使用的核心类型
- `SkFontMgr` - 字体管理器
- `SkTypeface` - 字体面
- `SkFont` - 字体对象（字体面 + 大小等参数）
- `SkSurface` / `SkCanvas` - 渲染表面和画布
- `SkPaint` - 画笔
- `SkPngEncoder` - PNG 编码器

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。用法：`write_text_to_png <name.png>`

执行流程：
1. 创建 100x50 像素的光栅 Surface
2. 配置平台字体管理器
3. 匹配 "Roboto" 字体
4. 创建 14px 大小的字体对象
5. 用黄色清除背景，用绿色绘制 "Hello world!" 文本
6. 编码为 PNG 输出

## 内部实现细节

### Surface 创建

```cpp
sk_sp<SkSurface> surface = SkSurfaces::Raster(
    SkImageInfo::MakeN32(100, 50, kOpaque_SkAlphaType));
```

使用不透明的原生 32 位色彩格式（N32 = 平台原生字节序的 RGBA/BGRA），避免 alpha 混合开销。

### 字体匹配

```cpp
sk_sp<SkTypeface> face = mgr->matchFamilyStyle("Roboto", SkFontStyle());
```

通过字体管理器按家族名和样式匹配字体。`SkFontStyle()` 使用默认的正常（Normal）样式。如果系统未安装 "Roboto" 字体，此调用可能返回 `nullptr`。

### 文本绘制

```cpp
SkFont font(face, 14);
SkPaint paint;
paint.setColor(SK_ColorGREEN);
canvas->clear(SK_ColorYELLOW);
canvas->drawString("Hello world!", 10, 25, font, paint);
```

`drawString` 是简便方法，内部完成文本到字形的映射和定位。坐标 (10, 25) 指定文本基线的起始位置。

### 像素回读和编码

```cpp
SkPixmap pixmap;
if (surface->peekPixels(&pixmap)) {
    SkPngEncoder::Encode(&output, pixmap, {});
}
```

`peekPixels` 直接访问 Surface 的像素数据（零复制），然后使用默认的 PNG 编码参数进行编码。

## 依赖关系

- **Skia 核心**：`SkCanvas`, `SkSurface`, `SkFont`, `SkTypeface`, `SkFontMgr`, `SkPaint`, `SkPixmap`, `SkStream`
- **编码器**：`SkPngEncoder`
- **平台字体**（条件编译）：`SkFontMgr_fontconfig.h` + `SkFontScanner_FreeType.h`（Linux）, `SkFontMgr_mac_ct.h`（macOS）

## 设计模式与设计决策

1. **最小化示例**：代码尽可能简洁，仅展示文本渲染的核心步骤，适合初学者理解 Skia 的基本使用方式。

2. **条件编译的字体后端**：使用编译时宏选择字体管理器，保持跨平台兼容性。

3. **不透明 Surface**：选择 `kOpaque_SkAlphaType` 避免不必要的 alpha 混合，这是绘制不需要透明度的图像时的最佳实践。

4. **peekPixels 零复制**：直接访问 Surface 的像素缓冲区，避免额外的内存分配和复制。

## 性能考量

- **CPU 光栅化**：整个渲染在 CPU 上完成，对于 100x50 的小图像几乎即时。
- **peekPixels 零复制**：避免了 `readPixels` 可能带来的额外内存分配。
- **单次字体查找**：`matchFamilyStyle` 是主要的 I/O 操作（可能涉及字体文件扫描），后续的 `drawString` 使用缓存的字形信息。

## 相关文件

- `include/core/SkFont.h` - 字体类定义
- `include/core/SkFontMgr.h` - 字体管理器接口
- `include/core/SkCanvas.h` - Canvas 绘图 API
- `include/encode/SkPngEncoder.h` - PNG 编码器
- `example/external_client/src/write_to_pdf.cpp` - 类似的 PDF 输出示例
- `example/external_client/src/shape_text.cpp` - 更高级的文本排版示例
