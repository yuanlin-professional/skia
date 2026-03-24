# TextAdapter - Skottie 文本适配器

> 源文件: [`modules/skottie/src/text/TextAdapter.h`](../../../../modules/skottie/src/text/TextAdapter.h), [`modules/skottie/src/text/TextAdapter.cpp`](../../../../modules/skottie/src/text/TextAdapter.cpp)

## 概述

TextAdapter 是 Skottie 文本层的核心适配器，负责将 Lottie 文本属性（字体、大小、颜色、对齐、文本内容等）转换为可渲染的场景图节点。它管理文本整形（shaping）、片段（fragment）构建、文本动画器应用、文本路径跟随以及字形装饰器等功能。

TextAdapter 是 Skottie 中最复杂的适配器之一，处理了 AE 文本层的几乎所有功能。

## 架构位置

位于 Skottie 文本子系统的顶层：

- **调用者**: AnimationBuilder::attachTextLayer
- **子系统**: TextAnimator（文本动画器）、Shaper（文本整形）、CustomFont（自定义字体）
- **输出**: sksg::Group 场景图节点（包含所有文本片段）

## 主要类与结构体

### `TextAdapter` 类
继承 AnimatablePropertyContainer，是文本层的主适配器。

```cpp
class TextAdapter final : public AnimatablePropertyContainer {
public:
    static sk_sp<TextAdapter> Make(const ObjectValue&, const AnimationBuilder*,
                                    sk_sp<SkFontMgr>, sk_sp<CustomFont::GlyphCompMapper>,
                                    sk_sp<Logger>, sk_sp<SkShapers::Factory>);
    const sk_sp<sksg::Group>& node() const;
    const TextValue& getText() const;
    void setText(const TextValue&);
};
```

### `FragmentRec` 结构体
每个文本片段的场景图记录：位置、字形数据、变换节点、填充/描边颜色节点、模糊滤镜。

### `AnchorPointGrouping` 枚举
锚点分组模式：kCharacter（按字符）、kWord（按单词）、kLine（按行）、kAll（全部）。

### `TextValueTracker` 内部结构体
文本值变更跟踪器，比较当前值和上一次值来检测外部修改。

### `PathInfo` 结构体
文本路径跟随的完整状态，包括路径、边距、垂直/反转标记，以及缓存的轮廓测量数据。

### `GlyphTextNode` 内部类
自定义 sksg::GeometryNode，封装 Shaper::ShapedGlyphs 以支持绘制和包围盒计算。

### `GlyphDecoratorNode` 内部类
场景图节点包装器，在渲染后调用 GlyphDecorator::onDecorate，支持文本编辑器等外部装饰功能。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Make(...)` | 工厂方法，从 JSON 创建 TextAdapter |
| `node()` | 获取场景图根节点 |
| `getText()` | 获取当前文本值 |
| `setText(value)` | 设置文本值（外部属性 API） |

## 内部实现细节

### 场景图结构
每个文本片段构建为：
```
[TransformEffect] -> [Transform]
  [Group]
    [Draw] -> [GlyphTextNode] [FillPaint]
    [Draw] -> [GlyphTextNode] [StrokePaint]
    [CompRenderTree]  // 自定义字体的合成字形
```

### 文本路径跟随
PathInfo 实现了 AE 的文本路径功能：
- 字形位置根据其水平锚点映射到路径上的距离
- 支持闭合路径（超出范围时环绕）和开放路径（超出范围时外推）
- "Perpendicular To Path" 控制字形是否跟随路径切线旋转
- First Margin / Last Margin 根据对齐方式产生偏移

### 文本动画器应用
在 onSync() 中：
1. 检测文本值是否变化，变化时重新整形（reshape）
2. 构建 ModulatorBuffer（每个片段一个调制器）
3. 各 TextAnimator 依次调制属性
4. 将解析后的属性推送到各片段的场景图节点

### 自定义字形处理
buildGlyphCompNodes 检查字形是否有合成映射（CustomFont::GlyphCompMapper），有则替换为合成渲染树并从常规字形列表中移除。

### JSON 结构
```json
"t": {
  "a": [],        // 动画器列表
  "d": { "k": [] }, // 文本数据（可含 "sid" 用于 slot）
  "m": { "g": 1, "a": {...} },  // 更多选项（锚点分组、分组对齐）
  "p": { ... }    // 路径选项
}
```

## 依赖关系

- `modules/skottie/include/TextShaper.h` - 文本整形器
- `modules/skottie/src/text/TextAnimator.h` - 文本动画器
- `modules/skottie/src/text/TextValue.h` - 文本值类型
- `modules/skottie/src/text/Font.h` - 自定义字体
- `modules/sksg/` - 场景图节点
- `include/core/SkContourMeasure.h` - 轮廓测量（路径跟随）

## 设计模式与设计决策

### 变更检测
TextValueTracker 使用值比较而非脏标记，正确处理外部通过 setText() 的修改。

### 惰性重整形
仅在文本值实际变化时触发重整形，属性动画（颜色、变换等）不需要重整形。

### 路径轮廓缓存
PathInfo 缓存 SkContourMeasure，仅在路径或反转状态变化时重新构建。

## 性能考量

- 重整形是最昂贵的操作，通过变更检测最小化触发
- 路径轮廓缓存避免重复测量
- 调制缓冲区预分配到片段数量
- 每个片段独立的场景图节点支持局部更新

## 相关文件

- `modules/skottie/src/text/TextAnimator.h` - 文本动画器
- `modules/skottie/src/text/RangeSelector.h` - 范围选择器
- `modules/skottie/src/text/Font.h` - 自定义字体系统
- `modules/skottie/include/TextShaper.h` - 文本整形 API
