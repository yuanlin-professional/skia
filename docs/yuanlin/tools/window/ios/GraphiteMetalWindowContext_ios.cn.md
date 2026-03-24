# GraphiteMetalWindowContext_ios - iOS Graphite Metal 窗口上下文

> 源文件: `tools/window/ios/GraphiteMetalWindowContext_ios.mm`

## 概述

`GraphiteMetalWindowContext_ios` 实现了 iOS 平台上使用 Metal 图形 API 和 Graphite 渲染后端的窗口上下文。它通过自定义 Objective-C 视图类 `GraphiteMetalView` 将 `CAMetalLayer` 集成到 UIKit 视图层级中，为 Graphite 的 Metal 渲染提供绘图表面。

## 架构位置

- 继承自 `skwindow::internal::GraphiteMetalWindowContext`（跨平台 Graphite Metal 基类）
- 由工厂函数 `MakeGraphiteMetalForIOS` 创建
- 使用 UIKit 框架（`UIViewController`, `UIView`）
- 与 Ganesh 版本 `MetalWindowContext_ios` 平行

## 主要类与结构体

### `GraphiteMetalView`（Objective-C）
- 继承自 `MainView`
- 覆盖 `+layerClass` 返回 `CAMetalLayer`，使视图使用 Metal 层

### `GraphiteMetalWindowContext_ios`（匿名命名空间）
- 继承自 `GraphiteMetalWindowContext`
- 成员：`fWindow`, `fViewController`, `fMetalView`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGraphiteMetalForIOS(IOSWindowInfo&, params)` | 工厂函数 |

## 内部实现细节

### 初始化流程
1. 创建 `GraphiteMetalView` 并添加到视图控制器的视图层级
2. 获取 `CAMetalLayer` 并配置：Metal 设备、像素格式（BGRA8Unorm）、drawable 尺寸、framebufferOnly = false
3. 设置 `contentsGravity = kCAGravityTopLeft` 使内容从左上角开始

### 资源清理
析构函数中先调用基类 `destroyContext()`，然后从视图层级移除并释放 `fMetalView`。

### 尺寸调整
更新 `CAMetalLayer` 的 `drawableSize` 和 `frame`，以及内部的宽高记录。

## 依赖关系

- `tools/window/GraphiteNativeMetalWindowContext.h` - Graphite Metal 基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明和 `IOSWindowInfo`
- `<Metal/Metal.h>` - Metal 框架
- `<UIKit/UIKit.h>` - UIKit 框架

## 设计模式与设计决策

- **Objective-C/C++ 混编**: `.mm` 文件混合使用 Objective-C（UIView 子类）和 C++（窗口上下文）
- **视图层级集成**: 通过自定义 UIView 子类将 Metal 层嵌入视图控制器
- **忽略 MSAA**: iOS 测试应用当前忽略 MSAA 设置
- **framebufferOnly = false**: 允许从帧缓冲读回像素，用于测试和截图

## 性能考量

- `framebufferOnly = false` 会略微降低渲染性能，但对于测试应用可接受
- `CAMetalLayer` 自动管理 Metal drawable 的交换链
- 视图创建和层级操作仅在初始化时执行

## 相关文件

- `tools/window/ios/MetalWindowContext_ios.mm` - Ganesh Metal 版本
- `tools/window/GraphiteNativeMetalWindowContext.h` - 跨平台基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明
