# main.mm - Skottie iOS 应用入口

> 源文件: `tools/skottie_ios_app/main.mm`

## 概述

Skottie iOS 演示应用的主入口文件,实现了一个 iOS 应用程序,加载并播放 Lottie JSON 动画文件。支持 Metal、OpenGL ES 和 CPU 三种渲染后端,通过条件编译自动选择。

## 架构位置

属于 Skia 示例应用层,展示了 Skottie 动画库在 iOS 平台上的集成方式。

## 主要类与结构体

- **`AppViewController`**: UIViewController 子类,管理动画视图的加载和布局
- **`AppDelegate`**: UIApplicationDelegate 实现,应用程序生命周期管理

## 公共 API 函数

- **`-[AppViewController viewDidLoad]`**: 初始化 Skia 上下文并加载所有 JSON 动画
- **`-[AppViewController handleTap:]`**: 处理点击手势,切换动画的暂停/播放状态
- **`main()`**: iOS 应用入口点

## 内部实现细节

应用启动时自动扫描 Bundle 中 `data` 目录下的所有 `.json` 文件,为每个动画创建一个 `SkottieViewController` 和对应的渲染视图。所有动画视图垂直排列在 UIScrollView 中,视图高度按动画宽高比自适应。

## 依赖关系

- `SkiaContext.h`: 抽象渲染上下文
- `SkottieViewController.h`: 动画控制器
- UIKit 框架

## 设计模式与设计决策

- 策略模式: 通过 `SkiaContext` 抽象不同渲染后端(Metal/GL/CPU)
- 条件编译选择最佳后端: Metal > GL > CPU

## 性能考量

动画视图使用 UIStackView 布局,UIScrollView 实现按需渲染可见区域。

## 相关文件

- `tools/skottie_ios_app/SkiaContext.h`
- `tools/skottie_ios_app/SkiaMetalContext.mm`, `SkiaGLContext.mm`, `SkiaUIContext.mm`
