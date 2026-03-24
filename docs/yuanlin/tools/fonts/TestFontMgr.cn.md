# TestFontMgr

> 源文件：tools/fonts/TestFontMgr.h, tools/fonts/TestFontMgr.cpp

## 概述

TestFontMgr 是 Skia 的便携字体管理器实现，专门用于测试和示例。该模块提供了完全由代码生成的字体集，确保在所有平台上产生完全一致的文本渲染结果。这对于回归测试、Golden Master 比较和跨平台一致性验证至关重要。

主要特性：
- 完全便携（无需系统字体）
- 跨平台一致的字形和度量
- 包含多种字体家族（Monospace、Sans-serif、Serif 等）
- 支持 SVG 表情符号字体（条件编译）
- 不支持从文件加载（仅使用内置字体）

该实现使用 TestTypeface 模块提供的代码生成字体，完全绕过了系统字体子系统。

## 架构位置

- **接口**：实现 SkFontMgr 抽象类
- **使用**：TestTypeface（字体定义）、TestSVGTypeface（SVG 字体）
- **调用者**：FontToolUtils::TestFontMgr()
- **用途**：测试、GM、便携示例

## 主要类与结构体

### FontStyleSet

```cpp
class FontStyleSet final : public SkFontStyleSet {
    struct TypefaceEntry {
        sk_sp<SkTypeface> fTypeface;
        SkFontStyle fStyle;
        const char* fStyleName;
    };

    int count() override;
    void getStyle(int index, SkFontStyle* style, SkString* name) override;
    sk_sp<SkTypeface> createTypeface(int index) override;
    sk_sp<SkTypeface> matchStyle(const SkFontStyle& pattern) override;

    std::vector<TypefaceEntry> fTypefaces;
    SkString fFamilyName;
};
```

表示单个字体家族的样式集合。

### FontMgr

```cpp
class FontMgr final : public SkFontMgr {
    int onCountFamilies() const override;
    void onGetFamilyName(int index, SkString* familyName) const override;
    sk_sp<SkFontStyleSet> onCreateStyleSet(int index) const override;
    sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override;
    sk_sp<SkTypeface> onMatchFamilyStyle(...) const override;
    sk_sp<SkTypeface> onMatchFamilyStyleCharacter(...) const override;
    sk_sp<SkTypeface> onLegacyMakeTypeface(...) const override;

    // 不支持的操作（返回 nullptr）
    sk_sp<SkTypeface> onMakeFromData(...) const override;
    sk_sp<SkTypeface> onMakeFromStreamIndex(...) const override;
    sk_sp<SkTypeface> onMakeFromStreamArgs(...) const override;
    sk_sp<SkTypeface> onMakeFromFile(...) const override;

private:
    std::vector<sk_sp<FontStyleSet>> fFamilies;
    sk_sp<FontStyleSet> fDefaultFamily;
    sk_sp<SkTypeface> fDefaultTypeface;
};
```

主字体管理器类，管理所有字体家族。

## 公共 API 函数

### MakePortableFontMgr

```cpp
sk_sp<SkFontMgr> MakePortableFontMgr();
```

创建便携字体管理器实例。这是模块唯一的公共工厂函数。

## 内部实现细节

### 初始化

FontMgr 构造函数从 TestTypeface 加载所有字体家族：

```cpp
FontMgr::FontMgr() {
    auto&& list = TestTypeface::Typefaces();
    for (auto&& family : list.families) {
        auto&& ss = fFamilies.emplace_back(sk_make_sp<FontStyleSet>(family.name));
        for (auto&& face : family.faces) {
            ss->fTypefaces.emplace_back(face.typeface, face.typeface->fontStyle(), face.name);
            if (face.isDefault) {
                fDefaultFamily = ss;
                fDefaultTypeface = face.typeface;
            }
        }
    }
    // 添加 SVG 表情符号字体（条件编译）
#if defined(SK_ENABLE_SVG)
    fFamilies.emplace_back(sk_make_sp<FontStyleSet>("Emoji"));
    fFamilies.back()->fTypefaces.emplace_back(
            TestSVGTypeface::Default(), SkFontStyle::Normal(), "Normal");
    fFamilies.emplace_back(sk_make_sp<FontStyleSet>("Planet"));
    fFamilies.back()->fTypefaces.emplace_back(
            TestSVGTypeface::Planets(), SkFontStyle::Normal(), "Normal");
#endif
}
```

### 家族匹配

`onMatchFamily` 使用部分字符串匹配：

```cpp
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override {
    if (familyName) {
        if (strstr(familyName, "ono")) {
            return this->createStyleSet(0);  // Monospace
        }
        if (strstr(familyName, "ans")) {
            return this->createStyleSet(1);  // Sans-serif
        }
        if (strstr(familyName, "erif")) {
            return this->createStyleSet(2);  // Serif
        }
#if defined(SK_ENABLE_SVG)
        if (strstr(familyName, "oji")) {
            return this->createStyleSet(6);  // Emoji
        }
        if (strstr(familyName, "Planet")) {
            return this->createStyleSet(7);  // Planet
        }
#endif
    }
    return nullptr;
}
```

这种模糊匹配允许 "Monospace"、"Monaco"、"Mono" 等名称都匹配到 Monospace 家族。

### 样式匹配

FontStyleSet 使用标准 CSS3 样式匹配算法：

```cpp
sk_sp<SkTypeface> matchStyle(const SkFontStyle& pattern) override {
    return this->matchStyleCSS3(pattern);
}
```

这是 SkFontStyleSet 基类提供的算法，根据权重、宽度和倾斜度计算最佳匹配。

### 字符匹配

`onMatchFamilyStyleCharacter` 忽略字符参数，简单回退到家族样式匹配：

```cpp
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(...) const override {
    (void)bcp47;
    (void)bcp47Count;
    (void)character;
    return this->matchFamilyStyle(familyName, style);
}
```

这简化了实现，因为便携字体已包含常用字符集。

### 默认字体

`onLegacyMakeTypeface` 实现传统字体查找：

```cpp
sk_sp<SkTypeface> onLegacyMakeTypeface(const char familyName[],
                                       SkFontStyle style) const override {
    if (familyName == nullptr) {
        return sk_sp<SkTypeface>(fDefaultFamily->matchStyle(style));
    }
    sk_sp<SkTypeface> typeface = sk_sp<SkTypeface>(this->matchFamilyStyle(familyName, style));
    if (!typeface) {
        typeface = fDefaultTypeface;
    }
    return typeface;
}
```

无家族名时返回默认家族的匹配样式，匹配失败时回退到默认字体。

### 不支持的操作

所有文件/流加载操作返回 nullptr：

```cpp
sk_sp<SkTypeface> onMakeFromData(...) const override { return nullptr; }
sk_sp<SkTypeface> onMakeFromStreamIndex(...) const override { return nullptr; }
sk_sp<SkTypeface> onMakeFromStreamArgs(...) const override { return nullptr; }
sk_sp<SkTypeface> onMakeFromFile(...) const override { return nullptr; }
```

这强制所有字体使用内置的便携字体。

## 依赖关系

### Skia 核心
- `include/core/SkFontMgr.h` - 字体管理器接口
- `include/core/SkFontStyle.h` - 字体样式
- `include/core/SkTypeface.h` - 字体面

### 便携字体
- `tools/fonts/TestTypeface.h` - 代码生成字体定义
- `tools/fonts/TestSVGTypeface.h` - SVG 表情符号字体（条件编译）

### 工具
- `tools/ToolUtils.h` - 通用工具
- `include/utils/SkCustomTypeface.h` - 自定义字体 API

## 设计模式与设计决策

### 工厂模式
`MakePortableFontMgr` 是工厂函数，创建配置好的字体管理器。

### 注册表模式
字体家族存储在向量中，通过索引或名称访问。

### 策略模式
CSS3 样式匹配作为可替换策略。

### 空对象模式
不支持的操作返回 nullptr 而非抛出异常。

### 模糊匹配
使用 `strstr` 实现宽松的家族名匹配，提高兼容性。

### 条件编译
SVG 字体仅在 `SK_ENABLE_SVG` 定义时包含，减少非必要依赖。

## 性能考量

- 所有字体在构造时预加载
- 无延迟加载或按需生成
- 字符匹配忽略实际字符（简化但可能不精确）
- 向量查找（O(n)）对于小家族集合足够快

## 相关文件

### 字体定义
- `tools/fonts/TestTypeface.h/cpp` - 便携字体实现
- `tools/fonts/TestSVGTypeface.h/cpp` - SVG 表情符号字体

### 使用者
- `tools/fonts/FontToolUtils.h/cpp` - 主要使用者
- GM 和测试代码

### Skia 核心
- `include/core/SkFontMgr.h` - 字体管理器接口
- `include/core/SkFontStyleSet.h` - 样式集接口
- `include/core/SkTypeface.h` - 字体面接口
