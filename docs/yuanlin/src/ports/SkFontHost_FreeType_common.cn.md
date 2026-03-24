# SkFontHost_FreeType_common

> 源文件
> - src/ports/SkFontHost_FreeType_common.h
> - src/ports/SkFontHost_FreeType_common.cpp

## 概述

`SkFontHost_FreeType_common` 是 Skia 字体渲染系统中使用 FreeType 库的核心组件，提供了 FreeType 字体渲染的通用功能实现。该模块负责将 FreeType 的字形数据转换为 Skia 可以使用的格式，支持多种字体渲染技术，包括：

- **位图字形渲染**：单色、灰度、LCD 子像素渲染
- **矢量字形生成**：将 FreeType 轮廓转换为 SkPath
- **彩色字体支持**：COLRv0、COLRv1、SVG 字形
- **高级排版特性**：可变字体、字形变换、子像素定位

该模块是 Android 和其他使用 FreeType 的平台上字体渲染的基础，提供了高性能、高质量的文本渲染能力。

## 架构位置

`SkFontHost_FreeType_common` 位于 Skia 的平台适配层，作为 FreeType 和 Skia 之间的桥梁：

```
SkCanvas (绘图接口)
    ↓
SkScalerContext (字形缩放上下文)
    ↓
SkScalerContextFTUtils (本模块)
    ↓
FreeType Library (FT_Face, FT_Glyph)
    ↓
字体文件 (TrueType, OpenType, WOFF, etc.)
```

该模块被多个平台的字体实现所使用，包括：
- Android: `SkFontHost_android.cpp`
- Linux: `SkFontHost_linux.cpp`
- macOS/iOS: 部分 FreeType 后备路径
- Windows: 部分场景下的 FreeType 渲染

## 主要类与结构体

### SkScalerContextFTUtils
FreeType 工具类，封装了所有 FreeType 字形渲染的核心功能。

**主要成员：**
- `fForegroundColor`: 前景色（用于彩色字体）
- `fFlags`: 缩放上下文标志（子像素定位、线性度量等）

**核心方法：**
- `init()`: 初始化工具类
- `isSubpixel()`: 是否启用子像素定位
- `isLinearMetrics()`: 是否使用线性度量
- `drawCOLRv0Glyph()`: 绘制 COLRv0 彩色字形
- `drawCOLRv1Glyph()`: 绘制 COLRv1 彩色字形
- `drawSVGGlyph()`: 绘制 SVG 字形
- `generateGlyphImage()`: 生成位图字形图像
- `generateGlyphPath()`: 生成矢量字形路径
- `computeColrV1GlyphBoundingBox()`: 计算 COLRv1 字形边界框
- `generateFacePath()`: 生成 FreeType face 的路径

### LoadGlyphFlags
类型别名 `uint32_t`，用于传递 FreeType 加载字形标志（如 `FT_LOAD_NO_HINTING`）。

### 辅助结构体

#### SkUniqueFTSize
FreeType 大小对象的智能指针类型，自动调用 `FT_Done_Size` 清理。

#### OpaquePaintHasher
COLRv1 不透明绘制对象的哈希函数对象，用于去重和缓存。

## 公共 API 函数

### SkScalerContextFTUtils::init()
```cpp
void init(SkColor fgColor, SkScalerContext::Flags flags);
```
初始化 FreeType 工具类，设置前景色和标志。

### SkScalerContextFTUtils::drawCOLRv0Glyph()
```cpp
bool drawCOLRv0Glyph(FT_Face face, const SkGlyph& glyph, LoadGlyphFlags loadFlags,
                     SkSpan<SkColor> palette, SkCanvas* canvas) const;
```
绘制 COLRv0（OpenType 彩色字体版本 0）字形。COLRv0 使用层叠的单色字形和调色板实现彩色效果。

**参数：**
- `face`: FreeType face 对象
- `glyph`: Skia 字形对象
- `loadFlags`: FreeType 加载标志
- `palette`: 颜色调色板
- `canvas`: 目标画布

**返回值：** 成功返回 true，失败或不支持返回 false

### SkScalerContextFTUtils::drawCOLRv1Glyph()
```cpp
bool drawCOLRv1Glyph(FT_Face face, const SkGlyph& glyph, LoadGlyphFlags loadFlags,
                     SkSpan<SkColor> palette, SkCanvas* canvas) const;
```
绘制 COLRv1（OpenType 彩色字体版本 1）字形。COLRv1 支持渐变、混合模式和高级图形效果。

### SkScalerContextFTUtils::drawSVGGlyph()
```cpp
bool drawSVGGlyph(FT_Face face, const SkGlyph& glyph, LoadGlyphFlags loadFlags,
                  SkSpan<SkColor> palette, SkCanvas* canvas) const;
```
绘制 SVG 格式的字形（如 Twitter Emoji 字体）。需要 OpenType SVG 解码器支持。

### SkScalerContextFTUtils::generateGlyphImage()
```cpp
void generateGlyphImage(FT_Face face, const SkGlyph& glyph, void* imageBuffer,
                        const SkMatrix& bitmapTransform,
                        const SkMaskGamma::PreBlend& preBlend) const;
```
生成字形的位图图像，支持多种像素格式：
- 单色位图 (BW)
- 灰度位图 (A8)
- LCD 子像素渲染 (LCD16)
- 彩色位图 (ARGB32)

### SkScalerContextFTUtils::generateGlyphPath()
```cpp
bool generateGlyphPath(FT_Face face, SkPathBuilder* pathBuilder) const;
```
生成字形的矢量路径，将 FreeType 轮廓转换为 SkPath。

### SkScalerContextFTUtils::computeColrV1GlyphBoundingBox()
```cpp
static bool computeColrV1GlyphBoundingBox(FT_Face face, SkGlyphID glyphID, SkRect* bounds);
```
计算 COLRv1 字形的边界框。注意：此方法可能改变 FT_Face 的配置状态。

### SK_TRACEFTR 宏
```cpp
#define SK_TRACEFTR(ERR, MSG, ...)
```
调试模式下追踪 FreeType 错误的宏，输出错误码和错误消息。

### SkTraceFtrGetError()
```cpp
const char* SkTraceFtrGetError(int errorCode);
```
将 FreeType 错误码转换为可读的错误字符串（仅调试模式）。

## 内部实现细节

### 像素格式转换

#### copyFT2LCD16()
将 FreeType 位图转换为 Skia 的 LCD16 格式（用于 LCD 子像素渲染）。

**支持的源格式：**
- `FT_PIXEL_MODE_MONO`: 单色位图
- `FT_PIXEL_MODE_GRAY`: 灰度位图
- `FT_PIXEL_MODE_LCD`: 水平 RGB 子像素
- `FT_PIXEL_MODE_LCD_V`: 垂直 RGB 子像素

**特性：**
- 模板参数 `APPLY_PREBLEND` 控制是否应用 gamma 预混合
- 支持 BGR 和 RGB 子像素顺序
- 使用查找表（LUT）进行 gamma 校正

#### copyFTBitmap()
将 FreeType 位图复制到 SkMask。支持的格式组合：

| FreeType 格式 | Skia 格式 | 支持状态 |
|--------------|----------|---------|
| MONO | BW | ✓ |
| MONO | A8 | ✓ (转换) |
| GRAY | A8 | ✓ |
| BGRA | ARGB32 | ✓ |
| MONO/GRAY | LCD16 | ✓ (通过 copyFT2LCD16) |

#### packA8ToA1()
将 A8 格式的 alpha 掩码打包为 A1 格式（每像素 1 位），用于优化内存使用。

### 彩色字体渲染

#### COLRv0 实现
COLRv0 使用简单的分层和调色板机制：
1. 读取字形的 COLR 表获取层列表
2. 对每一层加载对应的字形
3. 使用调色板中的颜色填充字形
4. 按顺序合成所有层

#### COLRv1 实现
COLRv1 支持复杂的图形效果，实现包括：

**渐变支持：**
- 线性渐变（`FT_PaintLinearGradient`）
- 径向渐变（`FT_PaintRadialGradient`）
- 扫描渐变（`FT_PaintSweepGradient`）

**混合模式：**
- 标准 Porter-Duff 混合模式
- 特殊的前景色混合

**变换支持：**
- 平移、旋转、缩放
- 仿射变换矩阵

**裁剪支持：**
- 使用 `FT_Get_Color_Glyph_ClipBox` 获取裁剪框
- 支持字形级别的裁剪

#### SVG 字形支持
通过 `SkOpenTypeSVGDecoder` 接口解码 SVG 字形：
1. 从字体中提取 SVG 数据
2. 调用注册的 SVG 解码器
3. 将 SVG 渲染为 SkDrawable
4. 绘制到目标画布

### 路径生成

#### generateFacePath()
将 FreeType 轮廓转换为 SkPath 的核心函数：

**转换过程：**
1. 使用 `FT_Outline_Decompose` 遍历轮廓
2. 将 FreeType 的轮廓命令映射到 Skia 路径操作：
   - `move_to` → `moveTo()`
   - `line_to` → `lineTo()`
   - `conic_to` → `conicTo()` (二次贝塞尔曲线)
   - `cubic_to` → `cubicTo()` (三次贝塞尔曲线)
3. 处理坐标转换（FreeType 使用 26.6 定点数）
4. 处理轮廓方向和填充规则

### 渐变处理

#### truncateToStopInterpolating()
截断颜色停止点并插值边界颜色。用于处理特殊情况，如零半径径向渐变。

#### lerpSkColor()
在两个颜色之间进行线性插值，使用 SIMD 优化（skvx）。

### 子像素渲染

**LCD 子像素渲染原理：**
1. FreeType 以 3 倍宽度渲染字形（RGB 通道分别渲染）
2. 应用 gamma 预混合（通过查找表）
3. 将 RGB 三元组打包为 16 位 RGB565 格式
4. 支持 BGR 和 RGB 子像素布局

**性能优化：**
- 使用模板特化避免运行时分支
- 内联关键函数
- SIMD 优化颜色转换

### 版本兼容性处理

模块包含大量的 FreeType 版本检测和兼容性代码：

```cpp
// 检测 COLRv1 支持
#ifdef TT_SUPPORT_COLRV1
#if (FREETYPE_MAJOR < 2 || ...) && !defined(FT_STATIC_CAST)
#    undef TT_SUPPORT_COLRV1
#endif
#endif

// FT_OUTLINE_OVERLAP 向后兼容
#ifndef FT_OUTLINE_OVERLAP
#    define FT_OUTLINE_OVERLAP 0x40
#endif

// FT_LOAD_COLOR 向后兼容
#ifndef FT_LOAD_COLOR
#    define FT_LOAD_COLOR ( 1L << 20 )
#    define FT_PIXEL_MODE_BGRA 7
#endif
```

这确保了 Skia 能够在不同版本的 FreeType 上正确编译和运行。

### 调试支持

#### kSkShowTextBlitCoverage
调试常量，启用时会高亮显示文本覆盖区域，帮助开发者诊断渲染问题。

#### SkTraceFtrGetError()
通过宏技巧将 FreeType 错误枚举转换为字符串，方便调试输出。

## 依赖关系

### 外部依赖
| 库 | 用途 |
|---|-----|
| **FreeType** | 字体加载和渲染核心库 |
| `<freetype/freetype.h>` | 核心 API |
| `<freetype/ftbitmap.h>` | 位图操作 |
| `<freetype/ftcolor.h>` | 彩色字体支持 |
| `<freetype/ftimage.h>` | 图像格式定义 |
| `<freetype/ftoutln.h>` | 轮廓操作 |
| `<freetype/ftsizes.h>` | 大小管理 |
| `<freetype/otsvg.h>` | SVG 字形支持 |

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkGlyph` | 字形数据结构 |
| `SkScalerContext` | 字形缩放上下文 |
| `SkCanvas` | 绘图画布（彩色字体） |
| `SkPath` / `SkPathBuilder` | 矢量路径 |
| `SkBitmap` | 位图数据 |
| `SkColor` | 颜色表示 |
| `SkMaskGamma` | Gamma 校正 |
| `SkGradient` | 渐变效果（COLRv1） |
| `SkOpenTypeSVGDecoder` | SVG 解码器接口 |
| `SkFDot6` | 26.6 定点数运算 |

## 设计模式与设计决策

### 1. 工具类模式（Utility Class Pattern）
`SkScalerContextFTUtils` 作为工具类，封装所有 FreeType 相关操作，避免了复杂的继承层次。

### 2. 模板方法模式（Template Method Pattern）
`copyFT2LCD16<APPLY_PREBLEND>` 使用模板参数控制是否应用预混合，在编译时消除分支，提升性能。

### 3. 策略模式（Strategy Pattern）
通过 `SkOpenTypeSVGDecoder` 接口实现 SVG 解码策略可插拔，允许使用不同的 SVG 渲染引擎。

### 4. RAII 模式（Resource Acquisition Is Initialization）
使用 `SkUniqueFTSize` 等智能指针类型自动管理 FreeType 资源。

### 5. 向后兼容性优先
大量的版本检测和宏定义确保在旧版本 FreeType 上也能编译，但功能可能受限。这是实用主义的设计决策。

### 6. 性能优先的数据转换
直接操作内存和位运算（如 `packTriple`、`pack_8_to_1`）而非使用高层 API，追求最大性能。

### 7. 分层渲染架构
彩色字体使用画布渲染而非直接像素操作，利用了 Skia 的图形能力，代码更简洁。

### 8. 渐进式功能启用
通过条件编译（如 `TT_SUPPORT_COLRV1`、`FT_CONFIG_OPTION_SVG`）只在支持的平台上启用高级功能。

## 性能考量

### 1. 内联关键函数
```cpp
inline int convert_8_to_1(unsigned byte)
inline SkMask::Format SkMaskFormat_for_SkColorType(SkColorType colorType)
```
频繁调用的小函数标记为 inline，消除函数调用开销。

### 2. 模板特化消除分支
使用 `copyFT2LCD16<APPLY_PREBLEND>` 模板参数在编译时决定代码路径，避免运行时 if 判断。

### 3. SIMD 优化
使用 `skvx::float4` 进行颜色插值，充分利用 SIMD 指令加速。

### 4. 直接内存操作
大量使用 `memcpy`、位运算和指针操作，最小化数据复制和转换开销。

### 5. 位图格式优化
- A1 格式打包 8 个像素到 1 字节，节省 87.5% 内存
- LCD16 格式使用 RGB565，相比 ARGB32 节省 50% 内存

### 6. 缓存和去重
使用 `OpaquePaintHasher` 对 COLRv1 绘制对象进行哈希和去重，避免重复计算。

### 7. 条件编译优化
Debug 代码（如 `kSkShowTextBlitCoverage`）使用 `constexpr` 和 `if constexpr`，在 Release 版本完全消除。

### 8. 增量复制策略
```cpp
size_t commonRowBytes = std::min(srcRowBytes, dstRowBytes);
```
只复制必要的字节数，避免浪费。

### 9. 定点数运算
FreeType 使用 26.6 定点数，避免浮点运算开销，代码通过 `SkFDot6` 高效转换。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontHost_FreeType.cpp` | FreeType 字体宿主主实现 |
| `src/core/SkScalerContext.h` | 字形缩放上下文接口 |
| `src/core/SkGlyph.h` | 字形数据结构定义 |
| `include/core/SkCanvas.h` | 绘图画布接口 |
| `include/core/SkPath.h` | 矢量路径接口 |
| `include/core/SkOpenTypeSVGDecoder.h` | SVG 解码器接口 |
| `src/core/SkMaskGamma.h` | Gamma 校正实现 |
| `src/core/SkFDot6.h` | 26.6 定点数工具 |
| `include/effects/SkGradient.h` | 渐变效果 API |
| `src/ports/SkFontMgr_android.cpp` | Android 字体管理器 |
| `src/ports/SkTypeface_FreeType.h` | FreeType typeface 实现 |
