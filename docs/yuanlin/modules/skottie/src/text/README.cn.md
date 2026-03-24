# skottie/src/text - 文本系统

## 概述

`text/` 目录实现了 Skottie 的完整文本处理管线,包括字体加载、文本排版 (Shaping)、文本动画和 Unicode 处理。文本图层是 Lottie 动画中功能最丰富也最复杂的图层类型之一,Skottie 通过 `TextAdapter` 将 Lottie 的文本属性转换为由多个 sksg 节点组成的渲染子树。

文本系统支持 After Effects 的文本动画器 (Text Animator) 特性,允许对每个字符、单词或行应用独立的位移、缩放、旋转、颜色和不透明度变化。范围选择器 (Range Selector) 控制动画器的作用范围和衰减曲线。

## 目录结构

```
text/
├── BUILD.bazel            # Bazel 构建配置
├── TextAdapter.h          # TextAdapter 类声明
├── TextAdapter.cpp        # TextAdapter 实现 (核心)
├── TextAnimator.h         # TextAnimator 和 DomainMaps 声明
├── TextAnimator.cpp       # TextAnimator 实现
├── TextValue.h            # TextValue 类型定义
├── TextValue.cpp          # TextValue 实现
├── TextShaper.cpp         # Shaper::Shape() 实现 (文本排版)
├── RangeSelector.h        # RangeSelector 声明
├── RangeSelector.cpp      # RangeSelector 实现
├── Font.h                 # CustomFont, GlyphCompMapper
├── Font.cpp               # 自定义字体实现 (字形路径/合成)
└── Unicode.cpp            # MakeStrictLinebreakUnicode 实现
```

## 关键类与函数

### TextAdapter - 文本图层核心适配器

```cpp
class TextAdapter final : public AnimatablePropertyContainer {
    static sk_sp<TextAdapter> Make(jobj, abuilder, fontMgr,
                                   glyphMapper, logger, shapingFactory);

    const sk_sp<sksg::Group>& node() const;  // 场景图根节点

    const TextValue& getText() const;
    void setText(const TextValue&);           // 运行时修改文本

protected:
    void onSync() override;  // 同步: reshape -> 生成片段 -> 推送属性
};
```

**TextAdapter 工作流程:**
1. `onSync()` 检测文本值变化
2. 若变化,调用 `reshape()` 重新排版
3. `Shaper::Shape()` 生成 `Shaper::Result` (片段列表)
4. `buildDomainMaps()` 构建字符/单词/行域映射
5. `addFragment()` 为每个片段创建 sksg 子树
6. 遍历片段,应用 `TextAnimator` 属性调制

### TextAnimator - 文本动画器

```cpp
class TextAnimator final : public SkNVRefCnt<TextAnimator> {
    // AE 动画属性 (直接映射)
    struct AnimatedProps {
        VectorValue position, scale;
        ColorValue  fill_color, stroke_color;
        SkV3        rotation;
        Vec2Value   blur, line_spacing;
        ScalarValue opacity, fill_opacity, stroke_opacity, tracking, stroke_width;
    };

    // 已解析属性 (适用于渲染)
    struct ResolvedProps {
        SkV3   position, scale, rotation;
        float  opacity, tracking, stroke_width;
        SkColor fill_color, stroke_color;
        SkV2   blur, line_spacing;
    };

    // 域映射: 索引域 -> 片段子集
    struct DomainSpan { size_t fOffset, fCount; float fAdvance, fAscent; };
    struct DomainMaps {
        DomainMap fNonWhitespaceMap, fWordsMap, fLinesMap;
    };

    // 属性调制: 根据范围选择器覆盖度调制属性
    void modulateProps(const DomainMaps&, ModulatorBuffer&) const;
};
```

### RangeSelector - 范围选择器

控制 TextAnimator 对哪些字符/单词/行生效,以及效果的衰减曲线。支持 AE 的 Based On (基于字符/单词/行)、Shape (方形/斜坡/三角/圆/平滑)、Mode (加/减/交/取反) 等选项。

### CustomFont - 自定义字体

```cpp
class CustomFont final {
    class Builder {
        bool parseGlyph(abuilder, jobj);  // 解析字形路径或合成
        unique_ptr<CustomFont> detach();
    };

    class GlyphCompMapper : public SkRefCnt {
        sk_sp<sksg::RenderNode> getGlyphComp(typeface, glyphID) const;
    };
};
```

用于处理 Lottie 内嵌的字形数据:
- 字形路径: 直接的矢量路径定义
- 字形合成: 通过 Lottie 合成定义的复杂字形 (如动画文字效果)

## 数据流

```
Lottie 文本图层 JSON
    |
    v
TextAdapter::Make()
    解析文本属性 (fText)
    解析文本动画器 -> vector<TextAnimator>
    设置锚点分组模式 (字符/单词/行/全部)
    |
    v
TextAdapter::onSync()
    |
    +---> reshape()
    |       |
    |       v
    |     Shaper::Shape(text, desc, box/point, fontMgr, factory)
    |       - 调用 SkShaper (HarfBuzz) 排版
    |       - 处理对齐、换行、自适应缩放
    |       - 返回 Shaper::Result { fragments[], scale }
    |       |
    |       v
    |     buildDomainMaps(result)
    |       - 构建非空白字符域映射
    |       - 构建单词域映射
    |       - 构建行域映射
    |       |
    |       v
    |     addFragment() (对每个片段)
    |       - 创建 sksg::Matrix (变换)
    |       - 创建 sksg::Color (填充/描边)
    |       - 创建 sksg::BlurImageFilter (可选模糊)
    |       - 或 buildGlyphCompNodes() (字形合成)
    |
    +---> modulateProps() (对每个动画器)
    |       - 范围选择器计算覆盖度
    |       - 调制属性值
    |
    +---> pushPropsToFragment() (对每个片段)
            - 设置变换矩阵
            - 设置填充/描边颜色和不透明度
            - 设置模糊参数
```

## 依赖关系

```
text/
  ├── Shaper (TextShaper.h/cpp)
  │     ├── SkShaper (skshaper 模块)
  │     ├── SkFontMgr
  │     └── SkUnicode (skunicode 模块)
  ├── sksg (Group, Color, Matrix, BlurImageFilter, Draw, Path)
  ├── animator/Animator.h (AnimatablePropertyContainer)
  └── SkottieValue.h (ScalarValue, Vec2Value, ColorValue, VectorValue)
```

## 相关文档与参考

- **文本排版 API**: `modules/skottie/include/TextShaper.h`
- **文本属性**: `modules/skottie/include/SkottieProperty.h` (TextPropertyValue)
- **父目录**: `docs/yuanlin/modules/skottie/src/README.md`
- **skshaper 模块**: `modules/skshaper/` - HarfBuzz 文本排版
