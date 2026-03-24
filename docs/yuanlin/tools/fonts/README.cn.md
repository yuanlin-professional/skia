# Skia 字体测试工具

## 概述

`tools/fonts` 提供了 Skia 测试和工具所需的字体相关工具函数。该模块的核心目标是提供**跨平台一致**的字体资源和字体管理器，确保测试结果在不同操作系统上可重复。它包含可移植字体管理器、内嵌测试字体数据、随机化字体缩放器以及 Emoji 字体测试支持。

## 目录结构

```
tools/fonts/
├── BUILD.bazel                  # Bazel 构建配置
├── FontToolUtils.h              # 字体工具函数声明（核心公共接口）
├── FontToolUtils.cpp            # 字体工具函数实现
├── TestFontMgr.h                # 测试用字体管理器声明
├── TestFontMgr.cpp              # 测试用字体管理器实现
├── TestTypeface.h               # 测试用 Typeface 实现声明
├── TestTypeface.cpp             # 测试用 Typeface 实现
├── TestSVGTypeface.h            # SVG 字体 Typeface（彩色字体）
├── TestSVGTypeface.cpp          # SVG 字体 Typeface 实现
├── TestEmptyTypeface.h          # 空 Typeface（无字形数据）
├── RandomScalerContext.h        # 随机字体缩放器上下文
├── RandomScalerContext.cpp      # 随机字体缩放器实现
├── create_test_font.cpp         # 测试字体数据生成工具
├── create_test_font_color.cpp   # 彩色测试字体生成工具
├── generate_fir_coeff.py        # FIR 滤波器系数生成脚本
├── test_font_index.inc          # 内嵌字体索引数据
├── test_font_monospace.inc      # 等宽字体数据（约 418KB）
├── test_font_sans_serif.inc     # 无衬线字体数据（约 418KB）
└── test_font_serif.inc          # 衬线字体数据（约 441KB）
```

## 核心公共接口（FontToolUtils.h）

### 可移植字体函数

| 函数 | 说明 |
|------|------|
| `DefaultPortableFont()` | 返回跨平台一致的默认字体 |
| `DefaultPortableTypeface()` | 返回跨平台一致的默认 Typeface |
| `CreatePortableTypeface(name, style)` | 创建指定名称和样式的可移植 Typeface |
| `DefaultFont()` | 返回使用 DefaultTypeface() 的字体 |
| `DefaultTypeface()` | 返回测试字体管理器的默认 Typeface |
| `CreateTestTypeface(name, style)` | 通过 TestFontMgr 创建 Typeface |

### Emoji 字体支持

```cpp
enum class EmojiFontFormat {
    Cbdt,     // CBDT/CBLC 格式（Android 风格）
    Sbix,     // sbix 格式（Apple 风格）
    ColrV0,   // COLR v0 格式
    Test,     // 测试用格式
    Svg       // SVG 字体格式
};

EmojiTestSample EmojiSample();                    // 获取可用的彩色 Emoji
EmojiTestSample EmojiSample(EmojiFontFormat fmt);  // 获取指定格式的 Emoji
```

### 字体管理器

```cpp
sk_sp<SkFontMgr> TestFontMgr();         // 获取测试用字体管理器
void UsePortableFontMgr();               // 切换为可移植字体管理器
bool FontMgrIsGDI();                     // 检查是否使用 GDI 字体管理器
```

## 内嵌测试字体

`test_font_*.inc` 文件包含三种内嵌字体的二进制数据：

- **test_font_monospace.inc**: 等宽字体（类似 Courier），用于等宽文本测试
- **test_font_sans_serif.inc**: 无衬线字体（类似 Arial），最常用的测试字体
- **test_font_serif.inc**: 衬线字体（类似 Times），用于衬线字体测试

这些字体数据是通过 `create_test_font.cpp` 生成的 C++ include 文件，直接编译进二进制中，不依赖系统字体。

## RandomScalerContext

`SkRandomTypeface` 是一个调试专用的 Typeface 实现：

- 基于 Glyph ID 确定性地随机返回不同的字形格式
- 可返回 LCD、A8、BW 或 RGBA 格式的字形掩码
- 用于测试 Skia 文本渲染管线对混合格式字形的处理能力
- 通过 `fFakeIt` 标志控制是否伪造字形格式

## 构建

```bash
# Bazel 构建
bazel build //tools/fonts:fonts

# 生成 FIR 滤波器系数
python tools/fonts/generate_fir_coeff.py
```

## 与其他模块的关系

- **tests/**: 几乎所有需要字体的测试都依赖此模块
- **gm/**: GM 测试使用 DefaultPortableFont() 确保跨平台一致性
- **bench/**: 基准测试使用 TestFontMgr() 提供字体
- **tools/fiddle/**: Fiddle 使用 fontMgr 全局变量
- **src/core/SkScalerContext.h**: RandomScalerContext 的基类
