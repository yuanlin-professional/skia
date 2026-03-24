# SkottieViewController

> 源文件：tools/skottie_ios_app/SkottieViewController.h, tools/skottie_ios_app/SkottieViewController.mm

## 概述

SkottieViewController 是 Skottie iOS 应用的核心视图控制器，负责加载、管理和渲染 Lottie 动画。该类继承自 SkiaViewController，将 Skottie 动画引擎封装为 Objective-C 接口，提供播放控制、时间管理和渲染功能。

主要功能：
- 加载 Lottie JSON 动画文件
- 播放/暂停控制
- 时间跳转（seek）
- 自动循环或在结尾停止
- 自适应缩放动画以适配视图尺寸
- 实时渲染到 Skia 画布

该模块包含三个内部辅助类：SkAnimationDraw（绘制管理）、SkTimeKeeper（时间管理）和 SkottieViewController（主控制器）。

## 架构位置

- **基类**：SkiaViewController
- **使用**：Skottie 动画引擎（C++）
- **调用者**：iOS 应用主界面
- **渲染目标**：SkCanvas（通过 SkSurface）

## 主要类与结构体

### SkottieViewController

```objc
@interface SkottieViewController : SkiaViewController
- (bool)loadAnimation:(NSData*)d;
- (void)seek:(float)seconds;
- (bool)togglePaused;
- (bool)isPaused;
- (void)setStopAtEnd:(bool)stop;
- (float)animationDurationSeconds;
- (float)currentTime;
- (CGSize)size;
- (void)draw:(CGRect)rect toCanvas:(SkCanvas*)canvas atSize:(CGSize)size;
@end
```

### SkAnimationDraw（内部类）

```cpp
class SkAnimationDraw {
    void draw(SkSize size, SkCanvas* canvas);
    void load(const void* data, size_t length);
    void seek(double time);
    float duration();
    SkSize size();
private:
    sk_sp<skottie::Animation> fAnimation;
    SkSize fSize;
    SkSize fAnimationSize;
    SkMatrix fMatrix;
};
```

负责：
- 加载和存储 Skottie 动画对象
- 自适应缩放矩阵计算
- 动画渲染到画布

### SkTimeKeeper（内部类）

```cpp
class SkTimeKeeper {
    float currentTime();
    void setDuration(float d);
    bool paused() const;
    void seek(float seconds);
    void togglePaused();
    void setStopAtEnd(bool s);
private:
    double fStartTime;
    float fAnimationMoment;
    float fDuration;
    bool fPaused;
    bool fStopAtEnd;
};
```

负责：
- 时间计算和跟踪
- 播放/暂停状态管理
- 循环和停止逻辑

## 公共 API 函数

### loadAnimation

```objc
- (bool)loadAnimation:(NSData*)data;
```

加载 Lottie JSON 动画。成功返回 true，失败返回 false。

### seek

```objc
- (void)seek:(float)seconds;
```

跳转到动画的指定时间点（秒）。

### togglePaused

```objc
- (bool)togglePaused;
```

切换播放/暂停状态，返回新状态。

### setStopAtEnd

```objc
- (void)setStopAtEnd:(bool)stop;
```

设置是否在动画结尾自动暂停。

### 查询函数

- **isPaused**：返回当前暂停状态
- **animationDurationSeconds**：返回动画总时长
- **currentTime**：返回当前播放时间
- **size**：返回动画的原始尺寸

### draw

```objc
- (void)draw:(CGRect)rect toCanvas:(SkCanvas*)canvas atSize:(CGSize)size;
```

将动画渲染到 Skia 画布。由渲染循环调用。

## 内部实现细节

### 动画加载

```cpp
void load(const void* data, size_t length) {
    skottie::Animation::Builder builder;
    fAnimation = builder.make((const char*)data, (size_t)length);
    fSize = {0, 0};
    fAnimationSize = fAnimation ? fAnimation->size() : SkSize{0, 0};
}
```

使用 Skottie Builder 从 JSON 数据创建动画对象。

### 自适应缩放

```cpp
if (size.width() != fSize.width() || size.height() != fSize.height()) {
    if (fAnimationSize.width() > 0 && fAnimationSize.height() > 0) {
        float scale = std::min(size.width() / fAnimationSize.width(),
                               size.height() / fAnimationSize.height());
        fMatrix.setScaleTranslate(
                scale, scale,
                (size.width()  - fAnimationSize.width()  * scale) * 0.5f,
                (size.height() - fAnimationSize.height() * scale) * 0.5f);
    }
    fSize = size;
}
```

计算缩放和居中矩阵，保持动画宽高比。

### 时间管理

```cpp
float currentTime() {
    if (fPaused) {
        return fAnimationMoment;
    }
    double time = 1e-9 * (SkTime::GetNSecs() - fStartTime);
    if (fStopAtEnd && time >= fDuration) {
        fPaused = true;
        fAnimationMoment = fDuration;
        return fAnimationMoment;
    }
    return std::fmod(time, fDuration);
}
```

暂停时返回固定时刻，播放时计算实时时间。

### 循环逻辑

使用 `std::fmod` 实现循环：
```cpp
return std::fmod(time, fDuration);
```

时间超过总时长时自动回到开始。

### 暂停/播放切换

```cpp
void togglePaused() {
    if (fPaused) {
        double offset = (fAnimationMoment >= fDuration) ? 0 : -1e9 * fAnimationMoment;
        fStartTime = SkTime::GetNSecs() + offset;
        fPaused = false;
    } else {
        fAnimationMoment = this->currentTime();
        fPaused = true;
    }
}
```

暂停→播放：计算新的开始时间以从当前时刻继续
播放→暂停：记录当前时刻

### 渲染流程

```cpp
- (void)draw:(CGRect)rect toCanvas:(SkCanvas*)canvas atSize:(CGSize)size {
    if (!fClock.paused()) {
        fDraw.seek(fClock.currentTime());
    }
    fDraw.draw(SkSize{(float)size.width, (float)size.height}, canvas);
}
```

1. 更新动画时间（如果播放中）
2. 绘制当前帧

## 依赖关系

### Skottie 引擎
- `modules/skottie/include/Skottie.h` - Skottie 动画 API
- `skottie::Animation::Builder` - 动画构建器

### Skia 核心
- `include/core/SkCanvas.h` - 绘制表面
- `include/core/SkMatrix.h` - 变换矩阵
- `src/base/SkTime.h` - 高精度时间

### iOS 框架
- Foundation - NSData、NSObject
- UIKit - UIView、CGRect、CGSize

## 设计模式与设计决策

### MVC 模式
- **Model**：SkAnimationDraw（动画数据）
- **View**：SkCanvas（渲染目标）
- **Controller**：SkottieViewController（协调）

### 组合模式
SkottieViewController 组合 SkAnimationDraw 和 SkTimeKeeper。

### 懒加载缩放矩阵
仅在视图尺寸变化时重新计算矩阵。

### 高精度时间
使用纳秒级 `SkTime::GetNSecs()` 确保平滑动画。

### 状态管理
时间管理器封装所有播放状态逻辑。

## 性能考量

- 缓存缩放矩阵避免重复计算
- 仅在播放时更新动画时间
- Skottie 引擎内部优化（增量渲染等）
- 使用 GPU 加速渲染（通过 Ganesh）

## 相关文件

- `tools/skottie_ios_app/SkiaViewController.h/.mm` - 基类
- `tools/skottie_ios_app/SkMetalViewBridge.h/.mm` - Metal 渲染桥接
- `modules/skottie/include/Skottie.h` - Skottie 引擎
- `include/core/SkCanvas.h` - Skia 画布
- `src/base/SkTime.h` - 时间工具
