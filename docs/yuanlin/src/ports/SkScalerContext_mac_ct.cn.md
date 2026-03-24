# SkScalerContext_Mac - macOS/iOS CoreText 字形缩放上下文

> 源文件:
> - `src/ports/SkScalerContext_mac_ct.h`
> - `src/ports/SkScalerContext_mac_ct.cpp`

## 概述

`SkScalerContext_Mac` 是 Skia 在 macOS 和 iOS 平台上通过 CoreText 和 CoreGraphics 框架实现的字形缩放上下文。它负责字形度量计算、光栅化图像生成、字形路径提取和字体度量获取。

该实现通过离屏 CGContext 进行字形渲染，处理了 CoreText/CoreGraphics 的各种平台特性和限制，包括子像素定位、LCD 平滑、颜色字形、以及 CoreGraphics 2.0 gamma 值的反转。

## 架构位置

```
SkScalerContext (src/core/)
  |
  v
SkScalerContext_Mac (src/ports/)     // 本类
  |
  +-- CTFontRef / CGFontRef          // CoreText/CoreGraphics 字体
  +-- Offscreen (内部类)              // 离屏渲染缓冲区
  +-- SkTypeface_Mac                 // 关联字体类型
```

## 主要类与结构体

### `SkScalerContext_Mac`

继承自 `SkScalerContext`。

**关键成员：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fOffscreen` | `Offscreen` | 离屏渲染缓冲区 |
| `fCTFont` | `SkUniqueCFRef<CTFontRef>` | 不含旋转的 CoreText 字体 |
| `fTransform` | `CGAffineTransform` | 不含字体大小的变换 |
| `fInvTransform` | `CGAffineTransform` | 逆变换 |
| `fCGFont` | `SkUniqueCFRef<CGFontRef>` | CoreGraphics 字体 |
| `fDoSubPosition` | `bool` | 是否启用子像素定位 |

### `Offscreen` 内部类

管理离屏 CGContext 进行字形渲染。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fImageStorage` | `SkAutoSMalloc<kSize>` | 图像存储（默认 32x32 像素） |
| `fRGBSpace` | `SkUniqueCFRef<CGColorSpaceRef>` | RGB 颜色空间 |
| `fCG` | `SkUniqueCFRef<CGContextRef>` | CG 上下文 |
| `fCGForegroundColor` | `SkUniqueCFRef<CGColorRef>` | COLR 前景色 |
| `fSize` | `SkISize` | 当前缓冲区大小 |
| `fDoAA` | `bool` | 是否启用抗锯齿 |
| `fDoLCD` | `bool` | 是否启用 LCD 平滑 |

## 公共 API 函数

### 构造函数

```cpp
SkScalerContext_Mac(SkTypeface_Mac&, const SkScalerContextEffects&, const SkDescriptor*);
```

1. 计算缩放和变换矩阵（分离大小和旋转）
2. 使用 `SkCTFontCreateExactCopy` 创建指定大小的 CTFont（保留 opsz 设置）
3. 获取对应的 CGFont

### 受保护的虚函数

```cpp
GlyphMetrics generateMetrics(const SkGlyph&, SkArenaAlloc*) override;
void generateImage(const SkGlyph&, void*) override;
std::optional<GeneratedPath> generatePath(const SkGlyph&) override;
void generateFontMetrics(SkFontMetrics*) override;
```

## 内部实现细节

### 字形度量生成

`generateMetrics()` 流程：
1. 通过 `CTFontGetAdvancesForGlyphs` 获取水平方向 advance 并应用变换
2. 通过 `CTFontGetBoundingRectsForGlyphs` 获取边界框并应用变换
3. 对零 advance 字形检查路径是否为空（处理 U+200B 等零宽空格的垃圾边界问题）
4. 子像素定位时扩展右/下边界
5. 向外扩展 1 像素（为 CG 抗锯齿留出空间）

### 离屏渲染

`Offscreen::getCG()` 管理离屏缓冲区：
1. 按需创建/扩展 CGBitmapContext（大小向上取到 2 的幂）
2. 配置子像素定位、子像素量化等 CG 属性
3. 颜色字形使用透明黑背景和 `kCGImageAlphaPremultipliedFirst`
4. 非颜色字形使用白色背景（黑色前景）
5. 调用 `CTFontDrawGlyphs` 绘制字形

### Gamma 反转

CoreGraphics 默认使用 2.0 作为子像素覆盖 gamma 值。`gLinearCoverageFromCGLCDValue` 查找表通过 `sk_pow2_table` 反转此 gamma，获得线性覆盖值。

### 像素格式转换

- `cgpixels_to_bits()` - CGRGBPixel 转 BW 位图
- `rgb_to_a8()` / `RGBToA8()` - CGRGBPixel 转 A8（可选 preblend）
- `RGBToLcd16()` - CGRGBPixel 转 LCD16（可选 preblend）
- `cgpixels_to_pmcolor()` - CGRGBPixel 转 ARGB32（彩色字形）

### CTFont 使用注意事项

代码注释详细说明了一个关键约束：

> 在 10.10.1 中，`CTFontGetAdvancesForGlyphs` 会将字体变换应用于 advance 宽度，但始终将高度设为 0。因此使用不含旋转的字体获取 advance，然后单独应用旋转。

> 创建相同大小但不同变换的 CTFont 副本可能会选择不同的底层字体数据。因此每个 `SkScalerContext` 只创建一个 CTFont。

## 依赖关系

### 平台依赖

- CoreText: `CTFontDrawGlyphs`, `CTFontGetAdvancesForGlyphs`, `CTFontGetBoundingRectsForGlyphs`
- CoreGraphics: `CGBitmapContextCreate`, `CGContextSetShouldSmoothFonts` 等

### Skia 内部

- `SkScalerContext` - 基类
- `SkTypeface_Mac` - 关联字体类型
- `SkCTFontCreateExactCopy` - 精确字体拷贝
- `SkMaskGamma` - gamma 校正
- `SkColorData` / `SkColorPriv` - 颜色处理

## 设计模式与设计决策

1. **离屏缓冲区复用**：`Offscreen` 对象随 scaler context 生命周期存活，按需扩展
2. **单 CTFont 原则**：每个 scaler context 只创建一个 CTFont 以避免字体数据选择不一致
3. **变换分离**：字体大小和变换矩阵分离处理，适应 CoreText 的 API 行为
4. **Gamma 反转表**：使用编译期生成的查找表反转 CG 2.0 gamma

## 性能考量

1. **缓冲区大小向上取整**：使用 `SkNextPow2` 减少重分配频率
2. **条件化 AA/LCD**：仅在设置变化时重新配置 CGContext
3. **预计算 gamma 表**：使用 `constexpr` 数组避免运行时计算
4. **彩色字形检测**：检查 `fHasColorGlyphs` 标志以决定是否禁用 LCD 和请求路径

### generateImage 完整处理流程

`generateImage()` 根据字形格式选择不同的像素转换路径：

```
CGRGBPixel* (从 Offscreen::getCG 获取)
  |
  +-- LCD/A8 + 平滑 -> 应用 gamma 反转 (gLinearCoverageFromCGLCDValue)
  |
  v
根据 maskFormat:
  +-- kBW_Format     -> cgpixels_to_bits()
  +-- kA8_Format     -> RGBToA8<APPLY_PREBLEND>()
  +-- kLCD16_Format  -> RGBToLcd16<APPLY_PREBLEND>()
  +-- kARGB32_Format -> cgpixels_to_pmcolor() (逐像素)
```

### CG 坐标系统处理

CoreGraphics 使用 Y 轴向上的坐标系，而 Skia 使用 Y 轴向下：

- `MatrixToCGAffineTransform()` 在转换矩阵时翻转 Y 方向的 skew 和 translate 分量
- 字形边界框从 CG 坐标转换为 Skia 坐标：`skBounds.origin.y = -cgBounds.origin.y - cgBounds.height`
- 字形绘制点位置需要通过逆变换映射到文本空间

### Offscreen 缓冲区生命周期

```
SkScalerContext_Mac 创建
  |
  v
Offscreen 初始化 (fSize = {0,0})
  |
  v
首次 getCG() 调用
  -> 创建 CGBitmapContext (大小向上取到 2 的幂)
  -> 配置子像素设置
  -> 设置文本绘制模式
  |
  v
后续 getCG() 调用
  -> 若字形大于当前缓冲区，扩展并重新创建 CGContext
  -> 否则复用现有 CGContext
  -> 仅在 AA/LCD 设置变化时重新配置
  |
  v
SkScalerContext_Mac 销毁 -> Offscreen 及其 CGContext 释放
```

### 字形路径生成

`generatePath()` 通过 `CTFontCreatePathForGlyph` 获取 CGPath，然后使用 CoreGraphics 的路径遍历 API 将其转换为 `SkPath`。路径中的变换（`fTransform`）需要单独应用。

### 字体度量生成

`generateFontMetrics()` 通过以下 CoreText API 获取度量：
- `CTFontGetAscent()` / `CTFontGetDescent()` / `CTFontGetLeading()`
- `CTFontGetBoundingBox()`
- `CTFontGetUnderlinePosition()` / `CTFontGetUnderlineThickness()`

## 相关文件

- `src/ports/SkTypeface_mac_ct.h` - macOS 字体类型
- `src/utils/mac/SkCTFontCreateExactCopy.h` - CoreText 字体精确拷贝
- `src/utils/mac/SkCGBase.h` - CoreGraphics 基础工具
- `src/utils/mac/SkCGGeometry.h` - CG 几何工具
- `src/core/SkScalerContext.h` - 缩放上下文基类
- `src/core/SkMaskGamma.h` - Gamma 校正
- `src/core/SkGlyph.h` - 字形数据结构
