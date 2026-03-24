# ParagraphSlide

> 源文件: modules/skparagraph/slides/ParagraphSlide.cpp

## 概述

`ParagraphSlide.cpp` 是 Skia 段落模块的综合测试和演示套件,包含超过 60 个独立的视觉测试用例,用于验证段落布局引擎的各种功能。该文件是 Skia viewer 工具的一部分,提供交互式演示界面,展示文本渲染、样式应用、多语言支持、文本对齐、换行、省略号、装饰线、阴影效果等功能。它是段落模块最重要的集成测试和功能展示文件,涵盖了从基本文本渲染到复杂的双向文本、emoji 序列、字体回退等高级场景。

## 架构位置

`ParagraphSlide.cpp` 位于段落模块的 `slides` 目录,作为 Skia 的可视化测试框架的一部分:

```
Skia 架构
├── tools/viewer (查看器工具)
│   └── Slide 框架 (幻灯片基础设施)
├── modules/skparagraph (段落模块)
│   ├── include/ (公共 API)
│   ├── src/ (核心实现)
│   │   ├── ParagraphImpl
│   │   ├── ParagraphBuilderImpl
│   │   ├── TextLine
│   │   └── Run
│   ├── utils/ (测试工具)
│   │   └── TestFontCollection
│   └── slides/
│       └── ParagraphSlide.cpp (本文件)
```

该文件通过 Skia viewer 框架与用户交互,使用段落模块的所有公共和内部 API 来创建各种测试场景。它依赖于 `TestFontCollection` 来加载测试字体,并使用 `ParagraphBuilderImpl` 来构建段落实例。

## 主要类与结构体

### ParagraphSlide_Base

```cpp
class ParagraphSlide_Base : public ClickHandlerSlide {
public:
    void load(SkScalar w, SkScalar h) override;
    void resize(SkScalar w, SkScalar h) override;
protected:
    sk_sp<TestFontCollection> getFontCollection();
    bool isVerbose();
    SkSize size() const;
private:
    SkSize fSize;
};
```

所有段落幻灯片的基类,提供通用功能:
- **size() 管理**: 跟踪画布尺寸,支持响应式布局
- **getFontCollection()**: 提供统一的字体集合访问,确保所有测试使用相同的字体资源
- **isVerbose()**: 控制调试输出级别

### 代表性幻灯片类

该文件包含 60+ 个幻灯片类,每个测试一个特定场景:

#### ParagraphSlide1
测试基本文本样式,包括字体族、粗细、斜体、字号、前景色、背景色、阴影和装饰线的各种组合。

#### ParagraphSlide2
测试文本换行和省略号,包括长单词、连字符单词、多行文本等边界情况。

#### ParagraphSlide3
测试文本对齐(左对齐、右对齐、居中、两端对齐)和方向(LTR/RTL)的组合。

#### ParagraphSlide_MultiStyle_Arabic1/Arabic2
测试阿拉伯文本的复杂排版,包括右到左文本方向和变音符号(diacritics)的正确渲染。

#### ParagraphSlideMixedTextDirection
测试混合文本方向场景,在同一段落中包含 LTR 和 RTL 文本。

#### ParagraphSlideGetPath
演示如何从段落中提取文本路径,用于自定义渲染效果(如渐变填充)。

#### ParagraphSlideEmojiSequence
测试 emoji 序列的正确处理,包括组合 emoji 和修饰符序列。

#### ParagraphSlideWordSpacing
测试单词间距调整在不同语言和文本方向中的效果。

## 公共 API 函数

### 辅助函数

#### get_unicode()
```cpp
static sk_sp<SkUnicode> get_unicode();
```
获取 Unicode 处理器实例,用于文本分段和断行。所有段落构建器都需要此实例来正确处理 Unicode 语义。

#### setgrad()
```cpp
sk_sp<SkShader> setgrad(const SkRect& r, SkColor c0, SkColor c1);
```
创建线性渐变着色器,从左到右在指定矩形内从 `c0` 渐变到 `c1`。用于创建视觉效果丰富的背景和文本填充。

### Slide 实现方法

每个幻灯片类都实现以下方法:

#### draw()
```cpp
void draw(SkCanvas* canvas) override;
```
幻灯片的主渲染方法,在给定画布上绘制测试场景。这是每个测试用例的核心逻辑所在。

#### load() / resize()
```cpp
void load(SkScalar w, SkScalar h) override;
void resize(SkScalar w, SkScalar h) override;
```
处理窗口大小变化,更新内部尺寸状态。

## 内部实现细节

### 测试模式

文件使用一致的测试模式:
1. **设置字体集合**: 调用 `getFontCollection()` 或创建自定义 `FontCollection`
2. **配置样式**: 创建 `TextStyle` 和 `ParagraphStyle` 对象
3. **构建段落**: 使用 `ParagraphBuilderImpl` 添加文本和样式
4. **布局**: 调用 `paragraph->layout(width)` 计算行分割
5. **渲染**: 调用 `paragraph->paint(canvas, x, y)` 绘制到画布
6. **验证**: 可选地使用 `extendedVisit()` 或其他 API 检查内部状态

### 字体加载策略

字体通过 `TestFontCollection` 加载,它会扫描资源目录中的字体文件:
```cpp
sk_sp<TestFontCollection> getFontCollection() {
    static sk_sp<TestFontCollection> fFC = nullptr;
    if (fFC == nullptr) {
        fFC = sk_make_sp<TestFontCollection>(GetResourcePath("fonts").c_str(), false, true);
    }
    return fFC;
}
```
使用单例模式确保字体只加载一次,提高性能。

### 多语言测试

文件包含大量多语言文本样本:
- **英文**: 基本拉丁字符,用于测试基础排版
- **中文**: 测试 CJK 字符的断行和字体回退
- **阿拉伯文**: 测试 RTL 方向和连写(cursive joining)
- **希伯来文**: 测试另一种 RTL 书写系统
- **Emoji**: 测试 Unicode emoji 序列和修饰符

### 样式组合测试

许多幻灯片测试样式属性的各种组合:
```cpp
const std::vector<std::tuple<std::string, bool, bool, int, SkColor, SkColor, bool, TextDecorationStyle>>
    gParagraph = {
        {"monospace", true, false, 14, SK_ColorWHITE, SK_ColorRED, true, TextDecorationStyle::kDashed},
        {"Assyrian", false, false, 20, SK_ColorWHITE, SK_ColorBLUE, false, TextDecorationStyle::kDotted},
        // ... 更多组合
    };
```
这种数据驱动的方法确保全面覆盖各种样式组合。

### 边界情况测试

文件特别关注边界情况:
- **超长单词**: 测试没有断点的长单词的处理
- **空白字符**: 测试尾随空格、换行符的处理
- **零宽字符**: 测试零宽连接符(ZWJ)等特殊字符
- **组合字符**: 测试变音符号和其他组合标记

### 调试支持

使用命令行标志控制详细输出:
```cpp
static DEFINE_bool(verboseParagraph, false, "paragraph samples very verbose.");
```
启用时,可以输出段落内部结构(如 run 分割、字体选择)等调试信息。

## 依赖关系

### Skia 核心依赖

- **SkCanvas**: 渲染目标,所有绘制操作的接口
- **SkPaint**: 绘制属性(颜色、抗锯齿等)
- **SkTypeface / SkFontMgr**: 字体管理
- **SkShader**: 高级填充效果(如渐变)
- **SkPath**: 用于文本路径提取测试

### 段落模块依赖

- **Paragraph / ParagraphBuilder**: 段落 API 的核心接口
- **ParagraphImpl / ParagraphBuilderImpl**: 内部实现类,用于访问内部状态
- **TextStyle / ParagraphStyle**: 样式配置类
- **TextLine / Run**: 内部排版数据结构
- **FontCollection / TypefaceFontProvider**: 字体管理
- **TestFontCollection**: 测试专用字体加载器

### 文本整形依赖

- **SkUnicode**: Unicode 处理(断行、分词等)
- **SkShaper**: 文本整形引擎(通过段落模块间接使用)

### 工具框架依赖

- **ClickHandlerSlide**: viewer 工具的幻灯片基类
- **Tools/Resources**: 资源文件访问
- **FontToolUtils**: 字体测试工具

## 设计模式与设计决策

### 模板方法模式

`ParagraphSlide_Base` 定义了幻灯片的通用结构,子类覆盖 `draw()` 方法实现具体测试逻辑。这确保所有测试遵循一致的生命周期和接口。

### 工厂模式

文件末尾使用宏 `DEF_SLIDE` 批量注册所有幻灯片:
```cpp
DEF_SLIDE(return new ParagraphSlide1();)
DEF_SLIDE(return new ParagraphSlide2();)
// ... 60+ 个幻灯片
```
这使得 viewer 工具能够自动发现和加载所有测试用例。

### 单例模式

字体集合使用单例模式,避免重复加载字体文件:
```cpp
static sk_sp<TestFontCollection> fFC = nullptr;
```
这是性能优化,因为字体加载是昂贵的操作。

### 数据驱动测试

许多测试使用参数化方法,通过数据结构驱动测试用例:
```cpp
auto draw = [&](const std::u16string& text, size_t lines, TextDirection dir) {
    // 通用测试逻辑
};
draw(u"Text 1", 1, TextDirection::kLtr);
draw(u"Text 2", 2, TextDirection::kRtl);
```
这减少了代码重复,提高了测试覆盖率。

### 设计决策

1. **分离测试场景**: 每个幻灯片专注于一个特定功能或边界情况,便于隔离问题和理解功能。

2. **可视化验证**: 作为视觉测试套件,依赖人工检查渲染结果,而非自动化断言。这对于排版质量评估很重要。

3. **内部 API 访问**: 许多测试使用内部实现类(如 `ParagraphImpl`),以便深入检查内部状态,这对于调试和验证算法正确性至关重要。

4. **真实文本样本**: 使用实际语言的真实文本样本而非占位符文本,确保测试反映真实使用场景。

## 性能考量

### 字体缓存

通过单例模式缓存 `TestFontCollection`,避免每次渲染时重新加载字体。这对于交互式查看器的流畅性至关重要。

### 延迟计算

段落布局只在 `layout()` 调用时计算,而非构建时。这允许段落在不同宽度下重用,是段落 API 的核心设计特性。

### 增量渲染

每个幻灯片独立渲染,不会影响其他幻灯片。viewer 工具只渲染当前可见的幻灯片,避免不必要的计算。

### 内存管理

所有 Skia 对象使用智能指针 (`sk_sp`) 管理,确保正确的生命周期管理。段落对象在幻灯片方法结束时自动释放。

### 性能敏感测试

文件不包含性能基准测试,专注于功能和视觉正确性。性能测试在单独的基准测试套件中进行。

## 相关文件

### 核心段落 API
- `modules/skparagraph/include/Paragraph.h`: 段落接口定义
- `modules/skparagraph/include/ParagraphBuilder.h`: 段落构建器接口
- `modules/skparagraph/include/TextStyle.h`: 文本样式定义
- `modules/skparagraph/include/ParagraphStyle.h`: 段落样式定义

### 内部实现
- `modules/skparagraph/src/ParagraphImpl.h/cpp`: 段落核心实现
- `modules/skparagraph/src/ParagraphBuilderImpl.h/cpp`: 构建器实现
- `modules/skparagraph/src/TextLine.h/cpp`: 文本行布局
- `modules/skparagraph/src/Run.h/cpp`: 排版运行单元

### 测试基础设施
- `modules/skparagraph/utils/TestFontCollection.h/cpp`: 测试字体加载器
- `tools/viewer/ClickHandlerSlide.h`: 幻灯片基类
- `tools/viewer/Viewer.cpp`: viewer 主应用程序

### 字体和整形
- `modules/skparagraph/include/FontCollection.h`: 字体集合管理
- `modules/skshaper/`: 文本整形模块
- `include/core/SkFontMgr.h`: Skia 字体管理器接口

### 单元测试
- `modules/skparagraph/tests/`: 自动化单元测试套件,与本文件的视觉测试互补

该文件是理解 Skia 段落模块功能和用法的最佳资源,提供了丰富的实际示例,涵盖从简单到复杂的各种文本排版场景。它既是功能测试,也是使用文档,也是调试工具。
