# FuzzCOLRv1.cpp - COLRv1 彩色字体渲染模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzCOLRv1.cpp`

## 概述

本文件实现了针对 COLRv1（Color Table Version 1）彩色字体格式渲染管线的模糊测试。COLRv1 是 OpenType 字体规范中的彩色字形格式，支持渐变、变换和合成等高级绘图操作。该测试将随机字节数据作为字体文件加载，然后尝试渲染其中的字形（glyph），用于发现字体解析和彩色字形渲染中的安全问题。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，覆盖了 Skia 字体渲染管线中的 COLRv1 子系统。COLRv1 字体在现代 emoji 和图标字体中广泛使用（如 Google 的 Noto Color Emoji），确保其渲染安全性对于浏览器和应用的安全至关重要。

## 主要类与结构体

- **`SkFontMgr`**: 字体管理器，负责从字节流创建字体面
- **`SkTypeface`**: 字体面，表示一个具体的字体
- **`SkFont`**: 字体配置（字体面 + 大小等参数）
- **`SkCanvas`**: 绘图画布
- **`SkSurface`**: 渲染目标
- **`SkPaint`**: 绘图属性

## 公共 API 函数

- **`FuzzCOLRv1(const uint8_t* data, size_t size)`**: 核心模糊测试函数
- **`LLVMFuzzerTestOneInput(const uint8_t* data, size_t size)`**: LibFuzzer 入口点，输入限制 80KB

## 内部实现细节

### 测试流程

1. 通过 `ToolUtils::TestFontMgr()` 获取非便携式字体管理器（需要支持从字节流创建字体）
2. 将输入字节作为字体流传入 `mgr->makeFromStream()` 创建字体面
3. 创建 128x128 的 Raster Surface
4. 使用 120pt 字体大小创建 `SkFont`
5. 遍历前 10 个字形（或全部字形，取较小者），逐个通过 `drawGlyphs()` 渲染

### 输入限制

80KB 的限制远大于其他模糊测试，因为 COLRv1 字体文件本身较大。这个值基于实际的语料库文件大小：小型测试字形文件约 8KB，完整的 Noto Emoji 字形覆盖约 80KB。

### 字形限制

最多渲染 10 个字形（`std::min(numGlyphs, 10)`），在覆盖渲染代码路径和控制测试时间之间取得平衡。

### 渲染配置

- 固定字体大小 120pt，在 128x128 画布上能够充分触发渲染路径
- 基线位置固定在 (10, 108)，选择在画布底部附近以显示字形

## 依赖关系

- **`include/core/SkCanvas.h`**: 画布 API
- **`include/core/SkFont.h` / `SkFontMgr.h` / `SkTypeface.h`**: 字体系统
- **`include/core/SkSurface.h`**: Surface API
- **`tools/fonts/FontToolUtils.h`**: 测试字体工具
- **`<algorithm>`**: `std::min`

## 设计模式与设计决策

- **真实字体管理器**: 使用 `TestFontMgr()` 而非便携式字体管理器，因为后者不支持从字节流创建字体
- **渲染验证**: 通过实际渲染字形来触发 COLRv1 的完整解析和绘制路径
- **80KB 输入上限**: 基于实际 COLRv1 字体文件大小设定，在真实性和效率之间平衡
- **逐字形渲染**: 遍历多个字形以提高代码覆盖率

## 性能考量

- 80KB 的输入上限是所有模糊测试中最大的之一，字体解析可能较慢
- 最多 10 个字形的限制控制了渲染时间
- 128x128 的小 Surface 尺寸减少了像素操作开销
- 120pt 的大字体在小画布上可能触发裁剪路径

### COLRv1 渲染管线

COLRv1 字体的渲染涉及以下步骤：
1. 字体文件解析和字体面创建
2. 字形 ID 到 COLRv1 记录的映射
3. COLRv1 绘图操作的解析（包括渐变、变换、合成等）
4. 通过 SkCanvas API 执行实际渲染
每个步骤都可能触发不同的代码路径和潜在的安全问题。

## 相关文件

- `src/core/SkTypeface.cpp` - 字体面实现
- `src/ports/SkFontMgr_*.cpp` - 各平台字体管理器实现
- `src/core/SkScalerContext.cpp` - 字形缩放上下文
- `tools/fonts/FontToolUtils.h` - 测试字体工具
