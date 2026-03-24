# SkTypeface_Mac - macOS/iOS CoreText 字体类型

> 源文件:
> - `src/ports/SkTypeface_mac_ct.h`
> - `src/ports/SkTypeface_mac_ct.cpp`

## 概述

`SkTypeface_Mac` 是 Skia 在 macOS 和 iOS 平台上基于 CoreText 框架实现的字体类型类。它封装了 `CTFontRef`，提供完整的字体元数据访问、字形映射、变体轴支持、序列化/反序列化以及缩放上下文创建等功能。

该实现处理了 CoreText API 的各种平台差异和限制，包括系统字体与用户数据字体的权重映射差异、`opsz`（光学大小）变体轴的特殊处理，以及 CoreText 的 `CTFontCopyVariationAxes` 性能问题的缓存策略。

## 架构位置

```
SkTypeface (include/core/)
  |
  v
SkTypeface_Mac (src/ports/)        // 本类
  |
  +-- CTFontRef (CoreText)         // 底层字体引用
  +-- SkScalerContext_Mac           // 字形缩放上下文
  +-- SkTypefaceCache               // 字体缓存
```

## 主要类与结构体

### `OpszVariation`

```cpp
struct OpszVariation {
    bool isSet = false;
    double value = 0;
};
```

记录光学大小变体轴设置。

### `CTFontVariation`

```cpp
struct CTFontVariation {
    SkUniqueCFRef<CFDictionaryRef> variation;
    SkUniqueCFRef<CFDictionaryRef> wrongOpszVariation;
    OpszVariation opsz;
};
```

封装 CoreText 字体变体信息。

### `SkTypeface_Mac`

继承自 `SkTypeface`。

**关键成员：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFontRef` | `SkUniqueCFRef<CTFontRef>` | CoreText 字体引用 |
| `fOpszVariation` | `OpszVariation` | 光学大小变体设置 |
| `fHasColorGlyphs` | `bool` | 是否包含彩色字形 |
| `fStream` | `unique_ptr<SkStreamAsset>` | 用户提供的字体数据流 |
| `fIsFromStream` | `bool` | 是否来自数据流 |
| `fVariationAxes` | `SkUniqueCFRef<CFArrayRef>` | 缓存的变体轴（延迟初始化） |

## 公共 API 函数

### `SkTypeface_Mac::Make()`

```cpp
static sk_sp<SkTypeface> Make(SkUniqueCFRef<CTFontRef> font,
                               OpszVariation opszVariation,
                               std::unique_ptr<SkStreamAsset> providedData);
```

创建字体类型实例。流程：
1. 从 `CTFontDescriptor` 获取字体样式
2. 检查 `kCTFontMonoSpaceTrait` 判断等宽字体
3. 若非来自流，通过 `SkTypefaceCache` 缓存查找/添加
4. 若来自流，直接创建（不缓存）

### `SkMakeTypefaceFromCTFont()`

公共函数，从外部 `CTFontRef` 创建 `SkTypeface`。调用 `CFRetain` 后委托给 `Make()`。

### 权重/宽度转换

```cpp
CGFloat SkCTFontCTWeightForCSSWeight(int fontstyleWeight);
CGFloat SkCTFontCTWidthForCSSWidth(int fontstyleWidth);
SkFontStyle SkCTFontDescriptorGetSkFontStyle(CTFontDescriptorRef desc, bool fromDataProvider);
```

处理 CSS [0,1000] 权重与 CoreText [-1,1] 权重之间的映射。系统字体和用户数据字体使用不同的映射表。

## 内部实现细节

### 字体样式映射

使用 `LinearInterpolater` 模板类在 CSS 权重/宽度和 CoreText 权重/宽度之间进行分段线性插值。系统字体使用 `NSFontWeight` 映射，数据字体使用独立映射。

### Glyph-to-Unicode 映射

`populate_glyph_to_unicode()` 构建字形到 Unicode 的映射表：
1. 尝试通过 `CTFontCopyCharacterSet` 获取字符集位图
2. 遍历位图中每个设置的位，通过 `CTFontGetGlyphsForCharacters` 获取字形 ID
3. 支持 BMP 和补充平面（最多 Plane 16）
4. 若 `CTFontCopyCharacterSet` 返回 nullptr，回退到逐字符遍历的慢速路径

### 变体轴缓存

```cpp
CFArrayRef getVariationAxes() const;
```

`CTFontCopyVariationAxes` 会获取所有轴的本地化名称，非常慢。因此使用 `SkOnce` 缓存结果，仅在首次调用时执行。

### 流式字体加载

`MakeFromStream()` 支持从流数据创建字体，处理：
- TTC 索引选择
- 变体位置参数
- 光学大小轴特殊处理

## 依赖关系

### 平台依赖

- **macOS**: `ApplicationServices.framework`（包含 CoreText、CoreGraphics）
- **iOS**: `CoreText.framework`、`CoreGraphics.framework`、`CoreFoundation.framework`

### Skia 内部

- `SkTypeface`：基类
- `SkTypefaceCache`：字体缓存
- `SkScalerContext_Mac`：缩放上下文
- `SkCTFontCreateExactCopy`：精确字体拷贝工具
- sfnt 表工具：`SkOTTable_OS_2`、`SkOTUtils` 等

## 设计模式与设计决策

1. **缓存策略**：系统字体通过 `SkTypefaceCache` 全局缓存，流式字体不缓存
2. **延迟初始化**：变体轴信息使用 `SkOnce` 延迟初始化以规避 CoreText 性能问题
3. **双映射表**：系统字体和数据字体使用不同的权重映射表以匹配各自的行为
4. **平台条件编译**：使用 `SK_BUILD_FOR_MAC` / `SK_BUILD_FOR_IOS` 区分平台头文件
5. **CFType 安全转型**：提供 `SkCFDynamicCast` 模板函数进行类型安全的 CF 类型向下转型

## 性能考量

1. **变体轴缓存**：缓存 `CTFontCopyVariationAxes` 结果，避免重复的昂贵调用
2. **字形映射位图遍历**：使用 `CFCharacterSetCreateBitmapRepresentation` 的位图表示高效遍历字符集
3. **字体缓存**：通过 `SkTypefaceCache` 避免为同一系统字体创建多个实例
4. **慢速回退路径**：`populate_glyph_to_unicode_slow` 仅在字符集不可用时使用（如 Web 字体）
5. **权重映射预计算**：使用 `SkOnce` 确保映射表只初始化一次

### 权重映射表详细说明

系统字体和数据字体使用不同的 CTFontDescriptor 权重范围：

**系统字体映射（使用 NSFont 权重）：**
```
CSS 权重 0   -> 约 -0.80 (CTFont)
CSS 权重 100 -> 约 -0.70
CSS 权重 400 -> 约  0.00 (Normal)
CSS 权重 700 -> 约  0.40 (Bold)
CSS 权重 900 -> 约  0.62
CSS 权重 1000-> 约  0.80
```

**数据字体映射：**
数据字体使用独立的映射表，因为 CoreText 对从 CGDataProvider 创建的字体使用不同的内部权重值。

### Glyph-to-Unicode 位图结构

`CFCharacterSetCreateBitmapRepresentation` 返回的位图格式：

```
[BMP 位图: 8192 字节]        // 覆盖 U+0000 - U+FFFF
[平面索引字节: 1]             // 平面号 (1-16)
[平面位图: 8192 字节]         // 覆盖该平面
... (重复 0-16 次)
```

每个位图中的每个位对应一个码点。通过位索引可以直接计算对应的 Unicode 码点。

### 高级度量获取

`onGetAdvancedMetrics()` 获取用于 PDF 嵌入的高级度量信息：
- 变体字体标志
- PostScript 字体名称
- 字形宽度信息
- 字体类型标志

### FactoryId 常量

```cpp
static constexpr SkTypeface::FactoryId FactoryId = SkSetFourByteTag('c','t','x','t');
```

`'ctxt'` 标识 CoreText 来源的字体，用于跨进程字体序列化和重建。

## 相关文件

- `src/ports/SkScalerContext_mac_ct.h` - macOS 缩放上下文
- `src/utils/mac/SkCTFontCreateExactCopy.h` - CoreText 字体拷贝工具
- `src/utils/mac/SkCTFont.h` - CoreText 字体工具函数
- `src/utils/mac/SkUniqueCFRef.h` - CoreFoundation RAII 封装
- `include/ports/SkTypeface_mac.h` - 公共 macOS 字体 API
- `src/core/SkTypefaceCache.h` - 字体缓存
- `src/sfnt/SkOTTable_OS_2.h` - OS/2 表（用于高级度量）
