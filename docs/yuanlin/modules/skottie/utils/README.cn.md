# skottie/utils - 工具类

## 概述

`utils/` 目录提供了基于 Skottie 公开 API 构建的高级工具类。这些工具类不属于核心 API,而是为常见的使用场景提供便捷的实现,如属性分组管理、文本编辑、文本预排版和预合成图层替换等。

## 目录结构

```
utils/
├── BUILD.bazel            # Bazel 构建配置
├── SkottieUtils.h         # CustomPropertyManager, ExternalAnimationPrecompInterceptor
├── SkottieUtils.cpp       # 工具类实现
├── TextEditor.h           # TextEditor (WYSIWYG 文本编辑器)
├── TextEditor.cpp         # TextEditor 实现
├── TextPreshape.h         # TextPreshape 声明
├── TextPreshape.cpp       # 文本预排版实现
└── PreshapeTool.cpp       # 预排版命令行工具 (独立可执行)
```

## 关键类与函数

### CustomPropertyManager - 属性分组管理器

```cpp
class CustomPropertyManager final {
    enum class Mode {
        kCollapseProperties,    // 按节点名分组 (忽略祖先链)
        kNamespacedProperties,  // 带命名空间的完整路径
    };

    // 颜色属性
    vector<PropKey> getColorProps() const;
    ColorPropertyValue getColor(key) const;
    bool setColor(key, value);

    // 不透明度属性
    vector<PropKey> getOpacityProps() const;
    OpacityPropertyValue getOpacity(key) const;
    bool setOpacity(key, value);

    // 变换属性
    vector<PropKey> getTransformProps() const;
    TransformPropertyValue getTransform(key) const;
    bool setTransform(key, value);

    // 文本属性
    vector<PropKey> getTextProps() const;
    TextPropertyValue getText(key) const;
    bool setText(key, value);

    // 标记
    const vector<MarkerInfo>& markers() const;

    // 获取用于 Builder 的观察器
    sk_sp<PropertyObserver> getPropertyObserver() const;
    sk_sp<MarkerObserver> getMarkerObserver() const;
};
```

**使用示例:**
```cpp
auto propMgr = CustomPropertyManager(Mode::kNamespacedProperties);
auto animation = Animation::Builder()
    .setPropertyObserver(propMgr.getPropertyObserver())
    .setMarkerObserver(propMgr.getMarkerObserver())
    .make(stream);

// 查询和修改属性
for (const auto& key : propMgr.getColorProps()) {
    propMgr.setColor(key, SK_ColorRED);
}
```

### ExternalAnimationPrecompInterceptor - 外部动画预合成拦截

```cpp
class ExternalAnimationPrecompInterceptor : public PrecompInterceptor {
    ExternalAnimationPrecompInterceptor(resourceProvider, prefix);

    // 匹配名称前缀的预合成图层会被替换为外部 Lottie 动画
    sk_sp<ExternalLayer> onLoadPrecomp(id, name, size) override;
};
```

### TextEditor - WYSIWYG 文本编辑器

```cpp
class TextEditor final : public GlyphDecorator {
    TextEditor(textProp, dependentProps);

    void toggleEnabled();
    void setEnabled(bool);

    // GlyphDecorator: 绘制光标和选区
    void onDecorate(SkCanvas*, const TextInfo&) override;

    // 输入处理
    bool onMouseInput(x, y, state, modifiers);
    bool onCharInput(SkUnichar c);

    void setCursorWeight(float w);
};
```

TextEditor 是一个基于 `GlyphDecorator` API 的示例文本编辑器,展示了如何实现:
- 光标渲染和闪烁
- 鼠标点击定位到字形
- 文本选区绘制
- 字符插入和删除
- 多属性同步更新 (依赖属性)

### TextPreshape - 文本预排版

文本预排版工具,可在构建阶段预先处理文本排版,将文本图层转换为预排版的路径/形状数据,减少运行时的排版开销。`PreshapeTool.cpp` 提供了对应的命令行工具。

## 依赖关系

```
utils/
  ├── skottie/include (Skottie.h, SkottieProperty.h, ExternalLayer.h)
  ├── skresources (ResourceProvider)
  ├── skui (InputState, ModifierKey) [TextEditor]
  └── include/core (SkCanvas, SkPath, SkRect)
```

## 相关文档与参考

- **Skottie API**: `docs/yuanlin/modules/skottie/include/README.md`
- **属性系统**: `modules/skottie/include/SkottieProperty.h`
- **外部图层**: `modules/skottie/include/ExternalLayer.h`
