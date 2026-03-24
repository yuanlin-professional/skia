# DegenerateTwoPtRadialsSlide

> 源文件: tools/viewer/DegenerateTwoPtRadialsSlide.cpp

## 概述

`DegenerateTwoPtRadialsSlide` 是一个专门测试双点径向渐变(Two-Point Radial Gradient)在退化情况下的渲染质量的动画演示。当两个圆的圆心非常接近(接近"切点"状态)时,渐变可能出现数值不稳定或渲染瑕疵。该 Slide 通过动画方式连续调整两个圆之间的间隙,从而暴露潜在的渲染问题。

这个测试对于验证渐变着色器的数值稳定性至关重要,特别是在以下场景:
- 圆心距离趋近于零
- 半径之和接近圆心距离
- GPU 和 CPU 渲染路径的一致性

动画周期为 15 秒,间隙参数在 -1/500 到 +1/500 之间振荡,提供充分的视觉检查时间。

## 架构位置

```
skia/
├── tools/viewer/
│   ├── DegenerateTwoPtRadialsSlide.cpp  # 本文件
│   └── Slide.h                           # Slide 基类
├── include/effects/
│   └── SkGradient.h                      # 渐变着色器工厂
└── src/shaders/gradients/
    └── SkTwoPointConicalGradient.cpp     # 双点圆锥渐变实现
```

## 主要类与结构体

### DegenerateTwoPtRadialsSlide 类

```cpp
class DegenerateTwoPtRadialsSlide : public Slide {
public:
    DegenerateTwoPtRadialsSlide();
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;

private:
    SkScalar fTime;  // 动画时间累加器
};
```

### 渐变参数

动画使用固定的矩形尺寸和渐变配置:
- 矩形: 500x500 像素,位于 (100, 100)
- 颜色停点: 红、绿、蓝、洋红在 0, 0.25, 0.75, 1.0 位置
- 圆心 c0: 水平位置随 delta 变化
- 圆心 c1: 固定位置
- 半径 r0: w/5 (100 像素)
- 半径 r1: 2*w/5 (200 像素)

## 公共 API 函数

### 构造函数

```cpp
DegenerateTwoPtRadialsSlide();
```
设置 Slide 名称为 "DegenerateTwoPtRadials"。

### draw

```cpp
void draw(SkCanvas* canvas) override;
```
执行绘制流程:
1. 清空画布为浅灰色 (0xFFDDDDDD)
2. 计算当前 delta 值(基于 fTime)
3. 创建双点圆锥渐变着色器
4. 绘制矩形应用渐变
5. 显示当前 delta 值文本

### animate

```cpp
bool animate(double nanos) override;
```
- 更新时间: `fTime = SkDoubleToScalar(1e-9 * nanos / 15)`
- 除以 15 实现 15 秒的动画周期
- 始终返回 `true` 触发持续重绘

## 内部实现细节

### Delta 计算逻辑

```cpp
SkScalar delta = fTime / 15.f;
int intPart = SkScalarFloorToInt(delta);
delta = delta - SK_Scalar1 * intPart;
if (intPart % 2) {
    delta = SK_Scalar1 - delta;  // 反向运动
}
delta -= SK_ScalarHalf;  // 范围: -0.5 到 +0.5
static const int DELTA_SCALE = 500;
delta /= DELTA_SCALE;    // 范围: -0.001 到 +0.001
```

这个计算产生一个三角波形:
- 周期: 15 秒
- 幅度: ±1/500
- 平滑的来回振荡

### 渐变创建

```cpp
static void draw_gradient2(SkCanvas* canvas, const SkRect& rect, SkScalar delta) {
    SkColor4f colors[] = {
        SkColors::kRed, SkColors::kGreen, SkColors::kBlue, SkColors::kMagenta
    };
    SkScalar pos[] = { 0, 0.25f, 0.75f, SK_Scalar1 };

    SkScalar l = rect.fLeft;
    SkScalar t = rect.fTop;
    SkScalar w = rect.width();
    SkScalar h = rect.height();

    // 第一个圆: 水平位置受 delta 影响
    SkPoint c0 = { l + 2 * w / 5 + delta, t + h / 2 };
    // 第二个圆: 固定位置
    SkPoint c1 = { l + 3 * w / 5, t + h / 2 };
    SkScalar r0 = w / 5;
    SkScalar r1 = 2 * w / 5;

    SkPaint paint;
    paint.setShader(SkShaders::TwoPointConicalGradient(
        c0, r0, c1, r1,
        {{colors, pos, SkTileMode::kClamp}, {}}));
    canvas->drawRect(rect, paint);
}
```

### 文本显示

使用白色背景上的黑色文本显示当前间隙值:

```cpp
SkString txt;
txt.appendf("gap at \"tangent\" pt = %f", delta);
canvas->drawString(txt,
                   l + w / 2 + w * DELTA_SCALE * delta,
                   t + h + SK_Scalar1 * 10,
                   ToolUtils::DefaultFont(),
                   SkPaint());
```

文本位置随 delta 移动,直观展示参数变化。

## 依赖关系

- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkString.h`: 字符串格式化
- `include/effects/SkGradient.h`: 渐变着色器
- `tools/fonts/FontToolUtils.h`: 默认字体
- `tools/viewer/Slide.h`: Slide 基类

## 设计模式与设计决策

### 退化情况测试

该 Slide 专注于最难处理的边缘情况:
- 圆心几乎重合
- "切点"附近的数值不稳定
- 浮点精度限制

### 极小增量

Delta 范围为 ±1/500(±0.002):
- 足够小以暴露数值问题
- 足够大以产生可见差异
- 在典型屏幕分辨率下有意义

### 往复动画

使用三角波而非正弦波:
- 恒定的速度变化率
- 在极值点停留更久
- 更容易观察瞬间状态

### 多色渐变

使用四种鲜艳颜色:
- 红、绿、蓝、洋红
- 高对比度便于发现瑕疵
- 不同颜色停点测试插值

## 性能考量

### 渐变着色器复杂度

双点圆锥渐变涉及复杂的数学计算:
- 二次方程求解
- 根判别式计算
- 边界条件处理

在退化情况下,这些计算可能:
- 触发特殊代码路径
- 产生 NaN 或无穷值
- 降低性能

### 每帧着色器创建

虽然每帧都创建新的着色器实例:

```cpp
paint.setShader(SkShaders::TwoPointConicalGradient(...));
```

这是有意为之,确保测试着色器创建路径,而非仅测试缓存的着色器。

### 15 秒周期

较长的动画周期允许:
- 详细视觉检查
- 捕获截图
- 性能分析

### 固定渐变参数

除 delta 外,所有参数都是常量:
- 隔离 delta 的影响
- 可预测的测试场景
- 便于重现问题

## 相关文件

### 渐变着色器实现

- `src/shaders/gradients/SkTwoPointConicalGradient.cpp`: 核心算法
- `src/shaders/gradients/SkGradientShader.cpp`: 渐变着色器基类
- `src/gpu/ganesh/gradients/`: GPU 渐变实现

### 数值稳定性

- `include/private/base/SkFloatBits.h`: 浮点工具
- `src/base/SkMathPriv.h`: 数学工具

### 类似的渐变测试

- `gm/gradients.cpp`: 各种渐变 GM 测试
- `gm/gradients_2pt_conical.cpp`: 双点圆锥渐变特定测试
- `tools/viewer/GradientsSlide.cpp`: 通用渐变演示

### 动画相关

- `tools/timer/Timer.h`: 时间工具
- `src/base/SkTime.h`: 时间函数
