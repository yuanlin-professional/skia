# SkFontMgr_mac_ct

> 源文件: include/ports/SkFontMgr_mac_ct.h, src/ports/SkFontMgr_mac_ct.cpp

## 概述

SkFontMgr_mac_ct 是 Skia 图形库为 macOS 和 iOS 平台提供的字体管理器实现，基于 Apple 的 CoreText 框架。该模块通过 CoreText API 访问系统字体，支持字体枚举、样式匹配、字符回退、变体字体和 CSS 通用家族映射。它处理 CoreText 特有的符号特征（Symbolic Traits）、权重/宽度/倾斜的精确映射，以及 macOS 10.11 的字体创建兼容性问题。

## 架构位置

该模块位于 Skia 的平台适配层（ports），专门为 Apple 平台提供字体管理：

```
skia/
├── include/ports/
│   └── SkFontMgr_mac_ct.h              # 公共接口
└── src/ports/
    ├── SkFontMgr_mac_ct.cpp            # 实现（561 行）
    └── SkTypeface_mac_ct.h             # CoreText typeface 实现
```

该模块在 macOS 上使用 ApplicationServices 框架，在 iOS 上使用 CoreText/CoreGraphics 框架。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `SkFontStyleSet_Mac` | `SkFontStyleSet` | 单个字体家族的样式集合 |
| `SkFontMgr_Mac` | `SkFontMgr` | CoreText 字体管理器主类 |

### 关键成员变量

**SkFontStyleSet_Mac:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fArray` | `SkUniqueCFRef<CFArrayRef>` | CoreText 字体描述符数组 |
| `fCount` | `int` | 字体数量 |

**SkFontMgr_Mac:**
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fNames` | `SkUniqueCFRef<CFArrayRef>` | 系统字体家族名称列表 |
| `fCount` | `int` | 字体家族数量 |
| `fFontCollection` | `SkUniqueCFRef<CTFontCollectionRef>` | CoreText 字体集合 |

## 公共 API 函数

### 工厂函数

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_CoreText(CTFontCollectionRef fontCollection);
```

创建 CoreText 字体管理器，参数说明：
- **fontCollection**: CoreText 字体集合，nullptr 则使用系统可用字体集合

### SkFontMgr 接口实现

```cpp
// 字体家族枚举
int onCountFamilies() const override;
void onGetFamilyName(int index, SkString* familyName) const override;
sk_sp<SkFontStyleSet> onCreateStyleSet(int index) const override;
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override;

// 字体匹配
sk_sp<SkTypeface> onMatchFamilyStyle(const char familyName[],
                                     const SkFontStyle& style) const override;
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(const char familyName[],
                                              const SkFontStyle& style,
                                              const char* bcp47[], int bcp47Count,
                                              SkUnichar character) const override;

// 从数据创建 typeface
sk_sp<SkTypeface> onMakeFromData(sk_sp<SkData>, int ttcIndex) const override;
sk_sp<SkTypeface> onMakeFromStreamArgs(std::unique_ptr<SkStreamAsset>,
                                       const SkFontArguments&) const override;
sk_sp<SkTypeface> onMakeFromFile(const char path[], int ttcIndex) const override;
```

## 内部实现细节

### 样式转换

#### CoreText 权重映射

使用 WebKit 风格的精确映射：

```cpp
static SkUniqueCFRef<CTFontDescriptorRef> create_descriptor(
        CFStringRef familyName, const SkFontStyle& style) {
    // 权重转换
    CGFloat ctWeight = SkCTFontCTWeightForCSSWeight(style.weight());
    // 范围: -1.0 (最轻) 到 1.0 (最重)

    // 宽度转换
    CGFloat ctWidth = SkCTFontCTWidthForCSSWidth(style.width());
    // 范围: -1.0 (最窄) 到 1.0 (最宽)

    // 倾斜转换
    static const CGFloat kSystemFontItalicSlope = 0.07;  // 基于 WebKit 实现
    CGFloat ctSlant = style.slant() == SkFontStyle::kUpright_Slant ? 0 : kSystemFontItalicSlope;

    // 创建 traits 字典
    CFDictionaryAddValue(cfTraits, kCTFontWeightTrait, cfFontWeight);
    CFDictionaryAddValue(cfTraits, kCTFontWidthTrait, cfFontWidth);
    CFDictionaryAddValue(cfTraits, kCTFontSlantTrait, cfFontSlant);
}
```

#### SkFontStyle 提取

从 CTFontDescriptorRef 提取 Skia 样式：

```cpp
SkFontStyle style = SkCTFontDescriptorGetSkFontStyle(desc, false);
```

该函数在 `SkTypeface_mac_ct.h` 中实现，处理 CoreText 特征到 Skia 样式的逆向映射。

### 符号特征处理（macOS 10.11 兼容）

macOS 10.11 存在字体创建 bug（[Chromium issue 8447](https://bugs.chromium.org/p/skia/issues/detail?id=8447)），需要验证并重建字体：

```cpp
static sk_sp<SkTypeface> create_from_desc_and_style(
        CTFontDescriptorRef desc, const SkFontStyle& style) {
    SkUniqueCFRef<CTFontRef> ctFont(CTFontCreateWithFontDescriptor(desc, 0, nullptr));

    // 1. 获取实际特征
    const CTFontSymbolicTraits traits = CTFontGetSymbolicTraits(ctFont.get());

    // 2. 计算期望特征
    CTFontSymbolicTraits expected_traits = traits;
    if (style.slant() != SkFontStyle::kUpright_Slant) {
        expected_traits |= kCTFontItalicTrait;
    }
    if (style.weight() >= SkFontStyle::kBold_Weight) {
        expected_traits |= kCTFontBoldTrait;
    }

    // 3. 不匹配则使用符号特征重建
    if (expected_traits != traits) {
        SkUniqueCFRef<CTFontRef> ctNewFont(CTFontCreateCopyWithSymbolicTraits(
            ctFont.get(), 0, nullptr, expected_traits, expected_traits));
        if (ctNewFont) {
            ctFont = std::move(ctNewFont);
        }
    }

    return SkTypeface_Mac::Make(std::move(ctFont), OpszVariation(), nullptr);
}
```

### CSS 通用家族映射

```cpp
static const char* map_css_names(const char* name) {
    static const struct {
        const char* fFrom;  // CSS 名称
        const char* fTo;    // macOS 系统字体
    } gPairs[] = {
        { "sans-serif", "Helvetica" },
        { "serif",      "Times"     },
        { "monospace",  "Courier"   }
    };

    for (size_t i = 0; i < std::size(gPairs); i++) {
        if (strcmp(name, gPairs[i].fFrom) == 0) {
            return gPairs[i].fTo;
        }
    }
    return name;  // 无变化
}
```

在 `onLegacyMakeTypeface` 中应用映射。

### 字体家族枚举

#### iOS 动态链接兼容

iOS 上 `CTFontManagerCopyAvailableFontFamilyNames` 可能不可用，需要回退实现：

```cpp
SkUniqueCFRef<CFArrayRef> SkCTFontManagerCopyAvailableFontFamilyNames() {
#ifdef SK_BUILD_FOR_IOS
    using CTFontManagerCopyAvailableFontFamilyNamesProc = CFArrayRef (*)(void);
    CTFontManagerCopyAvailableFontFamilyNamesProc ctFontManagerCopyAvailableFontFamilyNames;

    // 运行时查找函数指针
    *(void**)(&ctFontManagerCopyAvailableFontFamilyNames) =
        dlsym(RTLD_DEFAULT, "CTFontManagerCopyAvailableFontFamilyNames");

    if (ctFontManagerCopyAvailableFontFamilyNames) {
        return SkUniqueCFRef<CFArrayRef>(ctFontManagerCopyAvailableFontFamilyNames());
    }

    // 回退：手动从字体集合中提取
    SkUniqueCFRef<CTFontCollectionRef> collection(
        CTFontCollectionCreateFromAvailableFonts(nullptr));
    return SkCopyAvailableFontFamilyNames(collection.get());
#else
    return SkUniqueCFRef<CFArrayRef>(CTFontManagerCopyAvailableFontFamilyNames());
#endif
}
```

#### 手动提取家族名称

```cpp
SkUniqueCFRef<CFArrayRef> SkCopyAvailableFontFamilyNames(CTFontCollectionRef collection) {
    // 1. 获取所有字体描述符
    SkUniqueCFRef<CFArrayRef> descriptors(
        CTFontCollectionCreateMatchingFontDescriptors(collection));

    // 2. 提取家族名称到 CFSet（自动去重）
    SkUniqueCFRef<CFMutableSetRef> familyNameSet(
        CFSetCreateMutable(kCFAllocatorDefault, 0, &kCFTypeSetCallBacks));

    auto addDescriptorFamilyNameToSet = [](const void* value, void* context) -> void {
        CTFontDescriptorRef descriptor = static_cast<CTFontDescriptorRef>(value);
        CFMutableSetRef familyNameSet = static_cast<CFMutableSetRef>(context);
        SkUniqueCFRef<CFTypeRef> familyName(
            CTFontDescriptorCopyAttribute(descriptor, kCTFontFamilyNameAttribute));
        if (familyName) {
            CFSetAddValue(familyNameSet, familyName.get());
        }
    };
    CFArrayApplyFunction(descriptors.get(), CFRangeMake(0, CFArrayGetCount(descriptors.get())),
                         addDescriptorFamilyNameToSet, familyNameSet.get());

    // 3. 转换为数组并排序
    CFIndex count = CFSetGetCount(familyNameSet.get());
    std::unique_ptr<const void*[]> familyNames(new const void*[count]);
    CFSetGetValues(familyNameSet.get(), familyNames.get());

    std::sort(familyNames.get(), familyNames.get() + count, [](const void* a, const void* b){
        return CFStringCompare((CFStringRef)a, (CFStringRef)b, 0) == kCFCompareLessThan;
    });

    return SkUniqueCFRef<CFArrayRef>(
        CFArrayCreate(kCFAllocatorDefault, familyNames.get(), count, &kCFTypeArrayCallBacks));
}
```

### 字符回退匹配

使用 CoreText 的 `CTFontCreateForStringWithLanguage` 实现智能回退：

```cpp
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(
        const char familyName[], const SkFontStyle& style,
        const char* bcp47[], int bcp47Count, SkUnichar character) const override {
    // 1. 创建基础字体
    SkUniqueCFRef<CTFontDescriptorRef> desc = create_descriptor(familyName, style);
    SkUniqueCFRef<CTFontRef> familyFont(CTFontCreateWithFontDescriptor(desc.get(), 0, nullptr));

    // 2. 准备字符串（UTF-32）
    SkUniqueCFRef<CFStringRef> string(CFStringCreateWithBytes(
        kCFAllocatorDefault, reinterpret_cast<const UInt8*>(&character), sizeof(character),
        encoding, false));

    // 3. 准备语言标签
    const char* locale = bcp47Count ? bcp47[0] : "";
    SkUniqueCFRef<CFStringRef> cfLocale(CFStringCreateWithCString(..., locale, ...));

    // 4. 执行回退查询
    SkUniqueCFRef<CTFontRef> fallbackFont(CTFontCreateForStringWithLanguage(
        familyFont.get(), string.get(), range, cfLocale.get()));

    // 5. 验证字体包含字符
    if (!fallbackFont || !has_character(fallbackFont.get(), character)) {
        return nullptr;
    }

    // 6. 尝试样式匹配优化
    SkUniqueCFRef<CFStringRef> fallbackFamilyName(CTFontCopyFamilyName(fallbackFont.get()));
    if (fallbackFamilyName &&
        CFStringGetLength(fallbackFamilyName.get()) > 0 &&
        CFStringGetCharacterAtIndex(fallbackFamilyName.get(), 0) != '.')  // 跳过系统内部字体
    {
        SkUniqueCFRef<CTFontDescriptorRef> styledFallbackDesc =
            create_descriptor(fallbackFamilyName.get(), style);
        SkUniqueCFRef<CTFontRef> styledFallbackFont(
            CTFontCreateWithFontDescriptor(styledFallbackDesc.get(), 0, nullptr));
        if (styledFallbackFont && has_character(styledFallbackFont.get(), character)) {
            fallbackFont = std::move(styledFallbackFont);  // 使用更好的样式匹配
        }
    }

    return SkTypeface_Mac::Make(std::move(fallbackFont), OpszVariation(), nullptr);
}
```

字符检测辅助函数：

```cpp
static bool has_character(CTFontRef ctFont, SkUnichar character) {
    UniChar utf16[2] = {};  // UniChar 是 UTF-16 16 位码元
    CGGlyph glyph[2] = {};
    int srcCount = SkUTF::ToUTF16(character, utf16);  // 转换 Unicode 码点到 UTF-16
    return CTFontGetGlyphsForCharacters(ctFont, utf16, glyph, srcCount);
}
```

### 样式集合实现

```cpp
class SkFontStyleSet_Mac : public SkFontStyleSet {
public:
    SkFontStyleSet_Mac(CTFontDescriptorRef desc)
        : fArray(CTFontDescriptorCreateMatchingFontDescriptors(desc, name_required().get()))
        , fCount(0)
    {
        if (!fArray) {
            fArray.reset(CFArrayCreate(nullptr, nullptr, 0, nullptr));  // 空数组
        }
        fCount = SkToInt(CFArrayGetCount(fArray.get()));
    }

    int count() override { return fCount; }

    void getStyle(int index, SkFontStyle* style, SkString* name) override {
        CTFontDescriptorRef desc = (CTFontDescriptorRef)CFArrayGetValueAtIndex(fArray.get(), index);
        if (style) {
            *style = SkCTFontDescriptorGetSkFontStyle(desc, false);
        }
        if (name) {
            find_desc_str(desc, kCTFontStyleNameAttribute, name);  // 提取样式名称
        }
    }

    sk_sp<SkTypeface> matchStyle(const SkFontStyle& pattern) override {
        // CSS3 风格匹配
        return matchStyleCSS3(pattern);
    }

private:
    CTFontDescriptorRef findMatchingDesc(const SkFontStyle& pattern) const {
        // 计算距离度量，找到最佳匹配
        int bestMetric = SK_MaxS32;
        CTFontDescriptorRef bestDesc = nullptr;

        for (int i = 0; i < fCount; ++i) {
            CTFontDescriptorRef desc = (CTFontDescriptorRef)CFArrayGetValueAtIndex(fArray.get(), i);
            int metric = compute_metric(pattern, SkCTFontDescriptorGetSkFontStyle(desc, false));
            if (0 == metric) {
                return desc;  // 精确匹配
            }
            if (metric < bestMetric) {
                bestMetric = metric;
                bestDesc = desc;
            }
        }
        return bestDesc;
    }
};
```

距离度量计算：

```cpp
static int compute_metric(const SkFontStyle& a, const SkFontStyle& b) {
    // 归一化到基数 900，计算欧氏距离
    return sqr(a.weight() - b.weight()) +
           sqr((a.width() - b.width()) * 100) +
           sqr((a.slant() != b.slant()) * 900);
}
```

### 默认字体回退

```cpp
sk_sp<SkTypeface> onLegacyMakeTypeface(const char familyName[], SkFontStyle style) const override {
    if (familyName) {
        familyName = map_css_names(familyName);  // CSS 通用家族映射
    }

    sk_sp<SkTypeface> face = create_from_name(familyName, style);
    if (face) {
        return face;
    }

    // 回退到 Lucida Sans
    static SkTypeface* gDefaultFace;
    static SkOnce lookupDefault;
    static const char FONT_DEFAULT_NAME[] = "Lucida Sans";
    lookupDefault([]{
        gDefaultFace = create_from_name(FONT_DEFAULT_NAME, SkFontStyle()).release();
    });
    return sk_ref_sp(gDefaultFace);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| CoreText (macOS/iOS) | 字体查询和创建 |
| CoreFoundation | CF 对象管理 |
| CoreGraphics (iOS) | 图形基础设施 |
| `SkTypeface_Mac` | CoreText typeface 实现 |
| `SkUniqueCFRef` | CF 对象 RAII 包装 |
| `SkUTF` | Unicode 转换 |

### 被依赖的模块

该模块通过工厂函数被上层字体管理系统使用，在 macOS 和 iOS 平台上作为默认字体管理器。

## 设计模式与设计决策

### 设计模式

1. **工厂模式**: `SkFontMgr_New_CoreText` 工厂函数
2. **适配器模式**: 将 CoreText API 适配到 Skia 接口
3. **RAII**: `SkUniqueCFRef` 自动管理 CF 对象生命周期
4. **策略模式**: CSS3 样式匹配策略
5. **单例模式**: 默认字体使用线程安全的单例

### 设计决策

1. **CoreText 原生**: 直接使用系统字体服务，无需字体文件路径
2. **符号特征修复**: 显式处理 macOS 10.11 的字体创建 bug
3. **样式匹配精度**: 使用 WebKit 的斜率值（0.07）确保一致性
4. **CSS 兼容**: 支持常用 CSS 通用家族名称
5. **回退优化**: 字符回退后尝试样式重新匹配，提高视觉一致性
6. **iOS 动态链接**: 运行时检测 API 可用性，兼容老设备
7. **集合驱动**: 支持自定义字体集合，方便测试和隔离

### 平台特性利用

- **CTFontDescriptor**: 声明式字体查询
- **CTFontCollection**: 高效的字体集合管理
- **CTFontCreateForStringWithLanguage**: 智能语言感知回退
- **符号特征**: 快速粗体和斜体样式应用

## 性能考量

### 性能优势

1. **系统缓存**: CoreText 维护系统级字体缓存
2. **懒加载**: 字体数据仅在需要时加载
3. **家族名称缓存**: 启动时枚举一次，避免重复查询
4. **描述符匹配**: CoreText 优化的匹配算法

### 内存优化

- **CF 对象引用计数**: 自动内存管理
- **共享字体集合**: 多个管理器可共享 CTFontCollection
- **按需创建**: 样式集合和 typeface 延迟创建

### 潜在瓶颈

1. **家族枚举**: 首次枚举涉及所有系统字体，iOS 回退实现更慢
2. **字符回退**: `CTFontCreateForStringWithLanguage` 可能触发复杂查询
3. **样式重新匹配**: 回退字体的二次样式匹配有额外开销
4. **符号特征重建**: macOS 10.11 上的兼容代码需要重新创建字体

### 优化建议

- 避免频繁枚举字体家族
- 缓存常用字符的回退结果
- 在主线程外执行字体查询（CoreText 线程安全）

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_mac_ct.h` | 公共接口定义 |
| `src/ports/SkFontMgr_mac_ct.cpp` | 实现文件（561 行）|
| `src/ports/SkTypeface_mac_ct.h` | CoreText typeface 实现 |
| `src/utils/mac/SkUniqueCFRef.h` | CF 对象 RAII 包装 |
| `src/base/SkUTF.h` | Unicode 转换工具 |
| `include/core/SkFontMgr.h` | 字体管理器抽象基类 |
| `include/core/SkFontStyle.h` | 字体样式描述 |
| Apple CoreText API | 系统字体管理框架 |
