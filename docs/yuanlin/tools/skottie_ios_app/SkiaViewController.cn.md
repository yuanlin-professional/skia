# SkiaViewController

> 源文件：tools/skottie_ios_app/SkiaViewController.h, tools/skottie_ios_app/SkiaViewController.mm

## 概述

SkiaViewController 是 Skottie iOS 应用中的抽象基类，定义了所有 Skia 视图控制器的通用接口。该类提供了绘制到 Skia 画布的基本协议，以及播放控制的接口。子类（如 SkottieViewController）实现具体的绘制和控制逻辑。

主要职责：
- 定义绘制接口（draw 方法）
- 定义播放控制接口（isPaused、togglePaused）
- 提供默认实现（粉色背景）
- 作为 Objective-C 和 C++ Skia API 的桥接基类

该类使用 Objective-C 实现，设计为可被 Swift 或 Objective-C 代码继承和使用。

## 架构位置

- **角色**：抽象基类
- **子类**：SkottieViewController（Lottie 动画控制器）
- **使用者**：SkiaContext 及其子类
- **渲染目标**：SkCanvas

## 主要接口

### SkiaViewController

```objc
@interface SkiaViewController : NSObject
- (void)draw:(CGRect)rect toCanvas:(SkCanvas*)canvas atSize:(CGSize)size;
- (bool)isPaused;
- (void)togglePaused;
@end
```

## 公共 API 函数

### draw

```objc
- (void)draw:(CGRect)rect toCanvas:(SkCanvas*)canvas atSize:(CGSize)size;
```

渲染内容到 Skia 画布。

**参数**：
- `rect` - 需要绘制的区域（CGRect）
- `canvas` - Skia 画布指针
- `atSize` - 视图尺寸

**基类实现**：
```objc
canvas->clear(SkColorSetARGB(255, 255, 192, 203));  // 粉色背景
```

### isPaused

```objc
- (bool)isPaused;
```

查询当前暂停状态。基类实现返回 `false`（始终播放）。

### togglePaused

```objc
- (void)togglePaused;
```

切换播放/暂停状态。基类实现为空操作。

## 内部实现细节

### 默认绘制

基类提供粉色背景作为占位符：
```objc
SkColorSetARGB(255, 255, 192, 203)  // 粉色：RGB(255, 192, 203)
```

这使得未实现绘制的子类容易被识别。

### 空实现模式

播放控制方法提供空实现而非纯虚函数：
```objc
- (void)togglePaused {}
```

这允许不需要播放控制的子类无需实现这些方法。

## 依赖关系

### Skia 核心
- `include/core/SkCanvas.h` - 画布绘制
- `include/core/SkColor.h` - 颜色定义

### iOS 框架
- Foundation - NSObject
- CoreGraphics - CGRect、CGSize

## 设计模式与设计决策

### 模板方法模式
定义绘制和控制的接口，由子类实现具体行为。

### 接口隔离
仅定义最小必要接口，保持简洁。

### 默认实现
提供可见的默认绘制（粉色），便于调试。

### Objective-C 桥接
使用 Objective-C 便于与 iOS UI 框架集成。

## 性能考量

- 基类开销极小（仅虚函数表）
- 粉色清屏是简单的填充操作

## 相关文件

- `tools/skottie_ios_app/SkottieViewController.h/.mm` - 主要子类实现
- `tools/skottie_ios_app/SkiaContext.h/.mm` - 使用此接口
- `include/core/SkCanvas.h` - Skia 画布
