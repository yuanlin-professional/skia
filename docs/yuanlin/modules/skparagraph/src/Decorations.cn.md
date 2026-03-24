# Decorations

> 源文件: modules/skparagraph/src/Decorations.h, modules/skparagraph/src/Decorations.cpp

## 概述

`Decorations` 类负责在 Skia 段落模块中绘制文本装饰效果,包括下划线(underline)、上划线(overline)和删除线(line-through)。该类支持多种装饰样式(实线、虚线、点线、波浪线、双线),并能正确处理装饰与字形的间隙(gaps),确保装饰线不会遮挡文本的下行字母(descenders)。它根据字体度量信息精确计算装饰线的位置和粗细,遵循 Flutter 的文本装饰规范。

## 架构位置

`Decorations` 在段落渲染管线中负责装饰效果的绘制:

```
段落渲染流程
    ├── ParagraphImpl::paint()
    │   └── TextLine::paint()
    │       ├── 绘制文本 (TextBlob)
    │       └── Decorations::paint() (本类)
    │           ├── calculateThickness() (计算线条粗细)
    │           ├── calculatePosition() (计算位置)
    │           ├── calculatePaint() (配置绘制属性)
    │           ├── calculateWaves() (波浪线路径)
    │           └── calculateGaps() (计算字形间隙)
```

该类是文本装饰的专用绘制器,与 `TextLine` 配合工作,在文本绘制后添加装饰效果。

## 主要类与结构体

### Decorations 类

```cpp
class Decorations {
public:
    void paint(ParagraphPainter* painter, const TextStyle& textStyle,
               const TextLine::ClipContext& context, SkScalar baseline);
private:
    void calculateThickness(TextStyle textStyle, sk_sp<SkTypeface> typeface);
    void calculatePosition(TextDecoration decoration, SkScalar ascent);
    void calculatePaint(const TextStyle& textStyle);
    void calculateWaves(const TextStyle& textStyle, SkRect clip);
    void calculateGaps(const TextLine::ClipContext& context, const SkRect& rect,
                       SkScalar baseline, SkScalar halo);

    SkScalar fThickness;           // 装饰线粗细
    SkScalar fPosition;            // 装饰线位置(相对于基线)
    SkFontMetrics fFontMetrics;    // 字体度量信息
    ParagraphPainter::DecorationStyle fDecorStyle;  // 装饰绘制样式
    SkPath fPath;                  // 装饰线路径
};
```

核心成员说明:
- **fThickness**: 装饰线的粗细,根据字体大小或字体度量信息计算
- **fPosition**: 装饰线的垂直位置,相对于文本基线的偏移
- **fFontMetrics**: 从字体获取的度量信息,包含推荐的下划线/删除线位置和粗细
- **fDecorStyle**: 封装颜色、宽度和虚线效果的装饰样式
- **fPath**: 用于绘制复杂装饰(如波浪线、带间隙的线)的路径

### TextLine::ClipContext

```cpp
struct ClipContext {
    const Run* run;          // 当前文本运行
    SkRect clip;             // 裁剪区域
    size_t pos;              // 运行中的起始位置
    size_t size;             // 字形数量
    SkScalar fTextShift;     // 文本偏移(用于间隙绘制)
};
```

提供绘制装饰所需的上下文信息,包括文本运行、裁剪区域和位置信息。

## 公共 API 函数

### paint

```cpp
void paint(ParagraphPainter* painter, const TextStyle& textStyle,
           const TextLine::ClipContext& context, SkScalar baseline);
```

主绘制方法,根据 `textStyle` 中的装饰配置绘制装饰线。执行以下步骤:
1. 检查是否有装饰类型,无装饰则直接返回
2. 计算装饰线粗细(`calculateThickness`)
3. 遍历所有装饰类型(underline/overline/line-through)
4. 对每种装饰计算位置(`calculatePosition`)
5. 配置绘制属性(`calculatePaint`)
6. 根据装饰样式选择绘制方法:
   - 波浪线: 生成波浪路径并绘制
   - 双线: 绘制两条平行线
   - 虚线/点线: 使用虚线效果绘制
   - 实线: 绘制矩形或带间隙的路径

## 内部实现细节

### 装饰线粗细计算

```cpp
void calculateThickness(TextStyle textStyle, sk_sp<SkTypeface> typeface) {
    fThickness = textStyle.getFontSize() / 14.0f;  // 默认值

    // 优先使用字体度量中的推荐值
    if (fFontMetrics.fUnderlineThickness > 0) {
        fThickness = fFontMetrics.fUnderlineThickness;
    }

    // 删除线使用单独的度量
    if (decoration == TextDecoration::kLineThrough &&
        fFontMetrics.fStrikeoutThickness > 0) {
        fThickness = fFontMetrics.fStrikeoutThickness;
    }

    // 应用用户指定的倍数
    fThickness *= textStyle.getDecorationThicknessMultiplier();
}
```

粗细计算遵循 Flutter 规范:
1. 默认粗细为字体大小的 1/14
2. 如果字体提供度量信息,使用字体推荐值
3. 应用用户指定的倍数调整

### 装饰线位置计算

```cpp
void calculatePosition(TextDecoration decoration, SkScalar ascent) {
    switch (decoration) {
        case TextDecoration::kUnderline:
            fPosition = fFontMetrics.fUnderlinePosition > 0
                ? fFontMetrics.fUnderlinePosition
                : fThickness;  // 回退到使用粗细作为位置
            fPosition -= ascent;
            break;
        case TextDecoration::kOverline:
            fPosition = -ascent;  // 在文本顶部
            break;
        case TextDecoration::kLineThrough:
            fPosition = fFontMetrics.fStrikeoutPosition > 0
                ? fFontMetrics.fStrikeoutPosition
                : fFontMetrics.fXHeight / -2;  // 回退到 x-高度的一半
            fPosition -= ascent;
            break;
    }
}
```

位置计算基于字体度量:
- **下划线**: 使用字体推荐位置或默认为粗细值
- **上划线**: 位于文本顶部(ascent位置)
- **删除线**: 使用字体推荐位置或 x-高度的中点

### 虚线效果配置

```cpp
void calculatePaint(const TextStyle& textStyle) {
    SkScalar scaleFactor = textStyle.getFontSize() / 14.f;
    switch (textStyle.getDecorationStyle()) {
        case TextDecorationStyle::kDotted:
            dashPathEffect = {1.0f * scaleFactor, 1.5f * scaleFactor};
            break;
        case TextDecorationStyle::kDashed:
            dashPathEffect = {4.0f * scaleFactor, 2.0f * scaleFactor};
            break;
    }
}
```

虚线和点线的间隔按字体大小缩放,确保在不同字号下保持视觉一致性。

### 波浪线生成

```cpp
void calculateWaves(const TextStyle& textStyle, SkRect clip) {
    SkScalar quarterWave = fThickness;  // 四分之一波长
    SkScalar x_start = 0;
    int wave_count = 0;

    builder.moveTo(0, 0);
    while (x_start + quarterWave * 2 < clip.width()) {
        builder.rQuadTo(quarterWave,
                        wave_count % 2 != 0 ? quarterWave : -quarterWave,
                        quarterWave * 2, 0);
        x_start += quarterWave * 2;
        ++wave_count;
    }
    // 处理剩余部分...
}
```

波浪线使用二次贝塞尔曲线生成,波长基于装饰线粗细,交替向上和向下波动。最后的不完整波浪通过调整控制点平滑过渡。

### 字形间隙计算

```cpp
void calculateGaps(const TextLine::ClipContext& context, const SkRect& rect,
                   SkScalar baseline, SkScalar halo) {
    // 1. 创建文本 blob
    SkTextBlobBuilder builder;
    context.run->copyTo(builder, context.pos, context.size);
    sk_sp<SkTextBlob> blob = builder.make();

    // 2. 获取与装饰线相交的区域
    const SkScalar bounds[2] = {rect.fTop - baseline, rect.fBottom - baseline};
    blob->getIntercepts(bounds, intersections.data(), &decorPaint);

    // 3. 在相交区域之间绘制线段
    SkPathBuilder path;
    auto start = rect.fLeft;
    for (int i = 0; i < intersections.size(); i += 2) {
        auto end = intersections[i] - halo;  // 留出光晕空间
        if (end - start >= halo) {
            path.lineTo(end, rect.fTop).moveTo(start, rect.fTop);
            start = intersections[i + 1] + halo;
        }
    }
}
```

间隙绘制算法:
1. 将文本转换为 `SkTextBlob`
2. 使用 `getIntercepts()` 找到字形边界与装饰线的相交区域
3. 在非相交区域绘制装饰线,保留 `halo` 空间避免装饰线接触字形
4. 这确保下行字母(如 'g', 'y', 'p')不会被下划线遮挡

### 双线绘制

```cpp
case TextDecorationStyle::kDouble: {
    SkScalar bottom = y + kDoubleDecorationSpacing;  // 3.0f 固定间距
    if (drawGaps) {
        calculateGaps(context, SkRect::MakeXYWH(left, y, width, fThickness), ...);
        painter->drawPath(fPath, fDecorStyle);
        calculateGaps(context, SkRect::MakeXYWH(left, bottom, width, fThickness), ...);
        painter->drawPath(fPath, fDecorStyle);
    } else {
        draw_line_as_rect(painter, x, y, width, fDecorStyle);
        draw_line_as_rect(painter, x, bottom, width, fDecorStyle);
    }
    break;
}
```

双线样式绘制两条平行线,间距固定为 3 像素。两条线都支持间隙模式。

### 矩形优化绘制

```cpp
void draw_line_as_rect(ParagraphPainter* painter, SkScalar x, SkScalar y, SkScalar width,
                       const ParagraphPainter::DecorationStyle& decorStyle) {
    float radius = decorStyle.getStrokeWidth() * 0.5f;
    painter->drawFilledRect({x, y - radius, x + width, y + radius}, decorStyle);
}
```

对于实线样式,使用填充矩形而非描边线段,这在某些渲染器上性能更好。矩形高度等于线条粗细,中心位于 y 坐标。

## 依赖关系

### Skia 核心依赖
- **SkPath / SkPathBuilder**: 路径构建和绘制
- **SkPaint**: 绘制属性配置
- **SkFontMetrics**: 字体度量信息
- **SkTextBlob / SkTextBlobBuilder**: 文本 blob 操作(用于间隙计算)
- **SkTypeface**: 字体访问

### 段落模块依赖
- **ParagraphPainter**: 抽象绘制接口
- **TextStyle**: 文本和装饰样式配置
- **TextLine**: 文本行(提供 ClipContext)
- **Run**: 文本运行单元

### 枚举类型
- **TextDecoration**: 装饰类型(underline/overline/line-through)
- **TextDecorationStyle**: 装饰样式(solid/dotted/dashed/wavy/double)
- **TextDecorationMode**: 装饰模式(是否绘制间隙)

## 设计模式与设计决策

### 策略模式

不同装饰样式使用不同的绘制策略:
```cpp
switch (textStyle.getDecorationStyle()) {
    case TextDecorationStyle::kWavy: /* 波浪线策略 */ break;
    case TextDecorationStyle::kDouble: /* 双线策略 */ break;
    case TextDecorationStyle::kDotted: /* 点线策略 */ break;
    // ...
}
```

这使得添加新的装饰样式变得容易,只需在 switch 中添加新的 case。

### 模板方法模式

`paint()` 方法定义了装饰绘制的通用流程:
1. 计算粗细
2. 遍历装饰类型
3. 计算位置
4. 配置绘制属性
5. 执行绘制

每个步骤由专门的私有方法实现,职责清晰。

### 延迟计算

装饰属性(粗细、位置、路径)在 `paint()` 调用时即时计算,而非预先计算:
- 优点: 避免存储中间结果,减少内存占用
- 缺点: 重复绘制时需要重新计算

由于装饰绘制通常只发生一次(在布局后),延迟计算是合理的权衡。

### 设计决策

1. **遵循 Flutter 规范**: 粗细和位置计算逻辑与 Flutter 保持一致,确保跨平台的视觉一致性。

2. **字体度量优先**: 优先使用字体提供的度量信息,因为字体设计师最了解装饰应该出现的位置。

3. **间隙绘制支持**: 通过 `TextDecorationMode::kGaps` 支持智能间隙,这是高质量排版的重要特性,避免装饰线干扰字形可读性。

4. **矩形优化**: 对实线使用填充矩形而非描边路径,这在某些后端(特别是 GPU 渲染)上性能更好。

5. **独立类设计**: 将装饰逻辑封装在独立类中,而非混入 `TextLine`,保持关注点分离和代码清晰。

## 性能考量

### getIntercepts() 开销

间隙计算需要调用 `SkTextBlob::getIntercepts()`,这涉及字形边界计算:
```cpp
blob->getIntercepts(bounds, nullptr, &decorPaint);  // 第一次获取数量
blob->getIntercepts(bounds, intersections.data(), &decorPaint);  // 第二次获取数据
```

这是相对昂贵的操作,因此只在 `TextDecorationMode::kGaps` 启用时执行。

### 路径构建

波浪线和间隙装饰需要构建 `SkPath`,涉及内存分配和路径操作:
```cpp
SkPathBuilder builder;
// 添加多个路径操作
fPath = builder.detach();
```

对于简单的实线,使用矩形绘制避免了路径开销。

### 批处理机会

当前实现为每个文本运行单独绘制装饰。未来可以优化为批量绘制同一行的所有装饰,减少绘制调用次数。

### 缓存潜力

装饰属性(粗细、位置)在相同字体和字号下是恒定的,可以缓存在 `Run` 级别。但当前实现选择即时计算,因为计算开销相对较小。

## 相关文件

### 核心渲染
- `modules/skparagraph/src/TextLine.h/cpp`: 文本行实现,调用装饰绘制
- `modules/skparagraph/include/ParagraphPainter.h`: 抽象绘制器接口
- `modules/skparagraph/src/ParagraphPainterImpl.h/cpp`: 默认绘制器实现

### 样式定义
- `modules/skparagraph/include/TextStyle.h`: 文本样式(包含装饰配置)
- `modules/skparagraph/include/DartTypes.h`: 装饰类型枚举定义

### 相关渲染类
- `modules/skparagraph/src/Run.h/cpp`: 文本运行单元
- `modules/skparagraph/src/ParagraphImpl.h/cpp`: 段落实现

### Skia 核心
- `include/core/SkPath.h`: 路径操作
- `include/core/SkTextBlob.h`: 文本 blob 和 intercepts API
- `include/core/SkFontMetrics.h`: 字体度量定义

该类是段落模块中专门负责文本装饰的模块,实现了完整的装饰样式支持和智能间隙处理,是高质量文本渲染的重要组成部分。
