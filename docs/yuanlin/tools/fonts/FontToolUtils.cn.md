# FontToolUtils

> 源文件：tools/fonts/FontToolUtils.h, tools/fonts/FontToolUtils.cpp

## 概述

FontToolUtils 是 Skia 工具集中的字体管理工具模块，提供跨平台一致的字体访问、便携字体加载和表情符号字体支持。该模块对于确保测试和示例在不同平台上产生一致结果至关重要，通过提供标准化的字体集和字体管理器，消除了平台特定的字体差异。

主要功能：
- 创建和管理便携字体（跨平台一致）
- 访问测试字体管理器
- 加载表情符号字体（多种格式）
- 创建字符串位图/图像
- 支持用户自定义字体
- 配置原生 vs 便携字体渲染

该模块广泛应用于 Skia 的测试、GM（Golden Master）和示例代码中。

## 架构位置

- **角色**：字体工具和配置中心
- **使用者**：测试工具、GM、示例、基准测试
- **依赖**：平台字体管理器、TestFontMgr
- **提供**：统一的字体访问接口

## 主要类型和枚举

### EmojiFontFormat

```cpp
enum class EmojiFontFormat {
    Cbdt,    // CBDT/CBLC (位图)
    Sbix,    // sbix (Apple 位图)
    ColrV0,  // COLR V0 (分层矢量)
    Test,    // 测试表情符号字体
    Svg      // SVG 表情符号
};
```

### EmojiTestSample

```cpp
struct EmojiTestSample {
    sk_sp<SkTypeface> typeface = nullptr;
    const char* sampleText = "";
};
```

表示表情符号测试样本，包含字体和示例文本。

## 公共 API 函数

### 便携字体 API

#### DefaultPortableFont / DefaultPortableTypeface

```cpp
SkFont DefaultPortableFont();
sk_sp<SkTypeface> DefaultPortableTypeface();
```

返回默认的便携字体/字体面，跨平台一致（通常是 serif 字体）。

#### CreatePortableTypeface

```cpp
sk_sp<SkTypeface> CreatePortableTypeface(const char* name, SkFontStyle style);
```

创建指定名称和样式的便携字体。

**支持的名称**（部分匹配）：
- "ono" → Monospace
- "ans" → Sans-serif
- "erif" → Serif

### 测试字体管理器 API

#### TestFontMgr

```cpp
sk_sp<SkFontMgr> TestFontMgr();
```

返回配置的字体管理器。根据命令行标志和平台选择：
- 便携字体管理器（`--nativeFonts=false`）
- GDI 字体管理器（Windows + `--gdi`）
- AndroidNDK 字体管理器（Android + `--androidndkfonts`）
- 平台默认字体管理器

**平台默认值**：
- Android: `SkFontMgr_New_Android`
- Windows: `SkFontMgr_New_DirectWrite`
- macOS/iOS: `SkFontMgr_New_CoreText`
- Linux: `SkFontMgr_New_FontConfig`
- 其他: 目录或空字体管理器

#### TestFontScanner

```cpp
std::unique_ptr<SkFontScanner> TestFontScanner();
```

返回配置的字体扫描器（FreeType 或 Fontations）。

#### UsePortableFontMgr

```cpp
void UsePortableFontMgr();
```

强制使用便携字体管理器（设置 `FLAGS_nativeFonts = false`）。

#### FontMgrIsGDI

```cpp
bool FontMgrIsGDI();
```

检查是否使用 GDI 字体管理器（Windows 特定）。

### 字体创建 API

#### DefaultTypeface / DefaultFont

```cpp
sk_sp<SkTypeface> DefaultTypeface();
SkFont DefaultFont();
```

返回测试字体管理器的默认字体/字体面。如果不可用，回退到便携字体。

#### CreateTestTypeface

```cpp
sk_sp<SkTypeface> CreateTestTypeface(const char* name, SkFontStyle style);
```

使用 TestFontMgr 创建字体，失败时回退到便携字体。

#### CreateTypefaceFromResource

```cpp
sk_sp<SkTypeface> CreateTypefaceFromResource(const char* resource, int ttcIndex = 0);
```

从资源文件加载字体（通常是 `resources/fonts/` 目录）。

**参数**：
- `resource` - 资源路径（如 "fonts/Roboto-Regular.ttf"）
- `ttcIndex` - TTC（TrueType Collection）索引

### 表情符号字体 API

#### PlanetTypeface

```cpp
sk_sp<SkTypeface> PlanetTypeface();
```

返回带行星表情符号的彩色字体（用于缩放测试）。

**平台选择**：
- Windows: `fonts/planetcolr.ttf` (COLR)
- macOS/iOS: `fonts/planetsbix.ttf` (sbix)
- 其他: `fonts/planetcbdt.ttf` (CBDT)

#### EmojiSample

```cpp
EmojiTestSample EmojiSample();
EmojiTestSample EmojiSample(EmojiFontFormat format);
```

返回表情符号测试样本。无参数版本选择平台默认格式。

**示例文本**：
- 大多数格式: `"\U0001F600 \u2662"` (😀 ♢)
- SVG 格式: `"abcdefghij"`

#### NameForFontFormat

```cpp
SkString NameForFontFormat(EmojiFontFormat format);
```

返回格式名称字符串（如 "cbdt", "sbix", "colrv0"），用于测试命名。

### 其他 API

#### SampleUserTypeface

```cpp
sk_sp<SkTypeface> SampleUserTypeface();
```

创建简单的用户自定义字体（使用 SkCustomTypefaceBuilder）。

**特性**：
- 所有字形为圆形
- 自定义字体度量
- 用于测试用户字体 API

#### CreateStringBitmap / CreateStringImage

```cpp
SkBitmap CreateStringBitmap(int w, int h, SkColor c, int x, int y,
                           int textSize, const char* str);
sk_sp<SkImage> CreateStringImage(int w, int h, SkColor c, int x, int y,
                                 int textSize, const char* str);
```

创建包含文本的位图/图像，用于测试和验证。

#### RegisterAvailableTypefaceFactories

```cpp
void RegisterAvailableTypefaceFactories();
```

注册所有编译时可用的字体工厂（CoreText、DirectWrite、FreeType、Fontations）。

## 内部实现细节

### 命令行标志

```cpp
static DEFINE_bool(nativeFonts, true, "...");
static DEFINE_bool(gdi, false, "...");
static DEFINE_bool(fontations, false, "...");
static DEFINE_bool(androidndkfonts, false, "...");
```

这些标志控制字体管理器选择。

### 静态单例

TestFontMgr 使用线程安全的静态单例：

```cpp
sk_sp<SkFontMgr> TestFontMgr() {
    static sk_sp<SkFontMgr> mgr;
    static SkOnce once;
    once([] {
        // 初始化代码
    });
    return mgr;
}
```

`SkOnce` 确保仅初始化一次，即使多线程调用也安全。

### 平台检测

使用预处理器宏检测平台：

```cpp
#if defined(SK_BUILD_FOR_WIN)
    filename = "fonts/planetcolr.ttf";
#elif defined(SK_BUILD_FOR_MAC) || defined(SK_BUILD_FOR_IOS)
    filename = "fonts/planetsbix.ttf";
#else
    filename = "fonts/planetcbdt.ttf";
#endif
```

### 条件编译

大量条件编译确保仅编译平台支持的代码：

```cpp
#if defined(SK_FONTMGR_CORETEXT_AVAILABLE)
    mgr = SkFontMgr_New_CoreText(nullptr);
#elif defined(SK_FONTMGR_DIRECTWRITE_AVAILABLE)
    mgr = SkFontMgr_New_DirectWrite();
#endif
```

### 回退机制

许多函数提供回退：

```cpp
sk_sp<SkTypeface> CreateTestTypeface(...) {
    sk_sp<SkTypeface> face = fm->legacyMakeTypeface(name, style);
    if (face) {
        return face;
    }
    return CreatePortableTypeface(name, style);  // 回退
}
```

### 用户字体创建

SampleUserTypeface 展示 SkCustomTypefaceBuilder 用法：

```cpp
SkCustomTypefaceBuilder builder;
builder.setMetrics(metrics, 1.0f/upem);
builder.setFontStyle(SkFontStyle(...));
for (SkGlyphID index = 0; index <= 67; ++index) {
    builder.setGlyph(index, width/upem, SkPath::Circle(...));
}
return builder.detach();
```

## 依赖关系

### Skia 核心
- `include/core/SkFont.h` - 字体
- `include/core/SkTypeface.h` - 字体面
- `include/core/SkFontMgr.h` - 字体管理器
- `include/core/SkFontScanner.h` - 字体扫描器
- `include/utils/SkCustomTypeface.h` - 自定义字体

### 平台字体管理器
- Windows: DirectWrite、GDI
- macOS/iOS: CoreText
- Android: Android、AndroidNDK
- Linux: FontConfig
- 跨平台: FreeType、Fontations

### 工具
- `tools/fonts/TestFontMgr.h` - 便携字体管理器
- `tools/Resources.h` - 资源加载
- `tools/flags/CommandLineFlags.h` - 命令行标志

## 设计模式与设计决策

### 工厂模式
多个工厂函数创建不同类型的字体和字体管理器。

### 单例模式
TestFontMgr 使用延迟初始化单例。

### 策略模式
命令行标志选择不同的字体管理器策略。

### 回退模式
多层回退确保总能获得可用字体。

### 平台抽象
条件编译和统一接口隐藏平台差异。

## 性能考量

- 单例字体管理器避免重复初始化
- 静态缓存常用字体（如 PlanetTypeface）
- 延迟加载资源字体
- 便携字体预加载到内存

## 相关文件

### 同目录
- `tools/fonts/TestFontMgr.h/cpp` - 便携字体管理器实现
- `tools/fonts/TestTypeface.h` - 测试字体面定义
- `tools/fonts/TestSVGTypeface.h` - SVG 字体测试

### 资源
- `resources/fonts/` - 字体文件目录

### 平台移植
- `include/ports/SkFontMgr_*.h` - 各平台字体管理器
- `include/ports/SkFontScanner_*.h` - 各平台字体扫描器

### 工具
- `tools/Resources.h` - 资源加载
- `tools/flags/CommandLineFlags.h` - 命令行解析
