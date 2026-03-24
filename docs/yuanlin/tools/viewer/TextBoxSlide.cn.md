# TextBoxSlide

> 源文件: tools/viewer/TextBoxSlide.cpp

## 概述

`TextBoxSlide` 是 Skia Viewer 中用于演示和测试文本整形(text shaping)功能的幻灯片集合。它展示了不同文本整形引擎(Primitive, CoreText, HarfBuzz)在多语言文本布局、双向文本、复杂脚本渲染等方面的能力。该幻灯片将长段英文文本在不同背景色和前景色组合下以多种字体大小渲染,用于视觉比较不同整形器的效果。

## 架构位置

`TextBoxSlide` 位于 `tools/viewer` 目录,是文本渲染测试套件的一部分。它根据编译时可用的文本整形后端生成多个幻灯片实例。

```
tools/viewer/
├── Slide (基类)
├── TextBoxSlide (文本整形测试)
│   ├── Primitive Shaper (基础整形器)
│   ├── CoreText Shaper (macOS/iOS)
│   └── HarfBuzz Shaper (跨平台)
└── ShaperSlide (简单整形演示)
```

## 主要类与结构体

### 类型别名

```cpp
typedef std::unique_ptr<SkShaper> (*ShaperFactory)();

typedef std::unique_ptr<SkShaper::BiDiRunIterator> (*MakeBidiIteratorCallback)(
    sk_sp<SkUnicode> unicode,
    const char* utf8,
    size_t utf8Bytes,
    uint8_t bidiLevel);

typedef std::unique_ptr<SkShaper::ScriptRunIterator> (*MakeScriptRunCallback)(
    const char* utf8,
    size_t utf8Bytes,
    SkFourByteTag script);
```

### TextBoxSlide 类

```cpp
class TextBoxSlide : public Slide {
public:
    TextBoxSlide(ShaperFactory fact,
                 MakeBidiIteratorCallback bidi,
                 MakeScriptRunCallback script,
                 const char suffix[]);

    void load(SkScalar w, SkScalar h) override;
    void resize(SkScalar w, SkScalar h) override;
    void draw(SkCanvas* canvas) override;

private:
    void drawTest(SkCanvas* canvas, SkScalar w, SkScalar h,
                  SkColor fg, SkColor bg);

    SkSize fSize;
    std::unique_ptr<SkShaper> fShaper;
    MakeBidiIteratorCallback fBidiCallback;
    MakeScriptRunCallback fScriptRunCallback;
};
```

### ShaperSlide 类

简化版的整形器演示类,用于快速测试单个单词的整形效果。

## 公共 API 函数

### TextBoxSlide 构造函数

**TextBoxSlide(ShaperFactory fact, MakeBidiIteratorCallback bidi, MakeScriptRunCallback script, const char suffix[])**
- 使用工厂函数创建整形器实例
- 保存双向文本和脚本迭代器回调
- 设置幻灯片名称为 "TextBox_{suffix}"

### 生命周期函数

**void load(SkScalar w, SkScalar h)**
- 保存画布尺寸

**void resize(SkScalar w, SkScalar h)**
- 更新 `fSize` 成员变量

**void draw(SkCanvas* canvas)**
- 将画布分为 4 个区域,展示不同颜色组合:
  1. 左侧: 黑底白字
  2. 中间: 白底黑字
  3. 右上: 灰底白字
  4. 右下: 灰底黑字

### 内部函数

**void drawTest(SkCanvas* canvas, SkScalar w, SkScalar h, SkColor fg, SkColor bg)**
- 在指定区域绘制测试文本
- 使用多种字体大小(9pt 到 23pt,步长为 2)
- 应用文本整形和布局
- 使用 20 像素边距

## 内部实现细节

### 测试文本

使用《独立宣言》开头段落作为测试文本(约 391 字符):

```cpp
static const char gText[] =
    "When in the Course of human events it becomes necessary for one people "
    "to dissolve the political bands which have connected them with another "
    "and to assume among the powers of the earth, the separate and equal "
    "station to which the Laws of Nature and of Nature's God entitle them, "
    "a decent respect to the opinions of mankind requires that they should "
    "declare the causes which impel them to the separation.";
```

### 文本整形流程

```cpp
void drawTest(...) {
    for (int i = 9; i < 24; i += 2) {
        #if defined(SK_SHAPER_HARFBUZZ_AVAILABLE) && defined(SK_SHAPER_UNICODE_AVAILABLE)
        SkShapers::HB::PurgeCaches();
        #endif

        SkTextBlobBuilderRunHandler builder(gText, {margin, margin});
        SkFont srcFont(nullptr, SkIntToScalar(i));
        srcFont.setEdging(SkFont::Edging::kSubpixelAntiAlias);
        srcFont.setSubpixel(true);

        // 创建迭代器
        auto unicode = get_unicode();
        std::unique_ptr<SkShaper::BiDiRunIterator> bidi =
            fBidiCallback(unicode, utf8, utf8Bytes, 0xfe);
        std::unique_ptr<SkShaper::LanguageRunIterator> language =
            SkShaper::MakeStdLanguageRunIterator(utf8, utf8Bytes);
        std::unique_ptr<SkShaper::ScriptRunIterator> script =
            fScriptRunCallback(utf8, utf8Bytes, undeterminedScript);
        std::unique_ptr<SkShaper::FontRunIterator> font =
            SkShaper::MakeFontMgrRunIterator(utf8, utf8Bytes, srcFont,
                                            ToolUtils::TestFontMgr(),
                                            "Arial", SkFontStyle::Bold(),
                                            &*language);

        // 执行整形
        fShaper->shape(utf8, utf8Bytes, *font, *bidi, *script, *language,
                      nullptr, 0, w - margin, &builder);

        canvas->drawTextBlob(builder.makeBlob(), 0, 0, paint);
        canvas->translate(0, builder.endPoint().y());
    }
}
```

### Unicode 获取策略

```cpp
sk_sp<SkUnicode> get_unicode() {
#if defined(SK_UNICODE_ICU_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU::Make()) return unicode;
#endif
#if defined(SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::Libgrapheme::Make()) return unicode;
#endif
#if defined(SK_UNICODE_ICU4X_IMPLEMENTATION)
    if (auto unicode = SkUnicodes::ICU4X::Make()) return unicode;
#endif
    return nullptr;
}
```

优先使用 ICU,回退到其他实现。

### 整形器工厂

**Primitive Shaper**:
```cpp
DEF_SLIDE(return new TextBoxSlide(SkShapers::Primitive::PrimitiveText,
                                  make_trivial_bidi,
                                  make_trivial_script_runner,
                                  "primitive");)
```

**CoreText Shaper** (macOS/iOS):
```cpp
#if defined(SK_SHAPER_CORETEXT_AVAILABLE)
DEF_SLIDE(return new TextBoxSlide(SkShapers::CT::CoreText,
                                  make_trivial_bidi,
                                  make_trivial_script_runner,
                                  "coretext");)
#endif
```

**HarfBuzz Shaper**:
```cpp
#if defined(SK_SHAPER_HARFBUZZ_AVAILABLE) && defined(SK_SHAPER_UNICODE_AVAILABLE)
DEF_SLIDE(return new TextBoxSlide(
    []() {
        return SkShapers::HB::ShaperDrivenWrapper(get_unicode(),
                                                  SkFontMgr::RefEmpty());
    },
    make_unicode_bidi,
    make_harfbuzz_script_runner,
    "harfbuzz");)
#endif
```

## 依赖关系

### 核心依赖

- **SkShaper**: 文本整形核心接口
- **SkUnicode**: Unicode 处理(ICU/Libgrapheme/ICU4X)
- **SkFontMgr**: 字体管理
- **SkTextBlob**: 文本块表示

### 条件编译依赖

- `SK_SHAPER_CORETEXT_AVAILABLE`: CoreText 支持
- `SK_SHAPER_HARFBUZZ_AVAILABLE`: HarfBuzz 支持
- `SK_SHAPER_UNICODE_AVAILABLE`: Unicode 迭代器支持
- `SK_UNICODE_ICU_IMPLEMENTATION`: ICU Unicode
- `SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION`: Libgrapheme
- `SK_UNICODE_ICU4X_IMPLEMENTATION`: ICU4X

## 设计模式与设计决策

### 设计模式

1. **Strategy Pattern**: 通过回调函数参数化双向文本和脚本检测策略
2. **Factory Pattern**: 使用工厂函数创建不同类型的整形器
3. **Iterator Pattern**: 使用 BiDi, Script, Language, Font 迭代器遍历文本
4. **Builder Pattern**: `SkTextBlobBuilderRunHandler` 构建文本块

### 设计决策

1. **多引擎对比**: 生成多个幻灯片实例,便于并排比较
2. **多尺寸测试**: 9-23pt 范围覆盖常见字体大小
3. **亚像素渲染**: 启用 subpixel antialiasing,测试文本清晰度
4. **缓存清理**: HarfBuzz 整形前清除缓存,确保测量准确性
5. **回退机制**: Unicode 实现按优先级尝试,保证兼容性
6. **固定字体**: 使用 Arial Bold,避免字体变化影响比较

## 性能考量

1. **重复整形**: 每帧重新整形文本,开销较大(测试场景可接受)
2. **HarfBuzz 缓存**: 生产环境应保留缓存,显著提升性能
3. **迭代器创建**: 每次整形创建 4 个迭代器对象,有分配开销
4. **文本长度**: 391 字符的文本整形耗时约 1-5ms(取决于整形器)
5. **字体回退**: 字体管理器查找可能触发文件系统访问

## 相关文件

- **modules/skshaper/include/SkShaper.h**: 整形器接口
- **modules/skunicode/include/SkUnicode.h**: Unicode 处理接口
- **modules/skshaper/include/SkShaper_harfbuzz.h**: HarfBuzz 整形器
- **modules/skshaper/include/SkShaper_coretext.h**: CoreText 整形器
- **modules/skshaper/include/SkShaper_skunicode.h**: Unicode 整形辅助
- **include/core/SkTextBlob.h**: 文本块定义
- **tools/fonts/FontToolUtils.h**: 测试字体管理器
