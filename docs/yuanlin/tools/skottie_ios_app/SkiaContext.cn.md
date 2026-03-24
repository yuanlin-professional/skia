# SkiaContext

> 源文件：tools/skottie_ios_app/SkiaContext.h, tools/skottie_ios_app/SkiaContext.mm

## 概述

SkiaContext 是 Skottie iOS 应用中的抽象接口类，用于管理 Skia 渲染上下文和视图创建。该类作为工厂接口，根据不同的渲染后端（Metal、OpenGL、UIKit）创建相应的视图和视图控制器。该模块定义了跨渲染后端的统一接口，简化了上层应用代码对不同渲染方式的使用。

主要特性：
- 提供统一的视图创建接口
- 支持多种渲染后端（Metal、OpenGL、UIKit）
- 管理 SkiaViewController 的生命周期
- 作为 Objective-C 和 C++ Skia API 之间的桥接

该类使用 Objective-C 实现，基类实现为空（返回 nil），由具体子类提供实际实现。

## 架构位置

- **角色**：抽象工厂接口
- **子类**：MetalSkiaContext、GLSkiaContext、UISkiaContext（未在文件中显示）
- **使用者**：iOS 应用主视图控制器
- **平台**：仅 iOS/iPadOS

## 主要接口

### SkiaContext

```objc
@interface SkiaContext : NSObject
- (UIView*) makeViewWithController:(SkiaViewController*)vc withFrame:(CGRect)frame;
- (SkiaViewController*) getViewController:(UIView*)view;
@end
```

### 工厂函数

```cpp
SkiaContext* MakeSkiaMetalContext();
SkiaContext* MakeSkiaGLContext();
SkiaContext* MakeSkiaUIContext();
```

这些函数创建不同后端的 SkiaContext 实现。

## 设计模式

- **抽象工厂模式**：定义创建视图和控制器的接口
- **桥接模式**：连接 Objective-C UI 层和 C++ Skia 层
- **策略模式**：不同渲染后端作为可替换策略

## 相关文件

- `tools/skottie_ios_app/SkottieViewController.h` - 视图控制器接口
- `tools/skottie_ios_app/SkMetalViewBridge.h` - Metal 视图桥接
- `tools/skottie_ios_app/GrContextHolder.h` - Ganesh 上下文持有者
