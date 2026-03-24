# SkSGText - 场景图文本几何节点

> 源文件: `modules/sksg/src/SkSGText.cpp`

## 概述

`SkSGText.cpp` 实现了 Skia 场景图 (sksg) 中的 `Text` 类，用于将文本字符串渲染为场景图中的几何节点。该类支持字体、大小、缩放、倾斜、边缘渲染、提示等排版属性，以及左对齐、居中和右对齐三种对齐方式。文本在重新验证时被 shaping 为 `SkTextBlob`，然后通过标准的绘制和裁剪接口渲染。

## 架构位置

`Text` 位于 sksg 模块的几何节点层，继承自 `GeometryNode`（推测）。它是一个叶子几何节点，将文本内容封装为可绘制的几何形状。在场景图中，`Text` 节点通常与 `PaintNode` 配合使用，由 Skottie 驱动以实现 Lottie 动画中的文本图层。

## 主要类与结构体

### `Text`
```cpp
class Text {
    sk_sp<SkTypeface> fTypeface;  // 字体
    SkString fText;               // 文本内容
    SkPoint fPosition;            // 位置
    SkScalar fSize;               // 字体大小
    SkScalar fScaleX;             // 水平缩放
    SkScalar fSkewX;              // 水平倾斜
    SkFont::Edging fEdging;       // 边缘渲染模式
    SkFontHinting fHinting;       // 提示模式
    SkTextUtils::Align fAlign;    // 对齐方式
    sk_sp<SkTextBlob> fBlob;      // 缓存的文本 Blob
};
```

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `static sk_sp<Text> Make(sk_sp<SkTypeface>, const SkString&)` | 工厂方法创建 Text 节点 |
| `SkRect onRevalidate(InvalidationController*, const SkMatrix&)` | 重建 TextBlob 并计算边界 |
| `void onDraw(SkCanvas*, const SkPaint&) const` | 绘制文本 Blob |
| `void onClip(SkCanvas*, bool) const` | 使用文本路径进行裁剪 |
| `bool onContains(const SkPoint&) const` | 文本路径的点包含测试 |
| `SkPath onAsPath() const` | 返回文本路径（当前未实现） |

## 内部实现细节

### 文本对齐 (`alignedPosition`)
```cpp
SkPoint Text::alignedPosition(SkScalar advance) const {
    auto aligned = fPosition;
    switch (fAlign) {
    case kLeft_Align:   break;
    case kCenter_Align: aligned.offset(-advance / 2, 0); break;
    case kRight_Align:  aligned.offset(-advance, 0); break;
    }
    return aligned;
}
```
对齐通过偏移位置实现而非通过 `SkTextBlob` 内置机制，原因有二：
1. `SkTextBlob` 在带对齐时计算边界不够精确
2. `SkPaint::Align` 已被标记为弃用

### 重新验证 (`onRevalidate`)
```cpp
SkRect Text::onRevalidate(InvalidationController*, const SkMatrix&) {
    SkFont font;
    font.setTypeface(fTypeface);
    font.setSize(fSize);
    // ... 设置其他字体属性
    fBlob = SkTextBlob::MakeFromText(fText.c_str(), fText.size(), font, SkTextEncoding::kUTF8);
    // 计算对齐后的边界
    const auto aligned_pos = this->alignedPosition(bounds.width());
    return bounds.makeOffset(aligned_pos.x(), aligned_pos.y());
}
```

每次重新验证时完整重建 `SkTextBlob`，代码中有 TODO 注释提到未来可能追踪哪些失效不需要重建 blob。

### 未实现的 `onAsPath`
```cpp
SkPath Text::onAsPath() const {
    return SkPath();  // TODO
}
```
返回空路径，这意味着 `onContains` 的实现（依赖 `asPath`）目前不能正确工作。

## 依赖关系

- **直接依赖**: `SkSGText.h`、`SkCanvas.h`、`SkPath.h`、`SkTextBlob.h`、`SkTypeface.h`
- **文本排版**: 依赖 `SkTextBlob::MakeFromText` 进行文本 shaping
- **被使用**: Skottie 文本图层

## 设计模式与设计决策

- **工厂方法**: 使用 `Make()` 静态方法创建实例，构造函数为私有
- **延迟 shaping**: 文本 shaping（从字符串到 TextBlob）仅在 `onRevalidate` 时执行，利用场景图的失效机制避免每帧重复 shaping
- **外部对齐**: 对齐计算在节点外部处理，而非依赖 Skia 内置的对齐支持，这是一个务实的决策，避开了已知的 API 限制
- **UTF-8 编码**: 统一使用 UTF-8 编码处理文本，与 Skia 的主流文本 API 一致

## 性能考量

- **TextBlob 缓存**: `fBlob` 作为成员变量缓存，在参数未变化时不会重建。但目前 `onRevalidate` 在每次调用时都重建 blob，未来可以进行更细粒度的失效追踪
- **shaping 开销**: `SkTextBlob::MakeFromText` 包含完整的文本 shaping 流程，对于长文本或复杂字体可能较慢
- **onAsPath 未实现**: 这导致基于路径的操作（裁剪、包含测试）返回不正确的结果

## 相关文件

- `modules/sksg/include/SkSGText.h` — 类声明和属性定义
- `include/core/SkTextBlob.h` — TextBlob API
- `include/core/SkTypeface.h` — 字体接口
- `modules/sksg/src/SkSGGeometryEffect.cpp` — 其他几何节点实现
- `modules/skottie/src/text/` — Skottie 文本图层实现
