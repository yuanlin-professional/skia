# FlutterAnimateSlide

> 源文件: tools/viewer/FlutterAnimateSlide.cpp

## 概述

`FlutterAnimateSlide` 是一个用于压力测试字形图集(glyph atlas)的动画演示 Slide。它创建了一个包含 40 个随机字母的动画场景,每个字母在指定位置进行旋转动画。该 Slide 的主要目的是测试 Skia 的字形缓存系统在大量旋转文本渲染时的性能和稳定性,确保不会出现字形损坏或严重的性能下降。

这个测试最初是为 Flutter 框架设计的,用于验证在动态文本场景下的渲染质量。通过持续旋转多个字母,它能够有效地检测字形图集的管理是否正确,包括缓存驱逐、纹理更新和渲染一致性。

## 架构位置

`FlutterAnimateSlide` 位于 Skia 的 viewer 工具集中:

```
skia/
├── tools/
│   └── viewer/
│       ├── Slide.h                    # Slide 基类
│       ├── FlutterAnimateSlide.cpp    # 本文件
│       └── Viewer.cpp                 # Viewer 主程序
├── include/core/
│   ├── SkCanvas.h                     # 绘制接口
│   ├── SkFont.h                       # 字体配置
│   └── SkTypeface.h                   # 字体实例
└── tools/fonts/
    └── FontToolUtils.h                # 字体工具
```

该 Slide 是 Viewer 应用程序的一个测试场景,用于交互式演示和性能分析。

## 主要类与结构体

### FlutterAnimateView 类

```cpp
class FlutterAnimateView : public Slide {
public:
    FlutterAnimateView();

    // Slide 接口实现
    void load(SkScalar w, SkScalar h) override;
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;

private:
    void initChars();  // 初始化字符数据

    // 动画参数
    static constexpr double kDuration = 5.0;  // 动画周期(秒)
    double fCurrTime;    // 当前时间
    double fResetTime;   // 重置时间点
    SkRandom fRand;      // 随机数生成器

    // 字符数据
    struct AnimatedChar {
        char fChar[2];              // 字符(null-terminated)
        SkPoint fPosition;          // 屏幕位置
        SkScalar fStartRotation;    // 起始旋转角度
        SkScalar fEndRotation;      // 结束旋转角度
    };

    sk_sp<SkTypeface> fTypeface;           // 字体实例
    static constexpr int kNumChars = 40;   // 字符数量
    AnimatedChar fChars[kNumChars];        // 字符数组
};
```

### AnimatedChar 结构体

```cpp
struct AnimatedChar {
    char fChar[2];              // 存储单个字符及 null 终止符
    SkPoint fPosition;          // 字符在画布上的位置
    SkScalar fStartRotation;    // 动画起始旋转角度(弧度)
    SkScalar fEndRotation;      // 动画结束旋转角度(弧度)
};
```

该结构体封装了每个动画字符的所有状态信息。

## 公共 API 函数

### 构造函数

```cpp
FlutterAnimateView();
```
- 初始化 `fCurrTime` 和 `fResetTime` 为 0
- 设置 Slide 名称为 "FlutterAnimate"

### load

```cpp
void load(SkScalar w, SkScalar h) override;
```
- 加载测试字体文件 `/skimages/samplefont.ttf`
- 调用 `initChars()` 初始化字符动画数据
- 参数 `w` 和 `h` 未被使用(保留用于 Slide 接口一致性)

### draw

```cpp
void draw(SkCanvas* canvas) override;
```
- 清空画布为白色
- 遍历所有 40 个字符,计算当前旋转角度
- 对每个字符执行:
  - 保存画布状态
  - 移动到字符位置
  - 应用旋转变换
  - 绘制字符
  - 恢复画布状态
- 使用 50 像素大小的字体

### animate

```cpp
bool animate(double nanos) override;
```
- 更新当前时间: `fCurrTime = 1e-9 * nanos - fResetTime`
- 如果超过动画周期(5 秒),重新初始化字符并重置时间
- 始终返回 `true` 表示需要持续重绘

## 内部实现细节

### 字符初始化

```cpp
void initChars() {
    for (int i = 0; i < kNumChars; ++i) {
        char c = fRand.nextULessThan(26) + 65;  // 随机大写字母 A-Z
        fChars[i].fChar[0] = c;
        fChars[i].fChar[1] = '\0';

        // 随机位置(画布范围内)
        fChars[i].fPosition = SkPoint::Make(
            fRand.nextF() * 748 + 10,   // X: 10-758
            fRand.nextF() * 1004 + 10   // Y: 10-1014
        );

        // 随机旋转角度
        fChars[i].fStartRotation = fRand.nextF();
        fChars[i].fEndRotation = fRand.nextF() * 20 - 10;  // -10 到 10
    }
}
```

每次初始化时:
- 随机选择 A-Z 的字母
- 在指定范围内随机分布位置
- 分配随机的起始和结束旋转角度

### 旋转插值

在 `draw()` 中使用线性插值计算当前旋转角度:

```cpp
double rot = SkScalarInterp(fChars[i].fStartRotation,
                            fChars[i].fEndRotation,
                            fCurrTime / kDuration);
```

### 变换管理

每个字符的绘制使用精确的变换顺序:

```cpp
canvas->save();
// 1. 移动到字符位置(加上字形中心偏移)
canvas->translate(fChars[i].fPosition.fX + kMidX,
                 fChars[i].fPosition.fY - kMidY);
// 2. 应用旋转(转换为角度)
canvas->rotate(SkRadiansToDegrees(rot));
// 3. 反向偏移以实现中心旋转
canvas->translate(-35, +50);
// 4. 绘制字符
canvas->drawString(fChars[i].fChar, 0, 0, font, paint);
canvas->restore();
```

### 周期性重置

动画采用周期性重置策略:

```cpp
if (fCurrTime > kDuration) {
    this->initChars();           // 重新随机化字符
    fResetTime = 1e-9 * nanos;  // 记录重置时间点
    fCurrTime = 0;              // 重置计时器
}
```

这确保动画每 5 秒重新开始,产生不同的随机字符配置。

## 依赖关系

### 直接依赖

- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkFont.h`: 字体配置
- `include/core/SkTypeface.h`: 字体实例
- `tools/viewer/Slide.h`: Slide 基类
- `src/base/SkRandom.h`: 随机数生成
- `tools/fonts/FontToolUtils.h`: 字体工具函数

### 间接依赖

- `include/core/SkPaint.h`: 绘制样式
- `include/core/SkPoint.h`: 点坐标
- `src/base/SkTime.h`: 时间工具

## 设计模式与设计决策

### 固定时间步长动画

使用 5 秒的固定动画周期,配合线性插值实现平滑旋转:

```cpp
static constexpr double kDuration = 5.0;
```

这种设计便于:
- 可预测的性能测试
- 稳定的帧率分析
- 重复的测试场景

### 数据驱动动画

所有字符状态存储在数组中:

```cpp
AnimatedChar fChars[kNumChars];
```

这种设计:
- 便于批量更新
- 支持数据序列化
- 易于扩展字符数量

### 原地旋转变换

通过三步变换实现字符中心旋转:
1. 移动到目标位置
2. 应用旋转
3. 反向偏移实现中心旋转

这避免了复杂的矩阵计算,保持代码清晰。

### 周期性随机化

每个周期重新生成随机字符配置,这样:
- 测试覆盖更多字形组合
- 避免缓存热点
- 提供视觉变化

## 性能考量

### 字形图集压力测试

40 个字符同时旋转创造了高压力场景:
- 每帧可能产生多个不同角度的字形变体
- 测试字形缓存的容量和驱逐策略
- 验证字形图集纹理更新性能

### 旋转成本

文本旋转是昂贵的操作:
- 每个字符需要独立的变换矩阵
- 可能触发字形重新光栅化
- 测试 GPU 和 CPU 的文本渲染路径

### 画布状态管理

使用 `save()`/`restore()` 对确保:
- 变换不会累积
- 每个字符独立渲染
- 最小化状态污染

但频繁的 save/restore 也有开销,这是有意为之的压力测试。

### 字体加载优化

字体在 `load()` 阶段加载一次:

```cpp
fTypeface = ToolUtils::TestFontMgr()->makeFromFile("/skimages/samplefont.ttf");
```

避免每帧重复加载,确保测试专注于渲染性能。

## 相关文件

### 测试相关

- `tools/viewer/Viewer.cpp`: 主 Viewer 应用
- `tools/viewer/Slide.h`: Slide 基类定义

### 字体相关

- `tools/fonts/FontToolUtils.h`: 字体工具函数
- `include/core/SkFont.h`: 字体 API
- `include/core/SkFontMgr.h`: 字体管理器

### 类似的动画 Slide

- `tools/viewer/ClockSlide.cpp`: 时钟动画
- `tools/viewer/SkottieSlide.cpp`: Lottie 动画播放器

### 字形渲染核心

- `src/core/SkGlyphCache.h`: 字形缓存
- `src/core/SkStrike.h`: 字形渲染上下文
- `src/gpu/text/GrAtlasManager.h`: GPU 字形图集管理
