# shape_text.cpp - 段落文本排版示例

> 源文件: `example/external_client/src/shape_text.cpp`

## 概述

`shape_text.cpp` 是一个综合性的示例程序，演示了如何使用 Skia 的 skparagraph 模块进行高级文本排版（text shaping）和段落布局。与简单的 `drawString` 不同，skparagraph 提供了完整的段落级文本排版功能，包括自动换行、文本对齐、字体回退和 Unicode 支持。

该示例还展示了如何创建自定义的 `SkFontMgr`（`OneFontMgr`），将单个字体文件包装为完整的字体管理器，适用于嵌入式场景或资源受限的环境。

## 架构位置

```
Skia 示例程序
├── example/external_client/src/
│   ├── shape_text.cpp          <-- 本文件：段落排版示例
│   ├── write_text_to_png.cpp   <-- 简单文本渲染示例
│   └── ...
├── modules/skparagraph/         <-- 段落排版模块
│   └── include/
│       ├── Paragraph.h
│       ├── ParagraphBuilder.h
│       └── ParagraphStyle.h
├── modules/skunicode/           <-- Unicode 支持模块
└── include/ports/
    └── SkFontMgr_empty.h       <-- 空字体管理器
```

## 主要类与结构体

### `OneFontStyleSet`
自定义字体样式集，封装单个字体面，对所有样式查询返回同一字体。

```cpp
class OneFontStyleSet : public SkFontStyleSet {
protected:
    int count() override { return 1; }
    void getStyle(int, SkFontStyle* out_style, SkString*) override;
    sk_sp<SkTypeface> createTypeface(int index) override { return face_; }
    sk_sp<SkTypeface> matchStyle(const SkFontStyle&) override { return face_; }
private:
    sk_sp<SkTypeface> face_;
};
```

### `OneFontMgr`
自定义字体管理器，仅包含一个字体。对所有字体查询（按名称、按样式、按字符）都返回同一字体。

```cpp
class OneFontMgr : public SkFontMgr {
protected:
    int onCountFamilies() const override { return 1; }
    void onGetFamilyName(int, SkString*) const override;
    sk_sp<SkFontStyleSet> onCreateStyleSet(int) const override;
    sk_sp<SkTypeface> onMatchFamilyStyle(const char[], const SkFontStyle&) const override;
    sk_sp<SkTypeface> onMatchFamilyStyleCharacter(...) const override;
    // onMakeFrom* 方法调用 std::abort()，因为不支持动态字体加载
};
```

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口。用法：`shape_text <font.ttf> <name.jpg>`

参数：
- `<font.ttf>`: 字体文件路径
- `<name.jpg>`: 输出 JPEG 文件路径

执行流程：
1. 从文件加载字体
2. 创建自定义单字体管理器
3. 配置 FontCollection
4. 创建 200x200 像素的光栅 Surface
5. 配置文本样式和段落样式
6. 使用 ParagraphBuilder 构建段落
7. 执行布局并渲染到 Canvas
8. 编码为 JPEG 输出

## 内部实现细节

### 字体加载和包装

```cpp
sk_sp<SkData> font_data = SkData::MakeFromStream(&input, input.getLength());
sk_sp<SkFontMgr> mgr = SkFontMgr_New_Custom_Empty();
sk_sp<SkTypeface> face = mgr->makeFromData(font_data);

// 包装为自定义字体管理器
sk_sp<SkFontMgr> one_mgr = sk_make_sp<OneFontMgr>(face);
fontCollection->setDefaultFontManager(one_mgr);
```

使用空的自定义字体管理器（`SkFontMgr_New_Custom_Empty`）来解析字体文件，然后将解析后的字体包装到 `OneFontMgr` 中，作为 FontCollection 的默认字体管理器。

### 段落构建和布局

```cpp
skia::textlayout::TextStyle style;
style.setForegroundColor(paint);
style.setFontFamilies({SkString("sans-serif")});
style.setFontSize(10.5);

skia::textlayout::ParagraphStyle paraStyle;
paraStyle.setTextStyle(style);
paraStyle.setTextAlign(skia::textlayout::TextAlign::kRight);

auto builder = ParagraphBuilder::make(paraStyle, fontCollection, unicode);
builder->addText(story);

auto paragraph = builder->Build();
paragraph->layout(width - 20);  // 布局宽度 = 200 - 20 = 180px
paragraph->paint(canvas, 10, 10);  // 绘制位置 (10, 10)
```

### Unicode 支持

```cpp
sk_sp<SkUnicode> unicode = SkUnicodes::ICU::Make();
```

使用 ICU（International Components for Unicode）库提供 Unicode 处理能力，这对于正确的文本换行（word breaking）和双向文本（BiDi）至关重要。

### 测试文本

使用来自 Project Gutenberg (#72339) 的科幻小说片段作为测试文本，包含多个段落，能够充分测试换行和对齐算法。

### OneFontMgr 的防御性设计

```cpp
sk_sp<SkTypeface> onMakeFromData(sk_sp<SkData>, int) const override {
    std::abort();  // 不应该被调用
    return nullptr;
}
```

动态字体加载方法（`onMakeFromData`、`onMakeFromStreamIndex` 等）调用 `std::abort()`，因为 `OneFontMgr` 仅设计为包装已有字体，不支持运行时加载新字体。

## 依赖关系

- **Skia 核心**：`SkCanvas`, `SkSurface`, `SkFont`, `SkTypeface`, `SkFontMgr`, `SkData`, `SkStream`
- **skparagraph 模块**：`Paragraph`, `ParagraphBuilder`, `ParagraphStyle`, `TextStyle`, `DartTypes`, `FontCollection`
- **skunicode 模块**：`SkUnicode_icu`
- **字体端口**：`SkFontMgr_empty.h`
- **编码器**：`SkJpegEncoder`
- **外部库**（运行时）：ICU 库

## 设计模式与设计决策

1. **适配器模式**：`OneFontMgr` 和 `OneFontStyleSet` 将单个字体适配为 `SkFontMgr` 接口，使得 skparagraph 的 FontCollection 可以正常使用。

2. **Builder 模式**：`ParagraphBuilder` 提供了流式 API 来构建复杂的段落，支持混合样式和多段文本。

3. **组合优于继承**：`OneFontMgr` 虽然继承了 `SkFontMgr`，但其核心是组合了一个 `SkTypeface` 和一个 `OneFontStyleSet`。

4. **Fail-fast 设计**：`OneFontMgr` 中不支持的方法直接 `std::abort()`，确保非法使用立即被发现。

5. **从文件加载而非系统字体**：示例从指定的 TTF 文件加载字体，使其在没有系统字体的环境（如 Docker 容器）中也能工作。

## 性能考量

- **ICU 初始化**：`SkUnicodes::ICU::Make()` 需要加载 ICU 数据（可能有几 MB），是主要的一次性开销。
- **段落布局**：`paragraph->layout(width)` 执行复杂的文本排版算法（包括换行、双向文本处理等），对于长文本可能需要数毫秒。
- **字体解析**：`mgr->makeFromData(font_data)` 解析字体文件结构，对于大型字体文件（如 CJK 字体）可能需要显著时间。
- **JPEG 编码**：使用 JPEG 而非 PNG 编码，编码速度更快且文件更小，但有损压缩。
- **单字体回退**：`OneFontMgr` 对所有字符查询都返回同一字体，如果文本包含该字体不支持的字符（如 CJK），将显示为缺失字形。

## 相关文件

- `modules/skparagraph/include/Paragraph.h` - 段落类
- `modules/skparagraph/include/ParagraphBuilder.h` - 段落构建器
- `modules/skparagraph/include/ParagraphStyle.h` - 段落样式
- `modules/skparagraph/include/FontCollection.h` - 字体集合
- `modules/skunicode/include/SkUnicode_icu.h` - ICU Unicode 实现
- `include/ports/SkFontMgr_empty.h` - 空字体管理器
- `include/encode/SkJpegEncoder.h` - JPEG 编码器
- `example/external_client/src/write_text_to_png.cpp` - 简单文本渲染示例
