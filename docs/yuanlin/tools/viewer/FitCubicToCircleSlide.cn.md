# FitCubicToCircleSlide

> 源文件: tools/viewer/FitCubicToCircleSlide.cpp

## 概述

`FitCubicToCircleSlide` 是一个交互式演示工具,用于可视化如何用三次贝塞尔曲线拟合圆弧。该 Slide 允许用户通过拖动圆上的两个端点来定义弧段,然后实时计算并显示最佳拟合的三次曲线。它还能精确计算最大误差的位置(T 值)和误差大小(以像素为单位)。

该工具揭示了一个重要的数学发现:无论弧段角度如何,最大误差总是出现在 T=0.21132486540519 的位置,并且每次将弧段角度减半,最大误差会精确地减少 64 倍。这对于高质量的圆形和椭圆渲染至关重要,因为它指导了如何将圆分解为多个三次曲线段。

## 架构位置

```
skia/
├── tools/viewer/
│   ├── ClickHandlerSlide.h          # 支持鼠标交互的 Slide 基类
│   ├── FitCubicToCircleSlide.cpp    # 本文件
│   └── Slide.h                       # Slide 基类
├── include/core/
│   ├── SkPath.h                      # 路径绘制
│   └── SkCanvas.h                    # 画布接口
└── tools/fonts/
    └── FontToolUtils.h               # 字体工具
```

## 主要类与结构体

### SampleFitCubicToCircle 类

```cpp
class SampleFitCubicToCircle : public ClickHandlerSlide {
public:
    SampleFitCubicToCircle();
    void load(SkScalar w, SkScalar h) override;
    void draw(SkCanvas*) override;
    bool onChar(SkUnichar) override;

protected:
    Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey) override;
    bool onClick(Click*) override;

private:
    void fitCubic();

    // 单位圆上的两个端点坐标
    double fEndptsX[2] = {0, 1};
    double fEndptsY[2] = {-1, 0};

    // 拟合结果
    double fControlLength;           // 控制点长度
    double fMaxErrorT;               // 最大误差 T 值
    std::array<double, 4> fCubicX;   // 屏幕空间三次曲线 X 坐标
    std::array<double, 4> fCubicY;   // 屏幕空间三次曲线 Y 坐标
    double fMaxError;                // 最大误差(像素)
    double fTheta;                   // 弧段角度
    TArray<SkString> fInfoStrings;   // 信息文本

    class Click;
};
```

### 数学常量

```cpp
constexpr static int kCenterX = 300;   // 圆心 X
constexpr static int kCenterY = 325;   // 圆心 Y
constexpr static int kRadius = 250;    // 圆半径
```

## 公共 API 函数

### load

```cpp
void load(SkScalar w, SkScalar h) override;
```
- 调用 `fitCubic()` 进行初始拟合计算

### draw

```cpp
void draw(SkCanvas* canvas) override;
```
- 清空画布为黑色
- 绘制参考圆(半透明白色)
- 绘制拟合的三次曲线(绿色,10 像素宽)
- 绘制两个端点(蓝色圆点)
- 显示拟合信息文本

### onChar

```cpp
bool onChar(SkUnichar unichar) override;
```
- 按 'E' 键:迭代分割弧段,报告误差改善情况
- 展示误差每次减少 64 倍的规律

### onFindClickHandler 和 onClick

处理鼠标拖动端点的交互。

## 内部实现细节

### 核心拟合算法

```cpp
static float fit_cubic_to_unit_circle(double x0, double y0, double x1, double y1,
                                      std::array<double, 4>* X,
                                      std::array<double, 4>* Y)
```

基于三个约束条件拟合三次曲线:
1. 端点和切线方向匹配圆弧
2. 曲线对称(控制点距离相等)
3. 曲线高度匹配圆弧高度

核心公式:
```cpp
constexpr static double kM = -4.0/3;
constexpr static double kA = 4*M_SQRT2/3;
double d = x0*x1 + y0*y1;
double c = (std::sqrt(1 + d) * kM + kA) / std::sqrt(1 - d);
```

### 最大误差查找

使用牛顿-拉弗森迭代法找到误差导数为零的点:

```cpp
double find_max_error_T(double cubicX[4], double cubicY[4]) {
    double T = 0.25;  // 初始猜测
    for (int i = 0; i < 64; ++i) {
        // 计算误差的一阶和二阶导数
        double dError = 2*(x*dx + y*dy);
        double ddError = 2*(x*ddx + y*ddy + dx*dx + dy*dy);
        T -= dError / ddError;  // 牛顿迭代
    }
    return T;
}
```

误差函数定义为:
```
error = x² + y² - 1  (距离单位圆的偏差)
```

### De Casteljau 算法

用于稳定地求值三次曲线及其导数:

```cpp
static std::tuple<double, double, double> eval_cubic(double x[], double T) {
    double ab = lerp(x[0], x[1], T);
    double bc = lerp(x[1], x[2], T);
    double cd = lerp(x[2], x[3], T);
    double abc = lerp(ab, bc, T);
    double bcd = lerp(bc, cd, T);
    double abcd = lerp(abc, bcd, T);  // 曲线值
    return {abcd, 3 * (bcd - abc), 6 * (cd - 2*bc + ab)};
}
```

### 端点顺序保证

确保端点按逆时针顺序排列:

```cpp
if (that->fEndptsX[0] * that->fEndptsY[1] -
    that->fEndptsY[0] * that->fEndptsX[1] < 0) {
    std::swap(that->fEndptsX[0], that->fEndptsX[1]);
    std::swap(that->fEndptsY[0], that->fEndptsY[1]);
    fPtIdx = 1 - fPtIdx;
}
```

使用叉积判断顺序。

## 依赖关系

- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkPath.h`: 路径构造
- `include/core/SkPathBuilder.h`: 路径构建器
- `tools/viewer/ClickHandlerSlide.h`: 交互式 Slide 基类
- `tools/fonts/FontToolUtils.h`: 字体工具

## 设计模式与设计决策

### 交互式探索

用户可以拖动端点实时看到拟合结果变化,这种即时反馈对理解算法行为至关重要。

### 数值稳定性

- 使用 De Casteljau 算法而非直接幂基求值
- 双精度浮点数确保精度
- 牛顿迭代法快速收敛(64 次迭代足够)

### 教育性设计

按 'E' 键的功能专门用于展示数学规律:

```cpp
for (double theta = fTheta; lastError != 0; theta /= 2) {
    // 计算当前角度的误差
    // 显示相对于上次的改善倍数
}
```

输出示例:
```
180.00 degrees:   error=  0.14142px
 90.00 degrees:   error= 0.0022097px (64.00000000000000x improvement)
 45.00 degrees:   error=3.4527e-05px (64.00000000000000x improvement)
```

### 坐标空间转换

算法在单位圆空间工作,结果映射到屏幕空间:

```cpp
for (int i = 0; i < 4; ++i) {
    fCubicX[i] = X[i] * kRadius + kCenterX;
    fCubicY[i] = Y[i] * kRadius + kCenterY;
}
```

## 性能考量

### 实时计算

每次拖动端点都会重新计算拟合,但由于:
- 牛顿迭代快速收敛
- 仅涉及简单的浮点运算
- 无需复杂的矩阵分解

性能完全满足交互需求。

### 精度与速度平衡

- 64 次牛顿迭代足以达到双精度极限
- 初始猜测值 T=0.25 接近真实解,加速收敛

### 避免三角函数

虽然处理圆,但核心算法避免了 sin/cos 调用,仅在最后显示角度时使用 `atan2`。

## 相关文件

### 路径渲染

- `src/core/SkPath.cpp`: 路径实现
- `src/core/SkGeometry.h`: 几何工具

### 圆形绘制

- `src/core/SkCanvas.cpp`: `drawCircle` 和 `drawArc` 实现
- `src/core/SkPathEffect.cpp`: 路径效果

### 类似的几何 Slide

- `tools/viewer/PathSlide.cpp`: 通用路径演示
- `tools/viewer/QuadStrokerSlide.cpp`: 二次曲线描边
