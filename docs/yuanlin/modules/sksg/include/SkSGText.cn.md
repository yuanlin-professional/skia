# SkSGText -- 文本几何节点

> 源文件: `modules/sksg/include/SkSGText.h`

## 概述

`SkSGText.h` 定义了 Skia Scene Graph 中的文本几何节点 `Text`。该节点将文本内容封装为一个 `GeometryNode`，通过 `SkTextBlob` 进行文本排版和缓存。它支持设置字体、大小、倾斜、缩放、对齐方式、边缘处理和字体提示等多种文本属性，是场景图中文本渲染的基础构建块。

## 架构位置

`Text` 在 sksg 节点层次中的位置：

```
Node
└── GeometryNode (几何节点基类)
    ├── Path, Rect, RRect, Plane (基础几何体)
    └── Text (文本几何体)
```

作为 `GeometryNode` 的子类，`Text` 可以与 `PaintNode` 组合传入 `Draw` 节点进行绘制，也可以与 `GeometryEffect` 组合产生路径效果。文本内部被转化为 `SkTextBlob` 和 `SkPath`，融入了 Skia 的标准文本排版流水线。

## 主要类与结构体

### `Text`
```cpp
class Text final : public GeometryNode {
public:
    static sk_sp<Text> Make(sk_sp<SkTypeface> tf, const SkString& text);
    ~Text() override;

    SG_ATTRIBUTE(Typeface, sk_sp<SkTypeface>,  fTypeface)
    SG_ATTRIBUTE(Text,     SkString,           fText)
    SG_ATTRIBUTE(Position, SkPoint,            fPosition)
    SG_ATTRIBUTE(Size,     SkScalar,           fSize)
    SG_ATTRIBUTE(ScaleX,   SkScalar,           fScaleX)
    SG_ATTRIBUTE(SkewX,    SkScalar,           fSkewX)
    SG_ATTRIBUTE(Align,    SkTextUtils::Align, fAlign)
    SG_ATTRIBUTE(Edging,   SkFont::Edging,     fEdging)
    SG_ATTRIBUTE(Hinting,  SkFontHinting,      fHinting)

private:
    sk_sp<SkTextBlob> fBlob; // 缓存的文本 blob
};
```

## 公共 API 函数

### `Text::Make(tf, text)`
工厂方法，创建文本几何节点。接受字体（`SkTypeface`）和初始文本内容（`SkString`）。

### 属性访问器（通过 SG_ATTRIBUTE 生成）

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Typeface | `sk_sp<SkTypeface>` | 构造参数 | 字体 |
| Text | `SkString` | 构造参数 | 文本内容 |
| Position | `SkPoint` | (0, 0) | 文本基线位置 |
| Size | `SkScalar` | 12 | 字号大小 |
| ScaleX | `SkScalar` | 1 | 水平缩放 |
| SkewX | `SkScalar` | 0 | 水平倾斜 |
| Align | `SkTextUtils::Align` | kLeft_Align | 对齐方式 |
| Edging | `SkFont::Edging` | kAntiAlias | 边缘渲染模式 |
| Hinting | `SkFontHinting` | kNormal | 字体提示级别 |

每个属性的 `set*` 方法在值发生变化时自动触发节点失效。

## 内部实现细节

- **TextBlob 缓存**：`fBlob` 成员缓存排版后的 `SkTextBlob`，只在 `onRevalidate` 时重建。SkTextBlob 是不可变的，适合缓存。

- **对齐位置计算**：`alignedPosition` 是私有辅助方法，根据文本宽度和对齐方式（左/中/右）计算实际的绘制位置。

- **GeometryNode 接口实现**：
  - `onClip` -- 使用文本路径进行裁剪
  - `onDraw` -- 使用缓存的 TextBlob 绘制到 Canvas
  - `onContains` -- 使用文本路径进行点命中测试
  - `onAsPath` -- 将文本转换为路径表示

- **TODO 注释**：源码中标注了 `TODO: add shaping functionality`，说明当前的文本排版是简单的字形排列，尚未集成复杂的文本整形（shaping）功能（如连字、双向文本等）。

## 依赖关系

- `include/core/SkFont.h` -- SkFont 类型和 Edging 枚举
- `include/core/SkFontTypes.h` -- SkFontHinting 枚举
- `include/core/SkString.h` -- 文本内容存储
- `include/core/SkPath.h` -- 文本路径转换
- `include/utils/SkTextUtils.h` -- 文本对齐工具和 Align 枚举
- `modules/sksg/include/SkSGGeometryNode.h` -- 基类
- `SkTextBlob` -- 排版后的文本缓存（前向声明）
- `SkTypeface` -- 字体类型（前向声明）

## 设计模式与设计决策

1. **几何节点抽象**：将文本建模为几何节点而非专用渲染节点，使文本可以参与几何效果链（如 TrimEffect、DashEffect），与其他几何体统一处理。

2. **属性驱动的失效**：所有文本属性通过 SG_ATTRIBUTE 管理，变化时自动失效，驱动 TextBlob 重建。

3. **TextBlob 缓存策略**：SkTextBlob 在 revalidate 时创建并缓存，渲染时直接使用，避免每帧重新排版。

4. **丰富的字体控制**：暴露了 Edging（抗锯齿/子像素/无）和 Hinting（无/轻微/正常/完全）等底层字体渲染参数，提供精细的文本渲染控制。

## 性能考量

- TextBlob 缓存是关键优化点，文本排版只在属性变化时进行，渲染时使用缓存的 blob。
- `onAsPath` 将文本转换为路径是一个相对昂贵的操作，涉及字形轮廓提取。
- 频繁更改文本内容会导致 TextBlob 频繁重建，应尽量批量更新属性。
- 字体大小、倾斜和缩放的组合存储在 SkFont 中，避免了额外的矩阵变换。

## 相关文件

- `modules/sksg/src/SkSGText.cpp` -- Text 节点的实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGDraw.h` -- Draw 节点，用于将 Text + Paint 组合渲染
- `modules/sksg/include/SkSGPaint.h` -- PaintNode，与 Text 配对使用
