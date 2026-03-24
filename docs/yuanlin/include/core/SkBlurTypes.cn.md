# SkBlurTypes

> 源文件: `include/core/SkBlurTypes.h`

## 概述

SkBlurTypes 定义了 SkBlurStyle 枚举,用于指定模糊效果应用于形状的方式。该枚举控制模糊滤镜在对象内部和外部的应用策略,是 Skia 模糊效果系统的核心配置类型,直接影响阴影、发光和柔化边缘等视觉效果的呈现。

## 架构位置

SkBlurTypes 位于 Skia 核心图像效果层,属于模糊滤镜子系统的基础类型定义。它被 SkMaskFilter、SkImageFilter 和阴影绘制相关的模块使用,是配置模糊行为的关键参数。该类型影响从基础形状模糊到复杂图层效果的整个模糊渲染流程。

## 枚举定义

### SkBlurStyle

```cpp
enum SkBlurStyle : int {
    kNormal_SkBlurStyle,  // 内外都模糊
    kSolid_SkBlurStyle,   // 内部实心,外部模糊
    kOuter_SkBlurStyle,   // 内部无,外部模糊
    kInner_SkBlurStyle,   // 内部模糊,外部无
    kLastEnum_SkBlurStyle = kInner_SkBlurStyle,
};
```

**枚举值详解**:

| 枚举值 | 数值 | 内部效果 | 外部效果 | 典型用途 |
|--------|------|---------|---------|---------|
| kNormal_SkBlurStyle | 0 | 模糊 | 模糊 | 通用模糊、柔化边缘 |
| kSolid_SkBlurStyle | 1 | 实心不透明 | 模糊 | 外发光效果 |
| kOuter_SkBlurStyle | 2 | 完全透明 | 模糊 | 外阴影、光晕 |
| kInner_SkBlurStyle | 3 | 模糊 | 完全透明 | 内阴影、凹陷效果 |

## 模糊样式详解

### kNormal_SkBlurStyle (标准模糊)

**效果描述**:
- 形状内外均匀模糊
- 边缘柔化,无突变
- 整体半透明化

**数学定义**:
应用高斯卷积核到整个形状区域,不区分内外。

**适用场景**:
```cpp
// 柔化矩形边缘
SkPaint paint;
paint.setMaskFilter(SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, sigma));
canvas->drawRect(rect, paint);
```

**视觉效果**:
- 形状整体变模糊
- 边缘逐渐淡出
- 适合失焦效果

### kSolid_SkBlurStyle (实心外模糊)

**效果描述**:
- 形状内部保持完全不透明
- 外部边缘模糊扩散
- 产生"发光"效果

**数学定义**:
内部 Alpha = 1.0,外部应用高斯模糊。

**适用场景**:
```cpp
// 文字外发光
SkPaint paint;
paint.setMaskFilter(SkMaskFilter::MakeBlur(kSolid_SkBlurStyle, sigma));
canvas->drawText("GLOW", paint);
```

**视觉效果**:
- 清晰的内部填充
- 外围光晕或光圈
- 适合高亮和强调

### kOuter_SkBlurStyle (仅外模糊)

**效果描述**:
- 形状内部完全透明(挖空)
- 外部边缘模糊扩散
- 产生"阴影"或"光环"效果

**数学定义**:
内部 Alpha = 0,外部应用高斯模糊并保留原始形状外的部分。

**适用场景**:
```cpp
// 投影阴影
SkPaint shadowPaint;
shadowPaint.setMaskFilter(SkMaskFilter::MakeBlur(kOuter_SkBlurStyle, sigma));
shadowPaint.setColor(SK_ColorBLACK);
canvas->save();
canvas->translate(5, 5); // 偏移产生阴影
canvas->drawRect(rect, shadowPaint);
canvas->restore();
canvas->drawRect(rect, paint); // 绘制原始形状
```

**视觉效果**:
- 形状本身不可见
- 仅显示外围模糊
- 适合阴影和光晕

### kInner_SkBlurStyle (仅内模糊)

**效果描述**:
- 形状外部边缘锐利
- 内部向中心模糊
- 产生"凹陷"或"内阴影"效果

**数学定义**:
外部保持原始边界,内部应用反向高斯模糊。

**适用场景**:
```cpp
// 内阴影效果
SkPaint paint;
paint.setMaskFilter(SkMaskFilter::MakeBlur(kInner_SkBlurStyle, sigma));
canvas->drawRoundRect(roundRect, paint);
```

**视觉效果**:
- 清晰的外轮廓
- 内部渐变模糊
- 适合凹陷按钮、内嵌效果

## 内部实现细节

### 模糊算法

Skia 通常使用高斯模糊实现:
- **核心参数**: sigma (标准差),控制模糊半径
- **卷积核**: 二维高斯函数
- **优化**: 分离卷积(先水平后垂直)

### 边界处理

不同样式的边界处理策略:

**kNormal**: 边界两侧均匀卷积
```
原始: |████████|
模糊: ░░▓▓▓▓▓▓░░
```

**kSolid**: 内侧保持,外侧卷积
```
原始: |████████|
模糊: |████████░░
```

**kOuter**: 内侧清空,外侧卷积
```
原始: |████████|
模糊:  ░░░░░░░░
      (原始位置透明)
```

**kInner**: 外侧保持,内侧反向卷积
```
原始: |████████|
模糊: |░░▓▓▓▓░░|
```

### Alpha 通道处理

模糊操作主要影响 Alpha 通道:
- 颜色通道通常与 Alpha 关联处理(预乘 Alpha)
- 某些情况下可独立模糊颜色和 Alpha

## 依赖关系

### 依赖的模块

该头文件无外部依赖,是纯枚举定义。

### 被依赖的模块

SkBlurStyle 被以下模块使用:
- **SkMaskFilter**: 创建模糊遮罩滤镜
- **SkImageFilter**: 图层模糊效果
- **SkDrawLooper**: 阴影和发光效果
- **SkCanvas**: 阴影绘制 API
- **GPU 后端**: 实现高效的模糊渲染

## 设计模式与设计决策

### 枚举而非位标志

使用独立枚举值而非位组合:
- **简化性**: 4种样式覆盖常见需求
- **性能**: 每种样式有专门优化路径
- **清晰性**: 避免无效组合

### 命名约定

使用 `kXxx_SkBlurStyle` 模式:
- 前缀 `k` 表示常量
- 后缀 `_SkBlurStyle` 避免命名冲突
- 历史遗留风格,新代码可能使用 `enum class`

## 性能考量

### 样式性能对比

| 样式 | 计算复杂度 | GPU 友好度 | 典型用途 |
|------|----------|-----------|---------|
| kNormal | 中等 | 优秀 | 通用模糊 |
| kSolid | 中等 | 良好 | 文字发光 |
| kOuter | 高 | 中等 | 投影阴影 |
| kInner | 高 | 中等 | 内阴影 |

### 优化建议

1. **缓存模糊结果**: 相同参数的模糊可重用
2. **减小 sigma**: 模糊半径越小,计算量越少
3. **使用 GPU**: 现代 GPU 对高斯模糊高度优化
4. **降级处理**: 小对象可使用简化算法

### 模糊半径影响

```cpp
sigma = 1.0:  轻微模糊,性能良好
sigma = 5.0:  中等模糊,可接受性能
sigma = 20.0: 强烈模糊,性能开销大
```

## 使用示例

### 示例 1: 文字外发光

```cpp
SkPaint glowPaint;
glowPaint.setColor(SK_ColorYELLOW);
glowPaint.setMaskFilter(SkMaskFilter::MakeBlur(kSolid_SkBlurStyle, 3.0f));
canvas->drawText("HIGHLIGHT", 100, 100, glowPaint);
```

### 示例 2: 投影阴影

```cpp
// 绘制阴影层
SkPaint shadowPaint;
shadowPaint.setColor(SkColorSetARGB(128, 0, 0, 0)); // 半透明黑色
shadowPaint.setMaskFilter(SkMaskFilter::MakeBlur(kOuter_SkBlurStyle, 5.0f));
canvas->save();
canvas->translate(10, 10); // 阴影偏移
canvas->drawRect(rect, shadowPaint);
canvas->restore();

// 绘制主体
SkPaint mainPaint;
mainPaint.setColor(SK_ColorWHITE);
canvas->drawRect(rect, mainPaint);
```

### 示例 3: 按钮内阴影

```cpp
SkPaint buttonPaint;
buttonPaint.setColor(SkColorSetRGB(200, 200, 200));
buttonPaint.setMaskFilter(SkMaskFilter::MakeBlur(kInner_SkBlurStyle, 4.0f));

SkRRect roundRect = SkRRect::MakeRectXY(
    SkRect::MakeXYWH(50, 50, 200, 60), 10, 10);
canvas->drawRRect(roundRect, buttonPaint);
```

### 示例 4: 标准柔化

```cpp
SkPaint softPaint;
softPaint.setColor(SK_ColorBLUE);
softPaint.setMaskFilter(SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, 2.0f));
canvas->drawCircle(150, 150, 50, softPaint);
```

## 与其他图形系统的对比

| Skia | CSS box-shadow | Core Graphics | Direct2D |
|------|---------------|---------------|----------|
| kNormal | blur-radius | - | D2D1_SHADOW_OPTIMIZATION_BALANCED |
| kSolid | - | - | - |
| kOuter | spread + blur | CGContextSetShadow | D2D1_SHADOW_OPTIMIZATION_QUALITY |
| kInner | inset | - | - |

**注**: 其他系统通常通过参数组合实现类似效果,Skia 提供专门枚举更明确。

## 常见陷阱与最佳实践

### 陷阱 1: 过度模糊导致性能问题

```cpp
// 不推荐: sigma 过大
paint.setMaskFilter(SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, 50.0f));
// 可能导致帧率下降
```

### 陷阱 2: Inner 样式误用

```cpp
// 错误: 期望外阴影但使用了 kInner
paint.setMaskFilter(SkMaskFilter::MakeBlur(kInner_SkBlurStyle, sigma));
// 实际得到内阴影效果
```

### 最佳实践 1: 样式选择

```cpp
// 明确需求选择样式
if (needDropShadow) {
    style = kOuter_SkBlurStyle; // 投影
} else if (needGlow) {
    style = kSolid_SkBlurStyle; // 发光
} else if (needInset) {
    style = kInner_SkBlurStyle; // 内嵌
} else {
    style = kNormal_SkBlurStyle; // 通用
}
```

### 最佳实践 2: 性能优化

```cpp
// 缓存昂贵的模糊滤镜
sk_sp<SkMaskFilter> cachedBlur =
    SkMaskFilter::MakeBlur(kNormal_SkBlurStyle, 10.0f);

// 多次使用相同滤镜
paint1.setMaskFilter(cachedBlur);
paint2.setMaskFilter(cachedBlur);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkMaskFilter.h | 使用 SkBlurStyle 创建模糊滤镜 |
| include/effects/SkBlurMaskFilter.h | 具体的模糊实现 |
| include/core/SkImageFilter.h | 图层级模糊效果 |
| include/effects/SkBlurImageFilter.h | 图像模糊滤镜 |
| src/effects/SkBlurMask.h | 底层模糊算法实现 |
